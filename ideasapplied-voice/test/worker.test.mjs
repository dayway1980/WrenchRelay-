import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";

const env = {
  VOICE_ALLOWED_ORIGINS: "https://app.wrenchrelay.com",
  VOICE_AUTH_URL: "https://example.org/api/me",
  AI: { run: async () => ({ text: "servo motor vibration" }) }
};
const base = "https://voice.example/api/voice/transcribe";
const request = (method, origin, headers = {}, body) => new Request(base, {
  method, headers: { ...(origin ? { Origin: origin } : {}), ...headers }, body
});
test("health does not claim customer readiness", async () => {
  const r = await worker.fetch(new Request("https://voice.example/health"), env);
  assert.equal(r.status, 200);
  assert.equal((await r.json()).customer_ready, false);
});
test("allowed preflight includes browser headers", async () => {
  const r = await worker.fetch(request("OPTIONS", "https://app.wrenchrelay.com"), env);
  assert.equal(r.status, 204);
  assert.equal(r.headers.get("Access-Control-Allow-Origin"), "https://app.wrenchrelay.com");
  assert.match(r.headers.get("Access-Control-Allow-Headers"), /Authorization/);
});
test("unknown origins are denied", async () => {
  const r = await worker.fetch(request("OPTIONS", "https://attacker.example"), env);
  assert.equal(r.status, 403);
});
test("unauthenticated transcription fails closed", async () => {
  const r = await worker.fetch(request("POST", "https://app.wrenchrelay.com", {
    "Content-Type": "audio/wav"
  }, new Uint8Array([1,2,3])), env);
  assert.equal(r.status, 401);
  assert.equal(r.headers.get("Access-Control-Allow-Origin"), "https://app.wrenchrelay.com");
});
test("uncommissioned token endpoint cannot mint credentials", async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({ id: "test-user" }), {
    headers: { "Content-Type": "application/json" }
  });
  try {
    const r = await worker.fetch(new Request("https://voice.example/api/voice/token", {
      method: "POST", headers: { Authorization: "Bearer test-token" }
    }), env);
    assert.equal(r.status, 503);
  } finally { globalThis.fetch = original; }
});
test("auth identity without user identifier is rejected", async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({ status: "ok" }), {
    headers: { "Content-Type": "application/json" }
  });
  try {
    const r = await worker.fetch(request("POST", null, {
      Authorization: "Bearer test-token", "Content-Type": "audio/wav"
    }, new Uint8Array([1,2,3])), env);
    assert.equal(r.status, 401);
  } finally { globalThis.fetch = original; }
});
