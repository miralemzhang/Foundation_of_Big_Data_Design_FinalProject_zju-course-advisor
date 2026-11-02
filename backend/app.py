"""Flask entry point; local course services and the BaiLian/Qwen agent."""
import os
import uuid
from flask import Flask,jsonify,request,send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from config import ROOT
from catalog import Catalog,validate_filters
from memory import Memory,ConflictError
from pipeline import Pipeline

def create_app(catalog=None,memory=None,cloud=None,logger=None):
    app=Flask(__name__,static_folder=None)
    app.config['MAX_CONTENT_LENGTH']=65536
    app.json.ensure_ascii=False
    CORS(app,resources={r'/api/*':{'origins':['http://localhost:3000','http://127.0.0.1:3000']}})
    catalog=catalog or Catalog();memory=memory or Memory()
    pipeline=Pipeline(catalog,memory,cloud,**({'logger':logger} if logger else {}))
    app.extensions.update(catalog=catalog,memory=memory,pipeline=pipeline)

    def body():
        if not request.is_json:raise ValueError('请求需要 application/json')
        value=request.get_json(silent=True)
        if not isinstance(value,dict):raise ValueError('JSON请求体必须是对象')
        return value
    def user(data=None):return request.headers.get('X-User-ID') or (data or {}).get('user_id','local_demo')
    def integer(value,default,maximum):
        if value is None:return default
        if isinstance(value,bool):raise ValueError('分页参数必须是整数')
        try:n=int(value)
        except (TypeError,ValueError):raise ValueError('分页参数必须是整数')
        if str(n)!=str(value) or not 1<=n<=maximum:raise ValueError('分页参数超出范围')
        return n

    @app.before_request
    def request_id():request.trace_id=uuid.uuid4().hex

    @app.errorhandler(Exception)
    def error(exc):
        status=409 if isinstance(exc,ConflictError) else 404 if isinstance(exc,LookupError) else 400 if isinstance(exc,(ValueError,TypeError)) else exc.code if isinstance(exc,HTTPException) else 500
        if status==500:app.logger.exception('Unhandled request error')
        return jsonify({'status':'failed','error':{'code':type(exc).__name__,'message':str(exc) if status<500 else '服务内部错误'},'request_id':request.trace_id}),status

    @app.get('/api/health')
    def health():return jsonify({'status':'ready','data_ready':True,'model_configured':bool(os.getenv('DASHSCOPE_API_KEY')),
        'knowledge_configured':bool(os.getenv('BAILIAN_KNOWLEDGE_IDS')),'data_version':catalog.manifest['data_version'],'offerings':len(catalog.courses)})

    @app.get('/api/meta')
    def meta():return jsonify({'categories':catalog.categories,'colleges':sorted({c['college'] for c in catalog.courses if c['college']}),
        'data_version':catalog.manifest['data_version'],'is_sample':catalog.manifest.get('is_sample',False),'scope':'existing_tagged_general_education','summary':catalog.stats()['summary']})

    @app.post('/api/search')
    def search():
        b=body();result=catalog.search(b.get('query',''),b.get('filters'),b.get('sort','relevance'),b.get('page',1),b.get('page_size',20),b.get('semantic',False))
        memory.event(user(b),'search',{'query':b.get('query',''),'filters':result['filters']});return jsonify(result)

    @app.get('/api/courses/<oid>')
    def detail(oid):
        c=catalog.get(oid);memory.event(user(),'view_course',{'offering_id':oid,'categories':c['categories']});return jsonify({'course':c})

    @app.get('/api/courses/<oid>/evidence')
    def evidence(oid):return jsonify(catalog.evidence(oid,request.args.get('query',''),integer(request.args.get('limit'),8,30),integer(request.args.get('page'),1,100000)))

    @app.post('/api/compare')
    def compare():return jsonify(catalog.compare(body().get('offering_ids')))

    @app.post('/api/similar-courses')
    def similar():
        b=body();oid=b.get('offering_id')
        if not oid:
            matches=catalog.resolve(b.get('course_name',''))
            if len(matches)!=1:return jsonify({'status':'needs_clarification','candidates':matches[:20],'similar_courses':[]})
            oid=matches[0]['offering_id']
        return jsonify(catalog.similar(oid,b.get('filters'),b.get('limit',6)))

    @app.get('/api/hot-courses')
    def hot():
        r=catalog.search(sort='popularity',page_size=integer(request.args.get('limit'),12,100))
        return jsonify({'courses':r['results'],'basis':'按已关联教师的评分人数排序；不是实时选课人数','data_version':r['data_version']})

    @app.get('/api/college-stats')
    def stats():return jsonify(catalog.stats())

    @app.get('/api/teachers')
    def teachers():
        infos={c['teacher_id']:c['teacher_info'] for c in catalog.courses if c['teacher_id']}
        values=sorted(infos.values(),key=lambda t:(-(t['rating'] if t['rating'] is not None else -1),t['id']))
        if request.args.get('college'):values=[t for t in values if t['college']==request.args['college']]
        page=integer(request.args.get('page'),1,100000);size=integer(request.args.get('page_size'),20,100)
        return jsonify({'teachers':values[(page-1)*size:page*size],'total':len(values),'page':page})

    @app.route('/api/profile',methods=['GET','PUT'])
    def profile():return jsonify({'profile':memory.profile(user(),body() if request.method=='PUT' else None),'insights':memory.insights(user())})

    @app.post('/api/personalized-recommendations')
    def recommendations():
        b=body();uid=user(b);p=memory.profile(uid);insights=memory.insights(uid)
        f=validate_filters({**p['filters'],**b.get('filters',{})});query=' '.join(p['interests'])
        first=catalog.search(query,f,page_size=100,semantic=True)
        candidates=list(first['results'])
        for page in range(2,(first['total']+99)//100+1):
            candidates.extend(catalog.search(query,f,page=page,page_size=100,semantic=True)['results'])
        weights=insights['inferred_categories'];total=max(sum(weights.values()),1)
        for c in candidates:
            behavior=sum(weights.get(t,0) for t in c['categories'])/total
            c['recommendation_score']=round(c['relevance']+0.2*behavior+0.05*(c['avg_gpa'] or 0)/5,6)
            c['recommendation_reason']='；'.join(([f'兴趣匹配：{query}'] if query else ['尚未设置兴趣，展示符合条件的候选'])+
                (['与你浏览过的通识类别相关'] if behavior else [])+['已核对有效筛选条件'])
        candidates.sort(key=lambda c:(-c['recommendation_score'],c['offering_id']))
        return jsonify({'recommendations':candidates[:integer(b.get('limit'),12,30)],'preferences':p,'filters':f,'insights':insights})

    @app.route('/api/shortlist',methods=['GET','PUT'])
    def shortlist():
        if request.method=='PUT':
            b=body();items=b.get('items')
            if not isinstance(items,list):raise ValueError('items必须是数组')
            for oid in items:
                if not isinstance(oid,str):raise ValueError('课程ID非法')
                catalog.get(oid)
            result=memory.shortlist(user(),items,b.get('revision'))
        else:result=memory.shortlist(user())
        result['courses']=[catalog.get(i) for i in result['items'] if i in catalog.by_id]
        result['unavailable_items']=[i for i in result['items'] if i not in catalog.by_id]
        return jsonify(result)

    @app.post('/api/user-behavior')
    def behavior():
        b=body();memory.event(user(b),b.get('action_type'),b.get('data'));return jsonify({'status':'completed'})

    @app.post('/api/user-insights')
    def insights():return jsonify({'insights':memory.insights(user(body()))})

    @app.post('/api/sessions')
    def new_session():return jsonify(memory.new_session(user(body())))

    @app.route('/api/sessions/<sid>',methods=['GET','DELETE'])
    def session(sid):
        if request.method=='DELETE':memory.delete_session(sid,user());return jsonify({'status':'completed'})
        return jsonify(memory.session(sid,user()))

    @app.post('/api/chat')
    def chat():
        b=body();result=pipeline.run(b.get('prompt'),user(b),b.get('session_id'))
        return jsonify(result),result.get('error',{}).get('http_status',200)

    @app.get('/')
    def index():
        if (ROOT/'frontend/build/index.html').exists():return send_from_directory(ROOT/'frontend/build','index.html')
        return jsonify({'service':'浙大小先生','frontend':'http://localhost:3000','health':'/api/health'})

    @app.get('/static/<path:name>')
    def static(name):return send_from_directory(ROOT/'frontend/build/static',name)
    return app

if __name__=='__main__':create_app().run(host='127.0.0.1',port=int(os.getenv('BACKEND_PORT','5000')),debug=False)
