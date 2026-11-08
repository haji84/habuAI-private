"""Conditional known-positive detector sensitivity, never occupancy or authority.

API: evaluate_detection_opportunities(bundle, *, protocol, budget_seconds=30).
All inputs are exact built-in JSON. No source/output I/O, callbacks, model
deserialization, registration, fitting side effects or production context exist.
Only fixed installed-runtime metadata/imports are read for the numerical audit.

Closed bundle fields: schema_version='habu-detection-opportunity-bundle-v1',
cohort_source_id, opportunities, sources. Opportunity fields are ROW_FIELDS.
Source fields are NODE_FIELDS: exact raw_json_utf8 is encoded unchanged, checked
against ref{path,sha256,size_bytes}, then strictly decoded. Source bodies use
schema_version='habu-detection-source-v1': TRUTH_RECORDS/DETECTION_RECORDS have
exact records lists (TRUTH_FIELDS/DETECTION_FIELDS); REGISTERED_COHORT has exact
COHORT_FIELDS. Its parents bind independent truth/support sources, never detector
outcomes. RAW/DERIVED parent/readiness declarations are checked, not authenticated.

Protocol fields are PROTOCOL_FIELDS. All parameters are explicit. Only the
preregistered Beta(1,1), existing pinned analysis runtime, DEVELOPMENT phase,
complete independent-truth cohort, known-subset unknown reporting, one trial per
site/night and non-removal scope are implemented. Unsupported study policy does
not acquire a default. Bounds below are engineering ceilings, not sample-adequacy
criteria; the superseded n<=10000/handwritten-CDF restriction is not used.

Separate observational source channels and matching records establish declared
consistency only. A method name or independent flag does not establish biological
truth, real preregistration, exchangeability, closure or source authentication.
Counts refer to opportunity IDs, never inferred biological individual identities.
Trial intervals are half-open [start,end). The v1 site/night policy supports
single operational-night trials only; a cross07 trial is explicitly unsupported,
while an exclusive end at07:00 remains within the preceding night.
Unknown/omitted/unsupported trials are reported; they are never detector failures.
Incomplete cohorts expose only conditional known-subset diagnostics, not a full
measured sensitivity. Intervals are model-based and uncalibrated. Alternative
priors, real truth-method credibility and actual population claims require the
existing scientific protocol/authority process outside this pure calculation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import importlib
import importlib.metadata
import json
import math
from pathlib import PurePosixPath, PureWindowsPath
import time

from g0_forecast_contract import ForecastCapacityError, validate_readiness_graph
from master_contracts import validate_night

VERSION='habu-detection-evaluation-v1'
TARGET='DETECTOR_SENSITIVITY_GIVEN_INDEPENDENT_KNOWN_POSITIVE_OPPORTUNITY'
RUNTIME={'numpy':'2.2.6','scipy':'1.15.3','scikit-learn':'1.5.2'}
READINESS={'source_received_at','derived_at','materialized_at','audited_at'}
MAX_BYTES=16*1024**2
MAX_NODES=2_000_000
MAX_DEPTH=24
MAX_STRING_BYTES=4*1024**2
MAX_OPPORTUNITIES=100_000
MAX_SOURCES=16_384
MAX_QUANTILES=64
JST=timezone(timedelta(hours=9))
BUNDLE_FIELDS={'schema_version','cohort_source_id','opportunities','sources'}
PROTOCOL_FIELDS={'schema_version','phase','target','frozen_at','assessment_as_of','prior',
    'quantile_probabilities','numerics','capacities','runtime_versions','scope','observer_binding',
    'effort_policy','truth_methods','cohort_policy','unknown_policy','cluster_policy','removal_policy',
    'minimum_group_support'}
CAP_FIELDS={'max_opportunities','max_sources','max_json_bytes','max_json_nodes','max_depth',
    'max_string_bytes','max_quantiles','min_shape','max_shape','min_tail_probability','max_seconds'}
NODE_FIELDS={'id','role','source_kind','parents','ref','raw_json_utf8','readiness','usable_at'}
TRUTH_FIELDS={'opportunity_id','site_id','start_time','end_time','truth_status','truth_method',
              'truth_available_at','truth_capture_event_refs'}
DETECTION_FIELDS={'opportunity_id','site_id','start_time','end_time','observer_id','mode',
    'protocol_version','effort','detected','detection_time','outcome_available_at','capture_event_refs',
    'cluster_id','independence_status','depletion_status'}
ROW_FIELDS=TRUTH_FIELDS|DETECTION_FIELDS|{'truth_source_id','detection_source_id'}
COHORT_FIELDS={'schema_version','kind','opportunity_ids','selection_rule','scope','observer_binding',
               'registered_at','basis_source_ids'}
FORBIDDEN_METHODS={'GPX_PASSAGE','GPS_PASSAGE','CAPTURE_ONLY','SAME_CAPTURE','EVALUATED_DETECTOR_OUTCOME'}


class _Invalid(ValueError):
    pass


class _Missing(ValueError):
    pass


class _Capacity(ValueError):
    pass


class _Runtime(ValueError):
    pass


class _Budget:
    def __init__(self,seconds):
        kind=type(seconds)
        if (kind is not int and kind is not float) or not 0<seconds<=30 or not math.isfinite(seconds):
            raise _Invalid('INVALID_BUDGET')
        self.start=time.monotonic();self.deadline=self.start+seconds
        self.nodes=0;self.node_limit=MAX_NODES;self.depth_limit=MAX_DEPTH
        self.string_limit=MAX_STRING_BYTES;self.byte_limit=MAX_BYTES
        self.depth_seen=0;self.string_bytes_seen=0

    def check(self):
        if time.monotonic()>=self.deadline:
            raise _Capacity('ELAPSED_CAPACITY_EXCEEDED')

    def restrict(self,caps):
        self.deadline=min(self.deadline,self.start+caps['max_seconds'])
        self.node_limit=caps['max_json_nodes'];self.depth_limit=caps['max_depth']
        self.string_limit=caps['max_string_bytes'];self.byte_limit=caps['max_json_bytes']
        if (self.nodes>self.node_limit or self.depth_seen>self.depth_limit or
                self.string_bytes_seen>self.string_limit):
            raise _Capacity('JSON_CAPACITY_EXCEEDED')
        self.check()


def _fields(value,fields):
    if type(value) is not dict or set(value)!=fields:raise _Invalid('EXACT_FIELDS_REQUIRED')


def _text(value):
    if type(value) is not str or not value or len(value)>256 or not value.isprintable():
        raise _Invalid('BOUNDED_TEXT_REQUIRED')
    return value


def _number(value):
    kind=type(value)
    if kind is not int and kind is not float:raise _Invalid('FINITE_NONBOOLEAN_NUMBER_REQUIRED')
    if kind is int and value.bit_length()>256:raise _Invalid('NUMBER_CAPACITY_REQUIRED')
    if not math.isfinite(value):raise _Invalid('FINITE_NONBOOLEAN_NUMBER_REQUIRED')
    return value


def _integer(value,low,high):
    if type(value) is not int or not low<=value<=high:raise _Invalid('INTEGER_RANGE_REQUIRED')
    return value


def _time(value):
    if type(value) is not str:raise _Invalid('AWARE_TIME_REQUIRED')
    try:
        result=datetime.fromisoformat(value.replace('Z','+00:00'))
        if result.utcoffset() is None:raise _Invalid('AWARE_TIME_REQUIRED')
        return result.astimezone(timezone.utc)
    except (ValueError,OverflowError) as exc:
        raise _Invalid('AWARE_TIME_REQUIRED') from exc


def _ids(value,maximum,*,empty=False):
    if type(value) is not list or len(value)>maximum or (not value and not empty):
        raise _Invalid('BOUNDED_ID_LIST_REQUIRED')
    for item in value:_text(item)
    if len(set(value))!=len(value):raise _Invalid('DUPLICATE_ID')
    return value


def _encoded(value,budget):
    size=0
    for part in json.JSONEncoder(sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).iterencode(value):
        budget.check();raw=part.encode('utf-8');size+=len(raw)
        if size>budget.byte_limit:raise _Capacity('JSON_BYTE_CAPACITY_EXCEEDED')
        yield raw


def _digest(value,budget):
    sha=hashlib.sha256()
    for raw in _encoded(value,budget):sha.update(raw)
    budget.check();return sha.hexdigest()


def _owned(value,budget,depth=0):
    budget.check();budget.nodes+=1
    budget.depth_seen=max(depth,budget.depth_seen)
    if budget.nodes>budget.node_limit or depth>budget.depth_limit:raise _Capacity('JSON_COMPLEXITY_EXCEEDED')
    kind=type(value)
    if kind is dict:
        result={}
        for key,item in value.items():
            if type(key) is not str or len(key)>256:raise _Invalid('JSON_STRING_KEYS_REQUIRED')
            budget.string_bytes_seen=max(budget.string_bytes_seen,len(key.encode('utf-8')))
            result[key]=_owned(item,budget,depth+1)
        return result
    if kind is list:return [_owned(item,budget,depth+1) for item in value]
    if kind is str:
        if len(value)>budget.string_limit:raise _Capacity('JSON_STRING_CAPACITY_EXCEEDED')
        size=len(value.encode('utf-8'));budget.string_bytes_seen=max(budget.string_bytes_seen,size)
        if size>budget.string_limit:
            raise _Capacity('JSON_STRING_CAPACITY_EXCEEDED')
        return value
    if kind is bool or value is None:return value
    if kind is int or kind is float:return _number(value)
    raise _Invalid('BUILTIN_JSON_REQUIRED')


def _protocol(protocol,budget):
    if protocol is None:raise _Missing('EXPLICIT_PROTOCOL_NOT_SUPPLIED')
    _fields(protocol,PROTOCOL_FIELDS)
    if (protocol['schema_version']!='habu-detection-protocol-v1' or protocol['phase']!='DEVELOPMENT'
            or protocol['target']!=TARGET):raise _Invalid('DETECTION_PROTOCOL_REQUIRED')
    if any(value is None for value in protocol.values()):raise _Missing('EXPLICIT_PROTOCOL_VALUES_REQUIRED')
    _fields(protocol['prior'],{'alpha','beta'})
    if any(_number(v)!=1 for v in protocol['prior'].values()):raise _Invalid('PREREGISTERED_BETA_ONE_ONE_REQUIRED')
    _fields(protocol['numerics'],{'cdf_absolute_tolerance','log_tail_tolerance'})
    for value in protocol['numerics'].values():
        if not 0<_number(value)<1:raise _Invalid('EXPLICIT_INVERSE_TOLERANCE_REQUIRED')
    caps=protocol['capacities'];_fields(caps,CAP_FIELDS)
    for name,ceiling in [('max_opportunities',MAX_OPPORTUNITIES),('max_sources',MAX_SOURCES),
        ('max_json_bytes',MAX_BYTES),('max_json_nodes',MAX_NODES),('max_depth',MAX_DEPTH),
        ('max_string_bytes',MAX_STRING_BYTES),('max_quantiles',MAX_QUANTILES)]:
        _integer(caps[name],1,ceiling)
    if not 0<_number(caps['max_seconds'])<=30:raise _Invalid('EXPLICIT_ELAPSED_CAPACITY_REQUIRED')
    if not 0<_number(caps['min_shape'])<=_number(caps['max_shape']):raise _Invalid('EXPLICIT_SHAPE_RANGE_REQUIRED')
    if not 0<_number(caps['min_tail_probability'])<.5:raise _Invalid('EXPLICIT_TAIL_RANGE_REQUIRED')
    budget.restrict(caps)
    quantiles=protocol['quantile_probabilities']
    if type(quantiles) is not list or not quantiles or len(quantiles)>caps['max_quantiles']:
        raise _Invalid('EXPLICIT_QUANTILE_PROBABILITIES_REQUIRED')
    previous=-1
    for q in quantiles:
        if not previous<_number(q)<=1 or q<0:raise _Invalid('ORDERED_QUANTILES_REQUIRED')
        previous=q
    _fields(protocol['runtime_versions'],set(RUNTIME))
    if protocol['runtime_versions']!=RUNTIME:raise _Invalid('PINNED_ANALYSIS_PROTOCOL_REQUIRED')
    _fields(protocol['scope'],{'site_ids','start_time','end_time'})
    _ids(protocol['scope']['site_ids'],caps['max_opportunities'])
    start,end=(_time(protocol['scope'][key]) for key in ('start_time','end_time'))
    if not _time(protocol['frozen_at'])<=start<end<=_time(protocol['assessment_as_of']):
        raise _Invalid('PROTOCOL_SCOPE_CHRONOLOGY')
    _fields(protocol['observer_binding'],{'observer_id','mode','protocol_version'})
    for value in protocol['observer_binding'].values():_text(value)
    _fields(protocol['effort_policy'],{'unit','method','min_value','max_value'})
    effort=protocol['effort_policy'];_text(effort['unit']);_text(effort['method'])
    if effort['unit'] not in ('seconds','minutes','hours'):
        raise _Missing('SUPPORTED_TIME_EFFORT_POLICY_REQUIRED')
    if not 0<_number(effort['min_value'])<=_number(effort['max_value']):raise _Invalid('EXPLICIT_EFFORT_RANGE_REQUIRED')
    _ids(protocol['truth_methods'],caps['max_opportunities'])
    for field,required in [('cohort_policy','COMPLETE_REGISTERED_INDEPENDENT_TRUTH'),
        ('unknown_policy','REPORT_KNOWN_SUBSET_NO_FULL_COHORT_CLAIM'),
        ('cluster_policy','ONE_OPPORTUNITY_PER_SITE_NIGHT'),('removal_policy','NON_REMOVAL_OPPORTUNITIES_ONLY')]:
        if protocol[field]!=required:raise _Missing('UNSUPPORTED_DECLARED_STUDY_POLICY')
    _integer(protocol['minimum_group_support'],1,caps['max_opportunities'])
    return protocol


def _pairs(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise _Invalid('DUPLICATE_JSON_KEY')
        value[key]=item
    return value


def _path(value):
    _text(value)
    if ('\\' in value or ':' in value or PurePosixPath(value).is_absolute() or PureWindowsPath(value).drive or
            any(p in ('','.','..') or p.casefold() in {'sealed','confirmation'} for p in value.split('/'))):
        raise _Invalid('UNSAFE_SOURCE_REFERENCE')


def _sources(bundle,protocol,budget):
    caps=protocol['capacities'];nodes=bundle['sources']
    if type(nodes) is not list or len(nodes)>caps['max_sources']:raise _Capacity('SOURCE_CAPACITY_EXCEEDED')
    if not nodes:raise _Missing('SOURCE_NODES_NOT_SUPPLIED')
    by_id,paths,bodies,all_records={},set(),{},{}
    for node in nodes:
        budget.check();_fields(node,NODE_FIELDS);ident=_text(node['id'])
        if ident in by_id:raise _Invalid('DUPLICATE_SOURCE_ID')
        if node['role'] not in ('TRUTH','DETECTION','COHORT','SUPPORT'):raise _Invalid('SOURCE_ROLE_REQUIRED')
        if node['source_kind'] not in ('RAW','DERIVED'):raise _Invalid('SOURCE_KIND_REQUIRED')
        _ids(node['parents'],caps['max_sources'],empty=True)
        if bool(node['parents'])!=(node['source_kind']=='DERIVED'):raise _Invalid('DERIVED_PARENT_REQUIRED')
        ref=node['ref'];_fields(ref,{'path','sha256','size_bytes'});_path(ref['path'])
        if ref['path'] in paths:raise _Invalid('DUPLICATE_SOURCE_PATH')
        paths.add(ref['path'])
        raw=node['raw_json_utf8']
        if type(raw) is not str:raise _Invalid('SOURCE_UTF8_STRING_REQUIRED')
        raw=raw.encode('utf-8')
        if type(ref['size_bytes']) is not int or ref['size_bytes']!=len(raw) or ref['sha256']!=hashlib.sha256(raw).hexdigest():
            raise _Invalid('SOURCE_BYTE_BINDING_MISMATCH')
        _fields(node['readiness'],READINESS)
        times=[_time(value) for value in node['readiness'].values()]
        usable=_time(node['usable_at'])
        if max(times)>=_time(protocol['assessment_as_of']) or usable>=_time(protocol['assessment_as_of']):
            raise _Missing('SOURCE_NOT_AVAILABLE_BEFORE_ASSESSMENT')
        body=json.loads(raw,object_pairs_hook=_pairs)
        body=_owned(body,budget)
        if type(body) is not dict or body.get('schema_version')!='habu-detection-source-v1':
            raise _Invalid('TYPED_DETECTION_SOURCE_REQUIRED')
        if node['role'] in ('TRUTH','DETECTION'):
            _fields(body,{'schema_version','kind','records'})
            if body['kind']!=node['role']+'_RECORDS':raise _Invalid('SOURCE_BODY_ROLE_MISMATCH')
            records=body['records']
            if type(records) is not list or len(records)>caps['max_opportunities']:raise _Capacity('RECORD_CAPACITY_EXCEEDED')
            seen=set()
            for record in records:
                _fields(record,TRUTH_FIELDS if node['role']=='TRUTH' else DETECTION_FIELDS)
                rid=_text(record['opportunity_id'])
                if rid in seen:raise _Invalid('DUPLICATE_SOURCE_OPPORTUNITY')
                seen.add(rid)
                _record(record,node['role'])
                available=record['truth_available_at'] if node['role']=='TRUTH' else record['outcome_available_at']
                if _time(available)>usable:raise _Invalid('SOURCE_AVAILABLE_BEFORE_BOUND_RECORD')
                key=node['role'],rid
                if key in all_records:
                    _same_fields(record,all_records[key],TRUTH_FIELDS if node['role']=='TRUTH' else DETECTION_FIELDS)
                all_records[key]=record
        elif node['role']=='COHORT':
            _fields(body,COHORT_FIELDS)
            if body['kind']!='REGISTERED_COHORT':raise _Invalid('SOURCE_BODY_ROLE_MISMATCH')
        else:
            _fields(body,{'schema_version','kind','details'})
            if body['kind']!='SUPPORT':raise _Invalid('SUPPORT_SOURCE_KIND_REQUIRED')
        by_id[ident]=node;bodies[ident]=body
    graph=[{key:node[key] for key in ('id','parents','readiness','usable_at')} for node in nodes]
    validated=validate_readiness_graph(graph,_time(protocol['assessment_as_of']),check=budget.check)
    ancestors,raw_hashes={},{}
    for ident in validated['topological_order']:
        node=by_id[ident]
        ancestors[ident]={ident}|set().union(*(ancestors[p] for p in node['parents']))
        raw_hashes[ident]=set().union(*(raw_hashes[p] for p in node['parents']))
        if node['source_kind']=='RAW' and node['role'] in ('TRUTH','DETECTION'):
            raw_hashes[ident].add(node['ref']['sha256'])
    return by_id,bodies,ancestors,raw_hashes


def _record(record,role):
    _text(record['opportunity_id']);_text(record['site_id'])
    start,end=_time(record['start_time']),_time(record['end_time'])
    if not start<end:raise _Invalid('OPPORTUNITY_TIME_SCOPE_REQUIRED')
    if role=='TRUTH':
        if record['truth_status'] not in ('KNOWN_POSITIVE','KNOWN_NEGATIVE','UNKNOWN'):raise _Invalid('TRUTH_STATUS_REQUIRED')
        _text(record['truth_method']);_time(record['truth_available_at'])
        _ids(record['truth_capture_event_refs'],MAX_OPPORTUNITIES,empty=True)
    else:
        for key in ('observer_id','mode','protocol_version','cluster_id','independence_status','depletion_status'):_text(record[key])
        _fields(record['effort'],{'value','unit','method'})
        _number(record['effort']['value']);_text(record['effort']['unit']);_text(record['effort']['method'])
        detected=record['detected']
        if type(detected) is not bool and detected is not None:raise _Invalid('BOOLEAN_OR_NULL_DETECTION_REQUIRED')
        stamp=record['detection_time']
        if detected is True:
            if stamp is None:raise _Missing('DETECTION_TIME_NOT_SUPPLIED')
            if not start<=_time(stamp)<end:raise _Invalid('DETECTION_TIME_OUTSIDE_OPPORTUNITY')
        elif stamp is not None:raise _Invalid('UNKNOWN_OR_MISSED_DETECTION_HAS_TIME')
        available=_time(record['outcome_available_at'])
        if (detected is False and available<end or detected is True and available<_time(stamp)):
            raise _Invalid('OUTCOME_AVAILABLE_BEFORE_OBSERVATION')
        _ids(record['capture_event_refs'],MAX_OPPORTUNITIES,empty=True)


def _same_fields(row,source,fields):
    times={'start_time','end_time','truth_available_at','detection_time','outcome_available_at'}
    for key in fields:
        a,b=row[key],source[key]
        if key in times:
            same=a is None and b is None or a is not None and b is not None and _time(a)==_time(b)
        else:same=a==b
        if not same:raise _Invalid('SOURCE_RECORD_SCOPE_OR_VALUE_MISMATCH')


def _cohort(bundle,protocol,sources,bodies,ancestors,budget):
    ident=bundle['cohort_source_id']
    if type(ident) is not str or ident not in sources:raise _Missing('REGISTERED_COHORT_SOURCE_NOT_SUPPLIED')
    if sources[ident]['role']!='COHORT':raise _Invalid('COHORT_SOURCE_ROLE_MISMATCH')
    body=bodies[ident]
    ids=_ids(body['opportunity_ids'],protocol['capacities']['max_opportunities'],empty=True)
    basis=_ids(body['basis_source_ids'],protocol['capacities']['max_sources'])
    if set(basis)!=set(sources[ident]['parents']):raise _Invalid('COHORT_BASIS_PARENT_MISMATCH')
    if any(sources[p]['role'] not in ('TRUTH','SUPPORT') for p in ancestors[ident]-{ident}):
        raise _Missing('COHORT_SELECTED_FROM_DETECTOR_OUTCOMES')
    if (body['selection_rule']!=protocol['cohort_policy'] or body['scope']!=protocol['scope'] or
            body['observer_binding']!=protocol['observer_binding'] or
            _time(body['registered_at'])!=_time(protocol['frozen_at'])):
        raise _Invalid('REGISTERED_COHORT_PROTOCOL_MISMATCH')
    eligible=set()
    for source_id,node in sources.items():
        if node['role']=='TRUTH':
            for record in bodies[source_id]['records']:
                budget.check();_record(record,'TRUTH')
                if (record['site_id'] in protocol['scope']['site_ids'] and
                    _time(protocol['scope']['start_time'])<=_time(record['start_time']) and
                    _time(record['end_time'])<=_time(protocol['scope']['end_time'])):
                    eligible.add(record['opportunity_id'])
    return ids,eligible


def _classify(bundle,protocol,sources,bodies,ancestors,raw_hashes,registered,budget):
    rows=bundle['opportunities'];caps=protocol['capacities']
    if type(rows) is not list or len(rows)>caps['max_opportunities']:raise _Capacity('OPPORTUNITY_CAPACITY_EXCEEDED')
    lookup={};physical={};cluster_map={};record_indexes={};site_intervals={}
    for ident,node in sources.items():
        if node['role'] in ('TRUTH','DETECTION'):
            index={}
            for record in bodies[ident]['records']:
                budget.check();index[record['opportunity_id']]=record
            record_indexes[ident]=index
    for row in rows:
        budget.check();_fields(row,ROW_FIELDS);_record(row,'TRUTH');_record(row,'DETECTION')
        rid=row['opportunity_id']
        if rid in lookup:raise _Invalid('DUPLICATE_OPPORTUNITY_ID')
        lookup[rid]=row
        for key in ('truth_source_id','detection_source_id'):_text(row[key])
        night=(_time(row['start_time']).astimezone(JST)-timedelta(hours=7)).date().isoformat()
        validate_night(night)
        key=row['site_id'],night
        physical.setdefault(key,[]).append(rid)
        site_intervals.setdefault(row['site_id'],[]).append((_time(row['start_time']),_time(row['end_time']),rid))
        if row['cluster_id'] in cluster_map and cluster_map[row['cluster_id']]!=key:
            raise _Invalid('CLUSTER_SCOPE_CONTRADICTION')
        cluster_map[row['cluster_id']]=key
    overlapping=set()
    for intervals in site_intervals.values():
        budget.check();intervals.sort();group=[];latest=None
        for start,end,rid in intervals:
            budget.check()
            if latest is not None and start>=latest:
                if len(group)>1:overlapping.update(group)
                group=[];latest=None
            group.append(rid);latest=end if latest is None else max(latest,end)
        if len(group)>1:overlapping.update(group)
    registered_set=set(registered)
    if set(lookup)-registered_set:raise _Invalid('UNREGISTERED_OPPORTUNITY')
    classifications=[]
    for rid in registered:
        budget.check();row=lookup.get(rid);reasons=[]
        if row is None:
            classifications.append(dict(opportunity_id=rid,reasons=['REGISTERED_DENOMINATOR_INCOMPLETE'],detected=None,truth_status='UNKNOWN'))
            continue
        truth_id,det_id=row['truth_source_id'],row['detection_source_id']
        if truth_id not in sources or det_id not in sources:
            reasons.append('TRUTH_OR_OUTCOME_SOURCE_NOT_SUPPLIED')
        else:
            if sources[truth_id]['role']!='TRUTH' or sources[det_id]['role']!='DETECTION':
                raise _Invalid('OPPORTUNITY_SOURCE_ROLE_MISMATCH')
            truth=record_indexes[truth_id].get(rid)
            detector=record_indexes[det_id].get(rid)
            if truth is None or detector is None:reasons.append('SOURCE_OPPORTUNITY_RECORD_NOT_SUPPLIED')
            else:
                _record(truth,'TRUTH');_record(detector,'DETECTION')
                _same_fields(row,truth,TRUTH_FIELDS);_same_fields(row,detector,DETECTION_FIELDS)
                if (_time(row['truth_available_at'])>_time(sources[truth_id]['usable_at']) or
                        _time(row['outcome_available_at'])>_time(sources[det_id]['usable_at'])):
                    raise _Invalid('SOURCE_AVAILABLE_BEFORE_BOUND_RECORD')
            if any(sources[p]['role']=='DETECTION' for p in ancestors[truth_id]):
                reasons.append('TRUTH_DEPENDS_ON_EVALUATED_OUTCOME')
            if any(sources[p]['role']=='TRUTH' for p in ancestors[det_id]):
                reasons.append('DETECTOR_USED_TRUTH_CHANNEL')
            if not raw_hashes[truth_id] or not raw_hashes[det_id] or raw_hashes[truth_id]&raw_hashes[det_id]:
                reasons.append('INDEPENDENT_OBSERVATIONAL_CHANNELS_NOT_ESTABLISHED')
        if set(row['truth_capture_event_refs'])&set(row['capture_event_refs']):reasons.append('SAME_CAPTURE_USED_AS_TRUTH')
        if row['truth_method'] in FORBIDDEN_METHODS or row['truth_method'] not in protocol['truth_methods']:
            reasons.append('INDEPENDENT_TRUTH_METHOD_NOT_SUPPORTED')
        if row['truth_status']=='UNKNOWN':reasons.append('TRUTH_UNKNOWN')
        if (row['site_id'] not in protocol['scope']['site_ids'] or
                not _time(protocol['scope']['start_time'])<=_time(row['start_time'])<
                    _time(row['end_time'])<=_time(protocol['scope']['end_time'])):
            reasons.append('OPPORTUNITY_OUTSIDE_REGISTERED_SCOPE')
        effort=row['effort'];policy=protocol['effort_policy']
        if (any(row[key]!=value for key,value in protocol['observer_binding'].items()) or
                effort['unit']!=policy['unit'] or effort['method']!=policy['method'] or
                not policy['min_value']<=effort['value']<=policy['max_value']):
            reasons.append('OBSERVER_MODE_OR_EFFORT_OUTSIDE_PROTOCOL')
        if effort['unit'] in ('seconds','minutes','hours'):
            scale={'seconds':1,'minutes':60,'hours':3600}[effort['unit']]
            duration=_time(row['end_time'])-_time(row['start_time'])
            duration_us=(duration.days*86400+duration.seconds)*1000000+duration.microseconds
            if Decimal(str(effort['value']))*scale*1000000>duration_us:
                reasons.append('TIME_EFFORT_EXCEEDS_OPPORTUNITY_DURATION')
        night=(_time(row['start_time']).astimezone(JST)-timedelta(hours=7)).date().isoformat()
        # Trials are half-open. A v1 independent site/night trial may end at07:00,
        # but cannot include exposure on both sides of that boundary.
        last_instant=_time(row['end_time'])-timedelta(microseconds=1)
        end_night=(last_instant.astimezone(JST)-timedelta(hours=7)).date().isoformat()
        if end_night!=night:reasons.append('CROSS_NIGHT_OPPORTUNITY_UNSUPPORTED')
        if len(physical[(row['site_id'],night)])>1:reasons.append('REPEATED_SITE_NIGHT_NOT_INDEPENDENT')
        if rid in overlapping:reasons.append('OVERLAPPING_SITE_OPPORTUNITIES_NOT_INDEPENDENT')
        if row['independence_status']!='DECLARED_INDEPENDENT':reasons.append('INDEPENDENCE_NOT_ESTABLISHED')
        if row['depletion_status']!='NON_REMOVAL':reasons.append('REMOVAL_OR_DEPLETION_NOT_SUPPORTED')
        if row['detected'] is None:reasons.append('DETECTION_RESULT_UNKNOWN')
        classifications.append(dict(opportunity_id=rid,reasons=sorted(set(reasons)),
            detected=row['detected'],truth_status=row['truth_status']))
    return classifications


def _runtime(budget):
    budget.check()
    try:
        versions={name:importlib.metadata.version(name) for name in RUNTIME}
        numpy=importlib.import_module('numpy');scipy=importlib.import_module('scipy')
        stats=importlib.import_module('scipy.stats')
        if versions!=RUNTIME or numpy.__version__!=versions['numpy'] or scipy.__version__!=versions['scipy']:
            raise _Runtime('RUNTIME_BINDING_ERROR')
        beta=stats.beta
        if not all(callable(getattr(beta,name)) for name in ('ppf','cdf','logcdf','logsf')):
            raise _Runtime('RUNTIME_BINDING_ERROR')
    except (ImportError,OSError,AttributeError,importlib.metadata.PackageNotFoundError) as exc:
        raise _Runtime('RUNTIME_BINDING_ERROR') from exc
    budget.check();return versions,beta


def _posterior(n,s,protocol,budget):
    a,b=1+s,1+n-s
    output=dict(posterior_parameters=dict(alpha=a,beta=b),posterior_mean=a/(a+b),
        posterior_quantiles=None,numerical_status='NUMERICAL_CAPACITY_EXCEEDED')
    caps=protocol['capacities']
    if not caps['min_shape']<=min(a,b)<=max(a,b)<=caps['max_shape']:return output
    try:
        versions,beta=_runtime(budget)
    except _Runtime:
        output['numerical_status']='RUNTIME_BINDING_ERROR';return output
    output['runtime_versions']=versions
    values=[];previous=-1
    for q in protocol['quantile_probabilities']:
        budget.check()
        if q==0:x=0.
        elif q==1:x=1.
        else:
            if min(q,1-q)<caps['min_tail_probability']:return output
            try:
                x=float(beta.ppf(q,a,b));budget.check()
                if not math.isfinite(x) or not 0<x<1:
                    output['numerical_status']='NUMERICAL_NONCONVERGENCE';return output
                cdf=float(beta.cdf(x,a,b));lcdf=float(beta.logcdf(x,a,b));lsf=float(beta.logsf(x,a,b))
                budget.check();tol=protocol['numerics']
                if (not all(math.isfinite(v) for v in (cdf,lcdf,lsf)) or not 0<=cdf<=1 or
                    abs(cdf-q)>tol['cdf_absolute_tolerance'] or
                    (q<=.5 and abs(lcdf-math.log(q))>tol['log_tail_tolerance']) or
                    (q>.5 and abs(lsf-math.log1p(-q))>tol['log_tail_tolerance'])):
                    output['numerical_status']='NUMERICAL_NONCONVERGENCE';return output
            except (ValueError,OverflowError,FloatingPointError):
                output['numerical_status']='NUMERICAL_NONCONVERGENCE';return output
        if x<previous:
            output['numerical_status']='NUMERICAL_NONCONVERGENCE';return output
        values.append(dict(probability=q,value=x));previous=x
    output.update(posterior_quantiles=values,numerical_status='VERIFIED_MODEL_BASED_NOT_CALIBRATED')
    return output


def evaluate_detection_opportunities(bundle, *, protocol, budget_seconds=30):
    """Compute declared-source diagnostics; never admit truth or production use."""
    result=dict(schema_version=VERSION,execution_status='FAIL',reason_code=None,blockers=[],
        registered_cohort_size=None,n=None,s=None,unknown_results=None,
        observed_sensitivity=None,known_subset_sensitivity=None,posterior_mean=None,
        posterior_parameters=None,posterior_quantiles=None,numerical_status='NOT_COMPUTED',
        false_positive_rate=None,false_positive_status='NOT_VALIDATED',known_negative_n=None,
        brier=None,log_loss=None,prediction_evaluation_status='NOT_PRODUCED',
        source_authentication='NOT_ATTESTED',preregistration_authentication='NOT_ATTESTED',
        independence_authentication='NOT_ATTESTED',statistical_assumptions='DECLARED_NOT_VALIDATED',
        scientific_status='NOT_VALIDATED',source_authorized=False,scientific_authorized=False,
        confirmation_authorized=False,production_authorized=False,
        biological_tonight_activity_validated=False,occupancy_model_produced=False,
        source_sha256={},classifications=[])
    try:
        budget=_Budget(budget_seconds)
        bundle,protocol=_owned([bundle,protocol],budget)
        initial_size=sum(len(raw) for raw in _encoded([bundle,protocol],budget))
        protocol=_protocol(protocol,budget)
        if initial_size>protocol['capacities']['max_json_bytes']:raise _Capacity('JSON_BYTE_CAPACITY_EXCEEDED')
        if bundle is None:raise _Missing('OPPORTUNITY_BUNDLE_NOT_SUPPLIED')
        _fields(bundle,BUNDLE_FIELDS)
        if bundle['schema_version']!='habu-detection-opportunity-bundle-v1':raise _Invalid('OPPORTUNITY_BUNDLE_VERSION')
        result['input_digests']=dict(bundle=_digest(bundle,budget),protocol=_digest(protocol,budget))
        sources,bodies,ancestors,raw_hashes=_sources(bundle,protocol,budget)
        registered,truth_ids=_cohort(bundle,protocol,sources,bodies,ancestors,budget)
        classifications=_classify(bundle,protocol,sources,bodies,ancestors,raw_hashes,registered,budget)
        blockers={reason for record in classifications for reason in record['reasons']}
        if set(registered)!=truth_ids:blockers.add('REGISTERED_DENOMINATOR_INCOMPLETE')
        positive=[r for r in classifications if not r['reasons'] and r['truth_status']=='KNOWN_POSITIVE']
        negative=[r for r in classifications if not r['reasons'] and r['truth_status']=='KNOWN_NEGATIVE']
        n=len(positive);s=sum(r['detected'] is True for r in positive)
        complete=not blockers
        result.update(registered_cohort_size=len(registered),n=n,s=s,
            unknown_results=sum(r['detected'] is None for r in classifications),
            full_cohort_complete=complete,classifications=classifications,
            source_sha256={key:node['ref']['sha256'] for key,node in sorted(sources.items())},
            known_negative_n=len(negative),blockers=sorted(blockers))
        supported_positive=n>=protocol['minimum_group_support']
        supported_negative=len(negative)>=protocol['minimum_group_support']
        if negative and complete and supported_negative:
            result['false_positive_rate']=sum(r['detected'] is True for r in negative)/len(negative)
            result['false_positive_status']='CONDITIONAL_DESCRIPTIVE_NOT_VALIDATED'
        if n==0:
            result.update(execution_status='DATA_BLOCKED',reason_code='NO_KNOWN_POSITIVE_OBSERVED_OPPORTUNITIES')
            result['blockers'].append('NO_KNOWN_POSITIVE_OBSERVED_OPPORTUNITIES')
        else:
            estimate=s/n
            result['known_subset_sensitivity']=estimate
            result['observed_sensitivity']=estimate if complete and supported_positive else None
            result.update(_posterior(n,s,protocol,budget))
            if not supported_positive:result['blockers'].append('PREREGISTERED_GROUP_SUPPORT_NOT_MET')
            if negative and not supported_negative:result['blockers'].append('NEGATIVE_GROUP_SUPPORT_NOT_MET')
            result['execution_status']=('COMPUTED' if complete and not result['blockers'] and
                result['numerical_status']=='VERIFIED_MODEL_BASED_NOT_CALIBRATED' else 'PARTIAL')
            result['reason_code']='CONDITIONAL_DECLARED_SOURCE_DIAGNOSTIC'
        result['blockers']=sorted(set(result['blockers']))
        budget.check();result['receipt_sha256']=_digest(result,budget)
        budget.check()
    except _Missing as exc:
        result.update(execution_status='DATA_BLOCKED',reason_code=str(exc),blockers=[str(exc)])
    except ForecastCapacityError:
        result.update(execution_status='RUNTIME_BLOCKED',reason_code='SOURCE_GRAPH_CAPACITY_EXCEEDED',
            blockers=['SOURCE_GRAPH_CAPACITY_EXCEEDED'])
    except _Capacity as exc:
        result.update(execution_status='RUNTIME_BLOCKED',reason_code=str(exc),blockers=[str(exc)])
    except _Invalid as exc:
        result.update(execution_status='FAIL',reason_code=str(exc),blockers=[str(exc)])
    except (ValueError,TypeError,KeyError,IndexError,OverflowError,RecursionError,UnicodeError):
        result.update(execution_status='FAIL',reason_code='SOURCE_OR_PROTOCOL_VALIDATION_FAILED',
            blockers=['SOURCE_OR_PROTOCOL_VALIDATION_FAILED'])
    if result['execution_status'] in ('FAIL','RUNTIME_BLOCKED'):
        for key in ('receipt_sha256',):result.pop(key,None)
        result.update(n=None,s=None,observed_sensitivity=None,known_subset_sensitivity=None,
            posterior_mean=None,posterior_parameters=None,posterior_quantiles=None,classifications=[],
            false_positive_rate=None,false_positive_status='NOT_VALIDATED',known_negative_n=None)
    return result
