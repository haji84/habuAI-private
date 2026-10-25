"""Fixed two-record positive source crosswalk; no permanent animal identity.

All file reads, time checks and point charges are supplied by the existing Audit.
The returned proof is source consistency, never permission to train or issue P0.
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import math
from pathlib import PureWindowsPath
import re
import xml.etree.ElementTree as ET

from gpx_audit import mark_point_anomalies, match_capture_to_points
from master_contracts import digest
from sept28_positive_source_review import strict_json

PROFILE = 'aug31-owner-capture-occurrence-crosswalk-v1'
NIGHT = '2026-08-31'
JST = timezone(timedelta(hours=9))
REVIEW_NOT_BEFORE = '2026-10-25T15:42:47+00:00'
CAPTURE_PATH = 'data/processed/capture_events/2026/2026-08-31.csv'
INDIVIDUAL_PATH = 'data/processed/individuals/2026/2026-08-31.csv'
REVIEW_PATH = 'evidence/source_reviews/2026-08-31-positive-source-review.json'
CAPTURE_SIZE = 413
CAPTURE_SHA = '137c04b5abe6713c1668633fe10afa61f601a5c0a8d5331471d71f8cbf0a972f'
COORDINATE_METHOD = 'original owner TXT coordinates; real GPX point corroboration; no interpolation'
RECOVERY_CLASS = 'PRESERVED_OWNER_CAPTURE_SOURCE_REVIEW'
SCOPE = 'EXISTING_TWO_SOURCE_CAPTURE_OCCURRENCES_ONLY'
FORBIDDEN_AUTHORITY = (
    'negative_eligibility_assigned', 'search_scope_certified',
    'complete_outcome_coverage_claimed', 'training_authorized',
    'confirmation_authorized', 'official_issuance_authorized',
    'promotion_authorized', 'production_authorized',
)
FIXED = {
    'native_log': ('evidence/recovered_sources/2026-08-habu-log-10506-lines-library-read.txt',
                   116496, '130dedae6e04501f4be41fff4ff549a9cfc1a1840dcbb0126359b04465ab7e8c'),
    'native_byte_proof': ('evidence/recovered_sources/2026-08-native-original-library-byte-proof.json',
                          1408, 'a62dd9d612766f6626e2561a0705dbb14cfd1d862e4afc84efec40da34494745'),
    'gpx': ('data/raw/gpx/2026-08-31__legacy.gpx', 4753470,
            '870047567bb0d9bafca0789f768fda3b7b90eb5788f259d043cdb885ce219bd1'),
    'owner_count_record': ('data/reconstructions/habu_captures/2026-08-count-correction-owner-confirmed-47.json',
                           2551, '4fe0fcd7c7e4f67f51d86fc6962d5c2b5ae78d9c04b86412356937f773158c92'),
    'captures': (CAPTURE_PATH, CAPTURE_SIZE, CAPTURE_SHA),
    'individuals': (INDIVIDUAL_PATH, 378,
                    '6d0c01d185722044bf976f2858461990518dffe6ee402815269ad94f5f242947'),
}
# These keys are newly derived record/occurrence references, NOT original animal IDs.
EXPECTED = (
    ('AUG31SRC-L10110', 10110, 10119, 112368, 112489,
     '0e3ef4d50ff5cf9c98b3e0012d9fc75e7a24d6667e0f6b5f259ed5a86e7b4581',
     '2026-08-31T21:43:00+09:00', '', (10117, 10118)),
    ('AUG31SRC-L10492', 10492, 10500, 116249, 116392,
     '6bd4b0ed2c572d9b0bd39f8137456e53c7721028f7f88e6e03e4a822c88bceea',
     '2026-09-01T01:17:00+09:00', '瀬戸内町県道626号', (10499, 10500)),
)
REVIEW_FIELDS = set(FORBIDDEN_AUTHORITY) | {
    'schema_version', 'verification_profile', 'source_sha256', 'use_roles',
    'reviewed_at', 'cohort_exposure', 'scope', 'independent_device_authentication',
    'permanent_biological_identity', 'coordinate_method', 'recovery_class',
    'source_refs', 'proof', 'proof_sha256',
}


def is_capture_path(value):
    """Recognize aliases of this sole new CSV, so they cannot use legacy admission."""
    return type(value) is str and PureWindowsPath(value).as_posix().casefold() == CAPTURE_PATH.casefold()


def _time(value):
    if type(value) is not str:
        raise ValueError('AUG31_TIME')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('AUG31_TIMEZONE')
    return result.astimezone(JST)


def _hash(raw, tick):
    tick();result = hashlib.sha256(raw).hexdigest();tick()
    return result


def _digest(value, tick):
    tick();result = digest(value);tick()
    return result


def _owned_review(value, tick):
    """Bound JSON before copying; ordinary caller-check exceptions stay outside catches."""
    stack = [(value, 0)];nodes = 0
    while stack:
        tick();item, depth = stack.pop();nodes += 1
        if nodes > 16000 or depth > 64:
            raise ValueError('AUG31_REVIEW_STRUCTURE_LIMIT')
        kind = type(item)
        if kind in (dict, list):
            if len(item) + len(stack) + nodes > 16000:
                raise ValueError('AUG31_REVIEW_STRUCTURE_LIMIT')
            if kind is dict:
                if any(type(k) is not str for k in item):
                    raise ValueError('AUG31_REVIEW_JSON_TYPE')
                stack.extend((v, depth + 1) for v in item.values())
            else:stack.extend((v, depth + 1) for v in item)
        elif kind not in (str, int, float, bool, type(None)):
            raise ValueError('AUG31_REVIEW_JSON_TYPE')
        elif kind is int and item.bit_length() > 2048:
            raise ValueError('AUG31_REVIEW_NUMBER')
        elif kind is float and not math.isfinite(item):
            raise ValueError('AUG31_REVIEW_NUMBER')
        elif kind is str and len(item) > 128 * 1024:
            raise ValueError('AUG31_REVIEW_SIZE')
    parts = [];size = 0
    iterator = iter(json.JSONEncoder(ensure_ascii=False, allow_nan=False,
                                    sort_keys=True, separators=(',', ':')).iterencode(value))
    while True:
        tick()
        try:piece = next(iterator)
        except StopIteration:break
        raw = piece.encode('utf-8');size += len(raw)
        if size > 128 * 1024:
            raise ValueError('AUG31_REVIEW_SIZE')
        parts.append(raw)
    tick();raw = b''.join(parts);tick()
    return strict_json(raw, tick)


def _csv(raw, tick):
    tick();reader = csv.DictReader(io.StringIO(raw.decode('utf-8')))
    if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError('AUG31_CSV_HEADER')
    rows = []
    for row in reader:
        tick()
        if len(rows) >= 2 or None in row or any(v is None for v in row.values()):
            raise ValueError('AUG31_CSV_CARDINALITY_OR_WIDTH')
        rows.append(row)
    if len(rows) != 2:
        raise ValueError('AUG31_CSV_CARDINALITY')
    return rows


def _coordinate(value, low, high):
    try:result = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError('AUG31_COORDINATE') from error
    if not result.is_finite() or not low <= result <= high:
        raise ValueError('AUG31_COORDINATE')
    return result


def _points(raw, tick, consume_point):
    tick()
    if (type(raw) is not bytes or len(raw) != FIXED['gpx'][1]
            or b'<!DOCTYPE' in raw or b'<!ENTITY' in raw):
        raise ValueError('AUG31_GPX_SIZE_OR_ENTITY')
    root = ET.fromstring(raw);tick();points = []
    for sequence, element in enumerate(root.iter()):
        tick()
        if element.tag.rsplit('}', 1)[-1] != 'trkpt':continue
        consume_point()
        if len(points) >= 17906:raise ValueError('AUG31_GPX_POINTS')
        values = {}
        for child in element.iter():
            tick();tag = child.tag.rsplit('}', 1)[-1]
            if child.text and tag != 'trkpt':values.setdefault(tag, child.text.strip())
        lat = _coordinate(element.attrib['lat'], 0, 84)
        lon = _coordinate(element.attrib['lon'], 126, 132)
        hdop = float(values['hdop'])
        if not math.isfinite(hdop) or hdop <= 0:raise ValueError('AUG31_GPX_HDOP')
        points.append(dict(sequence=sequence, trackpoint_index=len(points),
            time_utc=_time(values['time']).astimezone(timezone.utc),
            latitude=float(lat), longitude=float(lon), hdop=hdop))
    if len(points) != 17906:raise ValueError('AUG31_GPX_POINTS')
    gaps = []
    for a, b in zip(points, points[1:]):
        tick();gap = (b['time_utc'] - a['time_utc']).total_seconds()
        if gap <= 0:raise ValueError('AUG31_GPX_CHRONOLOGY')
        gaps.append(gap)
    tick();marked = mark_point_anomalies(points);tick()
    return marked, dict(point_count=len(points), excluded_points=sum(p['exclude_point'] for p in marked),
        segment_breaks=sum(p['segment_break_before'] for p in marked), maximum_gap_seconds=round(max(gaps), 3))


def _cross_bind(payloads, *, tick, consume_point):
    """Internal bounded bytes seam; only reproduce_sources supplies pinned payloads."""
    tick()
    if type(payloads) is not dict or set(payloads) != set(FIXED):
        raise ValueError('AUG31_PAYLOAD_SET')
    for key, (_, limit, _) in FIXED.items():
        if type(payloads[key]) is not bytes or len(payloads[key]) > limit:
            raise ValueError('AUG31_PAYLOAD_SIZE_OR_TYPE')
    native = payloads['native_log'];lines = native.splitlines(keepends=True)
    if len(lines) != 10506 or b'\r' in native:
        raise ValueError('AUG31_NATIVE_LINES')
    offsets = [0]
    for line in lines:tick();offsets.append(offsets[-1] + len(line))
    provenance = strict_json(payloads['native_byte_proof'], tick)
    original = provenance['user_uploaded_native_source']
    if (provenance['verification_result'] != 'EXACT_SOURCE_BYTES_IDENTICAL'
            or original['native_raw_sha256'] != FIXED['native_log'][2]
            or type(original['native_raw_size_bytes']) is not int or original['native_raw_size_bytes'] != len(native)
            or provenance['file_device_authenticity_crypto_proved'] is not False):
        raise ValueError('AUG31_NATIVE_PROVENANCE')
    count_record = strict_json(payloads['owner_count_record'], tick)
    if count_record['count_scope'] != 'PERSONAL_HABU_CAPTURE_MONTHLY_AGGREGATE':
        raise ValueError('AUG31_OWNER_CONTEXT')
    if (count_record['owner_confirmation']['confirmed_count'] != 47
            or count_record['reconciliation']['newly_allocated_august31_day_count'] != 2
            or count_record['reconciliation']['corrected_cumulative_october_20'] != 243):
        raise ValueError('AUG31_OWNER_CONTEXT')
    events = _csv(payloads['captures'], tick);links = _csv(payloads['individuals'], tick)
    if len({r['event_id'] for r in events}) != 2 or len({r['individual_id'] for r in links}) != 2:
        raise ValueError('AUG31_DUPLICATE_RECORD_OR_OCCURRENCE')
    points, qc = _points(payloads['gpx'], tick, consume_point)
    by_sequence = {p['sequence']: p for p in points};crosswalk = []
    for i, expected in enumerate(EXPECTED):
        tick();key, start, end, byte_start, byte_end, slice_sha, clock, place, coordinate_lines = expected
        block = native[byte_start:byte_end]
        if (offsets[start - 1] != byte_start or offsets[end] != byte_end
                or _hash(block, tick) != slice_sha):raise ValueError('AUG31_NATIVE_SELECTOR')
        text = block.decode('utf-8').splitlines();event, link = events[i], links[i]
        if (text[1:3] != ['捕獲', 'ハブ捕獲100~120オス']
                or any(v in '\n'.join(text) for v in ('他人', '第三者', '伝聞', '代理'))):
            raise ValueError('AUG31_SPECIES_OR_OWNER_STATEMENT')
        stamp = datetime.strptime(text[0], '%Y/%m/%d %H:%M').replace(tzinfo=JST)
        if (stamp != _time(clock) or event['event_id'] != key or event['event_type'] != 'capture'
                or event['event_count'] != '1' or event['operational_date'] != NIGHT
                or _time(event['event_time_local']) != stamp
                or (stamp - timedelta(hours=7)).date().isoformat() != NIGHT):
            raise ValueError('AUG31_EVENT_BINDING')
        if (event['source_note'] != text[2] or event['surface'] != text[5] or event['event_place'] != place):
            raise ValueError('AUG31_EVENT_ATTRIBUTES')
        coordinates = [lines[n - 1].decode('utf-8').removesuffix('\n') for n in coordinate_lines]
        for column, original_value, low, high in zip(('latitude', 'longitude'), coordinates, (0, 126), (84, 132)):
            if (event[column] != original_value
                    or _coordinate(event[column], low, high) != _coordinate(original_value, low, high)):
                raise ValueError('AUG31_ORIGINAL_COORDINATE')
        if (link['individual_id'] != key + '-OCC01' or link['event_id'] != key or link['individual_index'] != '1'
                or link['operational_date'] != NIGHT or _time(link['event_time_local']) != stamp
                or link['event_place'] != place or link['size_note'] != '100~120' or link['sex'] != 'オス'
                or link['behavior'] != text[3] or link['microhabitat'] != text[4]):
            raise ValueError('AUG31_OCCURRENCE_BINDING')
        tick();match = match_capture_to_points(dict(event, datetime_jst=stamp.isoformat()), points);tick()
        point = by_sequence[match['matched_sequence']];pi = point['trackpoint_index']
        neighbors = [(point['time_utc'] - points[pi - 1]['time_utc']).total_seconds() if pi else None,
                     (points[pi + 1]['time_utc'] - point['time_utc']).total_seconds() if pi + 1 < len(points) else None]
        if (match['match_status'] != 'matched_100m_10min' or point['exclude_point'] or point['segment_break_before']
                or point['hdop'] > 10 or any(g is None or not 0 < g <= 30 for g in neighbors)):
            raise ValueError('AUG31_ACTUAL_GPX_POINT')
        crosswalk.append(dict(event_id=key, individual_occurrence_id=link['individual_id'], csv_row=i + 2,
            individual_csv_row=i + 2, source_line_start=start, source_line_end=end,
            source_byte_start=byte_start, source_byte_end_exclusive=byte_end, source_slice_sha256=slice_sha,
            source_time_jst=stamp.isoformat(), count=1, count_basis='SINGULAR_STATEMENT_AS_ONE_RECORDED_OCCURRENCE',
            coordinate_lines=list(coordinate_lines), coordinate_binding='EXACT_ORIGINAL_DECIMAL_EQUAL',
            gpx_sequence=point['sequence'], gpx_trackpoint_index=pi, gpx_time_utc=point['time_utc'].isoformat(),
            distance_m=round(match['distance_m'], 3), time_delta_seconds=round(match['time_delta_s'], 3),
            hdop=point['hdop'], neighboring_gap_seconds=neighbors))
    tick()
    return dict(event_count=2, individual_occurrence_count=2, permanent_biological_identity_verified=False,
                crosswalk=crosswalk, gpx_qc=qc, **{key: False for key in FORBIDDEN_AUTHORITY})


def reproduce_sources(refs, *, read_ref, tick, consume_point):
    """Reproduce fixed bytes; caller owns all actual I/O, resources and finalization."""
    tick()
    if type(refs) is not dict or set(refs) != set(FIXED):raise ValueError('AUG31_REFERENCE_SET')
    seen = [];payloads = {}
    def read(key, ref):
        tick();path, size, sha = FIXED[key]
        if (type(ref) is not dict or set(ref) != {'path', 'sha256', 'size_bytes'}
                or ref['path'] != path or ref['sha256'] != sha
                or type(ref['size_bytes']) is not int or ref['size_bytes'] != size):
            raise ValueError('AUG31_FIXED_REFERENCE')
        raw = read_ref(ref);tick()
        if type(raw) is not bytes or len(raw) != size or _hash(raw, tick) != sha:
            raise ValueError('AUG31_REFERENCE_BYTES')
        return raw
    for key in FIXED:
        payloads[key] = read(key, refs[key]);seen.append((key, refs[key]))
    proof = _cross_bind(payloads, tick=tick, consume_point=consume_point)
    for key, ref in seen:read(key, ref)
    tick();return proof


def verify_review(review, *, read_ref, tick, consume_point, now):
    review = _owned_review(review, tick)
    if (set(review) != REVIEW_FIELDS or review.get('schema_version') != '1.0'
            or review.get('verification_profile') != PROFILE or review.get('source_sha256') != CAPTURE_SHA
            or review.get('use_roles') not in (['diagnostic_only'], ['outcome_label'])
            or review.get('scope') != SCOPE or review.get('cohort_exposure') != 'RESEARCH_EXPOSED'
            or review.get('independent_device_authentication') != 'NOT_ESTABLISHED'
            or review.get('permanent_biological_identity') != 'NOT_ESTABLISHED'
            or review.get('coordinate_method') != COORDINATE_METHOD or review.get('recovery_class') != RECOVERY_CLASS
            or any(review.get(key) is not False for key in FORBIDDEN_AUTHORITY)
            or not _time(REVIEW_NOT_BEFORE) <= _time(review['reviewed_at']) <= _time(now)):
        raise ValueError('AUG31_PROFILE_OR_AUTHORITY')
    proof = reproduce_sources(review['source_refs'], read_ref=read_ref, tick=tick, consume_point=consume_point)
    if (_digest(review['proof'], tick) != _digest(proof, tick)
            or review['proof_sha256'] != _digest(proof, tick)):
        raise ValueError('AUG31_PROOF_BINDING')
    tick();return proof
