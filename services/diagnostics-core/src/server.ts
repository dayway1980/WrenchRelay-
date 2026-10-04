import "dotenv/config";
import { createHmac, timingSafeEqual } from "node:crypto";
import express, { type NextFunction, type Request, type Response } from "express";
import pino from "pino";
import { PrismaClient } from "./generated/prisma/client.js";
import { analyzeIntake, IntakeSchema } from "./diagnostics.js";
import { CmmsBridge, EnvironmentSecretResolver, PrepareDraftSchema } from "./cmmsBridge.js";
import { persistDiagnosticAnalysis } from "./persistence.js";

const logger=pino({level:process.env.LOG_LEVEL??"info"});
const app=express();app.disable("x-powered-by");app.use(express.json({limit:"1mb"}));
const production=process.env.NODE_ENV==="production",gatewaySecret=process.env.WR_GATEWAY_HMAC_SECRET;
const allowUnsignedDev=process.env.WR_ALLOW_UNSIGNED_DEV==="true"&&!production;
if(production&&(!gatewaySecret||gatewaySecret.length<32))throw new Error("WR_GATEWAY_HMAC_SECRET with at least 32 characters is required in production.");

type Principal={tenantId:string;userId:string;role:string};
declare global { namespace Express { interface Request { wrenchrelayPrincipal?: Principal } } }
function constantTimeEqual(a:string,b:string){const aa=Buffer.from(a),bb=Buffer.from(b);return aa.length===bb.length&&timingSafeEqual(aa,bb);}
function authenticate(req:Request,res:Response,next:NextFunction){
  const tenantId=req.header("x-wrenchrelay-tenant-id"),userId=req.header("x-wrenchrelay-user-id"),role=req.header("x-wrenchrelay-role")??"technician",timestamp=req.header("x-wrenchrelay-auth-timestamp"),signature=req.header("x-wrenchrelay-auth-signature");
  if(allowUnsignedDev&&tenantId&&userId){req.wrenchrelayPrincipal={tenantId,userId,role};return next();}
  if(!gatewaySecret||!tenantId||!userId||!timestamp||!signature)return res.status(401).json({error:"Authenticated WrenchRelay gateway headers are required."});
  const epoch=Number(timestamp);if(!Number.isFinite(epoch)||Math.abs(Date.now()-epoch)>5*60_000)return res.status(401).json({error:"Authentication timestamp is stale."});
  const canonical=[tenantId,userId,role,timestamp,req.method.toUpperCase(),req.path].join("."),expected=createHmac("sha256",gatewaySecret).update(canonical).digest("hex");
  if(!constantTimeEqual(expected,signature))return res.status(401).json({error:"Invalid gateway signature."});
  req.wrenchrelayPrincipal={tenantId,userId,role};next();
}
function requireHumanWriteRole(req:Request,res:Response,next:NextFunction){
  const role=req.wrenchrelayPrincipal?.role;
  if(!role||!["technician","supervisor","admin"].includes(role))return res.status(403).json({error:"A human technician/supervisor/admin role is required."});
  next();
}
const prisma=new PrismaClient();
const publicBaseUrl=process.env.WR_PUBLIC_BASE_URL??`http://localhost:${process.env.PORT??"8787"}`;
const bridge=new CmmsBridge(prisma,new EnvironmentSecretResolver(),publicBaseUrl);

app.get("/healthz",(_req,res)=>res.json({ok:true,service:"wrenchrelay-diagnostics-core",version:"0.1.0",directCmmsWriteAllowedFromAi:false}));
app.post("/v1/intake/analyze",authenticate,async(req,res,next)=>{try{
  const p=req.wrenchrelayPrincipal!,parsed=IntakeSchema.parse({...req.body,tenantId:p.tenantId,actorExternalId:p.userId});
  const result=analyzeIntake(parsed);
  await persistDiagnosticAnalysis(prisma,{tenantId:p.tenantId,tenantExternalKey:p.tenantId,actorExternalId:p.userId,workspace:parsed.workspace,analysis:result});
  res.status(200).json({...result,provenanceLedgerPersisted:true});
}catch(e){next(e);}});
app.post("/v1/cmms/prepare",authenticate,requireHumanWriteRole,async(req,res,next)=>{try{
  const p=req.wrenchrelayPrincipal!,parsed=PrepareDraftSchema.parse({...req.body,tenantId:p.tenantId,actorExternalId:p.userId});
  res.status(201).json(await bridge.prepare(parsed));
}catch(e){next(e);}});
app.post("/v1/cmms/:draftId/decision",authenticate,requireHumanWriteRole,async(req,res,next)=>{try{
  const p=req.wrenchrelayPrincipal!;res.status(200).json({ok:true,approval:await bridge.decide(p.tenantId,req.params.draftId,{...req.body,actorExternalId:p.userId})});
}catch(e){next(e);}});
app.post("/v1/cmms/:draftId/dispatch",authenticate,requireHumanWriteRole,async(req,res,next)=>{try{
  const p=req.wrenchrelayPrincipal!;res.status(200).json({ok:true,dispatch:await bridge.dispatch(p.tenantId,req.params.draftId,p.userId)});
}catch(e){next(e);}});
app.use((error:unknown,_req:Request,res:Response,_next:NextFunction)=>{const message=error instanceof Error?error.message:"Unknown error";logger.error({err:error},"request failed");const validation=typeof error==="object"&&error!==null&&"issues" in error;res.status(validation?422:400).json({error:message});});
const port=Number(process.env.PORT??"8787"),server=app.listen(port,"0.0.0.0",()=>logger.info({port},"WrenchRelay diagnostics core listening"));
async function shutdown(signal:string){logger.info({signal},"shutting down");server.close(async()=>{await prisma.$disconnect();process.exit(0);});}
process.on("SIGTERM",()=>void shutdown("SIGTERM"));process.on("SIGINT",()=>void shutdown("SIGINT"));
