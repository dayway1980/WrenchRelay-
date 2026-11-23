/**
 * WrenchRelay voice-first maintenance workflow drafts.
 * Original, deliberately local-first capture logic — no silent screen capture,
 * background recording, auto-publication, or claim of a verified fix.
 */
export const WORKFLOW_FIELDS = Object.freeze([
  {
    id: "symptom",
    en: "Problem / reported symptom",
    es: "Problema / síntoma reportado",
    questionEn: "What problem did the machine or vehicle have?",
    questionEs: "¿Qué problema tenía la máquina o el vehículo?"
  },
  {
    id: "observation",
    en: "Observed condition",
    es: "Condición observada",
    questionEn: "What did you directly observe or measure?",
    questionEs: "¿Qué observó o midió directamente?"
  },
  {
    id: "test",
    en: "Diagnostics and checks",
    es: "Diagnóstico y comprobaciones",
    questionEn: "What checks or tests did you perform, and what did each show?",
    questionEs: "¿Qué comprobaciones o pruebas realizó y qué indicaron?"
  },
  {
    id: "safety",
    en: "Safety / energy controls",
    es: "Seguridad / control de energía",
    questionEn: "What safety or isolation steps were documented? Say if none were recorded.",
    questionEs: "¿Qué medidas de seguridad o aislamiento documentó? Indique si no se registraron."
  },
  {
    id: "action",
    en: "Actions and parts",
    es: "Acciones y piezas",
    questionEn: "What action was taken, and which parts were actually used?",
    questionEs: "¿Qué acción se tomó y qué piezas se utilizaron realmente?"
  },
  {
    id: "verification",
    en: "Verification / outcome",
    es: "Verificación / resultado",
    questionEn: "How was the result verified? If untested, please say that.",
    questionEs: "¿Cómo se verificó el resultado? Si no se probó, indíquelo."
  }
]);

export function cleanWorkflowSteps(steps) {
  if (!Array.isArray(steps)) return [];
  return steps.slice(0, 60).filter((step) => step && typeof step.text === "string" && step.text.trim())
    .map((step) => ({
      id: String(step.id || ""),
      kind: WORKFLOW_FIELDS.some((field) => field.id === step.kind) ? step.kind : "observation",
      text: step.text.trim().slice(0, 1600),
      source: step.source === "voice" ? "voice" : "typed"
    }));
}

export function missingWorkflowFields(steps) {
  const recorded = new Set(cleanWorkflowSteps(steps).map((step) => step.kind));
  return WORKFLOW_FIELDS.filter((field) => !recorded.has(field.id));
}

export function nextWorkflowPrompt(steps, language = "English") {
  const first = missingWorkflowFields(steps)[0];
  if (!first) return language === "Spanish"
    ? "Ya hay una nota en cada categoría. Revise los hechos y confirme lo que sigue sin verificarse."
    : "Every section has an entry. Review the facts and identify anything still unverified.";
  return language === "Spanish" ? first.questionEs : first.questionEn;
}

export function buildWorkflowDraft({ steps, mode = "industrial", asset = "", language = "English" } = {}) {
  const records = cleanWorkflowSteps(steps);
  const spanish = language === "Spanish";
  const heading = spanish ? "BORRADOR DE CAPTURA DE TRABAJO" : "WORKFLOW CAPTURE DRAFT";
  const unset = spanish ? "No documentado; requiere seguimiento" : "Not documented; follow-up required";
  const lines = [
    heading,
    spanish ? "No aprobado. Solo para revisión de un técnico cualificado." : "Not approved. Qualified technician review required.",
    `${spanish ? "Contexto" : "Context"}: ${mode === "automotive" ? "Automotive" : "Industrial"}`,
    `${spanish ? "Equipo / vehículo" : "Asset / vehicle"}: ${String(asset).trim().slice(0, 200) || unset}`,
    ""
  ];
  WORKFLOW_FIELDS.forEach((field) => {
    lines.push(spanish ? field.es : field.en);
    const matches = records.filter((record) => record.kind === field.id);
    if (!matches.length) lines.push(`- ${unset}`);
    else matches.forEach((record, index) => lines.push(`${index + 1}. ${record.text}`));
    lines.push("");
  });
  lines.push(spanish ? "PREGUNTAS PENDIENTES" : "FOLLOW-UP QUESTIONS");
  const missing = missingWorkflowFields(records);
  if (missing.length) missing.forEach((field) => lines.push(`- ${spanish ? field.questionEs : field.questionEn}`));
  else lines.push(spanish ? "- Confirmar que cada entrada sea exacta; no se ha comprobado independientemente." : "- Confirm each entry's accuracy; nothing has been independently verified.");
  lines.push("");
  lines.push(spanish
    ? "ADVERTENCIA: Esta nota no autoriza reparaciones, maniobras eléctricas, anulación de protecciones, desbloqueo/etiquetado ni cambios en CMMS. Requiere revisión humana."
    : "CAUTION: This draft does not authorize repair, electrical work, bypassing safeguards, LOTO clearance, or CMMS changes. Human review is required.");
  return lines.join("\n");
}
