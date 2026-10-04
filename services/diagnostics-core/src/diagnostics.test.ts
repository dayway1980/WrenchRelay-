import test from "node:test";
import assert from "node:assert/strict";
import { analyzeIntake, normalizeTechnicianText } from "./diagnostics.js";

const tenantId = "00000000-0000-4000-8000-000000000001";

test("normalizes technician dictation", () => {
  const value = normalizeTechnicianText("PLC shows R S four eighty five timeout when V F D accelerates.");
  assert.match(value, /plc/); assert.match(value, /rs-485/); assert.match(value, /vfd/);
});

test("keeps CMMS write disabled and represents motor-coupled EMI", () => {
  const result = analyzeIntake({
    tenantId, actorExternalId:"tech-1", workspace:"INDUSTRIAL", locale:"en-US",
    transcript:"PLC RS-485 drops communication when the adjacent VFD motor accelerates. Shield drain is questionable and noise appears at ramp.",
    sensorFragments:[], machineCodes:[], assetContext:{voltage:"480V"}
  });
  assert.equal(result.requiresTechnicianReview,true);
  assert.equal(result.directCmmsWriteAllowed,false);
  assert.ok(result.hypotheses.some(h=>h.id==="motor_coupled_emi"));
  assert.ok(result.nextTests.some(t=>t.id==="passive_network_capture"));
});

test("retains explicit unknown-mechanism probability for sparse evidence", () => {
  const result = analyzeIntake({tenantId,actorExternalId:"tech-2",workspace:"INDUSTRIAL",locale:"en-US",transcript:"Machine acts weird sometimes.",sensorFragments:[],machineCodes:[],assetContext:{}});
  assert.ok(result.hypotheses.every(h=>h.unknownMechanismProbability>0));
  assert.equal(result.weakSupervision.labelDistribution.length,0);
});

test("automotive workspace recognizes hot-soak crank-position evidence", () => {
  const result = analyzeIntake({tenantId,actorExternalId:"advisor-1",workspace:"AUTOMOTIVE",locale:"en-US",transcript:"Intermittent crank no-start after hot soak. Scan RPM drops out and P0335 was stored.",sensorFragments:[],machineCodes:["P0335"],assetContext:{year:2017}});
  assert.ok(result.hypotheses.some(h=>h.id==="crank_position_heat_fault"));
});
