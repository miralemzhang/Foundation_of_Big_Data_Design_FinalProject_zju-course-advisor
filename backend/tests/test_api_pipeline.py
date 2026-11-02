import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from catalog import Catalog
from memory import Memory
from pipeline import Pipeline
from providers import ProviderError

def tool(name,args):return {'role':'assistant','content':None,'tool_calls':[{'id':'call_test','type':'function','function':{'name':name,'arguments':json.dumps(args)}}]}
def answer(ids=None):return {'role':'assistant','content':json.dumps({'status':'completed','answer':'按工具返回的历史资料查询。','course_ids':ids or [],'evidence_ids':[]})}
class FakeCloud:
    model='test-fixture'
    def __init__(self,messages=None,error=None):self.messages=iter(messages or []);self.error=error
    def chat(self,*args,**kwargs):
        if self.error:raise self.error
        return next(self.messages),{'prompt_tokens':1,'completion_tokens':1},self.model
    def retrieve(self,*args,**kwargs):raise ProviderError('injected_timeout','测试注入超时',504)

@pytest.fixture
def env(tmp_path,sample_catalog):return sample_catalog,Memory(tmp_path/'state.sqlite'),[]

def test_multi_turn_keeps_conditions(env):
    c,m,logs=env;s=m.new_session('u')
    p=Pipeline(c,m,FakeCloud([tool('search_courses',{'query':'','filters_patch':{'min_gpa':4.4}}),answer()]),logs.append)
    r=p.run('历史GPA至少4.4','u',s['session_id']);assert r['effective_constraints']=={'min_gpa':4.4}
    p.cloud=FakeCloud([tool('search_courses',{'query':'生物'}),answer()]);r=p.run('换生物方向，其他条件不变','u',s['session_id'])
    assert r['effective_constraints']=={'min_gpa':4.4} and r['query']=='生物'
    p.cloud=FakeCloud([tool('search_courses',{'filters_patch':{'min_gpa':None}}),answer()]);r=p.run('取消GPA限制','u',s['session_id'])
    assert r['effective_constraints']=={}
    assert any(e['event']=='finish' for e in logs)

def test_unverified_id_fails_after_one_repair(env):
    c,m,logs=env;p=Pipeline(c,m,FakeCloud([answer(['invented']),answer(['invented'])]),logs.append)
    r=p.run('查询','u');assert r['status']=='failed' and r['error']['code']=='verification_failed'
    assert len([e for e in logs if e['event']=='verification_failed'])==2

def test_provider_failure_is_not_success_or_committed(env):
    c,m,logs=env;s=m.new_session('u')
    p=Pipeline(c,m,FakeCloud(error=ProviderError('upstream_timeout','测试超时',504)),logs.append)
    r=p.run('查课程','u',s['session_id']);assert r['status']=='failed' and r['usage'] is None
    assert m.session(s['session_id'],'u')['messages']==[]

def test_retrieval_failure_keeps_verified_local_evidence(env):
    c,m,logs=env;oid=c.search('策略博弈入门（示例）')['results'][0]['offering_id']
    ref=next(e['evidence_id'] for e in c.evidence(oid,limit=5)['evidence'] if e['kind']=='comment')
    final=answer([oid]);final['content']=json.dumps({'status':'completed','answer':f'存在教师级评论[{ref}]','course_ids':[oid],'evidence_ids':[ref]})
    p=Pipeline(c,m,FakeCloud([tool('get_course_evidence',{'offering_id':oid}),final]),logs.append)
    r=p.run('看看评价','u');assert r['status']=='completed'
    assert any(e['event']=='rag_error' for e in logs)

def test_tool_whitelist_and_loop_limit(env):
    c,m,logs=env;p=Pipeline(c,m,FakeCloud([tool('run_shell',{'cmd':'test'}),answer()]),logs.append)
    r=p.run('test','u');assert r['tool_calls'][0]['status']=='failed'
    p.cloud=FakeCloud([tool('run_shell',{})]*6);r=p.run('test','u')
    assert r['status']=='failed' and r['error']['code']=='step_limit'

def test_placeholder_citation_is_rejected(env):
    c,m,logs=env;bad=answer();bad['content']=json.dumps({'status':'completed','answer':'相似依据[相似度证据ID]','course_ids':[],'evidence_ids':[]})
    p=Pipeline(c,m,FakeCloud([bad,bad]),logs.append)
    assert p.run('查依据','u')['error']['code']=='verification_failed'

def test_numeric_evidence_is_real_and_inline_whitespace_normalized(env):
    c,m,logs=env;oid=c.search('策略博弈入门（示例）')['results'][0]['offering_id']
    final=answer([oid]);final['content']=json.dumps({'status':'completed','answer':f'历史GPA为3.86[ gpa_{oid} ]','course_ids':[oid],'evidence_ids':[]})
    p=Pipeline(c,m,FakeCloud([tool('search_courses',{'query':'策略博弈入门（示例）'}),final]),logs.append)
    r=p.run('查GPA','u');assert r['status']=='completed'
    assert r['evidence'][0]['evidence_id']=='gpa_'+oid and '[ gpa_' not in r['answer']

def test_same_course_multiple_teachers_not_counted_as_distinct_courses(env):
    c,m,logs=env;ids=[x['offering_id'] for x in c.search('文化观察（示例）')['results']]
    bad=answer(ids);bad['content']=json.dumps({'status':'completed','answer':'这2门课程都可参考。','course_ids':ids,'evidence_ids':[]})
    p=Pipeline(c,m,FakeCloud([tool('search_courses',{'query':'文化观察（示例）'}),bad,bad]),logs.append)
    result=p.run('查询文化观察（示例）','u')
    assert result['status']=='completed' and result['answer_mode']=='verified_template'
    assert '2条课程—教师记录，涉及1个课程名称' in result['answer']

def test_ambiguous_rating_does_not_guess_a_scale_or_call_cloud(env):
    c,m,logs=env;p=Pipeline(c,m,FakeCloud(error=RuntimeError('must not be called')),logs.append)
    r=p.run('帮我推荐评分4.5以上的课程','u')
    assert r['status']=='needs_clarification' and r['effective_constraints']=={} and r['model_call_count']==0

def test_guessed_college_is_not_committed(env):
    c,m,logs=env;p=Pipeline(c,m,FakeCloud([tool('search_courses',{'query':'策略博弈入门（示例）','filters_patch':{'college':'经济学院'}}),answer()]),logs.append)
    r=p.run('找策略博弈入门（示例）','u');assert r['effective_constraints']=={}
    assert r['tool_calls'][0]['status']=='failed'

def test_record_quantifier_is_normalized_without_changing_numbers(env):
    c,m,logs=env;ids=[x['offering_id'] for x in c.search('文化观察（示例）')['results']]
    final=answer(ids);final['content']=json.dumps({'status':'completed','answer':'2门课程—教师记录，对应1门不同课程。','course_ids':ids,'evidence_ids':[]})
    p=Pipeline(c,m,FakeCloud([tool('search_courses',{'query':'文化观察（示例）'}),final]),logs.append)
    r=p.run('查询文化观察（示例）','u');assert r['status']=='completed' and '2条课程—教师记录' in r['answer']

def test_short_and_grouped_citations_map_to_real_sources(env):
    c,m,logs=env;oid=c.search('策略博弈入门（示例）')['results'][0]['offering_id']
    final=answer([oid]);final['content']=json.dumps({'status':'completed','answer':'历史GPA与教师评分见[E1, E2]。','course_ids':[oid],'evidence_ids':['E1','E2']})
    p=Pipeline(c,m,FakeCloud([tool('search_courses',{'query':'策略博弈入门（示例）'}),final]),logs.append)
    r=p.run('查GPA','u');assert r['status']=='completed' and 'gpa_'+oid in r['answer']
    assert {e['kind'] for e in r['evidence']}=={'gpa','teacher_rating'}

def test_citation_range_expands_only_existing_aliases(env):
    c,m,logs=env;oid=c.search('策略博弈入门（示例）')['results'][0]['offering_id']
    final=answer([oid]);final['content']=json.dumps({'status':'completed','answer':'历史依据[E1–E2]。','course_ids':[oid],'evidence_ids':['E1','E2']})
    p=Pipeline(c,m,FakeCloud([tool('search_courses',{'query':'策略博弈入门（示例）'}),final]),logs.append)
    r=p.run('查询GPA','u');assert r['status']=='completed' and len(r['evidence'])==2

def test_completed_tools_can_use_explicit_template_after_bounded_loop(env):
    c,m,logs=env;p=Pipeline(c,m,FakeCloud([tool('search_courses',{'query':'策略博弈入门（示例）'})]*6),logs.append)
    r=p.run('查询策略博弈入门（示例）GPA','u')
    assert r['status']=='completed' and r['answer_mode']=='verified_template' and r['generation_error']=='step_limit'
    assert r['courses'][0]['avg_gpa']==3.86 and len(r['tool_calls'])<=8

def test_explicit_cancel_is_effective_even_when_model_omits_null_patch(env):
    c,m,logs=env;s=m.new_session('u');s['filters']={'min_gpa':4.1,'min_teacher_rating':8};s['messages']=[{'role':'user','content':'原条件'}];m.save_session(s)
    p=Pipeline(c,m,FakeCloud([tool('search_courses',{'query':'文艺审美','filters_patch':{'categories':['文艺审美']}}),answer()]),logs.append)
    r=p.run('取消GPA限制，只找文艺审美类课程','u',s['session_id'])
    assert 'min_gpa' not in r['effective_constraints'] and r['effective_constraints']['min_teacher_rating']==8

def test_do_not_cancel_is_not_treated_as_reset():
    from constraints import explicit_resets
    assert not explicit_resets('不要取消GPA限制')[1]
    assert explicit_resets('取消GPA限制，只找文艺审美类')[1]=={'min_gpa','max_gpa'}
    assert explicit_resets('取消GPA来源人数限制')[1]=={'min_students'}

def test_model_cannot_silently_clear_unmentioned_constraints(env):
    c,m,logs=env;s=m.new_session('u');s['filters']={'min_gpa':4};s['messages']=[{'role':'user','content':'原条件'}];m.save_session(s)
    p=Pipeline(c,m,FakeCloud([tool('search_courses',{'query':'生物','reset_filters':True}),answer()]),logs.append)
    r=p.run('换成生物方向，其他条件不变','u',s['session_id'])
    assert r['effective_constraints']=={'min_gpa':4} and r['tool_calls'][0]['status']=='failed'

@pytest.mark.parametrize('payload',[None,[],{'query':None},{'filters':[]},{'filters':{'min_gpa':True}},
    {'query':'x'*501},{'semantic':'false'},{'page':False},{'page_size':101}])
def test_search_validation(env,payload):
    c,m,logs=env;client=create_app(c,m,FakeCloud(),logs.append).test_client()
    response=client.post('/api/search',json=payload) if payload is not None else client.post('/api/search',data='plain')
    assert response.status_code==400

def test_api_persistence_and_scope(env):
    c,m,logs=env;client=create_app(c,m,FakeCloud(),logs.append).test_client();h={'X-User-ID':'test_a'}
    oid=c.search('策略博弈入门（示例）')['results'][0]['offering_id']
    assert client.get('/api/health').status_code==200
    assert client.post('/api/search',json={'filters':{'min_gpa':4}}).json['total']>0
    assert client.put('/api/shortlist',headers=h,json={'items':[oid],'revision':0}).status_code==200
    assert client.put('/api/shortlist',headers=h,json={'items':[],'revision':0}).status_code==409
    assert client.get('/api/shortlist',headers={'X-User-ID':'test_b'}).json['items']==[]
    assert client.get('/api/courses/not_found').status_code==404
    assert client.post('/api/compare',json={'offering_ids':[oid,oid]}).status_code==400
    session=client.post('/api/sessions',headers=h,json={}).json
    assert client.get('/api/sessions/'+session['session_id'],headers={'X-User-ID':'test_b'}).status_code==404


def test_numeric_presentation_uses_actual_distinct_count(env):
    c,m,logs=env;ids=[x['offering_id'] for x in c.search('文化观察（示例）')['results']]
    final=answer(ids)
    final['content']=json.dumps({'status':'completed','answer':'已找到2门符合条件的课程。','course_ids':ids,'evidence_ids':[]})
    r=Pipeline(c,m,FakeCloud([tool('search_courses',{'query':'文化观察（示例）'}),final]),logs.append).run('查询文化观察（示例）','u')
    assert r['answer_mode']=='structured_data'
    assert '2条课程—教师记录，涉及1个课程名称' in r['answer']
    assert r['courses'] and all(e['evidence_id'] in r['answer'] for e in r['evidence'])


def test_comparison_request_completes_real_comparison_when_model_only_searches(env):
    c,m,logs=env
    ids=[c.search(q)['results'][0]['offering_id'] for q in ['策略博弈入门（示例）','数字摄影入门（示例）']]
    cloud=FakeCloud([tool('search_courses',{'query':'策略博弈入门（示例）'}),tool('search_courses',{'query':'数字摄影入门（示例）'}),answer(ids)])
    r=Pipeline(c,m,cloud,logs.append).run('比较这两门课程','u')
    assert r['status']=='completed' and r['answer_mode']=='structured_data'
    assert any(t['name']=='compare_courses' and t['origin']=='verifier' for t in r['tool_calls'])
    assert len(r['courses'])==2


@pytest.mark.parametrize('prompt',['你好 你是谁','你好，你能做些什么呀？','谢谢你，辛苦了','我还没想好选什么，先聊聊吧','什么是博弈论？'])
def test_general_conversation_uses_model_and_preserves_course_context(env,prompt):
    c,m,logs=env;s=m.new_session('u')
    last=[{'offering_id':c.courses[0]['offering_id'],'course_name':c.courses[0]['course_name'],'teacher':c.courses[0]['teacher']}]
    s.update(filters={'min_gpa':4.2},query='生物',last_courses=last,messages=[{'role':'user','content':'查课程'}]);m.save_session(s)
    final=answer();payload=json.loads(final['content']);payload['answer']='你好！我是浙大小先生，也可以和你聊聊兴趣和选课思路。';final['content']=json.dumps(payload)
    r=Pipeline(c,m,FakeCloud([final]),logs.append).run(prompt,'u',s['session_id'])
    assert r['status']=='completed' and r['answer_mode']=='model' and r['model_call_count']==1
    assert r['answer']==payload['answer'] and r['tool_calls']==[] and r['courses']==[]
    saved=m.session(s['session_id'],'u')
    assert r['effective_constraints']=={'min_gpa':4.2} and saved['query']=='生物' and saved['last_courses']==last
    assert saved['turns'][-1]['result']['answer']==payload['answer']


@pytest.mark.parametrize('content',['不客气！有想聊的话题随时告诉我。','不客气！很高兴能帮上忙。\n{"status":"completed","answer":"已搜索","course_ids":[],"evidence_ids":[]}'])
def test_direct_model_prose_is_preserved_without_repair(env,content):
    c,m,logs=env
    r=Pipeline(c,m,FakeCloud([{'role':'assistant','content':content}]),logs.append).run('谢谢你','u')
    assert r['status']=='completed' and r['model_call_count']==1
    assert r['answer']==content.split('{')[0].strip() and r['tool_calls']==[]
    assert any(e['event']=='conversational_text' for e in logs)


def test_prose_cannot_bypass_course_id_verification(env):
    c,m,logs=env;bad={'role':'assistant','content':'你好！{"status":"completed","answer":"课程","course_ids":["invented"],"evidence_ids":[]}'}
    r=Pipeline(c,m,FakeCloud([bad,bad]),logs.append).run('你好','u')
    assert r['status']=='failed' and r['error']['code']=='verification_failed'
