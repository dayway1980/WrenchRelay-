#!/usr/bin/env python3
"""Dependency-light commissioning checks for WrenchRelay source.
Runs without network access and without importing third-party app dependencies.
"""
from pathlib import Path
import ast, json, re, sys

ROOT=Path(__file__).resolve().parents[1]
failures=[]
passes=[]

def ok(name, cond, detail=''):
    (passes if cond else failures).append((name,detail))

# Required files
required=[
    'Dockerfile','railway.json','.env.example','backend/server.py','backend/production.py',
    'backend/requirements.txt','frontend/package.json','frontend/public/index.html',
    'frontend/src/App.js','frontend/src/index.js','frontend/src/styles.css'
]
for f in required: ok(f'required:{f}',(ROOT/f).is_file())

# JSON parse
for f in ['railway.json','frontend/package.json']:
    try: json.loads((ROOT/f).read_text()); ok(f'json:{f}',True)
    except Exception as e: ok(f'json:{f}',False,str(e))

# Python syntax
for f in ROOT.joinpath('backend').glob('*.py'):
    try: ast.parse(f.read_text()); ok(f'python-syntax:{f.name}',True)
    except Exception as e: ok(f'python-syntax:{f.name}',False,str(e))

server=(ROOT/'backend/server.py').read_text()
appjs=(ROOT/'frontend/src/App.js').read_text()
css=(ROOT/'frontend/src/styles.css').read_text()

# Endpoint inventory
routes=[
 '/api/health','/api/config','/api/auth/register','/api/auth/login','/api/auth/google','/api/me',
 '/api/ai/work-order','/api/ai/troubleshoot','/api/ai/handoff','/api/work-orders',
 '/api/knowledge/search','/api/billing/checkout','/api/billing/portal','/api/billing/webhook','/api/admin/status'
]
for r in routes: ok(f'route:{r}',r in server)

# Product feature inventory
features={
 'industrial-mode': "'industrial'" in appjs,
 'automotive-mode': "'automotive'" in appjs,
 'choice-first': 'modeGrid' in appjs and 'Enter Industrial' in appjs and 'Enter Automotive' in appjs,
 'voice-capture': 'SpeechRecognition' in appjs,
 'voice-greeting': 'speechSynthesis' in appjs,
 'google-auth': '/api/auth/google' in appjs and 'accounts.google.com/gsi/client' in appjs,
 'brava-lifetime': 'bravatile.com' in server and 'pro_lifetime' in server,
 'stripe-checkout': '/api/billing/checkout' in appjs,
 'stripe-portal': '/api/billing/portal' in appjs,
 'work-order': '/api/ai/work-order' in appjs,
 'troubleshoot': '/api/ai/troubleshoot' in appjs,
 'handoff': '/api/ai/handoff' in appjs,
 'history': '/api/work-orders' in appjs,
 'legal-terms': "terms:{title:'Terms of Service'" in appjs,
 'legal-privacy': "privacy:{title:'Privacy Policy'" in appjs,
 'legal-safety': "safety:{title:'Industrial & Automotive Safety Policy'" in appjs,
 'legal-billing': "billing:{title:'Subscription, Cancellation & Refund Policy'" in appjs,
 'human-verification': 'Verify before acting' in appjs,
 'responsive-css': '@media(max-width:900px)' in css,
}
for k,v in features.items(): ok(f'feature:{k}',v)

# 12 personalities
m=re.search(r'PERSONALITIES\s*=\s*\{(.*?)\n\}',server,re.S)
if m:
    count=len(re.findall(r'^\s*"[a-z0-9-]+"\s*:',m.group(1),re.M))
    ok('personalities>=10',count>=10,f'count={count}')
else: ok('personalities>=10',False,'PERSONALITIES not found')

# Railway expected settings
rail=json.loads((ROOT/'railway.json').read_text())
ok('railway:dockerfile',rail.get('build',{}).get('builder')=='DOCKERFILE')
ok('railway:healthcheck',rail.get('deploy',{}).get('healthcheckPath')=='/api/health')
ok('railway:no-sleep',rail.get('deploy',{}).get('sleepApplication') is False)

# Safety prompt boundaries
for phrase in ['Never advise bypassing guards','Clearly separate known facts','Do not invent missing facts']:
    ok('safety-prompt:'+phrase,phrase in server)

# Secret scan: detects obvious committed values, ignores variable names/empty examples
secret_patterns=[
 re.compile(r'sk_(?:live|test)_[A-Za-z0-9]{12,}'),
 re.compile(r'gh[pousr]_[A-Za-z0-9]{20,}'),
 re.compile(r'AIza[0-9A-Za-z_-]{20,}'),
 re.compile(r'(?i)(?:api[_-]?key|secret|token|password)\s*[=:]\s*["\'][^"\']{16,}["\']'),
]
hits=[]
for p in ROOT.rglob('*'):
    if not p.is_file() or any(x in p.parts for x in ['node_modules','.git','build']): continue
    if p.suffix.lower() not in {'.py','.js','.json','.txt','.md','.env','.example','.css','.html'} and p.name!='.env.example': continue
    try: text=p.read_text(errors='ignore')
    except Exception: continue
    for pat in secret_patterns:
        if pat.search(text): hits.append(str(p.relative_to(ROOT))); break
ok('security:no-obvious-secrets',not hits,','.join(sorted(set(hits))))

# Ensure test report artifacts aren't shipped
bad=[str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and ('test_reports' in p.parts or p.name.endswith('.report.json'))]
ok('security:no-test-report-artifacts',not bad,','.join(bad))

# Production entrypoint
prod=(ROOT/'backend/production.py').read_text()
docker=(ROOT/'Dockerfile').read_text()
ok('production:imports-app','from server import app' in prod)
ok('production:static-build','frontend' in prod and 'build' in prod)
ok('production:uvicorn-entry','uvicorn production:app' in docker)

print(f'PASS {len(passes)}')
for n,d in passes: print('  OK ',n, ('- '+d) if d else '')
print(f'FAIL {len(failures)}')
for n,d in failures: print('  FAIL',n, ('- '+d) if d else '')
sys.exit(1 if failures else 0)
