"""Frozen live task evaluation; deterministic/fault tests remain in pytest."""
import argparse
import csv
import json
import re
import time
import uuid
from pathlib import Path
from catalog import Catalog
from memory import Memory
from pipeline import Pipeline
from config import ROOT
from run_logger import write_event

def check(case,r,catalog):
    errors=[];courses=r.get('courses',[]);mode=case['check']
    if r['status']=='failed':errors.append('agent_failed:'+r.get('error',{}).get('code','unknown'))
    if case.get('expected_status') and r['status']!=case['expected_status']:errors.append('unexpected_status')
    if mode=='known_course':
        if not any(c['course_name']=='博弈论基础' and c['teacher']=='蒋文华' and c['avg_gpa']==3.86 for c in courses):errors.append('known_course_missing')
        if not r.get('evidence'):errors.append('missing_evidence')
        if not any(e.get('kind')=='comment' or e.get('matched_local_ids') for e in r.get('evidence',[])):errors.append('missing_comment_evidence')
    if mode in {'min_gpa','multi_turn'}:
        if r.get('effective_constraints',{}).get('min_gpa')!=case['min_gpa']:errors.append('constraint_not_preserved')
        if any(c['avg_gpa']<case['min_gpa'] for c in courses):errors.append('gpa_violation')
        if mode=='min_gpa' and not courses:errors.append('missing_candidates')
        if mode=='multi_turn' and '生物' not in r.get('query',''):errors.append('interest_not_updated')
    if mode=='combined':
        f=r.get('effective_constraints',{})
        if f.get('min_gpa')!=4 or f.get('min_teacher_rating')!=8 or f.get('min_teacher_rating_count')!=20 or '当代社会' not in f.get('categories',[]):errors.append('parsed_constraints_incorrect')
        if not courses:errors.append('missing_candidates')
    if mode=='no_results' and courses:errors.append('unexpected_candidates')
    if mode=='unsupported' and (courses or not any(word in r['answer'] for word in ['没有','无法','不支持','暂无','不能','不含','不可查','不具备','尚无','未提供'])):errors.append('unsupported_not_disclosed')
    if mode=='clarify' and not any(w in r['answer'] for w in ['GPA','绩点','教师']):errors.append('ambiguous_scale_not_clarified')
    if mode=='similar':
        if not any(t['name']=='find_similar_courses' and t['status']=='completed' for t in r['tool_calls']):errors.append('similar_tool_not_used')
        if not courses or any(c['course_name']=='博弈论基础' for c in courses):errors.append('similar_target_not_excluded')
    if mode=='compare' and {c['course_name'] for c in courses}!={'博弈论基础','数码摄影技术'}:errors.append('comparison_targets_wrong')
    if mode=='multiple_teachers' and {c['teacher'] for c in courses}!={'Demgenski,Philipp','刘朝晖'}:errors.append('teacher_variants_missing')
    if mode=='clear_condition' and ('min_gpa' in r.get('effective_constraints',{}) or '文艺审美' not in r.get('effective_constraints',{}).get('categories',[])):errors.append('condition_not_cleared')
    if mode=='rag' and not any(x.get('status')=='completed' and x.get('retrieved',0)>0 and x.get('verified',0)>0 for x in r.get('knowledge_retrievals',[])):errors.append('cloud_rag_not_verified')
    for c in courses:
        if c['offering_id'] not in catalog.by_id:errors.append('unknown_course')
        if not catalog.satisfies(c,r.get('effective_constraints',{})):errors.append('hard_constraint_violation')
    refs={e['evidence_id'] for e in r.get('evidence',[])}
    if any(x.strip() not in refs for x in re.findall(r'\[([^\[\]]+)\]',r['answer'])):errors.append('invalid_inline_citation')
    if courses and any(int(n)!=len({c['course_id'] for c in courses}) for n in re.findall(r'(\d+)\s*门(?:不同)?(?:通识)?课',r['answer'])):errors.append('course_count_wording')
    return errors

def main():
    p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');p.add_argument('--ids',default='');args=p.parse_args()
    if not args.live:raise SystemExit('Real calls require --live. Unit/fault tests: python -m pytest backend/tests')
    run=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:5]
    folder=ROOT/'evaluation/results'/run;folder.mkdir(parents=True)
    catalog=Catalog()
    if catalog.manifest.get('is_sample'):
        raise SystemExit('固定真实任务需要另交的完整历史数据；结构样例不得用于报告真实评测成绩。')
    memory=Memory(folder/'state.sqlite')
    pipeline=Pipeline(catalog,memory,logger=lambda e:write_event(e,folder/'run_log.jsonl'))
    cases=[json.loads(line) for line in (ROOT/'evaluation/cases.jsonl').read_text().splitlines() if line]
    if args.ids:cases=[c for c in cases if c['id'] in args.ids.split(',')]
    if not cases:raise SystemExit('No evaluation cases selected')
    rows=[]
    for case in cases:
        start=time.monotonic();r=pipeline.run(case['prompt'],'eval_'+case['id']);first=r
        if case.get('followup') and r['status']!='failed':r=pipeline.run(case['followup'],'eval_'+case['id'],r['session_id'])
        errors=check(case,r,catalog)
        (folder/(case['id']+'.json')).write_text(json.dumps({'case':case,'first_result':first,'result':r,'errors':errors},ensure_ascii=False,indent=2))
        row={'id':case['id'],'passed':not errors,'status':r['status'],'duration_ms':round((time.monotonic()-start)*1000),
             'model_calls':r.get('model_call_count',0)+(first.get('model_call_count',0) if first is not r else 0),
             'fallback_turns':int(r.get('answer_mode')=='verified_template')+(int(first.get('answer_mode')=='verified_template') if first is not r else 0),
             'structured_turns':int(r.get('answer_mode')=='structured_data')+(int(first.get('answer_mode')=='structured_data') if first is not r else 0),
             'tool_calls':len(r.get('tool_calls',[])),'errors':';'.join(errors)}
        rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
    summary={'run_id':run,'execution':'live_enabled_no_mock','cases':len(rows),'passed':sum(r['passed'] for r in rows),
        'cases_with_real_model_calls':sum(r['model_calls']>0 for r in rows),'total_model_calls':sum(r['model_calls'] for r in rows),
        'cases_using_verified_template':sum(r['fallback_turns']>0 for r in rows),'verified_template_turns':sum(r['fallback_turns'] for r in rows),
        'structured_data_turns':sum(r['structured_turns'] for r in rows),
        'success_rate':sum(r['passed'] for r in rows)/len(rows),'data_version':catalog.manifest['data_version'],
        'mean_duration_ms':sum(r['duration_ms'] for r in rows)/len(rows),
        'human_review':'Narrative relevance and faithfulness require separate inspection; automated pass is not human approval.'}
    (folder/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    with (folder/'results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps({'folder':str(folder),**summary},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
