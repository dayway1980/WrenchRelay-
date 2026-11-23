import React, { useCallback, useEffect, useRef, useState } from "react";

/**
 * Opt-in WebRTC Realtime voice preview.
 * No permanent API keys in this browser. The signed-in backend mints a short-
 * lived client secret only after explicit user action and per-user cost gates.
 * The user must review every transcript before using it as maintenance evidence.
 */
export default function RealtimeVoice({ mode = "industrial", language = "English", onTranscript }) {
  const [state, setState] = useState("idle");
  const [status, setStatus] = useState("");
  const [muted, setMuted] = useState(false);
  const [captured, setCaptured] = useState([]);
  const [lastAssistant, setLastAssistant] = useState("");
  const [consent, setConsent] = useState(false);
  const peer = useRef(null);
  const localStream = useRef(null);
  const audio = useRef(null);
  const timeout = useRef(null);
  const active = useRef(false);
  const started = useRef(false);
  const transcriptCounter = useRef(0);

  const stop = useCallback(() => {
    active.current = false;
    started.current = false;
    if (timeout.current) clearTimeout(timeout.current);
    timeout.current = null;
    try { peer.current?.close(); } catch (_) { /* ignore cleanup */ }
    peer.current = null;
    try { localStream.current?.getTracks().forEach((track) => track.stop()); } catch (_) { /* ignore */ }
    localStream.current = null;
    if (audio.current) {
      try { audio.current.pause(); audio.current.srcObject = null; } catch (_) { /* ignore */ }
    }
    setMuted(false);
    setState("idle");
  }, []);

  useEffect(() => () => stop(), [stop]);

  const start = async () => {
    if (active.current || !consent) return;
    if (!navigator.mediaDevices?.getUserMedia || !window.RTCPeerConnection) {
      setStatus("Realtime audio is unavailable in this browser. Use the one-step dictation or type notes instead.");
      return;
    }
    active.current = true;
    setState("connecting");
    setStatus("Requesting microphone permission…");
    let stream;
    let connection;
    try {
      // Ask permission before minting any billable Realtime credential.
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      localStream.current = stream;
      if (!active.current) { stream.getTracks().forEach((track) => track.stop()); return; }

      const keyRequest = await fetch("/api/realtime/client-secret", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode, language }),
        cache: "no-store",
      });
      if (!keyRequest.ok) {
        let message = "Realtime voice is not available. Use the regular voice capture instead.";
        if (keyRequest.status === 401) message = "Your login expired. Sign in again to use realtime voice.";
        if (keyRequest.status === 429) message = "Today's voice preview allowance is reached.";
        if (keyRequest.status === 403) message = "This website is not approved for realtime voice.";
        throw new Error(message);
      }
      const keyData = await keyRequest.json();
      if (typeof keyData.value !== "string" || !keyData.value.startsWith("ek_")) throw new Error("Invalid temporary voice credential.");
      if (!active.current) return;

      connection = new RTCPeerConnection();
      peer.current = connection;
      connection.ontrack = (event) => {
        if (!audio.current) return;
        audio.current.srcObject = event.streams[0];
        audio.current.play().catch(() => setStatus("Tap the speaker control or adjust browser audio permissions."));
      };
      connection.onconnectionstatechange = () => {
        if (connection.connectionState === "failed" || connection.connectionState === "closed") {
          if (active.current) { stop(); setStatus("Voice disconnected. Your text draft is unchanged."); }
        }
      };

      stream.getTracks().forEach((track) => connection.addTrack(track, stream));
      const events = connection.createDataChannel("oai-events");
      events.onmessage = (message) => {
        let event;
        try { event = JSON.parse(message.data); } catch (_) { return; }
        if (event.type === "conversation.item.input_audio_transcription.completed" && typeof event.transcript === "string") {
          const excerpt = event.transcript.trim().slice(0, 1600);
          if (excerpt) {
            setCaptured((previous) => [...previous, { id: ++transcriptCounter.current, text: excerpt }].slice(-24));
            setStatus("Review dictated statements below before transferring them to an evidence step.");
          }
        }
        if (event.type === "response.output_audio_transcript.delta" && typeof event.delta === "string") {
          setLastAssistant((previous) => (previous + event.delta).slice(-1600));
        }
        if (event.type === "response.created") setLastAssistant("");
        if (event.type === "error") setStatus("The voice provider reported a session error. Stop and try later.");
      };

      const offer = await connection.createOffer();
      await connection.setLocalDescription(offer);
      const sdpResponse = await fetch("https://api.openai.com/v1/realtime/calls", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${keyData.value}`,
          "Content-Type": "application/sdp",
        },
        body: offer.sdp,
      });
      if (!sdpResponse.ok) throw new Error("Voice provider could not establish the audio connection.");
      const answer = await sdpResponse.text();
      if (!active.current) return;
      await connection.setRemoteDescription({ type: "answer", sdp: answer });
      if (!active.current) return;

      setState("connected");
      setStatus("Realtime voice is connected. Stop at any time; the preview ends after three minutes.");
      timeout.current = setTimeout(() => {
        stop();
        setStatus("Three-minute preview ended. Your captured text remains available for review.");
      }, Math.min(180, Number(keyData.max_preview_seconds) || 180) * 1000);
      started.current = true;
    } catch (error) {
      stop();
      setStatus(error?.message || "Voice connection failed. Use typed notes instead.");
    }
  };

  const toggleMute = () => {
    const next = !muted;
    localStream.current?.getAudioTracks().forEach((track) => { track.enabled = !next; });
    setMuted(next);
    setStatus(next ? "Microphone muted. No new live microphone audio is being sent." : "Microphone resumed.");
  };

  return (
    <section className="realtimeVoice" aria-label="Realtime conversational voice preview">
      <h3>Conversational voice preview</h3>
      <p className="muted">Natural two-way questions, interruptions and speaker replies. This is optional and separate from the step-by-step dictation above.</p>
      <p className="workflowDisclosure">Audio is sent to the voice AI provider while connected. WrenchRelay does not save raw audio here. Automatic transcripts may be inaccurate. No work orders, fixes or safety sign-offs are created automatically.</p>
      <audio ref={audio} playsInline autoPlay aria-label="WrenchRelay voice output" />
      <label className="workflowConsent">
        <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} disabled={state !== "idle"} />
        I agree to send my microphone audio to the AI provider for this conversation; I will not dictate unauthorised personal or confidential data.
      </label>
      <div className="workflowActions">
        {state === "idle"
          ? <button className="primary" type="button" disabled={!consent} onClick={start}>Start conversational voice</button>
          : <button className="stopCapture" type="button" onClick={() => { stop(); setStatus("Voice ended. You can still review your transcript."); }}>End voice session</button>}
        {state === "connected" && <button className="workflowSecondary" type="button" onClick={toggleMute}>{muted ? "Unmute microphone" : "Mute microphone"}</button>}
      </div>
      {status && <p role="status" className="workflowStatus">{status}</p>}
      {lastAssistant && <p className="workflowAssistant"><strong>Voice assistant:</strong> {lastAssistant}</p>}
      {captured.length > 0 && (
        <div className="workflowCapturedVoice">
          <h4>Transcribed technician statements — review before adding</h4>
          {captured.map((item) => (
            <div className="workflowTranscriptLine" key={item.id}>
              <p>{item.text}</p>
              <button type="button" className="workflowSecondary" onClick={() => onTranscript(item.text)}>
                Insert into editable notes
              </button>
            </div>
          ))}
          <button type="button" className="workflowSecondary" onClick={() => setCaptured([])}>Clear displayed transcripts</button>
        </div>
      )}
    </section>
  );
}
