import { env } from 'cloudflare:workers';
import { snapshotSchema } from '@/lib/snapshot';
export const dynamic='force-dynamic';
const json=(data:unknown,status=200)=>Response.json(data,{status,headers:{'Cache-Control':'no-store'}});
// This shared club dataset is protected by the owner-private Sites access boundary.
// Service sync uses the platform's OAI-Sites-Authorization header. Do not make this Site public.
export async function GET(){
  if(!env.DB)return json({error:'Database unavailable'},503);
  const row=await env.DB.prepare('SELECT payload FROM analytics_snapshots WHERE id=1').first<{payload:string}>();
  return json(row?JSON.parse(row.payload):null);
}
export async function POST(request:Request){
  const origin=request.headers.get('origin');
  if(origin && origin!==new URL(request.url).origin)return json({error:'Cross-origin updates are not allowed'},403);
  const text=await request.text();
  if(text.length>10_000_000)return json({error:'Snapshot is too large'},413);
  let raw;try{raw=JSON.parse(text)}catch{return json({error:'Choose a valid JSON snapshot'},400)}
  const parsed=snapshotSchema.safeParse(raw);
  if(!parsed.success)return json({error:'This file is not a supported GWC analytics snapshot'},400);
  if(Date.parse(parsed.data.capturedAt)>Date.now()+300000)return json({error:'Snapshot time is in the future'},400);
  if(!env.DB)return json({error:'Database unavailable'},503);
  const result=await env.DB.prepare(`INSERT INTO analytics_snapshots(id,payload,captured_at) VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,captured_at=excluded.captured_at WHERE excluded.captured_at >= analytics_snapshots.captured_at`).bind(JSON.stringify(parsed.data),parsed.data.capturedAt).run();
  if(!result.meta.changes)return json({error:'A newer snapshot is already saved. Export the database again.'},409);
  return json({ok:true,capturedAt:parsed.data.capturedAt});
}
