"""Versioned individual-token declared-source diagnostics; never an issuer.

evaluate_individual_targets(bundle,*,protocol,budget_seconds=30) accepts exact
builtin JSON only. Closed fields/constants and synthetic tests document all
schemas. Raw UTF-8 is not normalized: physical size/SHA, strict JSON, typed role,
parent/readiness and scope/lineage consistency are checked. No file, callback,
model fitter, source qualifier, identity creator, transport or clock authority.
Protocol and observation bodies explicitly bind OWNER_CAPTURED_HABU_INDIVIDUALS
and owner_id. Unknown roles block; foreign fauna/person/roadkill targets reject.
These are declarations, not species/owner authentication. SourceAdapterv2 must
still verify original row roles before constructing the versioned projections.

One target owns at most one already-verified individual index. The existing
ordered_event_owners kernel is reused without changing EVENT-v1. Inclusive100m
AND600s are fixed. Source/numerical error bounds shrink certain edges and widen
possible edges; they never enlarge a confirmed threshold. Unknown quantities,
identity/precision/scope remain reported denominator uncertainty, not filtered
positives. Engineering caps never supply an unknown biological count bound.

Point recall requires a complete canonical denominator and equal certain/upper
matching counts. Other results are diagnostic bounds, conditional on supplied
source bounds and completeness, never authenticated biological truth. Outside
the future universe stays a miss. Unmatched targets are UNKNOWN unless separate
typed active-search and complete-owner-outcome raw sources cover the WHOLE
100m/600s target region, with ledger linkage. GPS/positive records alone cannot.
FP means an unmatched owner-capture forecast token, never biological absence.

SourceAdapterv2, road anchor generation, real prereveal/confirmation and official
KPI admission remain separate stages. No real scientific policy is selected.
Aware ISO timestamps support at most six fractional digits; finer source times
are rejected rather than silently truncated onto an eligibility boundary.
Raw JSON decimals must retain their value in the supported binary64 decimal
roundtrip representation; higher precision/underflow is rejected, not rounded.
All spatial/temporal decision arithmetic then uses exact decimal rationals,
squared distances and integer-microsecond timestamp differences. Displayed
distance/time floats are approximate diagnostics and never decide an edge.
Each numeric input rational is capped at 2048 numerator/denominator bits (which
includes the smallest positive binary64 decimal); predicates use a fixed number
of arithmetic operations under the shared source/node/pair/deadline work caps.
"""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from decimal import Decimal,InvalidOperation
from fractions import Fraction
import hashlib
import json
import math
import re
import time

from event_matching import ordered_event_owners
from g0_forecast_contract import validate_readiness_graph,ForecastCapacityError

VERSION='habu-individual-time-target-diagnostic-v1'
MAX_INPUT_RATIONAL_BITS=2048  # Includes 5e-324. Fixed JSON/node/pair caps bound work.
JST=timezone(timedelta(hours=9))
READINESS={'source_received_at','derived_at','materialized_at','audited_at'}
BUNDLE={'schema_version','universe_source_id','targets_source_id','ledger_source_id','ascertainment_source_id','sources'}
PROTOCOL={'schema_version','phase','target_semantics','radius_m','tolerance_seconds','crs','distance_method',
    'uncertainty_method','matching_policy','tie_policy','numeric_margins','context','scope','frozen_at',
    'assessment_as_of','lineage','exante_source_sha256','capacities','observation_target','owner_id'}
CONTEXT={'operational_night','cutoff_time','horizon_start','horizon_end'}
LINEAGE={'model_sha256','prediction_sha256','selection_policy_sha256'}
NODE={'id','role','parents','ref','raw_json_utf8','readiness','usable_at'}
CEILINGS=dict(max_targets=100,max_units=120000,max_events=20000,max_individuals=100000,max_sources=4096,
    max_json_bytes=16*1024**2,max_json_nodes=2000000,max_depth=24,max_raw_source_bytes=4*1024**2,
    max_pair_checks=2000000,max_edges=2000000,max_seconds=30)
KINDS=dict(UNIVERSE='FUTURE_UNIVERSE',TARGETS='FROZEN_TARGETS',LEDGER='VERIFIED_INDIVIDUAL_LEDGER',
    ASCERTAINMENT='TARGET_ASCERTAINMENT',ACTIVE_SEARCH='INDEPENDENT_ACTIVE_SEARCH_COVERAGE',
    OUTCOME_SCOPE='COMPLETE_CAPTURE_OUTCOME_COVERAGE',SUPPORT='SUPPORT')
OBSERVATION={'observation_target','owner_id'}
COMMON={'schema_version','kind','context','scope_sha256'}|OBSERVATION


class _Invalid(ValueError):pass
class _Missing(ValueError):pass
class _Capacity(ValueError):pass


class _Budget:
    def __init__(self,seconds):
        kind=type(seconds)
        if (kind is not int and kind is not float) or not 0<seconds<=30:raise _Invalid('INVALID_BUDGET')
        self.start=time.monotonic();self.deadline=self.start+seconds
        self.nodes=0;self.depth_seen=0;self.string_seen=0
        self.limits=dict(CEILINGS);self.pairs=0;self.edges=0
    def check(self):
        if time.monotonic()>=self.deadline:raise _Capacity('SHARED_DEADLINE_EXCEEDED')
    def pair(self):
        self.check()
        if self.pairs>=self.limits['max_pair_checks']:raise _Capacity('PAIR_WORK_CAPACITY_EXCEEDED')
        self.pairs+=1
    def edge(self):
        self.check()
        if self.edges>=self.limits['max_edges']:raise _Capacity('EDGE_CAPACITY_EXCEEDED')
        self.edges+=1


def _fields(value,keys):
    if type(value) is not dict or set(value)!=keys:raise _Invalid('EXACT_FIELDS_REQUIRED')


def _text(value):
    if type(value) is not str or not value or len(value)>128 or not value.isprintable():raise _Invalid('BOUNDED_ID_REQUIRED')
    return value


def _number(value,low=0,high=1e100):
    kind=type(value)
    if (kind is not int and kind is not float) or not low<=value<=high:raise _Invalid('FINITE_NONBOOLEAN_NUMBER_REQUIRED')
    return _q(value)


def _q(value):
    # Owned builtins only; do not use Fraction(float), which changes the source
    # decimal semantics. str(float) is exactly the raw roundtrip value admitted
    # by _source_float. A fixed bit cap bounds every elementary rational op;
    # these predicates use at most a fixed number of sums/products per pair.
    kind=type(value)
    if kind is not int and kind is not float:raise _Invalid('EXACT_BUILTIN_NUMBER_REQUIRED')
    result=Fraction(str(value))
    if result.numerator.bit_length()>MAX_INPUT_RATIONAL_BITS or result.denominator.bit_length()>MAX_INPUT_RATIONAL_BITS:
        raise _Capacity('EXACT_RATIONAL_CAPACITY_EXCEEDED')
    return result


def _seconds(delta):
    return Fraction((delta.days*86400+delta.seconds)*1000000+delta.microseconds,1000000)


def _distance2(a,b):
    return (a[0]-b[0])**2+(a[1]-b[1])**2


def _integer(value,low,high):
    if type(value) is not int or not low<=value<=high:raise _Invalid('BOUNDED_NONBOOLEAN_INTEGER_REQUIRED')
    return value


def _time(value):
    if type(value) is not str or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})',value):
        raise _Invalid('AWARE_MICROSECOND_RESOLUTION_TIME_REQUIRED')
    try:
        stamp=datetime.fromisoformat(value.replace('Z','+00:00'))
        if stamp.utcoffset() is None:raise _Invalid('AWARE_TIME_REQUIRED')
        return stamp.astimezone(timezone.utc)
    except (ValueError,OverflowError):raise _Invalid('AWARE_TIME_REQUIRED') from None


def _sha(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}',value):raise _Invalid('SHA256_REQUIRED')
    return value


def _ids(value,maximum,*,empty=True):
    if type(value) is not list or len(value)>maximum or not empty and not value:raise _Invalid('ID_LIST_REQUIRED')
    for ident in value:_text(ident)
    if len(value)!=len(set(value)):raise _Invalid('DUPLICATE_IDENTITY')
    return value


def _digest(value,budget):
    sha=hashlib.sha256();size=0
    for part in json.JSONEncoder(sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).iterencode(value):
        budget.check();raw=part.encode('utf-8');size+=len(raw)
        if size>budget.limits['max_json_bytes']:raise _Capacity('JSON_BYTE_CAPACITY_EXCEEDED')
        sha.update(raw)
    budget.check();return sha.hexdigest()


def _owned(value,budget,depth=0,active=None):
    budget.check();budget.nodes+=1;budget.depth_seen=max(budget.depth_seen,depth)
    if budget.nodes>budget.limits['max_json_nodes'] or depth>budget.limits['max_depth']:raise _Capacity('JSON_COMPLEXITY_EXCEEDED')
    active=set() if active is None else active;kind=type(value)
    if kind is dict or kind is list:
        if id(value) in active:raise _Invalid('CYCLIC_JSON')
        active.add(id(value))
        if kind is dict:
            result={}
            for key,item in value.items():
                if type(key) is not str or len(key)>256:raise _Invalid('BUILTIN_STRING_KEYS_REQUIRED')
                result[key]=_owned(item,budget,depth+1,active)
        else:result=[_owned(item,budget,depth+1,active) for item in value]
        active.remove(id(value));return result
    if kind is str:
        if len(value)>budget.limits['max_json_bytes']:raise _Capacity('STRING_CAPACITY_EXCEEDED')
        size=len(value.encode('utf-8'));budget.string_seen=max(budget.string_seen,size)
        if size>budget.limits['max_json_bytes']:raise _Capacity('STRING_CAPACITY_EXCEEDED')
        return value
    if kind is bool or value is None:return value
    if kind is int:
        if value.bit_length()>256:raise _Invalid('INTEGER_CAPACITY')
        return value
    if kind is float:
        if not math.isfinite(value):raise _Invalid('NONFINITE_JSON')
        return value
    raise _Invalid('EXACT_BUILTIN_JSON_REQUIRED')


def _same_context(value,expected):
    _fields(value,CONTEXT)
    if value['operational_night']!=expected['operational_night'] or any(_time(value[k])!=_time(expected[k]) for k in CONTEXT-{'operational_night'}):
        raise _Invalid('CONTEXT_SCOPE_MISMATCH')


def _observation(value,protocol):
    target=value['observation_target'];owner=value['owner_id']
    if target is None or target=='UNKNOWN':raise _Missing('OWNER_HABU_CAPTURE_TARGET_NOT_ESTABLISHED')
    if target!='OWNER_CAPTURED_HABU_INDIVIDUALS':raise _Invalid('FOREIGN_OBSERVATION_TARGET')
    if owner is None or owner=='UNKNOWN':raise _Missing('OWNER_CAPTURE_IDENTITY_NOT_ESTABLISHED')
    _text(owner)
    if owner!=protocol['owner_id']:raise _Invalid('OWNER_CAPTURE_IDENTITY_MISMATCH')


def _protocol(p,budget):
    if p is None:raise _Missing('EXPLICIT_PROTOCOL_REQUIRED')
    _fields(p,PROTOCOL)
    required=dict(schema_version='habu-individual-target-protocol-v1',phase='DEVELOPMENT',target_semantics='VERIFIED_INDIVIDUAL_TOKEN',
        crs='EPSG:32652',distance_method='EUCLIDEAN',uncertainty_method='FINITE_BOUNDS_CERTAIN_POSSIBLE_OR_UNKNOWN',
        matching_policy='ORDERED_DFS_MAX_INDIVIDUAL_CARDINALITY_V1',tie_policy='DISTANCE_THEN_TIME_THEN_INDIVIDUAL_ID')
    if any(p[k]!=v for k,v in required.items()):raise _Invalid('SUPPORTED_EXPLICIT_PROTOCOL_REQUIRED')
    _observation(p,p)
    if type(p['radius_m']) is not int or p['radius_m']!=100 or type(p['tolerance_seconds']) is not int or p['tolerance_seconds']!=600:
        raise _Invalid('FIXED_100M_AND_600S_REQUIRED')
    _fields(p['capacities'],set(CEILINGS))
    for name,ceiling in CEILINGS.items():
        if name=='max_seconds':
            if not 0<_number(p['capacities'][name],0,ceiling):raise _Invalid('POSITIVE_BUDGET_REQUIRED')
        else:_integer(p['capacities'][name],1,ceiling)
    budget.limits=dict(p['capacities']);budget.deadline=min(budget.deadline,budget.start+budget.limits['max_seconds'])
    if budget.nodes>budget.limits['max_json_nodes'] or budget.depth_seen>budget.limits['max_depth'] or budget.string_seen>budget.limits['max_json_bytes']:
        raise _Capacity('DECLARED_INPUT_CAPACITY_EXCEEDED')
    _fields(p['numeric_margins'],{'distance_m','time_seconds'})
    for value in p['numeric_margins'].values():_number(value)
    _fields(p['context'],CONTEXT);ctx=p['context']
    night=ctx['operational_night'];_text(night)
    try:
        start=datetime.fromisoformat(night+'T07:00:00+09:00');end=start+timedelta(days=1)
    except (ValueError,OverflowError):raise _Invalid('REPRESENTABLE_OPERATIONAL_NIGHT_REQUIRED') from None
    if start.date().isoformat()!=night:raise _Invalid('OPERATIONAL_NIGHT_REQUIRED')
    cutoff,lower,upper=(_time(ctx[k]) for k in ('cutoff_time','horizon_start','horizon_end'))
    if not start<=cutoff<lower<upper<=end:raise _Invalid('POSTCUTOFF_NIGHT_HORIZON_REQUIRED')
    if not _time(p['frozen_at'])<cutoff or not upper<_time(p['assessment_as_of']):raise _Invalid('FREEZE_ASSESSMENT_CHRONOLOGY')
    _fields(p['scope'],{'crs','bbox_utm'});box=p['scope']['bbox_utm']
    if p['scope']['crs']!='EPSG:32652' or type(box) is not list or len(box)!=4:raise _Invalid('EXPLICIT_UTM52_SCOPE_REQUIRED')
    x0,y0,x1,y1=(_number(v,0,10000000) for v in box)
    if not 100000<=x0<x1<=900000 or not 0<=y0<y1<=10000000:raise _Invalid('SCOPE_BOUNDARY_INVALID')
    _fields(p['lineage'],LINEAGE)
    for value in p['lineage'].values():_sha(value)
    _fields(p['exante_source_sha256'],{'universe','targets'})
    for value in p['exante_source_sha256'].values():_sha(value)
    budget.check();return start.astimezone(timezone.utc),cutoff,lower,upper


def _pairs(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise _Invalid('DUPLICATE_SOURCE_JSON_KEY')
        value[key]=item
    return value


def _source_float(token):
    value=float(token)
    try:exact=math.isfinite(value) and Decimal(token)==Decimal(str(value))
    except InvalidOperation:exact=False
    if not exact:
        raise _Invalid('UNSUPPORTED_SOURCE_NUMERIC_PRECISION')
    return value


def _sources(bundle,p,budget):
    nodes=bundle['sources']
    if type(nodes) is not list:raise _Invalid('SOURCE_LIST_REQUIRED')
    if not nodes:raise _Missing('TYPED_RAW_SOURCES_NOT_SUPPLIED')
    if len(nodes)>budget.limits['max_sources']:raise _Capacity('SOURCE_CAPACITY_EXCEEDED')
    sources={};bodies={};paths=set()
    for source in nodes:
        budget.check();_fields(source,NODE);ident=_text(source['id'])
        if ident in sources:raise _Invalid('DUPLICATE_SOURCE_ID')
        role=source['role']
        if type(role) is not str or role not in KINDS:raise _Invalid('SOURCE_ROLE_REQUIRED')
        _ids(source['parents'],budget.limits['max_sources']);_fields(source['ref'],{'path','sha256','size_bytes'})
        ref=source['ref'];path=ref['path']
        if type(path) is not str or not path or len(path)>512 or path.startswith('/') or '\\' in path or ':' in path or any(
            part in ('','.','..') or part.casefold() in {'sealed','confirmation','original','incoming'} for part in path.split('/')):
            raise _Invalid('UNSAFE_SOURCE_REFERENCE')
        if path in paths:raise _Invalid('DUPLICATE_SOURCE_PATH')
        paths.add(path);text=source['raw_json_utf8']
        if type(text) is not str:raise _Invalid('SOURCE_UTF8_STRING_REQUIRED')
        if len(text)>budget.limits['max_raw_source_bytes']:raise _Capacity('RAW_SOURCE_CAPACITY_EXCEEDED')
        raw=text.encode('utf-8');budget.check()
        if len(raw)>budget.limits['max_raw_source_bytes']:raise _Capacity('RAW_SOURCE_CAPACITY_EXCEEDED')
        if type(ref['size_bytes']) is not int or ref['size_bytes']!=len(raw) or _sha(ref['sha256'])!=hashlib.sha256(raw).hexdigest():
            raise _Invalid('PHYSICAL_SOURCE_BYTE_MISMATCH')
        _fields(source['readiness'],READINESS)
        for stamp in source['readiness'].values():_time(stamp)
        _time(source['usable_at'])
        body=_owned(json.loads(raw,object_pairs_hook=_pairs,parse_float=_source_float),budget)
        if type(body) is not dict or body.get('schema_version')!='habu-individual-target-source-v1' or body.get('kind')!=KINDS[role]:
            raise _Invalid('TYPED_SOURCE_ROLE_BODY_MISMATCH')
        if role=='SUPPORT':_fields(body,{'schema_version','kind','details'})
        sources[ident]=source;bodies[ident]=body
    graph=[{k:s[k] for k in ('id','parents','readiness','usable_at')} for s in nodes]
    validated=validate_readiness_graph(graph,_time(p['assessment_as_of']),check=budget.check)
    roles={};roots={};raw_bits={}
    for ident in validated['topological_order']:
        budget.check();roles[ident]={sources[ident]['role']}|set().union(*(roles[parent] for parent in sources[ident]['parents']))
        bits=0
        for parent in sources[ident]['parents']:bits|=roots[parent]
        if not sources[ident]['parents']:
            sha=sources[ident]['ref']['sha256']
            if sha not in raw_bits:raw_bits[sha]=1<<len(raw_bits)
            bits=raw_bits[sha]
        roots[ident]=bits
    selected={}
    for field,role in [('universe_source_id','UNIVERSE'),('targets_source_id','TARGETS'),('ledger_source_id','LEDGER'),('ascertainment_source_id','ASCERTAINMENT')]:
        ident=bundle[field]
        if field=='ascertainment_source_id' and ident is None:continue
        if type(ident) is not str or ident not in sources:raise _Missing('REQUIRED_TYPED_SOURCE_NOT_SUPPLIED')
        if sources[ident]['role']!=role:raise _Invalid('PRIMARY_SOURCE_ROLE_MISMATCH')
        selected[role]=ident
    for role in ('UNIVERSE','TARGETS','LEDGER','ASCERTAINMENT'):
        actual={ident for ident,node in sources.items() if node['role']==role}
        expected={selected[role]} if role in selected else set()
        if actual!=expected:
            raise _Invalid('DUPLICATE_OR_UNBOUND_PRIMARY_SOURCE_ROLE')
    reachable=set();todo=list(selected.values())
    while todo:
        budget.check();ident=todo.pop()
        if ident not in reachable:reachable.add(ident);todo.extend(sources[ident]['parents'])
    if reachable!=set(sources):raise _Invalid('UNCONSUMED_SOURCE_NODE')
    if selected['UNIVERSE'] not in sources[selected['TARGETS']]['parents']:
        raise _Invalid('TARGET_UNIVERSE_READINESS_PARENT_REQUIRED')
    cutoff=_time(p['context']['cutoff_time'])
    for role in ('UNIVERSE','TARGETS'):
        source=sources[selected[role]]
        if roles[selected[role]]-{'UNIVERSE','TARGETS','SUPPORT'}:raise _Invalid('EXANTE_SOURCE_DEPENDS_ON_OUTCOMES')
        if _time(source['usable_at'])>=cutoff:raise _Missing('EXANTE_SOURCE_NOT_BEFORE_CUTOFF')
        if source['ref']['sha256']!=p['exante_source_sha256'][role.lower()]:raise _Invalid('EXANTE_PROTOCOL_SOURCE_BINDING_MISMATCH')
    if _time(p['frozen_at'])<_time(sources[selected['TARGETS']]['usable_at']):raise _Invalid('FREEZE_PRECEDES_PHYSICAL_TARGET_READINESS')
    return sources,bodies,roles,roots,selected


def _header(body,p,fields):
    _fields(body,fields);_same_context(body['context'],p['context'])
    if OBSERVATION<=fields:_observation(body,p)
    if 'scope_sha256' in body and body['scope_sha256']!=_simple_scope_sha(p):raise _Invalid('SOURCE_SCOPE_HASH_MISMATCH')


def _simple_scope_sha(p):
    return hashlib.sha256(json.dumps(p['scope'],sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def _position(value):
    if value is None:return None
    _fields(value,{'crs','x_m','y_m','uncertainty_radius_m'})
    if value['crs']!='EPSG:32652':raise _Invalid('POSITION_CRS_MISMATCH')
    x=_number(value['x_m'],100000,900000);y=_number(value['y_m'],0,10000000)
    r=None if value['uncertainty_radius_m'] is None else _number(value['uncertainty_radius_m'])
    return x,y,r


def _universe(body,p,times,budget):
    _header(body,p,{'schema_version','kind','context','scope','units'})
    if _digest(body['scope'],budget)!=_digest(p['scope'],budget):raise _Invalid('UNIVERSE_SCOPE_MISMATCH')
    rows=body['units']
    if type(rows) is not list:raise _Invalid('UNIVERSE_UNITS_REQUIRED')
    if len(rows)>budget.limits['max_units']:raise _Capacity('UNIVERSE_CAPACITY_EXCEEDED')
    by_id={};physical=set();night,cutoff,start,end=times;x0,y0,x1,y1=map(_q,p['scope']['bbox_utm'])
    for row in rows:
        budget.check();_fields(row,{'row_id','cell_x','cell_y','window_start_jst'})
        ident=_text(row['row_id']);cx=_integer(row['cell_x'],1000,8999);cy=_integer(row['cell_y'],0,99999)
        stamp=_time(row['window_start_jst']);index=_seconds(stamp-night)//600
        if stamp.second or stamp.microsecond or stamp.minute%10 or not cutoff<stamp or not start<=stamp<stamp+timedelta(seconds=600)<=end:
            raise _Invalid('POSTCUTOFF_WHOLE_FUTURE_UNIT_REQUIRED')
        if not (cx*100<x1 and (cx+1)*100>x0) or not (cy*100<y1 and (cy+1)*100>y0):
            raise _Invalid('UNIVERSE_CELL_OUTSIDE_SCOPE')
        key=cx,cy,index
        if ident in by_id or key in physical:raise _Invalid('DUPLICATE_FUTURE_UNIT')
        by_id[ident]=(cx,cy,stamp);physical.add(key)
    return by_id,physical


def _targets(body,p,rows,universe_sha,times,budget):
    _header(body,p,COMMON|{'produced',*LINEAGE,'universe_source_sha256','frozen_at','targets'})
    if type(body['produced']) is not bool:raise _Invalid('EXPLICIT_TARGET_PRODUCED_BOOLEAN_REQUIRED')
    if body['universe_source_sha256']!=universe_sha or any(body[k]!=p['lineage'][k] for k in LINEAGE):raise _Invalid('TARGET_PREDICTION_LINEAGE_MISMATCH')
    if _time(body['frozen_at'])!=_time(p['frozen_at']):raise _Invalid('TARGET_FREEZE_BINDING_MISMATCH')
    values=body['targets']
    if type(values) is not list:raise _Invalid('TARGET_LIST_REQUIRED')
    if len(values)>budget.limits['max_targets']:raise _Capacity('TARGET_CAPACITY_EXCEEDED')
    if not body['produced']:
        if values:raise _Invalid('UNPRODUCED_TARGET_SET_NOT_EMPTY')
        raise _Missing('TARGET_SET_NOT_PRODUCED')
    targets=[];ids=set();units=set();_,cutoff,start,end=times
    for row in values:
        budget.check();_fields(row,{'target_id','source_unit_id','predicted_time','time_uncertainty_seconds','position'})
        ident=_text(row['target_id']);unit=_text(row['source_unit_id'])
        if ident in ids or unit in units:raise _Invalid('DUPLICATE_TARGET_OR_UNIT_TOKEN')
        if unit not in rows:raise _Invalid('TARGET_UNIT_NOT_IN_FROZEN_UNIVERSE')
        stamp=_time(row['predicted_time']);cx,cy,window=rows[unit]
        if not cutoff<stamp or not start<=stamp<end or not window<=stamp<window+timedelta(seconds=600):raise _Invalid('TARGET_TIME_OUTSIDE_SOURCE_UNIT')
        tau=None if row['time_uncertainty_seconds'] is None else _number(row['time_uncertainty_seconds'])
        point=_position(row['position'])
        if point is not None and (math.floor(point[0]/100),math.floor(point[1]/100))!=(cx,cy):raise _Invalid('TARGET_POINT_OUTSIDE_SOURCE_CELL')
        ids.add(ident);units.add(unit);targets.append(dict(id=ident,time=stamp,tau=tau,position=point,source=row))
    return sorted(targets,key=lambda t:t['id'])


def _scope(point,stamp,tau,available,p,times):
    _,cutoff,start,end=times;x0,y0,x1,y1=map(_q,p['scope']['bbox_utm'])
    spatial=point is not None and point[2] is not None
    if spatial:
        x,y,r=point;certain=x0<=x-r and x+r<x1 and y0<=y-r and y+r<y1
        possible=x+r>=x0 and x-r<x1 and y+r>=y0 and y-r<y1
    else:certain=False;possible=True
    temporal=stamp is not None and tau is not None
    if temporal:
        low=_seconds(stamp-start)-tau;high=_seconds(stamp-start)+tau
        if available is not None:high=min(high,_seconds(available-start))
        certain=certain and low>=0 and high<_seconds(end-start) and _seconds(stamp-cutoff)-tau>0
        possible=possible and high>=0 and low<_seconds(end-start) and _seconds(stamp-cutoff)+tau>0 and low<=high
    else:certain=False
    return certain,possible


def _eligibility(point,stamp,tau,available,keys,times,budget):
    if not keys:return False,False
    if point is None or point[2] is None or stamp is None or tau is None:return False,True
    x,y,r=point;night=times[0]
    a=math.floor((_seconds(stamp-night)-tau)/600)
    upper=_seconds(stamp-night)+tau
    if available is not None:upper=min(upper,_seconds(available-night))
    b=math.floor(upper/600)
    xs=(math.floor((x-r)/100),math.floor((x+r)/100));ys=(math.floor((y-r)/100),math.floor((y+r)/100))
    count=(xs[1]-xs[0]+1)*(ys[1]-ys[0]+1)*(b-a+1)
    if count>budget.limits['max_pair_checks']:return False,True  # Conservative unknown bound, no inferred misses.
    certain=True;possible=False
    for cx in range(xs[0],xs[1]+1):
        for cy in range(ys[0],ys[1]+1):
            for window in range(a,b+1):
                budget.pair();present=(cx,cy,window) in keys
                certain=certain and present;possible=possible or present
    return certain,possible


def _events(body,p,node_usable,keys,times,budget):
    _header(body,p,COMMON|{'scope_declaration','events'})
    if body['scope_declaration'] not in ('DECLARED_COMPLETE','UNKNOWN','INCOMPLETE'):raise _Invalid('EXPLICIT_LEDGER_SCOPE_STATUS_REQUIRED')
    values=body['events']
    if type(values) is not list:raise _Invalid('EVENT_LIST_REQUIRED')
    if len(values)>budget.limits['max_events']:raise _Capacity('EVENT_CAPACITY_EXCEEDED')
    events=[];ids=set();groups=set();verified=0;minimum=0;maximum=0;unknown_counts=0;incomplete_ids=0;unscorable=0;outside=[];unknown_upper=0
    for row in values:
        budget.check();_fields(row,{'event_id','operational_night','recorded_time','time_uncertainty_seconds','position',
            'verified_individual_ids','declared_count','individual_ids_complete','outcome_available_at'})
        ident=_text(row['event_id'])
        if ident in groups:raise _Invalid('DUPLICATE_CANONICAL_EVENT')
        groups.add(ident)
        if row['operational_night']!=p['context']['operational_night']:raise _Invalid('FOREIGN_LEDGER_NIGHT')
        if type(row['individual_ids_complete']) is not bool:raise _Invalid('EXPLICIT_ID_COMPLETENESS_REQUIRED')
        names=[] if row['verified_individual_ids'] is None else _ids(row['verified_individual_ids'],budget.limits['max_individuals'])
        if row['verified_individual_ids'] is None and row['individual_ids_complete']:raise _Invalid('COMPLETE_IDS_NOT_SUPPLIED')
        if ids&set(names):raise _Invalid('DUPLICATE_CANONICAL_INDIVIDUAL')
        ids.update(names);verified+=len(names)
        if verified>budget.limits['max_individuals']:raise _Capacity('INDIVIDUAL_CAPACITY_EXCEEDED')
        count=row['declared_count']
        if count is not None:_integer(count,1,budget.limits['max_individuals'])
        if count is not None and count<len(names) or row['individual_ids_complete'] and (count is None or count!=len(names)):
            raise _Invalid('INDIVIDUAL_MULTIPLICITY_CONTRADICTION')
        if count is None:unknown_counts+=1
        if not row['individual_ids_complete']:incomplete_ids+=1
        stamp=None if row['recorded_time'] is None else _time(row['recorded_time'])
        tau=None if row['time_uncertainty_seconds'] is None else _number(row['time_uncertainty_seconds'])
        if stamp is None and tau is not None:raise _Invalid('UNKNOWN_TIME_HAS_NO_FINITE_PRECISION')
        point=_position(row['position']);available=_time(row['outcome_available_at'])
        if available>node_usable or stamp is not None and tau is not None and _seconds(stamp-available)>tau:
            raise _Invalid('OUTCOME_SOURCE_PRECEDES_OBSERVATION')
        sure,possible=_scope(point,stamp,tau,available,p,times)
        if not possible:raise _Invalid('EVENT_CONTRADICTS_DECLARED_SCOPE')
        ec,ep=_eligibility(point,stamp,tau,available,keys,times,budget)
        if sure:minimum+=len(names)
        maximum=None if maximum is None or count is None else maximum+count
        if maximum is not None and maximum>budget.limits['max_individuals']:raise _Capacity('DECLARED_COUNT_CAPACITY_EXCEEDED')
        if not sure or point is None or point[2] is None or stamp is None or tau is None:unscorable+=len(names)
        if sure and not ep:outside.extend(names)
        if ep and count is None:unknown_upper=None
        elif ep and unknown_upper is not None:unknown_upper+=count-len(names)
        for name in names:
            events.append(dict(id=name,event_id=ident,time=stamp,tau=tau,position=point,available=available,
                scope_certain=sure,eligible_certain=ec,eligible_possible=ep))
    complete=body['scope_declaration']=='DECLARED_COMPLETE'
    if not complete:maximum=None;unknown_upper=None
    return events,dict(registered_verified_individual_count=verified,denominator_min=minimum,denominator_max=maximum,
        denominator_complete=complete and incomplete_ids==0 and unknown_counts==0 and minimum==maximum,
        unknown_count_event_count=unknown_counts,identity_incomplete_event_count=incomplete_ids,
        unscorable_individual_count=unscorable,outside_eligible_individual_ids=sorted(outside),
        unknown_identity_match_upper=unknown_upper,event_ids=groups)


def _match(targets,individuals,p,times,budget):
    certain=[];possible=[];edges_equal=True
    for target in targets:
        c=[];q=[];ts,tp=_scope(target['position'],target['time'],target['tau'],None,p,times)
        for index,event in enumerate(individuals):
            budget.pair()
            if not event['eligible_possible']:continue
            d2=None if target['position'] is None or event['position'] is None else _distance2(target['position'],event['position'])
            dt=None if event['time'] is None else abs(_seconds(target['time']-event['time']))
            radii=None if d2 is None or target['position'][2] is None or event['position'][2] is None else target['position'][2]+event['position'][2]
            tau=None if target['tau'] is None or event['tau'] is None else target['tau']+event['tau']
            md,mt=(_q(p['numeric_margins'][k]) for k in ('distance_m','time_seconds'))
            key=(d2 is None,d2 if d2 is not None else 0,dt is None,dt if dt is not None else 0,event['id'],index)
            possible_edge=tp and (d2 is None or radii is None or d2<=(100+radii+md)**2) and (dt is None or tau is None or dt<=600+tau+mt)
            room=None if radii is None else 100-radii-md
            certain_edge=(ts and event['scope_certain'] and event['eligible_certain'] and d2 is not None and room is not None and room>=0 and dt is not None and tau is not None
                and d2<=room**2 and dt+tau+mt<=600)
            if certain_edge:budget.edge();c.append(key)
            if possible_edge:budget.edge();q.append(key)
        c.sort();q.sort();certain.append([v[-1] for v in c]);possible.append([v[-1] for v in q]);edges_equal=edges_equal and certain[-1]==possible[-1]
    lower=ordered_event_owners(certain,check=budget.check);upper=ordered_event_owners(possible,check=budget.check)
    if len(lower)>len(upper):raise _Invalid('MATCHING_BOUNDS_CONTRADICTION')
    matching=[]
    for individual,target in sorted(lower.items(),key=lambda v:targets[v[1]]['id']):
        budget.check();t=targets[target];event=individuals[individual]
        matching.append(dict(target_id=t['id'],individual_id=event['id'],event_id=event['event_id'],
            distance_m=math.hypot(t['position'][0]-event['position'][0],t['position'][1]-event['position'][1]),
            time_delta_seconds=abs((t['time']-event['time']).total_seconds())))
    return matching,len(upper),edges_equal


def _coverage_records(body,node_usable,p,budget):
    values=body['coverage']
    if type(values) is not list or len(values)>budget.limits['max_targets']:raise _Invalid('BOUNDED_COVERAGE_REQUIRED')
    records=[];ids=set();x0,y0,x1,y1=map(_q,p['scope']['bbox_utm']);start=_time(p['context']['horizon_start']);end=_time(p['context']['horizon_end'])
    for row in values:
        budget.check();_fields(row,{'coverage_id','center_x_m','center_y_m','radius_m','start','end'})
        ident=_text(row['coverage_id'])
        if ident in ids:raise _Invalid('DUPLICATE_COVERAGE_ID')
        ids.add(ident);x=_number(row['center_x_m'],100000,900000);y=_number(row['center_y_m'],0,10000000);r=_number(row['radius_m'])
        a,b=_time(row['start']),_time(row['end'])
        if not a<b<=node_usable or not start<=a<b<=end or not x0<=x-r<=x+r<x1 or not y0<=y-r<=y+r<y1:
            raise _Invalid('COVERAGE_SOURCE_SCOPE_OR_CLOCK_CONTRADICTION')
        records.append((x,y,r,a,b))
    return records


def _ascertained(bundle,p,sources,bodies,roles,roots,selected,targets,ledger_sha,event_ids,budget):
    cache={}
    # Validate all supplied proof records before judging their independence or
    # applicability. An unused/shared-root proof cannot hide a contradiction.
    for key,source in sources.items():
        role=source['role']
        if role not in ('ACTIVE_SEARCH','OUTCOME_SCOPE'):continue
        budget.check();value=bodies[key]
        fields=COMMON|{'coverage_semantics','coverage'}|({'independence_basis'} if role=='ACTIVE_SEARCH' else {'ledger_source_sha256','event_ids'})
        _header(value,p,fields)
        if role=='ACTIVE_SEARCH':
            if value['coverage_semantics']!='WHOLE_REGION_ACTIVE_HABU_SEARCH' or value['independence_basis']!='SEPARATE_SEARCH_RECORD_NOT_CAPTURE_OR_GPS_INFERENCE':raise _Invalid('MEASURED_INDEPENDENT_ACTIVE_SEARCH_REQUIRED')
        else:
            if selected['LEDGER'] not in source['parents']:raise _Invalid('OUTCOME_LEDGER_READINESS_PARENT_REQUIRED')
            if value['coverage_semantics']!='COMPLETE_OWNER_CAPTURE_OUTCOMES' or value['ledger_source_sha256']!=ledger_sha or set(_ids(value['event_ids'],budget.limits['max_events']))!=event_ids:
                raise _Invalid('COMPLETE_OUTCOME_LEDGER_BINDING_REQUIRED')
        cache[key]=_coverage_records(value,_time(source['usable_at']),p,budget)
    if 'ASCERTAINMENT' not in selected:return set()
    ident=selected['ASCERTAINMENT'];body=bodies[ident]
    _header(body,p,COMMON|{'ledger_source_sha256','records'})
    if body['ledger_source_sha256']!=ledger_sha:raise _Invalid('ASCERTAINMENT_LEDGER_HASH_MISMATCH')
    records=body['records']
    if type(records) is not list or len(records)>budget.limits['max_targets']:raise _Invalid('ASCERTAINMENT_RECORDS_REQUIRED')
    by_id={t['id']:t for t in targets};seen=set();covered=set()
    for row in records:
        budget.check();_fields(row,{'target_id','active_search_source_id','outcome_source_id'})
        tid=_text(row['target_id'])
        if tid in seen or tid not in by_id:raise _Invalid('DUPLICATE_OR_FOREIGN_ASCERTAINMENT_TARGET')
        seen.add(tid);active,outcome=row['active_search_source_id'],row['outcome_source_id']
        if type(active) is not str or type(outcome) is not str or active not in sources or outcome not in sources:
            continue
        if active==outcome or sources[active]['role']!='ACTIVE_SEARCH' or sources[outcome]['role']!='OUTCOME_SCOPE':continue
        if active not in sources[ident]['parents'] or outcome not in sources[ident]['parents']:raise _Invalid('ASCERTAINMENT_PARENT_BINDING_MISMATCH')
        if selected['LEDGER'] not in sources[outcome]['parents']:raise _Invalid('OUTCOME_LEDGER_READINESS_PARENT_REQUIRED')
        if roles[active]&{'LEDGER','OUTCOME_SCOPE','TARGETS'}:continue
        if roots[active]&roots[selected['LEDGER']] or roots[active]&roots[outcome]:continue
        proof=[cache[active],cache[outcome]]
        target=by_id[tid];point=target['position'];tau=target['tau']
        if point is None or point[2] is None or tau is None:continue
        x,y,r=point
        def whole(records):
            for cx,cy,cr,a,b in records:
                budget.pair()
                md,mt=(_q(p['numeric_margins'][k]) for k in ('distance_m','time_seconds'))
                room=cr-100-r-md
                if (room>=0 and _distance2((x,y),(cx,cy))<=room**2 and
                    _seconds(target['time']-a)>=600+tau+mt and
                    _seconds(b-target['time'])>=600+tau+mt):return True
            return False
        if all(whole(records) for records in proof):covered.add(tid)
    return covered


def _empty():
    return dict(schema_version=VERSION,execution_status='FAIL',blockers=[],individual_recall=None,matched_individuals=None,
        denominator_min=None,denominator_max=None,matching_bounds=None,recall_bounds=None,matching=[],
        registered_verified_individual_count=None,unknown_count_event_count=None,identity_incomplete_event_count=None,unscorable_individual_count=None,
        unscorable_target_count=None,
        false_positives=None,precision=None,unknown_target_ids=[],source_authentication='NOT_ATTESTED',prereveal_authentication='NOT_ATTESTED',
        statistical_adequacy='NOT_ASSESSED',scientific_status='NOT_VALIDATED',source_authorized=False,prereveal_authorized=False,
        fit_authorized=False,selection_authorized=False,scientific_authorized=False,confirmation_authorized=False,
        official_100m_10min_kpi_computed=False,official_issuance_authorized=False,production_authorized=False)


def evaluate_individual_targets(bundle,*,protocol,budget_seconds=30):
    result=_empty()
    try:
        budget=_Budget(budget_seconds);bundle,p=_owned([bundle,protocol],budget);_digest([bundle,p],budget)
        times=_protocol(p,budget);_digest([bundle,p],budget)
        if bundle is None:raise _Missing('SOURCE_BOUND_BUNDLE_NOT_SUPPLIED')
        _fields(bundle,BUNDLE)
        if bundle['schema_version']!='habu-individual-target-evaluation-input-v1':raise _Invalid('BUNDLE_SCHEMA_REQUIRED')
        sources,bodies,roles,roots,selected=_sources(bundle,p,budget)
        universe_id,target_id,ledger_id=(selected[r] for r in ('UNIVERSE','TARGETS','LEDGER'))
        rows,keys=_universe(bodies[universe_id],p,times,budget)
        targets=_targets(bodies[target_id],p,rows,sources[universe_id]['ref']['sha256'],times,budget)
        individuals,counts=_events(bodies[ledger_id],p,_time(sources[ledger_id]['usable_at']),keys,times,budget)
        matching,possible,equal_edges=_match(targets,individuals,p,times,budget);certain=len(matching)
        target_unscorable=sum(not _scope(t['position'],t['time'],t['tau'],None,p,times)[0] for t in targets)
        extra=counts.pop('unknown_identity_match_upper');event_ids=counts.pop('event_ids');complete=counts.pop('denominator_complete')
        upper=len(targets) if extra is None else min(len(targets),possible+extra)
        minimum,maximum=counts['denominator_min'],counts['denominator_max']
        if maximum is not None:upper=min(upper,maximum)
        if upper<certain:raise _Invalid('MATCHING_DENOMINATOR_BOUNDS_CONTRADICTION')
        point=certain/minimum if complete and minimum>0 and certain==upper and target_unscorable==0 else None
        lower= certain/maximum if maximum else 0. if maximum is None else None
        high=min(1.,upper/minimum) if minimum else 1. if maximum is None or maximum>0 else None
        recalled=None if lower is None or high is None else dict(lower=lower,upper=high)
        covered=_ascertained(bundle,p,sources,bodies,roles,roots,selected,targets,sources[ledger_id]['ref']['sha256'],event_ids,budget)
        matched={r['target_id'] for r in matching};unmatched={t['id'] for t in targets}-matched
        fp=unmatched&covered if complete and equal_edges else set();unknown=unmatched-fp
        result.update(**counts,execution_status='DIAGNOSTIC_COMPUTED' if complete and certain==upper and target_unscorable==0 else 'PARTIAL_DIAGNOSTIC',
            individual_recall=point,matched_individuals=certain,matching_bounds=dict(certain=certain,possible=upper),recall_bounds=recalled,
            unscorable_target_count=target_unscorable,
            matching=matching,unknown_target_ids=sorted(unknown),false_positive_target_ids=sorted(fp),
            false_positives=len(fp) if not unknown else None,precision=certain/(certain+len(fp)) if not unknown and certain+len(fp)>0 else None,
            full_canonical_denominator=complete,denominator_status='DECLARED_COMPLETE_CANONICAL' if complete else 'UNKNOWN_OR_PARTIAL',
            bounds_semantics='CONSERVATIVE_NOT_NECESSARILY_SHARP_CONDITIONAL_ON_POSITIVE_DENOMINATOR',
            decision_arithmetic='EXACT_DECIMAL_RATIONAL_SQUARED_DISTANCE_AND_INTEGER_MICROSECONDS',
            displayed_matching_diagnostics='APPROXIMATE_BINARY64_NOT_USED_FOR_DECISIONS',
            input_digests=dict(bundle=_digest(bundle,budget),protocol=_digest(p,budget)),
            source_sha256={key:node['ref']['sha256'] for key,node in sorted(sources.items())},
            limitations=['DECLARED_SOURCE_BOUNDS_NOT_AUTHENTICATED_PRECISION','MATCHING_MAX_CARDINALITY_NOT_GLOBAL_MINIMUM_COST',
                'UNKNOWN_NOT_EXCLUDED_FROM_DENOMINATOR','FP_OWNER_CAPTURE_TOKEN_NOT_BIOLOGICAL_ABSENCE',
                'SOURCE_ADAPTER_V2_ROAD_GENERATOR_PREREVEAL_CONFIRMATION_OFFICIAL_ADMISSION_NOT_IMPLEMENTED'],
            work=dict(pair_checks=budget.pairs,stored_edges=budget.edges))
        if not complete:result['blockers'].append('CANONICAL_DENOMINATOR_OR_SCOPE_INCOMPLETE')
        if certain!=upper:result['blockers'].append('MATCHING_UNRESOLVED_WITHIN_SOURCE_OR_NUMERICAL_BOUNDS')
        if target_unscorable:result['blockers'].append('TARGET_PRECISION_OR_SCOPE_UNRESOLVED')
        result['receipt_sha256']=_digest(result,budget)
        _digest(result,budget)  # Include the returned seal in the output byte cap.
        budget.check()
    except _Missing as exc:result.update(execution_status='DATA_BLOCKED',blockers=[str(exc)])
    except _Capacity as exc:result.update(execution_status='RUNTIME_BLOCKED',blockers=[str(exc)])
    except ForecastCapacityError:result.update(execution_status='RUNTIME_BLOCKED',blockers=['READINESS_GRAPH_CAPACITY_EXCEEDED'])
    except _Invalid as exc:result.update(execution_status='FAIL',blockers=[str(exc)])
    except (ValueError,TypeError,KeyError,IndexError,OverflowError,RecursionError,UnicodeError):result.update(execution_status='FAIL',blockers=['SOURCE_OR_PROTOCOL_VALIDATION_FAILED'])
    if result['execution_status'] in ('FAIL','DATA_BLOCKED','RUNTIME_BLOCKED'):
        status,blockers=result['execution_status'],result['blockers']
        result=_empty();result.update(execution_status=status,blockers=blockers)
    return result
