#!/usr/bin/env node
/**
 * Read-only public access smoke checks.
 * Run: WR_BASE_URL=https://your-approved-customer-domain.example node scripts/customer-access-smoke.mjs
 * Does not register accounts, trigger checkout, send calls, or change production data.
 */
import assert from 'node:assert/strict';

const raw = process.env.WR_BASE_URL;
if (!raw) {
  console.error('Set WR_BASE_URL to the verified public customer-facing HTTPS origin.');
  process.exit(2);
}
let base;
try { base = new URL(raw); } catch { console.error('Invalid WR_BASE_URL'); process.exit(2); }
if (base.protocol !== 'https:' || base.username || base.password || base.pathname !== '/' || base.search || base.hash) {
  console.error('WR_BASE_URL must be an HTTPS origin with no credentials, path, query, or fragment.');
  process.exit(2);
}
const timeoutMs = 10000;
const paths = ['/', '/privacy', '/terms'];
let failures = 0;
for (const path of paths) {
  const started = Date.now();
  try {
    const response = await fetch(new URL(path, base), {
      method: 'GET',
      redirect: 'manual',
      headers: { accept: 'text/html' },
      signal: AbortSignal.timeout(timeoutMs),
    });
    const type = response.headers.get('content-type') || '';
    const location = response.headers.get('location') || '';
    const status = response.status;
    const ok = status === 200 && type.toLowerCase().includes('text/html');
    console.log(JSON.stringify({ path, status, contentType: type, redirectLocation: location || undefined, elapsedMs: Date.now() - started, result: ok ? 'PASS' : 'FAIL' }));
    if (!ok) failures++;
  } catch (error) {
    failures++;
    console.log(JSON.stringify({ path, result: 'FAIL', reason: error.name === 'TimeoutError' ? 'timeout' : 'network or TLS failure' }));
  }
}
if (failures) {
  console.error(`Customer access smoke: ${failures}/${paths.length} checks failed. Do not mark release ready.`);
  process.exit(1);
}
console.log('Public HTML routes passed. Authentication, persistence, payments, and service delivery remain UNVERIFIED.');
