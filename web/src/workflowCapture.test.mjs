import test from "node:test";
import assert from "node:assert/strict";
import { WORKFLOW_FIELDS, cleanWorkflowSteps, missingWorkflowFields, nextWorkflowPrompt, buildWorkflowDraft, createWorkflowDrafts, readWorkflowDraft, writeWorkflowDraft, writeModeText, readModeText } from "./workflowCapture.mjs";

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

test("switching industrial and automotive keeps an independent unsaved draft for each mode", () => {
  let drafts = createWorkflowDrafts();
  drafts = writeWorkflowDraft(drafts, "industrial", {
    entries: [{ id: "1", kind: "symptom", text: "Press 4 would not cycle", source: "voice" }],
    kind: "observation",
    text: "Pending industrial note",
    source: "typed",
    reviewed: false
  });
  const industrial = readWorkflowDraft(drafts, "industrial");
  const automotive = readWorkflowDraft(drafts, "automotive");
  assert.equal(industrial.entries[0].text, "Press 4 would not cycle");
  assert.equal(industrial.text, "Pending industrial note");
  assert.equal(automotive.entries.length, 0);
  assert.equal(automotive.text, "");

  drafts = writeWorkflowDraft(drafts, "automotive", {
    entries: [{ id: "2", kind: "symptom", text: "Intermittent no-crank", source: "typed" }],
    text: "",
    reviewed: false
  });
  assert.equal(readWorkflowDraft(drafts, "industrial").entries[0].text, "Press 4 would not cycle");
  assert.equal(readWorkflowDraft(drafts, "automotive").entries[0].text, "Intermittent no-crank");
  assert.match(buildWorkflowDraft({ mode: "industrial", steps: readWorkflowDraft(drafts, "industrial").entries }), /Press 4 would not cycle/);
  assert.match(buildWorkflowDraft({ mode: "automotive", steps: readWorkflowDraft(drafts, "automotive").entries }), /Intermittent no-crank/);
  assert.doesNotMatch(buildWorkflowDraft({ mode: "automotive", steps: readWorkflowDraft(drafts, "automotive").entries }), /Press 4 would not cycle/);
});

test("demo editor text stays associated with the mode that produced it", () => {
  let store = writeModeText(undefined, "industrial", "INDUSTRIAL DRAFT");
  store = writeModeText(store, "automotive", "AUTOMOTIVE DRAFT");
  assert.equal(readModeText(store, "industrial"), "INDUSTRIAL DRAFT");
  assert.equal(readModeText(store, "automotive"), "AUTOMOTIVE DRAFT");
  store = writeModeText(store, "automotive", "UPDATED AUTO");
  assert.equal(readModeText(store, "industrial"), "INDUSTRIAL DRAFT");
  assert.equal(readModeText(store, "automotive"), "UPDATED AUTO");
});
