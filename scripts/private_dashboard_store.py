"""Transactional private storage shared by Chat and the dashboard.

Raw BLOBs and seed inputs are immutable. Aggregate rendering calls the existing
builder in a private temporary workspace, never the public checkout.
"""
from __future__ import annotations
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
from datetime import datetime, timezone

from scripts.build_capture_dashboard import build
from scripts.import_owner_batch import validate_batch
from scripts.private_dashboard_inputs import SyncError, canonical, digest, decode_files, inspect_sources

SEED_PATTERNS = ('dashboard/baseline_2026.json', 'dashboard/owner_effort_2026-10-26.json',
                 'data/raw/habu_logs/**/*.json', 'data/raw/habu_effort/**/*.json',
                 'data/raw/habu_owner_nights/**/*.json', 'data/raw/habu_owner_amendments/**/*.json',
                 'data/processed/individuals/**/*.csv',
                 'data/reconstructions/habu_captures/*-owner-chat-dashboard-intake.json')

def checked_path(path):
    path = Path(path).absolute()
    if ".." in path.parts: raise SyncError("UNSAFE_PRIVATE_PATH")
    for part in (path, *path.parents):
        try: info = part.lstat()
        except FileNotFoundError: continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise SyncError('UNSAFE_PRIVATE_PATH')
    return path

class Store:
    def __init__(self, root: Path, seed_root: Path, *, code_root: Path | None = None):
        self.root = checked_path(root)
        self.code_root = (code_root or Path(__file__).resolve().parents[1]).resolve(strict=True)
        seed_root = checked_path(seed_root).resolve(strict=True)
        for public in (self.code_root, seed_root):
            if self.root.is_relative_to(public) or public.is_relative_to(self.root):
                raise SyncError('PRIVATE_STORE_OVERLAPS_CHECKOUT')
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name == 'posix': os.chmod(self.root, 0o700)
        self.db_path = checked_path(self.root / 'private-dashboard.sqlite3')
        self.contract = digest(canonical({name:digest((self.code_root/name).read_bytes()) for name in
            ('dashboard/intake-core.js','scripts/build_capture_dashboard.py','scripts/import_owner_batch.py',
             'scripts/private_dashboard_inputs.py')}).encode())
        with self.transaction() as db:
            for statement in (
                'CREATE TABLE IF NOT EXISTS seed(path TEXT PRIMARY KEY, sha TEXT NOT NULL, body BLOB NOT NULL)',
                'CREATE TABLE IF NOT EXISTS blobs(sha TEXT PRIMARY KEY, kind TEXT NOT NULL, body BLOB NOT NULL)',
                'CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY, payload TEXT NOT NULL)',
                'CREATE TABLE IF NOT EXISTS tallies(path TEXT PRIMARY KEY, body BLOB NOT NULL)',
                'CREATE TABLE IF NOT EXISTS snapshots(revision INTEGER PRIMARY KEY, summary TEXT NOT NULL)',
                'CREATE TABLE IF NOT EXISTS applications(receipt TEXT PRIMARY KEY, request_sha TEXT NOT NULL, revision INTEGER NOT NULL, batch TEXT NOT NULL)',
                'CREATE TABLE IF NOT EXISTS channels(receipt TEXT NOT NULL, channel TEXT NOT NULL, received_at TEXT NOT NULL, PRIMARY KEY(receipt,channel))',
            ): db.execute(statement)
            for table in ('seed','blobs','receipts','tallies','snapshots','applications','channels'):
                for operation in ('UPDATE','DELETE'):
                    db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'IMMUTABLE_RECORD'); END")
            if db.execute('SELECT count(*) FROM snapshots').fetchone()[0] == 0:
                inputs = {}
                for pattern in SEED_PATTERNS:
                    for path in seed_root.glob(pattern):
                        checked_path(path)
                        if not path.is_file(): raise SyncError('INVALID_SEED_SOURCE')
                        inputs[path.relative_to(seed_root).as_posix()] = path.read_bytes()
                if 'dashboard/baseline_2026.json' not in inputs or sum(map(len, inputs.values())) > 64*1024*1024:
                    raise SyncError('INVALID_SEED_INPUTS')
                for name, raw in sorted(inputs.items()):
                    db.execute('INSERT INTO seed VALUES(?,?,?)',(name,digest(raw),raw))
                summary = self.render(db)
                db.execute('INSERT INTO snapshots VALUES(0,?)',(canonical(summary),))
        if os.name == 'posix': os.chmod(self.db_path,0o600)

    @contextmanager
    def transaction(self):
        checked_path(self.db_path)
        db = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        try:
            db.execute('PRAGMA synchronous=FULL'); db.execute('BEGIN IMMEDIATE')
            yield db; db.commit()
        except BaseException:
            db.rollback(); raise
        finally: db.close()

    def current(self, db):
        row=db.execute('SELECT revision,summary FROM snapshots ORDER BY revision DESC LIMIT 1').fetchone()
        return {'revision':row[0], 'summary':json.loads(row[1])}

    def snapshot(self):
        with self.transaction() as db: return self.current(db)

    def render(self, db):
        with tempfile.TemporaryDirectory(dir=self.root, prefix='projection-') as directory:
            workspace=Path(directory)
            for path, sha, raw in db.execute('SELECT path,sha,body FROM seed'):
                if digest(raw)!=sha: raise SyncError('SEED_HASH_MISMATCH')
                out=workspace/path
                if not out.resolve().is_relative_to(workspace): raise SyncError('INVALID_SEED_PATH')
                out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(raw)
            for path, raw in db.execute('SELECT path,body FROM tallies'):
                out=workspace/path
                if not out.resolve().is_relative_to(workspace) or out.exists(): raise SyncError('TALLY_CONFLICT')
                out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(raw)
            return build(workspace)

    def prepare(self, files, *, channel):
        if channel not in ('chat','dashboard'): raise SyncError('INVALID_CHANNEL')
        sources=decode_files(files)
        identity={'sources':[(s['sha'],s['kind']) for s in sources], 'contract':self.contract}
        receipt_id=digest(canonical(identity).encode())
        analysis=inspect_sources(sources,self.root,self.code_root)
        payload={'receipt_id':receipt_id,'source_sha256':[s['sha'] for s in sources],
                 'contract':self.contract,'state':'HELD' if analysis['reasons'] else 'READY_FOR_CONFIRMATION',
                 **analysis}
        with self.transaction() as db:
            stored=db.execute('SELECT COALESCE(sum(length(body)),0) FROM blobs').fetchone()[0]
            additional=sum(len(s['body']) for s in sources if not db.execute('SELECT 1 FROM blobs WHERE sha=?',(s['sha'],)).fetchone())
            if stored+additional>2*1024*1024*1024:raise SyncError('PRIVATE_STORE_CAPACITY_REACHED')
            for source in sources:
                old=db.execute('SELECT kind,body FROM blobs WHERE sha=?',(source['sha'],)).fetchone()
                if old and (old[0]!=source['kind'] or old[1]!=source['body']): raise SyncError('SOURCE_HASH_CONFLICT')
                if not old:db.execute('INSERT INTO blobs VALUES(?,?,?)',(source['sha'],source['kind'],source['body']))
            encoded=canonical(payload)
            old=db.execute('SELECT payload FROM receipts WHERE id=?',(receipt_id,)).fetchone()
            if old and old[0]!=encoded:raise SyncError('RECEIPT_CONFLICT')
            if not old:db.execute('INSERT INTO receipts VALUES(?,?)',(receipt_id,encoded))
            db.execute('INSERT OR IGNORE INTO channels VALUES(?,?,?)',(receipt_id,channel,datetime.now(timezone.utc).isoformat()))
            current=self.current(db)
            applied=db.execute('SELECT revision,batch FROM applications WHERE receipt=?',(receipt_id,)).fetchone()
            return {**payload,'revision':current['revision'],'asof':current['summary']['asof'],
                    'archived_sources':len(sources),'applied_revision':applied[0] if applied else None,
                    'applied_confirmations':{x['content']['operational_date']:x['content']['capture_count'] for x in json.loads(applied[1])['files']} if applied else None,
                    'state':'APPLIED' if applied else payload['state']}

    def apply(self, receipt_id, batch, expected_revision):
        if not isinstance(receipt_id,str) or len(receipt_id)!=64 or type(expected_revision) is not int or expected_revision<0:
            raise SyncError('INVALID_APPLY_REQUEST')
        try: asof,entries=validate_batch(batch)
        except (ValueError,TypeError,KeyError): raise SyncError('INVALID_CONFIRMED_BATCH') from None
        request_sha=digest(canonical(batch).encode())
        try:
            with self.transaction() as db:
                receipt=db.execute('SELECT payload FROM receipts WHERE id=?',(receipt_id,)).fetchone()
                if not receipt:raise SyncError('UNKNOWN_RECEIPT')
                payload=json.loads(receipt[0]); current=self.current(db)
                previous=db.execute('SELECT request_sha,revision FROM applications WHERE receipt=?',(receipt_id,)).fetchone()
                if previous:
                    if previous[0]!=request_sha:raise SyncError('ALREADY_APPLIED_DIFFERENT_REQUEST')
                    return {'state':'APPLIED','receipt_id':receipt_id,'revision':previous[1],'duplicate':True}
                if payload['state']=='HELD':raise SyncError('RECEIPT_HELD')
                if payload['contract']!=self.contract:raise SyncError('PARSER_CHANGED_REPREPARE')
                if set(batch['source_sha256'])!=set(payload['source_sha256']):raise SyncError('SOURCE_HASH_MISMATCH')
                for sha in payload['source_sha256']:
                    row=db.execute('SELECT body FROM blobs WHERE sha=?',(sha,)).fetchone()
                    if not row or digest(row[0])!=sha:raise SyncError('SOURCE_HASH_MISMATCH')
                if current['revision']!=expected_revision or asof!=current['summary']['asof']:
                    raise SyncError('REVISION_CONFLICT')
                allowed={n['night'] for n in payload['nights']}
                if any(record['operational_date'] not in allowed for record in entries.values()):
                    raise SyncError('LOG_NIGHT_MISMATCH')
                new_nights={night for night in allowed if night>asof}
                if {record['operational_date'] for record in entries.values()} != new_nights:
                    raise SyncError('ALL_NEW_NIGHTS_MUST_BE_CONFIRMED')
                for path,record in entries.items():
                    if record['operational_date'] not in allowed:raise SyncError('LOG_NIGHT_MISMATCH')
                    if db.execute('SELECT 1 FROM seed WHERE path=?',(path,)).fetchone() or db.execute('SELECT 1 FROM tallies WHERE path=?',(path,)).fetchone():
                        raise SyncError('EXISTING_NIGHT_REVIEW_REQUIRED')
                    db.execute('INSERT INTO tallies VALUES(?,?)',(path,canonical(record).encode()))
                summary=self.render(db); revision=current['revision']+1
                db.execute('INSERT INTO snapshots VALUES(?,?)',(revision,canonical(summary)))
                db.execute('INSERT INTO applications VALUES(?,?,?,?)',(receipt_id,request_sha,revision,canonical(batch)))
                return {'state':'APPLIED','receipt_id':receipt_id,'revision':revision,'duplicate':False}
        except SyncError:raise
        except (ValueError,OSError,sqlite3.Error):raise SyncError('PRIVATE_COMMIT_FAILED') from None
