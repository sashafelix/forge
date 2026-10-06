"""Transactional state, event cursors and locally authenticated host receipts."""
from __future__ import annotations
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)

def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

def atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('Refusing symlink storage')
    temporary = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    with temporary.open('xb') as stream:
        os.chmod(temporary, 0o600); stream.write(data); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)

class Store:
    def __init__(self, root: Path, create: bool = False):
        self.root = root.resolve()
        if root.is_symlink() or any(p.is_symlink() for p in root.absolute().parents): raise ValueError('Run directory cannot contain a symlink')
        if create:
            self.root.mkdir(mode=0o700, parents=True, exist_ok=False)
            atomic(self.root/'authority.key', os.urandom(32))
        if not (self.root/'state.sqlite3').exists() and not create:
            raise ValueError('No host state at the selected run directory')
        if any((self.root/name).is_symlink() for name in ('authority.key','state.sqlite3','state.sqlite3-wal','state.sqlite3-shm')):
            raise ValueError('Host storage cannot contain symlinks')
        self.key = (self.root/'authority.key').read_bytes()
        if len(self.key) != 32: raise ValueError('Invalid receipt authority')
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS receipts (id TEXT PRIMARY KEY, data TEXT NOT NULL, signature TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS lease (id INTEGER PRIMARY KEY CHECK(id=1), owner TEXT, expires REAL, pid INTEGER);
            ''')
        os.chmod(self.root/'state.sqlite3', 0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.root/'state.sqlite3', timeout=10)
        try:
            db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA synchronous=FULL')
            with db: yield db
        finally: db.close()

    def state(self) -> dict:
        with self.connect() as db: row=db.execute('SELECT data FROM state WHERE id=1').fetchone()
        if not row: raise ValueError('Host run has no state')
        return json.loads(row[0])

    def update(self, state: dict, event: dict | None = None) -> None:
        state['updated_at'] = now()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous=db.execute('SELECT data FROM state WHERE id=1').fetchone()
            if previous and json.loads(previous[0]).get('status')=='cancelled' and state.get('status')!='cancelled':
                raise ValueError('Run was cancelled; stale updates cannot restart it')
            db.execute('INSERT OR REPLACE INTO state VALUES (1,?)', (canonical(state),))
            if event:
                sequence = db.execute('SELECT COALESCE(MAX(seq),0)+1 FROM events').fetchone()[0]
                event = {'schema_version':'1.0','sequence':sequence,'timestamp':now(),'story_id':state['story_id'],
                         'attempt':state['attempt'],'stage':state['stage'],'actor_role':'orchestrator','artifact_refs':[], **event}
                db.execute('INSERT INTO events(seq,data) VALUES (?,?)', (sequence,canonical(event)))

    def event(self, kind: str, **fields) -> None:
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            state=json.loads(db.execute('SELECT data FROM state WHERE id=1').fetchone()[0])
            sequence=db.execute('SELECT COALESCE(MAX(seq),0)+1 FROM events').fetchone()[0]
            event={'schema_version':'1.0','sequence':sequence,'timestamp':now(),'story_id':state['story_id'],
                   'attempt':state['attempt'],'stage':state['stage'],'actor_role':'orchestrator','artifact_refs':[],'event_type':kind,**fields}
            db.execute('INSERT INTO events(seq,data) VALUES (?,?)',(sequence,canonical(event)))

    def events(self, after: int = 0, limit: int = 200) -> list[dict]:
        if type(after) is not int or after < 0 or type(limit) is not int or not 1 <= limit <= 1000: raise ValueError('Invalid event cursor')
        with self.connect() as db: rows=db.execute('SELECT data FROM events WHERE seq>? ORDER BY seq LIMIT ?', (after,limit)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def receipt(self, payload: dict) -> dict:
        payload = {'schema_version':'1.0','host_version':'1.0','issued_at':now(), **payload}
        encoded=canonical(payload); signature=hmac.new(self.key,encoded.encode(),hashlib.sha256).hexdigest()
        with self.connect() as db:
            db.execute('INSERT INTO receipts VALUES (?,?,?)',(payload['id'],encoded,signature))
        return {**payload,'signature':signature}

    def receipts(self) -> list[dict]:
        with self.connect() as db: rows=db.execute('SELECT data,signature FROM receipts ORDER BY rowid').fetchall()
        result=[]
        for encoded,signature in rows:
            if not hmac.compare_digest(signature,hmac.new(self.key,encoded.encode(),hashlib.sha256).hexdigest()): raise ValueError('Host receipt ledger was modified')
            result.append({**json.loads(encoded),'signature':signature})
        return result

    @contextmanager
    def worker(self):
        owner=uuid.uuid4().hex
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT owner,expires,pid FROM lease WHERE id=1').fetchone()
            if self.active_lease(row): raise ValueError('Another worker owns this run')
            db.execute('INSERT OR REPLACE INTO lease VALUES (1,?,?,?)',(owner,time.time()+600,os.getpid()))
        try: yield owner
        finally:
            with self.connect() as db: db.execute('UPDATE lease SET owner=NULL,expires=0 WHERE id=1 AND owner=?',(owner,))

    def heartbeat(self, owner: str):
        with self.connect() as db:
            updated=db.execute('UPDATE lease SET expires=? WHERE id=1 AND owner=?',(time.time()+600,owner)).rowcount
            if not updated: raise ValueError('Run ownership was lost')

    @staticmethod
    def active_lease(row):
        if not row or not row[0] or row[1]<=time.time():return False
        try:os.kill(row[2],0)
        except ProcessLookupError:return False
        except (PermissionError,OSError):return True
        return True

    def worker_active(self):
        with self.connect() as db:row=db.execute('SELECT owner,expires,pid FROM lease WHERE id=1').fetchone()
        return self.active_lease(row)

    def event_bytes(self):
        with self.connect() as db: rows=db.execute('SELECT data FROM events ORDER BY seq').fetchall()
        return ('\n'.join(row[0] for row in rows)+'\n').encode()

    def project_events(self, bundle: Path):
        atomic(bundle/'events.jsonl', self.event_bytes())
