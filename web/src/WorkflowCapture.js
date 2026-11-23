import React, { useEffect, useRef, useState } from "react";
import { WORKFLOW_FIELDS, buildWorkflowDraft, cleanWorkflowSteps, missingWorkflowFields, nextWorkflowPrompt } from "./workflowCapture.mjs";

/**
 * Technician-controlled, browser-assisted workflow recorder.
 *
 * Captures ONLY text the technician submits or chooses to dictate after clicking
 * the microphone. This is not a screen recorder, a continuous microphone, or
 * an OpenAI Realtime voice connection. Nothing is published or sent to CMMS.
 */
export default function WorkflowCapture({ mode, asset, language, onUseDraft }) {
  const [capturing, setCapturing] = useState(false);
  const [entries, setEntries] = useState([]);
  const [kind, setKind] = useState("symptom");
  const [text, setText] = useState("");
  const [source, setSource] = useState("typed");
  const [listening, setListening] = useState(false);
  const [readQuestions, setReadQuestions] = useState(true);
  const [reviewed, setReviewed] = useState(false);
  const [status, setStatus] = useState("");
  const recognition = useRef(null);
  const serial = useRef(0);
  const spanish = language === "Spanish";
  const missing = missingWorkflowFields(entries);
  const nextQuestion = nextWorkflowPrompt(entries, language);
  const draft = buildWorkflowDraft({ steps: entries, mode, asset, language });

  useEffect(() => () => {
    try { recognition.current?.abort(); } catch (_) { /* no microphone session */ }
    try { window.speechSynthesis?.cancel(); } catch (_) { /* no speaker */ }
  }, []);

  const say = (message) => {
    if (!readQuestions || !message || !("speechSynthesis" in window)) return;
    try {
      window.speechSynthesis.cancel();
      const speech = new SpeechSynthesisUtterance(message);
      speech.lang = spanish ? "es-US" : "en-US";
      speech.rate = 1;
      window.speechSynthesis.speak(speech);
    } catch (_) {
      setStatus(spanish ? "El navegador no puede leer la pregunta." : "Spoken prompts are unavailable in this browser.");
    }
  };

  const begin = () => {
    setCapturing(true);
    setStatus(spanish ? "Captura iniciada. Use el micrófono cuando quiera dictar." : "Capture started. Tap the microphone only when you want to dictate.");
    say(nextQuestion);
  };

  const stop = () => {
    try { recognition.current?.abort(); } catch (_) { /* ignore */ }
    try { window.speechSynthesis?.cancel(); } catch (_) { /* ignore */ }
    recognition.current = null;
    setListening(false);
    setCapturing(false);
    setStatus(spanish ? "Captura detenida. Revise o edite los pasos." : "Capture stopped. Review or edit the recorded steps.");
  };

  const listen = () => {
    if (!capturing || listening) return;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setStatus(spanish ? "El micrófono de voz no está disponible. Puede escribir el paso." : "Speech recognition is unavailable in this browser. You can type every step instead.");
      return;
    }
    try {
      window.speechSynthesis?.cancel();
      const session = new SpeechRecognition();
      session.lang = spanish ? "es-US" : "en-US";
      session.continuous = false;
      session.interimResults = false;
      session.maxAlternatives = 1;
      session.onstart = () => setListening(true);
      session.onresult = (event) => {
        const heard = Array.from(event.results).map((item) => item[0]?.transcript || "").join(" ").trim();
        if (heard) {
          setText((previous) => [previous.trim(), heard].filter(Boolean).join(" "));
          setSource("voice");
          setStatus(spanish ? "Revise la transcripción antes de añadirla." : "Review the transcript before adding it as a step.");
        }
      };
      session.onerror = (event) => {
        setStatus(event.error === "not-allowed"
          ? (spanish ? "Permiso de micrófono denegado; escriba el paso." : "Microphone permission denied. Type the step instead.")
          : (spanish ? "No se pudo reconocer la voz. Escriba el paso o vuelva a intentar." : "Voice recognition stopped. Type the step or try again."));
      };
      session.onend = () => { setListening(false); recognition.current = null; };
      recognition.current = session;
      session.start();
    } catch (_) {
      setListening(false);
      setStatus(spanish ? "No se pudo iniciar el micrófono." : "Could not start voice input.");
    }
  };

  const addStep = () => {
    if (!capturing || !text.trim()) return;
    const next = { id: String(++serial.current), kind, text: text.trim().slice(0, 1600), source };
    const updated = [...entries, next].slice(0, 60);
    setEntries(updated);
    setKind(missingWorkflowFields(updated)[0]?.id || kind);
    setText("");
    setSource("typed");
    setReviewed(false);
    setStatus(spanish ? "Paso guardado solo en esta sesión del navegador." : "Step added to this browser session only.");
    say(nextWorkflowPrompt(updated, language));
  };

  const editStep = (id, changes) => {
    setEntries((previous) => previous.map((entry) => entry.id === id ? { ...entry, ...changes } : entry));
    setReviewed(false);
  };

  const removeStep = (id) => {
    setEntries((previous) => previous.filter((entry) => entry.id !== id));
    setReviewed(false);
  };

  const exportDraft = () => {
    if (!entries.length) return;
    const blob = new Blob([draft], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const element = document.createElement("a");
    element.href = url;
    element.download = `wrenchrelay-${mode}-workflow-draft.txt`;
    element.click();
    URL.revokeObjectURL(url);
  };

  const apply = () => {
    if (!reviewed || !cleanWorkflowSteps(entries).length) return;
    onUseDraft(draft);
    setStatus(spanish ? "Se envió el borrador al editor. Aún requiere revisión y aprobación." : "Draft sent to the work-order editor. This is not an approved repair or SOP.");
  };

  return (
    <section className="workflowCapture" aria-label={spanish ? "Captura de procedimiento" : "Repair Workflow Capture"} data-testid="workflow-capture">
      <header className="workflowHeader">
        <div>
          <span className="eyebrow">REPAIR WORKFLOW CAPTURE</span>
          <h2>{spanish ? "Explique el trabajo mientras lo realiza" : "Talk through the work. Keep the evidence."}</h2>
          <p>{spanish
            ? "Capture pasos de mantenimiento por voz o texto, revíselos y conviértalos en un borrador editable."
            : "Dictate or type what you observed, tested, changed, and verified. WrenchRelay builds a reviewable step-by-step draft."}</p>
        </div>
        <div className="workflowCaptureControls">
          {!capturing
            ? <button className="primary" type="button" onClick={begin}>{entries.length ? (spanish ? "Reanudar captura" : "Resume capture") : (spanish ? "Iniciar captura" : "Start capture")}</button>
            : <button className="stopCapture" type="button" onClick={stop}>{spanish ? "Detener captura" : "Stop capture"}</button>}
        </div>
      </header>

      <p className="workflowDisclosure">{spanish
        ? "Sin grabación de pantalla, micrófono continuo ni publicación automática. El dictado puede usar el servicio de voz del navegador. No introduzca secretos ni datos sin autorización."
        : "No screen recording, background microphone, or automatic publication. Speech recognition may use your browser's speech service. Do not dictate passwords or unauthorized customer or plant data."}</p>

      <div className="workflowQuestion" aria-live="polite">
        <strong>{spanish ? "Siguiente pregunta" : "Relay's next question"}</strong>
        <p>{nextQuestion}</p>
        <label>
          <input type="checkbox" checked={readQuestions} onChange={(event) => setReadQuestions(event.target.checked)} />
          {spanish ? "Leer preguntas en voz alta" : "Read questions aloud"}
        </label>
        <button type="button" className="workflowSecondary" onClick={() => say(nextQuestion)}>{spanish ? "Escuchar pregunta" : "Hear question"}</button>
      </div>

      <div className="workflowEntry">
        <label htmlFor="workflow-kind">{spanish ? "Tipo de evidencia" : "What are you recording?"}</label>
        <select id="workflow-kind" value={kind} disabled={!capturing} onChange={(event) => setKind(event.target.value)}>
          {WORKFLOW_FIELDS.map((field) => <option key={field.id} value={field.id}>{spanish ? field.es : field.en}</option>)}
        </select>
        <label htmlFor="workflow-entry">{spanish ? "Sus palabras — edite antes de guardar" : "Your words — edit before saving"}</label>
        <textarea id="workflow-entry" value={text} disabled={!capturing} onChange={(event) => { setText(event.target.value); setSource("typed"); }} rows={4} maxLength={1600}
          placeholder={spanish ? "Indique solo lo que sabe o hizo; no suponga resultados." : "Describe exactly what you know or did. Unknowns can stay unknown."} />
        <div className="workflowActions">
          <button className={listening ? "stopCapture" : "workflowSecondary"} type="button" disabled={!capturing || listening} onClick={listen} aria-pressed={listening}>
            {listening ? (spanish ? "Escuchando…" : "Listening…") : (spanish ? "Dictar un paso" : "Dictate one step")}
          </button>
          <button className="primary" type="button" disabled={!capturing || !text.trim()} onClick={addStep}>{spanish ? "Añadir paso" : "Add recorded step"}</button>
        </div>
        {status && <p className="workflowStatus" role="status">{status}</p>}
      </div>

      <section className="workflowSteps">
        <h3>{spanish ? "Pasos capturados" : "Captured steps"} <small>({entries.length})</small></h3>
        {!entries.length && <p className="muted">{spanish ? "Todavía no hay pasos. Empiece con el síntoma reportado." : "No steps yet. Start with the reported problem."}</p>}
        {entries.map((entry, index) => (
          <div className="workflowStep" key={entry.id}>
            <span className="workflowStepNumber">{index + 1}</span>
            <div className="workflowStepBody">
              <select value={entry.kind} aria-label={spanish ? "Categoría" : "Evidence category"}
                onChange={(event) => editStep(entry.id, { kind: event.target.value })}>
                {WORKFLOW_FIELDS.map((field) => <option key={field.id} value={field.id}>{spanish ? field.es : field.en}</option>)}
              </select>
              <textarea rows={2} maxLength={1600} value={entry.text} aria-label={spanish ? "Editar paso" : "Edit captured step"}
                onChange={(event) => editStep(entry.id, { text: event.target.value })} />
              <small>{entry.source === "voice" ? (spanish ? "Dictado — revisar transcripción" : "Dictated — check transcript") : (spanish ? "Introducido por técnico" : "Technician-entered")}</small>
            </div>
            <button className="workflowRemove" type="button" onClick={() => removeStep(entry.id)} aria-label={spanish ? "Eliminar paso" : "Remove step"}>×</button>
          </div>
        ))}
      </section>

      <section className="workflowReview">
        <h3>{spanish ? "Revisión del borrador" : "Review the draft"}</h3>
        <p className="muted">{missing.length
          ? (spanish ? `${missing.length} campos todavía no documentados; se mostrarán como pendientes.` : `${missing.length} evidence sections still undocumented; they will be marked for follow-up.`)
          : (spanish ? "Cada categoría tiene una entrada; ninguna ha sido verificada independientemente." : "Each section has an entry; none has been independently verified.")}</p>
        <pre tabIndex={0} className="workflowDraft">{draft}</pre>
        <label className="workflowConsent">
          <input type="checkbox" checked={reviewed} disabled={!entries.length} onChange={(event) => setReviewed(event.target.checked)} />
          {spanish
            ? "He revisado la transcripción y sé que esto es un borrador, no un procedimiento aprobado."
            : "I reviewed this transcript and understand it is a draft, not an approved procedure or confirmed fix."}
        </label>
        <div className="workflowActions">
          <button className="workflowSecondary" type="button" disabled={!entries.length} onClick={exportDraft}>{spanish ? "Exportar texto" : "Export text draft"}</button>
          <button className="primary" type="button" disabled={!reviewed || !entries.length} onClick={apply}>
            {spanish ? "Enviar al editor de órdenes" : "Use in work-order editor"}
          </button>
        </div>
        <p className="workflowDisclosure">{spanish
          ? "La revisión no sustituye LOTO, procedimientos OEM, autorización de trabajo o aprobación de CMMS."
          : "Review does not replace LOTO, OEM procedures, work authorization, independent verification, or CMMS approval."}</p>
      </section>
    </section>
  );
}
