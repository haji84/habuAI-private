"""Exercise the private command against exact synthetic files."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_individual_time_target_evaluation import fixture
from master_contracts import canonical_bytes, digest


ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / 'scripts' / 'score_private_pdca_individual_targets.py'
NIGHT = '2026-10-26'


class PrivateIndividualPdcaTests(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)
        self.p0_dir = self.root / 'predictions' / 'original' / NIGHT / 'P0'
        bundle, protocol = fixture()
        for node in bundle['sources']:
            path = self.root / node['ref']['path']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(node.pop('raw_json_utf8').encode())
        self.request = dict(schema_version='habu-private-individual-pdca-request-v1',
                            p0_payload_sha256=None, bundle=bundle, protocol=protocol)
        frozen_protocol = {k: v for k, v in protocol.items() if k != 'assessment_as_of'}
        exante = dict(universe_source_id='universe', targets_source_id='targets',
                      sources=sorted(bundle['sources'][:2], key=lambda node: node['id']))
        self.p0 = dict(prediction_version='P0', prediction_class='ORIGINAL',
                       operational_night=NIGHT, cutoff_time='2026-10-26T19:00:00+09:00',
                       frozen_at='2026-10-26T19:01:00+09:00',
                       model_sha256='a'*64, inference_sha256='b'*64,
                       individual_target_binding=dict(schema_version='habu-frozen-individual-target-binding-v1',
                           protocol_sha256=digest(frozen_protocol), exante_sources_sha256=digest(exante)))
        self.request_path = self.root / 'config' / 'private-individual-pdca-request.json'
        self.request_path.parent.mkdir()
        self.write_p0()

    def write_p0(self):
        self.p0_dir.mkdir(parents=True, exist_ok=True)
        self.p0.pop('payload_sha256', None)
        self.p0['payload_sha256'] = digest(self.p0)
        (self.p0_dir / 'prediction.json').write_bytes(canonical_bytes(self.p0) + b'\n')
        (self.p0_dir / 'sha256.txt').write_bytes((self.p0['payload_sha256'] + '  prediction.json\n').encode())
        self.request['p0_payload_sha256'] = self.p0['payload_sha256']

    def replace_exante(self, role, change):
        node = self.source(role)
        path = self.root / node['ref']['path']
        body = json.loads(path.read_bytes())
        change(body)
        raw = canonical_bytes(body) + b'\n'
        path.write_bytes(raw)
        node['ref'].update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        protocol = self.request['protocol']
        protocol['exante_source_sha256'][role.lower()] = node['ref']['sha256']
        self.p0['individual_target_binding'].update(
            protocol_sha256=digest({k: v for k, v in protocol.items() if k != 'assessment_as_of'}),
            exante_sources_sha256=digest(dict(universe_source_id='universe', targets_source_id='targets',
                sources=sorted((self.source('UNIVERSE'), self.source('TARGETS')), key=lambda row: row['id']))))
        self.write_p0()

    def source(self, role):
        return next(node for node in self.request['bundle']['sources'] if node['role'] == role)

    def score(self, expected_code, *, raw=None):
        if raw is None:
            raw = canonical_bytes(self.request) + b'\n'
        self.request_path.write_bytes(raw)
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        run = subprocess.run([sys.executable, '-B', str(COMMAND), '--root', str(self.root),
                              '--night', NIGHT, '--request-path', self.request_path.relative_to(self.root).as_posix(),
                              '--request-sha256', hashlib.sha256(raw).hexdigest()],
                             capture_output=True, timeout=30)
        self.assertEqual(run.returncode, expected_code, run.stderr.decode('utf-8', errors='replace'))
        self.assertEqual(run.stderr, b'')
        output = run.stdout.decode('utf-8')
        self.assertNotIn(str(self.root), output)
        for sensitive in ('synthetic-owner', 'individual0', 'event0', '3000050'):
            self.assertNotIn(sensitive, output)
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        return json.loads(output)

    def remove_ledger(self):
        (self.root / self.source('LEDGER')['ref']['path']).unlink()

    def score_in_process(self, command):
        raw = canonical_bytes(self.request) + b'\n'
        self.request_path.write_bytes(raw)
        return command.score_private_individual_targets(self.root, night=NIGHT,
            request_path=self.request_path.relative_to(self.root).as_posix(),
            request_sha256=hashlib.sha256(raw).hexdigest())

    def test_actual_command_computes_one_match_against_two_individuals(self):
        report = self.score(0)
        self.assertEqual(report['execution_status'], 'DIAGNOSTIC_COMPUTED')
        self.assertEqual(report['individual_recall'], 0.5)
        self.assertEqual(report['denominator_min'], 2)
        self.assertEqual(report['matched_individuals'], 1)
        self.assertIs(report['official_100m_10min_kpi_computed'], False)
        self.assertIs(report['official_issuance_authorized'], False)
        self.assertIs(report['production_authorized'], False)
        self.assertEqual(report['p0_record_sha256'],
                         hashlib.sha256((self.p0_dir / 'prediction.json').read_bytes()).hexdigest())
        self.assertEqual(report['p0_freeze_sidecar_sha256'],
                         hashlib.sha256((self.p0_dir / 'sha256.txt').read_bytes()).hexdigest())
        receipt = report.pop('receipt_sha256')
        self.assertEqual(receipt, digest(report))

    def test_recovered_p0_does_not_substitute_for_original(self):
        self.remove_ledger()
        recovered = self.root / 'predictions' / 'recovered_original'
        (self.root / 'predictions' / 'original').rename(recovered)
        report = self.score(2)
        self.assertEqual(report['blockers'], ['ORIGINAL_P0_REQUIRED'])

    def test_missing_freeze_sidecar_stops_before_ledger(self):
        self.remove_ledger()
        (self.p0_dir / 'sha256.txt').unlink()
        self.assertEqual(self.score(2)['blockers'], ['P0_FREEZE_SIDECAR_REQUIRED'])

    def test_corrupted_freeze_sidecar_stops_before_ledger(self):
        self.remove_ledger()
        sidecar = self.p0_dir / 'sha256.txt'
        sidecar.write_bytes(b'0' * 64 + b'  prediction.json\n')
        self.assertEqual(self.score(1)['blockers'], ['P0_FREEZE_SIDECAR_MISMATCH'])

    def test_unbound_original_stops_before_ledger(self):
        self.remove_ledger()
        self.p0.pop('individual_target_binding')
        self.write_p0()
        self.assertEqual(self.score(2)['blockers'], ['P0_FROZEN_INDIVIDUAL_BINDING_REQUIRED'])

    def test_resealed_request_with_changed_horizon_cannot_reselect(self):
        self.remove_ledger()
        self.request['protocol']['context']['horizon_end'] = '2026-10-26T22:00:00+09:00'
        self.assertEqual(self.score(1)['blockers'], ['P0_FROZEN_PROTOCOL_MISMATCH'])

    def test_resealed_request_with_changed_exante_clock_is_rejected(self):
        self.remove_ledger()
        self.source('TARGETS')['readiness']['source_received_at'] = '2026-10-26T18:44:00+09:00'
        self.assertEqual(self.score(1)['blockers'], ['P0_EXANTE_CLOSURE_MISMATCH'])

    def test_original_frozen_at_horizon_start_is_rejected(self):
        self.remove_ledger()
        self.p0['frozen_at'] = self.request['protocol']['context']['horizon_start']
        self.write_p0()
        self.assertEqual(self.score(1)['blockers'], ['P0_FROZEN_CONTEXT_MISMATCH'])

    def test_same_size_target_tamper_fails_before_missing_ledger(self):
        self.remove_ledger()
        target = self.root / self.source('TARGETS')['ref']['path']
        raw = target.read_bytes()
        changed = raw.replace(b'"t0"', b'"t1"')
        self.assertNotEqual(changed, raw)
        self.assertEqual(len(changed), len(raw))
        target.write_bytes(changed)
        self.assertEqual(self.score(1)['blockers'], ['EXANTE_SOURCE_VALIDATION_FAILED'])

    def test_missing_outcome_keeps_score_unknown(self):
        self.remove_ledger()
        report = self.score(2)
        self.assertEqual(report['blockers'], ['TYPED_SOURCE_NOT_SUPPLIED'])
        self.assertIsNone(report['individual_recall'])

    def test_frozen_but_unproduced_targets_stop_before_ledger(self):
        self.replace_exante('TARGETS', lambda body: body.update(produced=False, targets=[]))
        self.remove_ledger()
        self.assertEqual(self.score(2)['blockers'], ['TARGET_SET_NOT_PRODUCED'])

    def test_frozen_bytes_with_foreign_scope_stop_before_ledger(self):
        def change(body):
            body['context']['horizon_end'] = '2026-10-26T22:00:00+09:00'
        self.replace_exante('TARGETS', change)
        self.remove_ledger()
        self.assertEqual(self.score(1)['blockers'], ['FROZEN_EXANTE_BODY_MISMATCH'])

    def test_protocol_decimal_cannot_underflow_onto_frozen_zero(self):
        raw = canonical_bytes(self.request).replace(b'"distance_m":0.0', b'"distance_m":1e-999')
        self.assertIn(b'1e-999', raw)
        self.assertEqual(self.score(1, raw=raw)['blockers'], ['PRIVATE_SCORE_SOURCE_VALIDATION_FAILED'])

    def test_unsearched_forecast_remains_unknown_in_aggregate(self):
        def add_unit(body):
            unit = dict(body['units'][0], row_id='u1', cell_x=3010)
            body['units'].append(unit)
        self.replace_exante('UNIVERSE', add_unit)
        def add_target(body):
            body['universe_source_sha256'] = self.source('UNIVERSE')['ref']['sha256']
            target = dict(body['targets'][0], target_id='t1', source_unit_id='u1')
            target['position'] = dict(target['position'], x_m=301050.)
            body['targets'].append(target)
        self.replace_exante('TARGETS', add_target)
        report = self.score(0)
        self.assertEqual(report['unknown_targets'], 1)
        self.assertIsNone(report['false_positives'])
        self.assertIsNone(report['precision'])

    def test_original_record_must_have_its_canonical_physical_encoding(self):
        self.remove_ledger()
        path = self.p0_dir / 'prediction.json'
        path.write_bytes(path.read_bytes() + b'\n')
        self.assertEqual(self.score(1)['blockers'], ['ORIGINAL_P0_CANONICAL_INTEGRITY_FAILED'])

    def test_frozen_model_and_inference_must_match_protocol(self):
        self.remove_ledger()
        for field in ('model_sha256', 'inference_sha256'):
            with self.subTest(field=field):
                original = self.p0[field]
                self.p0[field] = 'e' * 64
                self.write_p0()
                self.assertEqual(self.score(1)['blockers'], ['P0_FROZEN_LINEAGE_MISMATCH'])
                self.p0[field] = original

    def test_git_workspace_and_sealed_source_paths_are_rejected(self):
        self.remove_ledger()
        self.source('LEDGER')['ref']['path'] = 'evidence/SeAlEd/ledger.json'
        self.assertEqual(self.score(1)['blockers'], ['UNSAFE_OR_DUPLICATE_EVIDENCE_PATH'])
        (self.root / '.git').write_text('marker')
        self.assertEqual(self.score(1)['blockers'], ['PRIVATE_SCORE_SOURCE_VALIDATION_FAILED'])

    def test_rescan_discards_score_if_source_changes_during_kernel(self):
        from scripts import score_private_pdca_individual_targets as command

        ledger = self.root / self.source('LEDGER')['ref']['path']
        evaluate = command.individual.evaluate_individual_targets

        def evaluate_then_mutate(*args, **kwargs):
            score = evaluate(*args, **kwargs)
            self.assertEqual(score['individual_recall'], 0.5)
            ledger.write_bytes(ledger.read_bytes().replace(b'individual1', b'individualX'))
            return score

        with patch.object(command.individual, 'evaluate_individual_targets', side_effect=evaluate_then_mutate):
            report = self.score_in_process(command)
        self.assertEqual(report['execution_status'], 'FAIL')
        self.assertIsNone(report['individual_recall'])
        self.assertNotIn('p0_payload_sha256', report)

    def check_invalid_exante_never_reads_ledger(self):
        from scripts import score_private_pdca_individual_targets as command

        reads = []
        read = command.g0.G0ArtifactReader.read

        def trace(reader, ref, **kwargs):
            reads.append(ref['path'])
            return read(reader, ref, **kwargs)

        with patch.object(command.g0.G0ArtifactReader, 'read', trace):
            report = self.score_in_process(command)
        self.assertEqual(report['execution_status'], 'FAIL')
        self.assertIn(self.source('UNIVERSE')['ref']['path'], reads)
        self.assertIn(self.source('TARGETS')['ref']['path'], reads)
        self.assertNotIn(self.source('LEDGER')['ref']['path'], reads)

    def test_frozen_invalid_universe_unit_never_reads_ledger(self):
        self.replace_exante('UNIVERSE', lambda body: body['units'][0].update(cell_x=4000))
        self.replace_exante('TARGETS', lambda body: body.update(
            universe_source_sha256=self.source('UNIVERSE')['ref']['sha256']))
        self.check_invalid_exante_never_reads_ledger()

    def test_frozen_target_outside_universe_never_reads_ledger(self):
        self.replace_exante('TARGETS', lambda body: body['targets'][0].update(source_unit_id='foreign'))
        self.check_invalid_exante_never_reads_ledger()

    def test_preflight_and_final_kernel_spend_the_same_frozen_deadline(self):
        from scripts import score_private_pdca_individual_targets as command

        protocol = self.request['protocol']
        protocol['capacities']['max_seconds'] = 1
        self.p0['individual_target_binding']['protocol_sha256'] = digest(
            {key: value for key, value in protocol.items() if key != 'assessment_as_of'})
        self.write_p0()
        clock = [100.]
        read_p0 = command._frozen_p0
        read_universe = command.individual._universe
        evaluate = command.individual.evaluate_individual_targets

        def timed_p0(*args):
            result = read_p0(*args)
            clock[0] += .4
            return result

        def timed_universe(*args):
            clock[0] += .4
            return read_universe(*args)

        with (patch.object(command.pi, 'monotonic', side_effect=lambda: clock[0]),
              patch.object(command.individual.time, 'monotonic', side_effect=lambda: clock[0]),
              patch.object(command, '_frozen_p0', side_effect=timed_p0),
              patch.object(command.individual, '_universe', side_effect=timed_universe),
              patch.object(command.individual, 'evaluate_individual_targets', wraps=evaluate) as scoring):
            report = self.score_in_process(command)
        self.assertAlmostEqual(scoring.call_args.kwargs['budget_seconds'], .2)
        self.assertEqual(report['execution_status'], 'RUNTIME_BLOCKED')
        self.assertIsNone(report['individual_recall'])


if __name__ == '__main__':
    unittest.main()
