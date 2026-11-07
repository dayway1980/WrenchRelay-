"""Durable approval intent ledger. No network calls or vendor writes.

Tenant/actor must come from authenticated server context. The permission callback
must consult current authorization, not claims supplied in an HTTP payload.
"""
from contextlib import contextmanager
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import sqlite3
import time
import uuid


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class ApprovalLedger:
    def __init__(self, path, authorize, clock=time.time):
        self.path, self.authorize, self.clock = str(Path(path)), authorize, clock
        with self._transaction() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS proposals (
                    tenant TEXT NOT NULL, id TEXT NOT NULL, body TEXT NOT NULL,
                    body_hash TEXT NOT NULL, expires REAL NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('PROPOSED','APPROVED','INTENT_RECORDED')),
                    approver TEXT, token_hash TEXT,
                    PRIMARY KEY(tenant,id));
                CREATE TABLE IF NOT EXISTS intents (
                    tenant TEXT NOT NULL, key TEXT NOT NULL, proposal TEXT NOT NULL,
                    PRIMARY KEY(tenant,key), UNIQUE(tenant,proposal),
                    FOREIGN KEY(tenant,proposal) REFERENCES proposals(tenant,id));
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY, tenant TEXT NOT NULL, proposal TEXT NOT NULL,
                    actor TEXT NOT NULL, action TEXT NOT NULL, at REAL NOT NULL,
                    body_hash TEXT NOT NULL,
                    FOREIGN KEY(tenant,proposal) REFERENCES proposals(tenant,id));
                CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
                    BEGIN SELECT RAISE(ABORT,'Audit events are append-only'); END;
                CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
                    BEGIN SELECT RAISE(ABORT,'Audit events are append-only'); END;
            ''')

    @contextmanager
    def _transaction(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA synchronous=FULL')
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            if db.in_transaction:
                db.commit()
        except BaseException:
            if db.in_transaction:
                db.rollback()
            raise
        finally:
            db.close()

    def _permission(self, tenant, actor, action):
        if not tenant or not actor or self.authorize(tenant, actor, action) is not True:
            raise PermissionError('Permission denied')

    def _row(self, db, tenant, proposal):
        row = db.execute('SELECT * FROM proposals WHERE tenant=? AND id=?', (tenant, proposal)).fetchone()
        if row is None:
            raise PermissionError('Proposal unavailable')
        return row

    def _event(self, db, row, actor, action):
        db.execute('INSERT INTO events(tenant,proposal,actor,action,at,body_hash) VALUES(?,?,?,?,?,?)',
                   (row['tenant'], row['id'], actor, action, self.clock(), row['body_hash']))

    def propose(self, tenant, actor, *, connector, asset, revision, payload, before_image, rollback_plan, ttl=300):
        self._permission(tenant, actor, 'propose')
        if not all(isinstance(v, str) and v.strip() for v in (connector, asset, revision, rollback_plan)):
            raise ValueError('Explicit connector, asset, revision and rollback plan required')
        if type(ttl) not in (int, float) or not 0 < ttl <= 900:
            raise ValueError('TTL must be positive and at most 900 seconds')
        body = canonical(dict(connector=connector, asset=asset, revision=revision,
                              payload=payload, before_image=before_image, rollback_plan=rollback_plan))
        proposal = str(uuid.uuid4())
        with self._transaction() as db:
            db.execute('INSERT INTO proposals(tenant,id,body,body_hash,expires,state) VALUES(?,?,?,?,?,?)',
                       (tenant, proposal, body, digest(body), self.clock()+ttl, 'PROPOSED'))
            self._event(db, self._row(db, tenant, proposal), actor, 'PROPOSED')
        return proposal, digest(body)

    def approve(self, tenant, actor, proposal, confirmed_hash):
        self._permission(tenant, actor, 'approve')
        with self._transaction() as db:
            row = self._row(db, tenant, proposal)
            if row['state'] != 'PROPOSED' or row['expires'] <= self.clock():
                raise ValueError('Proposal is expired or already approved')
            if not hmac.compare_digest(row['body_hash'], confirmed_hash):
                raise ValueError('Exact proposal confirmation required')
            token = secrets.token_urlsafe(32)
            db.execute("UPDATE proposals SET state='APPROVED',approver=?,token_hash=? WHERE tenant=? AND id=?",
                       (actor, digest(token), tenant, proposal))
            self._event(db, row, actor, 'APPROVED')
        return token

    def record_intent(self, tenant, actor, proposal, token, *, revision, key):
        """Consume approval once. Returns an audit receipt, never executes a write."""
        self._permission(tenant, actor, 'record_intent')
        if not isinstance(key, str) or not key.strip():
            raise ValueError('Idempotency key required')
        with self._transaction() as db:
            row = self._row(db, tenant, proposal)
            if row['state'] != 'APPROVED' or row['expires'] <= self.clock():
                raise ValueError('Approval unavailable or consumed')
            if row['approver'] != actor or not hmac.compare_digest(row['token_hash'], digest(token)):
                raise PermissionError('Approval does not belong to actor')
            if json.loads(row['body'])['revision'] != revision:
                raise ValueError('Target changed; obtain fresh evidence and approval')
            db.execute('INSERT INTO intents VALUES(?,?,?)', (tenant, key, proposal))
            db.execute("UPDATE proposals SET state='INTENT_RECORDED',token_hash=NULL WHERE tenant=? AND id=?", (tenant, proposal))
            self._event(db, row, actor, 'INTENT_RECORDED')
        return {'proposal': proposal, 'state': 'INTENT_RECORDED', 'vendor_write_executed': False}

    def history(self, tenant, actor, proposal):
        self._permission(tenant, actor, 'audit_read')
        with self._transaction() as db:
            self._row(db, tenant, proposal)
            return [dict(row) for row in db.execute('SELECT * FROM events WHERE tenant=? AND proposal=? ORDER BY seq', (tenant, proposal))]
