"""SQLite-backed local identity, sessions, preferences and ordered shortlist."""
import json
import re
import sqlite3
import time
import uuid
from config import STATE_DB
from catalog import validate_filters

class ConflictError(ValueError):
    pass

def identity(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',value):
        raise ValueError('用户／会话标识非法')
    return value

class Memory:
    def __init__(self,path=STATE_DB):
        self.path=path;path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.executescript('CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,profile TEXT NOT NULL,shortlist TEXT NOT NULL,revision INTEGER NOT NULL);'
                'CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,payload TEXT NOT NULL);'
                'CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,user_id TEXT,action TEXT,payload TEXT,created REAL);')

    def connect(self):
        db=sqlite3.connect(self.path,timeout=10)
        db.execute('PRAGMA busy_timeout=10000')
        return db

    def ensure_user(self,user):
        identity(user)
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO users VALUES(?,?,?,0)',(user,json.dumps({'interests':[],'filters':{}}),'[]'))

    def profile(self,user,profile=None):
        self.ensure_user(user)
        if profile is not None:
            if not isinstance(profile,dict) or set(profile)-{'interests','filters'}: raise ValueError('偏好字段非法')
            interests=profile.get('interests',[])
            if not isinstance(interests,list) or len(interests)>12 or any(not isinstance(i,str) or not 1<=len(i)<=80 for i in interests):
                raise ValueError('兴趣最多12项，每项1–80字')
            profile={'interests':list(dict.fromkeys(interests)),'filters':validate_filters(profile.get('filters',{}))}
            with self.connect() as db: db.execute('UPDATE users SET profile=? WHERE id=?',(json.dumps(profile,ensure_ascii=False),user))
        with self.connect() as db: return json.loads(db.execute('SELECT profile FROM users WHERE id=?',(user,)).fetchone()[0])

    def new_session(self,user):
        self.ensure_user(user)
        sid=uuid.uuid4().hex
        result={'session_id':sid,'user_id':user,'messages':[],'turns':[],'filters':{},'query':'','last_courses':[]}
        with self.connect() as db: db.execute('INSERT INTO sessions VALUES(?,?,?)',(sid,user,json.dumps(result,ensure_ascii=False)))
        return result

    def session(self,sid,user):
        identity(sid);identity(user)
        with self.connect() as db: row=db.execute('SELECT payload FROM sessions WHERE id=? AND user_id=?',(sid,user)).fetchone()
        if row is None: raise LookupError('会话不存在或不属于当前用户')
        return json.loads(row[0])

    def save_session(self,session):
        # Keep a bounded conversation; effective constraints and last candidates are explicit state.
        session['messages']=session['messages'][-40:]
        with self.connect() as db:
            cur=db.execute('UPDATE sessions SET payload=? WHERE id=? AND user_id=?',
                (json.dumps(session,ensure_ascii=False),session['session_id'],session['user_id']))
            if not cur.rowcount: raise LookupError('会话已清除')

    def delete_session(self,sid,user):
        self.session(sid,user)
        with self.connect() as db: db.execute('DELETE FROM sessions WHERE id=? AND user_id=?',(sid,user))

    def shortlist(self,user,items=None,revision=None):
        self.ensure_user(user)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            raw,current=db.execute('SELECT shortlist,revision FROM users WHERE id=?',(user,)).fetchone()
            if items is not None:
                if type(revision)!=int or revision!=current: raise ConflictError('清单已变更，请重新加载后再保存')
                if not isinstance(items,list) or len(items)>100 or any(not isinstance(i,str) for i in items) or len(set(items))!=len(items):
                    raise ValueError('清单最多100条且不能重复')
                current+=1;raw=json.dumps(items)
                db.execute('UPDATE users SET shortlist=?,revision=? WHERE id=?',(raw,current,user))
        return {'items':json.loads(raw),'revision':current}

    def event(self,user,action,data):
        self.ensure_user(user)
        if action not in {'search','view_course','add_shortlist','remove_shortlist'}: raise ValueError('不支持的行为类型')
        if not isinstance(data,dict) or len(json.dumps(data,ensure_ascii=False))>4000: raise ValueError('行为数据非法')
        with self.connect() as db: db.execute('INSERT INTO events(user_id,action,payload,created) VALUES(?,?,?,?)',(user,action,json.dumps(data,ensure_ascii=False),time.time()))

    def insights(self,user):
        self.ensure_user(user)
        with self.connect() as db:
            counts=dict(db.execute('SELECT action,COUNT(*) FROM events WHERE user_id=? GROUP BY action',(user,)))
            rows=db.execute('SELECT payload FROM events WHERE user_id=? AND action="view_course" ORDER BY id DESC LIMIT 50',(user,)).fetchall()
        categories={}
        for raw, in rows:
            for c in json.loads(raw).get('categories',[]):
                categories[c]=categories.get(c,0)+1
        return {'total_actions':sum(counts.values()),'search_count':counts.get('search',0),
                'view_count':counts.get('view_course',0),'inferred_categories':categories}
