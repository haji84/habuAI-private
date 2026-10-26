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
      status:'active',points:[],events:[],gaps:[],revision:1};
  }
  function validateSession(s) {
    if (!s || s.schema_version!=='habu-field-session-v1' || typeof s.id!=='string' ||
       !Array.isArray(s.points) || !Array.isArray(s.events) || !Array.isArray(s.gaps) ||
       !['active','stopped'].includes(s.status)) throw Error('保存データが不正');
    utc(s.startedAt);
    if (s.endedAt) utc(s.endedAt);
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
  function recordPoint(s,coords,ts) {
    validateSession(s);
    if(s.status!=='active') throw Error('探索は終了しています');
    if(s.points.length>=MAX_POINTS)throw Error('測位件数の上限。バックアップして探索を分けてください');
    const p=observedPoint(coords,ts);
    if(new Date(p.time)<new Date(s.startedAt)-60000)throw Error('探索開始前の測位');
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
    const e={id,type,species,count:n,time,owner:item.owner==='other'?'other':'self',note:String(item.note||'').slice(0,300)};
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
      let hasGap=lastTs!==null && (t-lastTs>GAP_MS || t<lastTs);
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
      '<gpx version="1.1" creator="HUB NATURAL local field recorder" xmlns="http://www.topografix.com/GPX/1/1" xmlns:habu="https://example.invalid/habu/field-accuracy">' +
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
    if(s.endedAt)events.push({time:s.endedAt,txt:['エリア探索終了']});
    events.sort((a,b)=>a.time.localeCompare(b.time));
    for(const e of events)out.push(clockJst(e.time),...e.txt,'');
    out.push('---','GPS測位実測点: '+s.points.length,'GPS中断記録: '+s.gaps.length,
      'このログは端末内の本人入力・GPS実測記録です。自動推定した捕獲個体・地点はありません。');
    return out.join('\n')+'\n';
  }
  function exportBackup(s){
    validateSession(s);
    return JSON.stringify(s,null,2)+'\n';
  }
  return {GAP_MS,night,clockJst,generateId,createSession,validateSession,observedPoint,
    markGap,recordPoint,event,stop,summary,gpx,logfile,exportBackup};
});