"""Pure planned intent projection; never measured effort or G0/source authority.

Only supplied original bytes are hashed. Domain/code physical-file declarations
remain caller dependencies. No files, network, current clock, model or publisher
are accessed; every operation shares the caller's existing prospective context.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import re

from g0_forecast_contract import validate_readiness
from master_contracts import validate_night
from prospective_inputs import InputCapacityError, ProspectiveReadContext, READINESS_FIELDS

VERSION='habu-g0-planned-effort-projection-v1'
SOURCE_VERSION='habu-planned-search-source-v1'
DOMAIN_VERSION='habu-planned-effort-domain-v1'
CODE_PATH='src/g0_planned_effort_projection.py'
MAX_RAW_BYTES=4*1024**2
MAX_INPUT_BYTES=MAX_OUTPUT_BYTES=16*1024**2
MAX_JSON_NODES=2_000_000
MAX_DEPTH=12
MAX_STRING=4096
MAX_ALLOCATIONS=20_000
MAX_OUTPUT_ROWS=120_000
MAX_DOMAIN_CELLS=100_000
MAX_WINDOWS=144
MAX_DOMAIN_ROWS=4_000_000
DOMAIN_FIELDS={'schema_version','operational_night','cutoff_time','horizon','cells'}
IDENTITY_FIELDS={'owner_id','observer_id','method_version','crew_size'}
SOURCE_FIELDS={'schema_version','plan_id','revision_id','issued_at','purpose','operational_night',
               'domain_sha256','horizon','coverage','allocations'} | IDENTITY_FIELDS
ALLOCATION_FIELDS={'allocation_id','cell_x','cell_y','start','end','planned_active_search_seconds'}
SHA256=re.compile(r'[a-f0-9]{64}\Z')
INTEGER=re.compile(r'-?(?:0|[1-9][0-9]*)\Z')
JST=timezone(timedelta(hours=9))


class PlannedEffortCapacityError(InputCapacityError):
    """Resource blocked; no truncated table or partial success is returned."""


class PlannedEffortCapabilityBlocked(ValueError):
    """A valid declared capability outside this single-observer implementation."""


def _cap(count,limit,label):
    if count>limit:
        raise PlannedEffortCapacityError('CAPACITY_BLOCKED: planned effort '+label)


def _fields(value,fields):
    if type(value) is not dict or set(value)!=fields:
        raise ValueError('Exact planned-effort fields required')


def _text(value,limit=256):
    if type(value) is not str or not value.strip() or len(value)>limit:
        raise ValueError('Bounded nonempty planned-effort string required')
    return value


def _hash(value):
    if type(value) is not str or not SHA256.fullmatch(value):
        raise ValueError('Explicit planned-effort SHA-256 required')
    return value


def _integer(value,low,high):
    if type(value) is not int or not low<=value<=high:
        raise ValueError('Planned-effort integer outside its physical bounds')
    return value


def _stamp(value,*,whole=False):
    _text(value,64)
    try:
        stamp=datetime.fromisoformat(value.replace('Z','+00:00'))
        if stamp.utcoffset() is None or (whole and stamp.microsecond):
            raise ValueError('Aware whole-second planned interval required')
        return stamp.astimezone(timezone.utc)
    except (OverflowError,TypeError) as exc:
        raise ValueError('Unsupported planned-effort timestamp') from exc


def _utc(stamp):
    return stamp.isoformat().replace('+00:00','Z')


def _interval(value,*,whole=False):
    _fields(value,{'start','end'})
    start,end=(_stamp(value[key],whole=whole) for key in ('start','end'))
    if start>=end:
        raise ValueError('Empty or reversed planned interval')
    return start,end


def _preflight(value,check,*,initial_nodes=0):
    """Depth-bounded DFS uses iterators, without allocating a wide pending list."""
    count=initial_nodes
    def visit(item,depth):
        nonlocal count
        check()
        count+=1
        _cap(count,MAX_JSON_NODES,'JSON nodes')
        _cap(depth,MAX_DEPTH,'JSON depth')
        kind=type(item)
        if kind is dict:
            _cap(count+len(item),MAX_JSON_NODES,'JSON width')
            for key,child in item.items():
                check()
                if type(key) is not str or len(key)>512:
                    raise ValueError('Bounded JSON string keys required')
                count+=1
                _cap(count,MAX_JSON_NODES,'JSON keys')
                visit(child,depth+1)
        elif kind is list:
            _cap(count+len(item),MAX_JSON_NODES,'JSON width')
            for child in item:visit(child,depth+1)
        elif kind is str:_cap(len(item),MAX_STRING,'JSON string')
        elif kind is int:
            _cap(item.bit_length(),67,'integer token bits')
            _cap(abs(item),10**20-1,'integer token magnitude')
        elif kind is not type(None):
            raise ValueError('JSON integer-only planned inputs required; no bool/float')
    visit(value,0)
    check()
    return count


def _encode(value,check,limit):
    count=0
    encoder=json.JSONEncoder(sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    for text in encoder.iterencode(value):
        check()
        raw=text.encode('utf-8')
        count+=len(raw)
        _cap(count,limit,'canonical bytes')
        yield raw
    check()


def _digest(value,check,*,limit=None):
    sha=hashlib.sha256()
    for raw in _encode(value,check,MAX_INPUT_BYTES if limit is None else limit):sha.update(raw)
    check()
    return sha.hexdigest()


def _unique(pairs,check):
    result={}
    for key,value in pairs:
        check()
        if key in result:raise ValueError('Duplicate planned-source JSON key')
        result[key]=value
    return result


def _owned(value,raw_size,check):
    nodes=_preflight(value,check)
    raw=bytearray()
    for chunk in _encode(value,check,MAX_INPUT_BYTES-raw_size):raw.extend(chunk)
    check()
    result=json.loads(raw,object_pairs_hook=lambda pairs:_unique(pairs,check))
    check()
    return result,nodes


def _scan_raw(text,check,initial_nodes):
    """Bound raw tokens before json.loads can allocate a decoded value tree."""
    index,depth,nodes=0,0,initial_nodes
    size=len(text)
    delimiters=' \t\r\n{}[]:,'
    while index<size:
        check()
        char=text[index]
        if char in ' \t\r\n:,':index+=1;continue
        nodes+=1
        _cap(nodes,MAX_JSON_NODES,'raw JSON tokens')
        if char=='"':
            start=index
            index+=1
            escaped=False
            while index<size:
                if index%256==0:check()
                _cap(index-start,MAX_STRING*6+2,'raw JSON string token')
                char=text[index]
                if char=='"' and not escaped:break
                escaped=(char=='\\' and not escaped)
                index+=1
            if index==size:raise ValueError('Unterminated planned-source JSON string')
            index+=1
        elif char in '{[':
            depth+=1
            _cap(depth,MAX_DEPTH,'raw JSON depth')
            index+=1
        elif char in '}]':
            depth-=1
            if depth<0:raise ValueError('Invalid planned-source JSON nesting')
            index+=1
        else:
            start=index
            while index<size and text[index] not in delimiters:
                if index%64==0:check()
                _cap(index-start,64,'raw JSON scalar token')
                index+=1
            token=text[start:index]
            if char in '-0123456789':
                digits=len(token)-(1 if token.startswith('-') else 0)
                _cap(digits,20,'raw integer digits')
                if not INTEGER.fullmatch(token):
                    raise ValueError('Only integer numeric tokens allowed in planned source')
            elif token!='null':
                raise ValueError('No bool/nonfinite/non-JSON planned-source tokens')
    if depth:raise ValueError('Invalid planned-source JSON nesting')
    check()


def _decode_raw(raw,check,nodes):
    check()
    try:text=raw.decode('utf-8')
    except UnicodeDecodeError as exc:raise ValueError('UTF-8 planned JSON source required') from exc
    check()
    _scan_raw(text,check,nodes)
    check()
    value=json.loads(text,object_pairs_hook=lambda pairs:_unique(pairs,check))
    check()
    _preflight(value,check,initial_nodes=nodes)
    return value


def _ref(value):
    _fields(value,{'path','sha256','size_bytes'})
    path=value['path']
    if (type(path) is not str or not path or len(path)>512 or ':' in path or '\\' in path or
            path.startswith('/') or any(part in ('','.','..') for part in path.split('/')) or
            any(part.endswith(('.', ' ')) or re.search(r'~[0-9]+(?:\.|$)',part) for part in path.split('/')) or
            any(part.casefold() in {'sealed','confirmation','original'} for part in path.split('/')) or
            any(ord(char)<32 or ord(char)==127 for char in path)):
        raise ValueError('Unsafe/reveal planned-source reference')
    _hash(value['sha256'])
    _integer(value['size_bytes'],1,128*1024**2)


def _ready(binding,cutoff,check,*,parents=()):
    _fields(binding['readiness'],READINESS_FIELDS)
    own=[]
    for key in sorted(READINESS_FIELDS):
        check();own.append(_stamp(binding['readiness'][key]))
    # Validate maxima even for a known-late declaration, before DATA classification.
    try:validation_cutoff=max(cutoff,max(*own,*parents)+timedelta(microseconds=1))
    except OverflowError as exc:raise ValueError('Unsupported readiness range') from exc
    ready=validate_readiness(binding['readiness'],binding['usable_at'],validation_cutoff,parent_usable_at=parents)
    check()
    return ready,own


def _domain(value,expected,as_of,check):
    _fields(value,DOMAIN_FIELDS)
    if value['schema_version']!=DOMAIN_VERSION:raise ValueError('Unsupported planned domain version')
    _text(value['operational_night'],10)
    validate_night(value['operational_night'])
    actual=_digest(value,check)
    if actual!=_hash(expected):raise ValueError('Planned domain canonical SHA mismatch')
    cutoff=_stamp(value['cutoff_time'])
    start,end=_interval(value['horizon'],whole=True)
    night=value['operational_night']
    night_of=lambda stamp:(stamp.astimezone(JST)-timedelta(hours=7)).date().isoformat()
    try:
        start_night=night_of(start)
        end_night=night_of(end-timedelta(microseconds=1))
        seconds=int((end-start).total_seconds())
    except OverflowError as exc:
        raise ValueError('Unsupported planned horizon datetime range') from exc
    if (cutoff>as_of or start<=as_of or start_night!=night or end_night!=night or
            start.minute%10 or start.second or seconds%600):
        raise ValueError('Planned horizon must match aligned future operational-night units')
    windows=seconds//600
    _cap(windows,MAX_WINDOWS,'domain windows')
    cells=value['cells']
    if type(cells) is not list or not cells:raise ValueError('Explicit nonempty planned domain cells required')
    _cap(len(cells),MAX_DOMAIN_CELLS,'domain cells')
    _cap(len(cells)*windows,MAX_DOMAIN_ROWS,'G0 domain rows')
    _cap(len(cells)*windows,MAX_OUTPUT_ROWS,'complete collected rows')
    positions={};previous=None
    for index,cell in enumerate(cells):
        check()
        if type(cell) is not list or len(cell)!=2:raise ValueError('Explicit 100m planned cell pair required')
        key=(_integer(cell[0],1000,8999),_integer(cell[1],0,99999))
        if previous is not None and key<=previous:raise ValueError('Planned cells must be sorted and unique')
        positions[key]=index;previous=key
    return actual,cutoff,start,end,windows,positions


def _identity(value):
    _fields(value,IDENTITY_FIELDS)
    for name in ('owner_id','observer_id','method_version'):_text(value[name])
    return _integer(value['crew_size'],1,100000)


def _bindings(value,cutoff,check):
    _fields(value,{'source','domain','code','projection'})
    ready,own,paths={},{},set()
    for role in ('source','domain','code'):
        check();item=value[role]
        _fields(item,{'ref','readiness','usable_at'})
        _ref(item['ref'])
        path=item['ref']['path']
        if path in paths:raise ValueError('Source/domain/code reference roles must have distinct paths')
        paths.add(path)
        ready[role],own[role]=_ready(item,cutoff,check)
    if value['code']['ref']['path']!=CODE_PATH:raise ValueError('Fixed planned projection code path required')
    _cap(value['source']['ref']['size_bytes'],MAX_RAW_BYTES,'declared raw bytes')
    _fields(value['projection'],{'readiness','usable_at'})
    ready['projection'],own['projection']=_ready(value['projection'],cutoff,check,
        parents=tuple(ready[role] for role in ('source','domain','code')))
    return ready,own


def _plan(value,domain,domain_sha,identity,source_own,projection_own,start,end,positions,check):
    _fields(value,SOURCE_FIELDS)
    if value['schema_version']!=SOURCE_VERSION or value['purpose']!='FUTURE_DECLARED_ACTIVE_HABU_SEARCH':
        raise ValueError('Explicit original planned-search format/purpose required')
    _text(value['plan_id']);_text(value['revision_id'])
    crew=_identity({key:value[key] for key in IDENTITY_FIELDS})
    if any(value[key]!=identity[key] for key in IDENTITY_FIELDS):raise ValueError('Planned identity/method mismatch')
    if (value['operational_night']!=domain['operational_night'] or _hash(value['domain_sha256'])!=domain_sha or
            _interval(value['horizon'],whole=True)!=(start,end)):
        raise ValueError('Original plan domain/night/horizon mismatch')
    if type(value['coverage']) is not str or value['coverage'] not in {'DECLARED_COMPLETE','UNKNOWN'}:
        raise ValueError('Explicit planned coverage required')
    issued=_stamp(value['issued_at'])
    if any(stamp<issued for stamp in [*source_own,*projection_own]):
        raise ValueError('Planned source/projection readiness precedes its issue')
    records=value['allocations']
    if type(records) is not list:raise ValueError('Explicit planned allocation list required')
    _cap(len(records),MAX_ALLOCATIONS,'allocations')
    found=set();allocations=[]
    for row in records:
        check();_fields(row,ALLOCATION_FIELDS)
        identifier=_text(row['allocation_id'])
        if identifier in found:raise ValueError('Duplicate planned allocation ID')
        found.add(identifier)
        key=(_integer(row['cell_x'],1000,8999),_integer(row['cell_y'],0,99999))
        first,last=_stamp(row['start'],whole=True),_stamp(row['end'],whole=True)
        seconds=_integer(row['planned_active_search_seconds'],1,86400)
        if key not in positions or not start<=first<last<=end:
            raise ValueError('Planned allocation outside declared cell/horizon scope')
        if seconds!=int((last-first).total_seconds()):raise ValueError('Explicit planned seconds/continuous interval mismatch')
        allocations.append((first,last,key,seconds))
    if crew!=1:raise PlannedEffortCapabilityBlocked('CAPABILITY_BLOCKED: multi-observer planned crew')
    def order(row):check();return row[:2]
    allocations.sort(key=order)
    check();previous=None
    for first,last,key,seconds in allocations:
        check()
        if previous is not None and first<previous:raise ValueError('Same-observer planned intervals overlap across cells')
        previous=last
    return issued,allocations


def _rows(domain,start,windows,positions,allocations,check):
    values={};total=0
    for first,last,cell,seconds in allocations:
        check();a=int((first-start).total_seconds());b=int((last-start).total_seconds());contributed=0
        for window in range(a//600,(b-1)//600+1):
            check()
            duration=min(b,(window+1)*600)-max(a,window*600)
            key=(positions[cell],window)
            values[key]=values.get(key,0)+duration
            if values[key]>600:raise ValueError('Planned observer effort exceeds a physical window')
            contributed+=duration
        if contributed!=seconds:raise ValueError('Planned bin contribution does not conserve source seconds')
        total+=seconds
    if total>int(windows*600):raise ValueError('Planned total exceeds one observer horizon')
    result=[]
    for cell_index,(cx,cy) in enumerate(domain['cells']):
        for window in range(windows):
            check();stamp=_utc(start+timedelta(seconds=window*600))
            result.append(dict(row_id=f'{cx}:{cy}@{stamp}',operational_night=domain['operational_night'],
                cell_x=cx,cell_y=cy,window_start_utc=stamp,planned_active_search_seconds=values.get((cell_index,window),0)))
    return result,total


def project_planned_effort(raw_plan_bytes,domain,bindings,*,expected_domain_sha256,
        expected_identity,as_of_time,context):
    """Return only complete bounded planned intent or an honest data blocker.

    Supplied raw plan physical SHA and domain canonical SHA are checked. Domain
    and code physical bytes are not verified. A coherent new JSON declaration is
    never evidence of an authenticated issuer, historical receipt or actual work.
    """
    if not isinstance(context,ProspectiveReadContext):raise ValueError('Existing prospective context required')
    if raw_plan_bytes is not None and type(raw_plan_bytes) is not bytes:
        raise ValueError('Immutable original planned JSON bytes or None required')
    check=context.check
    check();raw_size=0 if raw_plan_bytes is None else len(raw_plan_bytes)
    _cap(raw_size,MAX_RAW_BYTES,'raw bytes')
    owned,nodes=_owned(dict(domain=domain,bindings=bindings,expected_domain_sha256=expected_domain_sha256,
        identity=expected_identity,as_of_time=as_of_time),raw_size,check)
    domain,bindings,identity=owned['domain'],owned['bindings'],owned['identity']
    as_of=_stamp(owned['as_of_time'])
    domain_sha,cutoff,start,end,windows,positions=_domain(domain,owned['expected_domain_sha256'],as_of,check)
    crew=_identity(identity)
    ready,own=_bindings(bindings,cutoff,check)
    source=None;source_sha=None;issued=None;allocations=[];blockers=[]
    if raw_plan_bytes is None:blockers.append('RAW_PLAN_MISSING')
    else:
        sha=hashlib.sha256()
        for index in range(0,raw_size,65536):check();sha.update(raw_plan_bytes[index:index+65536])
        source_sha=sha.hexdigest();check()
        if raw_size!=bindings['source']['ref']['size_bytes'] or source_sha!=bindings['source']['ref']['sha256']:
            raise ValueError('Original planned source physical size/SHA mismatch')
        source=_decode_raw(raw_plan_bytes,check,nodes)
        issued,allocations=_plan(source,domain,domain_sha,identity,own['source'],own['projection'],
            start,end,positions,check)
        if source['coverage']=='UNKNOWN':blockers.append('PLAN_COVERAGE_UNKNOWN')
        if issued>=cutoff:blockers.append('PLAN_NOT_ISSUED_BEFORE_CUTOFF')
    if crew!=1:raise PlannedEffortCapabilityBlocked('CAPABILITY_BLOCKED: multi-observer planned crew')
    for role in ('source','domain','code','projection'):
        check()
        if ready[role]>=cutoff:blockers.append(role.upper()+'_NOT_AVAILABLE_BEFORE_CUTOFF')
    rows,total=([],None) if blockers else _rows(domain,start,windows,positions,allocations,check)
    recipe=dict(operation='SUM_EXPLICIT_ACTIVE_INTERVAL_INTERSECTIONS_SECONDS_V1',
        feature_name='planned_active_search_seconds',units='s',observer_count=1,version='1')
    result=dict(schema_version=VERSION,status='NEED_MORE_DATA' if blockers else 'DECLARED_PLAN_PROJECTED',
        blocker_kind='DATA_BLOCKED' if blockers else None,blockers=blockers,
        plan_id=source['plan_id'] if source else None,revision_id=source['revision_id'] if source else None,
        issued_at=_utc(issued) if issued else None,identity=identity,operational_night=domain['operational_night'],
        cutoff_time=_utc(cutoff),as_of_time=_utc(as_of),source_ref=bindings['source']['ref'],source_sha256=source_sha,
        source_canonical_sha256=_digest(source,check) if source is not None else None,
        domain_canonical_sha256=domain_sha,bindings=bindings,recipe=recipe,recipe_sha256=_digest(recipe,check),
        projection_readiness=bindings['projection']['readiness'],usable_at=_utc(ready['projection']),rows=rows,
        counts=dict(domain_cells=len(positions),windows=windows,expected_rows=len(positions)*windows,
            projected_rows=len(rows),allocation_count=len(allocations) if source is not None else None,
            total_planned_active_search_seconds=total),
        raw_plan_hash_matched=source is not None,domain_physical_bytes_verified=False,code_physical_bytes_verified=False,
        source_authenticity='NOT_ATTESTED',source_authentication='CALLER_DEPENDENCY_REQUIRED',
        issuer_authentication='CALLER_DEPENDENCY_REQUIRED',availability_authentication='CALLER_DEPENDENCY_REQUIRED',
        scientific_status='NOT_VALIDATED',statistical_adequacy='NOT_ASSESSED',
        fit_authorized=False,scientific_execution_authorized=False,selection_authorized=False,promotion_authorized=False,
        confirmation_authorized=False,official_issuance_authorized=False,production_authorized=False,
        g0_forecast_authorized=False,count_denominator_authorized=False,
        limitations=['PLANNED_INTENT_NOT_MEASURED_EFFORT_OR_NEGATIVE','DECLARED_DOMAIN_NOT_ALL_ISLAND_ROADS',
            'ISSUER_LATEST_REVISION_HISTORICAL_AVAILABILITY_NOT_ATTESTED','DOMAIN_CODE_PHYSICAL_BYTES_NOT_VERIFIED',
            'OUTSIDE_UNIVERSE_CONFIRMED_CAPTURES_REMAIN_IN_INDEPENDENT_FN_LEDGER'],
        implementation_blockers=['TYPED_G0_ADAPTER_NOT_IMPLEMENTED','COUNT_OR_PARENT_INFERENCE_NOT_IMPLEMENTED'])
    result['receipt_sha256']=_digest(result,check,limit=MAX_OUTPUT_BYTES)
    for chunk in _encode(result,check,MAX_OUTPUT_BYTES):pass
    check()
    return result
