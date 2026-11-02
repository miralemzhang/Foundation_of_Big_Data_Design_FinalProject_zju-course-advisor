"""Export the current local catalog with provenance; never overwrite raw tags or upload automatically."""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from catalog import Catalog
from config import DATA_SOURCE_DIR

def export():
    catalog=Catalog()
    for name,fingerprint in catalog.manifest['sources'].items():
        if hashlib.sha256((DATA_SOURCE_DIR/name).read_bytes()).hexdigest()!=fingerprint:
            raise ValueError('原始输入已改变，请先运行 scripts/build_catalog.py')
    folder=ROOT/'data/knowledge';folder.mkdir(parents=True,exist_ok=True)
    upload=folder/'upload';upload.mkdir(exist_ok=True)
    docs=[]
    for course in catalog.courses:
        data=catalog.evidence(course['offering_id'],limit=8)
        docs.append({'document_id':course['offering_id'],'data_version':catalog.manifest['data_version'],
            'course_name':course['course_name'],'teacher':course['teacher'],'categories':course['categories'],
            'evidence':data['evidence'],'notes':data['notes']})
    (folder/'documents.jsonl').write_text(''.join(json.dumps(d,ensure_ascii=False)+'\n' for d in docs))
    with (upload/'general_education_with_sources.txt').open('w') as f:
        for d in docs:
            f.write(f"\n## {d['course_name']}｜{d['teacher']}｜记录ID {d['document_id']}\n")
            f.write('类别：'+'、'.join(d['categories'])+'\n')
            for e in d['evidence']:
                f.write(f"[{e['evidence_id']}] 归属层级={e['scope']}；来源={json.dumps(e['source'],ensure_ascii=False)}\n{e['content']}\n")
            f.write('评论为教师级个人观点，不自动代表本课程或当前学期情况。\n')
    summary={'documents':len(docs),'data_version':catalog.manifest['data_version'],
        'export_file':'data/knowledge/upload/general_education_with_sources.txt','uploaded':False,
        'active_runtime':'user-configured cloud knowledge base; verified local matches only'}
    (folder/'export_manifest.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':export()
