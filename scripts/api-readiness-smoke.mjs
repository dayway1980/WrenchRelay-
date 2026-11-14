#!/usr/bin/env node
// Read-only API readiness checks. No account creation, billing, or writes.
// WR_API_URL=https://verified-api-origin.example node scripts/api-readiness-smoke.mjs
const raw=process.env.WR_API_URL;
if(!raw){console.error('WR_API_URL is required');process.exit(2)}
let origin;try{origin=new URL(raw)}catch{console.error('Invalid URL');process.exit(2)}
if(origin.protocol!=='https:'||origin.username||origin.password||origin.pathname!=='/'||origin.search||origin.hash){console.error('Use an HTTPS origin without credentials or path');process.exit(2)}
const checks=[
  {path:'/api/health/live',validate:d=>d.status==='ok'&&d.service==='wrenchrelay'},
  {path:'/api/health/ready',validate:d=>d.status==='ok'&&d.database==='ok'},
  {path:'/api/health',validate:d=>d.status==='ok'&&d.database==='ok'},
  {path:'/api/config',validate:d=>d.app_name==='WrenchRelay'&&typeof d.stripe_enabled==='boolean'}
];
let failures=0;
for(const {path,validate} of checks){
  const started=Date.now();
  try{
    const r=await fetch(new URL(path,origin),{redirect:'manual',headers:{accept:'application/json'},signal:AbortSignal.timeout(10000)});
    const type=r.headers.get('content-type')||'';
    let d={};if(r.status===200&&type.includes('application/json'))d=await r.json();
    const pass=r.status===200&&type.includes('application/json')&&validate(d);
    console.log(JSON.stringify({path,status:r.status,elapsedMs:Date.now()-started,result:pass?'PASS':'FAIL'}));
    if(!pass)failures++;
  }catch(e){failures++;console.log(JSON.stringify({path,result:'FAIL',reason:e.name==='TimeoutError'?'timeout':'network, TLS, or invalid JSON'}))}
}
console.log(failures?'BLOCKED: API readiness failed':'PASS: API read-only checks; signup, checkout and fulfillment remain unverified');
process.exitCode=failures?1:0;
