#!/usr/bin/env python3
"""Recover source-bound route evidence into an append-only PRIVATE sidecar.

No candidate database/model is generated or updated. No P0, formal label,
ex-ante feature, scientific qualification, or Champion authority is conferred.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.backfill_historical_environment import assert_private_directory
from scripts.private_pdca_intake import _ReadBudget, _read_bytes, guard_private_path

SCHEMA = 'habu-private-route-source-manifest-v1'
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_SOURCE_BYTES = 256 * 1024 * 1024
MAX_OUTPUT_BYTES = 160 * 1024 * 1024
HEX = re.compile(r'^[0-9a-f]{64}$')
IDENT = re.compile(r'^[A-Za-z0-9_-]{1,100}$')
KINDS = {'gpx', 'field-session', 'jsonl', 'captures', 'roads', 'activity', 'evidence'}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(',', ':'), allow_nan=False)+'\n').encode('utf-8')


def _json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError('DUPLICATE_JSON_KEY')
            value[key] = item
        return value
    def bad_constant(value):
        raise ValueError('NONFINITE_JSON')
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=bad_constant)
    pending = [(value, 0)]
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if depth > 48 or count > 2_000_000:
            raise ValueError('JSON_STRUCTURE_LIMIT')
        if isinstance(item, dict):
            pending.extend((x, depth+1) for x in item.values())
        elif isinstance(item, list):
            pending.extend((x, depth+1) for x in item)
        elif isinstance(item, float) and not math.isfinite(item):
            raise ValueError('NONFINITE_JSON')
    if not isinstance(value, dict):
        raise ValueError('JSON_OBJECT_REQUIRED')
    return value


def _aware(value):
    if not isinstance(value, str):
        raise ValueError('SOURCE_TIME_REQUIRED')
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError('SOURCE_TIMEZONE_REQUIRED')
    return stamp


def _source_path(root, relative):
    if (not isinstance(relative, str) or not relative or '\\' in relative
            or ':' in relative or relative.startswith('/')
            or any(x in ('', '.', '..') for x in relative.split('/'))):
        raise ValueError('INVALID_SOURCE_PATH')
    path = root / relative
    guard_private_path(root, path)
    return path


def _load_sources(root, manifest, budget, *, reading_started_at):
    sources = manifest.get('sources')
    if not isinstance(sources, list) or not 1 <= len(sources) <= 32:
        raise ValueError('SOURCE_COUNT_LIMIT')
    records, contents, hashes, total = {}, {}, set(), 0
    for item in sources:
        budget.check()
        if not isinstance(item, dict):
            raise ValueError('SOURCE_RECORD_REQUIRED')
        ident, kind, checksum = item.get('source_id'), item.get('kind'), item.get('sha256')
        size = item.get('size_bytes')
        if (not isinstance(ident, str) or not IDENT.fullmatch(ident)
                or ident in records or kind not in KINDS
                or not isinstance(checksum, str) or not HEX.fullmatch(checksum)
                or checksum in hashes or type(size) is not int or not 0 < size <= MAX_SOURCE_BYTES):
            raise ValueError('INVALID_OR_DUPLICATED_SOURCE')
        for field in ('source_identity', 'original_timezone', 'correction_revision'):
            if not isinstance(item.get(field), str) or not 0 < len(item[field]) <= 256:
                raise ValueError('SOURCE_PROVENANCE_REQUIRED')
        if _aware(item.get('received_at')) > reading_started_at:
            raise ValueError('SOURCE_RECEIVED_AFTER_READING_STARTED')
        total += size
        if total > MAX_TOTAL_SOURCE_BYTES:
            raise ValueError('TOTAL_SOURCE_BYTE_LIMIT')
        path = _source_path(root, item.get('path'))
        raw = _read_bytes(path, MAX_SOURCE_BYTES, budget)
        if len(raw) != size or _sha(raw) != checksum:
            raise ValueError('SOURCE_BYTES_CHANGED')
        records[ident], contents[ident] = item, raw
        hashes.add(checksum)
    return records, contents


def _optional(manifest, field, kind, records, contents):
    ident = manifest.get(field)
    matches = [x for x in records if records[x]['kind'] == kind]
    if ident is None:
        if matches:
            raise ValueError('UNREFERENCED_OPTIONAL_SOURCE')
        return None
    if not isinstance(ident, str) or ident not in records or records[ident]['kind'] != kind or matches != [ident]:
        raise ValueError('OPTIONAL_SOURCE_NOT_BOUND')
    value = _json(contents[ident])
    original = value.get('original_source_id')
    if original not in records or records[original]['kind'] != 'evidence':
        raise ValueError('ORIGINAL_EVIDENCE_NOT_BOUND')
    return value, records[original]['sha256'], records[ident]['sha256']


def _recover_route(parsed, **kwargs):
    from src.route_recovery import recover_route
    return recover_route(parsed, **kwargs)


def _attach_capture_references(routes, captures, *, source_provided):
    """Descriptive sample-match references; event ledger remains the count unit.

    A GPS sample within +/-10min is not the event's actual ten-minute bin.
    Never re-bin/replace the learning chat's existing 154 capture candidates.
    """
    from src.gpx_audit import utm52n
    from datetime import timedelta
    references, observed_intervals, source_wide_unknown = {}, [], []
    for sidecar in captures['sidecars']:
        if not sidecar['capture_positive_evidence']:
            continue
        event = sidecar['event']
        # A saved/completed capture time has no independently bounded discovery
        # latency. Do not invent a +/-10min bound for research no-capture labels.
        if event['time_semantics'] != 'OBSERVED_AT':
            source_wide_unknown.append(event['event_id'])
        else:
            stamp = _aware(event['recorded_at']).astimezone(timezone.utc)
            uncertainty = event['uncertainty_seconds']
            try:
                lower = stamp-timedelta(seconds=uncertainty)
            except OverflowError:
                lower = datetime.min.replace(tzinfo=timezone.utc)
            try:
                upper = stamp+timedelta(seconds=uncertainty)
            except OverflowError:
                upper = datetime.max.replace(tzinfo=timezone.utc)
            observed_intervals.append((lower, upper, uncertainty == 0, event['event_id']))
        for candidate in sidecar['candidates']:
            references.setdefault(candidate['point_id'], {})[sidecar['event']['event_id']] = {
                'event_id': sidecar['event']['event_id'],
                'match_status': sidecar['match_status'],
                'recorded_at': sidecar['event']['recorded_at'],
                'time_semantics': sidecar['event']['time_semantics'],
                'uncertainty_seconds': sidecar['event']['uncertainty_seconds'],
                'assignment': 'GPS_SAMPLE_MATCH_CANDIDATE_NOT_EVENT_WINDOW_LABEL'}
    observed_intervals.sort()
    captures['source_wide_uncertain_positive_event_ids'] = sorted(set(source_wide_unknown))
    temporal_cache, temporal_operations, link_count = {}, 0, 0
    for route in routes:
        by_window = {}
        for point in route['points']:
            if point.get('exclude_point') or point.get('point_id') not in references:
                continue
            instant = _aware(point['time_utc']).astimezone(timezone(timedelta(hours=9)))
            start = instant.replace(minute=instant.minute//10*10, second=0, microsecond=0)
            x, y = utm52n(point['latitude'], point['longitude'])
            key = math.floor(x/100), math.floor(y/100), start.isoformat()
            by_window.setdefault(key, {}).update(references[point['point_id']])
        for window in route['windows']:
            key = window['cell_x'], window['cell_y'], window['window_start_jst']
            refs = by_window.get(key, {})
            stamp = window['window_start_jst']
            if stamp not in temporal_cache:
                start = _aware(stamp).astimezone(timezone.utc)
                end = start+timedelta(minutes=10)
                ids = []
                for lower, upper, impulse, identity in observed_intervals:
                    temporal_operations += 1
                    if temporal_operations > 2_000_000:
                        raise ValueError('CAPTURE_TEMPORAL_LINK_CAPACITY')
                    if lower >= end:
                        break
                    if (impulse and lower >= start) or (not impulse and upper >= start):
                        ids.append(identity)
                temporal_cache[stamp] = sorted(set(ids))
            unresolved_ids = [identity for identity in temporal_cache[stamp] if identity not in refs]
            link_count += len(unresolved_ids)
            if link_count > 200_000:
                raise ValueError('CAPTURE_WINDOW_LINK_CAPACITY')
            window['positive_event_match_refs'] = [refs[k] for k in sorted(refs)]
            window['unallocated_positive_time_refs'] = unresolved_ids
            window['source_wide_uncertain_positive_events_present'] = bool(source_wide_unknown)
            window['capture_count_semantics'] = 'EVENT_LEDGER_ONCE_DO_NOT_SUM_MATCH_REFERENCES'
            if not source_provided:
                outcome = 'UNKNOWN_CAPTURE_SOURCE_NOT_PROVIDED'
            elif refs:
                outcome = 'HABU_CAPTURE_MEASURED_SAMPLE_MATCH_CANDIDATE'
            elif unresolved_ids or source_wide_unknown:
                outcome = 'UNKNOWN_CAPTURE_LOCATION_OR_TIME'
            elif window.get('activity_class') == 'SEARCH_INFERRED':
                outcome = 'NO_CAPTURE_RECORDED_DURING_INFERRED_SEARCH'
            else:
                outcome = 'NO_CAPTURE_RECORDED_IN_SUPPLIED_SOURCE'
            window['research_capture_outcome'] = outcome
            window['capture_outcome_completeness_verified'] = False
            window['formal_positive_eligible'] = False
            window['formal_negative_eligible'] = False
            window['canonical_capture_tally_delta'] = 0


def _recheck(root, manifest_path, manifest_sha256, records, budget):
    guard_private_path(root, manifest_path)
    if _sha(_read_bytes(manifest_path, MAX_MANIFEST_BYTES, budget)) != manifest_sha256:
        raise ValueError('MANIFEST_CHANGED_DURING_PROCESSING')
    for item in records.values():
        raw = _read_bytes(_source_path(root, item['path']), MAX_SOURCE_BYTES, budget)
        if len(raw) != item['size_bytes'] or _sha(raw) != item['sha256']:
            raise ValueError('SOURCE_CHANGED_DURING_PROCESSING')


def _output_guard(directory):
    assert_private_directory(directory)
    guard_private_path(directory, directory)
    for name in ('route-evidence.json', 'completion-receipt.json'):
        guard_private_path(directory, directory/name)


def _write_new(directory, name, raw, budget):
    budget.check()
    _output_guard(directory)
    path = directory/name
    if path.exists():
        if _read_bytes(path, MAX_OUTPUT_BYTES, budget) != raw:
            raise ValueError('CONFLICTING_PRIVATE_OUTPUT')
    else:
        with path.open('xb') as stream:
            stream.write(raw)
    _output_guard(directory)
    if _read_bytes(path, MAX_OUTPUT_BYTES, budget) != raw:
        raise ValueError('PRIVATE_OUTPUT_READBACK_FAILED')


def _verify_outputs(directory, expected, budget):
    _output_guard(directory)
    for name, raw in expected:
        current = _read_bytes(directory/name, MAX_OUTPUT_BYTES, budget)
        if len(current) != len(raw) or _sha(current) != _sha(raw):
            raise ValueError('PRIVATE_DERIVED_BYTES_CHANGED')


def _runtime_hashes():
    # The active development cycle binds the wider dependency closure. These
    # native-byte digests identify the concrete code used by this private run.
    paths = ('scripts/recover_private_route_evidence.py', 'src/route_recovery.py',
             'src/capture_route_evidence.py', 'src/gpx_audit.py',
             'src/terrain_road_features.py', 'src/osm_road.py', 'scripts/private_pdca_intake.py',
             'scripts/backfill_historical_environment.py', 'requirements-analysis.txt')
    return {name: _sha((ROOT/name).read_bytes()) for name in paths}


def _receipt(base, output, budget, started_at):
    path = output/'completion-receipt.json'
    if path.exists():
        raw = _read_bytes(path, MAX_MANIFEST_BYTES, budget)
        old = _json(raw)
        keys = set(base) | {'reading_started_at_utc', 'artifact_readback_at_utc',
                            'receipt_prepared_at_utc', 'receipt_payload_sha256'}
        if set(old) != keys or any(old[k] != v for k, v in base.items()):
            raise ValueError('CONFLICTING_PRIOR_RECEIPT')
        without_seal = {k: v for k, v in old.items() if k != 'receipt_payload_sha256'}
        if old['receipt_payload_sha256'] != _sha(_canonical(without_seal)) or raw != _canonical(old):
            raise ValueError('PRIOR_RECEIPT_HASH_MISMATCH')
        times = [_aware(old[k]) for k in ('reading_started_at_utc', 'artifact_readback_at_utc', 'receipt_prepared_at_utc')]
        if not times[0] <= times[1] <= times[2] <= datetime.now(timezone.utc):
            raise ValueError('PRIOR_RECEIPT_TIME_INVALID')
        return raw
    now = datetime.now(timezone.utc).isoformat()
    proof = dict(base, reading_started_at_utc=started_at,
                 artifact_readback_at_utc=now, receipt_prepared_at_utc=now)
    proof['receipt_payload_sha256'] = _sha(_canonical(proof))
    return _canonical(proof)


def run_recovery(manifest_path, manifest_sha256, private_output, *, timeout_seconds=180):
    budget = _ReadBudget(timeout_seconds, error_type=ValueError)
    started_at = datetime.now(timezone.utc).isoformat()
    manifest_path = Path(manifest_path).absolute()
    source_root = manifest_path.parent
    output = Path(private_output).absolute()
    assert_private_directory(source_root)
    _output_guard(output)
    if (output.resolve().is_relative_to(source_root.resolve())
            or source_root.resolve().is_relative_to(output.resolve())):
        raise ValueError('OUTPUT_OVERLAPS_INPUTS')
    if not isinstance(manifest_sha256, str) or not HEX.fullmatch(manifest_sha256):
        raise ValueError('MANIFEST_SHA_REQUIRED')
    guard_private_path(source_root, manifest_path)
    raw_manifest = _read_bytes(manifest_path, MAX_MANIFEST_BYTES, budget)
    if _sha(raw_manifest) != manifest_sha256:
        raise ValueError('MANIFEST_SHA_MISMATCH')
    manifest = _json(raw_manifest)
    if manifest.get('schema_version') != SCHEMA:
        raise ValueError('UNKNOWN_SOURCE_MANIFEST')
    records, contents = _load_sources(source_root, manifest, budget,
                                       reading_started_at=_aware(started_at))
    runtime_hashes = _runtime_hashes()
    road_data = _optional(manifest, 'roads_source_id', 'roads', records, contents)
    activity_data = _optional(manifest, 'activity_source_id', 'activity', records, contents)
    capture_data = _optional(manifest, 'captures_source_id', 'captures', records, contents)
    roads, activity, pauses = [], None, []
    if road_data:
        value, original_sha, _ = road_data
        if value.get('schema_version') != 'habu-road-geometry-reference-v1' or not isinstance(value.get('roads'), list):
            raise ValueError('ROAD_SCHEMA_REQUIRED')
        roads = value['roads']
        if len(roads) > 100_000 or any(not isinstance(x, dict) or x.get('source_sha256') != original_sha for x in roads):
            raise ValueError('ROAD_SOURCE_BINDING_REQUIRED')
    if activity_data:
        value, original_sha, _ = activity_data
        if value.get('schema_version') != 'habu-route-activity-annotations-v1' or type(value.get('owner_search_context')) is not bool:
            raise ValueError('ACTIVITY_SCHEMA_REQUIRED')
        activity = {'owner_search_context': value['owner_search_context'], 'source_sha256': original_sha}
        if value['owner_search_context']:
            start, end = _aware(value.get('scope_start')), _aware(value.get('scope_end'))
            if start >= end:
                raise ValueError('ACTIVITY_SCOPE_INVALID')
            activity.update(scope_start=value['scope_start'], scope_end=value['scope_end'])
        pauses = value.get('pauses', [])
        if not isinstance(pauses, list) or len(pauses) > 1000 or any(not isinstance(x, dict) or x.get('source_sha256') != original_sha for x in pauses):
            raise ValueError('PAUSE_SOURCE_BINDING_REQUIRED')
    from src.route_recovery import parse_route
    routes = []
    points = []
    time_scopes = []
    for ident, item in records.items():
        if item['kind'] not in {'gpx', 'field-session', 'jsonl'}:
            continue
        parsed = parse_route(contents[ident], format=item['kind'], source_sha256=item['sha256'])
        route = _recover_route(parsed, roads=roads, activity=activity, pauses=pauses)
        usable_times = [_aware(p['time_utc']) for p in route['points'] if not p.get('exclude_point')]
        if usable_times:
            start, end = min(usable_times), max(usable_times)
            if any(start <= prior_end and prior_start <= end for prior_start, prior_end in time_scopes):
                raise ValueError('OVERLAPPING_ROUTE_SOURCES_REQUIRE_RECONCILIATION')
            time_scopes.append((start, end))
        route['source_id'] = ident
        routes.append(route)
        points.extend(route['points'])
        budget.check()
    if not routes:
        raise ValueError('NO_MEASURED_ROUTE_SOURCE')
    captures = {'sidecars': [], 'summary': {'status': 'NOT_PROVIDED'}}
    if capture_data:
        value, original_sha, _ = capture_data
        if value.get('schema_version') != 'habu-capture-event-candidates-v1' or not isinstance(value.get('events'), list):
            raise ValueError('CAPTURE_SIDECAR_SCHEMA_REQUIRED')
        if len(value['events']) > 20_000:
            raise ValueError('CAPTURE_EVENT_LIMIT')
        from src.capture_route_evidence import match_captures
        captures = match_captures(value['events'], points, source_sha256=original_sha)
    _attach_capture_references(routes, captures, source_provided=capture_data is not None)
    authority = {'canonical_capture_tally_delta': 0, 'candidate_database_updated': False,
                 'model_created_or_updated': False, 'formal_positive_qualified': False,
                 'formal_negative_qualified': False, 'p0_authorized': False,
                 'champion_promoted': False}
    payload = {'schema_version': 'habu-private-recovered-route-evidence-v1',
               'phase': 'POST_SEARCH_RESEARCH_ONLY', 'source_manifest_sha256': manifest_sha256,
               'source_records': list(records.values()), 'routes': routes,
               'capture_evidence': captures, 'authority': authority,
               'runtime_code_sha256': runtime_hashes,
               'python_version': sys.version.split()[0],
               'limitations': ['SOURCE_HASHES_VERIFY_BYTES_NOT_OWNER_IDENTITY',
                   'GPS_MATCH_IS_NOT_PREDICTION_ACCURACY',
                   'INTERPOLATED_DURATION_IS_NOT_MEASURED_ACTIVE_SEARCH',
                   'OWNER_ACTIVITY_ANNOTATIONS_REQUIRE_INDEPENDENT_QUALIFICATION',
                   'LATEST_PRIVATE_CAPTURE_CROSSWALK_NOT_AUTOMATICALLY_CERTIFIED']}
    encoded = _canonical(payload)
    if len(encoded) > MAX_OUTPUT_BYTES:
        raise ValueError('OUTPUT_BYTE_LIMIT')
    proof = {'schema_version': 'habu-route-recovery-completion-v1',
             'source_manifest_sha256': manifest_sha256, 'artifact_sha256': _sha(encoded),
             'artifact_size_bytes': len(encoded), 'sources_rechecked_before_commit': True,
             'authority': authority, 'runtime_code_sha256': runtime_hashes,
             'python_version': sys.version.split()[0]}
    encoded_proof = None
    if (output/'completion-receipt.json').exists():
        encoded_proof = _receipt(proof, output, budget, started_at)
    _recheck(source_root, manifest_path, manifest_sha256, records, budget)
    # Preflight both names before writing either file. No old evidence is removed.
    for name, raw in (('route-evidence.json', encoded),):
        target = output/name
        if target.exists() and _read_bytes(target, MAX_OUTPUT_BYTES, budget) != raw:
            raise ValueError('CONFLICTING_PRIVATE_OUTPUT')
    output.mkdir(parents=True, exist_ok=True)
    _output_guard(output)
    _write_new(output, 'route-evidence.json', encoded, budget)
    _recheck(source_root, manifest_path, manifest_sha256, records, budget)
    _verify_outputs(output, (('route-evidence.json', encoded),), budget)
    if _runtime_hashes() != runtime_hashes:
        raise ValueError('RUNTIME_CODE_CHANGED')
    if encoded_proof is None:
        encoded_proof = _receipt(proof, output, budget, started_at)
    _write_new(output, 'completion-receipt.json', encoded_proof, budget)
    _recheck(source_root, manifest_path, manifest_sha256, records, budget)
    _verify_outputs(output, (('route-evidence.json', encoded),
                             ('completion-receipt.json', encoded_proof)), budget)
    if _runtime_hashes() != runtime_hashes:
        raise ValueError('RUNTIME_CODE_CHANGED')
    return {'status': 'PRIVATE_ROUTE_EVIDENCE_RECOVERED', 'source_count': len(records),
            'route_source_count': len(routes), 'point_record_count': len(points),
            'window_count': sum(len(x['windows']) for x in routes),
            'capture_sidecar_count': len(captures['sidecars']),
            'artifact_sha256': _sha(encoded), 'receipt_sha256': _sha(encoded_proof),
            'formal_training_qualified': False, 'model_updated': False,
            'p0_authorized': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--private-output', type=Path, required=True)
    parser.add_argument('--timeout-seconds', type=float, default=180)
    args = parser.parse_args()
    try:
        result = run_recovery(args.manifest, args.manifest_sha256, args.private_output,
                              timeout_seconds=args.timeout_seconds)
    except ImportError:
        print(json.dumps({'status': 'BLOCKED', 'reason': 'PRIVATE_ROUTE_EXECUTOR_UNAVAILABLE'}))
        return 2
    except (ValueError, TypeError, KeyError, OSError, RecursionError, OverflowError):
        print(json.dumps({'status': 'BLOCKED', 'reason': 'PRIVATE_ROUTE_INPUT_OR_OUTPUT_REJECTED'}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
