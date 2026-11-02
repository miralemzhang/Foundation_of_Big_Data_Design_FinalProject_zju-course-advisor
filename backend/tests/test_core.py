import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from catalog import Catalog,validate_filters
from memory import Memory,ConflictError

@pytest.fixture(scope='module')
def catalog(sample_catalog):return sample_catalog

def test_scope_and_gpa_evidence(catalog):
    c=catalog.search('策略博弈入门（示例）')['results'][0]
    assert c['teacher']=='示例教师甲' and c['avg_gpa']==3.86
    raw=json.loads((Path(__file__).resolve().parents[2]/'data/sample/gpa.json').read_text())
    assert float(raw[c['source']['teacher_key']][c['source']['row_index']][1])==c['avg_gpa']
    assert all(c['categories'] for c in catalog.courses)
    assert not catalog.search('乒乓球')['results']

def test_hard_filter_and_censored_count(catalog):
    result=catalog.search('',{'min_gpa':4.4,'min_teacher_rating':8,'min_students':1000},page_size=100)
    assert result['results']
    assert all(c['avg_gpa']>=4.4 and c['teacher_rating']>=8 and c['gpa_count_lower']>=1000 for c in result['results'])
    assert not catalog.search('策略博弈入门（示例）',{'min_students':1000})['results']
    low=catalog.search('',{'min_gpa':4})['total'];high=catalog.search('',{'min_gpa':4.5})['total']
    assert high<=low

@pytest.mark.parametrize('f',[{'min_gpa':True},{'min_gpa':float('nan')},{'min_gpa':-1},{'min_gpa':6},
    {'min_gpa':4,'max_gpa':3},{'categories':'当代社会'},{'unknown':1},{'min_students':2.5}])
def test_invalid_filters(f):
    with pytest.raises(ValueError):validate_filters(f)

def test_ambiguous_teachers_and_comments(catalog):
    ambiguous=next(c for c in catalog.courses if c['teacher_match']=='ambiguous')
    assert ambiguous['teacher_info'] is None and ambiguous['teacher_rating'] is None
    assert not [e for e in catalog.evidence(ambiguous['offering_id'])['evidence'] if e['kind']=='comment']
    known=catalog.search('策略博弈入门（示例）')['results'][0]
    assert all(e['scope']=='teacher' for e in catalog.evidence(known['offering_id'])['evidence'] if e['kind']=='comment')

def test_similar_excludes_same_course(catalog):
    c=catalog.search('策略博弈入门（示例）')['results'][0]
    rows=catalog.similar(c['offering_id'])['similar_courses']
    assert rows and all(r['course_id']!=c['course_id'] for r in rows)
    assert len({r['course_id'] for r in rows})==len(rows)

def test_stats(catalog):
    stats=catalog.stats()
    assert sum(s['offerings'] for s in stats['stats'].values())==len(catalog.courses)
    assert stats['summary']['avg_gpa']==pytest.approx(sum(c['avg_gpa'] for c in catalog.courses)/len(catalog.courses))

def test_persistence_isolation_and_shortlist(tmp_path):
    m=Memory(tmp_path/'state.sqlite');s=m.new_session('a');s['filters']={'min_gpa':4};m.save_session(s)
    m.profile('a',{'interests':['生物'],'filters':{'min_gpa':4}})
    n=Memory(tmp_path/'state.sqlite');assert n.session(s['session_id'],'a')['filters']=={'min_gpa':4}
    with pytest.raises(LookupError):n.session(s['session_id'],'b')
    n.shortlist('a',['one','two'],0);n.shortlist('a',['two','one'],1)
    assert m.shortlist('a')['items']==['two','one']
    with pytest.raises(ConflictError):m.shortlist('a',[],0)
    with pytest.raises(ValueError):m.shortlist('a',['one','one'],2)
    assert n.profile('b')['interests']==[]
    m.delete_session(s['session_id'],'a')
    assert n.profile('a')['interests']==['生物'] and n.shortlist('a')['items']==['two','one']
