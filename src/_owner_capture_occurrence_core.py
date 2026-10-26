"""Private closed, pinned owner-capture crosswalk core; no source admission API.

Only reviewed fixed facades construct Definition. Reads/checks/point charges are
supplied by their caller; this module creates no clock, Audit or file reader.
"""
from dataclasses import dataclass
import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import math
import xml.etree.ElementTree as ET
from gpx_audit import mark_point_anomalies, match_capture_to_points
from master_contracts import digest
from sept28_positive_source_review import strict_json

JST = timezone(timedelta(hours=9))
FORBIDDEN_AUTHORITY = ('negative_eligibility_assigned', 'search_scope_certified',
    'complete_outcome_coverage_claimed', 'training_authorized', 'confirmation_authorized',
    'official_issuance_authorized', 'promotion_authorized', 'production_authorized')

@dataclass(frozen=True)
class Record:
    key: str
    start: int
    end: int
    byte_start: int
    byte_end: int
    slice_sha: str
    clock: str
    place: str
    coordinate_lines: tuple
    note: str
    size_note: str
    sex: str
    behavior: str = ''
    microhabitat: str = ''
    surface: str = ''
    @property
    def selector(self):
        return (self.key,self.start,self.end,self.byte_start,self.byte_end,self.slice_sha,
                self.clock,self.place,self.coordinate_lines)

@dataclass(frozen=True)
class Definition:
    references: tuple
    records: tuple
    night: str
    point_count: int
    prefix: str = 'AUG31'
    strict_attributes: bool = False
    allowed_equal_time_edges: tuple = ()
    @property
    def fixed(self):
        return {row[0]:row[1:] for row in self.references}

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



def _owned_review(value, tick, prefix="AUG31"):
    """Bound JSON before copying; ordinary caller-check exceptions stay outside catches."""
    stack = [(value, 0)];nodes = 0
    while stack:
        tick();item, depth = stack.pop();nodes += 1
        if nodes > 16000 or depth > 64:
            raise ValueError(f'{prefix}_REVIEW_STRUCTURE_LIMIT')
        kind = type(item)
        if kind in (dict, list):
            if len(item) + len(stack) + nodes > 16000:
                raise ValueError(f'{prefix}_REVIEW_STRUCTURE_LIMIT')
            if kind is dict:
                for key in item:
                    tick()
                    if type(key) is not str:
                        raise ValueError(f'{prefix}_REVIEW_JSON_TYPE')
                    if len(key) > 128 * 1024:
                        raise ValueError(f'{prefix}_REVIEW_SIZE')
                stack.extend((v, depth + 1) for v in item.values())
            else:stack.extend((v, depth + 1) for v in item)
        elif kind not in (str, int, float, bool, type(None)):
            raise ValueError(f'{prefix}_REVIEW_JSON_TYPE')
        elif kind is int and item.bit_length() > 2048:
            raise ValueError(f'{prefix}_REVIEW_NUMBER')
        elif kind is float and not math.isfinite(item):
            raise ValueError(f'{prefix}_REVIEW_NUMBER')
        elif kind is str and len(item) > 128 * 1024:
            raise ValueError(f'{prefix}_REVIEW_SIZE')
    parts = [];size = 0
    iterator = iter(json.JSONEncoder(ensure_ascii=False, allow_nan=False,
                                    sort_keys=True, separators=(',', ':')).iterencode(value))
    while True:
        tick()
        try:piece = next(iterator)
        except StopIteration:break
        raw = piece.encode('utf-8');size += len(raw)
        if size > 128 * 1024:
            raise ValueError(f'{prefix}_REVIEW_SIZE')
        parts.append(raw)
    tick();raw = b''.join(parts);tick()
    return strict_json(raw, tick)



def _csv(raw, tick, count=2, prefix="AUG31"):
    tick();reader = csv.DictReader(io.StringIO(raw.decode('utf-8')))
    if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError(f'{prefix}_CSV_HEADER')
    rows = []
    for row in reader:
        tick()
        if len(rows) >= count or None in row or any(v is None for v in row.values()):
            raise ValueError(f'{prefix}_CSV_CARDINALITY_OR_WIDTH')
        rows.append(row)
    if len(rows) != count:
        raise ValueError(f'{prefix}_CSV_CARDINALITY')
    return rows



def _coordinate(value, low, high):
    try:result = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError('AUG31_COORDINATE') from error
    if not result.is_finite() or not low <= result <= high:
        raise ValueError('AUG31_COORDINATE')
    return result



def _points(raw, tick, consume_point, *, definition):
    tick()
    if (type(raw) is not bytes or len(raw) != definition.fixed['gpx'][1]
            or b'<!DOCTYPE' in raw or b'<!ENTITY' in raw):
        raise ValueError(f'{definition.prefix}_GPX_SIZE_OR_ENTITY')
    root = ET.fromstring(raw);tick();points = []
    for sequence, element in enumerate(root.iter()):
        tick()
        if element.tag.rsplit('}', 1)[-1] != 'trkpt':continue
        consume_point()
        if len(points) >= definition.point_count:raise ValueError(f'{definition.prefix}_GPX_POINTS')
        values = {}
        for child in element.iter():
            tick();tag = child.tag.rsplit('}', 1)[-1]
            if child.text and tag != 'trkpt':values.setdefault(tag, child.text.strip())
        lat = _coordinate(element.attrib['lat'], 0, 84)
        lon = _coordinate(element.attrib['lon'], 126, 132)
        hdop = float(values['hdop'])
        if not math.isfinite(hdop) or hdop <= 0:raise ValueError(f'{definition.prefix}_GPX_HDOP')
        points.append(dict(sequence=sequence, trackpoint_index=len(points),
            time_utc=_time(values['time']).astimezone(timezone.utc),
            latitude=float(lat), longitude=float(lon), hdop=hdop))
    if len(points) != definition.point_count:raise ValueError(f'{definition.prefix}_GPX_POINTS')
    edges = definition.allowed_equal_time_edges
    if type(edges) is not tuple:raise ValueError(f'{definition.prefix}_GPX_EQUAL_TIME_EDGE')
    if edges:
        tick()
        if (len(edges) != 1 or type(edges[0]) is not tuple or len(edges[0]) != 3
                or type(edges[0][0]) is not int or type(edges[0][1]) is not int
                or type(edges[0][2]) is not str
                or edges[0] != (20155, 20156, '2026-08-27T17:58:40.519000+00:00')
                or definition.night != '2026-08-27' or type(definition.point_count) is not int
                or definition.point_count != 21005 or type(definition.fixed['gpx'][1]) is not int
                or definition.fixed['gpx'] != ('data/raw/gpx/2026-08-27__legacy.gpx', 5561682,
                    '28bdafbaac617fffbe1dc1bd764bfb9ab5179bf623e9e0d323c20d1b9ac9d108')):
            raise ValueError(f'{definition.prefix}_GPX_EQUAL_TIME_EDGE')
    gaps = [];observed = set()
    for index, (a, b) in enumerate(zip(points, points[1:]), 1):
        tick();gap = (b['time_utc'] - a['time_utc']).total_seconds()
        if gap <= 0:
            edge = (index - 1, index, b['time_utc'].isoformat())
            if gap < 0 or not edges or edge not in edges:
                raise ValueError(f'{definition.prefix}_GPX_CHRONOLOGY')
            observed.add(edge)
        gaps.append(gap)
    if edges:
        tick()
        if observed != set(edges):raise ValueError(f'{definition.prefix}_GPX_EQUAL_TIME_EDGE')
    tick();marked = mark_point_anomalies(points);tick()
    if edges:
        for _, current, _ in edges:
            tick()
            if marked[current]['exclude_point'] is not False or marked[current]['segment_break_before'] is not True:
                raise ValueError(f'{definition.prefix}_GPX_EQUAL_TIME_BREAK')
    return marked, dict(point_count=len(points), excluded_points=sum(p['exclude_point'] for p in marked),
        segment_breaks=sum(p['segment_break_before'] for p in marked), maximum_gap_seconds=round(max(gaps), 3))



def _cross_bind(payloads, *, definition, tick, consume_point):
    """Internal bounded bytes seam; only reproduce_sources supplies pinned payloads."""
    tick()
    if type(payloads) is not dict or set(payloads) != set(definition.fixed):
        raise ValueError(f'{definition.prefix}_PAYLOAD_SET')
    for key, (_, limit, _) in definition.fixed.items():
        if type(payloads[key]) is not bytes or len(payloads[key]) > limit:
            raise ValueError(f'{definition.prefix}_PAYLOAD_SIZE_OR_TYPE')
    native = payloads['native_log'];lines = native.splitlines(keepends=True)
    if len(lines) != 10506 or b'\r' in native:
        raise ValueError(f'{definition.prefix}_NATIVE_LINES')
    offsets = [0]
    for line in lines:tick();offsets.append(offsets[-1] + len(line))
    provenance = strict_json(payloads['native_byte_proof'], tick)
    original = provenance['user_uploaded_native_source']
    if (provenance['verification_result'] != 'EXACT_SOURCE_BYTES_IDENTICAL'
            or original['native_raw_sha256'] != definition.fixed['native_log'][2]
            or type(original['native_raw_size_bytes']) is not int or original['native_raw_size_bytes'] != len(native)
            or provenance['file_device_authenticity_crypto_proved'] is not False):
        raise ValueError(f'{definition.prefix}_NATIVE_PROVENANCE')
    count_record = strict_json(payloads['owner_count_record'], tick)
    if count_record['count_scope'] != 'PERSONAL_HABU_CAPTURE_MONTHLY_AGGREGATE':
        raise ValueError(f'{definition.prefix}_OWNER_CONTEXT')
    if (count_record['owner_confirmation']['confirmed_count'] != 47
            or count_record['reconciliation']['newly_allocated_august31_day_count'] != 2
            or count_record['reconciliation']['corrected_cumulative_october_20'] != 243):
        raise ValueError(f'{definition.prefix}_OWNER_CONTEXT')
    events = _csv(payloads['captures'], tick, len(definition.records), definition.prefix);links = _csv(payloads['individuals'], tick, len(definition.records), definition.prefix)
    if len({r['event_id'] for r in events}) != len(definition.records) or len({r['individual_id'] for r in links}) != len(definition.records):
        raise ValueError(f'{definition.prefix}_DUPLICATE_RECORD_OR_OCCURRENCE')
    points, qc = _points(payloads['gpx'], tick, consume_point, definition=definition)
    by_sequence = {p['sequence']: p for p in points};crosswalk = []
    for i, expected in enumerate(definition.records):
        record = expected;expected = record.selector
        tick();key, start, end, byte_start, byte_end, slice_sha, clock, place, coordinate_lines = expected
        block = native[byte_start:byte_end]
        if (offsets[start - 1] != byte_start or offsets[end] != byte_end
                or _hash(block, tick) != slice_sha):raise ValueError(f'{definition.prefix}_NATIVE_SELECTOR')
        text = block.decode('utf-8').splitlines();event, link = events[i], links[i]
        if (text[1:3] != ['捕獲', record.note]
                or any(v in '\n'.join(text) for v in ('他人', '第三者', '伝聞', '代理'))):
            raise ValueError(f'{definition.prefix}_SPECIES_OR_OWNER_STATEMENT')
        if definition.strict_attributes and text[3:6] != [record.behavior, record.microhabitat, record.surface]:
            raise ValueError(f'{definition.prefix}_SOURCE_ATTRIBUTES')
        stamp = datetime.strptime(text[0], '%Y/%m/%d %H:%M').replace(tzinfo=JST)
        if (stamp != _time(clock) or event['event_id'] != key or event['event_type'] != 'capture'
                or event['event_count'] != '1' or event['operational_date'] != definition.night
                or _time(event['event_time_local']) != stamp
                or (stamp - timedelta(hours=7)).date().isoformat() != definition.night):
            raise ValueError(f'{definition.prefix}_EVENT_BINDING')
        if (event['source_note'] != text[2] or event['surface'] != text[5] or event['event_place'] != place):
            raise ValueError(f'{definition.prefix}_EVENT_ATTRIBUTES')
        coordinates = [lines[n - 1].decode('utf-8').removesuffix('\n') for n in coordinate_lines]
        for column, original_value, low, high in zip(('latitude', 'longitude'), coordinates, (0, 126), (84, 132)):
            if (event[column] != original_value
                    or _coordinate(event[column], low, high) != _coordinate(original_value, low, high)):
                raise ValueError(f'{definition.prefix}_ORIGINAL_COORDINATE')
        if (link['individual_id'] != key + '-OCC01' or link['event_id'] != key or link['individual_index'] != '1'
                or link['operational_date'] != definition.night or _time(link['event_time_local']) != stamp
                or link['event_place'] != place or link['size_note'] != record.size_note or link['sex'] != record.sex
                or link['behavior'] != text[3] or link['microhabitat'] != text[4]):
            raise ValueError(f'{definition.prefix}_OCCURRENCE_BINDING')
        tick();match = match_capture_to_points(dict(event, datetime_jst=stamp.isoformat()), points);tick()
        point = by_sequence[match['matched_sequence']];pi = point['trackpoint_index']
        neighbors = [(point['time_utc'] - points[pi - 1]['time_utc']).total_seconds() if pi else None,
                     (points[pi + 1]['time_utc'] - point['time_utc']).total_seconds() if pi + 1 < len(points) else None]
        if (match['match_status'] != 'matched_100m_10min' or point['exclude_point'] or point['segment_break_before']
                or point['hdop'] > 10 or any(g is None or not 0 < g <= 30 for g in neighbors)):
            raise ValueError(f'{definition.prefix}_ACTUAL_GPX_POINT')
        crosswalk.append(dict(event_id=key, individual_occurrence_id=link['individual_id'], csv_row=i + 2,
            individual_csv_row=i + 2, source_line_start=start, source_line_end=end,
            source_byte_start=byte_start, source_byte_end_exclusive=byte_end, source_slice_sha256=slice_sha,
            source_time_jst=stamp.isoformat(), count=1, count_basis='SINGULAR_STATEMENT_AS_ONE_RECORDED_OCCURRENCE',
            coordinate_lines=list(coordinate_lines), coordinate_binding='EXACT_ORIGINAL_DECIMAL_EQUAL',
            gpx_sequence=point['sequence'], gpx_trackpoint_index=pi, gpx_time_utc=point['time_utc'].isoformat(),
            distance_m=round(match['distance_m'], 3), time_delta_seconds=round(match['time_delta_s'], 3),
            hdop=point['hdop'], neighboring_gap_seconds=neighbors))
    tick()
    return dict(event_count=len(definition.records), individual_occurrence_count=len(definition.records), permanent_biological_identity_verified=False,
                crosswalk=crosswalk, gpx_qc=qc, **{key: False for key in FORBIDDEN_AUTHORITY})



def reproduce_sources(refs, *, definition, read_ref, tick, consume_point):
    """Reproduce fixed bytes; caller owns all actual I/O, resources and finalization."""
    tick()
    if type(refs) is not dict or set(refs) != set(definition.fixed):raise ValueError(f'{definition.prefix}_REFERENCE_SET')
    seen = [];payloads = {}
    def read(key, ref):
        tick();path, size, sha = definition.fixed[key]
        if (type(ref) is not dict or set(ref) != {'path', 'sha256', 'size_bytes'}
                or ref['path'] != path or ref['sha256'] != sha
                or type(ref['size_bytes']) is not int or ref['size_bytes'] != size):
            raise ValueError(f'{definition.prefix}_FIXED_REFERENCE')
        raw = read_ref(ref);tick()
        if type(raw) is not bytes or len(raw) != size or _hash(raw, tick) != sha:
            raise ValueError(f'{definition.prefix}_REFERENCE_BYTES')
        return raw
    for key in definition.fixed:
        payloads[key] = read(key, refs[key]);seen.append((key, refs[key]))
    proof = _cross_bind(payloads, definition=definition, tick=tick, consume_point=consume_point)
    for key, ref in seen:read(key, ref)
    tick();return proof
