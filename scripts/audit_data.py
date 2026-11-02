"""Verify original data fingerprints and report the current import manifest."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT/'backend'))
from config import DATA_SOURCE_DIR
manifest=json.loads((ROOT/'data/manifests/catalog.json').read_text())
changed=[name for name,digest in manifest['sources'].items() if hashlib.sha256((DATA_SOURCE_DIR/name).read_bytes()).hexdigest()!=digest]
print(json.dumps({'changed_inputs':changed,**{k:v for k,v in manifest.items() if k!='sources'}},ensure_ascii=False,indent=2))
if changed:raise SystemExit(1)
