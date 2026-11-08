/* Completed-session sync to the SAME authenticated private API used by intake.html.
 * Fail closed on static-only Pages: authenticate/validate status BEFORE sending bytes.
 * The on-device consent and receipts use separate IndexedDB stores; never localStorage.
 * This does not create a server, background service, or source-qualified model evidence. */
(function(){
'use strict';
const $=id=>document.getElementById(id);
if(!$('syncToggle')||!window.HabuFieldCore)return;
const core=window.HabuFieldCore;
const PER_FILE=12*1024*1024;
let syncDb=null,consent=false,working=false,pendingConfirmation=null,initialized=false;
function display(message,kind='warn'){
 const el=$('syncState');if(!el)return;
 el.textContent=message;el.dataset.kind=kind;
}
function openDb(name,version,upgrade){
 return new Promise((resolve,reject)=>{
  if(!window.indexedDB){reject(Error('端末の保存機能が利用できません'));return;}
  const r=indexedDB.open(name,version);
  r.onupgradeneeded=()=>{if(upgrade)upgrade(r.result);};
  r.onerror=()=>reject(r.error||Error('端末DBを開けません'));
  r.onsuccess=()=>resolve(r.result);
 });
}
function get(db,store,id){
 return new Promise((resolve,reject)=>{
  const tx=db.transaction(store,'readonly'),req=tx.objectStore(store).get(id);
  req.onsuccess=()=>resolve(req.result||null);
  req.onerror=()=>reject(req.error||Error('同期情報を読めません'));
 });
}
function getAll(db,store){
 return new Promise((resolve,reject)=>{
  const tx=db.transaction(store,'readonly'),req=tx.objectStore(store).getAll();
  req.onsuccess=()=>resolve(req.result||[]);
  req.onerror=()=>reject(req.error||Error('探索情報を読めません'));
 });
}
function put(db,store,value){
 return new Promise((resolve,reject)=>{
  const tx=db.transaction(store,'readwrite');
  tx.oncomplete=()=>resolve();
  tx.onabort=tx.onerror=()=>reject(tx.error||Error('同期情報を保存できません'));
  tx.objectStore(store).put(value);
 });
}
function endpoint(path){
 const url=new URL(path,document.baseURI);
 if(url.origin!==location.origin||url.protocol!=='https:')
  throw Error('私有サーバー以外には送信できません');
 return url.href;
}
async function request(path,body){
 const url=endpoint(path);
 const response=await fetch(url,{method:body?'POST':'GET',
  credentials:'same-origin',redirect:'error',cache:'no-store',
  headers:body?{'Content-Type':'application/json'}:{},
  body:body?JSON.stringify(body):undefined});
 if(!response||!response.ok||response.redirected||
    !/application\/json/i.test(response.headers.get('content-type')||''))
  throw Error('私有サーバー未接続');
 return await response.json();
}
async function status(){
 const s=await request('./api/private-intake/status');
 if(!s||s.schema_version!=='habu-private-dashboard-status-v1'||
    s.mode!=='PRIVATE_DURABLE_STORE'||!Number.isSafeInteger(s.revision)||
    typeof s.asof!=='string')throw Error('認証済み私有サーバーを確認できません');
 return s;
}
async function verifySummary(){
 const data=await request('./data/capture_summary.json?require_fresh=1');
 if(data.schema_version!=='habu-capture-dashboard-v2'||!Array.isArray(data.nights)||
    data.privacy!=='AGGREGATE_ONLY_NO_COORDINATES')throw Error('集計読み戻し形式が不正');
 return data;
}
function b64(bytes){
 let result='';
 for(let i=0;i<bytes.length;i+=32768)
  result+=String.fromCharCode(...bytes.subarray(i,i+32768));
 return btoa(result);
}
function prepareFiles(s){
 // The trailing human-readable footer is a local display note, not an
 // observed time-stamped event and would otherwise cause a parser hold.
 const txt=core.logfile(s);
 const marker='\n---\n',idx=txt.lastIndexOf(marker);
 if(idx<0)throw Error('ハブログの検証形式が不正');
 const log=new TextEncoder().encode(txt.slice(0,idx)+'\n');
 const files=[{kind:'log',content_b64:b64(log)}];
 if(s.points.length){
  const gpx=new TextEncoder().encode(core.gpx(s));
  if(gpx.byteLength>PER_FILE)throw Error('GPXが12MiBを超えます。端末から原本を保存してください');
  files.push({kind:'gpx',content_b64:b64(gpx)});
 }
 if(log.byteLength>PER_FILE)throw Error('ハブログが12MiBを超えます。端末から保存してください');
 return files;
}
function eligible(session){
 return session&&session.schema_version==='habu-field-session-v1'&&session.status==='stopped'&&
    typeof session.endedAt==='string';
}
async function loadSessions(){
 const source=await openDb('habu-field-local-v1',1);
 try{return await getAll(source,'sessions');}
 finally{source.close();}
}
async function updateQueue(){
 const records=await getAll(syncDb,'receipts');
 const ready=records.filter(r=>r.state==='ARCHIVED');
 pendingConfirmation=ready.sort((a,b)=>b.stoppedAt.localeCompare(a.stoppedAt))[0]||null;
 $('syncConfirm').disabled=!consent||working||!pendingConfirmation;
}
async function syncNow(){
 if(!initialized||!consent||working)return;
 if(navigator.onLine===false){display('圏外：端末保存のみ。通信復帰時に再試行します。');return;}
 working=true;$('syncNow').disabled=true;$('syncConfirm').disabled=true;
 try{
  await status(); // No raw bytes or GPS generated until trusted private service responds.
  const sessions=(await loadSessions()).filter(eligible)
    .sort((a,b)=>b.startedAt.localeCompare(a.startedAt)).slice(0,8);
  let uploaded=0,held=0;
  for(const s of sessions){
   let prev=await get(syncDb,'receipts',s.id);
   if(prev&&(prev.state==='ARCHIVED'||prev.state==='APPLIED'||prev.state==='HELD'))continue;
   // Check the stored session fully before serializing private GPS into a request.
   core.validateRestoredSession(s);
   const result=await request('./api/private-intake/prepare',
                            {files:prepareFiles(s),channel:'dashboard'});
   if(!result||!['READY_FOR_CONFIRMATION','HELD','APPLIED'].includes(result.state)||
      !/^[a-f0-9]{64}$/.test(result.receipt_id||''))throw Error('取込受付結果が不正');
   prev={id:s.id,stoppedAt:s.endedAt,revision:s.revision,
     receipt_id:result.receipt_id,state:result.state==='READY_FOR_CONFIRMATION'?'ARCHIVED':result.state,
     prepared:result.state==='READY_FOR_CONFIRMATION'?result:null};
   await put(syncDb,'receipts',prev);
   if(prev.state==='HELD')held++;else uploaded++;
  }
  if(uploaded||held)display('私有原本受付：'+uploaded+'件 / 要照合：'+held+'件。集計への反映は別途確認。','ok');
  else display('新規送信はありません。確定集計の確認待ち、または端末内に保存済み。','ok');
 }catch(error){
  display('自動同期は未接続：端末の記録は保持。'+String(error.message)+'。','warn');
 }finally{
  working=false;$('syncNow').disabled=!consent;
  await updateQueue().catch(()=>{});
 }
}
async function confirmNight(){
 if(working||!consent||!pendingConfirmation)return;
 const receipt=pendingConfirmation;working=true;
 $('syncConfirm').disabled=true;$('syncNow').disabled=true;
 try{
  const s=(await loadSessions()).find(row=>row.id===receipt.id);
  if(!eligible(s))throw Error('対象の探索原本を確認できません');
  const p=receipt.prepared,server=await status();
  // With a saved pendingBatch, a lost acknowledgement must be retried byte-for-byte.
  // Revision may have advanced because the first apply actually committed.
  if(!receipt.pendingBatch&&(server.revision!==p.revision||server.asof!==p.asof))
    throw Error('集計の版が更新されています。旧版に上書きできません');
  const candidates=p.nights.filter(n=>n.night>p.asof);
  if(!candidates.length)throw Error('新規集計日がありません。過去日の訂正は別途照合が必要です');
  const observations=new Map(core.summary(s).map(row=>[row.night,row.ownerHabuCaptures]));
  const entries=[];
  if(!receipt.pendingBatch)for(const n of candidates){
   const current=observations.get(n.night)||0;
   const answer=prompt(n.night+'の探索夜全体で、本人が捕獲したハブの確定匹数は？（本端末の記録：'+current+'匹）',String(current));
   if(answer===null){display('確認を取り消しました。原本の受付状態は保持しています。');return;}
   if(!/^\d{1,3}$/.test(answer.trim())||Number(answer)>100)
    throw Error('0〜100の整数のみ入力してください');
   entries.push({night:n.night,classification:'新規候補',
                 approved:true,searchConfirmed:true,confirmedCount:Number(answer)});
  }
  if(!receipt.pendingBatch){
   if(!confirm('対象の探索夜すべてを照合済みですか？ 本人捕獲数を確定集計へ反映しますか？')){
    display('集計反映を取り消しました。原本は私有受付済みです。');return;
   }
   receipt.pendingBatch=window.HabuLogIntake.makeBatch(entries,p.asof,p.source_sha256);
   // Persist the exact request before network submission so an acknowledgment
   // loss can retry the same request without silently changing the counts.
   await put(syncDb,'receipts',receipt);
  }
  const batch=receipt.pendingBatch;
  const applied=await request('./api/private-intake/apply',
    {receipt_id:receipt.receipt_id,batch,expected_revision:p.revision});
  const latest=await status(),summary=await verifySummary();
  if(applied.state!=='APPLIED'||latest.revision<applied.revision||
     summary.asof<candidates[candidates.length-1].night)
    throw Error('集計更新後の読み戻しが不一致');
  receipt.state='APPLIED';receipt.appliedRevision=applied.revision;
  delete receipt.pendingBatch;
  await put(syncDb,'receipts',receipt);
  display('原本同期・確定集計の読み戻し成功。累計'+summary.total+'匹、保存版'+applied.revision,'ok');
 }catch(error){
  display('確定集計は未完了：'+String(error.message)+'。原本と確認内容を端末に保持。','bad');
 }finally{
  working=false;$('syncNow').disabled=!consent;
  await updateQueue().catch(()=>{});
 }
}
async function init(){
 try{
  syncDb=await openDb('habu-field-sync-v1',1,db=>{
   if(!db.objectStoreNames.contains('receipts'))db.createObjectStore('receipts',{keyPath:'id'});
   if(!db.objectStoreNames.contains('meta'))db.createObjectStore('meta',{keyPath:'id'});
  });
  consent=(await get(syncDb,'meta','consent'))?.value===true;
  $('syncToggle').checked=consent;initialized=true;await updateQueue();
  if(consent)syncNow();
  else display('自動同期は未設定。端末内保存だけが有効です。');
 }catch(error){display('同期設定を読み出せません。端末の原本をバックアップしてください。','bad');}
}
$('syncToggle').addEventListener('change',async()=>{
 if(!syncDb){$('syncToggle').checked=false;return;}
 try{
  await put(syncDb,'meta',{id:'consent',value:$('syncToggle').checked});
  consent=$('syncToggle').checked;await updateQueue();
  if(consent)syncNow();
  else display('自動同期を停止しました。端末内記録は削除しません。');
 }catch(_){$('syncToggle').checked=consent;display('同期設定を保存できません。','bad');}
});
$('syncNow').addEventListener('click',()=>syncNow());
$('syncConfirm').addEventListener('click',()=>confirmNight());
window.addEventListener('online',()=>syncNow());
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')syncNow();});
window.HabuFieldSync={notifyStop:()=>{syncNow();}};
init();
})();
