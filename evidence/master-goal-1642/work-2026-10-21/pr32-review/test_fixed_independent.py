"""Independent verification against a read-only fixed candidate."""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

FIX = Path('/workspace/scratch/ded5451af149/pr32-fix')
ORIGINAL = Path('/workspace/scratch/ded5451af149/pr32-independent')
sys.path[:0] = [str(FIX / 'src'), str(ORIGINAL / 'tests')]
import prospective_inputs as pi
from master_contracts import canonical_bytes, digest, file_hash
from test_prospective_inputs import fixtures, run, write, NIGHT


class FixedIndependentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.u, self.f, self.s, self.ur, self.fr, self.sr = fixtures(self.root)

    def publish(self):
        self.ur = write(self.root, self.ur['path'], self.u)
        self.fr = write(self.root, self.fr['path'], self.f)
        self.s['universe'] = self.ur
        self.s['features'] = [self.fr]
        self.sr = write(self.root, self.sr['path'], self.s)

    def test_all_known_outcome_predictor_names(self):
        for name in ('label', 'observed', 'label_available_at', 'outcome',
                     'actual_capture', 'capture_event_ids', 'capture_count',
                     'gpx_trace', 'negative_observed'):
            with self.subTest(name=name):
                self.f['feature_name'] = name
                self.s['feature_schema_sha256'] = digest([name])
                self.publish()
                with self.assertRaisesRegex(ValueError, 'outcome|Outcome'):
                    run(self.root, self.sr, model_feature_names=(name,))

    def test_nested_row_outcome_rejected(self):
        self.u['rows'][0]['metadata'] = [{'nested': {'label': 1}}]
        self.publish()
        with self.assertRaisesRegex(ValueError, 'outcome|Outcome'):
            run(self.root, self.sr)

    def test_feature_metadata_outcome_rejected(self):
        self.f['metadata'] = [{'nested': {'capture_count': 3}}]
        self.publish()
        with self.assertRaisesRegex(ValueError, 'outcome|Outcome'):
            run(self.root, self.sr)

    def test_timezone_equivalent_duplicate_rejected(self):
        self.u['rows'][1]['utm_x_m'] = self.u['rows'][0]['utm_x_m']
        self.u['rows'][1]['window_start_jst'] = NIGHT + 'T10:00:00Z'
        self.publish()
        with self.assertRaisesRegex(ValueError, 'Duplicate 100m x 10min'):
            run(self.root, self.sr)

    def growth_hook(self, bytes_to_write, on_read=1):
        target = self.root / self.fr['path']
        original_open = Path.open
        count = 0
        def racing_open(path, mode='r', *args, **kwargs):
            nonlocal count
            if path == target and mode == 'rb':
                count += 1
                if count == on_read:
                    with original_open(target, 'wb') as writer:
                        writer.write(bytes_to_write)
            return original_open(path, mode, *args, **kwargs)
        return patch.object(Path, 'open', racing_open)

    def test_growth_after_stat_rejected_by_real_source_bytes(self):
        raw = canonical_bytes(dict(self.f, padding='x' * 2048)) + b'\n'
        self.s['features'][0]['sha256'] = hashlib.sha256(raw).hexdigest()
        self.sr = write(self.root, self.sr['path'], self.s)
        with patch.object(pi, 'MAX_SOURCE_BYTES', 1024), self.growth_hook(raw):
            with self.assertRaisesRegex(ValueError, 'oversized|budget'):
                run(self.root, self.sr)

    def test_growth_after_stat_rejected_by_real_total_bytes(self):
        raw = canonical_bytes(dict(self.f, padding='x' * 2048)) + b'\n'
        self.s['features'][0]['sha256'] = hashlib.sha256(raw).hexdigest()
        self.sr = write(self.root, self.sr['path'], self.s)
        total = sum((self.root / r['path']).stat().st_size for r in (self.sr, self.ur, self.fr))
        with patch.object(pi, 'MAX_SOURCE_BYTES', 4096), patch.object(pi, 'MAX_TOTAL_BYTES', total+512), self.growth_hook(raw):
            with self.assertRaisesRegex(ValueError, 'budget'):
                run(self.root, self.sr)

    def test_growth_during_final_recheck_is_bounded(self):
        raw = canonical_bytes(dict(self.f, padding='x' * 2048)) + b'\n'
        with patch.object(pi, 'MAX_SOURCE_BYTES', 1024), self.growth_hook(raw, on_read=2):
            with self.assertRaisesRegex(ValueError, 'oversized|budget'):
                run(self.root, self.sr)

    def test_real_400000_cell_limit_rejects_400032_before_source_reads(self):
        template = self.u['rows'][0]
        self.u['rows'] = [dict(template, row_id=f'r{i}', utm_x_m=100050+(i%1000)*100,
                              utm_y_m=3000050+(i//1000)*100) for i in range(12501)]
        self.ur = write(self.root, self.ur['path'], self.u)
        self.s['universe'] = self.ur
        self.s['features'] = [self.fr] * 32
        self.sr = write(self.root, self.sr['path'], self.s)
        with self.assertRaisesRegex(ValueError, 'join cell budget'):
            run(self.root, self.sr)

    def test_final_scan_atomicity_is_documented_limit(self):
        snapshot = self.root / self.sr['path']
        universe = self.root / self.ur['path']
        original_open = Path.open
        count = 0
        def racing_open(path, mode='r', *args, **kwargs):
            nonlocal count
            if path == universe and mode == 'rb':
                count += 1
                if count == 2:
                    with original_open(snapshot, 'wb') as writer:
                        writer.write(b'{"changed":true}\n')
            return original_open(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', racing_open):
            result = run(self.root, self.sr)
        self.assertNotEqual(file_hash(snapshot), self.sr['sha256'])
        self.assertEqual(result['consumed_sha256'][self.sr['path']], self.sr['sha256'])
        self.assertEqual(result['rows'][0]['features']['rain_3h_mm'], 0.5)
        self.assertFalse(result['official_issuance_authorized'])

    def test_missing_cell_remains_unknown(self):
        self.f['values'].pop('b')
        self.publish()
        with self.assertRaisesRegex(ValueError, 'entire ex-ante universe'):
            run(self.root, self.sr)

    def test_0700_boundary_and_equal_cutoff_availability(self):
        self.u['rows'][0]['window_start_jst'] = '2026-10-14T21:50:00Z'
        self.publish()
        self.assertEqual(len(run(self.root, self.sr)['rows']), 2)
        self.u['rows'][0]['window_start_jst'] = '2026-10-15T07:00:00+09:00'
        self.publish()
        with self.assertRaisesRegex(ValueError, 'off-night'):
            run(self.root, self.sr)
        self.u['rows'][0]['window_start_jst'] = NIGHT + 'T19:00:00+09:00'
        self.publish()
        self.s['features'][0]['available_at'] = self.s['cutoff_time']
        self.sr = write(self.root, self.sr['path'], self.s)
        with self.assertRaisesRegex(ValueError, 'not available before cutoff'):
            run(self.root, self.sr)

    def test_33_features_rejected_before_universe_open(self):
        self.s['features'] = [self.fr] * 33
        self.sr = write(self.root, self.sr['path'], self.s)
        (self.root / self.ur['path']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'feature count limit'):
            run(self.root, self.sr)

    def test_invalid_elapsed_allowances_rejected(self):
        for value in (0, -0.1, True, False, None, '30', 300.01,
                      float('nan'), float('inf'), float('-inf')):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'Invalid prospective elapsed budget'):
                    run(self.root, self.sr, budget_seconds=value)

    def test_elapsed_caller_boundary_and_ceiling(self):
        with patch.object(pi, 'monotonic', side_effect=(0, 0.125)):
            with self.assertRaisesRegex(TimeoutError, 'elapsed budget'):
                run(self.root, self.sr, budget_seconds=0.125)
        with patch.object(pi, 'monotonic', return_value=0):
            self.assertFalse(run(self.root, self.sr, budget_seconds=300)['official_issuance_authorized'])

    def test_deadline_after_initial_and_last_source_read(self):
        target = self.root / self.fr['path']
        for occurrence in (1, 2):
            with self.subTest(occurrence=occurrence):
                clock = [0.0]
                count = [0]
                original_open = Path.open
                def timed_open(path, mode='r', *args, **kwargs):
                    if path == target and mode == 'rb':
                        count[0] += 1
                        if count[0] == occurrence:
                            clock[0] = 31.0
                    return original_open(path, mode, *args, **kwargs)
                with patch.object(pi, 'monotonic', side_effect=lambda: clock[0]), patch.object(Path, 'open', timed_open):
                    with self.assertRaisesRegex(TimeoutError, 'elapsed budget'):
                        run(self.root, self.sr)

    def test_deadline_during_universe_rows(self):
        clock = [0.0]
        original_coordinates = pi._coordinates
        def timed_coordinates(row):
            clock[0] = 31.0
            return original_coordinates(row)
        with patch.object(pi, 'monotonic', side_effect=lambda: clock[0]), patch.object(pi, '_coordinates', timed_coordinates):
            with self.assertRaisesRegex(TimeoutError, 'elapsed budget'):
                run(self.root, self.sr)

    def test_deadline_during_numeric_cells(self):
        clock = [0.0]
        original_finite = pi.math.isfinite
        def timed_finite(value):
            if value == 0.5:
                clock[0] = 31.0
            return original_finite(value)
        with patch.object(pi, 'monotonic', side_effect=lambda: clock[0]), patch.object(pi.math, 'isfinite', timed_finite):
            with self.assertRaisesRegex(TimeoutError, 'elapsed budget'):
                run(self.root, self.sr)

    def test_deadline_during_nested_metadata_precedes_row_allocation(self):
        self.u['metadata'] = [{'synthetic_value': i} for i in range(1000)]
        self.publish()
        ticks = [0]
        def ticking_clock():
            ticks[0] += 1
            return 31.0 if ticks[0] >= 100 else 0.0
        with patch.object(pi, 'monotonic', side_effect=ticking_clock), patch.object(pi, '_coordinates', wraps=pi._coordinates) as coordinates:
            with self.assertRaisesRegex(TimeoutError, 'elapsed budget'):
                run(self.root, self.sr)
            coordinates.assert_not_called()


if __name__ == '__main__':
    unittest.main()
