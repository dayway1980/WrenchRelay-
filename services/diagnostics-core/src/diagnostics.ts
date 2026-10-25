import { createHash, randomUUID } from "node:crypto";
import { z } from "zod";

export const WorkspaceSchema = z.enum(["INDUSTRIAL", "AUTOMOTIVE"]);
export type Workspace = z.infer<typeof WorkspaceSchema>;

export const IntakeSchema = z.object({
  tenantId: z.string().uuid(),
  actorExternalId: z.string().min(1).max(200),
  workspace: WorkspaceSchema,
  locale: z.string().min(2).max(35).default("en-US"),
  transcript: z.string().min(2).max(50_000),
  sensorFragments: z.array(z.object({
    name: z.string().min(1).max(120),
    value: z.union([z.string(), z.number(), z.boolean()]),
    unit: z.string().max(40).optional(),
    occurredAt: z.string().datetime().optional()
  })).max(500).default([]),
  machineCodes: z.array(z.string().min(1).max(120)).max(100).default([]),
  assetContext: z.record(z.string(), z.union([z.string(), z.number(), z.boolean(), z.null()])).default({})
});
export type Intake = z.infer<typeof IntakeSchema>;

export type DiagnosticLabel =
  | "NETWORK_COMMUNICATION" | "EMI_COUPLING" | "DRIVE_OR_MOTOR" | "CONTROL_LOGIC"
  | "POWER_QUALITY" | "SENSOR_INSTRUMENTATION" | "SAFETY_INTERLOCK" | "MECHANICAL"
  | "HYDRAULIC_PNEUMATIC" | "AUTO_CRANK_POSITION" | "AUTO_IGNITION" | "AUTO_FUEL"
  | "AUTO_AIR_METERING" | "AUTO_STARTING_POWER";

export interface Observation {
  id: string;
  analysisId: string;
  source: "TECHNICIAN_TRANSCRIPT" | "TEXT_SPAN" | "SENSOR_FRAGMENT" | "MACHINE_CODE" | "ASSET_CONTEXT";
  locale: string;
  rawText?: string;
  normalizedText?: string;
  structuredValue?: Record<string, unknown>;
  startChar?: number;
  endChar?: number;
  inputSha256: string;
}

export interface HypothesisResult {
  id: string;
  label: string;
  summary: string;
  posterior: number;
  unknownMechanismProbability: number;
  evidence: Array<{ observationId: string; contribution: number; rationale: string }>;
}

export interface NextTest {
  id: string;
  title: string;
  expectedInformationGain: number;
  utility: number;
  risk: "READ_ONLY" | "LOW" | "MEDIUM" | "HIGH";
  downtimeCost: number;
  directCost: number;
  irreversibility: number;
  requiresHumanAuthorization: boolean;
  rationale: string;
}

export interface DiagnosticAnalysis {
  analysisId: string;
  inputSha256: string;
  normalizedTranscript: string;
  observations: Observation[];
  weakSupervision: {
    methodology: "DEPENDENCY_AWARE_UNLABELED_EM";
    labelDistribution: Array<{
      label: DiagnosticLabel; probability: number; effectiveSupport: number;
      rawVoteCount: number; evidenceIds: string[]; rationales: string[];
    }>;
    abstentionRate: number;
    conflictRate: number;
  };
  hypotheses: HypothesisResult[];
  nextTests: NextTest[];
  requiresTechnicianReview: true;
  directCmmsWriteAllowed: false;
  methodologyVersion: string;
}

type LF = {
  name: string;
  family: string;
  prior: number;
  label: DiagnosticLabel;
  regex: RegExp;
  reason: string;
};
type Vote = { lf: string; family: string; prior: number; label: DiagnosticLabel; observationId: string; reason: string };

const INDUSTRIAL: LF[] = [
  ["network","network",.82,"NETWORK_COMMUNICATION",/\b(rs-485|ethernet|modbus|profinet|profibus|network|comm(?:s|unication)?|timeout|packet|link down|node)\b/i,"Communication/network evidence."],
  ["emi","emi",.86,"EMI_COUPLING",/\b(emi|noise|shield|ground loop|inductive|kick|dv\/dt|common mode|interference)\b/i,"EMI/coupling evidence."],
  ["temporal_emi","temporal",.89,"EMI_COUPLING",/\b(when|while|during|as)\b.{0,60}\b(motor|vfd|drive)\b.{0,50}\b(start|accelerat|ramp|decel)/i,"Symptom is temporally coupled to motor/drive transition."],
  ["drive","drive",.82,"DRIVE_OR_MOTOR",/\b(vfd|drive|motor|overcurrent|overvoltage|undervoltage|fault code|trip|torque|frequency)\b/i,"Drive/motor evidence."],
  ["controls","controls",.78,"CONTROL_LOGIC",/\b(plc|hmi|ladder|logic|interlock|sequence|input bit|output bit|tag|program)\b/i,"PLC/HMI/logic evidence."],
  ["power","power",.80,"POWER_QUALITY",/\b(three-phase|3-phase|phase loss|voltage sag|brownout|transient|line voltage|480\s*v|240\s*v|120\s*v)\b/i,"Power-quality evidence."],
  ["sensor","sensor",.78,"SENSOR_INSTRUMENTATION",/\b(sensor|prox|encoder|thermocouple|transducer|4-20\s*ma|analog input|photoeye)\b/i,"Sensor/instrumentation evidence."],
  ["safety","safety",.95,"SAFETY_INTERLOCK",/\b(e-stop|loto|lockout|guard|safety relay|safety plc|arc flash|nfpa 70e)\b/i,"Safety-system evidence."],
  ["mechanical","mechanical",.78,"MECHANICAL",/\b(bearing|gear|chain|belt|shaft|coupling|vibration|alignment|jam|seized)\b/i,"Mechanical evidence."],
  ["fluid","fluid",.82,"HYDRAULIC_PNEUMATIC",/\b(hydraulic|pneumatic|air pressure|oil pressure|valve|solenoid|cylinder|psi|bar)\b/i,"Fluid-power evidence."]
].map(([name,family,prior,label,regex,reason]) => ({ name, family, prior, label, regex, reason } as LF));

const AUTOMOTIVE: LF[] = [
  ["position","position",.88,"AUTO_CRANK_POSITION",/\b(crank sensor|crankshaft position|cam sensor|camshaft position|p0335|p0340|hot soak)\b/i,"Position-sensor/heat-soak evidence."],
  ["ignition","ignition",.82,"AUTO_IGNITION",/\b(misfire|coil|spark|plug|p030[0-9]|ignition)\b/i,"Ignition evidence."],
  ["fuel","fuel",.80,"AUTO_FUEL",/\b(fuel pressure|fuel pump|injector|lean|rich|p0171|p0172|rail pressure)\b/i,"Fuel-delivery evidence."],
  ["air","air",.78,"AUTO_AIR_METERING",/\b(maf|map sensor|vacuum leak|throttle body|airflow|intake leak)\b/i,"Air-metering evidence."],
  ["starting","starting",.82,"AUTO_STARTING_POWER",/\b(no crank|slow crank|starter|battery|charging|alternator|voltage drop)\b/i,"Starting/charging evidence."]
].map(([name,family,prior,label,regex,reason]) => ({ name, family, prior, label, regex, reason } as LF));

const HYPOTHESES = {
  INDUSTRIAL: [
    {id:"physical_network_fault", summary:"Physical network, topology, connector, or communication-line fault.", prior:.18, supports:["NETWORK_COMMUNICATION"]},
    {id:"motor_coupled_emi", summary:"Motor/VFD switching or acceleration couples interference into communication or instrumentation.", prior:.12, supports:["EMI_COUPLING","DRIVE_OR_MOTOR","NETWORK_COMMUNICATION"]},
    {id:"drive_motor_fault", summary:"Drive or motor fault is primary.", prior:.16, supports:["DRIVE_OR_MOTOR","POWER_QUALITY"]},
    {id:"control_logic_fault", summary:"PLC/HMI sequence, state, or interlock defect is primary.", prior:.14, supports:["CONTROL_LOGIC","SAFETY_INTERLOCK"]},
    {id:"power_quality_fault", summary:"Supply sag, transient, phase, grounding, or power-quality event is primary.", prior:.13, supports:["POWER_QUALITY","NETWORK_COMMUNICATION"]},
    {id:"sensor_fault", summary:"Sensor/instrumentation path is primary.", prior:.14, supports:["SENSOR_INSTRUMENTATION"]},
    {id:"mechanical_process_fault", summary:"Mechanical or fluid-power process condition is primary.", prior:.13, supports:["MECHANICAL","HYDRAULIC_PNEUMATIC"]}
  ],
  AUTOMOTIVE: [
    {id:"crank_position_heat_fault", summary:"Crank/cam position sensing is unreliable with heat or intermittency.", prior:.22, supports:["AUTO_CRANK_POSITION"]},
    {id:"ignition_fault", summary:"Ignition energy or coil/plug path is primary.", prior:.21, supports:["AUTO_IGNITION"]},
    {id:"fuel_delivery_fault", summary:"Fuel pressure, pump, injector, or mixture delivery is primary.", prior:.21, supports:["AUTO_FUEL"]},
    {id:"air_metering_fault", summary:"Air metering or unmetered-air path is primary.", prior:.18, supports:["AUTO_AIR_METERING"]},
    {id:"starting_power_fault", summary:"Battery, starter, cabling, or charging path is primary.", prior:.18, supports:["AUTO_STARTING_POWER"]}
  ]
} as const;

const TESTS = {
  INDUSTRIAL: [
    {id:"read_drive_fault_history",title:"Read VFD/drive event history without changing parameters.",risk:"READ_ONLY",downtime:.05,cost:.02,irreversible:0,auth:false,signatures:{physical_network_fault:"none",motor_coupled_emi:"time-correlated",drive_motor_fault:"drive-fault",control_logic_fault:"none",power_quality_fault:"bus-event",sensor_fault:"none",mechanical_process_fault:"possible-overload"}},
    {id:"passive_network_capture",title:"Capture passive network errors and correlate them to motor/drive state.",risk:"READ_ONLY",downtime:.05,cost:.08,irreversible:0,auth:false,signatures:{physical_network_fault:"persistent",motor_coupled_emi:"switching-cluster",drive_motor_fault:"clean",control_logic_fault:"clean",power_quality_fault:"multi-node",sensor_fault:"clean",mechanical_process_fault:"clean"}},
    {id:"inspect_shield_ground_route",title:"Inspect routing, shield termination, bonding, and separation from motor conductors.",risk:"LOW",downtime:.08,cost:.04,irreversible:0,auth:true,signatures:{physical_network_fault:"termination-defect",motor_coupled_emi:"shield-route-defect",drive_motor_fault:"none",control_logic_fault:"none",power_quality_fault:"bonding-defect",sensor_fault:"signal-route-defect",mechanical_process_fault:"none"}},
    {id:"controlled_motor_off_comparison",title:"Under approved isolation procedure, compare communication with suspect motor/drive inactive.",risk:"MEDIUM",downtime:.45,cost:.12,irreversible:.05,auth:true,signatures:{physical_network_fault:"continues",motor_coupled_emi:"disappears",drive_motor_fault:"changes",control_logic_fault:"may-remain",power_quality_fault:"may-disappear",sensor_fault:"may-remain",mechanical_process_fault:"not-exercised"}}
  ],
  AUTOMOTIVE: [
    {id:"capture_rpm_during_no_start",title:"Observe scan-tool RPM while cranking during failure.",risk:"READ_ONLY",downtime:.05,cost:.02,irreversible:0,auth:false,signatures:{crank_position_heat_fault:"rpm-missing",ignition_fault:"rpm-present",fuel_delivery_fault:"rpm-present",air_metering_fault:"rpm-present",starting_power_fault:"rpm-slow"}},
    {id:"record_fuel_pressure_failure",title:"Record fuel pressure during failure.",risk:"LOW",downtime:.08,cost:.05,irreversible:0,auth:true,signatures:{crank_position_heat_fault:"normal",ignition_fault:"normal",fuel_delivery_fault:"abnormal",air_metering_fault:"normal",starting_power_fault:"tracks-voltage"}},
    {id:"battery_voltage_drop_test",title:"Measure battery and starter-circuit voltage drop while cranking.",risk:"LOW",downtime:.05,cost:.03,irreversible:0,auth:true,signatures:{crank_position_heat_fault:"normal",ignition_fault:"normal",fuel_delivery_fault:"normal",air_metering_fault:"normal",starting_power_fault:"excessive-drop"}}
  ]
} as const;

const hash = (value: string) => createHash("sha256").update(value, "utf8").digest("hex");
const clamp = (v:number,min=0,max=1) => Math.max(min,Math.min(max,v));
const softmax = (xs:number[]) => {
  if (!xs.length) return [];
  const m=Math.max(...xs), es=xs.map(x=>Math.exp(x-m)), s=es.reduce((a,b)=>a+b,0);
  return es.map(x=>x/s);
};

export function normalizeTechnicianText(input:string):string {
  return input.normalize("NFKC").replace(/[^\S\r\n]+/g," ").trim()
    .replace(/\br\s*s[\s-]*(four|4)\s*(eighty|80)\s*(five|5)\b/gi,"rs-485")
    .replace(/\brs[\s-]*485\b/gi,"rs-485").replace(/\bv[\s.-]*f[\s.-]*d\b/gi,"vfd")
    .replace(/\bp[\s.-]*l[\s.-]*c\b/gi,"plc").replace(/\bh[\s.-]*m[\s.-]*i\b/gi,"hmi")
    .replace(/\be[\s-]*stop\b/gi,"e-stop").replace(/\block[\s-]*out[\s-]*tag[\s-]*out\b/gi,"loto")
    .replace(/\bcrank[\s-]*no[\s-]*start\b/gi,"crank no-start").replace(/\bhot[\s-]*soak\b/gi,"hot soak")
    .replace(/\s+([,.;:!?])/g,"$1").toLowerCase();
}

function observations(input:Intake,analysisId:string):Observation[] {
  const out:Observation[]=[{id:randomUUID(),analysisId,source:"TECHNICIAN_TRANSCRIPT",locale:input.locale,rawText:input.transcript,normalizedText:normalizeTechnicianText(input.transcript),inputSha256:hash(input.transcript)}];
  const re=/[^.!?\n]+(?:[.!?]+|$)/g; let m:RegExpExecArray|null;
  while((m=re.exec(input.transcript))!==null){
    const lead=m[0].search(/\S/); if(lead<0) continue;
    const raw=m[0].trim(), start=m.index+lead;
    out.push({id:randomUUID(),analysisId,source:"TEXT_SPAN",locale:input.locale,rawText:raw,normalizedText:normalizeTechnicianText(raw),startChar:start,endChar:start+raw.length,inputSha256:hash(raw)});
  }
  for(const s of input.sensorFragments){
    const raw=JSON.stringify(s);
    out.push({id:randomUUID(),analysisId,source:"SENSOR_FRAGMENT",locale:input.locale,rawText:`${s.name}=${String(s.value)}${s.unit?` ${s.unit}`:""}`,normalizedText:normalizeTechnicianText(`${s.name} ${String(s.value)} ${s.unit??""}`),structuredValue:{name:s.name,value:s.value,unit:s.unit??null,occurredAt:s.occurredAt??null},inputSha256:hash(raw)});
  }
  for(const code of input.machineCodes) out.push({id:randomUUID(),analysisId,source:"MACHINE_CODE",locale:input.locale,rawText:code,normalizedText:normalizeTechnicianText(code),structuredValue:{code},inputSha256:hash(code)});
  if(Object.keys(input.assetContext).length){const raw=JSON.stringify(input.assetContext);out.push({id:randomUUID(),analysisId,source:"ASSET_CONTEXT",locale:input.locale,rawText:raw,normalizedText:normalizeTechnicianText(raw),structuredValue:input.assetContext,inputSha256:hash(raw)});}
  return out;
}

function weakSupervision(obs:Observation[],workspace:Workspace){
  const rules=workspace==="INDUSTRIAL"?INDUSTRIAL:AUTOMOTIVE;
  const candidates=obs.filter(o=>o.normalizedText&&o.source!=="TECHNICIAN_TRANSCRIPT");
  const votes:Vote[]=[]; let abstain=0, opportunities=0;
  for(const o of candidates) for(const lf of rules){opportunities++; if(lf.regex.test(o.normalizedText!)) votes.push({lf:lf.name,family:lf.family,prior:lf.prior,label:lf.label,observationId:o.id,reason:lf.reason}); else abstain++;}
  const labels=[...new Set(votes.map(v=>v.label))];
  if(!labels.length) return {methodology:"DEPENDENCY_AWARE_UNLABELED_EM" as const,labelDistribution:[],abstentionRate:opportunities?abstain/opportunities:1,conflictRate:0};

  const reliab=new Map<string,number>(); for(const v of votes) if(!reliab.has(v.lf)) reliab.set(v.lf,v.prior);
  const byObs=new Map<string,Vote[]>(); for(const o of candidates) byObs.set(o.id,votes.filter(v=>v.observationId===o.id));
  for(let iter=0;iter<6;iter++){
    const latent=new Map<string,Map<DiagnosticLabel,number>>();
    for(const o of candidates){
      const ov=byObs.get(o.id)??[];
      const scores=labels.map(label=>{let score=0;const families=new Set<string>();for(const v of ov){if(v.label!==label)continue;const r=clamp(reliab.get(v.lf)??.7,.51,.97),disc=families.has(v.family)?.35:1;families.add(v.family);score+=Math.log(r/(1-r))*disc;}return score;});
      const ps=softmax(scores); latent.set(o.id,new Map(labels.map((l,i)=>[l,ps[i]??0])));
    }
    for(const name of new Set(votes.map(v=>v.lf))){
      const lv=votes.filter(v=>v.lf===name); if(!lv.length)continue;
      const agree=lv.reduce((s,v)=>s+(latent.get(v.observationId)?.get(v.label)??.5),0)/lv.length;
      reliab.set(name,clamp(.70*lv[0]!.prior+.30*agree,.51,.97));
    }
  }

  const totals=new Map<DiagnosticLabel,{score:number,ids:Set<string>,reasons:Set<string>,raw:number}>();
  for(const l of labels) totals.set(l,{score:0,ids:new Set(),reasons:new Set(),raw:0});
  for(const o of candidates){
    const seen=new Set<string>();
    for(const v of byObs.get(o.id)??[]){
      const key=`${v.family}:${v.label}`,disc=seen.has(key)?.35:1;seen.add(key);
      const r=clamp(reliab.get(v.lf)??v.prior,.51,.97), t=totals.get(v.label)!;
      t.score+=Math.log(r/(1-r))*disc;t.ids.add(v.observationId);t.reasons.add(v.reason);t.raw++;
    }
  }
  const probs=softmax(labels.map(l=>totals.get(l)!.score));
  let active=0,conflicts=0;for(const o of candidates){const s=new Set((byObs.get(o.id)??[]).map(v=>v.label));if(s.size)active++;if(s.size>1)conflicts++;}
  return {methodology:"DEPENDENCY_AWARE_UNLABELED_EM" as const,labelDistribution:labels.map((label,i)=>{const t=totals.get(label)!;return{label,probability:probs[i]??0,effectiveSupport:Number(t.score.toFixed(4)),rawVoteCount:t.raw,evidenceIds:[...t.ids],rationales:[...t.reasons]};}).sort((a,b)=>b.probability-a.probability),abstentionRate:opportunities?abstain/opportunities:1,conflictRate:active?conflicts/active:0};
}

function hypotheses(dist:DiagnosticAnalysis["weakSupervision"]["labelDistribution"],workspace:Workspace){
  const by=new Map(dist.map(d=>[d.label,d])); const defs=HYPOTHESES[workspace];
  const scored=defs.map(h=>{let score=Math.log(h.prior);const evidence:HypothesisResult["evidence"]=[];for(const label of h.supports){const d=by.get(label as DiagnosticLabel);if(!d)continue;const c=1.6*d.probability;score+=c;for(const id of d.evidenceIds)evidence.push({observationId:id,contribution:clamp(c/Math.max(1,d.evidenceIds.length),-1,1),rationale:`Supports ${label}: ${d.rationales.join(" ")}`});}return{h,score,evidence};});
  const top=dist[0]?.probability??0, concentration=dist.reduce((s,d)=>s+d.probability*d.probability,0);
  const unknownLogit=1.4-2.3*top-.9*concentration, ps=softmax([...scored.map(s=>s.score),unknownLogit]), unknown=ps.at(-1)??1;
  return {unknown,items:scored.map((s,i)=>({id:s.h.id,label:s.h.id,summary:s.h.summary,posterior:ps[i]??0,unknownMechanismProbability:unknown,evidence:s.evidence})).sort((a,b)=>b.posterior-a.posterior)};
}

function nextTests(hs:HypothesisResult[],workspace:Workspace):NextTest[]{
  const active=hs.filter(h=>h.posterior>=.03).slice(0,5);
  return TESTS[workspace].map(t=>{let sep=0;for(let i=0;i<active.length;i++)for(let j=i+1;j<active.length;j++){const a=active[i]!,b=active[j]!,sig=t.signatures as Record<string,string>;if((sig[a.id]??"unknown")!==(sig[b.id]??"unknown"))sep+=a.posterior*b.posterior;}const info=clamp(sep*4),risk=t.risk==="HIGH"?.9:t.risk==="MEDIUM"?.45:t.risk==="LOW"?.15:0,utility=info-risk-t.downtime-t.cost-t.irreversible-(t.auth?.08:0);return{id:t.id,title:t.title,expectedInformationGain:Number(info.toFixed(4)),utility:Number(utility.toFixed(4)),risk:t.risk,downtimeCost:t.downtime,directCost:t.cost,irreversibility:t.irreversible,requiresHumanAuthorization:t.auth,rationale:`Expected hypothesis separation=${info.toFixed(3)}; utility subtracts safety, downtime, cost, irreversibility, and authorization penalties.`};}).sort((a,b)=>b.utility-a.utility);
}

export function analyzeIntake(untrusted:unknown):DiagnosticAnalysis{
  const input=IntakeSchema.parse(untrusted),analysisId=randomUUID(),obs=observations(input,analysisId),weak=weakSupervision(obs,input.workspace),h=hypotheses(weak.labelDistribution,input.workspace);
  return {analysisId,inputSha256:hash(JSON.stringify(input)),normalizedTranscript:normalizeTechnicianText(input.transcript),observations:obs,weakSupervision:weak,hypotheses:h.items,nextTests:nextTests(h.items,input.workspace),requiresTechnicianReview:true,directCmmsWriteAllowed:false,methodologyVersion:"wr-diagnostics-core/0.1.0"};
}
