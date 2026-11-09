import importlib.util
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class Users:
    def __init__(self):
        self.records = []
        self.updates = []

    def find_one(self, query):
        return next((r for r in self.records if all(r.get(k) == v for k, v in query.items())), None)

    def insert_one(self, record):
        self.records.append(record)

    def update_one(self, query, change, **kwargs):
        self.updates.append((query, change))
        record = self.find_one(query)
        if record is None and kwargs.get('upsert'):
            record = dict(query)
            record.update(change.get('$setOnInsert', {}))
            self.records.append(record)
        if record is not None:
            record.update(change.get('$set', {}))


@pytest.fixture(params=['server.py', 'api-service/main.py'])
def api(request, monkeypatch):
    for name in ('MONGO_URL', 'MONGODB_URI', 'OPENAI_API_KEY', 'ADMIN_EMAIL'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('JWT_SECRET', 'test-only-secret-not-a-production-credential')
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_local_only')
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET', 'whsec_local_only')
    spec = importlib.util.spec_from_file_location('app_under_test', Path(request.param))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    users = Users()
    users.records.append({'email': 'tech@example.com', 'plan': 'free'})
    users.records.append({'email': 'owner@example.com', 'plan': 'free'})
    class Database:
        pass
    database = Database()
    database.users = users
    monkeypatch.setattr(module, '_db', database)
    with TestClient(module.app) as client:
        yield module, client, users


def auth_headers(module, claims=None):
    claims = claims if claims is not None else {'sub': 'tech@example.com', 'exp': int(time.time()) + 60}
    token = module.jwt.encode(claims, module.JWT_SECRET, algorithm='HS256')
    return {'Authorization': 'Bearer ' + token}


def test_admin_configuration_fails_closed(api, monkeypatch):
    module, client, users = api
    assert client.get('/api/admin/status', headers=auth_headers(module)).status_code == 503
    monkeypatch.setenv('ADMIN_EMAIL', 'owner@example.com')
    assert client.get('/api/admin/status', headers=auth_headers(module)).status_code == 403
    owner_headers = auth_headers(module, {'sub': 'owner@example.com', 'exp': int(time.time())+60})
    assert client.get('/api/admin/status', headers=owner_headers).status_code == 403
    users.find_one({'email': 'owner@example.com'})['email_verified'] = True
    assert client.get('/api/admin/status', headers=owner_headers).status_code == 200


@pytest.mark.parametrize('claims', [{}, {'sub': 'tech@example.com'}, {'sub': '', 'exp': 9999999999}, {'sub': ['tech'], 'exp': 9999999999}])
def test_malformed_or_nonexpiring_tokens_rejected(api, claims):
    module, client, _ = api
    assert client.get('/api/me', headers=auth_headers(module, claims)).status_code == 401


def test_password_signup_cannot_claim_lifetime_access(api):
    _, client, users = api
    response = client.post('/api/auth/register', json={'email': 'unverified@bravatile.com', 'password': 'local-password-123'})
    assert response.status_code == 200
    assert response.json()['entitlement']['plan'] == 'free'
    assert users.find_one({'email': 'unverified@bravatile.com'})['email_verified'] is False


def test_old_unverified_lifetime_record_is_not_trusted(api):
    module, _, _ = api
    result = module.entitlement_for({'email': 'unverified@bravatile.com', 'plan': 'pro_lifetime', 'auth_method': 'password'})
    assert result['plan'] == 'free'


def test_verified_brava_keeps_lifetime_entitlement(api):
    module, _, _ = api
    assert module.entitlement_for({'email': 'verified@bravatile.com', 'email_verified': True})['plan'] == 'pro_lifetime'


def post_webhook(module, client, event, timestamp=None):
    import hashlib
    import hmac
    body = json.dumps(event).encode()
    stamp = int(time.time()) if timestamp is None else timestamp
    digest = hmac.new(b'whsec_local_only', str(stamp).encode()+b'.'+body, hashlib.sha256).hexdigest()
    return client.post('/api/billing/webhook', content=body, headers={'Stripe-Signature': f't={stamp},v1={digest}'})


@pytest.mark.parametrize('payment_status,plan', [('unpaid','pro'), ('paid','pro_lifetime'), ('paid','unknown')])
def test_webhook_does_not_grant_unpaid_or_unapproved_plans(api, payment_status, plan):
    module, client, users = api
    event = {'id': 'evt_local', 'type': 'checkout.session.completed', 'data': {'object': {'mode': 'subscription', 'payment_status': payment_status, 'customer': 'cus_local', 'subscription': 'sub_local', 'metadata': {'email': 'tech@example.com', 'plan': plan}}}}
    assert post_webhook(module, client, event).status_code == 200
    assert users.updates == []


def test_paid_signed_subscription_grants_approved_plan(api):
    module, client, users = api
    event = {'id': 'evt_local', 'type': 'checkout.session.completed', 'data': {'object': {'mode': 'subscription', 'payment_status': 'paid', 'customer': 'cus_local', 'subscription': 'sub_local', 'metadata': {'email': 'tech@example.com', 'plan': 'pro'}}}}
    assert post_webhook(module, client, event).status_code == 200
    assert users.updates[0][1]['$set']['plan'] == 'pro'


def test_invalid_or_stale_signature_cannot_write(api):
    module, client, users = api
    assert client.post('/api/billing/webhook', content=b'{}').status_code == 400
    assert post_webhook(module, client, {'type': 'checkout.session.completed'}, timestamp=1).status_code == 400
    assert users.updates == []


def test_cookie_write_requires_trusted_origin(api):
    module, client, _ = api
    client.cookies.set(module.SESSION_COOKIE, module.token_for('tech@example.com'))
    assert client.post('/api/auth/logout', headers={'Origin': 'https://attacker.invalid'}).status_code == 403
    assert client.post('/api/auth/logout').status_code == 403
    assert client.post('/api/auth/logout', headers={'Origin': module.FRONTEND_URL + '.attacker.invalid'}).status_code == 403
    assert client.post('/api/auth/logout', headers={'Origin': module.FRONTEND_URL}).status_code == 200


def test_google_verification_revokes_preverification_password_and_session(api, monkeypatch):
    module, client, users = api
    account = {'email': 'verified@bravatile.com', 'auth_method': 'password', 'plan': 'free', 'password_hash': module.pwd.hash('attacker-chosen-password')}
    users.records.append(account)
    old_token = module.token_for(account['email'])
    monkeypatch.setattr(module, 'GOOGLE_CLIENT_ID', 'local-test-client')
    monkeypatch.setattr(module.google_id_token, 'verify_oauth2_token', lambda *args: {'email': account['email'], 'email_verified': True, 'sub': 'google_test_subject'})
    response = client.post('/api/auth/google', json={'credential': 'local-test-only'})
    assert response.status_code == 200
    assert response.json()['entitlement']['plan'] == 'pro_lifetime'
    assert account['password_hash'] is None
    client.cookies.clear()
    assert client.get('/api/me', headers={'Authorization': 'Bearer ' + old_token}).status_code == 401
    assert client.get('/api/me', headers={'Authorization': 'Bearer ' + response.json()['token']}).status_code == 200
    assert client.post('/api/auth/login', json={'email': account['email'], 'password': 'attacker-chosen-password'}).status_code == 401


def test_serving_entrypoints_export_valid_openapi(api):
    _, client, _ = api
    response = client.get('/openapi.json')
    assert response.status_code == 200
    assert '/api/billing/webhook' in response.json()['paths']
