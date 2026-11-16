const MODEL = "@cf/openai/whisper-large-v3-turbo";
const MAX_AUDIO_BYTES = 8 * 1024 * 1024;
const CONTEXT = "LOTO, OBD-II, torque, schematic, VIN, PLC, CMMS, servo motor, work order";

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" }
  });
}

async function authorize(request, env) {
  const authorization = request.headers.get("authorization");
  // Bearer token is forwarded to the trusted application identity endpoint,
  // never decoded or accepted locally without verification.
  if (!authorization?.startsWith("Bearer ")) return false;
  const url = new URL(env.VOICE_AUTH_URL);
  if (url.protocol !== "https:") return false;
  const response = await fetch(url.toString(), {
    headers: { authorization, accept: "application/json" },
    redirect: "error"
  });
  return response.ok;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/health") return json({ service: "ideasapplied-voice", status: "configured" });
    if (url.pathname !== "/api/voice/transcribe" && url.pathname !== "/api/voice/token") return json({ error: "not_found" }, 404);
    if (request.method !== "POST") return json({ error: "method_not_allowed" }, 405);
    const origin = request.headers.get("origin");
    const allowed = (env.VOICE_ALLOWED_ORIGINS || "").split(",").map(x => x.trim()).filter(Boolean);
    if (origin && !allowed.includes(origin)) return json({ error: "origin_denied" }, 403);
    if (!await authorize(request, env)) return json({ error: "unauthorized" }, 401);
    if (url.pathname === "/api/voice/token") {
      // No provider token is minted until per-app entitlements and provider
      // credential issuance are implemented and verified.
      return json({ error: "live_voice_not_commissioned" }, 503);
    }
    const type = request.headers.get("content-type") || "";
    if (!type.startsWith("audio/") && !type.startsWith("application/octet-stream"))
      return json({ error: "audio_required" }, 415);
    const length = Number(request.headers.get("content-length") || "0");
    if (length > MAX_AUDIO_BYTES) return json({ error: "audio_too_large" }, 413);
    const audio = await request.arrayBuffer();
    if (!audio.byteLength || audio.byteLength > MAX_AUDIO_BYTES) return json({ error: "invalid_audio_size" }, 413);
    const bytes = new Uint8Array(audio);
    let binary = "";
    for (let i = 0; i < bytes.length; i += 32768) {
      binary += String.fromCharCode(...bytes.subarray(i, i + 32768));
    }
    try {
      const result = await env.AI.run(MODEL, {
        audio: btoa(binary), task: "transcribe", vad_filter: true,
        initial_prompt: CONTEXT
      });
      return json({ text: result.text || "", engine: "cloudflare-whisper" });
    } catch {
      return json({ error: "transcription_unavailable" }, 502);
    }
  }
};
