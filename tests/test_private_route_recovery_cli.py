"""Synthetic integration controls for the private source-bound route runner."""
import hashlib
import json
import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import recover_private_route_evidence as runner

ROOT = Path(__file__).resolve().parents[1]
GPX = b'''<gpx xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>
<trkpt lat="28.0" lon="129.3"><time>2026-10-01T09:59:50Z</time></trkpt>
<trkpt lat="28.0001" lon="129.3"><time>2026-10-01T10:00:00Z</time></trkpt>
<trkpt lat="28.0002" lon="129.3"><time>2026-10-01T10:00:10Z</time></trkpt>
</trkseg></trk></gpx>'''


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class PrivateRouteRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'private-input'
        self.source.mkdir()
        self.raw = self.source / 'measured.gpx'
        self.raw.write_bytes(GPX)
        self.out = self.base / 'private-output'
        self.manifest = self.source / 'manifest.json'
        self.data = {
            'schema_version': 'habu-private-route-source-manifest-v1',
            'sources': [self.entry('gpx', 'measured.gpx', GPX)],
        }
        self.seal()

    def entry(self, kind, path, raw, ident='gps'):
        return {'source_id': ident, 'kind': kind, 'path': path,
                'sha256': digest(raw), 'size_bytes': len(raw),
                'source_identity': 'SYNTHETIC_TEST_ONLY',
                'received_at': '2026-10-02T00:00:00+00:00',
                'original_timezone': 'UTC', 'correction_revision': 'original'}

    def seal(self):
        self.manifest.write_bytes((json.dumps(self.data, sort_keys=True)+'\n').encode())
        self.manifest_sha = digest(self.manifest.read_bytes())

    def run_case(self):
        return runner.run_recovery(self.manifest, self.manifest_sha, self.out)

    def test_actual_core_and_private_readback_are_idempotent(self):
        result = self.run_case()
        self.assertEqual(result['status'], 'PRIVATE_ROUTE_EVIDENCE_RECOVERED')
        artifact = self.out / 'route-evidence.json'
        receipt = self.out / 'completion-receipt.json'
        before = artifact.read_bytes(), receipt.read_bytes(), self.raw.read_bytes()
        self.assertEqual(self.run_case(), result)
        self.assertEqual(before, (artifact.read_bytes(), receipt.read_bytes(), self.raw.read_bytes()))
        payload = json.loads(artifact.read_bytes())
        self.assertEqual(payload['source_manifest_sha256'], self.manifest_sha)
        self.assertEqual(payload['authority']['canonical_capture_tally_delta'], 0)
        self.assertFalse(payload['authority']['formal_negative_qualified'])
        self.assertFalse(payload['authority']['model_created_or_updated'])
        self.assertFalse(payload['authority']['p0_authorized'])
        self.assertEqual(payload['phase'], 'POST_SEARCH_RESEARCH_ONLY')
        self.assertEqual(len(payload['routes']), 1)
        self.assertEqual(len(payload['routes'][0]['points']), 3)
        proof = json.loads(receipt.read_bytes())
        self.assertEqual(proof['artifact_sha256'], digest(artifact.read_bytes()))
        self.assertTrue(proof['sources_rechecked_before_commit'])

    def test_absent_road_source_is_reported_as_not_provided(self):
        self.run_case()
        route = json.loads((self.out/'route-evidence.json').read_bytes())['routes'][0]
        self.assertEqual(route['summary']['road_matching_status'], 'NOT_PRODUCED_NO_ROAD_SOURCE')
        self.assertEqual(route['summary']['road_distance_checks'], 0)
        self.assertTrue(all(p['road_match']['status'] == 'NOT_SUPPLIED' for p in route['points']))

    def test_wrong_manifest_hash_never_creates_output(self):
        with self.assertRaises(ValueError):
            runner.run_recovery(self.manifest, '0'*64, self.out)
        self.assertFalse(self.out.exists())

    def test_future_source_receipt_time_is_not_accepted(self):
        self.data['sources'][0]['received_at'] = '2099-01-01T00:00:00+00:00'
        self.seal()
        with self.assertRaises(ValueError): self.run_case()
        self.assertFalse(self.out.exists())

    def test_resealed_receipt_cannot_replace_boolean_contracts_with_numbers(self):
        self.run_case()
        path = self.out/'completion-receipt.json'
        original = json.loads(path.read_bytes())
        for parent, key, replacement in [('authority', 'formal_negative_qualified', 0),
                                          ('authority', 'canonical_capture_tally_delta', False),
                                          (None, 'sources_rechecked_before_commit', 1)]:
            with self.subTest(key=key):
                proof = copy.deepcopy(original)
                (proof[parent] if parent else proof)[key] = replacement
                proof['receipt_payload_sha256'] = runner._sha(runner._canonical(
                    {k: v for k, v in proof.items() if k != 'receipt_payload_sha256'}))
                mutated = runner._canonical(proof)
                path.write_bytes(mutated)
                with self.assertRaises(ValueError): self.run_case()
                self.assertEqual(path.read_bytes(), mutated)

    def test_resealed_prior_read_time_cannot_precede_its_source_receipt(self):
        self.run_case()
        path = self.out/'completion-receipt.json'
        proof = json.loads(path.read_bytes())
        proof.update(reading_started_at_utc='2000-01-01T00:00:00+00:00',
                     artifact_readback_at_utc='2000-01-01T00:00:01+00:00',
                     receipt_prepared_at_utc='2000-01-01T00:00:02+00:00')
        proof['receipt_payload_sha256'] = runner._sha(runner._canonical(
            {k: v for k, v in proof.items() if k != 'receipt_payload_sha256'}))
        mutated = runner._canonical(proof)
        path.write_bytes(mutated)
        with self.assertRaises(ValueError): self.run_case()
        self.assertEqual(path.read_bytes(), mutated)

    def test_changed_source_and_size_never_create_output(self):
        self.raw.write_bytes(GPX.replace(b'28.0001', b'28.0009'))
        with self.assertRaises(ValueError): self.run_case()
        self.assertFalse(self.out.exists())
        self.raw.write_bytes(GPX + b' ')
        with self.assertRaises(ValueError): self.run_case()
        self.assertFalse(self.out.exists())

    def test_changed_source_after_recovery_is_rechecked(self):
        real = runner._recover_route
        def mutate(*args, **kwargs):
            value = real(*args, **kwargs)
            self.raw.write_bytes(GPX.replace(b'28.0001', b'28.0009'))
            return value
        with patch.object(runner, '_recover_route', side_effect=mutate):
            with self.assertRaises(ValueError): self.run_case()
        self.assertFalse(self.out.exists())

    def test_derived_mutation_before_completion_cannot_report_success(self):
        real = runner._write_new
        def mutate(directory, name, raw, budget):
            if name == 'completion-receipt.json':
                path = directory/'route-evidence.json'
                path.write_bytes(path.read_bytes()+b' ')
            return real(directory, name, raw, budget)
        with patch.object(runner, '_write_new', side_effect=mutate):
            with self.assertRaises(ValueError): self.run_case()

    def test_time_only_positive_cannot_become_research_no_capture(self):
        routes = [{'points': [], 'windows': [{'cell_x': 1, 'cell_y': 2,
            'window_start_jst': '2026-10-01T19:00:00+09:00', 'activity_class': 'SEARCH_INFERRED'}]}]
        captures = {'sidecars': [{'capture_positive_evidence': True,
            'match_status': 'TIME_ONLY_POSITIVE_EVIDENCE', 'candidates': [],
            'event': {'event_id': 'synthetic-existing-event', 'recorded_at': '2026-10-01T10:05:00Z',
                      'time_semantics': 'OBSERVED_AT', 'uncertainty_seconds': 0}}]}
        runner._attach_capture_references(routes, captures, source_provided=True)
        window = routes[0]['windows'][0]
        self.assertEqual(window['research_capture_outcome'], 'UNKNOWN_CAPTURE_LOCATION_OR_TIME')
        self.assertEqual(window['unallocated_positive_time_refs'], ['synthetic-existing-event'])

    def test_unknown_recording_delay_cannot_make_other_windows_no_capture(self):
        routes = [{'points': [], 'windows': [{'cell_x': 1, 'cell_y': 2,
            'window_start_jst': '2026-10-01T19:00:00+09:00', 'activity_class': 'SEARCH_INFERRED'}]}]
        captures = {'sidecars': [{'capture_positive_evidence': True,
            'match_status': 'TIMING_AMBIGUOUS', 'candidates': [],
            'event': {'event_id': 'synthetic-delayed-event', 'recorded_at': '2026-10-02T10:05:00Z',
                      'time_semantics': 'RECORDED_AT', 'uncertainty_seconds': 0}}]}
        runner._attach_capture_references(routes, captures, source_provided=True)
        self.assertEqual(routes[0]['windows'][0]['research_capture_outcome'], 'UNKNOWN_CAPTURE_LOCATION_OR_TIME')

    def test_unknown_observation_precision_is_not_fabricated_or_no_capture(self):
        routes = [{'points': [], 'windows': [{'cell_x': 1, 'cell_y': 2,
            'window_start_jst': '2026-10-01T19:00:00+09:00', 'activity_class': 'SEARCH_INFERRED'}]}]
        captures = {'sidecars': [{'capture_positive_evidence': True,
            'match_status': 'TIMING_AMBIGUOUS', 'candidates': [],
            'event': {'event_id': 'synthetic-unknown-precision', 'recorded_at': '2026-10-01T10:00:00Z',
                      'time_semantics': 'OBSERVED_AT', 'uncertainty_seconds': None}}]}
        runner._attach_capture_references(routes, captures, source_provided=True)
        self.assertIsNone(captures['sidecars'][0]['event']['uncertainty_seconds'])
        self.assertEqual(routes[0]['windows'][0]['research_capture_outcome'], 'UNKNOWN_CAPTURE_LOCATION_OR_TIME')

    def test_observed_uncertainty_suppresses_adjacent_window_no_capture(self):
        routes = [{'points': [], 'windows': [{'cell_x': 1, 'cell_y': 2,
            'window_start_jst': '2026-10-01T19:00:00+09:00', 'activity_class': 'SEARCH_INFERRED'}]}]
        captures = {'sidecars': [{'capture_positive_evidence': True,
            'match_status': 'TIMING_AMBIGUOUS', 'candidates': [],
            'event': {'event_id': 'synthetic-boundary-event', 'recorded_at': '2026-10-01T10:10:01Z',
                      'time_semantics': 'OBSERVED_AT', 'uncertainty_seconds': 2}}]}
        runner._attach_capture_references(routes, captures, source_provided=True)
        self.assertEqual(routes[0]['windows'][0]['research_capture_outcome'], 'UNKNOWN_CAPTURE_LOCATION_OR_TIME')

    def test_actual_capture_sidecar_preserves_two_individuals_and_existing_input(self):
        original = b'SYNTHETIC ORIGINAL CAPTURE STATEMENT ONLY'
        (self.source/'capture-original.txt').write_bytes(original)
        event = {'event_id': 'existing-synthetic-event', 'individual_ids': ['animal-a','animal-b'],
            'source_sha256': digest(original), 'recorded_at': '2026-10-01T10:00:00Z',
            'time_semantics': 'OBSERVED_AT', 'uncertainty_seconds': 0,
            'latitude': 28.0001, 'longitude': 129.3, 'owner_role': 'OWNER',
            'species': 'HABU', 'event_type': 'CAPTURE', 'count': 2}
        raw = json.dumps({'schema_version': 'habu-capture-event-candidates-v1',
            'original_source_id': 'capture-original', 'events': [event]}).encode()
        path = self.source/'existing-capture-reference.json'
        path.write_bytes(raw)
        self.data['sources'] += [self.entry('evidence', 'capture-original.txt', original, ident='capture-original'),
                                  self.entry('captures', path.name, raw, ident='capture-reference')]
        self.data['captures_source_id'] = 'capture-reference'
        self.seal()
        result = self.run_case()
        self.assertEqual(result['capture_sidecar_count'], 1)
        payload = json.loads((self.out/'route-evidence.json').read_bytes())
        capture = payload['capture_evidence']
        self.assertEqual(len(capture['sidecars']), 1)
        self.assertEqual(capture['summary']['capture_positive_individuals'], 2)
        self.assertEqual(capture['summary']['model_updates'], 0)
        self.assertEqual(capture['summary']['canonical_updates'], 0)
        self.assertEqual(capture['sidecars'][0]['event'], event)
        refs = [ref for route in payload['routes'] for window in route['windows']
                for ref in window['positive_event_match_refs']]
        self.assertTrue(refs)
        self.assertEqual({x['event_id'] for x in refs}, {'existing-synthetic-event'})
        self.assertTrue(all(x['assignment'] == 'GPS_SAMPLE_MATCH_CANDIDATE_NOT_EVENT_WINDOW_LABEL' for x in refs))
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual((self.source/'capture-original.txt').read_bytes(), original)

    def test_duplicate_source_ids_or_bytes_are_not_double_added(self):
        self.data['sources'].append(dict(self.data['sources'][0], source_id='other'))
        self.seal()
        with self.assertRaises(ValueError): self.run_case()
        self.assertFalse(self.out.exists())

    def test_overlapping_route_sources_do_not_double_exposure(self):
        raw = GPX+b'\n'
        (self.source/'second.gpx').write_bytes(raw)
        self.data['sources'].append(self.entry('gpx', 'second.gpx', raw, ident='second'))
        self.seal()
        with self.assertRaises(ValueError): self.run_case()
        self.assertFalse(self.out.exists())

    def test_source_traversal_and_unbound_optional_inputs_reject(self):
        self.data['sources'][0]['path'] = '../private-input/measured.gpx'
        self.seal()
        with self.assertRaises(ValueError): self.run_case()
        self.data['sources'][0]['path'] = 'measured.gpx'
        self.data['activity_source_id'] = 'not-in-closure'
        self.seal()
        with self.assertRaises(ValueError): self.run_case()
        self.assertFalse(self.out.exists())

    def test_other_git_worktree_output_rejects_before_writing(self):
        other = self.base / 'other-public-worktree'
        other.mkdir()
        (other / '.git').write_text('gitdir: /synthetic/repo')
        self.out = other / 'never-private'
        with self.assertRaises(ValueError): self.run_case()
        self.assertFalse(self.out.exists())

    def test_output_must_not_overlap_sources_or_models(self):
        self.out = self.source
        with self.assertRaises(ValueError): self.run_case()
        self.assertFalse((self.source/'route-evidence.json').exists())

    def test_conflicting_prior_output_is_preserved(self):
        self.out.mkdir()
        target = self.out/'route-evidence.json'
        target.write_bytes(b'PRIOR_PRIVATE_OUTPUT')
        with self.assertRaises(ValueError): self.run_case()
        self.assertEqual(target.read_bytes(), b'PRIOR_PRIVATE_OUTPUT')
        self.assertFalse((self.out/'completion-receipt.json').exists())

    def test_duplicate_deep_nonfinite_manifest_is_sanitized_in_actual_cli(self):
        variants = [b'{"sources":[],"sources":[]}', b'{"number":NaN}',
                    (b'['*80)+(b']'*80), b'[]', b'{"private":"TOP_SECRET_MARKER"']
        for raw in variants:
            self.manifest.write_bytes(raw)
            proc = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT/'scripts/recover_private_route_evidence.py'),
                    '--manifest', str(self.manifest), '--manifest-sha256', digest(raw),
                    '--private-output', str(self.out)], capture_output=True, text=True, cwd=self.base)
            self.assertEqual(proc.returncode, 2)
            reply = json.loads(proc.stdout)
            self.assertEqual(reply['status'], 'BLOCKED')
            self.assertNotIn('TOP_SECRET_MARKER', proc.stdout+proc.stderr)
            self.assertNotIn(str(self.base), proc.stdout+proc.stderr)
            self.assertNotIn('Traceback', proc.stderr)
        self.assertFalse(self.out.exists())

    def test_cli_stdout_only_aggregates_and_hashes(self):
        proc = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT/'scripts/recover_private_route_evidence.py'),
                '--manifest', str(self.manifest), '--manifest-sha256', self.manifest_sha,
                '--private-output', str(self.out)], capture_output=True, text=True, cwd=self.base)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result['status'], 'PRIVATE_ROUTE_EVIDENCE_RECOVERED')
        for secret in ('28.0001', '129.3', '09:59:50', str(self.base), 'SYNTHETIC_TEST_ONLY'):
            self.assertNotIn(secret, proc.stdout+proc.stderr)


if __name__ == '__main__': unittest.main()
