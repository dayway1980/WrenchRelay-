#!/usr/bin/env python3
"""Dynamic API smoke tests using in-memory stubs; no external services or secrets required."""
import os, sys, types, hashlib, secrets, time, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
os.environ.setdefault('JWT_SECRET','unit-test-only-generated-'+secrets.token_hex(16))
os.environ.pop('MONGO_URL',None); os.environ.pop('MONGODB_URI',None)
os.environ.pop('OPENAI_API_KEY',None); os.environ.pop('GOOGLE_CLIENT_ID',None)
os.environ.pop('STRIPE_SECRET_KEY',None); os.environ.pop('STRIPE_SECRET_KEY_LIVE',None)

# jose stub
jose=types.ModuleType('jose')
class JWTError(Exception): pass
class JWT:
 @staticmethod
 def encode(data,key,algorithm='HS256'):
  payload={'sub':data['sub'],'exp':int(getattr(data['exp'],'timestamp',lambda:data['exp'])())}
  return 'stub.'+json.dumps(payload,separators=(',',':')).encode().hex()
 @staticmethod
 def decode(token,key,algorithms=None):
  try: payload=json.loads(bytes.fromhex(token.split('.',1)[1]).decode())
  except Exception as e: raise JWTError() from e
  if payload.get('exp',0)<int(time.time()): raise JWTError()
  return payload
jose.jwt=JWT; jose.JWTError=JWTError; sys.modules['jose']=jose

# passlib stub
passlib=types.ModuleType('passlib'); context=types.ModuleType('passlib.context')
class CryptContext:
 def __init__(self,*a,**k): pass
 def hash(self,p): return 'h$'+hashlib.sha256(p.encode()).hexdigest()
 def verify(self,p,h): return self.hash(p)==h
context.CryptContext=CryptContext; passlib.context=context; sys.modules['passlib']=passlib; sys.modules['passlib.context']=context

class Cursor:
 def __init__(self,docs): self.docs=list(docs)
 def sort(self,key,direction): self.docs.sort(key=lambda d:d.get(key,''),reverse=direction<0); return self
 def limit(self,n): self.docs=self.docs[:n]; return self
 def __iter__(self): return iter(self.docs)

class Collection:
 def __init__(self): self.docs=[]
 def find_one(self,q):
  for d in self.docs:
   if match(d,q): return d
  return None
 def insert_one(self,d): self.docs.append(dict(d)); return types.SimpleNamespace(inserted_id=len(self.docs))
 def update_one(self,q,update,upsert=False):
  d=self.find_one(q)
  if d is None and upsert:
   d=dict(q); self.docs.append(d)
  if d is None: return types.SimpleNamespace(matched_count=0)
  for k,v in update.get('$setOnInsert',{}).items(): d.setdefault(k,v)
  for k,v in update.get('$set',{}).items(): setpath(d,k,v)
  for k,v in update.get('$inc',{}).items(): setpath(d,k,getpath(d,k,0)+v)
  return types.SimpleNamespace(matched_count=1)
 def find(self,q,projection=None):
  out=[]
  for d in self.docs:
   if match(d,q):
    c=dict(d); c.pop('_id',None); out.append(c)
  return Cursor(out)

def getpath(d,path,default=None):
 cur=d
 for p in path.split('.'):
  if not isinstance(cur,dict) or p not in cur:return default
  cur=cur[p]
 return cur

def setpath(d,path,val):
 parts=path.split('.'); cur=d
 for p in parts[:-1]: cur=cur.setdefault(p,{})
 cur[parts[-1]]=val

def match(d,q):
 for k,v in q.items():
  if k=='$or':
   if not any(match(d,x) for x in v): return False
   continue
  actual=getpath(d,k)
  if isinstance(v,dict) and '$regex' in v:
   import re
   if re.search(v['$regex'],str(actual or ''),re.I if 'i' in v.get('$options','') else 0) is None:return False
  elif actual!=v:return False
 return True

class DB:
 def __init__(self):
  self.users=Collection(); self.work_orders=Collection()
class Client:
 def __init__(self,*a,**k): self.db=DB(); self.admin=types.SimpleNamespace(command=lambda x:{'ok':1})
 def __getitem__(self,name): return self.db
pymongo=types.ModuleType('pymongo'); pymongo.MongoClient=Client; sys.modules['pymongo']=pymongo

# openai stub
openai=types.ModuleType('openai')
class FakeCompletions:
 def create(self,**kwargs): return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content='Verified AI test output'))])
class OpenAI:
 def __init__(self,**kwargs): self.chat=types.SimpleNamespace(completions=FakeCompletions())
openai.OpenAI=OpenAI; sys.modules['openai']=openai

# optional vendor stubs
stripe=types.ModuleType('stripe'); stripe.api_key=''; sys.modules['stripe']=stripe
google=types.ModuleType('google'); oauth2=types.ModuleType('google.oauth2'); gid=types.ModuleType('google.oauth2.id_token'); ga=types.ModuleType('google.auth'); transport=types.ModuleType('google.auth.transport'); grequests=types.ModuleType('google.auth.transport.requests'); grequests.Request=object
gid.verify_oauth2_token=lambda *a,**k: {}
sys.modules.update({'google':google,'google.oauth2':oauth2,'google.oauth2.id_token':gid,'google.auth':ga,'google.auth.transport':transport,'google.auth.transport.requests':grequests})

import server
# Install fake DB after module import (MONGO_URL intentionally absent during import)
server._client=Client(); server._db=server._client.db
server.OPENAI_API_KEY='x'

from fastapi.testclient import TestClient
c=TestClient(server.app)

def chk(name,cond):
 if not cond: raise AssertionError(name)
 print('OK',name)

r=c.get('/api/health'); chk('health-200',r.status_code==200 and r.json()['status']=='ok')
r=c.get('/api/config'); chk('config-personalities',r.status_code==200 and len(r.json()['personalities'])>=10)
password=os.getenv('WRENCHRELAY_TEST_PASSWORD') or secrets.token_urlsafe(14)
r=c.post('/api/auth/register',json={'email':'commission-test@bravatile.com','password':password,'name':'Commission Test'})
chk('register-brava',r.status_code==200 and r.json()['entitlement']['brava_lifetime'] is True and r.json()['entitlement']['plan']=='pro_lifetime')
token=r.json()['token']; h={'Authorization':'Bearer '+token}
r=c.post('/api/auth/login',json={'email':'commission-test@bravatile.com','password':password}); chk('login',r.status_code==200)
r=c.get('/api/me',headers=h); chk('me-pro-lifetime',r.status_code==200 and r.json()['entitlement']['effective_plan']=='pro_lifetime')
r=c.post('/api/ai/work-order',headers=h,json={'text':'Motor stopped. Overload relay was tripped. Reset only after inspection; motor restarted and ran normally.','mode':'industrial','personality':'straight-shooter'}); chk('ai-work-order',r.status_code==200 and 'Verified AI test output' in r.json()['result'])
r=c.post('/api/ai/troubleshoot',json={'text':'No start'}); chk('ai-auth-protected',r.status_code==401)
r=c.post('/api/work-orders',headers=h,json={'mode':'industrial','narrative':'Verified record','data':{'asset':'Press 1','complaint':'No cycle'}}); chk('save-work-order',r.status_code==200)
r=c.get('/api/work-orders',headers=h); chk('history',r.status_code==200 and len(r.json())==1)
r=c.post('/api/auth/google',json={'credential':'x'}); chk('google-config-guard',r.status_code==503)
r=c.post('/api/billing/checkout',headers=h,json={'plan':'pro'}); chk('brava-billing-guard',r.status_code==409)
password2=os.getenv('WRENCHRELAY_TEST_PASSWORD_2') or secrets.token_urlsafe(14)
r=c.post('/api/auth/register',json={'email':'customer@example.com','password':password2,'name':'Customer'}); chk('register-standard',r.status_code==200 and r.json()['entitlement']['trial_active'] is True)
h2={'Authorization':'Bearer '+r.json()['token']}
r=c.post('/api/billing/checkout',headers=h2,json={'plan':'pro'}); chk('billing-config-guard',r.status_code==503)
print('DYNAMIC_SMOKE_PASS')
