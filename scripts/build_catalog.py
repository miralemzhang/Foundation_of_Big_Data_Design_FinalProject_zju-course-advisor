"""Build the existing tagged general-education scope without modifying raw files."""
import csv
import hashlib
import json
import math
import re
import sqlite3
import sys
import unicodedata
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
from config import CATALOG_DB, DATA_SOURCE_DIR

def normalized(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', str(text)))

def number(value, low=0, high=float('inf')):
    try:
        result = float(value)
        return result if math.isfinite(result) and low <= result <= high else None
    except (ValueError, TypeError):
        return None

def identifier(prefix, *parts):
    return prefix + hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()[:20]

def build(root=DATA_SOURCE_DIR, target=CATALOG_DB):
    root, target = Path(root), Path(target)
    sources = [root/'gpa.json', root/'teachers.csv', root/'courses_selected.txt'] + sorted(root.glob('comment_*.csv'))
    fingerprints = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    processor_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    version = hashlib.sha256(json.dumps({'sources':fingerprints,'processor':processor_hash}, sort_keys=True).encode()).hexdigest()[:16]
    gpa = json.loads((root/'gpa.json').read_text(encoding='utf-8-sig'))
    index = defaultdict(list)
    for teacher, entries in gpa.items():
        for position, row in enumerate(entries):
            if len(row) >= 4:
                index[(normalized(row[0]), normalized(teacher))].append((teacher, position, row))
    teachers, names, raw_names = {}, defaultdict(list), set()
    with (root/'teachers.csv').open(encoding='utf-8-sig', newline='') as f:
        for line, row in enumerate(csv.DictReader(f), 2):
            raw_names.add(row['姓名'])
            tid = row['id'].strip()
            if tid in teachers:
                raise ValueError(f'Duplicate teacher ID at teachers.csv:{line}')
            info = {'id':tid,'name':row['姓名'].strip(),'college':row['学院'].strip(),
                    'rating':number(row['评分'],0,10), 'rating_count':number(row['评分人数']),
                    'heat':number(row['热度']), 'source':f'teachers.csv:{line}'}
            if not info['rating_count']:
                info['rating'] = None
            teachers[tid] = info
            names[normalized(info['name'])].append(info)
    courses, unresolved, duplicate_tags = {}, [], 0
    scope_lines = (root/'courses_selected.txt').read_text(encoding='utf-8-sig').splitlines()
    for line, text in enumerate(scope_lines, 1):
        if not text.strip():
            continue
        match = re.search(r'课程名称：《(.+?)》，授课教师：(.+?)。',text)
        if not match:
            unresolved.append({'source':f'courses_selected.txt:{line}','reason':'unparsed_label'})
            continue
        title, name = match.groups()
        # Legacy annotation sometimes inserted brackets INSIDE the course name.
        # Removing just those brackets restores the literal name; still require exact GPA match.
        title = title.replace('【','').replace('】','')
        matches = index.get((normalized(title), normalized(name)), [])
        if len(matches) > 1:
            stat = re.search(r'平均绩点为([\d.]+)',text)
            if stat:
                matches = [m for m in matches if number(m[2][1],0,5) == float(stat.group(1))]
        if len(matches) != 1:
            unresolved.append({'source':f'courses_selected.txt:{line}','course':title,'teacher':name,
                               'reason':'gpa_mapping_ambiguous' if matches else 'gpa_mapping_missing'})
            continue
        raw_teacher, position, raw = matches[0]
        oid = identifier('o_',raw_teacher,raw)
        tags = sorted(set(re.findall(r'【([^】]+)】',text)))
        if oid in courses:
            courses[oid]['categories'] = sorted(set(courses[oid]['categories']+tags))
            duplicate_tags += 1
            continue
        possible = names.get(normalized(raw_teacher), [])
        teacher = possible[0] if len(possible)==1 else None
        if len(possible)>1:
            unresolved.append({'offering_id':oid,'reason':'teacher_name_ambiguous','teacher_ids':[t['id'] for t in possible]})
        elif not possible:
            unresolved.append({'offering_id':oid,'reason':'teacher_not_in_table'})
        count_raw = str(raw[2]); lower = number(count_raw.rstrip('+'))
        courses[oid] = {'offering_id':oid,'course_id':identifier('c_',normalized(raw[0])),
            'course_name':raw[0],'teacher':raw_teacher,'teacher_id':teacher['id'] if teacher else None,
            'teacher_match':'unique' if teacher else ('ambiguous' if possible else 'unmatched'),
            'teacher_candidates':possible if len(possible)>1 else [],'teacher_info':teacher,
            'college':teacher['college'] if teacher else None,'avg_gpa':number(raw[1],0,5),
            'student_count':count_raw,'gpa_count_lower':lower,'gpa_count_exact':not count_raw.endswith('+'),
            'std_dev':number(raw[3]),'teacher_rating':teacher['rating'] if teacher else None,
            'teacher_rating_count':teacher['rating_count'] if teacher else None,
            'categories':tags,'comment_count':0,'data_version':version,
            'source':{'file':'gpa.json','teacher_key':raw_teacher,'row_index':position,
                      'scope_file':'courses_selected.txt','scope_line':line}}
    if not courses:
        raise ValueError('No scoped courses; refusing to replace the catalog')
    relevant_ids = {c['teacher_id'] for c in courses.values() if c['teacher_id']}
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_suffix('.building.sqlite')
    with sqlite3.connect(staging) as db:
        db.executescript('DROP TABLE IF EXISTS courses; DROP TABLE IF EXISTS comments; DROP TABLE IF EXISTS meta; '
            'CREATE TABLE courses(id TEXT PRIMARY KEY,payload TEXT NOT NULL); '
            'CREATE TABLE comments(id TEXT PRIMARY KEY,teacher_id TEXT,date TEXT,content TEXT,source TEXT,votes REAL); '
            'CREATE INDEX comment_teacher ON comments(teacher_id); CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT);')
        counters = Counter(); by_teacher = Counter()
        for p in sorted(root.glob('comment_*.csv')):
            with p.open(encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f)
                for line,row in enumerate(reader,2):
                    counters['comment_rows']+=1
                    tid,content = (row.get('老师id') or '').strip(),(row.get('内容') or '').strip()
                    if not (row.get('老师姓名') or '').strip() or not content:
                        counters['comment_empty']+=1
                        continue
                    counters['comment_nonempty']+=1
                    if tid not in relevant_ids:
                        continue
                    cid = 'comment_'+(row.get('评论id') or identifier('',p.name,line))
                    cur=db.execute('INSERT OR IGNORE INTO comments VALUES(?,?,?,?,?,?)',
                        (cid,tid,row.get('发表时间'),content,f'{p.name}:{line}',number(row.get('点赞减去点踩数量'),-float('inf'))))
                    if cur.rowcount:
                        by_teacher[tid]+=1; counters['scoped_comments']+=1
                    else:
                        counters['duplicate_comment_ids']+=1
        for c in courses.values():
            c['comment_count']=by_teacher[c['teacher_id']]
            db.execute('INSERT INTO courses VALUES(?,?)',(c['offering_id'],json.dumps(c,ensure_ascii=False)))
        manifest = {'is_sample':(root/'SAMPLE_DATA.md').exists(),'data_version':version,'gpa_teacher_keys':len(gpa),
            'raw_offerings':sum(len(v) for v in gpa.values()),'raw_course_names':len({row[0] for v in gpa.values() for row in v}),
            'teacher_rows':len(teachers),'teacher_names':len({t['name'] for t in teachers.values()}),
            'teacher_name_strings_raw':len(raw_names),'teacher_names_normalized':len(names),
            'processor_sha256':processor_hash,'comment_files':len(list(root.glob('comment_*.csv'))),
            'tagged_lines':sum(bool(x.strip()) for x in scope_lines),'duplicate_tag_records':duplicate_tags,
            'scoped_offerings':len(courses),'scoped_course_names':len({c['course_id'] for c in courses.values()}),
            'scoped_unique_teachers':len(relevant_ids),'unresolved_records':len(unresolved),
            **dict(counters),'sources':fingerprints}
        db.execute('INSERT INTO meta VALUES(?,?)',('manifest',json.dumps(manifest,ensure_ascii=False)))
    staging.replace(target)
    manifest_dir=target.parent.parent/'manifests';manifest_dir.mkdir(parents=True,exist_ok=True)
    (manifest_dir/'catalog.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    (target.parent/'unresolved.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in unresolved)+'\n')
    return manifest

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=DATA_SOURCE_DIR)
    args=parser.parse_args()
    result=build(args.source_dir)
    print(json.dumps({k:v for k,v in result.items() if k!='sources'},ensure_ascii=False,indent=2))
