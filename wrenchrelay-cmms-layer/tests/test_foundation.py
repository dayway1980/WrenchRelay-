from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import unittest

from wrenchrelay_cmms.evidence import Fact, assess
from wrenchrelay_cmms.fiix_readonly import Credentials, prepare_find


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026,10,28,12,tzinfo=timezone.utc)
        self.fact = Fact('e1','t1','a1','11 A','fixture://record/1','current','v1',self.now,self.now)

    def assess(self, fact=None, **changes):
        args = dict(tenant='t1',asset='a1',now=self.now,max_age=timedelta(hours=1),supporting_ids=['e1'])
        args.update(changes)
        return assess([fact or self.fact],**args)

    def test_valid_evidence_still_unresolved_and_uncalibrated(self):
        result = self.assess()
        self.assertEqual(result['diagnosis'],'UNRESOLVED')
        self.assertIsNone(result['probability'])
        self.assertFalse(result['abstain'])

    def test_wrong_tenant_asset_missing_provenance_and_staleness_abstain(self):
        for changes in ({'tenant':'other'},{'asset':'other'},{'source_revision':''},
                        {'observed_at':self.now-timedelta(days=1)}, {'source_record':''}):
            self.assertTrue(self.assess(replace(self.fact,**changes))['abstain'])

    def test_naive_future_and_inverted_times_abstain(self):
        for changes in ({'observed_at':self.now.replace(tzinfo=None)},
                        {'retrieved_at':self.now+timedelta(seconds=1)},
                        {'observed_at':self.now+timedelta(seconds=1)}):
            self.assertTrue(self.assess(replace(self.fact,**changes))['abstain'])

    def test_no_support_unknown_reference_or_contradiction_abstain(self):
        for args in ({'supporting_ids':[]},{'supporting_ids':['missing']},{'contradicting_ids':['e1']}):
            self.assertTrue(self.assess(**args)['abstain'])

    def test_duplicate_evidence_rejected(self):
        with self.assertRaises(ValueError):
            assess([self.fact,self.fact],tenant='t1',asset='a1',now=self.now,max_age=timedelta(hours=1),supporting_ids=['e1'])


class FiixTests(unittest.TestCase):
    def prepare(self, **changes):
        args = dict(base_url='https://synthetic.fiixsandbox.com/api/',credentials=Credentials('fixture-app','fixture-access','fixture-secret'),object_class='Asset',timestamp_ms=1000)
        args.update(changes)
        return prepare_find(**args)

    def test_signature_uses_exact_url_without_protocol(self):
        request = self.prepare()
        expected=hmac.new(b'fixture-secret',request.url[8:].encode(),hashlib.sha256).hexdigest()
        self.assertEqual(request.headers['Authorization'],expected)
        self.assertEqual(request.headers['Content-Type'],'text/plain')
        self.assertEqual(json.loads(request.body)['_maCn'],'FindRequest')

    def test_production_and_unsafe_urls_rejected(self):
        for url in ['https://tenant.macmms.com/api/','http://synthetic.fiixsandbox.com/api/',
                    'https://synthetic.fiixsandbox.com.evil.test/api/',
                    'https://user:pass@synthetic.fiixsandbox.com/api/',
                    'https://synthetic.fiixsandbox.com/api/?override=1']:
            with self.assertRaises(ValueError):self.prepare(base_url=url)

    def test_writes_and_unknown_classes_rejected(self):
        for name in ['AddRequest','ChangeRequest','RemoveRequest','RPCRequest','User','BatchRequest']:
            with self.assertRaises(ValueError):self.prepare(object_class=name)

    def test_bounded_paging(self):
        for args in [{'limit':101},{'limit':0},{'offset':-1},{'limit':True}]:
            with self.assertRaises(ValueError):self.prepare(**args)

    def test_secrets_not_in_object_representations(self):
        self.assertNotIn('fixture-secret',repr(Credentials('a','b','fixture-secret')))
        self.assertNotIn('fixture-access',repr(self.prepare()))


if __name__ == '__main__':unittest.main()
