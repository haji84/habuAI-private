/* HUB NATURAL: evidence-preserving local field session logic.
 * This module never posts raw coordinates anywhere. */
(function(root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.HabuFieldCore = api;
})(typeof window !== 'undefined' ? window : null, function() {
  'use strict';
  const GAP_MS = 300000;
  const MAX_POINTS = 200000;
  const MAX_BACKUP_BYTES = 30*1024*1024;
  const TYPES = ['capture','sighting','roadkill','other'];
  function utc(v) {
    const d = new Date(v);
    if (!Number.isFinite(d.valueOf())) throw Error('日時が不正です');
    return d.toISOString();
  }
  function night(ts) {
    const shifted = new Date(new Date(utc(ts)).getTime() + 9*3600000);
    if (shifted.getUTCHours() < 7) shifted.setUTCDate(shifted.getUTCDate()-1);
    return shifted.toISOString().slice(0,10);
  }
  function clockJst(ts) {
    const t = new Date(new Date(utc(ts)).getTime() + 9*3600000);
    return String(t.getUTCFullYear()) + '/' + String(t.getUTCMonth()+1).padStart(2,'0') + '/' +
      String(t.getUTCDate()).padStart(2,'0') + ' ' +
      String(t.getUTCHours()).padStart(2,'0') + ':' +
      String(t.getUTCMinutes()).padStart(2,'0') + ':' + String(t.getUTCSeconds()).padStart(2,'0');
  }
  function finite(v) { return typeof v==='number' && Number.isFinite(v); }
  function generateId() {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return crypto.randomUUID();
    throw Error('安全なHTTPS環境が必要です');
  }
  function createSession(id,ts) {
    if (typeof id!=='string' || !/^[a-zA-Z0-9-]{16,90}$/.test(id)) throw Error('セッションIDが不正');
    return {schema_version:'habu-field-session-v1',id,startedAt:utc(ts),endedAt:null,
      status:'active',points:[],events:[],gaps:[],conditions:[],revision:1};
  }
  function validateSession(s) {
    if (!s || s.schema_version!=='habu-field-session-v1' || typeof s.id!=='string' ||
       !Array.isArray(s.points) || !Array.isArray(s.events) || !Array.isArray(s.gaps) ||
       (s.conditions!==undefined&&!Array.isArray(s.conditions)) ||
       !['active','stopped'].includes(s.status)) throw Error('保存データが不正');
    utc(s.startedAt);
    if (s.endedAt) utc(s.endedAt);
    return s;
  }
  function restoredTime(value) {
    const parts=typeof value==='string' && /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,3}))?(Z|[+-]\d{2}:\d{2})$/.exec(value);
    if(!parts)throw Error('復元する日時には正しい日付とタイムゾーンが必要です');
    const normalized=utc(value),zone=parts[8];
    const offset=zone==='Z'?0:(zone[0]==='-'?-1:1)*(Number(zone.slice(1,3))*60+Number(zone.slice(4,6)));
    const local=new Date(new Date(normalized).getTime()+offset*60000);
    const actual=[local.getUTCFullYear(),local.getUTCMonth()+1,local.getUTCDate(),
      local.getUTCHours(),local.getUTCMinutes(),local.getUTCSeconds()];
    if(actual.some((v,i)=>v!==Number(parts[i+1])) ||
       local.getUTCMilliseconds()!==Number((parts[7]||'').padEnd(3,'0')))
      throw Error('復元する日時が不正です');
    return normalized;
  }
  // Deep validation belongs at the backup boundary, never in every live fix.
  // Scratch records reuse creation rules without changing the supplied source.
  function validateRestoredSession(s) {
    validateSession(s);
    const start=restoredTime(s.startedAt),scratch=createSession(s.id,start);
    if(s.revision!==undefined && (!Number.isSafeInteger(s.revision)||s.revision<0||s.revision>=Number.MAX_SAFE_INTEGER))
      throw Error('保存版の番号が不正です');
    if(s.status==='active' ? s.endedAt!==null : typeof s.endedAt!=='string')
      throw Error('探索状態と終了時刻が一致しません');
    if(s.endedAt!==null && new Date(restoredTime(s.endedAt))<new Date(start))
      throw Error('終了時刻が開始より前です');
    if(s.points.length>MAX_POINTS)throw Error('測位件数の上限を超えています');
    let prior=new Date(start).getTime();
    for(const p of s.points){
      if(!p||typeof p!=='object'||Array.isArray(p))throw Error('GPS測位値が不正');
      if((p.altitude!==undefined&&!finite(p.altitude))||
         (p.speed!==undefined&&(!finite(p.speed)||p.speed<0)))throw Error('GPS測位値が不正');
      const point=observedPoint({latitude:p.lat,longitude:p.lon,accuracy:p.accuracy,
        altitude:p.altitude,speed:p.speed},restoredTime(p.time));
      const at=new Date(point.time).getTime();
      if(at<prior)throw Error('測位時刻が開始前、または逆順です');
      prior=at;
    }
    const ids=new Set();
    for(const e of s.events){
      if(!e||typeof e!=='object'||Array.isArray(e)||typeof e.species!=='string'||
         !e.species.trim()||e.species!==e.species.trim()||e.species.length>80||
         (e.note!==undefined&&(typeof e.note!=='string'||e.note.length>300))||ids.has(e.id))
        throw Error('観察記録が不正、またはIDが重複しています');
      const time=restoredTime(e.time);
      if(e.position!=null){
        const p=e.position;
        if(!p||typeof p!=='object'||Array.isArray(p)||(p.altitude!==undefined&&!finite(p.altitude)))
          throw Error('観察位置が不正です');
        const point=observedPoint({latitude:p.lat,longitude:p.lon,accuracy:p.accuracy,
          altitude:p.altitude},restoredTime(p.time));
        if(Math.abs(new Date(time)-new Date(point.time))>90000)throw Error('観察位置の測位時刻が離れています');
      }
      event(scratch,{...e,time});ids.add(e.id);scratch.events.length=0;
    }
    for(const gap of s.gaps){
      if(!gap||typeof gap!=='object'||Array.isArray(gap)||typeof gap.reason!=='string'||gap.reason.length>80)
        throw Error('GPS中断記録が不正です');
      restoredTime(gap.time);
    }
    if((s.conditions||[]).length>10000)throw Error('環境記録が多すぎます');
    for(const item of s.conditions||[]){
      if(!item||typeof item!=='object'||Array.isArray(item))
        throw Error('環境記録が不正です');
      const when=restoredTime(item.time);
      if(Date.parse(when)<Date.parse(start)||
         (s.endedAt&&Date.parse(when)>Date.parse(s.endedAt)))
        throw Error('探索範囲外の環境記録です');
      recordCondition(scratch,{...item,time:when});
      scratch.conditions.length=0;
    }
    return s;
  }
  function observedPoint(coords,ts) {
    const time=utc(ts);
    const lat=coords.latitude,lon=coords.longitude,accuracy=coords.accuracy;
    if (!finite(lat)||!finite(lon)||Math.abs(lat)>90||Math.abs(lon)>180||
      !finite(accuracy)||accuracy<0||accuracy>100000) throw Error('GPS測位値が不正');
    const p={time,lat,lon,accuracy};
    if (finite(coords.altitude)) p.altitude=coords.altitude;
    if (finite(coords.speed)&&coords.speed>=0) p.speed=coords.speed;
    return p;
  }
  function markGap(s,ts,reason) {
    validateSession(s);
    if(s.status!=='active')return false;
    const time=utc(ts);
    if(s.gaps.length && s.gaps[s.gaps.length-1].time===time)return false;
    s.gaps.push({time,reason:String(reason||'測位中断').slice(0,80)});
    s.revision++;
    return true;
  }
  const CONDITION_VALUES={
    road_surface:{dry:'ドライ',damp:'湿り',wet:'濡れ',puddle:'水たまり'},
    weather:{clear:'晴れ',cloudy:'曇り',rain:'雨',fog:'霧'}
  };
  function recordCondition(s,item){
    validateSession(s);
    if(s.status!=='active')throw Error('探索中だけ環境を記録できます');
    if(!item||typeof item!=='object'||Array.isArray(item))
      throw Error('環境入力が不正です');
    const time=utc(item.time);
    if(Date.parse(time)<Date.parse(s.startedAt))
      throw Error('探索開始前の環境記録です');
    const category=item.category, value=item.value;
    let source;
    if(Object.prototype.hasOwnProperty.call(CONDITION_VALUES,category)){
      if(typeof value!=='string'||
         !Object.prototype.hasOwnProperty.call(CONDITION_VALUES[category],value))
        throw Error('路面・天気は実際に観察した選択肢で記録してください');
      source='owner_visual';
    }else if(category==='air_temperature'){
      if(typeof value!=='number'||!Number.isFinite(value)||value<-30||value>60)
        throw Error('実測気温を-30〜60℃の数値で入力してください');
      source='thermometer';
    }else throw Error('環境の種類が不正です');
    if(item.source!==undefined&&item.source!==source)
      throw Error('環境情報の出典が不正です');
    const conditions=s.conditions||(s.conditions=[]);
    if(conditions.length>=10000)throw Error('環境記録数の上限です');
    const record={time,category,value,source};
    const prev=conditions.at(-1);
    if(prev&&prev.time===time&&prev.category===category&&prev.value===value)
      return false;
    conditions.push(record);s.revision++;
    return true;
  }
  function recordPoint(s,coords,ts) {
    validateSession(s);
    if(s.status!=='active') throw Error('探索は終了しています');
    if(s.points.length>=MAX_POINTS)throw Error('測位件数の上限。バックアップして探索を分けてください');
    const p=observedPoint(coords,ts);
    // Never admit a stale GPS measurement taken before this session started.
    if(new Date(p.time).getTime()<new Date(s.startedAt).getTime())throw Error('探索開始前の測位');
    const last=s.points[s.points.length-1];
    if(last && new Date(p.time)<new Date(last.time))throw Error('古い測位は使用しません');
    if(last && p.time===last.time && p.lat===last.lat && p.lon===last.lon)return false;
    s.points.push(p);s.revision++;
    return true;
  }
  function event(s, item) {
    validateSession(s);
    if(s.status!=='active')throw Error('探索は終了しています');
    const type=item.type;
    if(!TYPES.includes(type))throw Error('記録種別が不正');
    const species=String(item.species||'').trim().slice(0,80);
    const n=item.count;
    if(!species||!Number.isInteger(n)||n<1||n>100)throw Error('種類と匹数を正しく指定してください');
    const time=utc(item.time);
    if(new Date(time)<new Date(s.startedAt)-60000)throw Error('探索開始前の記録');
    const id=item.id;
    if(typeof id!=='string'||id.length<16||s.events.some(x=>x.id===id))throw Error('記録IDが重複しています');
    // Unknown/missing owner is not evidence of a personal capture.
    const owner=item.owner;
    if(owner!=='self'&&owner!=='other')throw Error('捕獲者が不正');
    const e={id,type,species,count:n,time,owner,note:String(item.note||'').slice(0,300)};
    if(item.observation!==undefined) {
      const observation=item.observation;
      if(!observation||typeof observation!=='object'||Array.isArray(observation)||
        Object.keys(observation).length!==2||!Object.hasOwn(observation,'observed_at')||
        !Object.hasOwn(observation,'uncertainty_seconds')||!finite(observation.uncertainty_seconds)||
        observation.uncertainty_seconds<0||observation.uncertainty_seconds>31536000)
        throw Error('観測時刻と時刻の誤差を正しく入力してください');
      const observedAt=restoredTime(observation.observed_at);
      if(Date.parse(observedAt)<Date.parse(s.startedAt)||Date.parse(observedAt)>Date.parse(time))
        throw Error('観測時刻は探索開始から記録を保存するまでの範囲で入力してください');
      e.observation={observed_at:observedAt,uncertainty_seconds:observation.uncertainty_seconds};
    }
    if(item.position) {
      const p=observedPoint({latitude:item.position.lat,longitude:item.position.lon,accuracy:item.position.accuracy,
        altitude:item.position.altitude},item.position.time);
      if(Math.abs(new Date(time)-new Date(p.time))<=90000)e.position=p;
    }
    s.events.push(e);s.revision++;return e;
  }
  function stop(s,ts) {
    validateSession(s);
    if(s.status!=='active')throw Error('すでに終了しています');
    const time=utc(ts);
    if(new Date(time)<new Date(s.startedAt))throw Error('終了時刻が開始より前');
    s.endedAt=time;s.status='stopped';s.revision++;
  }
  function summary(s) {
    validateSession(s);
    const byNight=new Map();
    function ensure(d){
      if(!byNight.has(d))byNight.set(d,{night:d,ownerHabuCaptures:0,captureEvents:0,sightings:0,
        roadkill:0,other:0,gpsPoints:0,sourceSessionId:s.id,ownerConfirmed:false,searchPerformed:'needs_review'});
      return byNight.get(d);
    }
    ensure(night(s.startedAt));
    for(const e of s.events){
      const n=ensure(night(e.time));
      if(e.type==='capture'){n.captureEvents++;if(e.species==='ハブ'&&e.owner==='self')n.ownerHabuCaptures+=e.count;}
      else if(e.type==='sighting')n.sightings++;
      else if(e.type==='roadkill')n.roadkill++;
      else n.other++;
    }
    for(const p of s.points)ensure(night(p.time)).gpsPoints++;
    if(s.endedAt)ensure(night(s.endedAt));
    return [...byNight.values()].sort((a,b)=>a.night.localeCompare(b.night));
  }
  function escapeXml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;').replace(/'/g,'&apos;');
  }
  function gpx(s){
    validateSession(s);
    const points=s.points;
    const gaps=(s.gaps||[]).map(x=>new Date(utc(x.time)).getTime()).sort((a,b)=>a-b);
    let gapIndex=0,lastTs=null,sections=[],current=[];
    for(const p of points){
      const t=new Date(utc(p.time)).getTime();
      let hasGap=lastTs!==null && (t-lastTs>=GAP_MS || t<lastTs);
      while(gapIndex<gaps.length && gaps[gapIndex]<=t){
        if(lastTs!==null && gaps[gapIndex]>=lastTs)hasGap=true;
        gapIndex++;
      }
      if(hasGap && current.length){sections.push(current);current=[];}
      const valid=observedPoint({latitude:p.lat,longitude:p.lon,accuracy:p.accuracy,
        altitude:p.altitude,speed:p.speed},p.time);
      let part='<trkpt lat="'+valid.lat+'" lon="'+valid.lon+'">';
      if(finite(valid.altitude))part+='<ele>'+valid.altitude+'</ele>';
      part+='<time>'+escapeXml(valid.time)+'</time>';
      part+='<extensions><habu:accuracyMeters>'+valid.accuracy+'</habu:accuracyMeters></extensions></trkpt>';
      current.push(part);lastTs=t;
    }
    if(current.length)sections.push(current);
    const segs=sections.map(a=>'<trkseg>'+a.join('')+'</trkseg>').join('');
    return '<?xml version="1.0" encoding="UTF-8"?>\n' +
      '<gpx version="1.1" creator="HUB NATURAL local field recorder" xmlns="http://www.topografix.com/GPX/1/1" xmlns:habu="urn:habu-ai:field:gpx:accuracy:1">' +
      '<metadata><name>HUB NATURAL GPS observations</name><time>'+escapeXml(s.startedAt)+'</time></metadata>' +
      '<trk><name>Field '+escapeXml(s.id)+'</name>'+segs+'</trk></gpx>\n';
  }
  function logfile(s){
    validateSession(s);
    const out=['ハブログ',''];
    const events=[{time:s.startedAt,txt:['エリア探索開始']}];
    for(const e of s.events){
      const parts=[e.type==='capture'?'捕獲':e.type==='sighting'?'目撃':e.type==='roadkill'?'轢死':'その他'];
      parts.push(e.count+'匹',e.species,'捕獲者: '+(e.owner==='self'?'本人':'他者'));
      if(e.note)parts.push('備考: '+e.note);
      if(e.position)parts.push('GPS精度: '+e.position.accuracy+'m',
        String(e.position.lat),String(e.position.lon));
      events.push({time:e.time,txt:parts});
    }
    for(const c of s.conditions||[]){
      let description;
      if(c.category==='road_surface')description='路面: '+CONDITION_VALUES.road_surface[c.value]+'（本人目視）';
      else if(c.category==='weather')description='天気: '+CONDITION_VALUES.weather[c.value]+'（本人目視）';
      else description='気温（温度計で実測）: '+c.value+'℃';
      events.push({time:c.time,txt:['環境観測',description]});
    }
    if(s.endedAt)events.push({time:s.endedAt,txt:['エリア探索終了']});
    events.sort((a,b)=>a.time.localeCompare(b.time));
    for(const e of events)out.push(clockJst(e.time),...e.txt,'');
    out.push('---','GPS測位実測点: '+s.points.length,'GPS中断記録: '+s.gaps.length,
      'このログは端末内の本人入力・GPS実測記録です。自動推定した捕獲個体・地点はありません。');
    return out.join('\n')+'\n';
  }
  function canUse(plan,feature){
    const levels=['FREE','TRACK','AI','PREMIUM'];
    const required={capture:0,gpsRecord:0,routeHistory:1,gpsExport:1,aiPrediction:2,advancedPrediction:3,routeOptimization:3};
    return Object.prototype.hasOwnProperty.call(required,feature)&&levels.indexOf(plan)>=required[feature];
  }
  // Commercial route export uses this guarded entry point. A trusted
  // subscription authority is required before enabling commercial accounts.
  function exportRouteForPlan(s,plan) {
    if(!canUse(plan,'gpsExport'))throw Error('GPS出力にはTRACK以上が必要です');
    return gpx(s);
  }
  function exportBackup(s){
    validateRestoredSession(s);
    const text=JSON.stringify(s,null,2)+'\n';
    if(new TextEncoder().encode(text).byteLength>MAX_BACKUP_BYTES)
      throw Error('記録一式が30MBを超えるため保存できません。GPXとログを個別に保存してください。端末内の記録は残っています');
    return text;
  }
  return {GAP_MS,MAX_BACKUP_BYTES,night,clockJst,generateId,createSession,validateSession,validateRestoredSession,observedPoint,
    markGap,recordCondition,recordPoint,event,stop,summary,gpx,logfile,exportBackup,canUse,exportRouteForPlan};
});
