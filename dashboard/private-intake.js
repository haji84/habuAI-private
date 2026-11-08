/* Private adapter only. No raw data, credentials or receipts in localStorage. */
(function(){
'use strict';
const $=id=>document.getElementById(id);
async function call(path,body){
 const response=await fetch('./api/private-intake/'+path,{method:body?'POST':'GET',credentials:'same-origin',cache:'no-store',redirect:'error',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});
 const value=await response.json();if(!response.ok)throw Error(value.reason||'接続エラー');return value;
}
if(!$('files')){
 let revision=null;
 const refresh=async()=>{if(document.hidden)return;try{const state=await call('status');if(revision!==null&&revision!==state.revision)$('reloadBtn')?.click();revision=state.revision;}catch(_){/* Do not label a failed poll as synchronized. */}};
 refresh();setInterval(refresh,30000);document.addEventListener('visibilitychange',refresh);return;
}
let prepared=null, summary=null, rows=[], epoch=0, busy=false, retryRequest=null;
const messages={GPX_LOG_NIGHT_CONFLICT:'ハブログとGPXの探索夜が一致しません。原本は保存し、集計を保留しました。',ALL_NEW_NIGHTS_MUST_BE_CONFIRMED:'同じ入力に含まれる新しい探索夜は、すべて確認してから一括反映してください。',LOG_PARSER_UNAVAILABLE:'解析処理を利用できません。反映されていないため、再送してください。',LOG_REQUIRED_FOR_TALLY:'GPX原本は保存しました。捕獲数を更新するにはハブログが必要です。',LOG_PARSE_REVIEW_REQUIRED:'日時の不明行または同時刻の異なる記録があります。集計は保留です。',GPX_INVALID_OR_UNTIMED:'GPXの形式・座標・時刻に不整合があります。集計は保留です。',REVISION_CONFLICT:'別の取込で集計が変わりました。再解析して確認してください。',PRIVATE_SERVICE_UNAVAILABLE:'私有保存先へ接続できません。反映済みとは扱いません。'};
function explain(code){return messages[code]||code;}
function buttons(){
 $('analyze').disabled=busy;$('clear').disabled=busy;
 for(const input of $('rows').querySelectorAll('input'))input.disabled=busy||input.dataset.canEdit!=='yes';
 $('export').disabled=busy||!prepared||prepared.state!=='READY_FOR_CONFIRMATION'||!rows.some(x=>x.classification==='新規候補')||rows.some(x=>x.classification==='新規候補'&&!(x.approved&&x.searchConfirmed&&Number.isInteger(x.confirmedCount)&&x.confirmedCount>=0&&x.confirmedCount<=100));
}
function invalidated(){epoch++;prepared=null;rows=[];retryRequest=null;$('export').disabled=true;$('preview').hidden=true;}
$('files').addEventListener('change',invalidated);$('pasted').addEventListener('input',invalidated);
$('analyze').textContent='原本を私有保存して照合';$('export').textContent='確認した捕獲数を集計へ反映';
function element(tag,text){const e=document.createElement(tag);if(text!==undefined)e.textContent=String(text);return e;}
function b64(bytes){let text='';for(let i=0;i<bytes.length;i+=32768)text+=String.fromCharCode(...bytes.subarray(i,i+32768));return btoa(text);}
async function load(){
 const r=await fetch('./data/capture_summary.json?require_fresh=1',{credentials:'same-origin',cache:'no-store',redirect:'error'});
 if(!r.ok)throw Error('最新集計を取得できません');const value=await r.json();
 if(value.schema_version!=='habu-capture-dashboard-v2'||!Array.isArray(value.nights))throw Error('集計形式が不正');return value;
}
function paint(){
 rows=HabuLogIntake.compare(prepared.nights,summary);$('rows').replaceChildren();
 for(const row of rows){
  const tr=element('tr');tr.append(element('td',row.night),element('td',row.classification),element('td',row.captureHints),element('td',row.starts+'/'+row.ends));
  for(const [type,key,label] of [['number','confirmedCount','本人捕獲数'],['checkbox','searchConfirmed','探索した'],['checkbox','approved','登録する']]){
   const td=element('td'),input=element('input');input.type=type;input.dataset.canEdit=row.classification==='新規候補'?'yes':'no';input.disabled=row.classification!=='新規候補';input.setAttribute('aria-label',row.night+' '+label);
   if(type==='number'){input.min='0';input.max='100';input.step='1';input.placeholder='要確認';}
   input.addEventListener('input',()=>{retryRequest=null;row[key]=type==='number'?(input.value.trim()===''?null:Number(input.value)):input.checked;buttons();});
   td.append(input);if(type==='checkbox')td.append(document.createTextNode(label));tr.append(td);
  }
  $('rows').append(tr);
 }
 $('preview').hidden=false;
 $('overview').textContent='原本保存済み '+prepared.archived_sources+'件 / '+prepared.nights.length+'探索夜 / GPX '+prepared.gpx.reduce((s,x)=>s+x.points,0)+'点（記録された時刻の確認のみ）';
 $('errors').hidden=!prepared.reasons.length;$('errors').textContent=prepared.reasons.map(explain).join(' / ');
 $('status').textContent=prepared.state==='APPLIED'?'この入力はすでに集計へ反映済みです。再加算しません。':prepared.state==='HELD'?'原本保存済み・集計は保留。':'原本保存済み。集計はまだ変更していません。新規候補の本人捕獲数をすべて確認してください。';buttons();
}
$('analyze').addEventListener('click',async()=>{
 if(busy)return;invalidated();const version=epoch;busy=true;buttons();$('saveStatus').textContent='';
 try{
  const files=[];let total=0;
  for(const file of $('files').files){
   const extension=file.name.split('.').pop().toLowerCase();if(!['txt','log','gpx'].includes(extension))throw Error('TXT・LOG・GPXのみ対応しています');
   total+=file.size;if(!file.size||file.size>12*1024*1024||total>48*1024*1024)throw Error('1ファイル12MiB、合計48MiBまでです');
   files.push({kind:extension==='gpx'?'gpx':'log',content_b64:b64(new Uint8Array(await file.arrayBuffer()))});
  }
  if($('pasted').value.trim()){const raw=new TextEncoder().encode($('pasted').value);total+=raw.length;if(raw.length>12*1024*1024||total>48*1024*1024)throw Error('入力が大きすぎます');files.push({kind:'log',content_b64:b64(raw)});}
  if(!files.length)throw Error('ハブログまたはGPXを選んでください');
  if(version!==epoch)throw Error('入力が変わりました。再解析してください');
  const result=await call('prepare',{files,channel:'dashboard'});const fresh=await load();
  if(version!==epoch)throw Error('保存中に入力が変わりました。保存した原本は保持しています。再解析してください');
  prepared=result;summary=fresh;paint();
 }catch(error){$('status').textContent='取込を確定できません: '+explain(error.message);}
 finally{busy=false;buttons();}
});
$('export').addEventListener('click',async()=>{
 if(busy||!prepared)return;busy=true;buttons();const version=epoch;
 try{
  const request=retryRequest||{receipt_id:prepared.receipt_id,expected_revision:prepared.revision,batch:HabuLogIntake.makeBatch(rows,prepared.asof,prepared.source_sha256)};
  retryRequest=request;const result=await call('apply',request);const state=await call('status');const fresh=await load();
  if(state.revision<result.revision)throw Error('保存後の読み戻し確認に失敗しました');
  if(version!==epoch)throw Error('入力が変更されました。反映結果はダッシュボードで確認してください');
  prepared.state='APPLIED';summary=fresh;$('status').textContent='集計反映済み。保存後の読み戻しも確認しました。';$('saveStatus').textContent='集計反映・読み戻し確認済み。累計 '+fresh.total+'匹 / '+fresh.asof+'まで / 保存版 '+result.revision;retryRequest=null;
 }catch(error){$('saveStatus').textContent='反映を確認できません: '+explain(error.message)+' 同じ内容で再送しても二重加算しません。';}
 finally{busy=false;buttons();}
});
$('clear').addEventListener('click',()=>{invalidated();$('files').value='';$('pasted').value='';$('status').textContent='画面の入力を消しました。私有保存済みの原本は削除していません。';buttons();});
call('status').then(s=>{$('status').textContent='私有保存先に接続済み / '+s.asof+'まで / 保存版 '+s.revision;}).catch(()=>{$('status').textContent='私有取込サービス未接続。ファイル選択だけでは反映されません。';});
})();
