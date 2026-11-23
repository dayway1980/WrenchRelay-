import test from "node:test";
import assert from "node:assert/strict";
import { WORKFLOW_FIELDS, cleanWorkflowSteps, missingWorkflowFields, nextWorkflowPrompt, buildWorkflowDraft } from "./workflowCapture.mjs";

test("empty capture keeps unknown evidence explicitly missing", () => {
  assert.equal(WORKFLOW_FIELDS.length, 6);
  assert.equal(missingWorkflowFields([]).length, 6);
  const draft = buildWorkflowDraft({ mode: "industrial", asset: "Press 4", steps: [] });
  assert.match(draft, /Not approved/);
  assert.match(draft, /Press 4/);
  assert.match(draft, /Not documented; follow-up required/);
  assert.doesNotMatch(draft, /confirmed fix/i);
});

test("steps stay separate by actual technician-labelled category", () => {
  const steps = [
    { id: "1", kind: "symptom", text: "  Drive would not start  ", source: "voice" },
    { id: "2", kind: "test", text: "Meter showed 24 VDC", source: "typed" },
    { id: "3", kind: "verification", text: "Not tested after adjustment", source: "voice" }
  ];
  const cleaned = cleanWorkflowSteps(steps);
  assert.equal(cleaned[0].text, "Drive would not start");
  assert.equal(cleaned[2].source, "voice");
  const draft = buildWorkflowDraft({ mode: "industrial", steps });
  assert.match(draft, /Meter showed 24 VDC/);
  assert.match(draft, /Not tested after adjustment/);
  assert.equal(missingWorkflowFields(steps).length, 3);
  assert.match(nextWorkflowPrompt(steps), /observe/);
});

test("invalid evidence types cannot invent validation", () => {
  const entries = [{ kind: "certified_fix", text: "Unknown root cause", source: "anything" }];
  const normalized = cleanWorkflowSteps(entries);
  assert.equal(normalized[0].kind, "observation");
  assert.equal(normalized[0].source, "typed");
  assert.match(buildWorkflowDraft({ steps: entries }), /Unknown root cause/);
  assert.match(buildWorkflowDraft({ steps: entries }), /CAUTION/);
  assert.equal(missingWorkflowFields(entries).length, 5);
});

test("automotive capture remains an unapproved draft", () => {
  const draft = buildWorkflowDraft({
    mode: "automotive", language: "Spanish", asset: "Vehicle RO 12",
    steps: [{ id: "1", kind: "action", text: "Se cambió el fusible", source: "voice" }]
  });
  assert.match(draft, /Automotive/);
  assert.match(draft, /Se cambió el fusible/);
  assert.match(draft, /PREGUNTAS PENDIENTES/);
  assert.match(draft, /No aprobado/);
});
