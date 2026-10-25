#!/usr/bin/env python3
"""Bounded, real-time PR33 -> PR32 integration diagnostic; no source changes."""
from __future__ import annotations
import base64
import csv
import hashlib
import importlib.util
import inspect
import io
import json
import math
from pathlib import Path
import sys
import time
import traceback
from collections import Counter
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True
ROOT = Path('/workspace/scratch/ded5451af149')
EVIDENCE = ROOT / 'premerge-integration-evidence'
CANDIDATE = ROOT / 'premerge-integration-20261021'
ARCHIVES = ROOT / 'pr33-review'
PARTS_RELATIVE = 'artifacts/Habu_AI_OSM_Road_Grid_2026-09-25.zip.parts'
OUTPUT = EVIDENCE / 'producer-output'
RESULT_PATH = EVIDENCE / 'real-producer-consumer-result.json'
JST = ZoneInfo('Asia/Tokyo')
EXPECTED_FEATURES = ('road_axial_cos', 'road_axial_sin', 'road_length_m')

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def manifest(root, predicate=lambda p: True):
    result = {}
    for path in sorted(root.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path.suffix == '.pyc' or not predicate(path):
            continue
        raw = path.read_bytes()
        result[path.relative_to(root).as_posix()] = {'size_bytes': len(raw), 'sha256': sha(raw)}
    return result

def save(name, obj):
    path = EVIDENCE / name
    raw = (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    path.write_bytes(raw)
    return {'path': str(path), 'size_bytes': len(raw), 'sha256': sha(raw)}

started = datetime.now(timezone.utc)
result = {
    'diagnostic': 'REAL_OSM_PR33_TO_PR32_DIRECT_BINDING',
    'started_at': started.isoformat(),
    'candidate_root': str(CANDIDATE),
    'archive_root': str(ARCHIVES),
    'python': sys.executable,
    'clock_is_actual_utc': True,
    'source_modified': False,
    'scope': 'preproduction input integrity only; no official prediction, P0, science-performance, main or CI claim',
}
candidate_before = manifest(CANDIDATE)
parts_before = manifest(ARCHIVES / PARTS_RELATIVE)
result['candidate_before_manifest'] = save('candidate-before-sha256.json', candidate_before)
result['archive_parts_before_manifest'] = save('archive-parts-before-sha256.json', parts_before)
exit_code = 1
try:
    assert len(parts_before) == 33, len(parts_before)
    producer_file = CANDIDATE / 'scripts/build_osm_prospective_universe.py'
    spec = importlib.util.spec_from_file_location('combined_candidate_pr33', producer_file)
    producer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(producer)
    # PR33 itself selects this candidate's src directory; inspect imports below.
    import prospective_inputs as consumer
    import master_contracts
    import model_evaluation
    imported = {
        'producer': producer,
        'consumer': consumer,
        'master_contracts': master_contracts,
        'model_evaluation': model_evaluation,
    }
    result['source_modules'] = {}
    for name, module in imported.items():
        path = Path(inspect.getfile(module)).resolve()
        assert path.is_relative_to(CANDIDATE), (name, str(path))
        raw = path.read_bytes()
        result['source_modules'][name] = {'path': str(path), 'sha256': sha(raw), 'size_bytes': len(raw)}
    print('Imported exact combined candidate producer and consumer:', result['source_modules'], flush=True)

    zipped = base64.b64decode(b''.join((ARCHIVES / PARTS_RELATIVE / f'part_{i:03d}.b64').read_bytes()
                                     for i in range(33)), validate=True)
    assert sha(zipped) == producer.ARCHIVE_SHA256
    csv_bytes = producer.load_verified_road_csv(ARCHIVES)
    assert sha(csv_bytes) == producer.CELLS_SHA256
    source_cells = {}
    for item in csv.DictReader(io.StringIO(csv_bytes.decode('utf-8-sig'))):
        cell_id = item['cell_id']
        assert cell_id not in source_cells
        source_cells[cell_id] = {
            'x': float(item['cell_center_x']), 'y': float(item['cell_center_y']),
            'length': float(item['road_length_m']), 'direction': float(item['road_direction_deg']),
        }
    assert len(source_cells) == 16990
    result['input'] = {'archive_sha256': sha(zipped), 'archive_size_bytes': len(zipped),
                       'road_csv_sha256': sha(csv_bytes), 'road_csv_size_bytes': len(csv_bytes),
                       'verified_parts': len(parts_before), 'road_cells': len(source_cells)}

    actual_now = datetime.now(timezone.utc)
    cutoff = actual_now + timedelta(seconds=20)
    first_window = (cutoff + timedelta(minutes=10)).astimezone(JST)
    first_window = first_window.replace(minute=(first_window.minute // 10) * 10, second=0, microsecond=0)
    night = producer.operational_night(cutoff)
    assert producer.operational_night(first_window + timedelta(minutes=50)) == night
    result['execution_request'] = {'operational_night': night, 'cutoff': cutoff.isoformat(),
                                   'first_window': first_window.isoformat(), 'windows': 6,
                                   'cutoff_lead_seconds': 20}
    build_start = time.monotonic()
    emitted = producer.materialize(ARCHIVES, OUTPUT, night, cutoff.isoformat(), first_window.isoformat(), 6)
    build_elapsed = time.monotonic() - build_start
    result['producer_receipt'] = emitted
    result['producer_elapsed_seconds_diagnostic_only'] = build_elapsed
    assert emitted['cells'] == 16990 and emitted['rows'] == 101940 and emitted['windows'] == 6
    assert emitted['status'] == 'PREPRODUCTION_INPUT_ONLY'
    assert emitted['official_prediction_eligible'] is False
    completed = datetime.fromisoformat(emitted['completed_at'])
    assert completed < cutoff
    snapshot_path = OUTPUT / emitted['snapshot']
    snapshot_raw = snapshot_path.read_bytes()
    assert sha(snapshot_raw) == emitted['snapshot_sha256']
    snapshot = json.loads(snapshot_raw)
    refs = [snapshot['universe'], *snapshot['features']]
    expected_consumed = {emitted['snapshot']: emitted['snapshot_sha256']}
    files = {}
    source_ready_values = []
    feature_refs = {}
    for ref in refs:
        path = OUTPUT / ref['path']
        raw = path.read_bytes()
        ready = datetime.fromisoformat(ref['available_at'])
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        assert sha(raw) == ref['sha256']
        assert modified <= ready <= completed < cutoff
        source_ready_values.append(ready.isoformat())
        expected_consumed[ref['path']] = ref['sha256']
        files[ref['path']] = {'size_bytes': len(raw), 'sha256': sha(raw),
                              'mtime': modified.isoformat(), 'available_at': ready.isoformat()}
        value = json.loads(raw)
        if 'feature_name' in value:
            feature_refs[value['feature_name']] = ref
            assert datetime.fromisoformat(value['available_at']) <= ready
    snapshot_mtime = datetime.fromtimestamp(snapshot_path.stat().st_mtime, timezone.utc)
    assert snapshot_mtime <= completed < cutoff
    files[emitted['snapshot']] = {'size_bytes': len(snapshot_raw), 'sha256': sha(snapshot_raw),
                                  'mtime': snapshot_mtime.isoformat()}
    result['producer_output_files'] = files
    print(f'Producer emitted {emitted["rows"]} rows; snapshot {emitted["snapshot_sha256"]}; completion {completed.isoformat()} < cutoff {cutoff.isoformat()}', flush=True)

    wait_start = time.monotonic()
    wait_deadline = wait_start + 25
    while datetime.now(timezone.utc) < cutoff:
        if time.monotonic() >= wait_deadline:
            raise TimeoutError('Bounded actual-clock cutoff wait exceeded 25s')
        time.sleep(min(0.25, max(0.001, (cutoff - datetime.now(timezone.utc)).total_seconds())))
    as_of = datetime.now(timezone.utc)
    assert cutoff <= as_of < first_window
    result['consumer_as_of'] = as_of.isoformat()
    result['actual_cutoff_wait_seconds'] = time.monotonic() - wait_start
    load_start = time.monotonic()
    joined = consumer.load_prospective_inputs(
        OUTPUT, emitted['snapshot'], emitted['snapshot_sha256'], night, as_of,
        model_feature_names=EXPECTED_FEATURES,
    )
    result['consumer_elapsed_seconds_diagnostic_only'] = time.monotonic() - load_start
    assert joined['qualification'] == 'PREPRODUCTION_INPUT_INTEGRITY_ONLY'
    assert joined['official_issuance_authorized'] is False
    assert joined['consumed_sha256'] == expected_consumed
    assert joined['feature_schema_sha256'] == snapshot['feature_schema_sha256']
    rows = joined['rows']
    assert len(rows) == 101940
    universe = json.loads((OUTPUT / snapshot['universe']['path']).read_bytes())
    original_rows = {unit['row_id']: unit for unit in universe['rows']}
    assert len(original_rows) == 101940
    window_counts = Counter()
    cells_by_window = {}
    checked_feature_values = 0
    for unit in rows:
        row_id = unit['row_id']
        original = original_rows.pop(row_id)
        assert {key: unit[key] for key in original} == original
        cell_id = row_id.rsplit('@', 1)[0]
        expected = source_cells[cell_id]
        assert unit['utm_x_m'] == expected['x'] and unit['utm_y_m'] == expected['y']
        assert set(unit['features']) == set(EXPECTED_FEATURES)
        expected_values = {'road_length_m': expected['length'],
                           'road_axial_cos': math.cos(math.radians(2 * expected['direction'])),
                           'road_axial_sin': math.sin(math.radians(2 * expected['direction']))}
        for name, number in expected_values.items():
            assert math.isfinite(unit['features'][name])
            assert math.isclose(unit['features'][name], number, rel_tol=1e-14, abs_tol=1e-14)
            assert unit['feature_source_refs'][name] == [feature_refs[name]['path']]
            assert unit['feature_available_at'][name] == feature_refs[name]['available_at']
            checked_feature_values += 1
        window = unit['window_start_jst']
        window_counts[window] += 1
        cells_by_window.setdefault(window, set()).add(cell_id)
    assert not original_rows
    assert len(window_counts) == 6 and set(window_counts.values()) == {16990}
    assert all(cells == set(source_cells) for cells in cells_by_window.values())
    assert checked_feature_values == 305820
    joined_raw = master_contracts.canonical_bytes(joined)
    result['consumer_output'] = {'rows': len(rows), 'feature_values_checked_against_actual_csv': checked_feature_values,
                                 'windows': dict(sorted(window_counts.items())),
                                 'all_cells_in_every_window': True, 'all_rows_preserved': True,
                                 'all_feature_values_match_actual_csv': True,
                                 'consumed_sha256': joined['consumed_sha256'],
                                 'feature_schema_sha256': joined['feature_schema_sha256'],
                                 'canonical_result_size_bytes': len(joined_raw), 'canonical_result_sha256': sha(joined_raw),
                                 'qualification': joined['qualification'],
                                 'official_issuance_authorized': joined['official_issuance_authorized']}
    result['checks'] = {'direct_emitted_snapshot_consumed_unchanged': True,
                        'producer_completion_strictly_before_cutoff': True,
                        'all_source_mtimes_before_observed_ref_availability': True,
                        'all_reference_availability_before_cutoff': True,
                        'consumer_as_of_is_real_clock_at_or_after_cutoff': True,
                        'all_windows_future_at_consumer_as_of': True,
                        'all_consumed_hashes_match_producer_files': True,
                        'producer_official_prediction_eligible': emitted['official_prediction_eligible'],
                        'consumer_official_issuance_authorized': joined['official_issuance_authorized']}
    result['verdict'] = 'PASS_DIRECT_PRODUCER_CONSUMER_INTEGRATION'
    exit_code = 0
except BaseException as error:
    result['verdict'] = 'FAIL_DIAGNOSTIC_NO_FIXES_APPLIED'
    result['failure'] = {'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}
    print(result['failure']['traceback'], flush=True)
finally:
    candidate_after = manifest(CANDIDATE)
    parts_after = manifest(ARCHIVES / PARTS_RELATIVE)
    result['candidate_after_manifest'] = save('candidate-after-sha256.json', candidate_after)
    result['archive_parts_after_manifest'] = save('archive-parts-after-sha256.json', parts_after)
    result['candidate_files_unchanged'] = candidate_after == candidate_before
    result['archive_parts_unchanged'] = parts_after == parts_before
    result['candidate_regular_source_data_files_checked'] = len(candidate_before)
    result['finished_at'] = datetime.now(timezone.utc).isoformat()
    if not result['candidate_files_unchanged'] or not result['archive_parts_unchanged']:
        result['verdict'] = 'FAIL_SOURCE_OR_INPUT_CHANGED_DURING_DIAGNOSTIC'
        exit_code = 1
    save(RESULT_PATH.name, result)
    print('VERDICT:', result['verdict'], flush=True)
    print('Candidate files unchanged:', result['candidate_files_unchanged'], '; archive parts unchanged:', result['archive_parts_unchanged'], flush=True)
    print('Result JSON:', RESULT_PATH, flush=True)
sys.exit(exit_code)
