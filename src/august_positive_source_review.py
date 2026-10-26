"""Closed August source-occurrence family; initial admission is Aug29 line9654.

The descriptor is a code-pinned input bound, not an issuer/scientific certificate.
All actual reads, checks and point charges belong to the supplied caller.
"""
from pathlib import PureWindowsPath
from datetime import date, timedelta
import math
import re

import _owner_capture_occurrence_core as core
from master_contracts import digest
from sept28_positive_source_review import strict_json

PROFILE = 'august-owner-capture-source-occurrence-v1'
STEM = '2026-08-29-line9654-v1'
CAPTURE_PREFIX = 'data/processed/capture_events/source_reviews/august-2026/'
INDIVIDUAL_PREFIX = 'data/processed/individuals/source_reviews/august-2026/'
CAPTURE_PATH = CAPTURE_PREFIX+STEM+'.csv'
REVIEW_PATH = 'evidence/source_reviews/august-2026/'+STEM+'.json'
ADMISSION_PATH = 'evidence/source_reviews/august-2026/admissions/'+STEM+'.json'
# Append-only reviewed pins, not a caller-extensible registry or candidate list.
ADMITTED = ((ADMISSION_PATH, 2424, '0582d7b6150d6dcc9cbffcd568172fdb23feab5d4b47ba3f32e0331eb693f32c',
    CAPTURE_PATH, 254, '84c7d546bca0eab9a3bf440d0709deade0ec51175cf1a24a8315317b87e0c71a', REVIEW_PATH),
    ('evidence/source_reviews/august-2026/admissions/2026-08-24-batch-v1.json', 4206,
     'b53fe9edce2c11e409ee93c46443f68ad812070f7300cad3a043892a836798a8',
     CAPTURE_PREFIX+'2026-08-24-batch-v1.csv', 518,
     'ac180f173926453fba5c2b80c7f50c9fa8b64483cffdf480c0ff56a39f120add',
     'evidence/source_reviews/august-2026/2026-08-24-batch-v1.json'),
    ('evidence/source_reviews/august-2026/admissions/2026-08-27-batch-v1.json', 4215,
     '90c5f4b3834b511b0d7b971b834c3808659d9f138f06921d9a655aa04a8a512e',
     CAPTURE_PREFIX+'2026-08-27-batch-v1.csv', 525,
     '113f5db498b421c7e48957aee82c04b67cc6c9a1bf007afc9917fa4753747e17',
     'evidence/source_reviews/august-2026/2026-08-27-batch-v1.json'))
# Literal reviewed batch shapes, never a caller-selected record count.
_BATCH_SHAPES = {ADMISSION_PATH: ('2026-08-29', 1), ADMITTED[1][0]: ('2026-08-24', 3),
                 ADMITTED[2][0]: ('2026-08-27', 3)}
_RECORD_FIELDS = {'behavior','coordinate_lines','count','count_basis','event_id','event_place',
    'legacy_aliases','microhabitat','operational_night','primary_sha256','sex','size_note',
    'source_byte_end_exclusive','source_byte_start','source_line_end','source_line_start',
    'source_note','source_slice_sha256','source_time_jst','surface'}
_POINT_FIELDS = {'event_id','gpx_sequence','gpx_trackpoint_index','gpx_time_utc','distance_m',
    'time_delta_seconds','hdop','neighboring_gap_seconds'}
FORBIDDEN_AUTHORITY = core.FORBIDDEN_AUTHORITY
COORDINATE_METHOD = 'original owner TXT coordinates; real GPX point corroboration; no interpolation'
RECOVERY_CLASS = 'PRESERVED_OWNER_CAPTURE_SOURCE_REVIEW'
SCOPE = 'ADMITTED_SOURCE_CAPTURE_OCCURRENCES_ONLY'
REVIEW_NOT_BEFORE = '2026-10-25T18:40:22.614929+00:00'
REVIEW_FIELDS = set(FORBIDDEN_AUTHORITY) | {
    'schema_version','verification_profile','source_sha256','use_roles','reviewed_at',
    'cohort_exposure','scope','independent_device_authentication','permanent_biological_identity',
    'coordinate_method','recovery_class','source_refs','descriptor_ref','proof','proof_sha256'}

def is_family_path(value):
    if type(value) is not str:return False
    normalized = PureWindowsPath(value).as_posix().casefold()
    prefixes=(CAPTURE_PREFIX.casefold(),INDIVIDUAL_PREFIX.casefold())
    if normalized.startswith(prefixes):return True
    # Recognition ONLY: forbidden Windows component aliases must participate in
    # atomic rejection. The original entry must still match a literal pin; this
    # spelling is never used to open or accept an alternate source path.
    rejected_alias='/'.join(part.rstrip(' .') for part in PureWindowsPath(value).parts).casefold()
    return rejected_alias.startswith(prefixes)

def _family_declaration(entry):
    """Recognize closed family intent for rejection, without opening aliases."""
    if type(entry) is not dict:return False
    if is_family_path(entry.get('path')):return True
    ref=entry.get('review_ref')
    if type(ref) is not dict or type(ref.get('path')) is not str:return False
    spelling='/'.join(part.rstrip(' .') for part in PureWindowsPath(ref['path']).parts).casefold()
    return spelling in {pin[6].casefold() for pin in ADMITTED}

def admission_ref():
    path,size,checksum,*_ = ADMITTED[0]
    return dict(path=path,size_bytes=size,sha256=checksum)

def _review_time(value):
    # Only input datetime conversion is classified here; caller callbacks are outside.
    try:return core._time(value)
    except OverflowError as error:raise ValueError('AUGUST_TIME_RANGE') from error

def _bounded_json(raw, tick):
    if type(raw) is not bytes or len(raw)>128*1024:raise ValueError('AUGUST_JSON_SIZE')
    # Bound parser nesting/tokens before allocation, honoring JSON string escapes.
    depth=0;tokens=0;quoted=False;escaped=False
    for byte in raw:
        tick()
        if quoted:
            if escaped:escaped=False
            elif byte==92:escaped=True
            elif byte==34:quoted=False
        elif byte==34:quoted=True
        elif byte in (123,91):depth+=1;tokens+=1
        elif byte in (125,93):depth-=1
        elif byte in (44,58):tokens+=1
        if depth>64 or tokens>16000:raise ValueError('AUGUST_JSON_STRUCTURE_LIMIT')
    return core._owned_review(strict_json(raw,tick),tick,'AUGUST')

def _ref(value, *, maximum=128*1024):
    if (type(value) is not dict or len(value)!=3 or set(value)!={'path','size_bytes','sha256'}
            or type(value['path']) is not str or len(value['path'])>1024 or type(value['size_bytes']) is not int
            or not 0<value['size_bytes']<=maximum or type(value['sha256']) is not str
            or len(value['sha256'])!=64
            or re.fullmatch('[0-9a-f]{64}',value['sha256']) is None):
        raise ValueError('AUGUST_REFERENCE_SCHEMA')

def _load(ref, read_ref, tick):
    tick();_ref(ref);ref=dict(ref)
    pin=next((p for p in ADMITTED if ref==dict(path=p[0],size_bytes=p[1],sha256=p[2])
              and type(ref['size_bytes']) is int),None)
    if pin is None:raise ValueError('AUGUST_UNADMITTED_DESCRIPTOR')
    night,count=_BATCH_SHAPES[pin[0]]
    raw=read_ref(dict(ref));tick()
    if (type(raw) is not bytes or len(raw)!=pin[1] or core._hash(raw,tick)!=pin[2]):
        raise ValueError('AUGUST_DESCRIPTOR_BYTES')
    value=_bounded_json(raw,tick)
    if (set(value)!={'schema_version','family_id','primary_ref','native_byte_proof_ref',
            'owner_context_ref','gpx_ref','records','captures_ref','occurrences_ref',
            'expected_counts','expected_gpx_qc'}
            or value['schema_version']!='habu-august-source-occurrence-descriptor-v1'
            or value['family_id']!=PROFILE or type(value['records']) is not list
            or len(value['records'])!=count
            or core._digest(value['expected_counts'],tick)!=core._digest(dict(events=count,source_occurrences=count),tick)):
        raise ValueError('AUGUST_DESCRIPTOR_SCHEMA')
    if value['captures_ref']!=dict(path=pin[3],size_bytes=pin[4],sha256=pin[5]):
        raise ValueError('AUGUST_DESCRIPTOR_CAPTURE_PIN')
    if (type(value['gpx_ref']) is not dict
            or set(value['gpx_ref'])!={'path','size_bytes','sha256','point_count'}
            or type(value['gpx_ref']['point_count']) is not int
            or not 0<value['gpx_ref']['point_count']<=1000000):
        raise ValueError('AUGUST_DESCRIPTOR_GPX')
    for refvalue in _refs(value).values():_ref(refvalue,maximum=100*1024*1024)
    previous=0;ids=set()
    for record in value['records']:
        tick()
        if (type(record) is not dict or set(record)!=_RECORD_FIELDS
                or any(type(record[k]) is not str for k in _RECORD_FIELDS-
                    {'coordinate_lines','count','legacy_aliases','source_line_start','source_line_end',
                     'source_byte_start','source_byte_end_exclusive'})
                or record['primary_sha256']!=value['primary_ref']['sha256']
                or type(record['count']) is not int or record['count']!=1
                or record['count_basis']!='SINGULAR_STATEMENT_AS_ONE_RECORDED_OCCURRENCE'
                or type(record['legacy_aliases']) is not list or record['legacy_aliases']!=[]
                or any(type(record[k]) is not int for k in ('source_line_start','source_line_end',
                    'source_byte_start','source_byte_end_exclusive'))
                or not previous<record['source_line_start']<=record['source_line_end']<=10506
                or not 0<=record['source_byte_start']<record['source_byte_end_exclusive']<=value['primary_ref']['size_bytes']
                or re.fullmatch('[0-9a-f]{64}',record['source_slice_sha256']) is None
                or record['operational_night']!=night
                or record['event_id']!='AUG2026SRC-L'+str(record['source_line_start'])
                or record['event_id'] in ids
                or type(record['coordinate_lines']) is not list or len(record['coordinate_lines'])!=2
                or any(type(n) is not int or not record['source_line_start']<=n<=record['source_line_end']
                       for n in record['coordinate_lines'])):
            raise ValueError('AUGUST_DESCRIPTOR_SELECTOR')
        stamp=_review_time(record['source_time_jst'])
        # Validate the bounded calendar pair before subtracting the night boundary.
        day=date.fromisoformat(night)
        if (stamp.date() not in (day,day+timedelta(days=1))
                or (stamp-timedelta(hours=7)).date()!=day):
            raise ValueError('AUGUST_DESCRIPTOR_NIGHT')
        previous=record['source_line_end'];ids.add(record['event_id'])
    _qc_schema(value,tick)
    _assert_disjoint(_keys(value)+_protected_aug31_keys(),tick)
    return value

def _qc_schema(desc,tick):
    expected=desc['expected_gpx_qc'];count=len(desc['records'])
    if (type(expected) is not dict or set(expected)!={'track','selected_points'}
            or type(expected['track']) is not dict
            or set(expected['track'])!={'point_count','excluded_points','segment_breaks','maximum_gap_seconds'}
            or type(expected['selected_points']) is not list or len(expected['selected_points'])!=count):
        raise ValueError('AUGUST_GPX_QC_SCHEMA')
    track=expected['track']
    if (any(type(track[k]) is not int or track[k]<0 for k in ('point_count','excluded_points','segment_breaks'))
            or track['point_count']!=desc['gpx_ref']['point_count']
            or type(track['maximum_gap_seconds']) is not float
            or not math.isfinite(track['maximum_gap_seconds']) or track['maximum_gap_seconds']<=0):
        raise ValueError('AUGUST_GPX_QC_SCHEMA')
    for record,row in zip(desc['records'],expected['selected_points']):
        tick()
        if (type(row) is not dict or set(row)!=_POINT_FIELDS or row['event_id']!=record['event_id']
                or type(row['gpx_sequence']) is not int or row['gpx_sequence']<0
                or type(row['gpx_trackpoint_index']) is not int
                or not 0<=row['gpx_trackpoint_index']<track['point_count']
                or type(row['gpx_time_utc']) is not str
                or not row['gpx_time_utc'].endswith('+00:00')
                or any(type(row[k]) is not float or not math.isfinite(row[k]) or not 0<=row[k]<=limit
                       for k,limit in (('distance_m',100),('time_delta_seconds',600),('hdop',10)))
                or type(row['neighboring_gap_seconds']) is not list or len(row['neighboring_gap_seconds'])!=2
                or any(type(g) is not float or not math.isfinite(g) or not 0<g<=30
                       for g in row['neighboring_gap_seconds'])):
            raise ValueError('AUGUST_GPX_QC_SCHEMA')
        _review_time(row['gpx_time_utc'])

def _refs(desc):
    return dict(native_log=desc['primary_ref'],native_byte_proof=desc['native_byte_proof_ref'],
        gpx={k:v for k,v in desc['gpx_ref'].items() if k!='point_count'},
        owner_count_record=desc['owner_context_ref'],captures=desc['captures_ref'],individuals=desc['occurrences_ref'])

def _keys(desc):
    return [(r['primary_sha256'],r['source_byte_start'],r['source_byte_end_exclusive']) for r in desc['records']]

def _protected_aug31_keys():
    from aug31_positive_source_review import EXPECTED,FIXED
    return [(FIXED['native_log'][2],r[3],r[4]) for r in EXPECTED]

def _assert_disjoint(keys, tick):
    last={}
    for checksum,start,end in keys:
        tick()
        if (type(checksum) is not str or re.fullmatch('[0-9a-f]{64}',checksum) is None
                or type(start) is not int or type(end) is not int or not 0<=start<end):
            raise ValueError('AUGUST_PRIMARY_SELECTOR')
    for checksum,start,end in sorted(keys):
        tick()
        if checksum in last and start<last[checksum]:raise ValueError('AUGUST_DUPLICATE_OR_OVERLAPPING_PRIMARY')
        last[checksum]=end

def _definition(desc):
    refs=_refs(desc)
    edges=()
    if (desc['records'][0]['operational_night']=='2026-08-27'
            and [r['event_id'] for r in desc['records']]==['AUG2026SRC-L7853','AUG2026SRC-L8052','AUG2026SRC-L8214']
            and type(desc['gpx_ref']['size_bytes']) is int and type(desc['gpx_ref']['point_count']) is int
            and desc['gpx_ref']==dict(path='data/raw/gpx/2026-08-27__legacy.gpx',size_bytes=5561682,
                sha256='28bdafbaac617fffbe1dc1bd764bfb9ab5179bf623e9e0d323c20d1b9ac9d108',point_count=21005)):
        edges=((20155,20156,'2026-08-27T17:58:40.519000+00:00'),)
    records=tuple(core.Record(r['event_id'],r['source_line_start'],r['source_line_end'],
        r['source_byte_start'],r['source_byte_end_exclusive'],r['source_slice_sha256'],
        r['source_time_jst'],r['event_place'],tuple(r['coordinate_lines']),r['source_note'],
        r['size_note'],r['sex'],r['behavior'],r['microhabitat'],r['surface']) for r in desc['records'])
    return core.Definition(tuple((key,v['path'],v['size_bytes'],v['sha256']) for key,v in refs.items()),
        records,desc['records'][0]['operational_night'],desc['gpx_ref']['point_count'],'AUGUST',True,
        allowed_equal_time_edges=edges)

def _reproduce_loaded(desc, ref, *, read_ref, tick, consume_point):
    # Core retains its references for final rescans; lend only owned copies.
    proof=core.reproduce_sources(_refs(desc),definition=_definition(desc),
        read_ref=lambda value:read_ref(dict(value)),tick=tick,consume_point=consume_point)
    selected=[{key:row[key] for key in expected}
              for row,expected in zip(proof['crosswalk'],desc['expected_gpx_qc']['selected_points'])]
    expected=desc['expected_gpx_qc']
    if (core._digest(proof['gpx_qc'],tick)!=core._digest(expected['track'],tick)
            or core._digest(selected,tick)!=core._digest(expected['selected_points'],tick)):
        raise ValueError('AUGUST_GPX_QC_BINDING')
    # All primary refs were rescanned by the core; close the descriptor as well.
    _load(ref,read_ref,tick)
    return dict(proof,family_id=PROFILE,descriptor_sha256=ref['sha256'],
                operational_night=desc['records'][0]['operational_night'])

def reproduce_sources(descriptor_ref, *, read_ref, tick, consume_point):
    _ref(descriptor_ref);descriptor_ref=dict(descriptor_ref)
    desc=_load(descriptor_ref,read_ref,tick)
    result=_reproduce_loaded(desc,descriptor_ref,read_ref=read_ref,tick=tick,consume_point=consume_point)
    tick();return result

def _verified(review, *, read_ref, tick, consume_point, now):
    review=core._owned_review(review,tick,'AUGUST')
    if (set(review)!=REVIEW_FIELDS or review.get('schema_version')!='1.0'
            or review.get('verification_profile')!=PROFILE or review.get('scope')!=SCOPE
            or review.get('use_roles') not in (['diagnostic_only'],['outcome_label'])
            or review.get('cohort_exposure')!='RESEARCH_EXPOSED'
            or review.get('independent_device_authentication')!='NOT_ESTABLISHED'
            or review.get('permanent_biological_identity')!='NOT_ESTABLISHED'
            or review.get('coordinate_method')!=COORDINATE_METHOD or review.get('recovery_class')!=RECOVERY_CLASS
            or any(review.get(key) is not False for key in FORBIDDEN_AUTHORITY)
            or not _review_time(REVIEW_NOT_BEFORE)<=_review_time(review['reviewed_at'])<=_review_time(now)):
        raise ValueError('AUGUST_PROFILE_OR_AUTHORITY')
    desc=_load(review['descriptor_ref'],read_ref,tick)
    if (review['source_sha256']!=desc['captures_ref']['sha256']
            or core._digest(review['source_refs'],tick)!=core._digest(_refs(desc),tick)):
        raise ValueError('AUGUST_REVIEW_SOURCE_BINDING')
    proof=_reproduce_loaded(desc,review['descriptor_ref'],read_ref=read_ref,tick=tick,consume_point=consume_point)
    if (core._digest(review['proof'],tick)!=core._digest(proof,tick)
            or review['proof_sha256']!=core._digest(proof,tick)):
        raise ValueError('AUGUST_PROOF_BINDING')
    tick();return review,desc,proof

def verify_review(review, *, read_ref, tick, consume_point, now):
    _,_,proof=_verified(review,read_ref=read_ref,tick=tick,consume_point=consume_point,now=now)
    tick();return proof

def preflight_declarations(policy_raw, *, read_ref, tick, consume_point, now):
    """Stage the entire new-family policy set; no source role is updated here."""
    policy=_bounded_json(policy_raw,tick)
    entries=[e for e in policy['sources'] if _family_declaration(e)]
    for entry in entries:
        tick()
        if set(entry)!={'path','size_bytes','sha256','review_ref'} or type(entry.get('path')) is not str:
            raise ValueError('AUGUST_DECLARATION_SCOPE')
    paths=[e['path'] for e in entries]
    if len(paths)!=len(set(PureWindowsPath(p).as_posix().casefold() for p in paths)):
        raise ValueError('AUGUST_DUPLICATE_DECLARATION')
    for index in (0,3,6):
        admitted_paths=[pin[index] for pin in ADMITTED]
        if (any(PureWindowsPath(p).as_posix()!=p for p in admitted_paths)
                or len(admitted_paths)!=len(set(p.casefold() for p in admitted_paths))):
            raise ValueError('AUGUST_DUPLICATE_ADMISSION_PATH')
    by_path={p[3]:p for p in ADMITTED}
    for entry in entries:
        tick();pin=by_path.get(entry['path'])
        if (pin is None or set(entry)!={'path','size_bytes','sha256','review_ref'}
                or type(entry['size_bytes']) is not int or entry['size_bytes']!=pin[4]
                or entry['sha256']!=pin[5]):raise ValueError('AUGUST_DECLARATION_SCOPE')
        _ref(entry['review_ref'])
        if entry['review_ref']['path']!=pin[6]:raise ValueError('AUGUST_CANONICAL_REVIEW_PATH')
    staged=[];loaded={}
    for entry in entries:
        raw=read_ref(dict(entry['review_ref']));tick()
        review=_bounded_json(raw,tick)
        review,desc,proof=_verified(review,read_ref=read_ref,tick=tick,consume_point=consume_point,now=now)
        if desc['captures_ref']['path']!=entry['path']:raise ValueError('AUGUST_DECLARATION_BINDING')
        loaded[review['descriptor_ref']['path']]=desc
        staged.append(dict(entry=entry,review=review))
    # All admitted descriptor selectors, including other batches, participate.
    for path,size,checksum,*_ in ADMITTED:
        if path not in loaded:loaded[path]=_load(dict(path=path,size_bytes=size,sha256=checksum),read_ref,tick)
    _assert_disjoint([key for desc in loaded.values() for key in _keys(desc)]+_protected_aug31_keys(),tick)
    from aug31_positive_source_review import EXPECTED
    identifiers={row[0] for row in EXPECTED}
    for desc in loaded.values():
        for record in desc['records']:
            tick()
            if record['event_id'] in identifiers:raise ValueError('AUGUST_DUPLICATE_SOURCE_OCCURRENCE_ID')
            identifiers.add(record['event_id'])
    for item in staged:read_ref(dict(item['entry']['review_ref']));tick()
    return staged
