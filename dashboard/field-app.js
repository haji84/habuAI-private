/* Mobile-first local-only recording controller.
 * All raw positions remain in IndexedDB unless the owner exports them.
 * There is intentionally no remote write endpoint or authentication token. */
(function() {
'use strict';
const core=window.HabuFieldCore;
const $=id=>document.getElementById(id);
const DB='habu-field-local-v1', STORE='sessions';
let db=null, session=null, watchId=null, lastFix=null, saveQueue=Promise.resolve(), saveFailed=false;
let saveState=null, pendingSaves=0;
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
function storedRevision(value){
 const revision=value.revision===undefined?0:value.revision;
 if(!Number.isSafeInteger(revision)||revision<0||revision>=Number.MAX_SAFE_INTEGER)
  throw Error('保存版の番号を確認できません。記録一式を保存してください');
 return revision;
}
function observeSession(isNew=false){
 session.revision=storedRevision(session);
 saveState={session,revision:isNew?null:session.revision};
}
function put(value,expectedRevision){
 return new Promise((resolve,reject)=>{
  const t=db.transaction(STORE,'readwrite'),store=t.objectStore(STORE);
  let failure=null,nextRevision;
  t.oncomplete=()=>resolve(nextRevision);
  t.onabort=t.onerror=()=>reject(failure||t.error||Error('端末への保存に失敗'));
  // The comparison and write share one serialized IDB transaction. The token
  // is the last committed version observed by this tab, never the incoming
  // session's mutation counter. null means a new/imported ID must be absent.
  const request=store.get(value.id);
  request.onsuccess=()=>{
   try{
    const current=request.result;
    if(expectedRevision===null ? current!==undefined :
       current===undefined||storedRevision(current)!==expectedRevision)
     throw Error('別の画面で更新された記録があります。上書きせず停止しました。この画面の未保存分を記録一式で保存してください');
    nextRevision=expectedRevision===null?1:expectedRevision+1;
    value.revision=nextRevision;store.put(value);
   }catch(e){failure=e;t.abort();}
  };
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
 if(!session||saveFailed)return saveQueue;
 const data=JSON.parse(JSON.stringify(session)),state=saveState;
 pendingSaves++;setButtons();
 saveQueue=saveQueue.then(()=>put(data,state.revision)).then(revision=>{
  state.revision=revision;
  if(session===state.session)session.revision=Math.max(session.revision,revision);
 }).catch(e=>{
  saveFailed=true;stopGps();
  say('端末保存エラー。新しい記録をやめて、記録一式を保存してください: '+e.message,'bad');
  setButtons();throw e;
 }).finally(()=>{pendingSaves--;setButtons();});
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
 if(saveFailed)return;
 const map={1:'位置情報が許可されていません。ブラウザの許可設定を確認してください',
  2:'GPSを取得できません。空の軌跡は補完しません',3:'測位がタイムアウトしました。'};
 say('GPS: '+(map[e.code]||e.message),'warn');
 if(session&&session.status==='active'){core.markGap(session,stamp(),'GPSエラー');persist().catch(()=>{});}
}
function onFix(pos){
 if(!session||session.status!=='active'||saveFailed)return;
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
 $('stats').textContent='ハブ本人捕獲 '+captures+'匹 / 目撃 '+countByType(session.events,'sighting')+'件 / 探索夜候補 '+nights.length+'夜 / GPS中断メモ '+session.gaps.length+'件 / 環境記録 '+(session.conditions||[]).length+'件';
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
 $('start').disabled=active||saveFailed||pendingSaves>0||!db;
 $('gpsStart').disabled=!active||watchId!==null||saveFailed;
 $('gpsStop').disabled=watchId===null;
 $('add').disabled=!active||saveFailed;
 $('stop').disabled=!active||saveFailed;
 $('gpxExport').disabled=!has;$('txtExport').disabled=!has;$('backup').disabled=!has;$('batchExport').disabled=!has||active||saveFailed;
 $('shareHabuFiles').disabled=!has||active||saveFailed||pendingSaves>0;
 $('deleteWarning').hidden=active;
 $('saved').disabled=active||saveFailed||pendingSaves>0;
 $('restore').disabled=active||saveFailed||pendingSaves>0;
 const conditionDisabled=!active||saveFailed||pendingSaves>0;
 if(typeof document.querySelectorAll==='function')
  for(const button of document.querySelectorAll('[data-condition-category]'))button.disabled=conditionDisabled;
 const tempSave=$('recordTemperature');
 if(tempSave)tempSave.disabled=conditionDisabled;
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
   observeSession();
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
 if(saveFailed||pendingSaves||session&&session.status==='active')return;
 try{
  session=core.createSession(core.generateId(),stamp());lastFix=null;saveFailed=false;
  observeSession(true);
  await persist();await refreshSelect();render();
  say('探索開始を保存。GPSを開始するには「GPS開始」を押してください。','ok');
 }catch(e){say('探索開始に失敗: '+e.message,'bad');}
});
$('gpsStart').addEventListener('click',gpsStart);
$('gpsStop').addEventListener('click',()=>{
 if(saveFailed)return;
 if(session&&session.status==='active'){core.markGap(session,stamp(),'GPS手動停止');persist().catch(()=>{});}
 stopGps();say('GPS追跡を停止しました。探索自体は継続中です。','warn');
});
$('add').addEventListener('click',async()=>{
 if(!session||session.status!=='active'||saveFailed)return;
 try{
  const species=$('species').value==='other' ? $('speciesOther').value.trim() : $('species').value;
  const count=Number($('count').value);
  const observed=$('observedAt');
  const uncertainty=$('timeUncertainty');
  let observation;
  if(observed.value||uncertainty.value||observed.validity?.badInput||uncertainty.validity?.badInput) {
   if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/.test(observed.value)||
     observed.validity?.badInput||!uncertainty.value||uncertainty.validity?.badInput)
    throw Error('観測時刻と時刻の誤差は両方入力してください');
   const jstTime=observed.value.length===16 ? observed.value+':00' : observed.value;
   observation={observed_at:jstTime+'+09:00',uncertainty_seconds:Number(uncertainty.value)};
  }
  const e=core.event(session,{id:core.generateId(),time:stamp(),type:$('type').value,
   species,count,owner:$('owner').value,note:$('note').value,position:eventTimePosition(),observation});
  await persist();
  $('note').value='';observed.value='';uncertainty.value='';render();
  say(e.species+' '+e.count+'匹の観察記録を端末に保存。ダッシュボード確定集計には未登録です。','ok');
  if(window.HabuFieldQuick&&typeof window.HabuFieldQuick.ack==='function')
    window.HabuFieldQuick.ack(true,e.species+' '+e.count+'匹');
 }catch(e){
  say('観察の保存を停止: '+e.message,'bad');
  if(window.HabuFieldQuick&&typeof window.HabuFieldQuick.ack==='function')
    window.HabuFieldQuick.ack(false,e.message);
 }
});
// First-class condition observations, separate from biological sightings/captures.
// No external weather API or phone-temperature guess is used here.
function showCondition(message,kind='normal'){
 const el=$('conditionState');if(!el)return;
 el.textContent=message;el.dataset.kind=kind;
}
async function saveCondition(category,value,label){
 if(!session||session.status!=='active'||saveFailed||pendingSaves>0){
  showCondition('探索中の保存可能な状態で入力してください。','bad');return;
 }
 try{
  const added=core.recordCondition(session,{time:stamp(),category,value});
  if(!added){showCondition('同じ時刻に同じ状態が保存済みです。','warn');return;}
  await persist();
  render();
  showCondition(label+'：観察時刻とともに端末保存済み。ダッシュボード同期とは別です。','ok');
 }catch(error){showCondition('環境記録を保存できません: '+error.message,'bad');}
}
if(typeof document.querySelectorAll==='function'){
 for(const button of document.querySelectorAll('[data-condition-category]')){
  button.addEventListener('click',()=>{
   saveCondition(button.dataset.conditionCategory,button.dataset.conditionValue,
                 button.textContent.trim());
  });
 }
}
$('recordTemperature').addEventListener('click',()=>{
 const raw=$('airTemperatureC').value.trim();
 if(raw===''||!/^-?\\d{1,2}(?:\\.\\d{1,2})?$/.test(raw)){
  showCondition('温度計で測った気温だけ入力してください。未測定なら空欄でOK。','bad');return;
 }
 const c=Number(raw);
 saveCondition('air_temperature',c,c+'℃（実測）');
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
  if(window.HabuFieldSync&&typeof window.HabuFieldSync.notifyStop==='function')
    window.HabuFieldSync.notifyStop();
 }catch(e){say('終了保存に失敗: '+e.message,'bad');}
});
$('shareHabuFiles').addEventListener('click',async()=>{
 if(!session||session.status!=='stopped'||saveFailed||pendingSaves)return;
 try{
  if(typeof File!=='function'||!navigator.share)throw Error('端末のファイル共有に未対応です。個別保存を使ってください');
  const files=[
   new File([core.logfile(session)],fileName('txt'),{type:'text/plain'}),
   new File([core.gpx(session)],fileName('gpx'),{type:'application/gpx+xml'})
  ];
  if(navigator.canShare&&!navigator.canShare({files}))throw Error('この端末では複数ファイルの共有に対応していません');
  await navigator.share({files,title:'HABU FIELD ハブログとGPX'});
  say('共有画面を閉じました。受信先での保存成功は別途確認してください。','warn');
 }catch(e){
  if(e&&e.name==='AbortError')return;
  say('共有未完了: '+e.message+'。ハブログとGPXを個別保存できます。','warn');
 }
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
  try{
   download(fileName('json'),core.exportBackup(session),'application/json;charset=utf-8');
   say('記録一式を端末にエクスポートしました。共有や保存場所の安全性に注意してください。','ok');
  }catch(e){say('記録一式を出力しません: '+e.message,'warn');}
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
 if(saveFailed||pendingSaves){
  say(saveFailed?'未保存の記録があります。先に記録一式を保存してください。':'端末への保存完了を待ってください。','bad');
  e.target.value=session?session.id:'';return;
 }
 if(session&&session.status==='active'){
  say('探索中の記録があります。先に終了してください。','warn');e.target.value=session.id;return;
 }
 try{
  const row=(await all()).find(s=>s.id===e.target.value);
  if(saveFailed||pendingSaves)throw Error('未保存の記録があるため切り替えません');
  session=core.validateSession(row);lastFix=session.points[session.points.length-1]||null;
  observeSession();
  stopGps();updateSelected();
 }catch(err){say('保存済みデータを開けません: '+err.message,'bad');}
});
$('restore').addEventListener('change',async e=>{
 const f=e.target.files[0];if(!f)return;
 try{
  if(saveFailed||pendingSaves)throw Error('未保存の記録があります。先に記録一式を保存してください');
  if(f.size>core.MAX_BACKUP_BYTES)throw Error('30MBを超えるバックアップは取り扱えません');
  const restored=core.validateRestoredSession(JSON.parse(await f.text()));
  if(!/^[a-zA-Z0-9-]{16,90}$/.test(restored.id))throw Error('IDが不正');
  const exists=(await all()).find(x=>x.id===restored.id);
  if(exists){say('同じIDの記録はすでに端末にあります。上書きしません。','warn');return;}
  if(saveFailed||pendingSaves)throw Error('未保存の記録があるため復元しません');
  if(session&&session.status==='active')throw Error('現在の探索を終了してから復元してください');
  session=restored;lastFix=null;observeSession(true);await persist();await refreshSelect();render();
  say('バックアップを復元。GPSは自動で再開しません。','ok');
 }catch(err){say('復元を拒否: '+err.message,'bad');}
 finally{e.target.value='';}
});
document.addEventListener('visibilitychange',()=>{
 if(document.visibilityState==='hidden'&&session&&session.status==='active'&&!saveFailed){
  core.markGap(session,stamp(),'バックグラウンド移行（連続GPS未保証）');persist().catch(()=>{});
 }else if(document.visibilityState==='visible'&&session&&session.status==='active'&&!saveFailed){
  say('画面に戻りました。バックグラウンド中のGPS記録は保証されません。必要なら追跡を再開してください。','warn');
 }
});
window.addEventListener('pagehide',()=>{
 if(session&&session.status==='active'&&!saveFailed){core.markGap(session,stamp(),'ページ終了・中断');persist().catch(()=>{});}
});

// An authenticated first online visit installs the field shell. Subsequent
// sessions can launch without connectivity. Raw GPS/log records stay in IndexedDB.
let offlineShellReady=false;
let offlinePreparation=null;
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
 if(offlinePreparation)offlinePreparation.cancel();
 if(!window.isSecureContext||!('serviceWorker' in navigator)){
  showOfflineState('オフライン起動にはHTTPSと対応ブラウザが必要です。','bad');
  return;
 }
 let channel,timer;
 const attempt={active:true,cancel:null};
 const current=()=>offlinePreparation===attempt&&attempt.active;
 const ensureCurrent=()=>{if(!current())throw Error('準備処理が更新されました');};
 const cancelled=new Promise((resolve,reject)=>{
  attempt.cancel=()=>{attempt.active=false;reject(Error('オフライン準備がタイムアウトまたは更新されました'));};
 });
 offlinePreparation=attempt;
 // One deadline covers registration, never-rejecting ready, and status reply.
 timer=setTimeout(attempt.cancel,8000);
 try{
  const status=await Promise.race([cancelled,(async()=>{
   const reg=await navigator.serviceWorker.register('./sw.js',{scope:'./'});
   ensureCurrent();
   const ready=await navigator.serviceWorker.ready;
   ensureCurrent();
   const worker=ready.active||reg.active;
   if(!worker)throw Error('オフライン用の画面がまだ有効ではありません');
   return await new Promise((resolve,reject)=>{
    channel=new MessageChannel();
    channel.port1.onmessage=e=>{if(current())resolve(e.data);};
    worker.postMessage({type:'HABU_FIELD_OFFLINE_STATUS'},[channel.port2]);
   });
  })()]);
  ensureCurrent();
  offlineShellReady=status?.type==='HABU_FIELD_OFFLINE_STATUS'&&status.ready===true;
  connectivityStatus();
 }catch(e){
  if(offlinePreparation===attempt){
   offlineShellReady=false;
   showOfflineState('オフライン起動の準備を確認できません: '+e.message,'warn');
  }
 }finally{
  clearTimeout(timer);attempt.active=false;
  if(channel){
   channel.port1.onmessage=null;
   for(const port of [channel.port1,channel.port2]){try{port.close();}catch{}}
  }
  if(offlinePreparation===attempt)offlinePreparation=null;
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
