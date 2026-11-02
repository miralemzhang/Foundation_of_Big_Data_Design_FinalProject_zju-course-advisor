import json
import re
import threading
from datetime import datetime,timezone
from config import RUN_LOG

LOCK=threading.Lock()
def write_event(event,path=RUN_LOG):
    path.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps({'time':datetime.now(timezone.utc).isoformat(),**event},ensure_ascii=False,allow_nan=False)
    text=re.sub(r'(?<![A-Za-z])sk-[A-Za-z0-9_-]{12,}','[REDACTED]',text)
    with LOCK,path.open('a',encoding='utf-8') as f:f.write(text+'\n')
