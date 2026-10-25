"""Hermetic declaration controls; synthetic completeness is not source authentication."""
import copy
import csv
import io
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from master_contracts import canonical_bytes, digest
from prospective_inputs import ProspectiveReadContext
from test_g0_forecast_contract import NIGHT, CUTOFF, base_ref
import test_research_pdca_adapter as parent_fixtures
from prospective_inputs import _time

READY = '2026-10-15T08:00:00+09:00'
PRIOR = '2026-10-14T17:00:00+09:00'


def csv_bytes(rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


class SourceFixture:
    """Public test helper for independent hostile probes; no actual records invented."""
    def __init__(self, parent):
        self.parent, self.root = parent, parent.root
        self.scope = dict(schema_version='habu-stage1-scope-source-v1', operational_night=NIGHT,
            cutoff_time=CUTOFF, horizon_start=NIGHT + 'T19:00:00+09:00',
            horizon_end=NIGHT + 'T19:20:00+09:00',
            scope=dict(crs='EPSG:32652', bbox_utm=[390000, 2990000, 450000, 3010000]))
        self.captures = []
        self.individuals = []
        for ident, x, count in [('inside', 400050, 2), ('outside', 430050, 1)]:
            stamp = NIGHT + 'T19:03:00+09:00'
            self.captures.append(dict(event_id=ident, operational_date=NIGHT, event_time_local=stamp,
                event_type='capture', event_count=str(count), utm_x_m=str(x), utm_y_m='3000050'))
            for i in range(1, count + 1):
                self.individuals.append(dict(individual_id=f'{ident}-{i}', event_id=ident,
                    individual_index=str(i), operational_date=NIGHT, event_time_local=stamp))
        self.nodes = {}
        self.coverage = dict(schema_version='habu-stage1-coverage-source-v1', declaration='DECLARED_COMPLETE',
            operational_night=NIGHT, scope_sha256=digest(self.scope['scope']),
            horizon_start=self.scope['horizon_start'], horizon_end=self.scope['horizon_end'],
            captures_ref=None, individuals_ref=None,
            event_ids=['inside', 'outside'], individual_ids=['inside-1', 'inside-2', 'outside-1'])
        self.manifest = dict(schema_version='habu-stage1-source-contract-v1', purpose='DEVELOPMENT_EVALUATION_ONLY',
            operational_night=NIGHT, evaluation_as_of='2026-10-15T09:00:00+09:00',
            forecast_manifest_sha256=parent.forecast.ref['sha256'], joined_universe_sha256=None,
            scope_id='scope', captures_id='captures', individuals_id='individuals', coverage_id='coverage',
            source_nodes=[], readiness=self.ready(READY), usable_at=READY)
        # The strict forecast loader is used, never a made-up joined digest.
        import g0_forecast_contract as g0
        loaded = g0.load_g0_forecast_rows(self.root, parent.forecast.ref, NIGHT,
            _time(parent.request['forecast_as_of']), expected_feature_definition_sha256=parent.request['feature_definition_sha256'])
        self.manifest['joined_universe_sha256'] = loaded['receipt']['canonical_joined_rows_sha256']
        self.publish()

    @staticmethod
    def ready(stamp):
        from prospective_inputs import READINESS_FIELDS
        return dict.fromkeys(READINESS_FIELDS, stamp)

    def node(self, role, raw, stamp=READY):
        ref = base_ref(self.root, f'evidence/stage1/{role}.{"csv" if role in ("captures", "individuals") else "json"}', raw)
        self.nodes[role] = dict(id=role, ref=ref, source_kind='RAW', role=role, parents=[],
                                readiness=self.ready(stamp), usable_at=stamp)
        return ref

    def publish(self):
        self.node('scope', canonical_bytes(self.scope), PRIOR)
        self.coverage['captures_ref'] = self.node('captures', csv_bytes(self.captures))
        self.coverage['individuals_ref'] = self.node('individuals', csv_bytes(self.individuals))
        self.node('coverage', canonical_bytes(self.coverage))
        return self.manifest_only()

    def manifest_only(self):
        self.manifest['source_nodes'] = list(self.nodes.values())
        self.ref = base_ref(self.root, 'evidence/stage1/manifest.json', canonical_bytes(self.manifest))
        self.parent.request.update(schema_version='habu-research-model-request-v2', stage1_manifest=self.ref)
        self.parent.publish()
        return self.ref


class Stage1SourceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.parent = parent_fixtures.ResearchPDCAAdapterTests()
        self.parent.setUp()
        self.addCleanup(self.parent.doCleanups)
        self.root = self.parent.root
        self.fixture = SourceFixture(self.parent)

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
            _time(request['forecast_as_of']), expected_feature_definition_sha256=request['feature_definition_sha256'], _read_context=context)
        prepared = models.prepare_research_candidates(selected['selection'], forecast['rows'], cutoff_time=CUTOFF,
            joined_universe_sha256=forecast['receipt']['canonical_joined_rows_sha256'])
        return context, forecast, prepared

    def evaluate(self, **options):
        from evaluation.stage1_source_adapter import evaluate_stage1_sources
        context, forecast, prepared = self.projections()
        return evaluate_stage1_sources(self.root, self.fixture.ref, forecast, prepared, context=context, **options)

    def test_complete_source_ledger_keeps_outside_fn_and_two_existing_individuals(self):
        result = self.evaluate()
        self.assertEqual(result['status'], 'DIAGNOSTIC_ONLY')
        self.assertEqual(result['per_night'][0]['denominator'], 3)
        self.assertEqual(result['per_night'][0]['denominator_events'], 2)
        self.assertEqual(result['per_night'][0]['outside_universe_individuals'], 1)
        for ident in ('uniform', 'HB-A0', 'HB-B1'):
            self.assertAlmostEqual(result['pooled'][ident]['recall'], 2 / 3)
        self.assertEqual(result['source_authentication'], 'NOT_ATTESTED')
        self.assertFalse(result['official_threshold_pass'])
        self.assertEqual(result['paired_uncertainty']['seed'], 0)
        self.assertEqual(result['paired_uncertainty']['replicates'], 2000)
        self.assertEqual(result['source_receipt']['projection_sha256'], result['input_digests'])

    def test_v2_parent_publishes_one_immutable_replay_after_predictions_before_labels(self):
        import research_model_adapter as models
        actual_prepare, actual_open = models.prepare_research_candidates, Path.open
        prepared = []
        def prepare(*a, **kw):
            value = actual_prepare(*a, **kw)
            prepared.append(value['receipt_sha256'])
            return value
        def opening(path, *a, **kw):
            if path.name in ('captures.csv', 'individuals.csv', 'coverage.json'):
                self.assertTrue(prepared, 'Outcome payload opened before prediction hashes')
            return actual_open(path, *a, **kw)
        with patch.object(models, 'prepare_research_candidates', side_effect=prepare), patch.object(Path, 'open', new=opening):
            result = self.parent.call()
        self.assertEqual(len(result['candidates']), 3, str(result))
        self.assertEqual(len(result['replay']), 1)
        payload = json.loads((self.root / result['replay'][0]['path']).read_bytes())
        self.assertEqual(payload['stage1_diagnostic']['pooled']['uniform']['denominator'], 3)
        self.assertEqual(self.parent.call()['replay'], result['replay'])

    def test_unknown_incomplete_or_missing_complete_never_returns_partial_metrics(self):
        for declaration in ('UNKNOWN', 'INCOMPLETE', None):
            f = self.fixture
            f.coverage['declaration'] = declaration or 'UNKNOWN'
            f.publish()
            if declaration is None:
                f.manifest['coverage_id'] = None
                f.nodes.pop('coverage')
                f.manifest_only()
            result = self.parent.call()
            self.assertEqual(len(result['candidates']), 3, str(result))
            self.assertEqual(len(result['replay']), 1)
            diagnostic = result['stage1_diagnostic']
            self.assertEqual(diagnostic['status'], 'NEED_MORE_DATA')
            self.assertEqual((diagnostic['per_night'], diagnostic['pooled'], diagnostic['paired_uncertainty']), ([], {}, {}))

    def test_subset_coverage_is_contradiction_even_if_unknown(self):
        for declaration in ('DECLARED_COMPLETE', 'UNKNOWN'):
            self.fixture.coverage.update(declaration=declaration, event_ids=['inside'], individual_ids=['inside-1', 'inside-2'])
            self.fixture.publish()
            result = self.parent.call()
            self.assertEqual(result['stages'][0]['status'], 'FAIL')
            self.assertEqual(result['replay'], [])

    def test_individual_count_duplicate_and_causal_contradictions_fail(self):
        baseline = copy.deepcopy(self.fixture.individuals)
        for rows in (baseline[:-1], baseline + baseline[:1]):
            self.fixture.individuals = rows
            self.fixture.publish()
            self.assertEqual(self.parent.call()['stages'][0]['status'], 'FAIL')
        self.fixture.individuals = baseline
        self.fixture.publish()
        self.fixture.nodes['captures']['readiness']['source_received_at'] = PRIOR
        self.fixture.manifest_only()
        self.assertEqual(self.parent.call()['stages'][0]['status'], 'FAIL')

    def test_observational_raw_ancestor_cannot_hide_pre_event_readiness(self):
        f = self.fixture
        ancestor = copy.deepcopy(f.nodes['captures'])
        ancestor.update(id='capture-raw')
        ancestor['ref'] = base_ref(self.root, 'evidence/stage1/capture-raw.csv', csv_bytes(f.captures))
        ancestor['readiness']['source_received_at'] = PRIOR
        f.nodes['capture-raw'] = ancestor
        f.nodes['captures'].update(source_kind='DERIVED', parents=['capture-raw'])
        f.manifest_only()
        result = self.parent.call()
        self.assertEqual(result['stages'][0]['status'], 'FAIL')
        self.assertIn('readiness precedes', result['stages'][0]['reason'])
        self.assertEqual(result['replay'], [])

    def test_complete_coverage_cannot_predate_horizon_on_any_stage(self):
        f = self.fixture
        f.nodes['coverage']['readiness']['derived_at'] = NIGHT + 'T19:19:00+09:00'
        f.manifest_only()
        self.assertEqual(self.parent.call()['stages'][0]['status'], 'FAIL')

    def test_unknown_coverage_actual_ids_cannot_predate_known_capture(self):
        f = self.fixture
        f.coverage['declaration'] = 'UNKNOWN'
        f.publish()
        f.nodes['coverage']['readiness']['source_received_at'] = PRIOR
        f.manifest_only()
        self.assertEqual(self.parent.call()['stages'][0]['status'], 'FAIL')

    def test_missing_scope_does_not_hide_invalid_supplied_coverage(self):
        f = self.fixture
        f.coverage.update(declaration='UNKNOWN', scope_sha256=True)
        f.publish()
        f.manifest['scope_id'] = None
        f.nodes.pop('scope')
        f.manifest_only()
        self.assertEqual(self.parent.call()['stages'][0]['status'], 'FAIL')

    def test_empty_capture_csv_still_requires_explicit_coordinate_schema(self):
        f = self.fixture
        f.nodes['captures']['ref'] = base_ref(self.root, 'evidence/stage1/captures.csv',
            b'event_id,operational_date,event_time_local,event_type,event_count\n')
        f.nodes['individuals']['ref'] = base_ref(self.root, 'evidence/stage1/individuals.csv',
            b'individual_id,event_id,individual_index,operational_date,event_time_local\n')
        f.coverage.update(event_ids=[], individual_ids=[], captures_ref=f.nodes['captures']['ref'],
            individuals_ref=f.nodes['individuals']['ref'])
        f.nodes['coverage']['ref'] = base_ref(self.root, 'evidence/stage1/coverage.json', canonical_bytes(f.coverage))
        f.manifest_only()
        self.assertEqual(self.parent.call()['stages'][0]['status'], 'FAIL')

    def test_prior_scope_is_bound_before_outcome_reads_independent_of_node_order(self):
        f = self.fixture
        f.scope['horizon_end'] = NIGHT + 'T19:10:00+09:00'
        f.publish()
        f.nodes = dict(reversed(list(f.nodes.items())))
        f.manifest_only()
        actual = Path.open
        def opening(path, *a, **kw):
            if path.name in ('captures.csv', 'individuals.csv', 'coverage.json'):
                raise AssertionError('Contradictory prior scope reached label payload')
            return actual(path, *a, **kw)
        with patch.object(Path, 'open', new=opening):
            self.assertEqual(self.parent.call()['stages'][0]['status'], 'FAIL')

    def test_nonnull_missing_csv_is_need_more_data_but_bad_bytes_are_failure(self):
        path = self.root / self.fixture.nodes['captures']['ref']['path']
        path.unlink()
        result = self.parent.call()
        self.assertEqual(len(result['candidates']), 3, str(result))
        self.assertEqual(result['stage1_diagnostic']['status'], 'NEED_MORE_DATA')
        self.assertIn('FILE:captures', result['stage1_diagnostic']['source_receipt']['missing_inputs'])
        path.write_bytes(b'wrong supplied bytes')
        self.assertEqual(self.parent.call()['stages'][0]['status'], 'FAIL')

    def test_malformed_csv_all_rows_rejected_even_outside_scope(self):
        f = self.fixture
        original = copy.deepcopy(f.captures)
        row = dict(original[0], event_id='irrelevant-other-night', operational_date='2026-10-13',
                   event_count='true', event_time_local='2026-10-13T20:00:00+09:00')
        f.captures.append(row)
        f.publish()
        self.assertEqual(self.parent.call()['stages'][0]['status'], 'FAIL')
        f.captures = original
        f.publish()
        f.nodes['captures']['ref'] = base_ref(self.root, 'evidence/stage1/captures.csv', b'event_id,event_id\na,b\n')
        f.coverage['captures_ref'] = f.nodes['captures']['ref']
        f.nodes['coverage']['ref'] = base_ref(self.root, 'evidence/stage1/coverage.json', canonical_bytes(f.coverage))
        f.manifest_only()
        self.assertEqual(self.parent.call()['stages'][0]['status'], 'FAIL')

    def test_shared_byte_cap_is_charged_on_source_reads_before_replay(self):
        import research_model_adapter as models
        actual = models.prepare_research_candidates
        context = ProspectiveReadContext(300, 2 * 1024**3)
        def narrow(*a, **kw):
            result = actual(*a, **kw)
            context.max_bytes = context.bytes_read + 10
            return result
        with patch.object(models, 'prepare_research_candidates', side_effect=narrow):
            result = self.parent.call(_read_context=context)
        self.assertGreater(context.bytes_read, context.max_bytes)
        self.assertEqual(result['stages'][0]['blocker_kind'], 'RUNTIME_BLOCKED')
        self.assertEqual(result['replay'], [])

    def test_native_unit_mean_preserves_task6_exact_float_aggregation(self):
        from evaluation.stage1_source_adapter import _prepared
        from statistics import mean
        context, forecast, prepared = self.projections()
        candidate = prepared['candidates'][1]
        values = [.1, .1, .1, .3]
        for unit, value in zip(candidate['prediction']['unit_predictions'], values):
            unit['spatial_score'] = value
        prediction = candidate['prediction']
        prediction['prediction_sha256'] = digest({k: v for k, v in prediction.items() if k != 'prediction_sha256'})
        candidate['prediction_sha256'] = prediction['prediction_sha256']
        prepared['receipt_sha256'] = digest({k: v for k, v in prepared.items() if k != 'receipt_sha256'})
        projections = _prepared(forecast, prepared, context.check)[-1]
        self.assertEqual(list(projections[1]['scores'][NIGHT].values()), [mean(values)])

    def test_sealed_nested_source_rejected_before_payload_open(self):
        self.fixture.nodes['captures']['ref']['path'] = 'evidence/sealed/confirmation/captures.csv'
        self.fixture.manifest_only()
        actual_open = Path.open
        def opening(path, *a, **kw):
            if 'sealed' in path.parts:
                raise AssertionError('sealed payload opened')
            return actual_open(path, *a, **kw)
        with patch.object(Path, 'open', new=opening):
            self.assertEqual(self.parent.call()['stages'][0]['status'], 'FAIL')

    def test_stage1_source_final_rescan_rejects_mutation_and_shared_expiry(self):
        from evaluation import full_ledger_stage1 as pure
        original = pure.evaluate_full_ledger_stage1
        def mutate(*a, **kw):
            result = original(*a, **kw)
            (self.root / 'evidence/stage1/captures.csv').write_bytes(b'changed after evaluation')
            return result
        with patch.object(pure, 'evaluate_full_ledger_stage1', side_effect=mutate):
            result = self.parent.call()
        self.assertEqual(result['stages'][0]['status'], 'FAIL')
        self.assertEqual(result['replay'], [])
        self.fixture.publish()
        context = ProspectiveReadContext(300, 2 * 1024**3)
        def expire(*a, **kw):
            context.deadline = 0
            return original(*a, **kw)
        with patch.object(pure, 'evaluate_full_ledger_stage1', side_effect=expire):
            result = self.parent.call(_read_context=context)
        self.assertEqual(result['stages'][0]['blocker_kind'], 'RUNTIME_BLOCKED')
        self.assertEqual(result['replay'], [])

    def test_forged_prepared_score_and_geometry_fail_before_source_payload(self):
        from evaluation.stage1_source_adapter import evaluate_stage1_sources
        context, forecast, prepared = self.projections()
        prepared['candidates'][0]['prediction']['unit_predictions'][0]['spatial_score'] += 1
        actual_open = Path.open
        def opening(path, *a, **kw):
            if path.name == 'captures.csv':
                raise AssertionError('unbound predictions reached outcome payload')
            return actual_open(path, *a, **kw)
        with patch.object(Path, 'open', new=opening), self.assertRaises(ValueError):
            evaluate_stage1_sources(self.root, self.fixture.ref, forecast, prepared, context=context)

    def test_pure_callback_uses_parent_absolute_budget_without_default_numeric_change(self):
        from evaluation.full_ledger_stage1 import evaluate_full_ledger_stage1
        from test_full_ledger_stage1 import fixtures
        universe, scores, ledger = fixtures()
        expected = evaluate_full_ledger_stage1(universe, scores, ledger)
        self.assertEqual(expected, evaluate_full_ledger_stage1(universe, scores, ledger, check=lambda: None))
        calls = []
        def check():
            calls.append(1)
            if len(calls) > 200:
                raise TimeoutError('parent absolute budget')
        with self.assertRaisesRegex(TimeoutError, 'parent absolute budget'):
            evaluate_full_ledger_stage1(universe, scores, ledger, check=check)

    def test_late_v2_expiry_removes_only_own_new_replay(self):
        import research_pdca_adapter as parent
        context = ProspectiveReadContext(300, 2 * 1024**3)
        actual = parent.stage
        def expire(name, *a, **kw):
            result = actual(name, *a, **kw)
            if name == 'candidate_validation':
                context.deadline = 0
            return result
        with patch.object(parent, 'stage', side_effect=expire):
            result = self.parent.call(_read_context=context)
        self.assertEqual(result['replay'], [])
        self.assertEqual(list((self.root / 'predictions/replay').rglob('*.json')), [])

    def test_late_expiry_during_link_cleans_new_but_keeps_preexisting_replay(self):
        import research_pdca_adapter as parent
        actual_link = parent.os.link
        context = ProspectiveReadContext(300, 2 * 1024**3)
        def expire_link(*a, **kw):
            actual_link(*a, **kw)
            context.deadline = 0
        with patch.object(parent.os, 'link', side_effect=expire_link):
            result = self.parent.call(_read_context=context)
        self.assertEqual(result['replay'], [])
        self.assertEqual(list((self.root / 'predictions/replay').rglob('*.json')), [])
        existing = self.parent.call()['replay'][0]
        payload = (self.root / existing['path']).read_bytes()
        context = ProspectiveReadContext(300, 2 * 1024**3)
        actual_stage = parent.stage
        def expire_stage(name, *a, **kw):
            value = actual_stage(name, *a, **kw)
            if name == 'candidate_validation':
                context.deadline = 0
            return value
        with patch.object(parent, 'stage', side_effect=expire_stage):
            self.assertEqual(self.parent.call(_read_context=context)['replay'], [])
        self.assertEqual((self.root / existing['path']).read_bytes(), payload)

    def test_interrupt_after_native_link_before_return_still_cleans_owned_inode(self):
        import research_pdca_adapter as parent
        actual_link = parent.os.link
        def interrupt(*a, **kw):
            actual_link(*a, **kw)
            raise TimeoutError('native link completed before interruption')
        with patch.object(parent.os, 'link', side_effect=interrupt):
            result = self.parent.call()
        self.assertEqual(result['replay'], [])
        self.assertEqual(result['stages'][0]['blocker_kind'], 'RUNTIME_BLOCKED')
        self.assertEqual(list((self.root / 'predictions/replay').rglob('*.json')), [])

    def test_v1_publication_does_not_add_temporary_stat_syscall(self):
        import research_pdca_adapter as parent
        actual = parent.os.stat
        def stat(path, *a, **kw):
            if not isinstance(path, int) and Path(path).name.startswith('.research-replay-'):
                raise AssertionError('v1 added a temporary stat syscall')
            return actual(path, *a, **kw)
        with patch.object(parent.os, 'stat', side_effect=stat):
            result = parent._publish(self.root, NIGHT, {'synthetic_v1': True}, ProspectiveReadContext(30, 2 * 1024**3))
        self.assertTrue((self.root / result['path']).is_file())

    def test_cleanup_refuses_replaced_owned_artifact(self):
        import research_pdca_adapter as parent
        context = ProspectiveReadContext(300, 2 * 1024**3)
        actual_link = parent.os.link
        def replace(*a, **kw):
            actual_link(*a, **kw)
            destination = Path(a[1])
            destination.unlink()
            destination.write_bytes(b'foreign replacement sentinel')
            context.deadline = 0
        with patch.object(parent.os, 'link', side_effect=replace):
            result = self.parent.call(_read_context=context)
        files = list((self.root / 'predictions/replay').rglob('*.json'))
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].read_bytes(), b'foreign replacement sentinel')
        self.assertTrue(any('Untrusted residual' in item for item in result['data_blockers']))

    def test_late_directory_reparse_cannot_delete_external_replay_or_temp_sentinel(self):
        import research_pdca_adapter as parent
        context = ProspectiveReadContext(300, 2 * 1024**3)
        actual_link = parent.os.link
        changed = []
        with tempfile.TemporaryDirectory() as directory:
            external = Path(directory).absolute()
            def swap(source, destination, *a, **kw):
                actual_link(source, destination, *a, **kw)
                folder = Path(destination).parent
                saved = folder.with_name('research-saved')
                self.assertTrue(folder.absolute().is_relative_to(self.root.absolute()))
                folder.rename(saved)
                (external / Path(source).name).write_bytes(b'external temporary sentinel')
                (external / Path(destination).name).write_bytes(b'external replay sentinel')
                if os.name == 'nt':
                    subprocess.run(['cmd', '/c', 'mklink', '/J', str(folder), str(external)], check=True, capture_output=True)
                else:
                    folder.symlink_to(external, target_is_directory=True)
                changed.append(folder)
                context.deadline = 0
            try:
                with patch.object(parent.os, 'link', side_effect=swap):
                    result = self.parent.call(_read_context=context)
                self.assertEqual(result['replay'], [])
                self.assertTrue(any('Untrusted residual' in item for item in result['data_blockers']))
                self.assertEqual(sorted(path.read_bytes() for path in external.iterdir()),
                                 [b'external replay sentinel', b'external temporary sentinel'])
            finally:
                for link in changed:
                    os.rmdir(link) if os.name == 'nt' else link.unlink()

    def test_cleanup_ancestor_swap_after_real_handle_identity_preserves_external_file(self):
        import research_pdca_adapter as parent
        directory = self.root / 'cleanup-parent'
        directory.mkdir()
        target = directory / 'owned.json'
        target.write_bytes(b'owned cleanup bytes')
        identity = target.stat()
        relative = target.relative_to(self.root).as_posix()
        backup = directory.with_name('cleanup-backup')
        swapped = []
        denied = []
        with tempfile.TemporaryDirectory() as temporary:
            external = Path(temporary).absolute()
            sentinel = external / target.name
            sentinel.write_bytes(b'external sentinel')
            native = parent.os.fstat if os.name == 'nt' else parent.os.stat
            function = '_unlink_owned_windows' if os.name == 'nt' else '_unlink_owned_posix'
            def after_identity(*a, **kw):
                value = native(*a, **kw)
                if inspect.currentframe().f_back.f_code.co_name == function and not swapped:
                    self.assertTrue(directory.absolute().is_relative_to(self.root.absolute()))
                    try:
                        directory.rename(backup)
                    except PermissionError as exc:
                        if os.name != 'nt':
                            raise
                        denied.append(exc.winerror)
                        return value
                    if os.name == 'nt':
                        subprocess.run(['cmd', '/c', 'mklink', '/J', str(directory), str(external)], check=True, capture_output=True)
                        self.assertTrue(directory.is_junction())
                    else:
                        directory.symlink_to(external, target_is_directory=True)
                    swapped.append(True)
                return value
            try:
                with patch.object(parent.os, 'fstat' if os.name == 'nt' else 'stat', new=after_identity):
                    residual = parent._cleanup_owned(self.root, [(relative, identity.st_dev, identity.st_ino)])
                self.assertTrue(swapped or denied, 'Actual identity/delete race was not exercised')
                self.assertEqual(sentinel.read_bytes(), b'external sentinel')
                if swapped:
                    self.assertEqual(residual, [relative])
                    self.assertFalse((backup / target.name).exists(), 'Only verified owned handle should be removed')
                else:
                    self.assertEqual(denied, [5], 'Record real Windows native rename denial')
                    self.assertEqual(residual, [])
                    self.assertFalse(target.exists())
            finally:
                if swapped:
                    os.rmdir(directory) if os.name == 'nt' else directory.unlink()

    def test_source_directory_os_link_is_rejected_before_external_read(self):
        f = self.fixture
        with tempfile.TemporaryDirectory() as directory:
            external = Path(directory).absolute()
            (external / 'captures.csv').write_bytes(csv_bytes(f.captures))
            link = self.root / 'evidence/linked-captures'
            self.assertTrue(link.absolute().is_relative_to(self.root.absolute()))
            try:
                if os.name == 'nt':
                    subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(external)], check=True, capture_output=True)
                    self.assertTrue(link.is_junction())
                else:
                    link.symlink_to(external, target_is_directory=True)
                f.nodes['captures']['ref']['path'] = 'evidence/linked-captures/captures.csv'
                f.coverage['captures_ref'] = f.nodes['captures']['ref']
                f.nodes['coverage']['ref'] = base_ref(self.root, 'evidence/stage1/coverage.json', canonical_bytes(f.coverage))
                f.manifest_only()
                actual, external_opens = Path.open, []
                def opening(path, *a, **kw):
                    if 'linked-captures' in path.parts or path.is_relative_to(external):
                        external_opens.append(path)
                    return actual(path, *a, **kw)
                with patch.object(Path, 'open', new=opening):
                    result = self.parent.call()
                self.assertEqual(external_opens, [])
                self.assertEqual(result['stages'][0]['status'], 'FAIL')
            finally:
                if os.path.lexists(link):
                    # Remove the link itself, never recursively clean its target.
                    os.rmdir(link) if os.name == 'nt' else link.unlink()

    @unittest.skipIf(os.name == 'nt', 'Real POSIX atomic quarantine needs dir_fd; Ubuntu CI runs this')
    def test_posix_public_leaf_replacement_is_preserved_after_atomic_claim(self):
        import research_pdca_adapter as parent
        folder = self.root / 'cleanup-leaf'
        folder.mkdir()
        target = folder / 'owned.json'
        target.write_bytes(b'owned bytes')
        identity = target.stat()
        relative = target.relative_to(self.root).as_posix()
        native = parent.os.rename
        swapped = []
        def before_claim(source, destination, *a, **kw):
            if source == target.name and destination == 'claimed' and not swapped:
                target.rename(folder / 'original-backup')
                target.write_bytes(b'foreign replacement')
                swapped.append(True)
            return native(source, destination, *a, **kw)
        with patch.object(parent.os, 'rename', new=before_claim):
            residual = parent._cleanup_owned(self.root, [(relative, identity.st_dev, identity.st_ino)])
        self.assertEqual(swapped, [True])
        self.assertEqual(target.read_bytes(), b'foreign replacement')
        self.assertEqual((folder / 'original-backup').read_bytes(), b'owned bytes')
        recovery = [path for path in residual if path != relative]
        self.assertEqual(len(recovery), 1)
        self.assertEqual((self.root / recovery[0]).read_bytes(), b'foreign replacement')
        self.assertEqual((self.root / recovery[0]).parent.stat().st_mode & 0o777, 0o700)

    @unittest.skipIf(os.name == 'nt', 'Real POSIX atomic quarantine needs dir_fd; Ubuntu CI runs this')
    def test_posix_interruption_after_atomic_claim_reports_recoverable_owned_bytes(self):
        import research_pdca_adapter as parent
        folder = self.root / 'claim-interruption'
        folder.mkdir()
        target = folder / 'owned.json'
        target.write_bytes(b'owned recoverable bytes')
        identity = target.stat()
        relative = target.relative_to(self.root).as_posix()
        native = parent.os.rename
        def after_claim(*a, **kw):
            native(*a, **kw)
            raise TimeoutError('native claim succeeded before interruption')
        with patch.object(parent.os, 'rename', new=after_claim):
            residual = parent._cleanup_owned(self.root, [(relative, identity.st_dev, identity.st_ino)])
        recovery = [path for path in residual if path != relative]
        self.assertEqual(len(recovery), 1)
        self.assertEqual((self.root / recovery[0]).read_bytes(), b'owned recoverable bytes')
        self.assertIn(relative, residual)

    @unittest.skipIf(os.name == 'nt', 'Real POSIX atomic quarantine needs dir_fd; Ubuntu CI runs this')
    def test_posix_uuid_collision_preserves_preexisting_private_directory(self):
        import research_pdca_adapter as parent
        folder = self.root / 'claim-collision'
        folder.mkdir()
        target = folder / 'owned.json'
        target.write_bytes(b'owned bytes')
        identity = target.stat()
        collision = folder / ('.research-cleanup-' + 'a' * 32)
        collision.mkdir()
        class FixedUUID:
            hex = 'a' * 32
        relative = target.relative_to(self.root).as_posix()
        with patch.object(parent.uuid, 'uuid4', return_value=FixedUUID()):
            residual = parent._cleanup_owned(self.root, [(relative, identity.st_dev, identity.st_ino)])
        self.assertEqual(residual, [relative])
        self.assertTrue(collision.is_dir())
        self.assertEqual(target.read_bytes(), b'owned bytes')

    @unittest.skipIf(os.name == 'nt', 'Real POSIX atomic quarantine needs dir_fd; Ubuntu CI runs this')
    def test_posix_contested_restore_keeps_both_foreign_contents_and_recovery_paths(self):
        import research_pdca_adapter as parent
        folder = self.root / 'claim-contested'
        folder.mkdir()
        target = folder / 'owned.json'
        target.write_bytes(b'original own bytes')
        identity = target.stat()
        relative = target.relative_to(self.root).as_posix()
        rename, link = parent.os.rename, parent.os.link
        def before_claim(source, destination, *a, **kw):
            if source == target.name and destination == 'claimed':
                target.rename(folder / 'original-backup')
                target.write_bytes(b'first foreign replacement')
            return rename(source, destination, *a, **kw)
        def contested(*a, **kw):
            target.write_bytes(b'second foreign replacement')
            return link(*a, **kw)
        with patch.object(parent.os, 'rename', new=before_claim), patch.object(parent.os, 'link', new=contested):
            residual = parent._cleanup_owned(self.root, [(relative, identity.st_dev, identity.st_ino)])
        self.assertEqual(target.read_bytes(), b'second foreign replacement')
        recovery = [path for path in residual if path != relative]
        self.assertEqual(len(recovery), 1)
        self.assertEqual((self.root / recovery[0]).read_bytes(), b'first foreign replacement')
        self.assertEqual((folder / 'original-backup').read_bytes(), b'original own bytes')

    def test_current_sept28_positive_csvs_do_not_prove_complete_denominator(self):
        # Native immutable Git bytes, including on Windows core.autocrlf checkouts.
        f = self.fixture
        for role, path in [('captures', 'data/processed/capture_events/2026/2026-09-28.csv'),
                           ('individuals', 'data/processed/individuals/2026/2026-09-28.csv')]:
            raw = subprocess.check_output(['git', 'show', 'HEAD:' + path], cwd=ROOT)
            f.node(role, raw, '2026-10-25T18:00:00+09:00')
        # No invented coverage/scope for actual Sept28. Missing scope is explicit;
        # supplied real source rows still undergo schema/identity/count checks.
        f.manifest['scope_id'] = f.manifest['coverage_id'] = None
        f.nodes.pop('scope')
        f.nodes.pop('coverage')
        f.manifest.update(evaluation_as_of='2026-10-25T19:00:00+09:00',
            readiness=f.ready('2026-10-25T18:00:00+09:00'), usable_at='2026-10-25T18:00:00+09:00')
        f.manifest_only()
        result = self.evaluate()
        self.assertEqual(result['status'], 'NEED_MORE_DATA')
        self.assertEqual(result['source_summary']['capture_events'], 5)
        self.assertEqual(result['source_summary']['individuals'], 6)
        self.assertEqual(result['pooled'], {})

    @unittest.skipIf(os.name == 'nt', 'Actual master lock needs POSIX fcntl; Ubuntu CI runs this')
    def test_v2_actual_master_snapshot_and_parent_dispatch_remain_diagnostic(self):
        from master_orchestrator import run_master
        result = run_master(self.root, NIGHT)
        candidate = next(s for s in result['stages'] if s['name'] == 'candidate_generation')
        self.assertEqual(candidate['status'], 'PASS', str(result))
        self.assertFalse(result['completed'])


if __name__ == '__main__':
    unittest.main()
