"""Synthetic native Task6a -> existing G0 materialization regressions."""
import hashlib
import importlib
import importlib.util
import json
import pathlib
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts'), str(ROOT / 'tests')]
import test_evidence_audit as fixtures
import test_g0_training_source_contract as g0_fixtures
import evidence_audit


class MaterializerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.parent = pathlib.Path(self.tmp.name).resolve()
        self.root = self.parent / 'source'
        self.root.mkdir()
        self.output = self.parent / 'private-output'

    def call(self, **options):
        self.assertIsNotNone(importlib.util.find_spec('materialize_private_g0_sources'),
                             'Missing native Task6a materializer')
        module = importlib.import_module('materialize_private_g0_sources')
        return module.materialize_sources(self.root, self.output,
            night=fixtures.NIGHT, **options)

    def test_missing_feature_components_preserves_native_unknown_audit_without_training(self):
        fixtures.fixture(self.root)
        originals = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = self.call()
        receipt = result['receipt']
        self.assertEqual(receipt['status'], 'BLOCKED')
        self.assertIn('FEATURE_CORPUS_NOT_SUPPLIED', receipt['reason_codes'])
        self.assertIsNone(receipt['manifest_ref'])
        self.assertIsNone(receipt['eligible_training_units'])
        self.assertEqual(receipt['new_real_fits'], 0)
        self.assertFalse(receipt['production_authorized'])
        audit = json.loads((self.output / receipt['audit_ref']['path']).read_bytes())
        self.assertEqual(audit['implementation_version'], 'evidence-audit-v1')
        self.assertIsNone(audit['observation_units'][0]['label'])
        self.assertFalse(any(p.name == 'candidates' for p in self.output.rglob('*')))
        for path, raw in originals.items():
            self.assertEqual(path.read_bytes(), raw)

    def test_source_event_identity_quantity_and_unknown_precision_are_preserved(self):
        fixtures.fixture(self.root, qualified=True)
        result = self.call()
        rows = result['observations']
        positive_source = [r for r in rows if r['capture_event_ids']]
        self.assertEqual(len(positive_source), 1)
        row = positive_source[0]
        self.assertEqual(row['capture_event_ids'], ['C'])
        self.assertEqual(row['recorded_quantity'], 2)
        self.assertEqual(row['individual_ids'], [])
        self.assertEqual(row['observation'], 'UNKNOWN')
        self.assertIsNone(row['label'])
        self.assertIn('CAPTURE_ROLE_OR_PRECISION_NOT_ESTABLISHED', row['reason_codes'])

    def test_sample_negative_does_not_become_complete_g0_negative(self):
        _, cap = fixtures.fixture(self.root, qualified=True, empty=True)
        fixtures.complete_coverage(self.root, cap)
        result = self.call()
        audit = json.loads((self.output / result['receipt']['audit_ref']['path']).read_bytes())
        self.assertTrue(any(u['label'] == 0 for u in audit['observation_units']))
        self.assertTrue(all(r['label'] is None for r in result['observations']))
        self.assertEqual(result['receipt']['new_negative_rows'], 0)

    def components(self, *, species='HABU', empty=False, negative_proofs=False):
        fx = g0_fixtures.TrainingSourceContractTests()
        fx.setUp()
        self.addCleanup(fx.doCleanups)
        self.root = fx.root
        self.output = fx.fixture.work / 'private-materialized'
        columns = ('event_id,event_type,event_count,datetime_jst,latitude,longitude,operational_date,'
                   'owner_role,species,time_semantics,uncertainty_seconds,accuracy_m\n')
        record = '' if empty else ('C,capture,2,2026-09-28T21:20:00+09:00,28.151,129.31,2026-09-28,'
                    'OWNER,' + species + ',OBSERVED_AT,0,0\n')
        _, cap = fixtures.fixture(self.root, qualified=True, empty=empty,
                                  capture_bytes=(columns + record).encode())
        if empty:
            fixtures.complete_coverage(self.root, cap)
        keys = [evidence_audit.unit_key(28.15, 129.3,
                    evidence_audit.timestamp('2026-09-28T21:00:00+09:00'))]
        if not empty:
            keys.append(evidence_audit.unit_key(28.151, 129.31,
                    evidence_audit.timestamp('2026-09-28T21:20:00+09:00')))
        original = fx.fixture.rows[0]
        rows = []
        for index, (cx, cy, window) in enumerate(keys):
            row = dict(original, row_id='template-' + str(index), night=fixtures.NIGHT,
                cell_x=cx, cell_y=cy, window_start_jst=window,
                source_refs=[cap['path'], 'features/road-source.txt'], outcome_source_ref=cap['path'],
                capture_event_ids=[] if empty else ['caller-invented-id-' + str(index)],
                label_available_at=fixtures.VERIFIED, audit_available_at=fixtures.VERIFIED,
                label=0 if empty else 1, observation='observed_negative' if empty else 'capture_observed')
            rows.append(row)
        fx.fixture.rows = rows
        fx.fixture.corpus['rows'] = rows
        fx.fixture.corpus['source_manifest'] = [s for s in fx.fixture.corpus['source_manifest']
                                               if s['role'] == 'feature']
        fx.fixture.add_source(cap['path'], (self.root / cap['path']).read_bytes(), fixtures.VERIFIED, 'label')
        if negative_proofs:
            for row in rows:
                fx.fixture.add_negative_proofs(row)
        fx.fixture.publish()
        fx.build_manifest()
        self.fx = fx
        return dict(feature_corpus_ref=fx.manifest['corpus']['ref'], strict_manifest_ref=fx.ref,
                    heldout_night='2030-01-02', fit_cutoff='2030-01-01T19:00:00+09:00',
                    forecast_cutoff='2030-01-02T18:00:00+09:00')

    def test_complete_existing_components_call_real_g0_and_ignore_caller_labels(self):
        result = self.call(**self.components())
        receipt = result['receipt']
        self.assertEqual(receipt['status'], 'DECLARATION_MATERIALIZED')
        self.assertEqual(receipt['declared_training_units'], 1)
        self.assertIsNone(receipt['eligible_training_units'])
        workspace = pathlib.Path(result['private_workspace'])
        manifest = json.loads((workspace / receipt['manifest_ref']['path']).read_bytes())
        corpus = json.loads((workspace / manifest['corpus']['ref']['path']).read_bytes())
        self.assertEqual(sorted(r['capture_event_ids'] for r in corpus['rows']), [[], ['C']])
        self.assertEqual(sorted(str(r['label']) for r in corpus['rows']), ['1', 'None'])
        self.assertFalse(any('caller-invented' in str(r) for r in corpus['rows']))
        self.assertFalse(receipt['production_authorized'])
        self.assertEqual(receipt['new_real_fits'], 0)
        self.assertEqual(result['selector_result']['receipt']['source_authentication'], 'NOT_ATTESTED')

    def test_non_habu_source_remains_unknown_despite_template_positive(self):
        result = self.call(**self.components(species='HIMEHABU'))
        self.assertEqual(result['receipt']['declared_training_units'], 0)
        self.assertTrue(all(r['label'] is None for r in result['observations']))

    def test_complete_typed_negative_scopes_use_existing_g0_rules(self):
        result = self.call(**self.components(empty=True, negative_proofs=True))
        self.assertEqual(result['receipt']['declared_training_units'], 1)
        self.assertEqual(result['receipt']['new_negative_rows'], 1)
        self.assertEqual(result['selector_result']['selection']['counts']['negatives'], 1)

    def test_new_audit_cannot_be_backdated_into_old_forecast_fold(self):
        options = self.components()
        options.update(heldout_night='2026-10-20', fit_cutoff='2026-10-19T19:00:00+09:00',
                       forecast_cutoff='2026-10-20T18:00:00+09:00')
        result = self.call(**options)
        self.assertEqual(result['receipt']['status'], 'BLOCKED')
        self.assertIsNone(result['receipt']['manifest_ref'])
        self.assertIn('G0_INPUTS_NOT_READY_OR_CAPABILITY_BLOCKED', result['receipt']['reason_codes'])

    def test_invalid_original_dag_usable_time_is_not_repaired_into_acceptance(self):
        options = self.components()
        self.fx.manifest['source_nodes'][0]['usable_at'] = '2020-01-01T00:00:00+09:00'
        self.fx.publish()
        options['strict_manifest_ref'] = self.fx.ref
        with self.assertRaises(ValueError):
            self.call(**options)

    def test_duplicate_physical_feature_rows_fail_without_completed_receipt(self):
        options = self.components()
        clone = dict(self.fx.fixture.rows[0], row_id='distinct-id-same-physical-unit')
        self.fx.fixture.rows.append(clone)
        self.fx.fixture.publish()
        self.fx.build_manifest()
        options.update(feature_corpus_ref=self.fx.manifest['corpus']['ref'], strict_manifest_ref=self.fx.ref)
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_FEATURE_UNIT'):
            self.call(**options)
        self.assertFalse(any(p.name == 'receipt.json' for p in self.output.rglob('*')))

    def test_template_hash_tampering_is_rejected(self):
        options = self.components()
        (self.root / options['feature_corpus_ref']['path']).write_bytes(b'{}')
        with self.assertRaises(ValueError):
            self.call(**options)

    def test_actual_record_time_uncertainty_spanning_windows_remains_unknown(self):
        fx = g0_fixtures.TrainingSourceContractTests()
        fx.setUp()
        self.addCleanup(fx.doCleanups)
        self.root = fx.root
        self.output = fx.fixture.work / 'uncertain-materialized'
        raw = (b'event_id,event_type,event_count,datetime_jst,latitude,longitude,operational_date,'
               b'owner_role,species,time_semantics,uncertainty_seconds,accuracy_m\n'
               b'C,capture,2,2026-09-28T21:20:00+09:00,28.151,129.31,2026-09-28,'
               b'OWNER,HABU,OBSERVED_AT,1,0\n')
        fixtures.fixture(self.root, qualified=True, capture_bytes=raw)
        result = self.call()
        self.assertTrue(all(r['label'] is None for r in result['observations']))
        self.assertEqual([r['capture_event_ids'] for r in result['observations'] if r['capture_event_ids']], [['C']])

    def test_private_output_inside_source_is_rejected_before_native_audit(self):
        self.output = self.root / 'private-output'
        with patch.object(evidence_audit, 'audit_evidence', side_effect=AssertionError('must not read')):
            with self.assertRaises(ValueError):
                self.call()
        self.assertFalse(self.output.exists())

    def test_native_local_capacity_is_blocked_not_malformed_source(self):
        fixtures.fixture(self.root)
        with patch.object(evidence_audit, 'MAX_POINTS', 0):
            result = self.call()
        self.assertEqual(result['receipt']['status'], 'BLOCKED')
        self.assertIsNone(result['receipt']['manifest_ref'])

    def test_final_write_deadline_expiry_leaves_no_completed_receipt(self):
        fixtures.fixture(self.root)
        import materialize_private_g0_sources as module
        original_save = module._save
        def expires(output, relative, value, context, **kwargs):
            if relative.endswith('/receipt.json'):
                context.deadline = 0
            return original_save(output, relative, value, context, **kwargs)
        with patch.object(module, '_save', side_effect=expires):
            with self.assertRaises(TimeoutError):
                self.call()
        self.assertFalse(any(p.name == 'receipt.json' for p in self.output.rglob('*')))

    def test_completed_output_reports_final_actual_read_ledger(self):
        fixtures.fixture(self.root)
        result = self.call()
        before = result['receipt']['actual_read_bytes_before_completion_read']
        final = result['execution']['actual_read_bytes']
        self.assertEqual(final - before, result['receipt_ref']['size_bytes'] +
                         result['execution']['after_completion_read_bytes'])

    def test_shared_raw_ancestry_cannot_supply_independent_negative_proofs(self):
        options = self.components(empty=True, negative_proofs=True)
        fx = self.fx
        fx.fixture.add_source('evidence/common-origin.txt', b'synthetic shared original',
                              fixtures.VERIFIED, 'search_evidence')
        fx.fixture.publish()
        fx.build_manifest()
        common = next(n for n in fx.manifest['source_nodes'] if n['ref']['path'] == 'evidence/common-origin.txt')
        for node in fx.manifest['source_nodes']:
            if (node['source_role'] == 'label' or
                    node['source_role'] == 'search_evidence' and node['id'] != common['id']):
                node.update(source_kind='DERIVED', parents=[common['id']])
        fx.publish()
        options.update(feature_corpus_ref=fx.manifest['corpus']['ref'], strict_manifest_ref=fx.ref)
        result = self.call(**options)
        self.assertEqual(result['receipt']['new_negative_rows'], 0)
        self.assertEqual(result['receipt']['declared_training_units'], 0)

    def test_conflicting_alias_record_does_not_hide_behind_first_precise_source(self):
        raw = (b'event_id,event_type,event_count,datetime_jst,latitude,longitude,operational_date,'
               b'owner_role,species,time_semantics,uncertainty_seconds,accuracy_m\n'
               b'C,capture,2,2026-09-28T21:20:00+09:00,28.151,129.31,2026-09-28,'
               b'OWNER,HABU,OBSERVED_AT,0,0\n')
        fixtures.fixture(self.root, qualified=True, capture_bytes=raw)
        alias = self.root / 'data/processed/capture_events/z-alias.csv'
        alias.write_bytes(raw.replace(b'OWNER,HABU,', b'OTHER,HIMEHABU,'))
        result = self.call()
        captured = [r for r in result['observations'] if r['capture_event_ids']]
        self.assertEqual(captured[0]['capture_event_ids'], ['C'])
        self.assertIsNone(captured[0]['label'])

    def test_deadline_after_completion_write_removes_only_new_owned_receipt(self):
        fixtures.fixture(self.root)
        import materialize_private_g0_sources as module
        original_read = module.g0.G0ArtifactReader.read
        def expires(reader, ref, **options):
            if ref['path'].endswith('/receipt.json'):
                reader.context.deadline = 0
            return original_read(reader, ref, **options)
        with patch.object(module.g0.G0ArtifactReader, 'read', expires):
            with self.assertRaises(TimeoutError):
                self.call()
        self.assertFalse(any(p.name == 'receipt.json' for p in self.output.rglob('*')))

    def test_cli_existing_components_are_usable_and_stdout_is_aggregate_only(self):
        options = self.components()
        command = [sys.executable, '-B', '-X', 'utf8', str(ROOT / 'scripts/materialize_private_g0_sources.py'),
            '--root', str(self.root), '--output', str(self.output), '--night', fixtures.NIGHT,
            '--feature-corpus-ref', json.dumps(options['feature_corpus_ref']),
            '--strict-manifest-ref', json.dumps(options['strict_manifest_ref']),
            '--heldout-night', options['heldout_night'], '--fit-cutoff', options['fit_cutoff'],
            '--forecast-cutoff', options['forecast_cutoff']]
        completed = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        value = json.loads(completed.stdout)
        self.assertEqual(value['status'], 'DECLARATION_MATERIALIZED')
        self.assertNotIn(str(self.root), completed.stdout + completed.stderr)
        self.assertNotIn('129.31', completed.stdout + completed.stderr)
        self.assertNotIn('caller-invented', completed.stdout + completed.stderr)

    def test_foreign_reference_types_fail_before_callbacks_or_native_audit(self):
        calls = []
        class Foreign(str):
            def startswith(self, *args):
                calls.append('callback')
                raise AssertionError('foreign reference callback')
        ref = dict(path=Foreign('data/processed/observations.json'), sha256='a' * 64, size_bytes=1)
        with patch.object(evidence_audit, 'audit_evidence', side_effect=AssertionError('must not audit')):
            with self.assertRaises(ValueError):
                self.call(feature_corpus_ref=ref)
        self.assertEqual(calls, [])

    def test_supplied_parent_budget_keeps_prior_charges_and_absolute_deadline(self):
        fixtures.fixture(self.root)
        from prospective_inputs import ProspectiveReadContext
        parent = ProspectiveReadContext(60, 8 * 1024 * 1024)
        parent.account(123)
        deadline, capacity = parent.deadline, parent.max_bytes
        result = self.call(_read_context=parent)
        self.assertEqual(parent.deadline, deadline)
        self.assertEqual(parent.max_bytes, capacity)
        self.assertGreater(parent.bytes_read, 123)
        self.assertEqual(result['execution']['actual_read_bytes'], parent.bytes_read)

    def test_submicrosecond_cutoff_is_rejected_without_rounding(self):
        fixtures.fixture(self.root)
        with self.assertRaisesRegex(ValueError, 'UNREPRESENTABLE_TIME'):
            self.call(fit_cutoff='2030-01-01T19:00:00.0000001+09:00')

    def test_comma_submicrosecond_cutoff_is_not_silently_truncated(self):
        options = self.components()
        options['fit_cutoff'] = '2030-01-01T19:00:00,0000001+09:00'
        with self.assertRaisesRegex(ValueError, 'UNREPRESENTABLE_TIME'):
            self.call(**options)

    def test_foreign_metaclass_budget_does_not_execute_equality(self):
        calls = []
        class Meta(type):
            def __eq__(cls, other):
                calls.append('equality')
                return False
        class Foreign(metaclass=Meta):
            pass
        with self.assertRaises(ValueError):
            self.call(budget_seconds=Foreign())
        self.assertEqual(calls, [])

    def test_huge_integer_budget_is_a_bounded_validation_error(self):
        with self.assertRaises(ValueError):
            self.call(budget_seconds=10 ** 10000)

    def test_late_workspace_mutation_cannot_publish_success(self):
        options = self.components()
        import materialize_private_g0_sources as module
        original_save = module._save
        def mutates(output, relative, value, context, **kwargs):
            result = original_save(output, relative, value, context, **kwargs)
            if relative.endswith('/observations.json'):
                targets = [p for p in self.output.rglob('*.json')
                           if '/data/processed/materialized/' in p.as_posix()]
                self.assertEqual(len(targets), 1)
                targets[0].write_bytes(targets[0].read_bytes() + b' ')
            return result
        with patch.object(module, '_save', side_effect=mutates):
            with self.assertRaises(ValueError):
                self.call(**options)
        self.assertFalse(any(p.name == 'receipt.json' for p in self.output.rglob('*')))

    def test_late_native_audit_mutation_cannot_publish_success(self):
        options = self.components()
        import materialize_private_g0_sources as module
        original_save = module._save
        def mutates(output, relative, value, context, **kwargs):
            result = original_save(output, relative, value, context, **kwargs)
            if relative.endswith('/observations.json'):
                target = next(self.output.rglob('audit.json'))
                target.write_bytes(target.read_bytes() + b' ')
            return result
        with patch.object(module, '_save', side_effect=mutates):
            with self.assertRaises(ValueError):
                self.call(**options)
        self.assertFalse(any(p.name == 'receipt.json' for p in self.output.rglob('*')))

    def test_materialized_workspace_composes_with_existing_preparation_same_budget(self):
        options = self.components()
        from prospective_inputs import ProspectiveReadContext
        from habu_qualified_fit_cycle import prepare_source
        parent = ProspectiveReadContext(60, 32 * 1024 * 1024)
        parent.account(321)
        deadline, maximum = parent.deadline, parent.max_bytes
        result = self.call(**options, _read_context=parent)
        receipt = result['receipt']
        self.assertEqual(len(receipt['research_refs']), 2)
        workspace = pathlib.Path(result['private_workspace'])
        for ref in receipt['research_refs']:
            raw = (workspace / ref['path']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), ref['sha256'])
        prior_read = parent.bytes_read
        prepared = prepare_source(workspace, self.fx.fixture.work / 'portable-private',
            heldout_night=options['heldout_night'], fit_cutoff=options['fit_cutoff'],
            forecast_cutoff=options['forecast_cutoff'],
            research_refs=tuple(receipt['research_refs']),
            manifest_path=receipt['manifest_ref']['path'], manifest_sha256=receipt['manifest_ref']['sha256'],
            feature_sha256=receipt['feature_definition_sha256'], budget_seconds=300, _read_context=parent)
        self.assertEqual(prepared['receipt']['status'], 'DECLARATION_PREPARED')
        self.assertEqual(prepared['receipt']['declared_training_units'], 1)
        self.assertEqual(parent.deadline, deadline)
        self.assertEqual(parent.max_bytes, maximum)
        self.assertGreater(parent.bytes_read, prior_read)
        self.assertFalse(prepared['receipt']['scientific_fit_authorized'])


if __name__ == '__main__':
    unittest.main()
