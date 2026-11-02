"""Project-local configuration; importing this module never starts a server."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env', override=False)

def path_setting(name, default):
    value = Path(os.getenv(name, default))
    return value if value.is_absolute() else ROOT / value

CATALOG_DB = path_setting('CATALOG_DB', 'data/processed/catalog.sqlite')
STATE_DB = path_setting('STATE_DB', 'runtime/app.sqlite')
RUN_LOG = path_setting('RUN_LOG_PATH', 'logs/run_log.jsonl')

DATA_SOURCE_DIR = path_setting('DATA_SOURCE_DIR', 'data/sample')
