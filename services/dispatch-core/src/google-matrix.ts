import { z } from 'zod';
import { normalizeGoogleMatrix, type DispatchRequest } from './dispatch.js';
const Point = z.object({id:z.string().regex(/^[A-Za-z0-9_.:-]{1,100}$/),
 lat:z.number().min(-90).max(90),lng:z.number().min(-180).max(180)}).strict();
export type MatrixPoint = z.infer<typeof Point>;
/** Restricted server-only API key. Sequential batches cap each request at 100 elements.
 * API failure aborts automatic matching; cached/missing routes never become zero-distance legs.
 */
export async function googleMatrix(origins:readonly MatrixPoint[], destinations:readonly MatrixPoint[],
 apiKey:string, compliance:ReadonlyMap<string,{transitCountries:string[];approvedBorderDelaySeconds:number}>,
 signal?:AbortSignal):Promise<DispatchRequest['routes']>{
 if(!apiKey || origins.length>10000 || destinations.length>500 || origins.length*destinations.length>10000)
  throw new Error('Invalid matrix configuration or admission limit');
 origins.forEach(p=>Point.parse(p));destinations.forEach(p=>Point.parse(p));
 const result:DispatchRequest['routes']=[];
 const waypoint=(p:MatrixPoint)=>({waypoint:{location:{latLng:{latitude:p.lat,longitude:p.lng}}}});
 for(let i=0;i<origins.length;i+=10)for(let j=0;j<destinations.length;j+=10){
  const from=origins.slice(i,i+10),to=destinations.slice(j,j+10);
  const observedAt=Date.now();
  const response=await fetch('https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix',{
   method:'POST',redirect:'error',signal:signal?AbortSignal.any([signal,AbortSignal.timeout(8000)]):AbortSignal.timeout(8000),
   headers:{'Content-Type':'application/json','X-Goog-Api-Key':apiKey,
    'X-Goog-FieldMask':'originIndex,destinationIndex,status,condition,distanceMeters,duration'},
   body:JSON.stringify({origins:from.map(waypoint),destinations:to.map(waypoint),
    travelMode:'DRIVE',routingPreference:'TRAFFIC_AWARE_OPTIMAL'})});
  if(!response.ok)throw new Error('Matrix unavailable: '+response.status);
  const reader=response.body?.getReader();if(!reader)throw new Error('Empty matrix response');
  let size=0;let text='';const decoder=new TextDecoder();
  try{
   while(true){const chunk=await reader.read();if(chunk.done)break;
    size+=chunk.value.byteLength;if(size>1048576)throw new Error('Oversized matrix response');
    text+=decoder.decode(chunk.value,{stream:true});
   }
   text+=decoder.decode();
  }finally{await reader.cancel().catch(()=>undefined);reader.releaseLock();}
  const data:unknown=JSON.parse(text);
  result.push(...normalizeGoogleMatrix(data,from.map(p=>p.id),to.map(p=>p.id),observedAt,compliance));
 }
 return result;
}
