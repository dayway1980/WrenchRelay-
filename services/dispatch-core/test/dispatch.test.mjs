import { test } from 'node:test';
import assert from 'node:assert/strict';
import { matchDispatch, convertMinor, normalizeGoogleMatrix, localTime } from '../dist/dispatch.js';
import { googleMatrix } from '../dist/google-matrix.js';
const now=Date.parse('2026-10-26T12:00:00Z');
function fixture(){return {tenantId:'a',now,maxSnapshotAgeMs:60000,maxRouteHorizonMs:3600000,
 job:{id:'job',country:'US',timeZone:'America/Chicago',acceptedLanguages:['en-US'],requiredSkills:{plc:0.8},
  parts:[{sku:'p',quantity:1}],windowStart:now,windowEnd:now+3600000,serviceSeconds:600,settlementCurrency:'USD'},
 technicians:[{id:'t1',tenantId:'a',version:1,position:{lat:40,lng:-91},observedAt:now,availableAt:now,
  shiftEnd:now+7200000,authorizedCountries:['US'],languages:['en-US'],skills:{plc:0.9},
  remainingKg:10,remainingLiters:10,onboard:{p:1},dispatchFee:{minor:'1000',currency:'USD'}}],
 warehouses:[],routes:[{from:'t1',to:'job',seconds:100,meters:1000,observedAt:now,
  transitCountries:['US'],approvedBorderDelaySeconds:0}],fx:[]};}
function withWarehouse(){const f=fixture();f.technicians[0].onboard={};
 f.warehouses=[{id:'w',tenantId:'a',version:4,country:'US',observedAt:now,readyAt:now,stock:{p:1},
  skuInfo:{p:{kg:5,liters:1,unitPrice:{minor:'100',currency:'USD'}}},pickupSeconds:30}];
 f.routes=[{...f.routes[0],to:'w'},{...f.routes[0],from:'w'}];return f;}
test('earliest completion wins before lower fee',()=>{const f=fixture();
 f.technicians.push({...f.technicians[0],id:'t2',dispatchFee:{minor:'90000',currency:'USD'}});
 f.routes.push({...f.routes[0],from:'t2',seconds:50});assert.equal(matchDispatch(f).best?.technicianId,'t2');});
test('equal finish uses cost, then meters, then stable IDs regardless of input order',()=>{
 const f=fixture();f.technicians.push({...f.technicians[0],id:'t2',dispatchFee:{minor:'999',currency:'USD'}});
 f.routes.push({...f.routes[0],from:'t2'});assert.equal(matchDispatch(f).best?.technicianId,'t2');
 f.technicians[1].dispatchFee.minor='1000';f.routes[1].meters=500;
 assert.equal(matchDispatch(f).best?.technicianId,'t2');f.routes[1].meters=1000;
 f.technicians.reverse();assert.equal(matchDispatch(f).best?.technicianId,'t1');});
test('tenant, certified skill, language and transit permissions are hard constraints',()=>{
 for(const mutate of [f=>f.technicians[0].tenantId='other',f=>f.technicians[0].skills={},
  f=>f.technicians[0].languages=['es-MX'],f=>f.routes[0].transitCountries.push('CA')]){
  const f=fixture();mutate(f);assert.equal(matchDispatch(f).best,null);
 }});
test('stale, future and missing routes fail closed',()=>{
 for(const at of [now-60001,now+1]){const f=fixture();f.routes[0].observedAt=at;assert.equal(matchDispatch(f).best,null);}
 const f=fixture();f.routes=[];assert.equal(matchDispatch(f).best,null);});
test('vehicle capacity and vendor availability must both pass',()=>{
 const f=withWarehouse();assert.equal(matchDispatch(f).best?.warehouseId,'w');
 f.warehouses[0].skuInfo.p.kg=11;assert.equal(matchDispatch(f).best,null);
 f.warehouses[0].skuInfo.p.kg=5;f.warehouses[0].stock.p=0;assert.equal(matchDispatch(f).best,null);});
test('onboard parts reduce pickup and quote includes the missing kit',()=>{
 const f=withWarehouse();f.job.parts[0].quantity=2;f.technicians[0].onboard={p:1};
 const best=matchDispatch(f).best;assert.deepEqual(best?.pickup,{p:1});assert.equal(best?.costMinor,'1100');});
test('currency conversion stays integer and includes differing minor-unit ratios',()=>{
 assert.equal(convertMinor(100n,123n,100n),123n);assert.equal(convertMinor(1n,1n,3n),1n);
 assert.equal(convertMinor(10000n,67n,100n),6700n);assert.throws(()=>convertMinor(1n,1n,0n));
 const f=fixture();f.technicians[0].dispatchFee={minor:'10000',currency:'JPY'};
 assert.equal(matchDispatch(f).best,null);
 f.fx=[{from:'JPY',to:'USD',numerator:'67',denominator:'100',observedAt:now}];
 assert.equal(matchDispatch(f).best?.costMinor,'6700');f.fx[0].observedAt=now-60001;assert.equal(matchDispatch(f).best,null);});
test('job windows, shifts and traffic horizon constrain dispatch',()=>{
 const f=fixture();f.job.windowEnd=now+699999;assert.equal(matchDispatch(f).best,null);
 const g=fixture();g.technicians[0].shiftEnd=now+699999;assert.equal(matchDispatch(g).best,null);
 const h=fixture();h.technicians[0].availableAt=now+3600001;assert.equal(matchDispatch(h).best,null);});
test('invalid IANA zones reject and display handles a DST transition',()=>{
 assert.match(localTime(Date.parse('2026-11-01T07:30:00Z'),'America/Chicago'),/CST/);
 const f=fixture();f.job.timeZone='Invalid/Zone';assert.throws(()=>matchDispatch(f));});
test('duplicate stock requests, route keys and endpoint IDs reject',()=>{
 const a=fixture();a.job.parts.push({sku:'p',quantity:1});assert.throws(()=>matchDispatch(a));
 const b=fixture();b.routes.push({...b.routes[0]});assert.throws(()=>matchDispatch(b));
 const c=fixture();c.job.id='t1';assert.throws(()=>matchDispatch(c));});
test('nonfinite quantities and unrecognized top-level fields reject',()=>{
 const a=fixture();a.technicians[0].remainingKg=Infinity;assert.throws(()=>matchDispatch(a));
 const b=fixture();b.admin=true;assert.throws(()=>matchDispatch(b));});
test('language tags are canonicalized',()=>{const f=fixture();f.technicians[0].languages=['en-us'];assert.ok(matchDispatch(f).best);});
test('candidate expiry uses only its own route, inventory and FX inputs',()=>{
 const f=fixture();f.routes[0].observedAt=now-59000;
 f.routes.push({...f.routes[0],from:'unused',observedAt:now-60001});
 assert.equal(matchDispatch(f).best?.validUntil,now+1000);});
test('prototype-like SKU cannot invent onboard stock',()=>{
 const f=fixture();f.job.parts=[{sku:'constructor',quantity:1}];f.technicians[0].onboard={};
 assert.equal(matchDispatch(f).best,null);});
test('matrix error and unapproved cells never become usable routes',()=>{
 const cell={originIndex:0,destinationIndex:0,condition:'ROUTE_EXISTS',distanceMeters:10,duration:'1.2s'};
 assert.deepEqual(normalizeGoogleMatrix([cell],['t'],['j'],now,new Map()),[]);
 const map=new Map([[JSON.stringify(['t','j']),{transitCountries:['US'],approvedBorderDelaySeconds:0}]]);
 assert.equal(normalizeGoogleMatrix([cell],['t'],['j'],now,map)[0].seconds,2);
 assert.deepEqual(normalizeGoogleMatrix([{...cell,status:{code:5}}],['t'],['j'],now,map),[]);
 assert.throws(()=>normalizeGoogleMatrix([cell,cell],['t'],['j'],now,map));});
test('matrix HTTP adapter batches and binds results to approved endpoints',async()=>{
 const old=globalThis.fetch;let count=0;
 globalThis.fetch=async(url,request)=>{count++;assert.equal(url,'https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix');
  const body=JSON.parse(request.body);assert.ok(body.origins.length*body.destinations.length<=100);
  assert.equal(request.redirect,'error');
  return new Response(JSON.stringify([{originIndex:0,destinationIndex:0,condition:'ROUTE_EXISTS',distanceMeters:100,duration:'5s'}]));};
 try{const map=new Map([[JSON.stringify(['t','j']),{transitCountries:['US'],approvedBorderDelaySeconds:0}]]);
  const routes=await googleMatrix([{id:'t',lat:40,lng:-91}],[{id:'j',lat:41,lng:-91}],'test-key',map);
  assert.equal(routes[0].seconds,5);assert.equal(count,1);
 }finally{globalThis.fetch=old;}
});
test('matrix provider failures stop assignment inputs',async()=>{
 const old=globalThis.fetch;globalThis.fetch=async()=>new Response('outage',{status:503});
 try{await assert.rejects(googleMatrix([{id:'t',lat:40,lng:-91}],[{id:'j',lat:41,lng:-91}],'test-key',new Map()),/503/);}
 finally{globalThis.fetch=old;}
});
