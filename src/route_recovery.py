"""Pure, bounded recovery of source GPS facts and research-only route support.

Points always refer to original measurements. Straight lines between short,
plausible brackets are explicitly interpolated hypotheses, never inserted into
the measured point array. No search confirmation, scientific label, or issuer
authority is granted by this module.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import math
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from src.gpx_audit import mark_point_anomalies, utm52n
from src.osm_road import segment_grid_contributions_xy
from src.terrain_road_features import point_segment_distance_and_bearing

MAX_BYTES = 20_000_000
MAX_POINTS = 100_000
MAX_NODES = 500_000
MAX_DEPTH = 32
MAX_OPERATIONS = 2_000_000
MAX_WINDOWS = 200_000
JST = timezone(timedelta(hours=9))
HEX = re.compile(r'[0-9a-f]{64}\Z')
DEFAULT_POLICY = dict(max_interval_seconds=30.0, max_speed_mps=60.0,
                      max_hdop=10.0, max_accuracy_m=100.0,
                      road_match_radius_m=50.0, road_ambiguity_margin_m=10.0)


def _fail(code):
    raise ValueError(code)


def _sha(value):
    if not isinstance(value, str) or not HEX.fullmatch(value):
        _fail('INVALID_SOURCE_SHA256')
    return value


def _time(value):
    if not isinstance(value, str):
        _fail('INVALID_AWARE_TIME')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        _fail('INVALID_AWARE_TIME')
    if result.tzinfo is None or result.utcoffset() is None:
        _fail('INVALID_AWARE_TIME')
    return result.astimezone(timezone.utc)


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        _fail('INVALID_FINITE_NUMBER')
    try:
        result = float(value)
    except ValueError:
        _fail('INVALID_FINITE_NUMBER')
    if not math.isfinite(result):
        _fail('INVALID_FINITE_NUMBER')
    return result


def _position(lat, lon):
    lat, lon = _number(lat), _number(lon)
    # This explicit projection domain is a technical UTM52N support bound.
    if not (0 <= lat < 84 and 126 <= lon <= 132):
        _fail('OUTSIDE_UTM52N_SUPPORT')
    return lat, lon


def _night(t):
    return (t.astimezone(JST) - timedelta(hours=7)).date().isoformat()


def _bucket(t):
    local = t.astimezone(JST)
    return local.replace(minute=(local.minute // 10) * 10, second=0, microsecond=0)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail('DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def _json(raw):
    def bad_constant(_):
        _fail('NONFINITE_JSON')
    try:
        value = json.loads(raw, object_pairs_hook=_unique, parse_constant=bad_constant)
    except (json.JSONDecodeError, UnicodeError, RecursionError):
        _fail('INVALID_ROUTE_JSON')
    stack, nodes = [(value, 1)], 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if depth > MAX_DEPTH or nodes > MAX_NODES:
            _fail('ROUTE_JSON_CAPACITY')
        if isinstance(item, dict):
            stack.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            stack.extend((v, depth + 1) for v in item)
    return value


def _point(raw, index, track, segment, source):
    reasons = []
    p = dict(point_id=source + ':' + str(index), source_sha256=source,
             sequence=index, track_index=track, segment_index=segment,
             origin='GPS_MEASURED', time_raw=raw.get('time'), time_utc=None,
             latitude=None, longitude=None, accuracy_m=None, hdop=None,
             speed_mps=None, course_deg=None, elevation_m=None,
             exclude_point=False, qc_reasons=reasons, raw_fields=copy.deepcopy(raw))
    try:
        t = _time(raw.get('time'))
        p.update(time_utc=t.isoformat(), operational_night=_night(t))
    except ValueError:
        reasons.append('INVALID_OR_MISSING_AWARE_TIME')
        p['operational_night'] = None
    try:
        p['latitude'], p['longitude'] = _position(raw.get('lat'), raw.get('lon'))
    except ValueError:
        reasons.append('INVALID_COORDINATE')
    for source_key, key in [('accuracy', 'accuracy_m'), ('hdop', 'hdop'),
                            ('speed', 'speed_mps'), ('course', 'course_deg'),
                            ('altitude', 'elevation_m')]:
        value = raw.get(source_key)
        if value is None or value == '':
            continue
        try:
            value = _number(value)
            if key != 'elevation_m' and value < 0:
                _fail('NEGATIVE_QUALITY_VALUE')
            if key == 'course_deg' and value >= 360:
                _fail('INVALID_COURSE')
            p[key] = value
        except ValueError:
            reasons.append('INVALID_' + key.upper())
    p['exclude_point'] = bool(reasons)
    return p


def _gpx_rows(raw):
    if b'<!doctype' in raw.lower() or b'<!entity' in raw.lower():
        _fail('GPX_ENTITY_FORBIDDEN')
    rows, stack, track, segment, nodes = [], [], -1, -1, 0
    try:
        for event, el in ET.iterparse(io.BytesIO(raw), events=('start', 'end')):
            tag = el.tag.rsplit('}', 1)[-1]
            if event == 'start':
                stack.append(tag)
                nodes += 1
                if len(stack) > MAX_DEPTH or nodes > MAX_NODES:
                    _fail('GPX_XML_CAPACITY')
                if len(stack) == 1 and tag != 'gpx':
                    _fail('INVALID_GPX_ROOT')
                if tag == 'trk':
                    if stack != ['gpx', 'trk']:
                        _fail('INVALID_GPX_TRACK_STRUCTURE')
                    track += 1
                if tag == 'trkseg':
                    if stack != ['gpx', 'trk', 'trkseg']:
                        _fail('INVALID_GPX_SEGMENT_STRUCTURE')
                    segment += 1
                if tag == 'trkpt' and stack != ['gpx', 'trk', 'trkseg', 'trkpt']:
                    _fail('INVALID_GPX_POINT_STRUCTURE')
            else:
                if tag == 'trkpt':
                    if len(rows) >= MAX_POINTS:
                        _fail('ROUTE_POINT_CAPACITY')
                    values = defaultdict(list)
                    for child in el.iter():
                        name = child.tag.rsplit('}', 1)[-1]
                        if child is not el and child.text and child.text.strip():
                            values[name].append(child.text.strip())
                    row = dict(lat=el.attrib.get('lat'), lon=el.attrib.get('lon'))
                    for name, key in [('time', 'time'), ('hdop', 'hdop'), ('speed', 'speed'),
                                      ('course', 'course'), ('ele', 'altitude'),
                                      ('accuracyMeters', 'accuracy')]:
                        if len(values[name]) > 1:
                            _fail('AMBIGUOUS_GPX_POINT_FIELD')
                        if values[name]:
                            row[key] = values[name][0]
                    rows.append((row, track, segment))
                    el.clear()
                stack.pop()
    except ET.ParseError:
        _fail('INVALID_GPX_XML')
    if not rows:
        _fail('GPX_HAS_NO_MEASURED_POINTS')
    return rows, []


def _json_rows(raw, format):
    gaps = []
    if format == 'field-session':
        value = _json(raw)
        if (not isinstance(value, dict) or value.get('schema_version') != 'habu-field-session-v1'
                or not isinstance(value.get('points'), list)
                or not isinstance(value.get('events'), list)
                or not isinstance(value.get('gaps'), list)
                or value.get('status') not in ('active', 'stopped')):
            _fail('INVALID_FIELD_SESSION')
        _time(value.get('startedAt'))
        if value.get('endedAt') is not None:
            _time(value['endedAt'])
        values = value['points']
        for gap in value['gaps']:
            if not isinstance(gap, dict):
                _fail('INVALID_RECORDER_GAP')
            gaps.append(_time(gap.get('time')).isoformat())
    else:
        lines = raw.splitlines()
        if len(lines) > MAX_POINTS:
            _fail('ROUTE_POINT_CAPACITY')
        values = [_json(line) for line in lines if line.strip()]
    if not values or len(values) > MAX_POINTS:
        _fail('ROUTE_POINT_CAPACITY')
    rows, previous, segment = [], object(), -1
    allowed = {'time', 'lat', 'lon', 'accuracy', 'altitude', 'speed', 'course', 'heading', 'segment', 'sequence'}
    for value in values:
        if not isinstance(value, dict) or not set(value) <= allowed:
            _fail('UNSUPPORTED_RECORDER_POINT')
        label = value.get('segment', 0)
        if not isinstance(label, (str, int)) or isinstance(label, bool):
            _fail('INVALID_RECORDER_SEGMENT')
        if label != previous:
            segment += 1
        previous = label
        row = dict(value)
        if 'heading' in row:
            if 'course' in row and row['course'] != row['heading']:
                _fail('CONFLICTING_RECORDER_HEADING')
            row['course'] = row['heading']
        rows.append((row, 0, segment))
    return rows, gaps


def parse_route(raw: bytes, format: str = 'gpx', source_sha256: str | None = None) -> dict:
    """Parse exact source bytes without file/network access or source reordering."""
    _sha(source_sha256)
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES:
        _fail('ROUTE_BYTE_CAPACITY')
    if hashlib.sha256(raw).hexdigest() != source_sha256:
        _fail('ROUTE_SOURCE_SHA_MISMATCH')
    if format not in ('gpx', 'field-session', 'jsonl'):
        _fail('UNSUPPORTED_ROUTE_FORMAT')
    rows, gaps = _gpx_rows(raw) if format == 'gpx' else _json_rows(raw, format)
    points = [_point(row, i, track, segment, source_sha256)
              for i, (row, track, segment) in enumerate(rows)]
    segments = []
    for p in points:
        if not segments or segments[-1]['segment_index'] != p['segment_index']:
            segments.append(dict(track_index=p['track_index'], segment_index=p['segment_index'], point_ids=[]))
        segments[-1]['point_ids'].append(p['point_id'])
    return dict(schema_version='habu-source-route-v1', source_sha256=source_sha256,
                format=format, points=points, segments=segments, recorder_gaps=gaps,
                qc=dict(source_points=len(points), quarantined_points=sum(p['exclude_point'] for p in points)))


def _quality(points, policy):
    clocks = {}
    for p in points:
        if p['time_utc'] is None:
            continue
        t = _time(p['time_utc'])
        key = (p['track_index'], p['segment_index'])
        if key in clocks and t <= clocks[key]:
            p['qc_reasons'].append('NON_MONOTONIC_TIME')
        else:
            clocks[key] = t
        if p['hdop'] is not None and p['hdop'] > policy['max_hdop']:
            p['qc_reasons'].append('HDOP_OVER_POLICY_LIMIT')
        if p['accuracy_m'] is not None and p['accuracy_m'] > policy['max_accuracy_m']:
            p['qc_reasons'].append('ACCURACY_OVER_POLICY_LIMIT')
        p['exclude_point'] = bool(p['qc_reasons'])
    # Run existing spike/rapid-jump QC only within source-contiguous valid runs.
    runs, current = [], []
    for p in points:
        if p['exclude_point'] or (current and
                (p['track_index'], p['segment_index']) != (current[-1]['track_index'], current[-1]['segment_index'])):
            if current:
                runs.append(current)
            current = []
        if not p['exclude_point']:
            current.append(p)
    if current:
        runs.append(current)
    for run in runs:
        legacy = [dict(p, time_utc=_time(p['time_utc'])) for p in run]
        for p, marked in zip(run, mark_point_anomalies(legacy)):
            p['segment_break_before'] = marked['segment_break_before']
            p['qc_segment_break_reason'] = marked['anomaly_reason'].upper()
            if marked['exclude_point']:
                p['exclude_point'] = True
                p['qc_reasons'].append(marked['anomaly_reason'].upper())
    for p in points:
        if not p['exclude_point']:
            p['utm_x'], p['utm_y'] = utm52n(p['latitude'], p['longitude'])
        p['spatial_uncertainty_m'] = p['accuracy_m']
        p['quality_support'] = 'REPORTED_ACCURACY' if p['accuracy_m'] is not None else 'HDOP_ONLY' if p['hdop'] is not None else 'ACCURACY_UNKNOWN'


def _pauses(pauses, start, end):
    intervals = []
    if not isinstance(pauses, (list, tuple)) or len(pauses) > 1000:
        _fail('PAUSE_CAPACITY')
    for pause in pauses:
        if (not isinstance(pause, dict) or pause.get('owner_confirmed') is not True
                or pause.get('classification') != 'INTENTIONAL_PAUSE'):
            _fail('UNCONFIRMED_INTENTIONAL_PAUSE')
        _sha(pause.get('source_sha256'))
        a, b = _time(pause.get('start')), _time(pause.get('end'))
        if b <= a:
            _fail('INVALID_PAUSE_INTERVAL')
        a, b = max(a, start), min(b, end)
        if a < b:
            intervals.append((a, b))
    merged = []
    for a, b in sorted(intervals):
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def _overlap(a, b, intervals):
    return math.fsum(max(0, (min(b, y) - max(a, x)).total_seconds()) for x, y in intervals)


def _road_index(roads, policy):
    if roads is None:
        return None
    if not isinstance(roads, list) or len(roads) > 100_000:
        _fail('ROAD_CAPACITY')
    index, seen, used, vertices = defaultdict(list), set(), 0, 0
    radius = policy['road_match_radius_m']
    for road in roads:
        if (not isinstance(road, dict) or not isinstance(road.get('road_id'), str)
                or not road['road_id'] or road['road_id'] in seen):
            _fail('INVALID_OR_DUPLICATE_ROAD')
        seen.add(road['road_id'])
        _sha(road.get('source_sha256'))
        geometry = road.get('geometry')
        if not isinstance(geometry, dict) or geometry.get('type') != 'LineString':
            _fail('INVALID_ROAD_GEOMETRY')
        coordinates = geometry.get('coordinates')
        if not isinstance(coordinates, list) or not 2 <= len(coordinates) <= MAX_POINTS:
            _fail('ROAD_VERTEX_CAPACITY')
        vertices += len(coordinates)
        if vertices > MAX_NODES:
            _fail('ROAD_VERTEX_CAPACITY')
        xy = []
        for coordinate in coordinates:
            if not isinstance(coordinate, (list, tuple)) or len(coordinate) != 2:
                _fail('INVALID_ROAD_COORDINATE')
            lat, lon = _position(coordinate[1], coordinate[0])
            xy.append(utm52n(lat, lon))
        for a, b in zip(xy, xy[1:]):
            entry = (road['road_id'], road['source_sha256'], *a, *b)
            nx = range(math.floor((min(a[0], b[0]) - radius) / 100), math.floor((max(a[0], b[0]) + radius) / 100) + 1)
            ny = range(math.floor((min(a[1], b[1]) - radius) / 100), math.floor((max(a[1], b[1]) + radius) / 100) + 1)
            if len(nx) * len(ny) + used > MAX_OPERATIONS:
                _fail('ROAD_INDEX_CAPACITY')
            for x in nx:
                for y in ny:
                    index[(x, y)].append(entry)
                    used += 1
    return index


def _match_road(p, index, policy, budget):
    if index is None:
        return dict(status='NOT_SUPPLIED', candidates=[])
    found = {}
    for road_id, source, ax, ay, bx, by in index.get((math.floor(p['utm_x'] / 100), math.floor(p['utm_y'] / 100)), []):
        budget[0] += 1
        if budget[0] > MAX_OPERATIONS:
            _fail('ROAD_MATCH_CAPACITY')
        distance, bearing = point_segment_distance_and_bearing(p['utm_x'], p['utm_y'], ax, ay, bx, by)
        if distance <= policy['road_match_radius_m'] and (road_id not in found or distance < found[road_id]['distance_m']):
            found[road_id] = dict(road_id=road_id, source_sha256=source, distance_m=distance,
                                  orientation_deg=bearing, support='AUXILIARY_PUBLIC_ROAD_REFERENCE')
    candidates = sorted(found.values(), key=lambda r: (r['distance_m'], r['road_id']))
    if not candidates:
        return dict(status='UNMATCHED', candidates=[])
    margin = max(policy['road_ambiguity_margin_m'], p['accuracy_m'] or 0)
    ambiguous = len(candidates) > 1 and candidates[1]['distance_m'] - candidates[0]['distance_m'] <= margin
    return dict(status='AMBIGUOUS' if ambiguous else 'MATCHED', candidates=candidates,
                official_access_verified=False)


def recover_route(parsed: dict, *, roads=None, activity=None, pauses=(), policy=None) -> dict:
    """Recover bounded route/time proxies without rewriting or qualifying evidence."""
    if (not isinstance(parsed, dict) or parsed.get('schema_version') != 'habu-source-route-v1'
            or not isinstance(parsed.get('points'), list) or not 0 < len(parsed['points']) <= MAX_POINTS):
        _fail('INVALID_PARSED_ROUTE')
    _sha(parsed.get('source_sha256'))
    for i, p in enumerate(parsed['points']):
        if (not isinstance(p, dict) or p.get('origin') != 'GPS_MEASURED'
                or p.get('source_sha256') != parsed['source_sha256']
                or type(p.get('sequence')) is not int or p['sequence'] != i
                or p.get('point_id') != parsed['source_sha256'] + ':' + str(i)
                or type(p.get('exclude_point')) is not bool
                or not isinstance(p.get('qc_reasons'), list)
                or any(not isinstance(x, str) for x in p['qc_reasons'])
                or any(type(p.get(k)) is not int or p[k] < 0 for k in ('track_index', 'segment_index'))):
            _fail('INVALID_MEASURED_POINT_LINEAGE')
    policy = dict(DEFAULT_POLICY, **(policy or {}))
    if set(policy) != set(DEFAULT_POLICY):
        _fail('UNKNOWN_ROUTE_POLICY')
    policy = {k: _number(v) for k, v in policy.items()}
    upper = dict(max_interval_seconds=30, max_speed_mps=100, max_hdop=100,
                 max_accuracy_m=1000, road_match_radius_m=1000, road_ambiguity_margin_m=1000)
    if any(v <= 0 or v > upper[k] for k, v in policy.items()):
        _fail('INVALID_ROUTE_POLICY')
    context, activity_scope, context_scope = False, None, 'NOT_SUPPLIED'
    if activity is not None:
        if not isinstance(activity, dict) or type(activity.get('owner_search_context')) is not bool:
            _fail('INVALID_ACTIVITY_CONTEXT')
        _sha(activity.get('source_sha256'))
        context = activity['owner_search_context']
        has_start, has_end = 'scope_start' in activity, 'scope_end' in activity
        if has_start != has_end:
            _fail('INCOMPLETE_ACTIVITY_SCOPE')
        if has_start:
            activity_scope = (_time(activity['scope_start']), _time(activity['scope_end']))
            if activity_scope[1] <= activity_scope[0]:
                _fail('INVALID_ACTIVITY_SCOPE')
            context_scope = 'SOURCE_BOUND_TIME_SCOPE'
        else:
            context_scope = 'EXPLICIT_WHOLE_SOURCE_CONTEXT'
    points = copy.deepcopy(parsed['points'])
    _quality(points, policy)
    valid = [p for p in points if not p['exclude_point']]
    if not valid:
        _fail('NO_USABLE_MEASURED_POINTS')
    start = min(_time(p['time_utc']) for p in valid)
    end = max(_time(p['time_utc']) for p in valid)
    activity_scope = activity_scope or (start, end)
    confirmed_pauses = _pauses(pauses, start, end)
    recorded_gaps = [_time(t) for t in parsed.get('recorder_gaps', [])]
    index, budget = _road_index(roads, policy), [0]
    for p in valid:
        p['road_match'] = _match_road(p, index, policy, budget)
    segments, gaps, pieces, directions = [], [], [], {}
    for a, b in zip(points, points[1:]):
        if a['time_utc'] is None or b['time_utc'] is None:
            gaps.append(dict(reason='QUARANTINED_POINT', from_point_id=a['point_id'], to_point_id=b['point_id'],
                             duration_seconds=None, route_hypothesis_produced=False))
            continue
        t0, t1 = _time(a['time_utc']), _time(b['time_utc'])
        seconds, reason = (t1 - t0).total_seconds(), None
        if a['exclude_point'] or b['exclude_point']:
            reason = 'QUARANTINED_POINT'
        elif (a['track_index'], a['segment_index']) != (b['track_index'], b['segment_index']):
            reason = 'SOURCE_SEGMENT_BOUNDARY'
        elif seconds <= 0:
            reason = 'NON_MONOTONIC_TIME'
        elif seconds > policy['max_interval_seconds']:
            reason = 'TIME_GAP'
        elif b.get('qc_segment_break_reason') == 'RAPID_JUMP':
            reason = 'RAPID_JUMP'
        elif any(t0 <= t <= t1 for t in recorded_gaps):
            reason = 'RECORDER_GAP'
        distance = math.hypot(b['utm_x'] - a['utm_x'], b['utm_y'] - a['utm_y']) if not (a['exclude_point'] or b['exclude_point']) else None
        if reason is None and distance / seconds > policy['max_speed_mps']:
            reason = 'IMPLAUSIBLE_SPEED'
        if reason is None and (a['road_match']['status'] == 'AMBIGUOUS' or b['road_match']['status'] == 'AMBIGUOUS'):
            reason = 'ROAD_MATCH_AMBIGUITY'
        if (reason is None and a['road_match']['status'] == b['road_match']['status'] == 'MATCHED'
                and a['road_match']['candidates'][0]['road_id'] != b['road_match']['candidates'][0]['road_id']):
            reason = 'ROAD_PATH_NOT_ESTABLISHED'
        if reason:
            gaps.append(dict(reason=reason, from_point_id=a['point_id'], to_point_id=b['point_id'],
                             start=t0.isoformat(), end=t1.isoformat(), duration_seconds=seconds if seconds > 0 else None,
                             signed_source_elapsed_seconds=seconds,
                             intentional_pause_overlap_seconds=_overlap(t0, t1, confirmed_pauses) if seconds > 0 else 0,
                             gps_hardware_failure='NOT_ESTABLISHED', route_hypothesis_produced=False))
            continue
        sid = parsed['source_sha256'] + ':interval:' + str(a['sequence'])
        segment = dict(segment_id=sid, from_point_id=a['point_id'], to_point_id=b['point_id'],
                       start=t0.isoformat(), end=t1.isoformat(), duration_seconds=seconds,
                       displacement_m=distance, speed_mps=distance / seconds,
                       origin='GPS_INTERPOLATED', measured_endpoints=True,
                       geometry_support='STRAIGHT_ENDPOINT_BRACKET_NOT_CONTINUOUS_MEASUREMENT',
                       continuous_search_confirmed=False)
        segments.append(segment)
        if distance:
            directions[sid] = math.atan2(b['utm_y'] - a['utm_y'], b['utm_x'] - a['utm_x'])
        cuts = {0.0, 1.0}
        if distance:
            contributions = segment_grid_contributions_xy(a['utm_x'], a['utm_y'], b['utm_x'], b['utm_y'])
            at = 0.0
            for contribution in contributions[:-1]:
                at += contribution['length_m'] / distance
                cuts.add(at)
        boundary = _bucket(t0) + timedelta(minutes=10)
        while boundary < t1:
            cuts.add((boundary - t0).total_seconds() / seconds)
            boundary += timedelta(minutes=10)
        for x, y in confirmed_pauses:
            for boundary in (x, y):
                if t0 < boundary < t1:
                    cuts.add((boundary - t0).total_seconds() / seconds)
        ordered = []
        for cut in sorted(cuts):
            if not ordered or cut - ordered[-1] > 1e-8:
                ordered.append(cut)
        for f0, f1 in zip(ordered, ordered[1:]):
            u, v = t0 + timedelta(seconds=seconds * f0), t0 + timedelta(seconds=seconds * f1)
            middle = (f0 + f1) / 2
            x = a['utm_x'] + (b['utm_x'] - a['utm_x']) * middle
            y = a['utm_y'] + (b['utm_y'] - a['utm_y']) * middle
            pieces.append(dict(cell_x=math.floor(x / 100), cell_y=math.floor(y / 100),
                               start=u, end=v, interval_id=sid,
                               operational_night=_night(u + (v - u) / 2),
                               window_start_jst=_bucket(u + (v - u) / 2).isoformat(),
                               distance_m=distance * (f1 - f0)))
            if len(pieces) > MAX_OPERATIONS:
                _fail('ROUTE_PARTITION_CAPACITY')
    turns = set()
    for a, b in zip(segments, segments[1:]):
        if (a['to_point_id'] == b['from_point_id'] and a['segment_id'] in directions
                and b['segment_id'] in directions):
            angle = abs((directions[b['segment_id']] - directions[a['segment_id']] + math.pi) % (2 * math.pi) - math.pi)
            if angle >= math.radians(135) and activity_scope[0] <= _time(b['start']) < activity_scope[1]:
                turns.update((a['segment_id'], b['segment_id']))
    windows = {}
    def window(key):
        if key not in windows:
            if len(windows) >= MAX_WINDOWS:
                _fail('ROUTE_WINDOW_CAPACITY')
            x, y, bucket = key
            windows[key] = dict(cell_x=x, cell_y=y, window_start_jst=bucket,
                                operational_night=_night(_time(bucket)), point_count=0,
                                interpolated_seconds=0.0, pause_overlap_seconds=0.0,
                                movement_effort_proxy_seconds=0.0, movement_distance_m=0.0,
                                measured_continuous_search_seconds=None, visit_count=0, visit_ids=[],
                                interval_ids=[], point_ids=[], origins=[], activity_class='UNRESOLVED_ACTIVITY',
                                activity_reasons=[], formal_negative_eligible=False,
                                source_sha256=parsed['source_sha256'], _pieces=[])
        return windows[key]
    for p in valid:
        t = _time(p['time_utc'])
        row = window((math.floor(p['utm_x'] / 100), math.floor(p['utm_y'] / 100), _bucket(t).isoformat()))
        row['point_count'] += 1
        row['point_ids'].append(p['point_id'])
    for piece in pieces:
        window((piece['cell_x'], piece['cell_y'], piece['window_start_jst']))['_pieces'].append(piece)
    for key, row in windows.items():
        intervals = sorted(row.pop('_pieces'), key=lambda p: (p['start'], p['end'], p['interval_id']))
        previous_end = None
        for piece in intervals:
            duration = (piece['end'] - piece['start']).total_seconds()
            pause_seconds = _overlap(piece['start'], piece['end'], confirmed_pauses)
            if previous_end is None or (piece['start'] - previous_end).total_seconds() > 1e-5:
                row['visit_count'] += 1
                row['visit_ids'].append(':'.join(map(str, key)) + ':visit:' + str(row['visit_count']))
            previous_end = max(previous_end, piece['end']) if previous_end else piece['end']
            row['interpolated_seconds'] += duration
            row['pause_overlap_seconds'] += pause_seconds
            row['movement_effort_proxy_seconds'] += duration - pause_seconds
            row['movement_distance_m'] += piece['distance_m']
            if piece['interval_id'] not in row['interval_ids']:
                row['interval_ids'].append(piece['interval_id'])
        scoped, previous_end, scoped_visits = [], None, 0
        for piece in intervals:
            a, b = max(piece['start'], activity_scope[0]), min(piece['end'], activity_scope[1])
            if a >= b:
                continue
            if previous_end is None or (a - previous_end).total_seconds() > 1e-5:
                scoped_visits += 1
            previous_end = max(previous_end, b) if previous_end else b
            scoped.append((a, b, piece['interval_id']))
        row['activity_scope_covered_proxy_seconds'] = math.fsum(
            (b - a).total_seconds() - _overlap(a, b, confirmed_pauses) for a, b, _ in scoped) if context else 0
        inferred = math.fsum((b - a).total_seconds() - _overlap(a, b, confirmed_pauses)
                             for a, b, sid in scoped if scoped_visits > 1 or sid in turns) if context else 0
        row['search_inferred_proxy_seconds'] = inferred
        if row['interpolated_seconds'] and row['pause_overlap_seconds'] >= row['interpolated_seconds'] - 1e-5:
            row['activity_class'] = 'INTENTIONAL_PAUSE'
            row['activity_reasons'] = ['OWNER_CONFIRMED_PAUSE_OVERLAP']
        elif inferred > 0 and math.isclose(inferred, row['movement_effort_proxy_seconds'], abs_tol=1e-5):
            row['activity_class'] = 'SEARCH_INFERRED'
            row['activity_reasons'] = ['SOURCE_BOUND_OWNER_SEARCH_CONTEXT', context_scope]
            if scoped_visits > 1:
                row['activity_reasons'].append('REPEATED_TRAVERSAL')
            if any(i in turns for i in row['interval_ids']):
                row['activity_reasons'].append('TURN_BACK_PATTERN')
        elif inferred > 0:
            row['activity_reasons'] = ['PARTIAL_INFERRED_ACTIVITY_SCOPE', context_scope]
        row['origins'] = (['GPS_MEASURED'] if row['point_count'] else []) + (['GPS_INTERPOLATED'] if row['interpolated_seconds'] else [])
        row['bracketed_seconds'] = row['interpolated_seconds']
        row['activity_rule'] = 'owner_context_and_repeat_or_135deg_turnback_v1_not_calibrated'
    elapsed = (end - start).total_seconds()
    pause_seconds = _overlap(start, end, confirmed_pauses)
    return dict(schema_version='habu-recovered-route-research-v1', source_sha256=parsed['source_sha256'],
                activity_source_sha256=activity['source_sha256'] if activity is not None else None,
                pause_evidence=copy.deepcopy(list(pauses)),
                scope='POST_SEARCH_RESEARCH_ONLY', points=points, segments=segments, gaps=gaps,
                windows=sorted(windows.values(), key=lambda r: (r['window_start_jst'], r['cell_x'], r['cell_y'])),
                policy=policy, summary=dict(source_points=len(points), accepted_points=len(valid),
                    quarantined_points=len(points) - len(valid),
                    qc_reasons=dict(Counter(reason for p in points for reason in p['qc_reasons'])),
                    source_segments=len(parsed.get('segments', [])), recovered_intervals=len(segments),
                    gap_count=len(gaps), windows=len(windows),
                    session_elapsed_seconds=elapsed, intentional_pause_seconds=pause_seconds,
                    elapsed_minus_pause_proxy_seconds=elapsed - pause_seconds,
                    interpolated_seconds=math.fsum(s['duration_seconds'] for s in segments),
                    measured_continuous_search_seconds=None, formal_positive_count=0, formal_negative_count=0,
                    training_eligibility='NOT_ASSESSED', official_prediction_authorized=False,
                    production_authorized=False, route_hypotheses_produced=False,
                    road_matching_status='NOT_PRODUCED_NO_ROAD_SOURCE' if roads is None else 'AUXILIARY_REFERENCE_MATCHES_ONLY',
                    road_distance_checks=budget[0],
                    activity_context_scope=context_scope,
                    no_capture_research_windows_are_not_negatives=True))
