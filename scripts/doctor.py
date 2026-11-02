"""Read-only local diagnostic. Never prints credential values."""
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from config import CATALOG_DB

def inspect():
    packages={}
    for name in ['Flask','Werkzeug','Flask-Cors','dashscope','numpy','scipy','scikit-learn','jieba','pytest']:
        try:packages[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:packages[name]=None
    candidates=sorted(ROOT.glob('.tools/node-*/bin/node'))
    node=str(candidates[0]) if candidates else shutil.which('node')
    npm=str(Path(node).parent/'npm') if node else None
    def version(command):
        try:
            env={**os.environ,'PATH':str(Path(node).parent)+os.pathsep+os.environ.get('PATH','')}
            return subprocess.run([command,'--version'],capture_output=True,text=True,check=True,timeout=8,env=env).stdout.strip()
        except (OSError,subprocess.SubprocessError):return None
    result={'python':platform.python_version(),'architecture':platform.machine(),'system':platform.system(),
        'packages':packages,'node':version(node) if node else None,'npm':version(npm) if npm else None,
        'catalog_exists':CATALOG_DB.exists(),'frontend_build_exists':(ROOT/'frontend/build/index.html').exists(),
        'credential_configured':bool(os.getenv('DASHSCOPE_API_KEY')),'workspace_configured':bool(os.getenv('BAILIAN_WORKSPACE_ID')),
        'knowledge_configured':bool(os.getenv('BAILIAN_KNOWLEDGE_IDS')),
        'note':'Configuration presence is not a live cloud connectivity test; see actual probe and evaluation records.'}
    return result
if __name__=='__main__':
    result=inspect();print(json.dumps(result,ensure_ascii=False,indent=2))
    if '--save' in sys.argv:
        (ROOT/'docs/environment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    if platform.python_version_tuple()[:2]!=('3','11') or not all(result['packages'].values()):raise SystemExit(1)
