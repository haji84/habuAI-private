"""Bounded clean actual-source PR33 materialization, with read-only output QA."""
import hashlib
import importlib.util
import json
import math
import resource
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

root = Path(__file__).parent.resolve()
spec = importlib.util.spec_from_file_location('pr33', root / 'scripts/build_osm_prospective_universe.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
source_manifest = json.loads((root / 'head-source-manifest.json').read_text())
def check_source():
    for entry in source_manifest:
        raw = (root / entry['path']).read_bytes()
        assert len(raw) == entry['size']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == entry['sha']
check_source()
raw = m.load_verified_road_csv(root)
cells = m.parse_road_cells(raw)
cutoff = datetime.now(timezone.utc) + timedelta(minutes=5)
night = m.operational_night(cutoff)
future = (cutoff + timedelta(minutes=10)).astimezone(m.JST)
first = future.replace(minute=(future.minute // 10) * 10, second=0, microsecond=0)
output_root = root.parent / 'pr33-actual-output'
assert not output_root.exists(), 'Use a clean output root for reproducibility'
started = time.monotonic()
result = m.materialize(root, output_root, night, cutoff.isoformat(), first.isoformat(), 6)
elapsed = time.monotonic() - started
snapshot_file = output_root / result['snapshot']
snapshot = json.loads(snapshot_file.read_bytes())
assert hashlib.sha256(snapshot_file.read_bytes()).hexdigest() == result['snapshot_sha256']
sources = {}
for ref in [snapshot['universe'], *snapshot['features']]:
    path = output_root / ref['path']
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == ref['sha256']
    assert m.aware(ref['available_at']) < cutoff
    sources[ref['path']] = {'bytes': len(data), 'sha256': ref['sha256']}
universe = json.loads((output_root / snapshot['universe']['path']).read_bytes())
features = {f['feature_name']: f for f in (
    json.loads((output_root / ref['path']).read_bytes()) for ref in snapshot['features'])}
rows = universe['rows']
assert len(rows) == 16990 * 6 == len({r['row_id'] for r in rows})
counts = Counter(r['window_start_jst'] for r in rows)
assert len(counts) == 6 and set(counts.values()) == {16990}
assert {r['row_id'] for r in rows} == set(next(iter(features.values()))['values'])
lookup = {c['cell_id']: c for c in cells}
for row in rows:
    cell = lookup[row['row_id'].split('@')[0]]
    assert (row['utm_x_m'], row['utm_y_m']) == (cell['x'], cell['y'])
    assert row['window_start_jst'] > first.isoformat() or row['window_start_jst'] == first.isoformat()
    assert not {'label','observed','capture_count','gpx_trace','outcome'} & set(row)
    rid = row['row_id']
    assert features['road_length_m']['values'][rid] == cell['length']
    assert abs(features['road_axial_cos']['values'][rid] - math.cos(math.radians(2 * cell['direction']))) < 1e-15
    assert abs(features['road_axial_sin']['values'][rid] - math.sin(math.radians(2 * cell['direction']))) < 1e-15
assert m.digest(m.canonical(sorted(features))) == snapshot['feature_schema_sha256']
assert result['official_prediction_eligible'] is False
assert universe['geographic_domain']['legal_access_and_current_closures'] == 'UNKNOWN'
assert universe['geographic_domain']['official_road_eligibility'] == 'NOT_VALIDATED'
boundary = {}
one = cells[:1]
for name, args, expected_error in [
    ('06:50_last_bin_allowed', ('2026-10-21','2026-10-22T06:40:00+09:00','2026-10-22T06:50:00+09:00',1,'2026-10-21T20:00:00+09:00'), None),
    ('07:00_rollover_rejected', ('2026-10-21','2026-10-22T06:40:00+09:00','2026-10-22T06:50:00+09:00',2,'2026-10-21T20:00:00+09:00'), 'boundary'),
    ('cutoff_equals_available_rejected', ('2026-10-21','2026-10-21T20:00:00+09:00','2026-10-21T21:00:00+09:00',1,'2026-10-21T20:00:00+09:00'), 'readiness'),
    ('window_equals_cutoff_rejected', ('2026-10-21','2026-10-21T20:00:00+09:00','2026-10-21T20:00:00+09:00',1,'2026-10-21T19:00:00+09:00'), 'order'),
    ('07:00_cutoff_prior_night_rejected', ('2026-10-21','2026-10-22T07:00:00+09:00','2026-10-22T07:10:00+09:00',1,'2026-10-21T19:00:00+09:00'), 'order'),
]:
    try:
        m.build_artifacts(one, *args)
        assert expected_error is None, name
        boundary[name] = 'PASS'
    except ValueError as error:
        assert expected_error and expected_error in str(error), (name, error)
        boundary[name] = 'PASS: ' + str(error)
sys.path.insert(0, str(root.parent / 'pr32-independent/src'))
import prospective_inputs
bound = prospective_inputs.load_prospective_inputs(output_root, result['snapshot'], result['snapshot_sha256'], night, cutoff, model_feature_names=tuple(sorted(features)))
assert len(bound['rows']) == len(rows) and bound['official_issuance_authorized'] is False
check_source()
evidence = {'head_sha':'10500af7fffcbe86dda8ad29ae968db778435662',
    'status':'PASS_ACTUAL_BYTES_PREPRODUCTION_ONLY','result':result,'window_rows':dict(counts),
    'cutoff':cutoff.isoformat(),'files':sources,'total_input_source_bytes':sum(v['bytes'] for v in sources.values()),
    'materialize_elapsed_seconds':elapsed,'ru_maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'boundary_checks':boundary,'all_37_source_blob_hashes_unchanged_after':True,
    'geometry_and_axial_values_checked_all_rows':True,'pr32_snapshot_binding':'PASS; synthetic as_of=cutoff only, no issuance',
    'notes':['Actual main/new-source bytes verified; no road reconstruction or legality validation claimed.',
             '100m/10-minute universe cells are not formal 100m ±10-minute target inference.',
             'No GPX, captures, Raw or ORIGINAL source files were written.']}
(root / 'actual-build-evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(evidence,ensure_ascii=False,indent=2))
