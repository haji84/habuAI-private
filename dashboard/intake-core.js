/* Safe local-only parsing of mixed-date owner logs. Never treats sightings as confirmed captures. */
(function(root,factory){
  const api=factory();
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  if(root)root.HabuLogIntake=api;
})(typeof window!=='undefined'?window:null,function(){
  'use strict';
  function nightOf(year,mon,day,hour,minute){
    const d=new Date(Date.UTC(year,mon-1,day));
    if(d.getUTCFullYear()!==year||d.getUTCMonth()!==mon-1||d.getUTCDate()!==day||
       hour<0||hour>23||minute<0||minute>59)return null;
    if(hour<7)d.setUTCDate(d.getUTCDate()-1);
    return d.toISOString().slice(0,10);
  }
  function timestamp(line){
    const s=line.normalize('NFKC').trim();
    const m=s.match(/^(\d{4})[\/-](\d{1,2})[\/-](\d{1,2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
    if(!m)return null;
    const y=+m[1],mo=+m[2],day=+m[3],hour=+m[4],min=+m[5],sec=+(m[6]||0);
    if(sec>59)return {error:'時刻が不正: '+s};
    const night=nightOf(y,mo,day,hour,min);
    if(!night)return {error:'日付が不正: '+s};
    return {night,when:y+'-'+String(mo).padStart(2,'0')+'-'+String(day).padStart(2,'0')+' '+String(hour).padStart(2,'0')+':'+String(min).padStart(2,'0')+':'+String(sec).padStart(2,'0')};
  }
  function normalized(s){return s.normalize('NFKC').replace(/\r/g,'').trim().replace(/[ \t]+/g,' ');}
  function classify(lines){
    const a=lines.map(v=>normalized(v));
    if(a.some(v=>/^(?:エリア)?探索開始$/.test(v)))return '探索開始';
    if(a.some(v=>/^(?:エリア)?探索終了$/.test(v)))return '探索終了';
    if(a.some(v=>v==='捕獲'))return '捕獲の記載';
    if(a.some(v=>v==='目撃'))return '目撃';
    if(a.some(v=>v==='轢死'||v==='死亡'))return '轢死等';
    return 'その他・不明';
  }
  function parse(text){
    if(typeof text!=='string'||text.length>12*1024*1024)throw Error('文字列で12MB以下のログを指定してください');
    const lines=text.replace(/\r\n?/g,'\n').split('\n');
    const blocks=[]; const problems=[]; let pending=null,unassigned=[];
    function finish(){
      if(pending){pending.body=pending.body.filter(x=>x!==undefined);pending.kind=classify(pending.body);
        pending.key=pending.when+'|'+pending.body.map(normalized).filter(Boolean).join('\n');
        blocks.push(pending);pending=null;}
    }
    for(let i=0;i<lines.length;i++){
      const stamp=timestamp(lines[i]);
      if(stamp){
        finish();
        if(stamp.error){problems.push('行'+(i+1)+' '+stamp.error);unassigned.push(lines[i]);continue;}
        pending={line:i+1,night:stamp.night,when:stamp.when,body:[]};
      }else if(pending){pending.body.push(lines[i]);}
      else if(lines[i].trim()&&lines[i].trim()!=='ハブログ'){unassigned.push(lines[i]);}
    }
    finish();
    if(unassigned.length)problems.push('日時に紐づかない行が'+unassigned.length+'行あります。原本は別途保存してください');
    if(!blocks.length)problems.push('認識できる日時付きイベントがありません。自動登録できません');
    const uniq=new Map();let repeated=0;const duplicateTimes=new Map();
    for(const b of blocks){
      if(uniq.has(b.key)){repeated++;continue;}
      uniq.set(b.key,b);
      const timeKey=b.when;
      if(!duplicateTimes.has(timeKey))duplicateTimes.set(timeKey,[]);
      duplicateTimes.get(timeKey).push(b);
    }
    const nights=new Map();
    for(const b of uniq.values()){
      if(!nights.has(b.night))nights.set(b.night,{night:b.night,events:[],captureHints:0,starts:0,ends:0,sightings:0,ambiguousTimes:0});
      const n=nights.get(b.night);n.events.push(b);
      if(b.kind==='捕獲の記載')n.captureHints++;
      if(b.kind==='探索開始')n.starts++;
      if(b.kind==='探索終了')n.ends++;
      if(b.kind==='目撃')n.sightings++;
    }
    for(const same of duplicateTimes.values())if(same.length>1){
      for(const b of same)nights.get(b.night).ambiguousTimes++;
    }
    return {nights:[...nights.values()].sort((a,b)=>a.night.localeCompare(b.night)),
      blocks:blocks.length,uniqueBlocks:uniq.size,exactRepeats:repeated,
      problems,warning:'捕獲の記載は件数の手掛かりに過ぎず、本人の確定捕獲数ではありません。'};
  }
  function compare(nights,summary){
    if(!summary||!Array.isArray(summary.nights)||typeof summary.asof!=='string')throw Error('既存の確定集計データが読み込めません');
    const existing=new Map(summary.nights.map(n=>[n.night,n]));
    return nights.map(n=>{
      const old=existing.get(n.night);
      return {...n,existingCount:old?old.count:null,existingEffort:old?old.effort_confirmed:null,
        classification:old?'登録済み・要照合':n.night<=summary.asof?'過去日の未登録候補・要審査':'新規候補'};
    });
  }
  function makeBatch(items,asof,fileHashes){
    if(!/^\d{4}-\d{2}-\d{2}$/.test(asof))throw Error('集計基準日が不正');
    const seen=new Set(),files=[];
    for(const x of items){
      if(x.classification!=='新規候補'||!x.approved)continue;
      if(x.night<=asof||seen.has(x.night)||!Number.isInteger(x.confirmedCount)||x.confirmedCount<0||x.confirmedCount>100||
         x.searchConfirmed!==true)throw Error('日付・探索確認・匹数に不整合があります: '+x.night);
      seen.add(x.night);
      files.push({path:'data/raw/habu_owner_nights/'+x.night.slice(0,4)+'/'+x.night+'.json',
        content:{schema_version:'habu-owner-night-v1',source:'user Habu log',
          operational_date:x.night,owner_confirmed:true,search_performed:true,capture_count:x.confirmedCount,revision:1}});
    }
    if(!files.length)throw Error('確定して登録する新規探索夜がありません');
    return {schema_version:'habu-local-intake-review-batch-v1',baseline_asof:asof,
      source_sha256:fileHashes,requires_server_reconciliation:true,
      counts_are_owner_confirmed_not_scientific_labels:true,files};
  }
  return {nightOf,timestamp,parse,compare,makeBatch};
});