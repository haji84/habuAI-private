"""Isolated, synthetic reproduction of PR33 availability/path contract defects."""
import importlib.util
import json
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

MODULE = Path(__file__).parent / 'scripts/build_osm_prospective_universe.py'
spec = importlib.util.spec_from_file_location('pr33', MODULE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
cells = [{'cell_id': 'utm52n_100m_4000_30000', 'x': 400050.0,
          'y': 3000050.0, 'island': '奄美大島', 'length': 10.0, 'direction': 15.0}]

def arguments(seconds=0.1):
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(seconds=seconds)
    local = (cutoff + timedelta(minutes=10)).astimezone(m.JST)
    first = local.replace(minute=(local.minute // 10) * 10, second=0, microsecond=0)
    return m.operational_night(cutoff), cutoff, first

def mocked_source():
    return patch.multiple(m, load_verified_road_csv=lambda _: b'synthetic',
                          parse_road_cells=lambda _: cells)

results = {'head_sha': '10500af7fffcbe86dda8ad29ae968db778435662',
           'source': 'synthetic, loader mocked to isolate materializer boundaries'}
with tempfile.TemporaryDirectory() as scratch:
    root = Path(scratch)
    repo = root / 'canonical'
    repo.mkdir()
    night, cutoff, first = arguments()
    original_canonical = m.canonical
    stalled = [False]
    def delayed_canonical(obj):
        if not stalled[0]:
            stalled[0] = True
            time.sleep(0.25)
        return original_canonical(obj)
    with mocked_source(), patch.object(m, 'canonical', delayed_canonical):
        emitted = m.materialize(repo, root / 'output', night, cutoff.isoformat(), first.isoformat(), 1)
    finished = datetime.now(timezone.utc)
    snapshot_path = root / 'output' / emitted['snapshot']
    snapshot = json.loads(snapshot_path.read_text())
    availability = m.aware(snapshot['universe']['available_at'])
    stat_time = datetime.fromtimestamp(snapshot_path.stat().st_mtime, timezone.utc)
    assert emitted['status'] == 'PREPRODUCTION_INPUT_ONLY'
    assert availability < cutoff < stat_time <= finished
    results['availability'] = {'emitted_status': emitted['status'],
        'available_at': availability.isoformat(), 'cutoff': cutoff.isoformat(),
        'snapshot_file_mtime': stat_time.isoformat(), 'returned_at': finished.isoformat(),
        'cutoff_exceeded_but_success': True}
with tempfile.TemporaryDirectory() as scratch:
    root = Path(scratch)
    repo = root / 'canonical'
    raw = repo / 'data/raw'
    raw.mkdir(parents=True)
    sentinel = raw / 'original.bin'
    sentinel.write_bytes(b'original bytes must remain unchanged')
    out = root / 'outside'
    out.mkdir()
    (out / 'features').symlink_to(raw, target_is_directory=True)
    night, cutoff, first = arguments(10)
    with mocked_source():
        emitted = m.materialize(repo, out, night, cutoff.isoformat(), first.isoformat(), 1)
    final = (out / emitted['snapshot']).resolve()
    assert final.is_relative_to(repo)
    assert sentinel.read_bytes() == b'original bytes must remain unchanged'
    results['output_path'] = {'output_root_resolves_outside_repo': not out.resolve().is_relative_to(repo),
        'emitted_status': emitted['status'], 'resolved_snapshot_inside_repo': final.is_relative_to(repo),
        'resolved_snapshot_relative_to_repo': str(final.relative_to(repo)),
        'raw_original_bytes_preserved_in_fixture': True,
        'new_files_inside_raw': sorted(str(p.relative_to(raw)) for p in raw.rglob('*') if p.is_file())}
out = Path(__file__).parent / 'reproduction-evidence.json'
out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
print(out.read_text())
