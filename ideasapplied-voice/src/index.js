const MODEL = "@cf/openai/whisper-large-v3-turbo";
const MAX_AUDIO_BYTES = 8 * 1024 * 1024;
const CONTEXT = "LOTO, OBD-II, torque, schematic, VIN, PLC, CMMS, servo motor, work order";
const ALLOWED_METHODS = "POST, OPTIONS";
const ALLOWED_HEADERS = "Authorization, Content-Type";

function response(body, status = 200, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...headers }
  });
}

function corsHeaders(origin, env) {
  const allowed = (env.VOICE_ALLOWED_ORIGINS || "").split(",").map(x => x.trim()).filter(Boolean);
  return origin && allowed.includes(origin)
    ? { "Access-Control-Allow-Origin": origin, "Access-Control-Allow-Methods": ALLOWED_METHODS,
        "Access-Control-Allow-Headers": ALLOWED_HEADERS, "Vary": "Origin" }
    : null;
}

async function authorize(request, env) {
  const authorization = request.headers.get("authorization");
  if (!authorization || !/^Bearer [^\s]+$/.test(authorization) || !env.VOICE_AUTH_URL) return false;
  let url;
  try { url = new URL(env.VOICE_AUTH_URL); } catch { return false; }
  if (url.protocol !== "https:" || url.username || url.password) return false;
  try {
    const result = await fetch(url.toString(), {
      headers: { authorization, accept: "application/json" },
      redirect: "error",
      signal: AbortSignal.timeout(5000)
    });
    if (!result.ok) return false;
    const identity = await result.json();
    return !!identity && typeof identity === "object" &&
      (typeof identity.id === "string" || typeof identity.user_id === "string" ||
       (identity.user && typeof identity.user.id === "string"));
  } catch { return false; }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/health" && request.method === "GET")
      return response({ service: "ideasapplied-voice", status: "configured", customer_ready: false });
    if (url.pathname !== "/api/voice/transcribe" && url.pathname !== "/api/voice/token")
      return response({ error: "not_found" }, 404);
    const origin = request.headers.get("origin");
    const cors = corsHeaders(origin, env);
    if (origin && !cors) return response({ error: "origin_denied" }, 403);
    if (request.method === "OPTIONS")
      return new Response(null, { status: 204, headers: { ...cors, "Cache-Control": "no-store" } });
    if (request.method !== "POST") return response({ error: "method_not_allowed" }, 405, cors || {});
    if (!await authorize(request, env)) return response({ error: "unauthorized" }, 401, cors || {});
    if (url.pathname === "/api/voice/token")
      return response({ error: "live_voice_not_commissioned" }, 503, cors || {});
    const type = (request.headers.get("content-type") || "").split(";")[0].toLowerCase();
    if (!["audio/wav", "audio/wave", "audio/x-wav", "audio/mpeg", "audio/mp3", "audio/ogg", "audio/webm", "application/octet-stream"].includes(type))
      return response({ error: "unsupported_audio_type" }, 415, cors || {});
    const length = Number(request.headers.get("content-length") || "0");
    if (!Number.isFinite(length) || length > MAX_AUDIO_BYTES)
      return response({ error: "audio_too_large" }, 413, cors || {});
    const audio = await request.arrayBuffer();
    if (!audio.byteLength || audio.byteLength > MAX_AUDIO_BYTES)
      return response({ error: "invalid_audio_size" }, 413, cors || {});
    const bytes = new Uint8Array(audio);
    let binary = "";
    for (let i = 0; i < bytes.length; i += 32768)
      binary += String.fromCharCode(...bytes.subarray(i, i + 32768));
    try {
      const result = await env.AI.run(MODEL, {
        audio: btoa(binary), task: "transcribe", vad_filter: true, initial_prompt: CONTEXT
      });
      return response({ text: result.text || "", engine: "cloudflare-whisper" }, 200, cors || {});
    } catch {
      return response({ error: "transcription_unavailable" }, 502, cors || {});
    }
  }
};
