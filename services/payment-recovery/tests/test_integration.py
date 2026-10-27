import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import integration
import test_recovery as fixtures


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.Tests(methodName='test_requires_existing_customer_database')
        self.fixture.setUp()
        self.host=ModuleType('fixture_host')
        self.host.app=FastAPI()
        self.host.DB_PATH=self.fixture.path
        def identity(auth):
            if auth!='Bearer fixture-session':
                raise HTTPException(401,'Unauthorized')
            return {'account_id':'a'}
        self.host.current_user=identity
        self.host.config=lambda:{'legal_entity':'WrenchRelay LLC','stripe_enabled':False}
        @self.host.app.get('/unrelated')
        def unrelated(): return {'ok':True}
        @self.host.app.post('/api/checkout')
        def legacy(): return {'legacy':True}
        self.api=fixtures.FakeStripe()
        old=self.api.call
        def call(method,path,parameters=None,idempotency=None):
            if path=='/v1/account':return {'id':'acct_fixture','charges_enabled':True}
            return old(method,path,parameters,idempotency)
        self.api.call=call
        self.env={'WR_PAYMENTS_RECOVERY_ENABLED':'true','STRIPE_ACCOUNT_ID':'acct_fixture',
                  'STRIPE_ALLOWED_PRICE_IDS':'price_pro','STRIPE_DEFAULT_PRICE_ID':'price_pro',
                  'STRIPE_RETURN_ORIGIN':'https://www.wrenchrelayllc.com',
                  'STRIPE_SECRET_KEY_LIVE':'sk_live_fixture','STRIPE_WEBHOOK_SECRET':'whsec_fixture'}

    def tearDown(self):
        self.fixture.tearDown()

    def test_authenticated_checkout_and_existing_routes(self):
        with patch.dict(os.environ,self.env,clear=True),patch.object(integration,'StripeAPI',return_value=self.api):
            integration.install(self.host)
            with TestClient(self.host.app) as c:
                self.assertEqual(c.get('/unrelated').json(),{'ok':True})
                self.assertEqual(c.post('/api/checkout',json={}).status_code,401)
                headers={'Authorization':'Bearer fixture-session','Idempotency-Key':'fixture_request_123456'}
                a=c.post('/api/checkout',json={'price_id':'price_pro'},headers=headers)
                b=c.post('/api/checkout',json={'price_id':'price_pro'},headers=headers)
                self.assertEqual(a.status_code,200);self.assertEqual(a.json(),b.json())
                self.assertEqual(len(self.api.checkout_by_key),1)
                self.assertEqual(c.post('/api/checkout',json={'account_id':'b'},headers=headers).status_code,422)
                self.assertEqual(c.post('/api/checkout',json={'price_id':'price_foreign'},headers=headers).status_code,422)

    def test_unsigned_webhook_rejected_and_signed_event_persisted_before_ack(self):
        with patch.dict(os.environ,self.env,clear=True),patch.object(integration,'StripeAPI',return_value=self.api):
            integration.install(self.host)
            with TestClient(self.host.app) as c:
                self.assertEqual(c.post('/api/stripe/webhook',content=b'{}').status_code,400)
                # Align the fixture signing clock with the integration's real-time clock.
                self.fixture.now=int(time.time())
                raw,sig=self.fixture.event()
                headers={'Stripe-Signature':sig,'Content-Type':'application/json'}
                a=c.post('/api/stripe/webhook',content=raw,headers=headers)
                b=c.post('/api/billing/webhook',content=raw,headers=headers)
                self.assertEqual(a.json(),{'received':True,'queued':True})
                self.assertEqual(b.json(),{'received':True,'queued':False})
                self.assertFalse(c.get('/api/billing/status',headers={'Authorization':'Bearer fixture-session'}).json()['active'])
                with self.fixture.r.connection() as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM wr_payment_inbox').fetchone()[0],1)

    def test_disabled_adapter_preserves_legacy_checkout_and_reports_unavailable(self):
        with patch.dict(os.environ,{'WR_PAYMENTS_RECOVERY_ENABLED':'false'},clear=True):
            integration.install(self.host)
            with TestClient(self.host.app) as c:
                self.assertEqual(c.post('/api/checkout').json(),{'legacy':True})
                self.assertEqual(c.get('/api/billing/health').status_code,503)

    def test_missing_secret_stops_checkout_but_not_the_main_application(self):
        env={**self.env,'STRIPE_SECRET_KEY_LIVE':''}
        with patch.dict(os.environ,env,clear=True),patch.object(integration,'StripeAPI',return_value=self.api):
            integration.install(self.host)
            with TestClient(self.host.app) as c:
                self.assertEqual(c.get('/unrelated').status_code,200)
                self.assertEqual(c.get('/api/billing/health').status_code,503)
                self.assertEqual(c.post('/api/checkout',json={},headers={'Authorization':'Bearer fixture-session'}).status_code,503)


if __name__=='__main__':unittest.main()
