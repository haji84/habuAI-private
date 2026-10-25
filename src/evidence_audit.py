"""Executed source consistency and bounded observation eligibility; never Gold by filename.

Declared source roles are verified against referenced review/receipt bytes. These
checks do not authenticate the issuer or establish scientific/production authority.
"""
from __future__ import annotations
import base64
import csv
import hashlib
import io
import json
import math
import re
import time
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from zoneinfo import ZoneInfo
from master_contracts import canonical_bytes, digest, file_hash, safe_path, validate_night
from gpx_audit import utm52n

VERSION='evidence-audit-v1'
JST=ZoneInfo('Asia/Tokyo')
OSM_ARCHIVE='artifacts/Habu_AI_OSM_Road_Grid_2026-09-25.zip.parts'
INPUT_PREFIXES={'data','evidence','policies','features','protocols'}
MAX_POINTS=1_000_000
MAX_READ_BYTES=512*1024*1024
MAX_READS=4000


class AuditBudgetExceeded(RuntimeError):
    pass


def timestamp(value):
    dt=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if dt.tzinfo is None: raise ValueError('TIMEZONE_REQUIRED')
    return dt.astimezone(JST)


def night_for(dt): return (dt.astimezone(JST)-timedelta(hours=7)).date().isoformat()


def coordinates(lat,lon):
    lat,lon=float(lat),float(lon)
    if not(math.isfinite(lat) and math.isfinite(lon) and 0<=lat<=84 and 126<=lon<=132):
        raise ValueError('COORDINATE_OUTSIDE_UTM52N')
    return lat,lon


def unit_key(lat,lon,dt):
    x,y=utm52n(lat,lon);dt=dt.astimezone(JST)
    return math.floor(x/100),math.floor(y/100),dt.replace(minute=dt.minute//10*10,second=0,microsecond=0).isoformat()


class Audit:
    def __init__(self,root,verified_at,budget_seconds=300):
        self.root=Path(root);self.now=timestamp(verified_at).isoformat()
        self.deadline=time.monotonic()+max(0,budget_seconds);self.read_bytes=0;self.reads=0;self.points=0
        self.consumed={};self.sources={};self.checks=[];self.requirements=[];self.receipts={}
    def tick(self):
        if time.monotonic()>=self.deadline:raise AuditBudgetExceeded("AUDIT_TIME_LIMIT")
        if self.points>MAX_POINTS:raise AuditBudgetExceeded("AUDIT_POINT_LIMIT")
        if self.read_bytes>MAX_READ_BYTES or self.reads>MAX_READS:raise AuditBudgetExceeded("AUDIT_INPUT_LIMIT")
    def read(self,path):
        self.tick()
        if Path(path).parts[0] not in INPUT_PREFIXES and not path.startswith(OSM_ARCHIVE+'/'):
            raise ValueError('UNAPPROVED_INPUT_NAMESPACE')
        p=safe_path(self.root,path)
        size=p.stat().st_size
        if size>100*1024*1024: raise ValueError('SOURCE_SIZE_LIMIT')
        self.read_bytes+=size;self.reads+=1;self.tick()
        raw=p.read_bytes();sha=hashlib.sha256(raw).hexdigest()
        if path in self.consumed and self.consumed[path]!=sha: raise ValueError('SOURCE_CHANGED_DURING_AUDIT')
        self.consumed[path]=sha
        return raw
    def js(self,path):return json.loads(self.read(path))
    def ref(self,ref):
        raw=self.read(ref['path'])
        if hashlib.sha256(raw).hexdigest()!=ref['sha256']:raise ValueError('REFERENCE_HASH_MISMATCH: '+ref['path'])
        return raw
    def check(self,name,status,source,reason=''):
        self.checks.append(dict(check=name,status=status,source=source,reason=str(reason)))
    def need(self,code,source,criterion):
        item=dict(code=code,kind='DATA_BLOCKED',source_ids=[source],criterion=criterion,
                  evidence_needed=criterion,permitted_next_action='Supply hash-bound source evidence; never infer from absence')
        if item not in self.requirements:self.requirements.append(item)
    def source(self,path,sha=None,size=None):
        if path in self.sources:return self.sources[path]
        if sha is None:
            raw=self.read(path);sha=hashlib.sha256(raw).hexdigest();size=len(raw)
        receipt=self.receipts.get(path)
        out=dict(path=path,sha256=sha,size_bytes=size,source_id=sha,
                 first_verified_received_at=receipt['received_at_utc'] if receipt else None,
                 historical_available_at=None,available_at=receipt['received_at_utc'] if receipt else self.now,
                 availability_basis='VERIFIED_RECEIPT' if receipt else 'VERIFIED_PRESENT_NOW',
                 receipt_ref=receipt.get('_ref') if receipt else None,use_roles=['diagnostic_only'],
                 quality='UNKNOWN',recovery_class='UNKNOWN',search_role='UNKNOWN',checked_at=self.now)
        self.sources[path]=out
        return out


def _receipts(a):
    for path in sorted((a.root/'evidence/raw_intake').glob('*.json')):
        a.tick()
        rel=path.relative_to(a.root).as_posix()
        try:
            row=a.js(rel);rawpath=row.get('raw_path') or row.get('raw_duplicate_path')
            if not rawpath:continue
            raw=a.read(rawpath)
            if hashlib.sha256(raw).hexdigest()!=row['sha256'] or len(raw)!=row['bytes']:
                raise ValueError('RECEIPT_HASH_OR_SIZE_MISMATCH')
            if timestamp(row['received_at_utc'])>timestamp(a.now):raise ValueError('FUTURE_RECEIPT')
            row['_ref']={'path':rel,'sha256':a.consumed[rel]}
            old=a.receipts.get(rawpath)
            if not old or timestamp(row['received_at_utc'])<timestamp(old['received_at_utc']):a.receipts[rawpath]=row
            a.check('receipt','PASS',rawpath)
        except (KeyError,ValueError,OSError,TypeError) as e:a.check('receipt','FAIL',rel,e)


def _declarations(a):
    path='policies/observation_evidence.json';sessions=[]
    if not (a.root/path).exists():return sessions
    try:
        policy=a.js(path)
        if policy['schema_version']!='1.0':raise ValueError('POLICY_SCHEMA')
        for entry in policy['sources']:
            a.tick()
            try:
                a.ref(entry);source=a.source(entry['path'])
                review=json.loads(a.ref(entry['review_ref']))
                if review['source_sha256']!=source['sha256']:raise ValueError('REVIEW_SOURCE_BINDING')
                if timestamp(review['reviewed_at'])>timestamp(a.now):raise ValueError('FUTURE_REVIEW')
                roles=review['use_roles']
                if not isinstance(roles,list) or not set(roles)<={'observed_exposure','outcome_label','static_predictor','forecast_predictor','universe','diagnostic_only'}:raise ValueError('SOURCE_ROLE')
                # Connector response representations are never original field-label authority.
                if entry['path'].startswith('data/raw/other/library_saved_read_'):raise ValueError('RECOVERED_RESPONSE_DIAGNOSTIC_ONLY')
                if source['receipt_ref'] is None: a.need('RECEIPT',entry['path'],'Receipt or new verified availability; historical time cannot be inferred')
                source.update(use_roles=roles,review_ref=entry['review_ref'],coordinate_method=review.get('coordinate_method'),
                              recovery_class=review.get('recovery_class','UNKNOWN'),
                              available_at=max(timestamp(source['available_at']),timestamp(review['reviewed_at']),timestamp(a.now)).isoformat(),
                              qualification_checked_at=a.now,qualification_basis='CURRENT_SOURCE_BOUND_AUDIT; persist this audit identity for future reuse')
            except (ValueError,KeyError,TypeError,OSError) as e:a.check('source_declaration','FAIL',str(entry),e)
        sessions=policy.get('sessions',[])
    except (ValueError,KeyError,TypeError,OSError) as e:a.check('observation_policy','FAIL',path,e)
    return sessions


def audit_captures(root,a=None):
    a=a or Audit(root,datetime.now(timezone.utc).isoformat())
    events={};conflicts=set();rejected=[];duplicate_candidates=[];bad_sources=set();parsed_sources=[];noncaptures=[]
    paths=sorted(set((a.root/'data/raw/capture_db').rglob('*.csv'))|set((a.root/'data/processed/capture_events').rglob('*.csv')))
    for path in paths:
        a.tick()
        rel=path.relative_to(a.root).as_posix();source=a.source(rel)
        reader=csv.DictReader(io.StringIO(a.read(rel).decode('utf-8-sig')))
        fields=reader.fieldnames or []
        required=(('event_normalized','event_type','event','type'),
                  ('datetime_jst','event_time_local','datetime','time_jst','timestamp'),
                  ('latitude','lat'),('longitude','lon','lng'),('event_count','count'))
        if len(fields)!=len(set(fields)) or any(not set(group).intersection(fields) for group in required):
            bad_sources.add(rel);a.check('capture_schema','FAIL',rel,'REQUIRED_CAPTURE_COLUMNS')
            rejected.append({'source':rel,'row':1,'reason':'REQUIRED_CAPTURE_COLUMNS'});continue
        parsed_sources.append(rel)
        for index,row in enumerate(reader,2):
            a.tick()
            try:
                if None in row or any(value is None for value in row.values()):raise ValueError('CAPTURE_ROW_WIDTH')
                def get(*keys):return next((row[k] for k in keys if row.get(k) not in ('',None)), '')
                kind=get('event_normalized','event_type','event','type').lower()
                if kind in ('sighting','roadkill','reaction','目撃','轢死','反応'):
                    noncaptures.append({'source':rel,'row':index,'event_type':kind,'source_sha256':source['sha256'],'record':row});continue
                if kind not in ('capture','捕獲'):raise ValueError('AMBIGUOUS_CAPTURE_EVENT_TYPE')
                dt=timestamp(get('datetime_jst','event_time_local','datetime','time_jst','timestamp'))
                lat,lon=coordinates(get('latitude','lat'),get('longitude','lon','lng'))
                count=float(get('event_count','count'))
                if not math.isfinite(count) or not count.is_integer() or count<=0:raise ValueError('EXACT_POSITIVE_COUNT_REQUIRED')
                claimed=get('operational_date','night_date')
                if claimed and claimed!=night_for(dt):raise ValueError('NIGHT_CONTRADICTION')
                event_id=get('event_id','id')
                # No-ID observations may be diagnosed, but never assigned fabricated canonical identity.
                identity=event_id or 'diagnostic:'+rel+':'+str(index)
                body=dict(event_id=identity,datetime_jst=dt.isoformat(),latitude=lat,longitude=lon,
                          night_date=night_for(dt),capture_count=int(count))
                selector={'path':rel,'sha256':source['sha256'],'selector':{'csv_row':index,'event_id':event_id}}
                canonical=bool(event_id and 'outcome_label' in source['use_roles'] and source.get('coordinate_method'))
                if identity in events:
                    if any(events[identity][k]!=v for k,v in body.items()):conflicts.add(identity)
                    else:events[identity]['source_refs'].append(selector)
                    continue
                events[identity]=dict(body,source_refs=[selector],canonical_eligible=canonical,
                                     available_at=max(timestamp(source['available_at']),dt).isoformat(),individual_ids=[])
            except (ValueError,KeyError,TypeError) as e:
                rejected.append({'source':rel,'row':index,'reason':str(e)});bad_sources.add(rel)
    individuals=defaultdict(list);individual_seen={};link_errors=[]
    for path in sorted((a.root/'data/processed/individuals').rglob('*.csv')):
        a.tick()
        rel=path.relative_to(a.root).as_posix();a.source(rel)
        for index,row in enumerate(csv.DictReader(io.StringIO(a.read(rel).decode('utf-8-sig'))),2):
            a.tick()
            ident=row.get('individual_id');event=row.get('event_id')
            if not ident or ident in individual_seen or event not in events:
                link_errors.append({'source':rel,'row':index,'reason':'INVALID_OR_DUPLICATE_INDIVIDUAL_LINK'});continue
            individual_seen[ident]=event;individuals[event].append(ident)
    for event,ids in individuals.items():
        a.tick()
        if len(ids)!=events[event]['capture_count']:link_errors.append({'event_id':event,'reason':'INDIVIDUAL_COUNT_MISMATCH'});conflicts.add(event)
        events[event]['individual_ids']=sorted(ids)
    for error in link_errors:a.check('individual_links','FAIL',error.get('source',error.get('event_id','individuals')),error['reason'])
    for identity in conflicts:events.pop(identity,None)
    by_unit=defaultdict(list)
    for event in events.values():by_unit[(event['datetime_jst'],event['latitude'],event['longitude'])].append(event['event_id'])
    duplicate_candidates=[ids for ids in by_unit.values() if len(ids)>1]
    for identity in conflicts:a.check('capture_conflict','FAIL',identity,'Same canonical ID has conflicting quantities/time/location or individual links')
    for rel in bad_sources:a.need('CAPTURE_ROWS',rel,'Resolve rejected capture rows before asserting logging completeness')
    result=dict(parsed_capture_sources=parsed_sources,noncapture_records=noncaptures,events=sorted(events.values(),key=lambda e:e['event_id']),rejected=rejected,conflicts=sorted(conflicts),
                duplicate_candidates=duplicate_candidates,diagnostic_individuals=sum(e['capture_count'] for e in events.values()),
                individual_link_status='FAIL' if link_errors else 'PASS' if individuals else 'NOT_VALIDATED',individual_link_errors=link_errors)
    return result,bad_sources


def _raw_logs(a,captures):
    candidates=[]
    for path in sorted((a.root/'data/raw/habu_logs').rglob('*.json')):
        a.tick()
        rel=path.relative_to(a.root).as_posix()
        source_ref={'path':rel,'selector':{'json_pointer':''}}
        try:
            source=a.source(rel);source_ref['sha256']=source['sha256']
            log=a.js(rel);entries=[]
            for index,event in enumerate(log['events']):
                a.tick()
                if event.get('type')!='capture':continue
                source_ref['selector']={'json_pointer':f'/events/{index}'}
                dt=timestamp(event['time_local']);count=event['individual_count']
                if isinstance(count,bool) or not isinstance(count,int) or count<=0:raise ValueError('RAW_LOG_EXACT_COUNT_REQUIRED')
                if night_for(dt)!=log['operational_date']:raise ValueError('RAW_LOG_NIGHT_MISMATCH')
                matches=[e for e in captures['events'] if timestamp(e['datetime_jst'])==dt]
                if matches and sum(e['capture_count'] for e in matches)!=count:raise ValueError('RAW_PROCESSED_CAPTURE_COUNT_CONFLICT')
                entries.append({'source_ref':{'path':rel,'sha256':source['sha256'],'selector':{'json_pointer':f'/events/{index}'}},
                    'night_date':night_for(dt),'datetime_jst':dt.isoformat(),'capture_count':count,
                    'matched_event_id':matches[0]['event_id'] if len(matches)==1 else None,
                    'canonical_match':bool(len(matches)==1 and matches[0]['canonical_eligible']),
                    'available_at':source['available_at'],'interpretation':'diagnostic time/count reconciliation; no inferred coordinates'})
            source_ref['selector']={'json_pointer':'/capture_summary'}
            summary=log.get('capture_summary',{})
            if summary and (summary.get('individuals')!=sum(e['capture_count'] for e in entries) or summary.get('capture_events')!=len(entries)):raise ValueError('RAW_LOG_SUMMARY_CONFLICT')
            candidates.extend(entries);a.check('raw_log_counts','PASS',rel,'Declared quantities reconciled; coordinate/availability provenance separate')
        except (ValueError,KeyError,TypeError,OSError) as e:
            a.check('raw_log_counts','FAIL',rel,e)
            # Failed reconciliation cannot establish an empty outcome log. Keep the
            # source and failed selector; count/location remain unresolved, so the
            # existing rejected-evidence guards conservatively block completeness.
            captures['rejected'].append({'source':rel,'source_ref':source_ref,'reason':str(e)})
    captures['raw_log_candidates']=candidates


def _gpx(a,path,raw,expected_count=None):
    source=a.source(path);points=[];segments=[];count=0
    raw_sha=hashlib.sha256(raw).hexdigest()
    if expected_count is not None:source.update(reconstructed_sha256=raw_sha,reconstructed_size_bytes=len(raw))
    if b'<!DOCTYPE' in raw or b'<!ENTITY' in raw:raise ValueError('XML_ENTITY_FORBIDDEN')
    root=ET.fromstring(raw)
    for segment_index,seg in enumerate(root.findall('.//{*}trkseg')):
        a.tick()
        segment=[];issues=[];last=None
        for index,p in enumerate(seg.findall('{*}trkpt')):
            a.tick()
            count+=1;a.points+=1;a.tick()
            try:
                lat,lon=coordinates(p.attrib['lat'],p.attrib['lon']);t=p.find('{*}time')
                if t is None:raise ValueError('MISSING_TIME')
                dt=timestamp(t.text)
                if last:
                    seconds=(dt-last['datetime_jst']).total_seconds()
                    if seconds==0:issues.append({'point_index':index,'code':'ZERO_TIME_DELTA'})
                    elif seconds<0:issues.append({'point_index':index,'code':'BACKWARD_TIME'})
                    elif seconds>300:issues.append({'point_index':index,'code':'GAP_GT_300S'})
                    else:
                        x,y=utm52n(lat,lon);px,py=utm52n(last['latitude'],last['longitude'])
                        if math.hypot(x-px,y-py)/seconds>45:issues.append({'point_index':index,'code':'SPEED_OUTLIER'})
                row=dict(latitude=lat,longitude=lon,datetime_jst=dt,night_date=night_for(dt),segment_index=segment_index,
                         point_index=index,source=path,source_sha256=source['sha256'])
                segment.append(row);last=row
            except (ValueError,KeyError,TypeError) as e:
                issues.append({'point_index':index,'code':str(e)});last=None
                a.check('gpx_schema','FAIL',path,f'segment {segment_index} point {index}: {e}')
        segments.append(dict(segment_index=segment_index,point_count=len(seg.findall('{*}trkpt')),valid_points=len(segment),issues=issues))
        for point in segment:point['segment_eligible']=not issues
        points.extend(segment)
    if expected_count is not None and count!=expected_count:raise ValueError('ARCHIVE_POINT_COUNT_MISMATCH')
    return dict(source=path,sha256=raw_sha,point_count=count,valid_points=len(points),segment_count=len(segments),
                segments=segments,source_class='ACTUAL_GPX',quality='SILVER' if points else 'REJECTED'),points


def _trajectories(a):
    reports=[];points=[];seen=set()
    sources=[]
    for path in sorted((a.root/'data/raw/gpx').rglob('*.gpx')):
        a.tick()
        rel=path.relative_to(a.root).as_posix();sources.append((rel,a.read(rel),None))
    for path in sorted((a.root/'data/raw/gpx_archives').rglob('manifest.json')):
        a.tick()
        rel=path.relative_to(a.root).as_posix()
        try:
            m=a.js(rel);pattern=m.get('part_glob','part_*.txt')
            if '/' in pattern or '..' in pattern:raise ValueError('UNSAFE_ARCHIVE_GLOB')
            parts=sorted(path.parent.glob(pattern))
            if len(parts)!=m['part_count']:raise ValueError('ARCHIVE_PART_COUNT')
            raw='\n'.join(a.read(p.relative_to(a.root).as_posix()).decode(m.get('encoding','utf-8')) for p in parts).encode(m.get('encoding','utf-8'))
            if len(raw)!=m['raw_size_bytes'] or hashlib.sha256(raw).hexdigest()!=m['raw_sha256']:raise ValueError('ARCHIVE_HASH_OR_SIZE')
            sources.append((rel,raw,m['trackpoint_count']));a.check('archive_integrity','PASS',rel)
        except (ValueError,KeyError,OSError,TypeError) as e:a.check('archive_integrity','FAIL',rel,e)
    for rel,raw,count in sources:
        a.tick()
        sha=hashlib.sha256(raw).hexdigest()
        if sha in seen:a.check('duplicate_gpx','PASS',rel,'Byte-identical alias excluded from effort');continue
        seen.add(sha)
        try:
            report,rows=_gpx(a,rel,raw,count);reports.append(report);points.extend(rows)
        except (ValueError,KeyError,ET.ParseError,TypeError) as e:a.check('gpx_schema','FAIL',rel,e)
    qc=a.root/'evidence/legacy/habuAI-public/v2_actual_gpx_13night_qc.csv'
    if qc.exists():
        rel=qc.relative_to(a.root).as_posix()
        for row in csv.DictReader(io.StringIO(a.read(rel).decode('utf-8-sig'))):
            a.tick()
            matched=next((r for r in reports if r['sha256']==row.get('sha256')),None)
            if matched:
                a.check('legacy_qc_count','PASS' if matched['point_count']==int(row['gps_points']) else 'FAIL',matched['source'])
    return reports,points


def _sessions(a,sessions,bad_sources,parsed_sources):
    eligible=[]
    for session in sessions:
        a.tick()
        try:
            a.ref(session['trajectory']);source=a.source(session['trajectory']['path'])
            if 'observed_exposure' not in source['use_roles'] or source['recovery_class']!='COMPLETE_REAL_GPX':raise ValueError('TRAJECTORY_USE_NOT_ELIGIBLE')
            record=json.loads(a.ref(session['recording_ref']));search=json.loads(a.ref(record['search_evidence_ref']))
            if record['recording_rule']!='ALL_CAPTURES_RECORDED' or search['trajectory_sha256']!=source['sha256']:raise ValueError('SESSION_RECORDING_BINDING')
            if search['search_role'] not in ('SEARCH','PASSAGE'):raise ValueError('NOT_SEARCH_OR_OBSERVED_PASSAGE')
            start,end=timestamp(record['start']),timestamp(record['end'])
            if start>=end or timestamp(search['start'])>start or timestamp(search['end'])<end:raise ValueError('SESSION_SCOPE_MISMATCH')
            if not record['capture_sources']:raise ValueError('MISSING_CAPTURE_LOG')
            for ref in record['capture_sources']:
                a.tick()
                a.ref(ref);cap=a.source(ref['path'])
                if ref['path'] not in parsed_sources or ref['path'] in bad_sources or 'outcome_label' not in cap['use_roles']:raise ValueError('CAPTURE_LOG_NOT_ELIGIBLE')
            eligible.append(dict(source=session['trajectory']['path'],start=start,end=end,id=session['session_id'],
                                 search_role=search['search_role'],
                                 refs=[session['trajectory'],session['recording_ref'],record['search_evidence_ref']]+record['capture_sources']))
        except (ValueError,KeyError,TypeError,OSError) as e:a.need('SESSION_ELIGIBILITY',str(session.get('session_id')),str(e))
    return eligible


def _units(a,points,capture_audit,sessions,complete_scopes):
    """Labels require both SEARCH proof and independently scoped outcome coverage.

    Session timestamps, PASSAGE declarations and GPX samples alone cannot
    certify an absence of capture. Keep unqualified cells UNKNOWN.
    """
    captures=capture_audit['events'];units={};previous={}
    coverage_by_night=defaultdict(list)
    for scope in complete_scopes:
        bbox=scope['domain']['bbox']
        coverage_by_night[scope['night']].append(bbox)
    # A source-qualified empty log cannot erase another known positive candidate.
    # Unlocatable/rejected/conflicting evidence cannot safely be assigned a narrower scope.
    blocked_all=bool(capture_audit['rejected'] or capture_audit['conflicts'] or capture_audit['individual_link_errors'])
    blocked_keys={unit_key(c['latitude'],c['longitude'],timestamp(c['datetime_jst']))
                  for c in captures if not c['canonical_eligible']}
    blocked_nights={c['night_date'] for c in capture_audit.get('raw_log_candidates',[]) if not c['canonical_match']}
    if blocked_all or blocked_keys or blocked_nights:
        a.need('UNRESOLVED_POSITIVE_EVIDENCE','capture_audit','Resolve known positive candidates before assigning noncapture labels in their possible scope')
    for p in points:
        a.tick()
        key=unit_key(p['latitude'],p['longitude'],p['datetime_jst'])
        u=units.setdefault(key,dict(cell_x=key[0],cell_y=key[1],window_start_jst=key[2],night_date=p['night_date'],
            point_count=0,sample_latitude=p['latitude'],sample_longitude=p['longitude'],label=None,observation='UNKNOWN',
            source_refs=[],duration_seconds=None,distance_m=None))
        u['point_count']+=1
        active=next((s for s in sessions if s['source']==p['source'] and s['start']<=p['datetime_jst']<s['end']),None)
        # A validated session is not the complete capture-outcome denominator.
        # Require a distinct, source-bound, full operational-night/domain ledger,
        # and a SEARCH (not simple PASSAGE) interval for this exact coordinate.
        covered=any(lo<=p['longitude']<=hi and la<=p['latitude']<=ha
                    for lo,la,hi,ha in coverage_by_night.get(p['night_date'],[]))
        if (active and active['search_role']=='SEARCH' and covered
                and p['segment_eligible'] and not blocked_all
                and key not in blocked_keys and p['night_date'] not in blocked_nights):
            u.update(label=0,observation='observed_negative',label_available_at=a.now,quality='AUDITED_OBSERVED')
            for ref in active['refs']:
                a.tick()
                if ref not in u['source_refs']:u['source_refs'].append(ref)
            selector={'path':p['source'],'sha256':p['source_sha256'],'selector':{'segment':p['segment_index'],'point':p['point_index']}}
            if not any('selector' in r for r in u['source_refs']):u['source_refs'].append(selector)
            prev=previous.get((p['source'],p['segment_index']))
            if prev and unit_key(prev['latitude'],prev['longitude'],prev['datetime_jst'])==key and active['start']<=prev['datetime_jst']:
                dt=(p['datetime_jst']-prev['datetime_jst']).total_seconds()
                if 0<dt<=300:
                    x,y=utm52n(p['latitude'],p['longitude']);px,py=utm52n(prev['latitude'],prev['longitude'])
                    u['duration_seconds']=(u['duration_seconds'] or 0)+dt;u['distance_m']=(u['distance_m'] or 0)+math.hypot(x-px,y-py)
                    u.update(effort_method='within-unit consecutive audited GPS samples')
        previous[(p['source'],p['segment_index'])]=p
    for c in captures:
        a.tick()
        if not c['canonical_eligible']:continue
        key=unit_key(c['latitude'],c['longitude'],timestamp(c['datetime_jst']))
        u=units.setdefault(key,dict(cell_x=key[0],cell_y=key[1],window_start_jst=key[2],night_date=c['night_date'],
            point_count=0,sample_latitude=c['latitude'],sample_longitude=c['longitude'],source_refs=[],duration_seconds=None,distance_m=None))
        u.update(label=1,observation='capture_observed',quality='AUDITED_OBSERVED',label_available_at=max(timestamp(c['available_at']),timestamp(a.now)).isoformat())
        u['source_refs']+=c['source_refs']
    return sorted(units.values(),key=lambda u:(u['window_start_jst'],u['cell_x'],u['cell_y']))


def _outcome_coverage(a,captures,bad_sources):
    """Reconcile an explicit complete domain/night declaration against all known events.

    Completeness is a source assertion with checked scope and provenance, not a
    conclusion drawn from an empty file, sample count or observed search session.
    """
    policy_path='policies/observation_evidence.json'
    if not (a.root/policy_path).exists():return []
    complete=[]
    for ref in a.js(policy_path).get('outcome_coverage',[]):
        a.tick()
        try:
            declaration=json.loads(a.ref(ref));night=declaration['night'];validate_night(night)
            domain=json.loads(a.ref(declaration['domain_ref']))
            proof=json.loads(a.ref(declaration['coverage_evidence_ref']))
            if declaration['schema_version']!='1.0' or domain['crs']!='EPSG:4326':raise ValueError('COVERAGE_DOMAIN_SCHEMA')
            bbox=domain['bbox']
            if len(bbox)!=4 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in bbox):raise ValueError('COVERAGE_DOMAIN_BOUNDS')
            lo,la,hi,ha=bbox
            if not(126<=lo<hi<=132 and 0<=la<ha<=84):raise ValueError('COVERAGE_DOMAIN_BOUNDS')
            start=timestamp(night+'T07:00:00+09:00');end=start+timedelta(days=1)
            if proof['coverage_kind']!='COMPLETE_CAPTURE_LOG_FOR_DOMAIN_AND_NIGHT' or proof['night']!=night or timestamp(proof['start'])!=start or timestamp(proof['end'])!=end:raise ValueError('COVERAGE_MUST_SPAN_OPERATIONAL_NIGHT')
            if proof['domain_sha256']!=declaration['domain_ref']['sha256']:raise ValueError('COVERAGE_DOMAIN_BINDING')
            source_refs=declaration['capture_sources']
            if not source_refs or sorted(r['sha256'] for r in source_refs)!=sorted(proof['capture_source_sha256s']):raise ValueError('COVERAGE_CAPTURE_SOURCE_BINDING')
            paths=set()
            for source_ref in source_refs:
                a.tick()
                a.ref(source_ref);source=a.source(source_ref['path']);paths.add(source_ref['path'])
                if source_ref['path'] not in captures['parsed_capture_sources'] or source_ref['path'] in bad_sources or 'outcome_label' not in source['use_roles']:raise ValueError('UNRESOLVED_CAPTURE_SOURCE')
            if captures['conflicts'] or captures['individual_link_errors']:raise ValueError('UNRESOLVED_CAPTURE_CONFLICT')
            if any(c['night_date']==night and not c['canonical_match'] for c in captures.get('raw_log_candidates',[])):raise ValueError('UNRESOLVED_RAW_CAPTURE')
            relevant=[e for e in captures['events'] if e['night_date']==night and lo<=e['longitude']<=hi and la<=e['latitude']<=ha]
            if any(not e['canonical_eligible'] or not any(r['path'] in paths for r in e['source_refs']) for e in relevant):raise ValueError('UNRESOLVED_KNOWN_CAPTURE')
            # Rejected quantities/locations might be within this domain; do not silently
            # drop them from a denominator merely because parsing could not locate them.
            if captures['rejected']:raise ValueError('UNRESOLVED_REJECTED_CAPTURE_ROWS')
            complete.append({'night':night,'domain':domain,'domain_sha256':declaration['domain_ref']['sha256'],
                             'start':start.isoformat(),'end':end.isoformat(),'confirmed_individuals':sum(e['capture_count'] for e in relevant),
                             'event_ids':sorted(e['event_id'] for e in relevant),'declaration_ref':ref,
                             'source_refs':[declaration['domain_ref'],declaration['coverage_evidence_ref']]+source_refs,
                             'qualification_available_at':a.now,'scope':'DECLARED_COMPLETE_DOMAIN_AND_NIGHT'})
        except (ValueError,KeyError,TypeError,OSError) as e:a.need('FULL_OUTCOME_COVERAGE',str(ref),str(e))
    return complete


def _osm(a):
    payloads={};member_count=0;archive=a.root/OSM_ARCHIVE;manifest='evidence/osm/osm_road_evidence_manifest.csv'
    if archive.exists():
        try:
            readme=a.read(OSM_ARCHIVE+'/README.md').decode();expected=re.search(r'Original SHA-256: `([a-f0-9]{64})`',readme).group(1)
            parts=sorted(archive.glob('part_*.b64'))
            if [p.name for p in parts]!=[f'part_{i:03}.b64' for i in range(33)]:raise ValueError('OSM_PART_COUNT')
            encoded=b''.join(a.read(p.relative_to(a.root).as_posix()) for p in parts)
            raw=base64.b64decode(encoded,validate=True)
            if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('OSM_ARCHIVE_SHA')
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                members=z.infolist()
                if len(members)>10000 or sum(m.file_size for m in members)>300*1024*1024:raise ValueError('OSM_ZIP_LIMIT')
                seen=set()
                for m in members:
                    a.tick()
                    pp=PurePosixPath(m.filename)
                    if pp.is_absolute() or '..' in pp.parts or '\\' in m.filename or ':' in m.filename or m.filename in seen or (m.external_attr>>16)&0o170000==0o120000 or m.flag_bits&1:raise ValueError('OSM_ZIP_PATH_OR_TYPE')
                    seen.add(m.filename)
                    if m.is_dir():continue
                    if m.file_size>100*1024*1024:raise ValueError('OSM_MEMBER_LIMIT')
                    member_count+=1
                    data=z.read(m);payloads[(hashlib.sha256(data).hexdigest(),len(data))]=m.filename
            a.check('osm_archive','PASS',OSM_ARCHIVE,'SHA/CRC verified; no bundled code executed')
        except (ValueError,AttributeError,OSError,zipfile.BadZipFile) as e:a.check('osm_archive','FAIL',OSM_ARCHIVE,e)
    rows=[]
    if (a.root/manifest).exists():
        for row in csv.DictReader(io.StringIO(a.read(manifest).decode('utf-8-sig'))):
            a.tick()
            member=payloads.get((row['sha256'],int(row['bytes'])))
            rows.append(dict(declared_path=row['path'],sha256=row['sha256'],resolved_member=member,status='PASS' if member else 'BLOCKED'))
            if not member:a.need('OSM_PAYLOAD',row['path'],'Recover exact payload bytes matching hash and size; never redirect arbitrary absolute paths')
    return {'resolved':sum(r['status']=='PASS' for r in rows),'unresolved':sum(r['status']!='PASS' for r in rows),
            'archive_members':member_count,'unique_payload_hashes':len(payloads),'rows':rows,'source_class':'OpenStreetMap auxiliary',
            'historical_available_at':None,'verified_present_at':a.now if payloads else None}


def _recovered(a):
    path='evidence/master-goal-1642/recovered-response-intake.json';out={'verified_responses':0,'capture_candidates':0,'canonical_labels_admitted':0}
    if (a.root/path).exists():
        for item in a.js(path)['items']:
            a.tick()
            try:
                r=item['receipt'];raw=a.read(r['raw_path']);receipt=a.js(r['evidence_path'])
                if len(raw)!=r['bytes'] or hashlib.sha256(raw).hexdigest()!=r['sha256'] or any(receipt[k]!=r[k] for k in ('raw_path','sha256','bytes','received_at_utc')):raise ValueError('RECOVERED_RESPONSE_RECEIPT')
                out['verified_responses']+=1;a.check('recovered_response','PASS',r['raw_path'],'Saved response representation; not canonical observation')
            except (ValueError,KeyError,OSError) as e:a.check('recovered_response','FAIL',path,e)
    path='evidence/master-goal-1642/recovered_sources/overlap-candidate-review.json'
    if (a.root/path).exists():out['capture_candidates']=len(a.js(path)['capture_candidates'])
    return out


def audit_evidence(root,night,*,verified_at=None,budget_seconds=300):
    validate_night(night);a=Audit(root,verified_at or datetime.now(timezone.utc).isoformat(),budget_seconds)
    try:
        a.tick()
        _receipts(a);sessions=_declarations(a);captures,bad_sources=audit_captures(root,a)
        _raw_logs(a,captures)
        trajectories,points=_trajectories(a);eligible=_sessions(a,sessions,bad_sources,captures['parsed_capture_sources'])
        # Prove capture-outcome completeness for the specific night and spatial
        # domain before a sampled GPX passage may receive a Negative label.
        complete_scopes=_outcome_coverage(a,captures,bad_sources)
        units=_units(a,points,captures,eligible,complete_scopes)
        sampled_coverage = {}
        for point in points:sampled_coverage[point['night_date']]=sampled_coverage.get(point['night_date'],0)+1
        # Persist all qualified units plus requested-night diagnostic coverage; raw+selectors
        # reproduce other unqualified samples without bloating compact recovery artifacts.
        units=[u for u in units if u['night_date']==night or u['label'] is not None]
        if not any(c['night']==night for c in complete_scopes):
            a.need('FULL_OUTCOME_COVERAGE',night,'Source-bound complete domain/night declaration under policies/observation_evidence.json outcome_coverage; session logging is narrower')
        for t in trajectories:
            a.tick()
            if not any(s['source']==t['source'] for s in eligible):a.need('SEARCH_ROLE',t['source'],'Source-bound search interval and applicable complete capture recording policy')
        for event in captures['events']:
            a.tick()
            if not event['canonical_eligible']:a.need('CAPTURE_PROVENANCE',event['event_id'],'Verified quantity/location derivation, source review roles and availability')
        nights=sorted({p['night_date'] for p in points})
        for n in nights:
            a.tick()
            if not any(e['night_date']==n for e in captures['events']) and not any(night_for(s['start'])==n for s in eligible) and not any(c['night']==n for c in complete_scopes):a.need('OUTCOME_LOG',n,'Explicit capture logging evidence; missing capture file is not zero captures')
        osm=_osm(a);recovered=_recovered(a)
        for path,sha in a.consumed.items():
            a.tick()
            if file_hash(safe_path(a.root,path))!=sha:raise ValueError('SOURCE_CHANGED_DURING_AUDIT')
        status='FAIL' if any(c['status']=='FAIL' for c in a.checks) else 'PARTIAL' if a.requirements else 'PASS'
        ledger={'schema_version':'1.0','events':[e for e in captures['events'] if e['canonical_eligible']],
                'known_events_independent_of_forecast_universe':True,
                'denominator_coverage':'ESTABLISHED_FOR_DECLARED_DOMAIN' if any(c['night']==night for c in complete_scopes) else 'NOT_ESTABLISHED',
                'complete_scopes':complete_scopes,
                'coverage_scopes':[{'session_id':s['id'],'start':s['start'].isoformat(),'end':s['end'].isoformat(),
                                    'source_refs':s['refs'],'coverage':'DECLARED_SESSION_ONLY'} for s in eligible]}
        ledger['ledger_sha256']=digest(ledger)
        result=dict(schema_version='1.0',implementation_version=VERSION,operational_night=night,verified_at=a.now,
                    status=status,checks=a.checks,source_manifest=list(a.sources.values()),capture_audit=captures,
                    trajectory_audit=trajectories,sampled_coverage=sampled_coverage,observation_units=units,outcome_ledger=ledger,osm_audit=osm,
                    recovered_source_audit=recovered,input_requirements=a.requirements,input_hashes=a.consumed,
                    scientific_validation='NOT_VALIDATED')
    except (AuditBudgetExceeded,ValueError,KeyError,OSError,TypeError,ET.ParseError) as e:
        runtime=isinstance(e,AuditBudgetExceeded)
        if runtime:
            a.requirements.append(dict(code="AUDIT_BUDGET",kind="RUNTIME_BLOCKED",source_ids=[],criterion=str(e),
                evidence_needed="A bounded fresh run with sufficient audit budget or a smaller explicit input snapshot",
                permitted_next_action="Review runtime limits; do not infer missing data or observation labels"))
        result=dict(schema_version='1.0',implementation_version=VERSION,operational_night=night,verified_at=a.now,status='BLOCKED' if runtime else 'FAIL',
                    checks=a.checks+[{'check':'audit','status':'BLOCKED' if runtime else 'FAIL','reason':str(e)}],input_requirements=a.requirements,
                    input_hashes=a.consumed,source_manifest=list(a.sources.values()),observation_units=[],
                    capture_audit={'events':[],'diagnostic_individuals':0,'rejected':[],'conflicts':[]},
                    trajectory_audit=[],outcome_ledger={'events':[],'denominator_coverage':'NOT_ESTABLISHED'},
                    osm_audit={},recovered_source_audit={})
    result['audit_sha256']=digest(result)
    return result
