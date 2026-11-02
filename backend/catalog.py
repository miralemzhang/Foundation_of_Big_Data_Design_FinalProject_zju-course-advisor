"""Shared, read-only course services. Numeric constraints are enforced here, not by the LLM."""
import json
import math
import re
import sqlite3
import threading
from collections import defaultdict
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config import CATALOG_DB

FILTERS={'min_gpa','max_gpa','min_teacher_rating','max_teacher_rating','min_teacher_rating_count',
         'min_students','college','categories'}

def validate_filters(filters):
    if not isinstance(filters,dict): raise ValueError('filters 必须是对象')
    if set(filters)-FILTERS: raise ValueError('未知筛选项：'+','.join(sorted(set(filters)-FILTERS)))
    clean={}
    for key,value in filters.items():
        if value is None: continue
        if key=='categories':
            if not isinstance(value,list) or len(value)>20 or any(not isinstance(v,str) or len(v)>50 for v in value):
                raise ValueError('categories 必须是类别字符串数组')
        elif key=='college':
            if not isinstance(value,str) or len(value)>100: raise ValueError('college 必须是学院名称')
        else:
            high=5 if key.endswith('gpa') else (10 if key.endswith('rating') else 10000000)
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=high:
                raise ValueError(f'{key} 必须是 0–{high} 的有限数值')
            if key in {'min_students','min_teacher_rating_count'} and int(value)!=value:
                raise ValueError(f'{key} 必须是整数')
        clean[key]=value
    for lo,hi in [('min_gpa','max_gpa'),('min_teacher_rating','max_teacher_rating')]:
        if lo in clean and hi in clean and clean[lo]>clean[hi]: raise ValueError('筛选下限不能大于上限')
    return clean

class Catalog:
    def __init__(self,path=CATALOG_DB):
        self.path=path
        with self.connection() as db:
            self.courses=[json.loads(r[0]) for r in db.execute('SELECT payload FROM courses ORDER BY id')]
            self.manifest=json.loads(db.execute("SELECT value FROM meta WHERE key='manifest'").fetchone()[0])
        self.by_id={c['offering_id']:c for c in self.courses}
        self.categories=sorted({t for c in self.courses for t in c['categories']})
        self._vectorizer=None; self._matrix=None; self._lock=threading.Lock()

    def connection(self):
        return sqlite3.connect(f'file:{self.path}?mode=ro',uri=True)

    @staticmethod
    def satisfies(c,f):
        for key,field,lower in [('min_gpa','avg_gpa',True),('max_gpa','avg_gpa',False),
                ('min_teacher_rating','teacher_rating',True),('max_teacher_rating','teacher_rating',False),
                ('min_teacher_rating_count','teacher_rating_count',True),('min_students','gpa_count_lower',True)]:
            if key in f and (c.get(field) is None or (c[field]<f[key] if lower else c[field]>f[key])): return False
        if f.get('college') and f['college'] not in (c.get('college') or ''): return False
        if f.get('categories') and not set(f['categories']).intersection(c['categories']): return False
        return True

    def _index(self):
        with self._lock:
            if self._vectorizer is None:
                jieba.setLogLevel(40)
                self._vectorizer=TfidfVectorizer(tokenizer=jieba.lcut,token_pattern=None,lowercase=True,
                                                max_features=12000,ngram_range=(1,2))
                self._matrix=self._vectorizer.fit_transform(c['course_name']+' '+ ' '.join(c['categories']) for c in self.courses)

    def get(self,oid):
        if oid not in self.by_id: raise LookupError('未找到该课程记录')
        return dict(self.by_id[oid])

    def search(self,query='',filters=None,sort='relevance',page=1,page_size=20,semantic=False):
        if not isinstance(query,str) or len(query)>500: raise ValueError('查询必须是500字以内文本')
        filters=validate_filters({} if filters is None else filters)
        if type(semantic)!=bool: raise ValueError('semantic 必须是布尔值')
        if isinstance(page,bool) or not isinstance(page,int) or not 1<=page<=100000: raise ValueError('page 非法')
        if isinstance(page_size,bool) or not isinstance(page_size,int) or not 1<=page_size<=100: raise ValueError('page_size 为1–100')
        if sort not in {'relevance','gpa','rating','popularity'}: raise ValueError('排序方式非法')
        unknown=set(filters.get('categories',[]))-set(self.categories)
        if unknown:raise ValueError('未知通识类别。可用类别：'+'、'.join(self.categories))
        scored=[];q=query.strip().casefold().replace('《','').replace('》','')
        def matches(text):return q in text or (len(q.split())>1 and all(t in text for t in q.split()))
        exact_exists=bool(q and any(matches((c['course_name']+' '+c['teacher']+' '+' '.join(c['categories'])).casefold()) for c in self.courses))
        scores=None
        if q and semantic:
            self._index();scores=cosine_similarity(self._vectorizer.transform([q]),self._matrix)[0]
        for i,c in enumerate(self.courses):
            if not self.satisfies(c,filters): continue
            text=(c['course_name']+' '+c['teacher']+' '+' '.join(c['categories'])).casefold()
            direct=bool(q and matches(text))
            relevance=1.0 if direct else (float(scores[i]) if scores is not None else 0)
            if q and not direct and (exact_exists or not semantic or relevance<=0.015): continue
            scored.append({**c,'relevance':round(relevance,6)})
        field={'gpa':'avg_gpa','rating':'teacher_rating','popularity':'teacher_rating_count','relevance':'relevance'}[sort]
        scored.sort(key=lambda c:(-(c.get(field) if c.get(field) is not None else -1),-(c['avg_gpa'] or 0),c['offering_id']))
        return {'results':scored[(page-1)*page_size:page*page_size],'total':len(scored),
                'total_course_names':len({c['course_id'] for c in scored}),
                'page':page,'page_size':page_size,'filters':filters,'data_version':self.manifest['data_version']}

    def resolve(self,name):
        if name in self.by_id: return [self.get(name)]
        return self.search(name,page_size=100)['results']

    def evidence(self,oid,query='',limit=8,page=1):
        c=self.get(oid)
        if not isinstance(query,str) or len(query)>500: raise ValueError('证据查询过长')
        if type(limit)!=int or not 1<=limit<=30 or type(page)!=int or page<1: raise ValueError('证据分页参数非法')
        entries=[{'evidence_id':'gpa_'+oid,'kind':'gpa','scope':'course_teacher',
                  'content':f"{c['course_name']}，教师{c['teacher']}；历史GPA {c['avg_gpa']}，来源人数 {c['student_count']}，标准差 {c['std_dev']}。",
                  'source':c['source']}]
        if c['teacher_info']:
            t=c['teacher_info'];entries.append({'evidence_id':'teacher_'+t['id'],'kind':'teacher_rating','scope':'teacher',
                'content':f"{t['name']}：教师评分 {t['rating']}，评分人数 {t['rating_count']}。",'source':t['source']})
        with self.connection() as db:
            # Literal LIKE escape prevents '%' / '_' from turning into unintended wildcards.
            escaped=query.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
            rows=db.execute("SELECT id,date,content,source FROM comments WHERE teacher_id=? AND content LIKE ? ESCAPE '\\' ORDER BY votes DESC,id LIMIT ? OFFSET ?",
                            (c['teacher_id'],'%'+escaped+'%',limit,(page-1)*limit)).fetchall()
            matching=db.execute("SELECT COUNT(*) FROM comments WHERE teacher_id=? AND content LIKE ? ESCAPE '\\'",(c['teacher_id'],'%'+escaped+'%')).fetchone()[0]
        entries += [{'evidence_id':r[0],'kind':'comment','scope':'teacher','date':r[1],
                     'content':r[2],'source':r[3]} for r in rows]
        return {'course':c,'evidence':entries,'comment_total':c['comment_count'],'matching_comments':matching,'page':page,
                'notes':['评论属于教师级资料，不自动等同于本课程专项评价。']+
                        (['教师姓名不能唯一关联，未附加教师评分或评论。'] if c['teacher_match']!='unique' else [])}

    def similar(self,oid,filters=None,limit=6):
        target=self.get(oid);filters=validate_filters({} if filters is None else filters)
        if type(limit)!=int or not 1<=limit<=30: raise ValueError('limit 为1–30')
        self._index();pos=next(i for i,c in enumerate(self.courses) if c['offering_id']==oid)
        scores=cosine_similarity(self._matrix[pos],self._matrix)[0]
        candidates=sorted([(float(scores[i]),c) for i,c in enumerate(self.courses)
            if c['course_id']!=target['course_id'] and self.satisfies(c,filters) and scores[i]>0],
            key=lambda item:(-item[0],item[1]['offering_id']))
        seen=set();out=[]
        for score,c in candidates:
            if c['course_id'] in seen: continue
            seen.add(c['course_id']);out.append({**c,'similarity':round(score,6),
                'similarity_basis':'课程名称与通识类别的中文TF-IDF余弦相似度；不是质量分或选中概率'})
            if len(out)>=limit: break
        return {'target':target,'similar_courses':out,'filters':filters}

    def compare(self,ids):
        if not isinstance(ids,list) or not 2<=len(ids)<=3 or len(set(ids))!=len(ids): raise ValueError('比较需要2–3条不同课程记录')
        return {'courses':[self.get(i) for i in ids], 'details':[self.evidence(i,limit=3) for i in ids],
                'notes':['历史GPA和教师评分口径不同；资料缺失时不推断。']}

    def stats(self):
        groups=defaultdict(list)
        for c in self.courses: groups[c['college'] or '教师学院未唯一核实'].append(c)
        stats={}
        for name,rows in sorted(groups.items()):
            grades=[c['avg_gpa'] for c in rows if c['avg_gpa'] is not None]
            stats[name]={'courses':len({c['course_id'] for c in rows}),'offerings':len(rows),
                'teachers':len({c['teacher_id'] for c in rows if c['teacher_id']}),
                'avg_gpa':sum(grades)/len(grades) if grades else None}
        grades=[c['avg_gpa'] for c in self.courses if c['avg_gpa'] is not None]
        return {'stats':stats,'summary':{'courses':len({c['course_id'] for c in self.courses}),
            'offerings':len(self.courses),'teachers':len({c['teacher_id'] for c in self.courses if c['teacher_id']}),
            'avg_gpa':sum(grades)/len(grades) if grades else None},'data_version':self.manifest['data_version']}
