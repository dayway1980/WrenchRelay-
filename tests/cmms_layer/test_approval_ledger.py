from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
import unittest

from cmms_layer.approval_ledger import ApprovalLedger


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'audit.db'
        self.now = 100
        self.allowed = True
        self.ledger = self.open()

    def open(self):
        return ApprovalLedger(self.path, lambda tenant, actor, action: self.allowed and tenant == 't1' and actor == 'tech', lambda: self.now)

    def propose(self):
        return self.ledger.propose('t1', 'tech', connector='synthetic', asset='asset1', revision='v1',
                                   payload={'note': 'observed'}, before_image={'note': ''}, rollback_plan='Separate approved compensation')

    def intent(self, proposal, token, ledger=None, **changes):
        args = dict(revision='v1', key='key1')
        args.update(changes)
        return (ledger or self.ledger).record_intent('t1','tech',proposal,token,**args)

    def test_restart_and_no_vendor_write(self):
        proposal, hashed = self.propose()
        token = self.ledger.approve('t1','tech',proposal,hashed)
        receipt = self.intent(proposal,token,self.open())
        self.assertFalse(receipt['vendor_write_executed'])
        self.assertEqual([e['action'] for e in self.open().history('t1','tech',proposal)], ['PROPOSED','APPROVED','INTENT_RECORDED'])

    def test_exact_confirmation_required(self):
        proposal, _ = self.propose()
        with self.assertRaises(ValueError):
            self.ledger.approve('t1','tech',proposal,'changed')

    def test_expiry(self):
        proposal, hashed = self.propose()
        token = self.ledger.approve('t1','tech',proposal,hashed)
        self.now = 400
        with self.assertRaises(ValueError):
            self.intent(proposal,token)

    def test_revision_change_does_not_consume_approval(self):
        proposal, hashed = self.propose()
        token = self.ledger.approve('t1','tech',proposal,hashed)
        with self.assertRaises(ValueError):
            self.intent(proposal,token,revision='v2')
        self.intent(proposal,token)

    def test_revoked_permissions(self):
        proposal, hashed = self.propose()
        token = self.ledger.approve('t1','tech',proposal,hashed)
        self.allowed = False
        with self.assertRaises(PermissionError):
            self.intent(proposal,token)

    def test_cross_tenant_denied_even_with_broad_permission_callback(self):
        proposal, _ = self.propose()
        other = ApprovalLedger(self.path,lambda *args: True)
        with self.assertRaises(PermissionError):
            other.history('t2','tech',proposal)

    def test_wrong_token_and_actor_denied(self):
        proposal, hashed = self.propose()
        token = self.ledger.approve('t1','tech',proposal,hashed)
        with self.assertRaises(PermissionError):
            self.intent(proposal,'wrong')
        other = ApprovalLedger(self.path,lambda *args: True,lambda: self.now)
        with self.assertRaises(PermissionError):
            other.record_intent('t1','other',proposal,token,revision='v1',key='x')

    def test_replay_denied(self):
        proposal, hashed = self.propose()
        token = self.ledger.approve('t1','tech',proposal,hashed)
        self.intent(proposal,token)
        with self.assertRaises(ValueError):
            self.intent(proposal,token)

    def test_concurrent_consumption_has_single_winner(self):
        proposal, hashed = self.propose()
        token = self.ledger.approve('t1','tech',proposal,hashed)
        def attempt(_):
            try:
                self.intent(proposal,token,self.open())
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(attempt,range(2))),1)

    def test_idempotency_conflict_rolls_back_transaction(self):
        proposal, hashed = self.propose()
        token = self.ledger.approve('t1','tech',proposal,hashed)
        self.intent(proposal,token)
        second, hashed = self.propose()
        token2 = self.ledger.approve('t1','tech',second,hashed)
        with self.assertRaises(sqlite3.IntegrityError):
            self.intent(second,token2)
        self.assertEqual(len(self.ledger.history('t1','tech',second)),2)
        self.intent(second,token2,key='key2')

    def test_audit_cannot_be_updated_or_deleted_through_sql(self):
        self.propose()
        with sqlite3.connect(self.path) as db:
            for sql in ('UPDATE events SET actor="other"','DELETE FROM events'):
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute(sql)


if __name__ == '__main__':
    unittest.main()
