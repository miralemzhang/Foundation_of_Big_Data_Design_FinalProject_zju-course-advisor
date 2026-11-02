"""Public offline fixture: always use the fictional dataset and temporary SQLite."""
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
sys.path.insert(0,str(ROOT/'scripts'))
from catalog import Catalog
from build_catalog import build
@pytest.fixture(scope='session')
def sample_catalog(tmp_path_factory):
    target=tmp_path_factory.mktemp('sample')/'processed/catalog.sqlite'
    build(ROOT/'data/sample',target)
    return Catalog(target)
