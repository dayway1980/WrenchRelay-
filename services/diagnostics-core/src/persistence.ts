import { randomUUID } from "node:crypto";
import { PrismaClient, WorkspaceKind, ObservationSource } from "./generated/prisma/client.js";
import type { DiagnosticAnalysis, Workspace } from "./diagnostics.js";

function workspaceKind(workspace: Workspace): WorkspaceKind {
  return workspace === "INDUSTRIAL" ? WorkspaceKind.INDUSTRIAL : WorkspaceKind.AUTOMOTIVE;
}
function observationSource(source: string): ObservationSource {
  switch (source) {
    case "TECHNICIAN_TRANSCRIPT": return ObservationSource.TECHNICIAN_TRANSCRIPT;
    case "SENSOR_FRAGMENT": return ObservationSource.SENSOR_FRAGMENT;
    case "MACHINE_CODE": return ObservationSource.MACHINE_CODE;
    case "ASSET_CONTEXT": return ObservationSource.ASSET_CONTEXT;
    case "TEXT_SPAN": return ObservationSource.TECHNICIAN_TEXT;
    default: return ObservationSource.EXTERNAL_SYSTEM;
  }
}

export async function persistDiagnosticAnalysis(
  prisma: PrismaClient,
  args: { tenantId:string; tenantExternalKey:string; actorExternalId:string; workspace:Workspace; analysis:DiagnosticAnalysis }
): Promise<void> {
  const { tenantId,tenantExternalKey,actorExternalId,workspace,analysis }=args;
  await prisma.$transaction(async(tx)=>{
    await tx.tenant.upsert({where:{id:tenantId},update:{},create:{id:tenantId,externalKey:tenantExternalKey,displayName:tenantExternalKey}});
    for(const observation of analysis.observations){
      await tx.observation.create({data:{
        id:observation.id,tenantId,analysisId:analysis.analysisId,workspace:workspaceKind(workspace),
        source:observationSource(observation.source),locale:observation.locale,rawText:observation.rawText??null,
        normalizedText:observation.normalizedText??null,structuredValue:(observation.structuredValue??{}) as object,
        inputSha256:observation.inputSha256,actorExternalId
      }});
      if(observation.source==="TEXT_SPAN"&&observation.rawText&&observation.normalizedText){
        await tx.evidenceSpan.create({data:{id:observation.id,observationId:observation.id,startChar:observation.startChar??null,endChar:observation.endChar??null,rawFragment:observation.rawText,normalizedValue:observation.normalizedText,semanticType:"TECHNICIAN_TEXT_SPAN",fragmentSha256:observation.inputSha256}});
      }
    }
    for(const hypothesis of analysis.hypotheses){
      const inferenceId=randomUUID();
      await tx.inference.create({data:{id:inferenceId,tenantId,analysisId:analysis.analysisId,label:hypothesis.label,summary:hypothesis.summary,confidence:hypothesis.posterior,unknownMechanismProbability:hypothesis.unknownMechanismProbability,method:"CAUSAL_COUNTERFACTUAL_RANKING",methodVersion:analysis.methodologyVersion,requiresHumanReview:true}});
      for(const evidence of hypothesis.evidence){
        const sourceObservation=analysis.observations.find(o=>o.id===evidence.observationId);
        await tx.inferenceEvidence.create({data:{id:randomUUID(),inferenceId,observationId:evidence.observationId,evidenceSpanId:sourceObservation?.source==="TEXT_SPAN"?evidence.observationId:null,contribution:evidence.contribution,rationale:evidence.rationale}});
        await tx.provenanceEdge.create({data:{id:randomUUID(),tenantId,sourceEntity:sourceObservation?.source==="TEXT_SPAN"?"EvidenceSpan":"Observation",sourceId:evidence.observationId,relation:"WAS_DERIVED_FROM",targetEntity:"Inference",targetId:inferenceId,activity:"CAUSAL_COUNTERFACTUAL_RANKING",agentExternalId:"wrenchrelay-diagnostics-core",metadata:{methodologyVersion:analysis.methodologyVersion,contribution:evidence.contribution}}});
      }
    }
  },{timeout:15_000});
}
