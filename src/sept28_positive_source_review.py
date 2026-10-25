"""Fixed, read-only reproduction of five preserved owner-capture occurrences.

All I/O, deadline checks and point accounting belong to the calling audit. This
profile proves consistency of existing sources, not a trusted issuer, permanent
animal identity, search effort, complete outcomes, or permission to train.
"""
from __future__ import annotations

import base64
import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import math
import re
import zipfile
import xml.etree.ElementTree as ET

from gpx_audit import distance_m, mark_point_anomalies, match_capture_to_points
from master_contracts import digest

PROFILE = 'sept28-owner-capture-crosswalk-v1'
CAPTURE_PATH = 'data/processed/capture_events/2026/2026-09-28.csv'
RAW_PATH = 'data/raw/habu_logs/2026/2026-09-28.json'
INDIVIDUAL_PATH = 'data/processed/individuals/2026/2026-09-28.csv'
GPX_DIR = 'data/raw/gpx_archives/2026-09-28-探索.gpx.lines'
RECEIPT_PATH = 'evidence/source_reviews/2026-09-28-source-capsule-receipt.json'
CAPSULE_NAME = ('ee803478c0a1ec574591fc219fa585afad101539b5ddfaebae966e41c5b60aee'
                '__september-validation.zip.b64')
CAPSULE_PATH = 'evidence/source_reviews/capsules/' + CAPSULE_NAME
CAPTURE_SHA = 'e58d3c26001b62c86c5afe0b94911f3440b58a9f9d5702d93f12a711e9b4e033'
ZIP_SHA = 'ee803478c0a1ec574591fc219fa585afad101539b5ddfaebae966e41c5b60aee'
TXT_SHA = 'f27a9e06cf89b06a68520365d29630d695d59a96810c95081cfbdb88652bd733'
GPX_SHA = '2e9fde7aa459fc100abf8014d95635e697a638679cc9df731f4e0f6a80fb62f3'
IMPORT_AT = '2026-10-25T06:38:59.025479+00:00'
JST = timezone(timedelta(hours=9))
NIGHT = '2026-09-28'

# Pins are already-preserved byte identities, not declarations of source authority.
FIXED = {
    'capsule': (CAPSULE_PATH, 1648327, 'f6b52e4ac4aa3ffc61ae47a3736c48daac17e332f8d7b350f3d7e4f88bc8fc6d'),
    'receipt': (RECEIPT_PATH, None, '9f334ac51184610c899fea0c3988d2a0156731be2675f4f1db68703c6f8aa8cf'),
    'raw_log': (RAW_PATH, 1383, '733194d344f3b53047401672ed82797166f4aa1d8d1065cd57c83464e5ad5f15'),
    'captures': (CAPTURE_PATH, 887, CAPTURE_SHA),
    'individuals': (INDIVIDUAL_PATH, 901, '7aaec196b60bf3d7c7f3883928dfd2d32c149397f495c3eff3b740b90a6762f3'),
    'gpx_manifest': (GPX_DIR + '/manifest.json', 581, '549e961b111576737d4ed4d8031f4fb5415aa38efffd25c1a423fa36e9719e70'),
}
# These IDs already exist in the committed tables. No identifiers are generated.
EXPECTED = (
    ('CAP-20260928-2041-001', 7712, 1, ('CAP-20260928-2041-001-01',)),
    ('CAP-20260928-2205-001', 7935, 1, ('CAP-20260928-2205-001-01',)),
    ('CAP-20260929-0000-001', 8105, 2, ('CAP-20260929-0000-001-01', 'CAP-20260929-0000-001-02')),
    ('CAP-20260929-0008-001', 8115, 1, ('CAP-20260929-0008-001-01',)),
    ('CAP-20260929-0019-001', 8125, 1, ('CAP-20260929-0019-001-01',)),
)
FORBIDDEN_AUTHORITY = (
    'negative_eligibility_assigned', 'search_scope_certified',
    'complete_outcome_coverage_claimed', 'training_authorized',
    'confirmation_authorized', 'official_issuance_authorized', 'production_authorized',
)


def strict_json(raw, tick):
    tick()
    if not isinstance(raw, bytes) or len(raw) > 128 * 1024:
        raise ValueError('SOURCE_REVIEW_JSON_SIZE')
    def unique(pairs):
        tick()
        result = {}
        for key, value in pairs:
            tick()
            if key in result:
                raise ValueError('SOURCE_REVIEW_DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def invalid(_):
        raise ValueError('SOURCE_REVIEW_NONFINITE_JSON')
    def finite_float(text):
        tick()
        result=float(text)
        if not math.isfinite(result):invalid(text)
        return result
    try:
        value = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid,parse_float=finite_float)
    except (RecursionError, UnicodeError) as error:
        raise ValueError('SOURCE_REVIEW_JSON') from error
    tick()
    if not isinstance(value, dict):
        raise ValueError('SOURCE_REVIEW_JSON_OBJECT')
    return value


def _time(value):
    if not isinstance(value, str):
        raise ValueError('SOURCE_REVIEW_TIME')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('SOURCE_REVIEW_TIMEZONE')
    return result.astimezone(JST)


def _csv(raw):
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError('SOURCE_REVIEW_CSV_HEADER')
    result = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in result):
        raise ValueError('SOURCE_REVIEW_CSV_WIDTH')
    return result


def _coordinate(value, low, high):
    try:
        result = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError('SOURCE_REVIEW_COORDINATE') from error
    if not result.is_finite() or not low <= result <= high:
        raise ValueError('SOURCE_REVIEW_COORDINATE')
    return result


def _points(raw, tick, consume_point):
    tick()
    if len(raw) != 6068111 or b'<!DOCTYPE' in raw or b'<!ENTITY' in raw:
        raise ValueError('SOURCE_REVIEW_GPX_SIZE_OR_ENTITY')
    root = ET.fromstring(raw)
    tick()
    points = []
    for sequence, element in enumerate(root.iter()):
        tick()
        if element.tag.rsplit('}', 1)[-1] != 'trkpt':
            continue
        consume_point()
        values = {}
        for child in element.iter():
            tag = child.tag.rsplit('}', 1)[-1]
            if child.text and tag != 'trkpt':
                values.setdefault(tag, child.text.strip())
        lat = _coordinate(element.attrib['lat'], 0, 84)
        lon = _coordinate(element.attrib['lon'], 126, 132)
        hdop = float(values['hdop'])
        if not math.isfinite(hdop) or hdop <= 0:
            raise ValueError('SOURCE_REVIEW_GPX_HDOP')
        points.append(dict(sequence=sequence, trackpoint_index=len(points),
                           time_utc=_time(values['time']).astimezone(timezone.utc),
                           latitude=float(lat), longitude=float(lon), hdop=hdop))
    if len(points) != 22990:
        raise ValueError('SOURCE_REVIEW_GPX_POINTS')
    gaps = [(b['time_utc'] - a['time_utc']).total_seconds() for a, b in zip(points, points[1:])]
    if any(gap <= 0 for gap in gaps):
        raise ValueError('SOURCE_REVIEW_GPX_CHRONOLOGY')
    tick()
    marked = mark_point_anomalies(points)
    tick()
    return marked, dict(point_count=len(points), excluded_points=sum(p['exclude_point'] for p in marked),
                        segment_breaks=sum(p['segment_break_before'] for p in marked),
                        maximum_gap_seconds=round(max(gaps), 3),
                        hdop_at_most_10_points=sum(p['hdop'] <= 10 for p in marked))


def cross_bind(*, native_log, raw_log, captures, individuals, gpx, tick, consume_point):
    """Compare bounded owned bytes; this result alone grants no observation role."""
    tick()
    for raw, limit in ((native_log,128*1024),(raw_log,4096),(captures,4096),
                       (individuals,4096),(gpx,8*1024*1024)):
        if not isinstance(raw,bytes) or len(raw)>limit:
            raise ValueError('SOURCE_REVIEW_PAYLOAD_SIZE_OR_TYPE')
    raw = strict_json(raw_log, tick)
    if (raw.get('source') != 'user Habu log' or raw.get('operational_date') != NIGHT
            or raw.get('capture_summary') != {'individuals': 6, 'capture_events': 5}):
        raise ValueError('SOURCE_REVIEW_OWNER_LOG_SCOPE')
    raw_captures = [(i, row) for i, row in enumerate(raw['events']) if row.get('type') == 'capture']
    events, links = _csv(captures), _csv(individuals)
    if len(events) != 5 or len(raw_captures) != 5 or len(links) != 6:
        raise ValueError('SOURCE_REVIEW_COHORT_CARDINALITY')
    if len({x['individual_id'] for x in links}) != 6:
        raise ValueError('SOURCE_REVIEW_DUPLICATE_INDIVIDUAL')
    lines = native_log.decode('utf-8-sig').splitlines()
    points, qc = _points(gpx, tick, consume_point)
    point_by_sequence = {p['sequence']: p for p in points}
    crosswalk = []
    for position, (event, (raw_index, row), expected) in enumerate(zip(events, raw_captures, EXPECTED)):
        tick()
        ident, line, count, ids = expected
        block = []
        for text in lines[line - 1:]:
            if block and re.fullmatch(r'\d{4}/\d{1,2}/\d{1,2} \d{1,2}:\d{2}', text):
                break
            block.append(text)
        if (len(block) < 9 or block[1] != '捕獲' or not block[2].startswith('ハブ捕獲')
                or any(marker in '\n'.join(block) for marker in ('他人', '第三者', '伝聞', '代理'))):
            raise ValueError('SOURCE_REVIEW_SPECIES_OR_OWNER_CAPTURE')
        source_time = datetime.strptime(block[0], '%Y/%m/%d %H:%M').replace(tzinfo=JST)
        event_time = _time(event['event_time_local'])
        if (event['event_id'] != ident or event.get('event_type') != 'capture'
                or event['operational_date'] != NIGHT
                or (event_time - timedelta(hours=7)).date().isoformat() != NIGHT
                or source_time != event_time or _time(row['time_local']) != event_time):
            raise ValueError('SOURCE_REVIEW_EVENT_BINDING')
        quantities = re.findall(r'(\d+)匹', '\n'.join(block))
        source_count = int(quantities[0]) if len(quantities) == 1 else 1
        if len(quantities) > 1 or (count == 2 and quantities != ['2']):
            raise ValueError('SOURCE_REVIEW_EXPLICIT_TWO_REQUIRED')
        if (type(row.get('individual_count')) is not int or row['individual_count'] != count
                or event['event_count'] != str(count) or source_count != count):
            raise ValueError('SOURCE_REVIEW_COUNT_BINDING')
        numbers = [text for text in block if re.fullmatch(r'-?\d+\.\d+', text)]
        if len(numbers) != 2:
            raise ValueError('SOURCE_REVIEW_ORIGINAL_COORDINATE')
        if (_coordinate(event['latitude'], 0, 84) != _coordinate(numbers[0], 0, 84)
                or _coordinate(event['longitude'], 126, 132) != _coordinate(numbers[1], 126, 132)):
            raise ValueError('SOURCE_REVIEW_COORDINATE_BINDING')
        selected = [(i + 2, item) for i, item in enumerate(links) if item['event_id'] == ident]
        if tuple(item['individual_id'] for _, item in selected) != ids:
            raise ValueError('SOURCE_REVIEW_INDIVIDUAL_BINDING')
        for index, (_, item) in enumerate(selected, 1):
            if (item['individual_index'] != str(index) or item['operational_date'] != NIGHT
                    or _time(item['event_time_local']) != event_time
                    or item['size_note'].replace('～', '~') not in block[2]
                    or (item['sex'] and item['sex'] not in block[2])):
                raise ValueError('SOURCE_REVIEW_INDIVIDUAL_ATTRIBUTES')
        match = match_capture_to_points(dict(event, datetime_jst=event_time.isoformat()), points)
        tick()
        point = point_by_sequence[match['matched_sequence']]
        pi = point['trackpoint_index']
        gaps = [(point['time_utc'] - points[pi - 1]['time_utc']).total_seconds() if pi else None,
                (points[pi + 1]['time_utc'] - point['time_utc']).total_seconds() if pi + 1 < len(points) else None]
        if (match['match_status'] != 'matched_100m_10min' or point['exclude_point']
                or point['segment_break_before'] or point['hdop'] > 10
                or any(gap is None or not 0 < gap <= 30 for gap in gaps)):
            raise ValueError('SOURCE_REVIEW_ACTUAL_GPX_POINT')
        crosswalk.append(dict(event_id=ident, csv_row=position + 2, raw_event_index=raw_index,
                              source_line=line, count=count, individual_ids=list(ids),
                              individual_csv_rows=[i for i, _ in selected],
                              coordinate_binding='EXACT_ORIGINAL_DECIMAL_EQUAL',
                              gpx_sequence=point['sequence'], gpx_trackpoint_index=pi,
                              gpx_time_utc=point['time_utc'].isoformat(),
                              distance_m=round(match['distance_m'], 3),
                              time_delta_seconds=round(match['time_delta_s'], 3),
                              hdop=point['hdop'], neighboring_gap_seconds=gaps))
    tick()
    return dict(event_count=5, individual_count=6, crosswalk=crosswalk, gpx_qc=qc,
                negative_eligibility_assigned=False, training_authorized=False)


def reproduce_sources(refs, *, read_ref, tick, consume_point):
    """Reproduce pinned byte lineage using only the calling audit's reader."""
    tick()
    if not isinstance(refs, dict) or set(refs) != set(FIXED) | {'gpx_parts'}:
        raise ValueError('SOURCE_REVIEW_REFERENCE_SET')
    seen = []
    def read(ref):
        tick()
        if (not isinstance(ref, dict) or set(ref) != {'path', 'sha256', 'size_bytes'}
                or type(ref['size_bytes']) is not int or not 0 < ref['size_bytes'] <= 2 * 1024 * 1024
                or not isinstance(ref['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', ref['sha256'])):
            raise ValueError('SOURCE_REVIEW_REFERENCE_SCHEMA')
        raw = read_ref(ref)
        tick()
        if len(raw) != ref['size_bytes'] or hashlib.sha256(raw).hexdigest() != ref['sha256']:
            raise ValueError('SOURCE_REVIEW_REFERENCE_BYTES')
        tick()
        return raw
    payloads = {}
    for role, (path, size, sha) in FIXED.items():
        ref = refs[role]
        if (not isinstance(ref,dict) or ref.get('path') != path or ref.get('sha256') != sha
                or (size is not None and ref.get('size_bytes') != size)):
            raise ValueError('SOURCE_REVIEW_FIXED_REFERENCE')
        payloads[role] = read(ref); seen.append(ref)
    parts = refs['gpx_parts']
    if not isinstance(parts, list) or len(parts) != 24:
        raise ValueError('SOURCE_REVIEW_GPX_PARTS')
    raw_parts = []
    for index, ref in enumerate(parts):
        if not isinstance(ref,dict) or ref.get('path') != GPX_DIR + '/part_%03d.txt' % index:
            raise ValueError('SOURCE_REVIEW_GPX_PART_SELECTOR')
        raw_parts.append(read(ref)); seen.append(ref)
    manifest = strict_json(payloads['gpx_manifest'], tick)
    gpx = b'\n'.join(raw_parts)
    if (manifest.get('part_count') != 24 or manifest.get('raw_sha256') != GPX_SHA
            or len(gpx) != 6068111 or hashlib.sha256(gpx).hexdigest() != GPX_SHA):
        raise ValueError('SOURCE_REVIEW_GPX_RECONSTRUCTION')
    tick()
    receipt = strict_json(payloads['receipt'], tick)
    if (receipt.get('imported_at_utc') != IMPORT_AT
            or receipt.get('original_archive_sha256') != ZIP_SHA
            or receipt.get('runtime_capsule_path') != CAPSULE_PATH):
        raise ValueError('SOURCE_REVIEW_CAPSULE_RECEIPT')
    original_receipt = base64.b64decode(receipt['origin_receipt_base64'], validate=True)
    if hashlib.sha256(original_receipt).hexdigest() != receipt['origin_receipt_sha256']:
        raise ValueError('SOURCE_REVIEW_ORIGIN_RECEIPT')
    origin = strict_json(original_receipt, tick)
    if not any(item.get('sha256') == ZIP_SHA and item.get('size_bytes') == 1220188
               for item in origin.get('sources', [])):
        raise ValueError('SOURCE_REVIEW_ORIGIN_ARCHIVE')
    tick()
    archive_bytes = base64.b64decode(b''.join(payloads['capsule'].split()), validate=True)
    tick()
    if len(archive_bytes) != 1220188 or hashlib.sha256(archive_bytes).hexdigest() != ZIP_SHA:
        raise ValueError('SOURCE_REVIEW_ARCHIVE_BYTES')
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            members = archive.infolist()
            if (len(members) != 19 or len({x.filename for x in members}) != 19
                    or sum(x.file_size for x in members) > 4 * 1024 * 1024):
                raise ValueError('SOURCE_REVIEW_ARCHIVE_LIMIT')
            for item in members:
                with archive.open(item) as handle:
                    while handle.read(65536):
                        tick()
            native = archive.read(receipt['native_member'])
    except (zipfile.BadZipFile, KeyError, RuntimeError) as error:
        # Do not catch the caller's deadline/budget exception (a RuntimeError).
        if isinstance(error, RuntimeError) and not isinstance(error, zipfile.BadZipFile):
            raise
        raise ValueError('SOURCE_REVIEW_ARCHIVE') from error
    tick()
    if len(native) != 96493 or hashlib.sha256(native).hexdigest() != TXT_SHA:
        raise ValueError('SOURCE_REVIEW_NATIVE_MEMBER')
    proof = cross_bind(native_log=native, raw_log=payloads['raw_log'], captures=payloads['captures'],
                       individuals=payloads['individuals'], gpx=gpx, tick=tick, consume_point=consume_point)
    for ref in seen:
        read(ref)
    tick()
    return proof


def verify_review(review, *, read_ref, tick, consume_point, now):
    tick()
    if (not isinstance(review, dict) or review.get('verification_profile') != PROFILE
            or review.get('schema_version') != '1.0' or review.get('source_sha256') != CAPTURE_SHA
            or review.get('use_roles') not in (['diagnostic_only'], ['outcome_label'])
            or review.get('cohort_exposure') != 'RESEARCH_EXPOSED'
            or review.get('independent_device_authentication') != 'NOT_ESTABLISHED'
            or review.get('scope') != 'EXISTING_FIVE_EVENTS_SIX_INDIVIDUAL_OCCURRENCES_ONLY'
            or any(review.get(key) is not False for key in FORBIDDEN_AUTHORITY)
            or not _time(IMPORT_AT) <= _time(review['reviewed_at']) <= _time(now)
            or review.get('coordinate_method') != 'original owner TXT coordinates; real GPX point corroboration; no interpolation'
            or review.get('recovery_class') != 'PRESERVED_OWNER_CAPTURE_SOURCE_REVIEW'):
        raise ValueError('SOURCE_REVIEW_PROFILE_OR_AUTHORITY')
    proof = reproduce_sources(review['source_refs'], read_ref=read_ref, tick=tick, consume_point=consume_point)
    tick()
    if (review.get('proof') != proof or review.get('proof_sha256') != digest(proof)
            or digest(review.get('proof')) != digest(proof)):
        raise ValueError('SOURCE_REVIEW_PROOF_BINDING')
    tick()
    return proof
