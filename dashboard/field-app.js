/* Mobile-first local-only recording controller.
 * All raw positions remain in IndexedDB unless the owner exports them.
 * There is intentionally no remote write endpoint or authentication token. */
(function() {
'use strict';
const core=window.HabuFieldCore;
const $=id=>document.getElementById(id);
const DB='habu-field-local-v1', STORE='sessions';
let db=null, session=null, watchId=null, lastFix=null, saveQueue=Promise.resolve(), saveFailed=false;
function say(msg,kind) { const e=$('state'); e.textContent=msg; e.dataset.kind=kind||'normal'; }
function openDb(){
 return new Promise((resolve,reject)=>{
  if(!window.indexedDB){reject(Error('このブラウザはローカル保存に対応していません'));return;}
  const r=indexedDB.open(DB,1);
  r.onupgradeneeded=()=>{const d=r.result;if(!d.objectStoreNames.contains(STORE))d.createObjectStore(STORE,{keyPath:'id'});};
  r.onerror=()=>reject(r.error||Error('端末内DBを開けません'));
  r.onsuccess=()=>resolve(r.result);
 });
}
function put(value){
 return new Promise((resolve,reject)=>{
  const t=db.transaction(STORE,'readwrite');t.objectStore(STORE).put(value);
  t.oncomplete=()=>resolve();t.onabort=t.onerror=()=>reject(t.error||Error('端末への保存に失敗'));
 });
}
function all(){
 return new Promise((resolve,reject)=>{
  const t=db.transaction(STORE,'readonly'),req=t.objectStore(STORE).getAll();
  req.onsuccess=()=>resolve(req.result||[]);
  req.onerror=()=>reject(req.error||Error('記録の読み出しに失敗'));
 });
}
function persist(){
 if(!session)return saveQueue;
 const data=JSON.parse(JSON.stringify(session));
 saveQueue=saveQueue.then(()=>put(data)).catch(e=>{
  saveFailed=true;stopGps();
  say('端末保存エラー。新しい記録をやめて、記録一式を保存してください: '+e.message,'bad');
  setButtons();throw e;
 });
 return saveQueue;
}
function stopGps(){
 if(watchId!==null && navigator.geolocation){
  navigator.geolocation.clearWatch(watchId);watchId=null;
 }
 setButtons();
}
function stamp(){return new Date().toISOString();}
function gpsError(e){
 const map={1:'位置情報が許可されていません。ブラウザの許可設定を確認してください',
  2:'GPSを取得できません。空の軌跡は補完しません',3:'測位がタイムアウトしました。'};
 say('GPS: '+(map[e.code]||e.message),'warn');
 if(session&&session.status==='active'){core.markGap(session,stamp(),'GPSエラー');persist().catch(()=>{});}
}
function onFix(pos){
 if(!session||session.status!=='active')return;
 try{
  if(core.recordPoint(session,pos.coords,pos.timestamp)){
   const p=session.points[session.points.length-1];lastFix=p;
   $('gps').textContent='測位中 '+session.points.length+'点 / 精度 '+Math.round(p.accuracy)+'m';
   $('last').textContent='最終測位 '+core.clockJst(p.time);
   persist().catch(()=>{});
  }
 }catch(e){say('GPS測位を保留: '+e.message,'warn');}
}
function gpsStart(){
 if(!session||session.status!=='active'||saveFailed)return;
 if(!window.isSecureContext || !navigator.geolocation){
  say('GPSはHTTPSと位置情報の許可が必要です。', 'bad');return;
 }
 if(watchId!==null)return;
 if(session.points.length || session.gaps.length){
  core.markGap(session,stamp(),'GPS追跡の再開');
  persist().catch(()=>{});
 }
 watchId=navigator.geolocation.watchPosition(onFix,gpsError,{
  enableHighAccuracy:true,maximumAge:0,timeout:20000
 });
 say('GPS追跡を開始。アプリを前面にしたまま探索してください。','ok');
 setButtons();
}
function countByType(list,key){return list.filter(x=>x.type===key).length;}
function render(){
 const running=session&&session.status==='active';
 if(!session){
  $('session').textContent='探索記録なし';$('gps').textContent='GPS停止';
  $('last').textContent='';$('stats').textContent='記録がありません';
  $('events').replaceChildren();setButtons();return;
 }
 $('session').textContent=core.clockJst(session.startedAt)+'開始'+(session.endedAt?' / '+core.clockJst(session.endedAt)+'終了':' / 探索中');
 $('gps').textContent=(watchId===null?'GPS停止':'GPS追跡中')+' / 実測 '+session.points.length+'点';
 const last=session.points[session.points.length-1];
 $('last').textContent=last?'最終測位 '+core.clockJst(last.time)+'、精度 '+Math.round(last.accuracy)+'m':'GPS測位はまだありません';
 const nights=core.summary(session),captures=nights.reduce((n,x)=>n+x.ownerHabuCaptures,0);
 $('stats').textContent='ハブ本人捕獲 '+captures+'匹 / 目撃 '+countByType(session.events,'sighting')+'件 / 探索夜候補 '+nights.length+'夜 / GPS中断メモ '+session.gaps.length+'件';
 const list=$('events');list.replaceChildren();
 session.events.slice().reverse().forEach(e=>{
  const li=document.createElement('li');
  li.textContent=core.clockJst(e.time)+' '+({capture:'捕獲',sighting:'目撃',roadkill:'轢死',other:'その他'}[e.type])+
    ' '+e.species+' '+e.count+'匹'+(e.owner==='other'?'（他者）':'')+(e.position?' [GPS実測あり]':' [座標なし]');
  list.append(li);
 });
 setButtons();
}
function setButtons(){
 const has=!!session,active=has&&session.status==='active';
 $('start').disabled=active||saveFailed||!db;
 $('gpsStart').disabled=!active||watchId!==null||saveFailed;
 $('gpsStop').disabled=watchId===null;
 $('add').disabled=!active||saveFailed;
 $('stop').disabled=!active||saveFailed;
 $('gpxExport').disabled=!has;$('txtExport').disabled=!has;$('backup').disabled=!has;$('batchExport').disabled=!has||active||saveFailed;
 $('deleteWarning').hidden=active;
}
function download(filename,content,type){
 const blob=new Blob([content],{type});
 const url=URL.createObjectURL(blob),a=document.createElement('a');
 a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(url),10000);
}
function fileName(ext){return (session?core.night(session.startedAt):'unknown')+'_'+(session?session.id.slice(0,8):'none')+'.'+ext;}
function eventTimePosition(){
 if(!lastFix)return null;
 if(Date.now()-new Date(lastFix.time).getTime()>90000)return null;
 return lastFix;
}
function updateSelected(){
 if(!session)return;
 say('端末内の記録を選択しました。GPSは自動で再開しません。必要なら「GPS再開」を押してください。','warn');
 render();
}
function refreshSelect(){
 return all().then(rows=>{
  const host=$('saved');host.replaceChildren();
  const empty=document.createElement('option');empty.value='';empty.textContent='保存した探索を選択';host.append(empty);
  rows.sort((a,b)=>b.startedAt.localeCompare(a.startedAt));
  rows.forEach(x=>{
   const option=document.createElement('option');option.value=x.id;
   option.textContent=core.clockJst(x.startedAt)+' ('+(x.status==='active'?'未終了':'終了')+')';
   host.append(option);
  });
  if(session)host.value=session.id;
 });
}
async function init(){
 try{
  db=await openDb();
  await refreshSelect();
  const existing=await all();
  const active=existing.filter(x=>x.status==='active').sort((a,b)=>b.startedAt.localeCompare(a.startedAt));
  if(active.length===1){
   session=core.validateSession(active[0]);lastFix=session.points[session.points.length-1]||null;
   $('saved').value=session.id;render();
   say('未終了の探索記録を復元しました。GPSは自動再開しません。','warn');
  }else if(active.length>1){
   say('未終了の探索が複数あります。記録を選択して確認してください。','warn');
  }
  if(navigator.storage&&navigator.storage.persist){
   try{await navigator.storage.persist();}catch(e){/* best effort only */}
  }
  if(!active.length)say('端末内保存が使えます。記録一式のバックアップも定期的に保存してください。','ok');
  setButtons();
 }catch(e){say('ローカル保存を初期化できません: '+e.message,'bad');}
}
$('start').addEventListener('click',async()=>{
 if(session&&session.status==='active')return;
 try{
  session=core.createSession(core.generateId(),stamp());lastFix=null;saveFailed=false;
  await persist();await refreshSelect();render();
  say('探索開始を保存。GPSを開始するには「GPS開始」を押してください。','ok');
 }catch(e){say('探索開始に失敗: '+e.message,'bad');}
});
$('gpsStart').addEventListener('click',gpsStart);
$('gpsStop').addEventListener('click',()=>{
 if(session&&session.status==='active'){core.markGap(session,stamp(),'GPS手動停止');persist().catch(()=>{});}
 stopGps();say('GPS追跡を停止しました。探索自体は継続中です。','warn');
});
$('add').addEventListener('click',async()=>{
 if(!session||session.status!=='active'||saveFailed)return;
 try{
  const species=$('species').value==='other' ? $('speciesOther').value.trim() : $('species').value;
  const count=Number($('count').value);
  const e=core.event(session,{id:core.generateId(),time:stamp(),type:$('type').value,
   species,count,owner:$('owner').value,note:$('note').value,position:eventTimePosition()});
  await persist();$('note').value='';render();
  say(e.species+' '+e.count+'匹の観察記録を端末に保存。ダッシュボード確定集計には未登録です。','ok');
 }catch(e){say('観察の保存を停止: '+e.message,'bad');}
});
$('species').addEventListener('change',()=>{
 $('speciesOther').hidden=$('species').value!=='other';
});
$('stop').addEventListener('click',async()=>{
 if(!session||session.status!=='active'||saveFailed)return;
 if(!confirm('探索を終了しますか？ 未測位の区間は補完せず、記録を保存します。'))return;
 try{
  stopGps();core.stop(session,stamp());await persist();await refreshSelect();render();
  say('探索終了を保存。GPX・ログ・記録一式をエクスポートできます。','ok');
 }catch(e){say('終了保存に失敗: '+e.message,'bad');}
});
$('gpxExport').addEventListener('click',()=>{
 try{
  if(!session.points.length)say('GPS実測点が0件です。空の軌跡を出力します。','warn');
  download(fileName('gpx'),core.gpx(session),'application/gpx+xml;charset=utf-8');
 }catch(e){say('GPX保存エラー: '+e.message,'bad');}
});
$('txtExport').addEventListener('click',()=>{
 download(fileName('txt'),core.logfile(session),'text/plain;charset=utf-8');
});
$('backup').addEventListener('click',()=>{
 download(fileName('json'),core.exportBackup(session),'application/json;charset=utf-8');
 say('記録一式を端末にエクスポートしました。共有や保存場所の安全性に注意してください。','ok');
});

$('batchExport').addEventListener('click',async()=>{
 if(!session||session.status!=='stopped'||saveFailed)return;
 try{
  const resp=await fetch('./data/capture_summary.json?require_fresh=1',{cache:'no-store',credentials:'same-origin'});
  if(!resp.ok)throw Error('最新集計データを取得できません。');
  const summary=await resp.json();
  if(!summary||summary.schema_version!=='habu-capture-dashboard-v2'||!Array.isArray(summary.nights)||
    typeof summary.asof!=='string'||summary.privacy!=='AGGREGATE_ONLY_NO_COORDINATES')
    throw Error('既存集計の形式を確認できません');
  const known=new Set(summary.nights.map(x=>x.night));
  const candidates=core.summary(session).filter(x=>x.night>summary.asof&&!known.has(x.night));
  if(!candidates.length)throw Error('登録できる新規探索夜がありません。既存日付は照合・訂正経路へ');
  const requested=[];
  for(const n of candidates){
   const promptText=n.night+'の一晩全体で本人が捕獲したハブの確定数は？（このセッションの記録は'+
     n.ownerHabuCaptures+'匹。別の記録があれば含めて入力してください）';
   const answer=prompt(promptText,String(n.ownerHabuCaptures));
   if(answer===null)throw Error('確認を取り消しました');
   if(!/^\d{1,3}$/.test(answer.trim())||+answer>100)throw Error('0〜100の整数で入力してください');
   if(!confirm(n.night+'の探索あり・本人捕獲 '+Number(answer)+'匹で確定しますか？'))throw Error('確定を取り消しました');
   requested.push({night:n.night,classification:'新規候補',approved:true,searchConfirmed:true,confirmedCount:Number(answer)});
  }
  const input=new TextEncoder().encode(core.exportBackup(session));
  const sha=await crypto.subtle.digest('SHA-256',input);
  const digest=[...new Uint8Array(sha)].map(b=>b.toString(16).padStart(2,'0')).join('');
  const batch=window.HabuLogIntake.makeBatch(requested,summary.asof,[digest]);
  download('HABU_探索確定候補_'+core.night(session.startedAt)+'.json',
    JSON.stringify(batch,null,2)+'\n','application/json;charset=utf-8');
  say('捕獲数の確認用パッケージを保存。GitHubへの登録・同期はまだ行っていません。','ok');
 }catch(e){say('集計候補を出力しません: '+e.message,'warn');}
});
$('saved').addEventListener('change',async e=>{
 if(!e.target.value)return;
 if(session&&session.status==='active'&&session.id!==e.target.value){
  say('探索中の記録があります。先に終了してください。','warn');e.target.value=session.id;return;
 }
 try{
  const row=(await all()).find(s=>s.id===e.target.value);
  session=core.validateSession(row);lastFix=session.points[session.points.length-1]||null;
  stopGps();updateSelected();
 }catch(err){say('保存済みデータを開けません: '+err.message,'bad');}
});
$('restore').addEventListener('change',async e=>{
 const f=e.target.files[0];if(!f)return;
 try{
  if(f.size>30*1024*1024)throw Error('30MB以上のバックアップは取り扱えません');
  const restored=core.validateSession(JSON.parse(await f.text()));
  if(!/^[a-zA-Z0-9-]{16,90}$/.test(restored.id))throw Error('IDが不正');
  const exists=(await all()).find(x=>x.id===restored.id);
  if(exists){say('同じIDの記録はすでに端末にあります。上書きしません。','warn');return;}
  if(session&&session.status==='active')throw Error('現在の探索を終了してから復元してください');
  session=restored;lastFix=null;await persist();await refreshSelect();render();
  say('バックアップを復元。GPSは自動で再開しません。','ok');
 }catch(err){say('復元を拒否: '+err.message,'bad');}
 finally{e.target.value='';}
});
document.addEventListener('visibilitychange',()=>{
 if(document.visibilityState==='hidden'&&session&&session.status==='active'){
  core.markGap(session,stamp(),'バックグラウンド移行（連続GPS未保証）');persist().catch(()=>{});
 }else if(document.visibilityState==='visible'&&session&&session.status==='active'){
  say('画面に戻りました。バックグラウンド中のGPS記録は保証されません。必要なら追跡を再開してください。','warn');
 }
});
window.addEventListener('pagehide',()=>{
 if(session&&session.status==='active'){core.markGap(session,stamp(),'ページ終了・中断');persist().catch(()=>{});}
});

// An authenticated first online visit installs the field shell. Subsequent
// sessions can launch without connectivity. Raw GPS/log records stay in IndexedDB.
let offlineShellReady=false;
function showOfflineState(message,kind){
 const el=$('offlineState');if(!el)return;
 el.textContent=message;el.dataset.kind=kind||'warn';
}
function connectivityStatus(){
 const networkHint=navigator.onLine===false?'圏外/通信なしの可能性：':'通信状態は保証されません：';
 if(offlineShellReady){
  showOfflineState(networkHint+'オフライン起動用の画面を保存済み。探索ログ・GPXは端末だけで作成できます。','ok');
 }else{
  showOfflineState(networkHint+'オフライン起動の準備がまだ確認できません。電波がある場所でこの画面を開き直してください。','warn');
 }
}
async function prepareOfflineShell(){
 if(!window.isSecureContext||!('serviceWorker' in navigator)){
  showOfflineState('オフライン起動にはHTTPSと対応ブラウザが必要です。','bad');
  return;
 }
 try{
  const reg=await navigator.serviceWorker.register('./sw.js',{scope:'./'});
  const ready=await navigator.serviceWorker.ready;
  const worker=ready.active||reg.active;
  if(!worker)throw Error('オフライン用の画面がまだ有効ではありません');
  const status=await new Promise((resolve,reject)=>{
   const channel=new MessageChannel();
   const timeout=setTimeout(()=>reject(Error('確認がタイムアウト')),8000);
   channel.port1.onmessage=e=>{
    clearTimeout(timeout);channel.port1.close();resolve(e.data);
   };
   worker.postMessage({type:'HABU_FIELD_OFFLINE_STATUS'},[channel.port2]);
  });
  offlineShellReady=status?.type==='HABU_FIELD_OFFLINE_STATUS'&&status.ready===true;
  connectivityStatus();
 }catch(e){
  offlineShellReady=false;
  showOfflineState('オフライン起動の準備を確認できません: '+e.message,'warn');
 }
}
window.addEventListener('online',()=>{connectivityStatus();prepareOfflineShell();});
window.addEventListener('offline',connectivityStatus);
if('serviceWorker' in navigator){
 navigator.serviceWorker.addEventListener('controllerchange',()=>{prepareOfflineShell();});
}
prepareOfflineShell();

init();
})();