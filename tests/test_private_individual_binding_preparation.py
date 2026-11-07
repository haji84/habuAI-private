"""Synthetic prereveal preparation; no actual predictions or outcomes are issued."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_private_individual_pdca_scoring as fixtures
from master_contracts import canonical_bytes, digest
from scripts import score_private_pdca_individual_targets as command


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.fx = fixtures.PrivateIndividualPdcaTests()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        # Only this preparation fixture adopts the dedicated ex-ante namespace.
        # The ordinary scorer's existing synthetic fixtures stay unchanged.
        for node in self.fx.request['bundle']['sources'][:2]:
            previous = self.fx.root / node['ref']['path']
            node['ref']['path'] = 'evidence/exante/' + node['id'] + '.json'
            target = self.fx.root / node['ref']['path']
            target.parent.mkdir(exist_ok=True)
            previous.rename(target)
        self.fx.p0['individual_target_binding']['exante_sources_sha256'] = digest(dict(
            universe_source_id='universe', targets_source_id='targets',
            sources=sorted(self.fx.request['bundle']['sources'][:2], key=lambda row: row['id'])))
        self.fx.write_p0()
        self.request = dict(schema_version='habu-private-individual-binding-request-v1',
            protocol={k: v for k, v in self.fx.request['protocol'].items() if k != 'assessment_as_of'},
            exante=dict(universe_source_id='universe', targets_source_id='targets',
                        sources=copy.deepcopy(self.fx.request['bundle']['sources'][:2])))
        self.now = datetime.fromisoformat('2026-10-26T18:59:00+09:00')

    def write(self):
        raw = canonical_bytes(self.request) + b'\n'
        self.fx.request_path.write_bytes(raw)
        return dict(root=self.fx.root, night=fixtures.NIGHT,
            request_path=self.fx.request_path.relative_to(self.fx.root).as_posix(),
            request_sha256=hashlib.sha256(raw).hexdigest())

    def prepare(self, **kwargs):
        api = getattr(command, 'prepare_private_individual_binding', None)
        self.assertTrue(callable(api), 'Missing read-only pre-cutoff binding preparer')
        args = self.write()
        args.update(kwargs)
        before = {p: p.read_bytes() for p in self.fx.root.rglob('*') if p.is_file()}
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return self.now.astimezone(tz) if tz else self.now.replace(tzinfo=None)
        with patch.object(command, 'datetime', Clock):
            result = api(**args)
        self.assertEqual(before, {p: p.read_bytes() for p in self.fx.root.rglob('*') if p.is_file()})
        return result

    def test_prepares_exact_existing_binding_without_p0_or_ledger_reads(self):
        self.fx.remove_ledger()
        reads = []
        actual = command.g0.G0ArtifactReader.read
        def trace(reader, ref, **kw):
            reads.append(ref['path'])
            return actual(reader, ref, **kw)
        with patch.object(command.g0.G0ArtifactReader, 'read', trace):
            result = self.prepare()
        self.assertEqual(result['execution_status'], 'BINDING_PREPARED', result)
        self.assertEqual(result['individual_target_binding'], self.fx.p0['individual_target_binding'])
        self.assertFalse(any('ledger' in p or 'predictions/' in p for p in reads))
        self.assertFalse(result['official_issuance_authorized'])
        self.assertFalse(result['production_authorized'])
        self.assertIsNone(result['individual_recall'])
        self.assertEqual(result['receipt_sha256'], digest({k: v for k, v in result.items() if k != 'receipt_sha256'}))
        for private in (str(self.fx.root), 'synthetic-owner', '3000050'):
            self.assertNotIn(private, json.dumps(result))

    def test_afterward_ordinary_scorer_accepts_the_same_binding_and_real_assessment(self):
        result = self.prepare()
        self.assertEqual(result['execution_status'], 'BINDING_PREPARED', result)
        self.fx.p0['individual_target_binding'] = result['individual_target_binding']
        self.fx.write_p0()
        scored = self.fx.score(0)
        self.assertEqual(scored['individual_recall'], .5)
        self.assertFalse(scored['official_100m_10min_kpi_computed'])

    def test_actual_cutoff_equality_and_after_are_blocked(self):
        for stamp in ('2026-10-26T19:00:00+09:00', '2026-10-26T19:00:00.000001+09:00'):
            self.now = datetime.fromisoformat(stamp)
            result = self.prepare()
            self.assertEqual(result['execution_status'], 'DATA_BLOCKED', result)
            self.assertIsNone(result['individual_target_binding'])

    def test_future_declared_freeze_is_not_prepared(self):
        self.now = datetime.fromisoformat('2026-10-26T18:44:59+09:00')
        self.assertEqual(self.prepare()['execution_status'], 'DATA_BLOCKED')

    def test_all_outcome_roles_and_disconnected_support_rejected_without_reads(self):
        original = copy.deepcopy(self.request)
        for role in ('LEDGER', 'ASCERTAINMENT', 'ACTIVE_SEARCH', 'OUTCOME_SCOPE', 'SUPPORT'):
            self.request = copy.deepcopy(original)
            extra = copy.deepcopy(self.fx.request['bundle']['sources'][2])
            extra['role'] = role
            self.request['exante']['sources'].append(extra)
            with patch.object(command.g0.G0ArtifactReader, 'read', side_effect=AssertionError('source opened')):
                result = self.prepare()
            self.assertEqual(result['execution_status'], 'FAIL', result)
            self.assertIsNone(result['individual_target_binding'])

    def test_assessment_and_outcome_selector_fields_are_forbidden(self):
        self.request['protocol']['assessment_as_of'] = '2026-10-27T12:00:00+09:00'
        self.assertEqual(self.prepare()['execution_status'], 'FAIL')
        self.request['protocol'].pop('assessment_as_of')
        self.request['exante']['ledger_source_id'] = 'ledger'
        self.assertEqual(self.prepare()['execution_status'], 'FAIL')

    def test_exact_night_hash_and_private_path_are_required(self):
        for kwargs in (dict(night='2026-10-27'), dict(request_sha256='0'*64),
                       dict(request_path='../outside.json'), dict(root=fixtures.ROOT)):
            with self.subTest(kwargs=list(kwargs)):
                result = self.prepare(**kwargs)
                self.assertEqual(result['execution_status'], 'FAIL', result)
                self.assertIsNone(result['individual_target_binding'])

    def test_resealed_invalid_scope_target_and_precision_are_rejected(self):
        for mutation in ('unit', 'owner', 'precision'):
            self.fx.doCleanups()
            self.setUp()
            def change(body):
                if mutation == 'unit': body['targets'][0]['source_unit_id'] = 'absent'
                elif mutation == 'owner': body['owner_id'] = 'foreign'
                else: body['targets'][0]['predicted_time'] = '2026-10-26T21:05:00.0000001+09:00'
            self.fx.replace_exante('TARGETS', change)
            self.request['protocol'] = {k:v for k,v in self.fx.request['protocol'].items() if k!='assessment_as_of'}
            self.request['exante']['sources'] = copy.deepcopy(self.fx.request['bundle']['sources'][:2])
            self.assertEqual(self.prepare()['execution_status'], 'FAIL')

    def test_late_wall_clock_and_runtime_expiry_clear_all_prepared_claims(self):
        api = getattr(command, 'prepare_private_individual_binding', None)
        self.assertTrue(callable(api), 'Missing preparer')
        args = self.write()
        before = self.now
        after = datetime.fromisoformat('2026-10-26T19:00:00+09:00')
        class Clock(datetime):
            calls = 0
            @classmethod
            def now(cls, tz=None):
                cls.calls += 1
                return (before if cls.calls == 1 else after).astimezone(tz)
        with patch.object(command, 'datetime', Clock):
            result = api(**args)
        self.assertEqual(result['execution_status'], 'DATA_BLOCKED', result)
        self.assertIsNone(result['individual_target_binding'])
        with patch.object(command.pi.ProspectiveReadContext, 'check', side_effect=TimeoutError):
            result = api(**args)
        self.assertEqual(result['execution_status'], 'RUNTIME_BLOCKED')
        self.assertIsNone(result['individual_target_binding'])

    def test_cli_has_explicit_read_only_mode_and_no_clock_override(self):
        args = self.write()
        run = subprocess.run([sys.executable, '-B', str(fixtures.COMMAND), '--prepare-binding',
            '--root', str(self.fx.root), '--night', fixtures.NIGHT,
            '--request-path', args['request_path'], '--request-sha256', args['request_sha256']], capture_output=True)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(run.stderr, b'', run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(result['execution_status'], 'DATA_BLOCKED')
        self.assertIsNone(result['individual_target_binding'])
        help_run = subprocess.run([sys.executable, '-B', str(fixtures.COMMAND), '--help'], capture_output=True)
        self.assertIn(b'--prepare-binding', help_run.stdout)
        self.assertNotIn(b'--clock', help_run.stdout)

    def test_readiness_after_freeze_and_parent_cycle_are_rejected(self):
        initial = copy.deepcopy(self.request)
        for case in ('future', 'cycle'):
            self.request = copy.deepcopy(initial)
            if case == 'future':
                target = self.request['exante']['sources'][1]
                stamp = '2026-10-26T18:46:00+09:00'
                target.update(readiness=dict.fromkeys(command.individual.READINESS, stamp), usable_at=stamp)
            else:
                self.request['exante']['sources'][0]['parents'] = ['targets']
            result = self.prepare()
            self.assertEqual(result['execution_status'], 'FAIL', result)
            self.assertIsNone(result['individual_target_binding'])

    def test_unproduced_target_is_missing_not_a_prepared_forecast(self):
        self.fx.replace_exante('TARGETS', lambda body: body.update(produced=False, targets=[]))
        self.request['protocol'] = {k:v for k,v in self.fx.request['protocol'].items() if k!='assessment_as_of'}
        self.request['exante']['sources'] = copy.deepcopy(self.fx.request['bundle']['sources'][:2])
        result = self.prepare()
        self.assertEqual(result['execution_status'], 'DATA_BLOCKED', result)
        self.assertIsNone(result['individual_target_binding'])

    def test_source_or_request_changed_after_validation_cannot_leave_a_binding(self):
        api = getattr(command, 'prepare_private_individual_binding', None)
        self.assertTrue(callable(api))
        for change_request in (False, True):
            args = self.write()
            target = self.fx.request_path if change_request else self.fx.root / self.request['exante']['sources'][0]['ref']['path']
            original = target.read_bytes()
            native = command._exante_texts
            def mutate(*args):
                result = native(*args)
                target.write_bytes(bytes([original[0] ^ 1]) + original[1:])
                return result
            class Clock(datetime):
                @classmethod
                def now(cls, tz=None): return self.now.astimezone(tz)
            try:
                with patch.object(command, 'datetime', Clock), patch.object(command, '_exante_texts', side_effect=mutate):
                    result = api(**args)
                self.assertEqual(result['execution_status'], 'FAIL', result)
                self.assertIsNone(result['individual_target_binding'])
                self.assertIsNone(result['prepared_at'])
            finally:
                target.write_bytes(original)

    def test_late_deadline_and_clock_reversal_cannot_release_partial_binding(self):
        native = command._exante_texts
        def expire(reader, nodes, protocol, times, budget):
            result = native(reader, nodes, protocol, times, budget)
            reader.context.deadline = 0
            return result
        with patch.object(command, '_exante_texts', side_effect=expire):
            result = self.prepare()
        self.assertEqual(result['execution_status'], 'RUNTIME_BLOCKED', result)
        self.assertIsNone(result['individual_target_binding'])
        api = command.prepare_private_individual_binding
        args = self.write()
        class Clock(datetime):
            calls = 0
            @classmethod
            def now(cls, tz=None):
                cls.calls += 1
                minute = '59' if cls.calls == 1 else '58'
                return datetime.fromisoformat('2026-10-26T18:'+minute+':00+09:00').astimezone(tz)
        with patch.object(command, 'datetime', Clock):
            result = api(**args)
        self.assertEqual(result['execution_status'], 'DATA_BLOCKED', result)
        self.assertIsNone(result['individual_target_binding'])

    def test_depth_capacity_and_foreign_budget_fail_without_callbacks(self):
        for value in (True, 10**400, float('inf'), float('nan')):
            result = self.prepare(budget_seconds=value)
            self.assertEqual(result['execution_status'], 'FAIL', result)
        calls = []
        class Foreign:
            def __float__(self): calls.append('float'); raise AssertionError
            def __lt__(self, other): calls.append('compare'); raise AssertionError
        self.assertEqual(self.prepare(budget_seconds=Foreign())['execution_status'], 'FAIL')
        self.assertEqual(calls, [])
        self.request['protocol']['capacities']['max_json_nodes'] = 1
        result = self.prepare()
        self.assertEqual(result['execution_status'], 'RUNTIME_BLOCKED', result)
        self.assertIsNone(result['individual_target_binding'])

    def test_reachable_ledger_or_opaque_support_is_rejected_before_any_body_read(self):
        initial = copy.deepcopy(self.request)
        for wrapper in (False, True):
            with self.subTest(wrapper=wrapper):
                self.request = copy.deepcopy(initial)
                extra = copy.deepcopy(self.fx.request['bundle']['sources'][2])
                if wrapper:
                    ledger = json.loads((self.fx.root / extra['ref']['path']).read_bytes())
                    raw = canonical_bytes(dict(schema_version='habu-individual-target-source-v1',
                        kind='SUPPORT', details=ledger)) + b'\n'
                    extra['ref'] = dict(path='evidence/exante/opaque.json',
                        sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
                    (self.fx.root / extra['ref']['path']).write_bytes(raw)
                stamp = '2026-10-26T17:00:00+09:00'
                extra.update(id='opaque', role='SUPPORT',
                    readiness=dict.fromkeys(command.individual.READINESS, stamp), usable_at=stamp)
                self.request['exante']['sources'].append(extra)
                self.request['exante']['sources'][0]['parents'] = ['opaque']
                reads = []
                actual = command.g0.G0ArtifactReader.read
                def trace(reader, ref, **kw):
                    reads.append(ref['path'])
                    return actual(reader, ref, **kw)
                with patch.object(command.g0.G0ArtifactReader, 'read', trace):
                    result = self.prepare()
                self.assertEqual(reads, [], 'Preparation opened a source body before rejecting opaque ancestry')
                self.assertEqual(result['execution_status'], 'FAIL', result)
                self.assertIsNone(result['individual_target_binding'])

    def test_non_exante_source_paths_are_rejected_before_any_body_read(self):
        initial = copy.deepcopy(self.request)
        for relative in ('evidence/synthetic/universe.json', 'evidence/Exante/universe.json',
                         'evidence/exante-alias/universe.json'):
            self.request = copy.deepcopy(initial)
            node = self.request['exante']['sources'][0]
            raw = (self.fx.root / node['ref']['path']).read_bytes()
            target = self.fx.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            node['ref']['path'] = relative
            with patch.object(command.g0.G0ArtifactReader, 'read', side_effect=AssertionError('source opened')):
                result = self.prepare()
            self.assertEqual(result['execution_status'], 'FAIL', result)
            self.assertIsNone(result['individual_target_binding'])

    def test_declared_json_byte_cap_covers_request_and_known_physical_bodies(self):
        for limit in (500, len(canonical_bytes(self.request)) + 100):
            with self.subTest(limit=limit):
                self.request['protocol']['capacities']['max_json_bytes'] = limit
                result = self.prepare()
                self.assertEqual(result['execution_status'], 'RUNTIME_BLOCKED', result)
                self.assertIsNone(result['individual_target_binding'])
                self.assertIsNone(result['prepared_at'])

    def test_cutoff_reached_during_result_encoding_releases_no_binding(self):
        args = self.write()
        early = self.now
        late = datetime.fromisoformat('2026-10-26T19:00:00+09:00')
        encoded_result = [False]
        native = command.individual._digest
        def track(value, budget):
            result = native(value, budget)
            if type(value) is dict and value.get('execution_status') == 'BINDING_PREPARED':
                encoded_result[0] = True
            return result
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None): return (late if encoded_result[0] else early).astimezone(tz)
        with patch.object(command, 'datetime', Clock), patch.object(command.individual, '_digest', side_effect=track):
            result = command.prepare_private_individual_binding(**args)
        self.assertEqual(result['execution_status'], 'DATA_BLOCKED', result)
        self.assertIsNone(result['individual_target_binding'])
