import { createHash, randomUUID } from "node:crypto";
import { z } from "zod";
import { PrismaClient, CmmsDraftStatus, ApprovalDecision } from "./generated/prisma/client.js";
import { t, translationMatrix } from "./i18n.js";

const ProviderSchema = z.enum(["FIIX", "EMAINT", "MAINTENANCE_CONNECTION", "GENERIC_REST"]);
export type CmmsProvider = z.infer<typeof ProviderSchema>;

const WorkOrderSchema = z.object({
  title: z.string().min(1).max(240),
  description: z.string().min(1).max(20_000),
  assetExternalId: z.string().max(240).optional(),
  priority: z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"]).default("MEDIUM"),
  requestedStart: z.string().datetime().optional(),
  safetyNotes: z.array(z.string().max(1000)).max(50).default([]),
  diagnosis: z.object({
    inferenceId: z.string().uuid().optional(),
    summary: z.string().max(5000),
    confidence: z.number().min(0).max(1),
    unknownMechanismProbability: z.number().min(0).max(1)
  }).optional(),
  customFields: z.record(z.string(), z.union([z.string(), z.number(), z.boolean(), z.null()])).default({})
});

export const PrepareDraftSchema = z.object({
  tenantId: z.string().uuid(),
  connectionId: z.string().uuid(),
  actorExternalId: z.string().min(1).max(200),
  locale: z.string().min(2).max(35).default("en-US"),
  operation: z.literal("CREATE_WORK_ORDER"),
  workOrder: WorkOrderSchema
});

export const ApprovalSchema = z.object({
  actorExternalId: z.string().min(1).max(200),
  actorDisplay: z.string().max(200).optional(),
  decision: z.enum(["APPROVED", "REJECTED"]),
  approvedPayloadSha256: z.string().regex(/^[a-f0-9]{64}$/),
  comment: z.string().max(4000).optional(),
  clientContext: z.record(z.string(), z.unknown()).optional()
});

type ConnectionConfig = {
  createWorkOrderPath?: string;
  createWorkOrderMethod?: "POST" | "PUT";
  auth?: { type?: "BEARER" | "API_KEY_HEADER"; headerName?: string };
  fieldMap?: Record<string, string>;
  extraHeaders?: Record<string, string>;
};

export interface ConfirmationPayload {
  type: "CMMS_WRITE_CONFIRMATION";
  draftId: string;
  immutablePayloadSha256: string;
  provider: CmmsProvider;
  operation: "CREATE_WORK_ORDER";
  status: "AWAITING_HUMAN_APPROVAL";
  titleKey: "cmms.confirm.title";
  warningKey: "cmms.confirm.warning";
  locale: string;
  copy: { title: string; warning: string; approve: string; reject: string };
  translations: Record<string, string>;
  preview: Array<{ labelKey: string; label: string; value: string }>;
  controls: { directAiWriteAllowed: false; approvalBoundToExactHash: true; requiresAuthenticatedHuman: true };
  actions: Array<{ id: "approve" | "reject"; method: "POST"; href: string; requiresReauthentication: boolean; bodyTemplate: Record<string, string> }>;
}

export interface SecretResolver { resolve(secretRef: string): Promise<string> }

export class EnvironmentSecretResolver implements SecretResolver {
  async resolve(secretRef: string): Promise<string> {
    const envName = `WR_SECRET_${secretRef.toUpperCase().replace(/[^A-Z0-9]+/g, "_")}`;
    const value = process.env[envName];
    if (!value) throw new Error(`CMMS secret reference '${secretRef}' is not available in this runtime.`);
    return value;
  }
}

function canonicalize(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalize).join(",")}]`;
  if (value && typeof value === "object") {
    const object = value as Record<string, unknown>;
    return `{${Object.keys(object).sort().map((key) => `${JSON.stringify(key)}:${canonicalize(object[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}
function sha256(value: unknown): string { return createHash("sha256").update(canonicalize(value), "utf8").digest("hex") }
function safeJoinUrl(baseUrl: string, path: string): string {
  const base = new URL(baseUrl);
  if (base.protocol !== "https:" && process.env.NODE_ENV === "production") throw new Error("Production CMMS connections must use HTTPS.");
  return new URL(path.replace(/^\/+/, ""), baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`).toString();
}
function mapWorkOrder(workOrder: z.infer<typeof WorkOrderSchema>, map: Record<string, string> = {}): Record<string, unknown> {
  const source: Record<string, unknown> = {
    title: workOrder.title, description: workOrder.description, assetExternalId: workOrder.assetExternalId,
    priority: workOrder.priority, requestedStart: workOrder.requestedStart, safetyNotes: workOrder.safetyNotes,
    diagnosis: workOrder.diagnosis, ...workOrder.customFields
  };
  const output: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(source)) if (value !== undefined) output[map[key] ?? key] = value;
  return output;
}
function defaultFieldMap(provider: CmmsProvider): Record<string, string> {
  switch (provider) {
    case "FIIX": return { title: "strDescription", description: "strLongDescription", assetExternalId: "intAssetID" };
    case "EMAINT": return { title: "title", description: "description", assetExternalId: "assetId" };
    case "MAINTENANCE_CONNECTION": return { title: "requestName", description: "description", assetExternalId: "assetId" };
    case "GENERIC_REST": return {};
  }
}

export class CmmsBridge {
  constructor(private readonly prisma: PrismaClient, private readonly secrets: SecretResolver, private readonly publicBaseUrl: string) {}

  async prepare(inputUnknown: unknown): Promise<ConfirmationPayload> {
    const input = PrepareDraftSchema.parse(inputUnknown);
    const connection = await this.prisma.cmmsConnection.findFirst({ where: { id: input.connectionId, tenantId: input.tenantId, enabled: true } });
    if (!connection) throw new Error("Enabled CMMS connection not found for tenant.");
    if (input.workOrder.diagnosis?.inferenceId) {
      const inference = await this.prisma.inference.findFirst({ where: { id: input.workOrder.diagnosis.inferenceId, tenantId: input.tenantId } });
      if (!inference) throw new Error("Referenced diagnostic inference does not belong to this tenant.");
    }
    const provider = ProviderSchema.parse(connection.provider);
    const payload = mapWorkOrder(input.workOrder, { ...defaultFieldMap(provider), ...((connection.providerConfig as ConnectionConfig).fieldMap ?? {}) });
    const payloadSha256 = sha256(payload);
    const draft = await this.prisma.cmmsDraft.create({
      data: {
        id: randomUUID(), tenantId: input.tenantId, connectionId: connection.id,
        inferenceId: input.workOrder.diagnosis?.inferenceId ?? null, operation: input.operation, payload,
        payloadSha256, status: CmmsDraftStatus.PREPARED, createdBy: input.actorExternalId
      }
    });
    const base = this.publicBaseUrl.replace(/\/+$/, "");
    return {
      type:"CMMS_WRITE_CONFIRMATION", draftId:draft.id, immutablePayloadSha256:payloadSha256, provider,
      operation:"CREATE_WORK_ORDER", status:"AWAITING_HUMAN_APPROVAL", titleKey:"cmms.confirm.title",
      warningKey:"cmms.confirm.warning", locale:input.locale,
      copy:{title:t(input.locale,"cmms.confirm.title"),warning:t(input.locale,"cmms.confirm.warning"),approve:t(input.locale,"cmms.confirm.approve"),reject:t(input.locale,"cmms.confirm.reject")},
      translations: translationMatrix(input.locale),
      preview:[
        {labelKey:"cmms.field.title",label:t(input.locale,"cmms.field.title"),value:input.workOrder.title},
        {labelKey:"cmms.field.description",label:t(input.locale,"cmms.field.description"),value:input.workOrder.description},
        {labelKey:"cmms.field.priority",label:t(input.locale,"cmms.field.priority"),value:input.workOrder.priority},
        ...(input.workOrder.assetExternalId?[{labelKey:"cmms.field.asset",label:t(input.locale,"cmms.field.asset"),value:input.workOrder.assetExternalId}]:[])
      ],
      controls:{directAiWriteAllowed:false,approvalBoundToExactHash:true,requiresAuthenticatedHuman:true},
      actions:[
        {id:"approve",method:"POST",href:`${base}/v1/cmms/${draft.id}/decision`,requiresReauthentication:true,bodyTemplate:{decision:"APPROVED",approvedPayloadSha256:payloadSha256}},
        {id:"reject",method:"POST",href:`${base}/v1/cmms/${draft.id}/decision`,requiresReauthentication:false,bodyTemplate:{decision:"REJECTED",approvedPayloadSha256:payloadSha256}}
      ]
    };
  }

  async decide(tenantId: string, draftId: string, inputUnknown: unknown) {
    const input = ApprovalSchema.parse(inputUnknown);
    return this.prisma.$transaction(async (tx) => {
      const draft = await tx.cmmsDraft.findFirst({ where: { id: draftId, tenantId } });
      if (!draft) throw new Error("Draft not found.");
      if (![CmmsDraftStatus.PREPARED, CmmsDraftStatus.APPROVED].includes(draft.status)) throw new Error(`Draft is not reviewable from status ${draft.status}.`);
      const liveHash = sha256(draft.payload);
      if (liveHash !== draft.payloadSha256 || input.approvedPayloadSha256 !== draft.payloadSha256) throw new Error("Approval hash mismatch. The exact payload shown to the technician must be approved.");
      const decision = input.decision === "APPROVED" ? ApprovalDecision.APPROVED : ApprovalDecision.REJECTED;
      const approval = await tx.humanApproval.create({
        data: {
          id:randomUUID(), tenantId, draftId, decision, approvedPayloadSha256:input.approvedPayloadSha256,
          actorExternalId:input.actorExternalId, actorDisplay:input.actorDisplay??null, comment:input.comment??null,
          clientContext:(input.clientContext??{}) as object
        }
      });
      await tx.cmmsDraft.update({where:{id:draftId},data:{status:input.decision==="APPROVED"?CmmsDraftStatus.APPROVED:CmmsDraftStatus.REJECTED}});
      return approval;
    });
  }

  async dispatch(tenantId: string, draftId: string, actorExternalId: string) {
    const prepared = await this.prisma.$transaction(async (tx) => {
      const draft = await tx.cmmsDraft.findFirst({where:{id:draftId,tenantId},include:{connection:true,approvals:{orderBy:{decidedAt:"desc"},take:1}}});
      if (!draft) throw new Error("Draft not found.");
      if (draft.status !== CmmsDraftStatus.APPROVED) throw new Error("Draft has not been approved.");
      const approval=draft.approvals[0];
      if (!approval || approval.decision !== ApprovalDecision.APPROVED) throw new Error("No active human approval exists.");
      const liveHash=sha256(draft.payload);
      if (liveHash!==draft.payloadSha256 || approval.approvedPayloadSha256!==draft.payloadSha256) throw new Error("Approved payload hash no longer matches; dispatch blocked.");
      const idempotencyKey=`cmms:${draft.id}:${draft.payloadSha256}`;
      const existing=await tx.cmmsDispatch.findUnique({where:{idempotencyKey}});
      if(existing?.httpStatus&&existing.httpStatus>=200&&existing.httpStatus<300)return{alreadyComplete:existing,draft:null,dispatchId:existing.id};
      const dispatch=await tx.cmmsDispatch.upsert({
        where:{idempotencyKey},update:{startedAt:new Date(),finishedAt:null,errorCode:null,httpStatus:null},
        create:{id:randomUUID(),draftId:draft.id,idempotencyKey,requestSha256:draft.payloadSha256}
      });
      await tx.cmmsDraft.update({where:{id:draft.id},data:{status:CmmsDraftStatus.DISPATCHING}});
      return{alreadyComplete:null,draft,dispatchId:dispatch.id};
    });
    if(prepared.alreadyComplete)return prepared.alreadyComplete;
    const draft=prepared.draft!,config=draft.connection.providerConfig as ConnectionConfig,path=config.createWorkOrderPath;
    if(!path){await this.markDispatchFailure(draft.id,prepared.dispatchId,"CMMS endpoint path is not configured.");throw new Error("Tenant CMMS connection has no verified createWorkOrderPath.");}
    const method=config.createWorkOrderMethod??"POST",token=await this.secrets.resolve(draft.connection.secretRef);
    const headers:Record<string,string>={"content-type":"application/json","idempotency-key":`wrenchrelay-${draft.id}`,"x-wrenchrelay-approved-by":actorExternalId,...(config.extraHeaders??{})};
    if(config.auth?.type==="API_KEY_HEADER")headers[config.auth.headerName??"x-api-key"]=token;else headers.authorization=`Bearer ${token}`;
    const url=safeJoinUrl(draft.connection.baseUrl,path);
    try{
      const response=await fetch(url,{method,headers,body:JSON.stringify(draft.payload),signal:AbortSignal.timeout(20_000)});
      const text=await response.text();let responseBody:unknown={raw:text.slice(0,20_000)};try{responseBody=JSON.parse(text);}catch{}
      await this.prisma.$transaction([
        this.prisma.cmmsDispatch.update({where:{id:prepared.dispatchId},data:{httpStatus:response.status,responseBody:responseBody as object,providerRecordId:extractProviderRecordId(responseBody)??null,finishedAt:new Date(),errorCode:response.ok?null:"PROVIDER_HTTP_ERROR"}}),
        this.prisma.cmmsDraft.update({where:{id:draft.id},data:{status:response.ok?CmmsDraftStatus.DISPATCHED:CmmsDraftStatus.FAILED}})
      ]);
      if(!response.ok)throw new Error(`CMMS provider returned HTTP ${response.status}.`);
      return this.prisma.cmmsDispatch.findUniqueOrThrow({where:{id:prepared.dispatchId}});
    }catch(error){
      await this.markDispatchFailure(draft.id,prepared.dispatchId,error instanceof Error?error.message.slice(0,240):"UNKNOWN_DISPATCH_ERROR");
      throw error;
    }
  }

  private async markDispatchFailure(draftId:string,dispatchId:string,errorCode:string){
    await this.prisma.$transaction([
      this.prisma.cmmsDispatch.update({where:{id:dispatchId},data:{finishedAt:new Date(),errorCode}}),
      this.prisma.cmmsDraft.update({where:{id:draftId},data:{status:CmmsDraftStatus.FAILED}})
    ]);
  }
}

function extractProviderRecordId(body: unknown): string | undefined {
  if (!body || typeof body !== "object") return undefined;
  const obj=body as Record<string,unknown>;
  for(const key of ["id","workOrderId","work_order_id","requestId"]){const value=obj[key];if(typeof value==="string"||typeof value==="number")return String(value);}
  return undefined;
}
