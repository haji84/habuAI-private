"""Closed August source-occurrence family; initial admission is Aug29 line9654.

The descriptor is a code-pinned input bound, not an issuer/scientific certificate.
All actual reads, checks and point charges belong to the supplied caller.
"""
from pathlib import PureWindowsPath
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
    CAPTURE_PATH, 254, '84c7d546bca0eab9a3bf440d0709deade0ec51175cf1a24a8315317b87e0c71a', REVIEW_PATH),)
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
    return normalized.startswith((CAPTURE_PREFIX.casefold(), INDIVIDUAL_PREFIX.casefold()))

def admission_ref():
    path,size,checksum,*_ = ADMITTED[0]
    return dict(path=path,size_bytes=size,sha256=checksum)

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
    if (type(value) is not dict or set(value)!={'path','size_bytes','sha256'}
            or type(value['path']) is not str or type(value['size_bytes']) is not int
            or not 0<value['size_bytes']<=maximum or type(value['sha256']) is not str
            or re.fullmatch('[0-9a-f]{64}',value['sha256']) is None):
        raise ValueError('AUGUST_REFERENCE_SCHEMA')

def _load(ref, read_ref, tick):
    tick();_ref(ref)
    pin=next((p for p in ADMITTED if ref==dict(path=p[0],size_bytes=p[1],sha256=p[2])
              and type(ref['size_bytes']) is int),None)
    if pin is None:raise ValueError('AUGUST_UNADMITTED_DESCRIPTOR')
    raw=read_ref(ref);tick()
    if (type(raw) is not bytes or len(raw)!=pin[1] or core._hash(raw,tick)!=pin[2]):
        raise ValueError('AUGUST_DESCRIPTOR_BYTES')
    value=_bounded_json(raw,tick)
    if (set(value)!={'schema_version','family_id','primary_ref','native_byte_proof_ref',
            'owner_context_ref','gpx_ref','records','captures_ref','occurrences_ref',
            'expected_counts','expected_gpx_qc'}
            or value['schema_version']!='habu-august-source-occurrence-descriptor-v1'
            or value['family_id']!=PROFILE or type(value['records']) is not list
            or len(value['records'])!=1
            or core._digest(value['expected_counts'],tick)!=core._digest(dict(events=1,source_occurrences=1),tick)):
        raise ValueError('AUGUST_DESCRIPTOR_SCHEMA')
    if value['captures_ref']!=dict(path=pin[3],size_bytes=pin[4],sha256=pin[5]):
        raise ValueError('AUGUST_DESCRIPTOR_CAPTURE_PIN')
    record=value['records'][0]
    if (record['primary_sha256']!=value['primary_ref']['sha256']
            or type(record['count']) is not int or record['count']!=1
            or record['count_basis']!='SINGULAR_STATEMENT_AS_ONE_RECORDED_OCCURRENCE'
            or record['legacy_aliases']!=[]
            or any(type(record[k]) is not int for k in ('source_line_start','source_line_end',
                'source_byte_start','source_byte_end_exclusive'))
            or type(value['gpx_ref']['point_count']) is not int):
        raise ValueError('AUGUST_DESCRIPTOR_SELECTOR')
    for refvalue in _refs(value).values():_ref(refvalue,maximum=100*1024*1024)
    _assert_disjoint(_keys(value)+_protected_aug31_keys(),tick)
    return value

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
    records=tuple(core.Record(r['event_id'],r['source_line_start'],r['source_line_end'],
        r['source_byte_start'],r['source_byte_end_exclusive'],r['source_slice_sha256'],
        r['source_time_jst'],r['event_place'],tuple(r['coordinate_lines']),r['source_note'],
        r['size_note'],r['sex'],r['behavior'],r['microhabitat'],r['surface']) for r in desc['records'])
    return core.Definition(tuple((key,v['path'],v['size_bytes'],v['sha256']) for key,v in refs.items()),
        records,desc['records'][0]['operational_night'],desc['gpx_ref']['point_count'],'AUGUST',True)

def _reproduce_loaded(desc, ref, *, read_ref, tick, consume_point):
    proof=core.reproduce_sources(_refs(desc),definition=_definition(desc),
        read_ref=read_ref,tick=tick,consume_point=consume_point)
    selected=[{key:row[key] for key in desc['expected_gpx_qc']['selected_points'][0]}
              for row in proof['crosswalk']]
    expected=desc['expected_gpx_qc']
    if (core._digest(proof['gpx_qc'],tick)!=core._digest(expected['track'],tick)
            or core._digest(selected,tick)!=core._digest(expected['selected_points'],tick)):
        raise ValueError('AUGUST_GPX_QC_BINDING')
    # All primary refs were rescanned by the core; close the descriptor as well.
    _load(ref,read_ref,tick)
    return dict(proof,family_id=PROFILE,descriptor_sha256=ref['sha256'],
                operational_night=desc['records'][0]['operational_night'])

def reproduce_sources(descriptor_ref, *, read_ref, tick, consume_point):
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
            or not core._time(REVIEW_NOT_BEFORE)<=core._time(review['reviewed_at'])<=core._time(now)):
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
    entries=[e for e in policy['sources'] if isinstance(e,dict) and is_family_path(e.get('path'))]
    paths=[e['path'] for e in entries]
    if len(paths)!=len(set(PureWindowsPath(p).as_posix().casefold() for p in paths)):
        raise ValueError('AUGUST_DUPLICATE_DECLARATION')
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
        raw=read_ref(entry['review_ref']);tick()
        review=_bounded_json(raw,tick)
        review,desc,proof=_verified(review,read_ref=read_ref,tick=tick,consume_point=consume_point,now=now)
        if desc['captures_ref']['path']!=entry['path']:raise ValueError('AUGUST_DECLARATION_BINDING')
        loaded[review['descriptor_ref']['path']]=desc
        staged.append(dict(entry=entry,review=review))
    # All admitted descriptor selectors, including other batches, participate.
    for path,size,checksum,*_ in ADMITTED:
        if path not in loaded:loaded[path]=_load(dict(path=path,size_bytes=size,sha256=checksum),read_ref,tick)
    _assert_disjoint([key for desc in loaded.values() for key in _keys(desc)]+_protected_aug31_keys(),tick)
    for item in staged:read_ref(item['entry']['review_ref']);tick()
    return staged
