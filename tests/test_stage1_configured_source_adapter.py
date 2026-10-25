"""Synthetic configured source controls; no field evidence or parent opt-in."""
import copy
import inspect
import itertools
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from master_contracts import digest
from prospective_inputs import ProspectiveReadContext, _time
from prospective_inputs import InputCapacityError
from test_g0_forecast_contract import NIGHT, CUTOFF
import test_stage1_source_adapter as old
import test_research_pdca_adapter as parents
from evaluation import stage1_source_adapter as adapter


class ConfiguredSourceFixture:
    """Actual strict loaders and full-seven synthetic source declarations."""
    def __init__(self, case):
        self.case = parents.ResearchConfigV3Tests()
        self.case.setUp()
        case.addCleanup(self.case.doCleanups)
        self.case.full_seven_fixture()
        self.root, self.parent = self.case.root, self.case.parent
        self.source = old.SourceFixture(self.parent)
        self.config = self.case.source.config
        self.publish()

    def publish(self):
        self.source.manifest.update(schema_version='habu-stage1-source-contract-v2',
            candidate_config_sha256=digest(self.config),
            feature_definition_sha256=self.parent.request['feature_definition_sha256'])
        self.source.manifest_only()

    def projections(self):
        import g0_forecast_contract as g0
        import g0_training_source_contract as train
        import research_model_adapter as models
        context = ProspectiveReadContext(300, 2 * 1024**3)
        request = self.parent.request
        selected = train.select_g0_training_rows(self.root, request['training_manifest'], NIGHT,
            request['fit_cutoff'], CUTOFF, expected_feature_definition_sha256=request['feature_definition_sha256'],
            _read_context=context)
        forecast = g0.load_g0_forecast_rows(self.root, request['forecast_manifest'], NIGHT,
            _time(request['forecast_as_of']), expected_feature_definition_sha256=request['feature_definition_sha256'],
            _read_context=context)
        prepared = models.prepare_research_candidates_v2(selected['selection'], forecast['rows'],
            candidate_config=self.config, expected_config_sha256=digest(self.config), cutoff_time=CUTOFF,
            joined_universe_sha256=forecast['receipt']['canonical_joined_rows_sha256'],
            feature_definition_sha256=request['feature_definition_sha256'],
            budget_seconds=context.remaining_seconds, check=context.check)
        return context, forecast, prepared

    def evaluate(self, values=None, **kw):
        context, forecast, prepared = values or self.projections()
        return adapter.evaluate_stage1_sources_v2(self.root, self.source.ref, forecast, prepared,
            candidate_config=self.config, expected_config_sha256=digest(self.config),
            feature_definition_sha256=self.parent.request['feature_definition_sha256'], context=context, **kw)


def reseal(prepared):
    for candidate in prepared['candidates']:
        model, prediction = candidate['model'], candidate['prediction']
        model['model_sha256'] = digest({k:v for k,v in model.items() if k != 'model_sha256'})
        prediction['model_sha256'] = model['model_sha256']
        prediction['prediction_sha256'] = digest({k:v for k,v in prediction.items() if k != 'prediction_sha256'})
        candidate.update(model_sha256=model['model_sha256'], prediction_sha256=prediction['prediction_sha256'])
    prepared['receipt_sha256'] = digest({k:v for k,v in prepared.items() if k != 'receipt_sha256'})


class ConfiguredStage1SourceTests(unittest.TestCase):
    def setUp(self):
        self.f = ConfiguredSourceFixture(self)

    def test_additive_api_complete_ledger_preserves_two_count_and_outside_fn(self):
        self.assertTrue(callable(getattr(adapter, 'evaluate_stage1_sources_v2', None)), 'Missing additive configured source API')
        result = self.f.evaluate()
        self.assertEqual(result['source_contract_version'], 'habu-stage1-source-contract-v2')
        self.assertEqual(result['candidate_ids'], self.f.config['candidate_ids'])
        self.assertEqual(result['source_summary'], dict(capture_events=2, individuals=3))
        self.assertEqual(result['per_night'][0]['outside_universe_individuals'], 1)
        for item in result['pooled'].values():
            self.assertEqual((item['numerator'], item['denominator']), (2, 3))
        self.assertEqual(result['candidate_config_sha256'], digest(self.f.config))
        self.assertEqual(result['source_authentication'], 'NOT_ATTESTED')
        self.assertEqual(result['source_consistency'], 'DECLARED_CONSISTENCY_ONLY')
        for name in ('selection_authorized', 'promotion_authorized', 'confirmation_authorized',
                     'official_threshold_pass', 'production_authorized'):
            self.assertIs(result[name], False)

    def test_all_six_configured_orders_keep_exact_native_lineage_and_b1_recipe(self):
        from evaluation import full_ledger_stage1 as pure
        for optional in itertools.permutations(('HB-A0', 'HB-B1', 'HB-A1'), 2):
            self.f.config['candidate_ids'] = ['uniform', *optional]
            recipe = self.f.case.source.config.get('hba1_recipe')
            if 'HB-A1' not in optional:
                self.saved_recipe = recipe or self.saved_recipe
                self.f.config['hba1_recipe'] = None
            elif recipe is None:
                self.f.config['hba1_recipe'] = self.saved_recipe
            self.f.publish()
            values = self.f.projections()
            original = copy.deepcopy(values[2])
            captured = []
            actual = pure.evaluate_full_ledger_stage1_v2
            def capture(u, s, l, **kw):
                captured.append(copy.deepcopy(s))
                return actual(u, s, l, **kw)
            with patch.object(pure, 'evaluate_full_ledger_stage1_v2', side_effect=capture):
                result = self.f.evaluate(values)
            self.assertEqual(values[2], original)
            self.assertEqual(result['candidate_ids'], ['uniform', *optional])
            projection = captured[0]
            self.assertEqual(projection['schema_version'], 'habu-stage1-scores-v2')
            for source, score in zip(original['candidates'], projection['candidates']):
                self.assertEqual((score['model_sha256'], score['prediction_sha256']),
                                 (source['model_sha256'], source['prediction_sha256']))
                expected = digest(self.f.config['hba1_recipe']) if score['candidate_id'] == 'HB-A1' else None
                self.assertEqual(score['recipe_sha256'], expected)
                if score['candidate_id'] == 'HB-B1':
                    self.assertIsInstance(source['model']['recipe_sha256'], str)
                    self.assertEqual(score['score_semantics'], 'MEAN_NATIVE_UNIT_RANK_SCORE')

    def test_invalid_prepared_binding_rejected_before_any_evaluation_open(self):
        baseline = self.f.projections()
        mutations = [
            lambda p:p.update(candidate_config_sha256='a'*64),
            lambda p:p.update(feature_definition_sha256='b'*64),
            lambda p:p.update(candidate_ids=['uniform', 'HB-A1', 'HB-A0']),
            lambda p:p['candidates'][-1].update(training_rows_sha256='c'*64),
            lambda p:p['candidates'][-1]['model'].update(recipe_sha256='d'*64),
            lambda p:p['candidates'][-1]['prediction'].update(recipe_sha256='e'*64),
            lambda p:p['candidates'][-1]['model'].update(training_rows_sha256='f'*64),
            lambda p:p['candidates'][-1]['prediction'].update(production_activation_authorized=True),
        ]
        for mutation in mutations:
            values = (baseline[0], copy.deepcopy(baseline[1]), copy.deepcopy(baseline[2]))
            mutation(values[2]); reseal(values[2])
            with patch.object(Path, 'open', side_effect=AssertionError('Evaluation opened before identity validation')):
                with self.assertRaises(ValueError): self.f.evaluate(values)

    def test_manifest_config_identity_must_match_before_payload_read(self):
        for key in ('candidate_config_sha256', 'feature_definition_sha256'):
            self.f.source.manifest[key] = 'a'*64
            self.f.source.manifest_only()
            values = self.f.projections()
            actual = Path.open
            def opening(path, *args, **kw):
                if path.name != 'manifest.json': raise AssertionError('Payload opened before manifest config binding')
                return actual(path, *args, **kw)
            with patch.object(Path, 'open', new=opening):
                with self.assertRaises(ValueError): self.f.evaluate(values)
            self.f.publish()

    def test_unknown_missing_and_noncomplete_keep_empty_metrics(self):
        for mode in ('UNKNOWN', 'INCOMPLETE', 'missing_scope', 'missing_file'):
            if mode in ('UNKNOWN', 'INCOMPLETE'):
                self.f.source.coverage['declaration'] = mode
                self.f.source.publish(); self.f.publish()
            elif mode == 'missing_scope':
                self.f.source.manifest['scope_id'] = None
                self.f.source.nodes.pop('scope')
                self.f.publish()
            else:
                (self.f.root / self.f.source.nodes['individuals']['ref']['path']).unlink()
            result = self.f.evaluate()
            self.assertEqual(result['status'], 'NEED_MORE_DATA')
            self.assertEqual((result['per_night'], result['pooled'], result['paired_uncertainty']), ([], {}, {}))

    def test_missing_scope_does_not_hide_known_source_or_causal_contradiction(self):
        self.f.source.manifest['scope_id'] = None
        self.f.source.nodes.pop('scope')
        self.f.source.nodes['captures']['readiness']['source_received_at'] = old.PRIOR
        self.f.publish()
        with self.assertRaisesRegex(ValueError, 'readiness precedes'): self.f.evaluate()

    def test_unknown_still_rejects_duplicate_or_wrong_individual_count(self):
        self.f.source.coverage['declaration'] = 'UNKNOWN'
        self.f.source.individuals.pop()
        self.f.source.publish(); self.f.publish()
        with self.assertRaisesRegex(ValueError, 'count'): self.f.evaluate()

    def test_config_budget_is_combined_and_precedes_first_source_open(self):
        from evaluation import full_ledger_stage1 as pure
        values = self.f.projections()
        with patch.object(pure, 'MAX_JSON_BYTES', 1024), patch.object(Path, 'open', side_effect=AssertionError('source read before cap')):
            with self.assertRaises(InputCapacityError) as caught: self.f.evaluate(values)
        self.assertIn('CAPACITY_BLOCKED', str(caught.exception))

    def test_expired_shared_context_never_opens_evaluation_sources(self):
        values = self.f.projections()
        values[0].deadline = 0
        with patch.object(Path, 'open', side_effect=AssertionError('expired source open')):
            with self.assertRaises(TimeoutError): self.f.evaluate(values)

    def test_existing_parent_v3_nonlegacy_dispatch_remains_blocked_and_unread(self):
        self.f.parent.request.update(schema_version='habu-research-model-request-v3',
            candidate_config_manifest=self.f.case.source.ref, stage1_manifest=self.f.source.ref)
        self.f.parent.publish()
        with patch.object(adapter, 'evaluate_stage1_sources_v2', side_effect=AssertionError('implicit parent opt-in')):
            result = self.f.parent.call()
        self.assertEqual(result['stage1_dispatch']['status'], 'IMPLEMENTATION_BLOCKED')
        self.assertEqual(len(result['candidates']), 3)
        self.assertEqual(len(result['replay']), 1)

    def test_stale_hash_or_wrong_configuration_precedes_manifest_read(self):
        values = self.f.projections()
        actual = copy.deepcopy(self.f.config)
        for mode in ('hash', 'order', 'recipe', 'feature'):
            config = copy.deepcopy(actual)
            if mode == 'order': config['candidate_ids'].reverse()
            if mode == 'recipe': config['hba1_recipe']['feature_mask'][0] = False
            if mode == 'feature': config['feature_definition_sha256'] = 'a'*64
            with patch.object(Path, 'open', side_effect=AssertionError('invalid config opened source')):
                with self.assertRaises(ValueError):
                    adapter.evaluate_stage1_sources_v2(self.f.root, self.f.source.ref, values[1], values[2],
                        candidate_config=config, expected_config_sha256='b'*64 if mode == 'hash' else digest(config),
                        feature_definition_sha256=self.f.parent.request['feature_definition_sha256'], context=values[0])

    def test_actual_combined_byte_cap_is_not_three_separate_caps(self):
        from evaluation import full_ledger_stage1 as pure
        from master_contracts import canonical_bytes
        values = self.f.projections()
        parts = (self.f.config, values[1], values[2])
        cap = max(len(canonical_bytes(part)) for part in parts) + 1
        self.assertGreater(len(canonical_bytes(list(parts))), cap)
        with patch.object(pure, 'MAX_JSON_BYTES', cap), patch.object(Path, 'open', side_effect=AssertionError('combined cap opened source')):
            with self.assertRaises(InputCapacityError): self.f.evaluate(values)

    def test_no_new_clock_and_actual_reads_charge_existing_context(self):
        values = self.f.projections()
        before, original_deadline = values[0].bytes_read, values[0].deadline
        result = self.f.evaluate(values)
        self.assertEqual(values[0].deadline, original_deadline)
        self.assertGreater(values[0].bytes_read, before)
        self.assertEqual(result['source_receipt']['actual_read_bytes'], values[0].bytes_read)
        values = self.f.projections()
        values[0].max_bytes = values[0].bytes_read + self.f.source.ref['size_bytes'] + 5
        with self.assertRaises(InputCapacityError): self.f.evaluate(values)

    def test_sealed_source_preflight_rejects_all_payload_reads(self):
        values = self.f.projections()
        self.f.source.nodes['individuals']['ref']['path'] = 'evidence/sealed/individuals.csv'
        self.f.publish()
        actual = Path.open
        def opening(path, *a, **kw):
            if path.name != 'manifest.json': raise AssertionError('Payload opened before all-path preflight')
            return actual(path, *a, **kw)
        with patch.object(Path, 'open', new=opening):
            with self.assertRaisesRegex(ValueError, 'namespace|reveal'): self.f.evaluate(values)

    def test_final_source_rescan_detects_mutation_after_pure_evaluation(self):
        from evaluation import full_ledger_stage1 as pure
        actual = pure.evaluate_full_ledger_stage1_v2
        def change(*a, **kw):
            value = actual(*a, **kw)
            path = self.f.root / self.f.source.nodes['captures']['ref']['path']
            path.write_bytes(path.read_bytes() + b'changed')
            return value
        with patch.object(pure, 'evaluate_full_ledger_stage1_v2', side_effect=change):
            with self.assertRaises(ValueError): self.f.evaluate()

    def test_shared_expiry_during_pure_or_final_seal_never_returns_metrics(self):
        from evaluation import full_ledger_stage1 as pure
        values = self.f.projections()
        actual = pure.evaluate_full_ledger_stage1_v2
        def expire(*a, **kw):
            result = actual(*a, **kw); values[0].deadline = 0; return result
        with patch.object(pure, 'evaluate_full_ledger_stage1_v2', side_effect=expire):
            with self.assertRaises(TimeoutError): self.f.evaluate(values)
        values = self.f.projections()
        seal = pure._finish
        def expire_seal(result, check):
            if 'source_contract_version' in result: values[0].deadline = 0
            return seal(result, check)
        with patch.object(pure, '_finish', side_effect=expire_seal):
            with self.assertRaises(TimeoutError): self.f.evaluate(values)

    def test_actual_mean_semantics_remain_statistics_mean(self):
        from statistics import mean
        values = self.f.projections()
        prepared = values[2]
        for candidate in prepared['candidates']:
            if candidate['candidate_id'] == 'HB-A0':
                for unit, score in zip(candidate['prediction']['unit_predictions'], (.1, .1, .1, .3)):
                    unit['spatial_score'] = score
        reseal(prepared)
        captured = []
        actual = adapter.pure.evaluate_full_ledger_stage1_v2
        def capture(u, scores, ledger, **kw):
            captured.append(scores); return actual(u, scores, ledger, **kw)
        with patch.object(adapter.pure, 'evaluate_full_ledger_stage1_v2', side_effect=capture): self.f.evaluate(values)
        a0 = next(c for c in captured[0]['candidates'] if c['candidate_id'] == 'HB-A0')
        self.assertEqual(list(a0['scores'][NIGHT].values()), [mean((.1,.1,.1,.3))])

    def test_source_manifest_exact_versioned_fields_and_no_v1_downgrade(self):
        for mode in ('extra', 'absent', 'v1'):
            baseline = copy.deepcopy(self.f.source.manifest)
            if mode == 'extra': self.f.source.manifest['extra'] = None
            elif mode == 'absent': self.f.source.manifest.pop('candidate_config_sha256')
            else: self.f.source.manifest['schema_version'] = adapter.VERSION
            self.f.source.manifest_only()
            with self.assertRaises(ValueError): self.f.evaluate()
            self.f.source.manifest = baseline
            self.f.publish()

    def test_rehashed_prepared_chronology_and_forecast_counts_must_bind(self):
        baseline = self.f.projections()
        for changes in (dict(heldout_night='2026-10-13'), dict(forecast_units=True),
                        dict(fit_cutoff='2026-10-15T07:00:00+09:00')):
            values = baseline[0], baseline[1], copy.deepcopy(baseline[2])
            values[2].update(changes); reseal(values[2])
            # Check a legacy pair too; the common v2 metadata is not A1-only.
            with patch.object(Path, 'open', side_effect=AssertionError('invalid prepared metadata opened source')):
                with self.assertRaises(ValueError): self.f.evaluate(values)

    def test_malformed_owned_receipt_and_model_are_valueerror_before_io(self):
        baseline = self.f.projections()
        for mode in ('receipt', 'model'):
            values = baseline[0], copy.deepcopy(baseline[1]), copy.deepcopy(baseline[2])
            if mode == 'receipt': values[1]['receipt'] = None
            else:
                values[2]['candidates'][-1]['model'] = None
                values[2]['receipt_sha256'] = digest({k:v for k,v in values[2].items() if k != 'receipt_sha256'})
            with patch.object(Path, 'open', side_effect=AssertionError('malformed snapshot opened source')):
                with self.assertRaises(ValueError): self.f.evaluate(values)

    def test_real_link_rejected_before_reading_external_payload(self):
        values = self.f.projections()
        external, link = self.f.root / 'external-sentinel', self.f.root / 'evidence' / 'linked'
        external.mkdir()
        sentinel = external / 'individuals.csv'
        sentinel.write_bytes(old.csv_bytes(self.f.source.individuals))
        ref = self.f.source.nodes['individuals']['ref']
        ref['path'] = 'evidence/linked/individuals.csv'
        self.f.source.coverage['individuals_ref'] = copy.deepcopy(ref)
        self.f.source.node('coverage', old.canonical_bytes(self.f.source.coverage))
        self.f.publish()
        opened = []
        actual = Path.open
        def opening(path, *a, **kw):
            if path == link / 'individuals.csv' or path == sentinel: opened.append(path)
            return actual(path, *a, **kw)
        try:
            if os.name == 'nt':
                subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(external)],
                               check=True, capture_output=True)
                self.assertTrue(link.is_junction())
            else:
                link.symlink_to(external, target_is_directory=True)
                self.assertTrue(link.is_symlink())
            with patch.object(Path, 'open', new=opening):
                with self.assertRaises(ValueError): self.f.evaluate(values)
            self.assertEqual(opened, [])
            self.assertEqual(sentinel.read_bytes(), old.csv_bytes(self.f.source.individuals))
        finally:
            # Remove the actual link itself before TemporaryDirectory cleanup.
            if os.name == 'nt' and link.is_junction(): link.rmdir()
            elif link.is_symlink(): link.unlink()

    def test_actual_sept28_five_events_six_individuals_still_have_no_complete_scope(self):
        source = self.f.source
        stamp = '2026-10-25T18:00:00+09:00'
        for role, path in [('captures', 'data/processed/capture_events/2026/2026-09-28.csv'),
                           ('individuals', 'data/processed/individuals/2026/2026-09-28.csv')]:
            native = subprocess.check_output(['git', 'show', 'HEAD:' + path], cwd=ROOT)
            source.node(role, native, stamp)
        source.manifest['scope_id'] = source.manifest['coverage_id'] = None
        source.nodes.pop('scope'); source.nodes.pop('coverage')
        source.manifest.update(evaluation_as_of='2026-10-25T19:00:00+09:00',
            readiness=source.ready(stamp), usable_at=stamp)
        self.f.publish()
        result = self.f.evaluate()
        self.assertEqual(result['status'], 'NEED_MORE_DATA')
        self.assertEqual(result['source_summary'], dict(capture_events=5, individuals=6))
        self.assertEqual((result['per_night'], result['pooled'], result['paired_uncertainty']), ([], {}, {}))

    def test_rehashed_changed_b1_native_recipe_is_not_a_new_configured_recipe(self):
        self.f.config.update(candidate_ids=['uniform','HB-A0','HB-B1'], hba1_recipe=None)
        self.f.publish()
        values = self.f.projections()
        model = values[2]['candidates'][-1]['model']
        model['recipe']['parent_strength'] = 5
        model['recipe_sha256'] = digest(model['recipe'])
        reseal(values[2])
        with patch.object(Path, 'open', side_effect=AssertionError('changed native recipe opened source')):
            with self.assertRaises(ValueError): self.f.evaluate(values)


class LegacyWholeArtifactTests(unittest.TestCase):
    # Collected from unedited PR107+reviewed pure/F source merge 70b3fff.
    # Native source ffc0f686481f822b1409fef5645c72e1ef68f41c279af1fdf4205773822b9037.
    # Full external oracle SHA dc6add19bed7b92bc7d3c08c07280551ec69af910321eefd4e8813427290b79c.
    ORACLES = {
        'complete': ('b0056b3d1eb8b496b769a33a92b0dd10df971fed15f4041176cbfe83dbdd02d1', 126056),
        'unknown': ('007d47cec2c2784f54268eec38dac96bc21ebd3dd340d59feae5fa4c0f062f1d', 126036),
        'missing_scope': ('6cc730ed1697ea0b663185a654cf4f78b4465c04d21c8903a3bb37bed3b5a0e1', 96998),
        'missing_coverage': ('aaaa65a4e314bda46ff5058ab24cb3099798a2d98e6ed374f8042419e48ce6f5', 123816),
    }

    def test_v1_signature_rejects_private_configuration(self):
        self.assertEqual(str(inspect.signature(adapter.evaluate_stage1_sources)),
                         '(root, manifest_ref, forecast, prepared, *, context)')

    def test_four_original_whole_receipts_projections_and_readbytes_are_exact(self):
        native = subprocess.check_output(['git', 'show', 'HEAD:protocols/development/g0-policy-v1.json'], cwd=ROOT)
        actual = Path.read_bytes
        def reading(path):
            if path == ROOT / 'protocols/development/g0-policy-v1.json': return native
            return actual(path)
        for mode, (expected, final_bytes) in self.ORACLES.items():
            with patch.object(Path, 'read_bytes', new=reading):
                fixture = old.Stage1SourceAdapterTests(); fixture.setUp()
            try:
                source = fixture.fixture
                if mode == 'unknown':
                    source.coverage['declaration'] = 'UNKNOWN'; source.publish()
                elif mode.startswith('missing_'):
                    role = mode.removeprefix('missing_')
                    source.manifest[role + '_id'] = None; source.nodes.pop(role); source.manifest_only()
                context, forecast, prepared = fixture.projections()
                self.assertEqual(context.bytes_read, 90654)
                result = adapter.evaluate_stage1_sources(fixture.root, source.ref, forecast, prepared, context=context)
                self.assertEqual(digest(result), expected, mode)
                self.assertEqual(context.bytes_read, final_bytes, mode)
            finally: fixture.doCleanups()


if __name__ == '__main__': unittest.main()
