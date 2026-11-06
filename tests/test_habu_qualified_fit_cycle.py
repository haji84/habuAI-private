"""Reproducible synthetic end-to-end validation of the existing G0 fit path."""
import pathlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))

from habu_qualified_fit_cycle import run_cycle
import habu_qualified_fit_cycle as qualified_cycle
from master_contracts import canonical_bytes
import test_g0_training_source_contract as source_fixtures


class QualifiedAutoFitTests(unittest.TestCase):
    def setUp(self):
        self.fx = source_fixtures.TrainingSourceContractTests()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.output = self.fx.fixture.work / 'private-out'
        self.kwargs = {
            'manifest_path': self.fx.ref['path'],
            'manifest_sha256': self.fx.ref['sha256'],
            'feature_sha256': source_fixtures.definition_hash(self.fx.features),
            'heldout_night': '2026-10-20',
            'fit_cutoff': '2026-10-19T19:00:00+09:00',
            'forecast_cutoff': '2026-10-20T18:00:00+09:00',
        }

    def execute(self, **changed):
        kwargs = dict(self.kwargs, **changed)
        return run_cycle(self.fx.root, self.output, **kwargs)

    def cli(self, output):
        arguments = [sys.executable, '-B', '-X', 'utf8', str(ROOT / 'scripts/habu_qualified_fit_cycle.py'),
                     '--root', str(self.fx.root), '--private-output', str(output)]
        for key, value in self.kwargs.items():
            arguments.extend(['--' + key.replace('_', '-'), value])
        return subprocess.run(arguments, cwd=self.fx.fixture.work, capture_output=True,
                              text=True, encoding='utf-8', timeout=30)

    def assert_cli_private_rejection(self, output):
        originals = {p: p.read_bytes() for p in self.fx.root.rglob('*') if p.is_file()}
        result = self.cli(output)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'BLOCKED')
        self.assertEqual(result.stderr, '')
        self.assertNotIn(str(self.fx.fixture.work), result.stdout)
        for path, raw in originals.items():
            self.assertEqual(path.read_bytes(), raw)

    def test_actual_cli_rejects_other_git_checkout_before_fitting(self):
        repo = self.fx.fixture.work / 'public-checkout'
        subprocess.run(['git', 'init', '--quiet', str(repo)], check=True, capture_output=True)
        output = repo / 'private-candidates'
        self.assert_cli_private_rejection(output)
        self.assertFalse(output.exists())

    def test_actual_cli_rejects_an_output_ancestor_of_the_input_workspace(self):
        self.assert_cli_private_rejection(self.fx.fixture.work)
        self.assertFalse((self.fx.fixture.work / 'candidates').exists())

    def test_actual_cli_rejects_symlink_output_ancestor_before_resolving(self):
        destination, alias = self.fx.fixture.work / 'real-output', self.fx.fixture.work / 'alias'
        destination.mkdir()
        try:
            alias.symlink_to(destination, target_is_directory=True)
        except OSError as exc:
            self.skipTest('Native directory symlink unavailable: ' + str(exc.winerror if os.name == 'nt' else exc.errno))
        self.addCleanup(alias.unlink)
        self.assert_cli_private_rejection(alias / 'nested')
        self.assertEqual(list(destination.iterdir()), [])

    @unittest.skipUnless(os.name == 'nt', 'Windows junction control')
    def test_actual_cli_rejects_junction_output_ancestor_before_resolving(self):
        destination, alias = self.fx.fixture.work / 'real-output', self.fx.fixture.work / 'junction'
        destination.mkdir()
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(alias), str(destination)], capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.addCleanup(alias.rmdir)
        self.assert_cli_private_rejection(alias / 'nested')
        self.assertEqual(list(destination.iterdir()), [])

    def test_actual_cli_rejects_input_parent_file_without_replacing_it(self):
        source = self.fx.root / self.fx.ref['path']
        self.assert_cli_private_rejection(source / 'nested')

    def test_actual_cli_conflicting_model_stays_immutable_without_path_traceback(self):
        first = self.cli(self.output)
        self.assertEqual(first.returncode, 0, first.stderr)
        output = self.output / json.loads(first.stdout)['model_relative_path']
        output.write_bytes(b'preserved original conflict')
        self.assert_cli_private_rejection(self.output)
        self.assertEqual(output.read_bytes(), b'preserved original conflict')

    def test_module_cli_help_remains_supported(self):
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-m',
                                 'scripts.habu_qualified_fit_cycle', '--help'],
                                cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--private-output', result.stdout)

    def test_qualified_synthetic_selection_fits_prospective_readable_research_only_candidate(self):
        result = self.execute()
        self.assertEqual(result['status'], 'RESEARCH_CANDIDATE_FITTED')
        self.assertFalse(result['production_model_activated'])
        self.assertFalse(result['official_prediction_authorized'])
        self.assertEqual(result['future_independent_validation'], 'NOT_PERFORMED')
        self.assertEqual(result['fit_counts']['rows'], 4)
        model_file = self.output / result['model_relative_path']
        self.assertTrue(model_file.exists())
        self.assertFalse((self.fx.root / 'models').exists())
        self.assertEqual(self.execute(), result)

    def test_unqualified_source_is_explicit_blocked_no_model(self):
        result = self.execute(manifest_path=None, manifest_sha256=None, feature_sha256=None)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['reason'], 'MISSING_SOURCE_QUALIFIED_G0_MANIFEST')
        self.assertFalse(self.output.exists())

    def test_missing_manifest_path_blocks_no_model(self):
        result = self.execute(manifest_path='protocols/development/nonexistent.json')
        self.assertEqual(result['reason'], 'QUALIFIED_MANIFEST_SOURCE_NOT_AVAILABLE')
        self.assertFalse(self.output.exists())

    def test_tampered_manifest_fails_closed(self):
        manifest_path = self.fx.root / self.fx.ref['path']
        manifest_path.write_bytes(manifest_path.read_bytes() + b'\n')
        with self.assertRaises(ValueError):
            self.execute()
        self.assertFalse(self.output.exists())

    def test_missing_independent_negative_exposure_blocks_fit(self):
        self.fx.fixture.rows[1]['search_role'] = 'UNKNOWN'
        self.fx.fixture.publish()
        self.fx.build_manifest()
        result = self.execute(manifest_sha256=self.fx.ref['sha256'])
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['reason'], 'INSUFFICIENT_SOURCE_QUALIFIED_TRAINING_UNITS')
        self.assertEqual(result['counts']['negatives'], 1)
        self.assertFalse(self.output.exists())

    def test_historical_future_source_is_not_fit_input(self):
        self.fx.fixture.add_development_holdout()
        self.fx.build_manifest()
        result = self.execute(manifest_sha256=self.fx.ref['sha256'])
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['reason'], 'G0_TRAINING_SOURCE_GATE_BLOCKED')
        self.assertFalse(self.output.exists())

    def test_never_write_model_inside_repo_workspace(self):
        with self.assertRaisesRegex(ValueError, 'outside'):
            run_cycle(self.fx.root, self.fx.root / 'models' / 'candidates', **self.kwargs)
        self.assertFalse((self.fx.root / 'models').exists())

    def test_reject_unbound_manifest_or_unvalidated_source_family(self):
        for bad in ({'manifest_sha256': 'b' * 64, 'feature_sha256': None},
                    {'manifest_path': '../private.json'},
                    {'manifest_path': 'sealed/confirmation/fake.json'}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.execute(**bad)

    def test_exposed_nights_do_not_train_as_untouched_confirmation(self):
        result = self.execute(exposed_nights=('2026-09-12',))
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertFalse(self.output.exists())


class PrivateSourcePreparationTests(unittest.TestCase):
    """Synthetic artifacts exercise the real selector, never certify field data."""

    def setUp(self):
        self.fx = source_fixtures.TrainingSourceContractTests()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.root = self.fx.root
        self.output = self.fx.fixture.work / 'prepared-private'
        self.parameters = dict(heldout_night='2026-10-20',
            fit_cutoff='2026-10-19T19:00:00+09:00',
            forecast_cutoff='2026-10-20T18:00:00+09:00')
        self.binding = dict(manifest_path=self.fx.ref['path'],
            manifest_sha256=self.fx.ref['sha256'],
            feature_sha256=source_fixtures.definition_hash(self.fx.features))

    def execute(self, **changes):
        self.assertTrue(callable(getattr(qualified_cycle, 'prepare_source', None)),
                        'Missing no-fit private G0 source preparation entry')
        options = dict(self.parameters)
        options.update(self.binding)
        options.update(changes)
        return qualified_cycle.prepare_source(self.root, self.output, **options)

    def research_ref(self):
        import hashlib
        path = self.root / 'evidence/research-route.json'
        raw = canonical_bytes(dict(activity='SEARCH_INFERRED', capture_records=[],
                                   training_observation='UNKNOWN', formal_negative=False))
        path.write_bytes(raw)
        return dict(path='evidence/research-route.json',
                    sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))

    def test_missing_declaration_preserves_research_and_exact_blocked_report_without_fit(self):
        ref = self.research_ref()
        originals = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with (patch.object(qualified_cycle, 'select_g0_training_rows', side_effect=AssertionError('no declaration')),
              patch.object(qualified_cycle, 'fit_candidate', side_effect=AssertionError('preparation never fits'))):
            result = self.execute(research_refs=(ref,), manifest_path=None,
                                  manifest_sha256=None, feature_sha256=None)
        receipt = result['receipt']
        self.assertEqual(receipt['status'], 'BLOCKED')
        self.assertEqual(receipt['reason'], 'MISSING_SOURCE_QUALIFIED_G0_MANIFEST')
        self.assertIsNone(receipt['prepared_manifest_ref'])
        self.assertIsNone(receipt['declared_training_units'])
        self.assertEqual(receipt['research_refs'], [ref])
        workspace = self.output / receipt['prepared_workspace']
        self.assertEqual((workspace / ref['path']).read_bytes(), originals[self.root / ref['path']])
        fit_ref = result['execution']['blocked_fit_report_ref']
        actual = json.loads((self.output / fit_ref['path']).read_bytes())
        expected = run_cycle(self.root, self.output, manifest_path=None,
                            manifest_sha256=None, feature_sha256=None, **self.parameters)
        self.assertEqual(actual, expected)
        self.assertFalse(any(p.name == 'candidates' for p in self.output.rglob('*')))
        for path, raw in originals.items():
            self.assertEqual(path.read_bytes(), raw)

    def test_existing_declaration_is_copied_and_checked_with_real_selector_without_fit(self):
        expected = self.fx.call()['selection']
        with patch.object(qualified_cycle, 'fit_candidate', side_effect=AssertionError('preparation never fits')):
            result = self.execute()
        receipt = result['receipt']
        self.assertEqual(receipt['status'], 'DECLARATION_PREPARED')
        self.assertEqual(receipt['training_selection_sha256'], expected['selection_sha256'])
        self.assertEqual(receipt['declared_training_units'], expected['counts']['accepted_rows'])
        self.assertEqual(receipt['source_authentication'], 'NOT_ATTESTED')
        self.assertFalse(receipt['scientific_fit_authorized'])
        self.assertFalse(receipt['production_authorized'])
        self.assertEqual(receipt['prepared_manifest_ref'], self.fx.ref)
        workspace = self.output / receipt['prepared_workspace']
        for path, sha in result['execution']['source_gate_receipt']['consumed_sha256'].items():
            self.assertEqual((workspace / path).read_bytes(), (self.root / path).read_bytes())
        self.assertEqual(result['execution']['source_gate_receipt']['training_selection_sha256'],
                         result['execution']['prepared_gate_receipt']['training_selection_sha256'])
        self.assertGreater(result['execution']['prepared_gate_receipt']['actual_read_bytes'],
                           result['execution']['source_gate_receipt']['actual_read_bytes'])
        self.assertFalse((self.output / 'candidates').exists())

    def test_rerun_preserves_semantic_identity_and_all_prepared_bytes(self):
        first = self.execute()
        workspace = self.output / first['receipt']['prepared_workspace']
        before = {p.relative_to(workspace): p.read_bytes()
                  for p in workspace.rglob('*') if p.is_file()}
        second = self.execute()
        self.assertEqual(first['receipt'], second['receipt'])
        self.assertEqual(first['receipt_ref'], second['receipt_ref'])
        self.assertEqual(before, {p.relative_to(workspace): p.read_bytes()
                                 for p in workspace.rglob('*') if p.is_file()})

    def test_reference_tamper_is_rejected_before_output(self):
        ref = self.research_ref()
        (self.root / ref['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError):
            self.execute(research_refs=(ref,))
        self.assertFalse(self.output.exists())

    def test_conflicting_prepared_file_is_not_replaced_on_rerun(self):
        first = self.execute()
        target = self.output / first['receipt']['prepared_workspace'] / self.fx.ref['path']
        target.write_bytes(b'preserved conflicting output')
        with self.assertRaises(ValueError):
            self.execute()
        self.assertEqual(target.read_bytes(), b'preserved conflicting output')

    def test_duplicate_nonportable_reserved_and_prefix_paths_do_not_create_output(self):
        ref = self.research_ref()
        for path in ('../outside', '/absolute', 'evidence/./a', 'evidence//a',
                     'evidence/sealed/a', 'evidence/CONFIRMATION/a', 'evidence/.git/a',
                     'evidence/NUL.txt', 'evidence/a.', 'evidence/a ', 'evidence/a:b'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.execute(research_refs=(dict(ref, path=path),))
        with self.assertRaises(ValueError):
            self.execute(research_refs=(ref, ref))
        for additional in (dict(ref, path=ref['path'].upper()),
                           dict(ref, path=ref['path'] + '/nested')):
            with self.assertRaises(ValueError):
                self.execute(research_refs=(ref, additional))
        self.assertFalse(self.output.exists())

    def test_input_size_and_reference_caps_precede_source_reads(self):
        ref = self.research_ref()
        for value in (True, -1, qualified_cycle.MAX_PREPARATION_FILE_BYTES + 1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.execute(research_refs=(dict(ref, size_bytes=value),))
        refs = [dict(ref, path='evidence/'+str(i), size_bytes=64*1024**2) for i in range(9)]
        with self.assertRaises(ValueError):
            self.execute(research_refs=refs)
        with self.assertRaises(ValueError):
            self.execute(research_refs=[ref] * 257)
        self.assertFalse(self.output.exists())

    def test_actual_prior_charges_and_parent_deadline_are_not_replenished(self):
        from prospective_inputs import ProspectiveReadContext
        context = ProspectiveReadContext(20, 2*1024**2)
        context.account(777)
        deadline = context.deadline
        result = self.execute(_read_context=context)
        self.assertEqual(context.deadline, deadline)
        self.assertEqual(context.max_bytes, 2*1024**2)
        self.assertEqual(result['actual_read_bytes'], context.bytes_read)
        self.assertGreater(result['actual_read_bytes'], 777)
        self.assertGreater(result['execution']['source_gate_receipt']['actual_read_bytes'], 777)

    def test_depleted_parent_budget_counts_failed_read_without_output(self):
        from prospective_inputs import InputCapacityError, ProspectiveReadContext
        ref = self.research_ref()
        context = ProspectiveReadContext(20, 5)
        context.account(4)
        with self.assertRaises(InputCapacityError):
            self.execute(research_refs=(ref,), manifest_path=None,
                         manifest_sha256=None, feature_sha256=None, _read_context=context)
        self.assertGreater(context.bytes_read, 5)
        self.assertFalse(self.output.exists())

    def test_late_readiness_persists_original_blocked_fit_envelope_without_model(self):
        node = self.fx.manifest['source_nodes'][0]
        node['readiness']['audited_at'] = '2026-10-20T07:00:00+09:00'
        self.fx.publish()
        self.binding['manifest_sha256'] = self.fx.ref['sha256']
        result = self.execute()
        self.assertEqual(result['receipt']['status'], 'BLOCKED')
        self.assertEqual(result['receipt']['reason'], 'G0_TRAINING_SOURCE_GATE_BLOCKED')
        actual = json.loads((self.output / result['execution']['blocked_fit_report_ref']['path']).read_bytes())
        self.assertEqual(actual, run_cycle(self.root, self.fx.fixture.work / 'other-output',
                                        **self.parameters, **self.binding))
        self.assertFalse((self.output / 'candidates').exists())

    def test_short_physical_validity_remains_an_existing_gate_rejection(self):
        self.fx.validity['rows'][self.fx.fixture.rows[0]['row_id']]['road_length_m']['valid_time']['end'] = \
            self.fx.fixture.rows[0]['window_start_jst']
        from test_g0_forecast_contract import base_ref
        bound = base_ref(self.root, 'features/synthetic-training-validity.json', canonical_bytes(self.fx.validity))
        self.fx.manifest['row_validity']['ref'] = bound
        self.fx.publish()
        self.binding['manifest_sha256'] = self.fx.ref['sha256']
        with self.assertRaises(ValueError):
            self.execute()
        self.assertFalse(self.output.exists())

    def test_research_booleans_cannot_become_a_declared_g0_corpus(self):
        import hashlib
        relative = 'protocols/development/foreign-research.json'
        raw = canonical_bytes(dict(species='HIMEHABU', owner_role='OTHER',
            event_type='ROADKILL', SEARCH_INFERRED=True, qualification='AUDITED_TRAIN_ONLY',
            capture_record_missing=True, formal_negative=True))
        (self.root / relative).write_bytes(raw)
        with self.assertRaises(ValueError):
            self.execute(manifest_path=relative, manifest_sha256=hashlib.sha256(raw).hexdigest())
        self.assertFalse(self.output.exists())

    def test_final_original_or_destination_change_cannot_publish_completion(self):
        original = qualified_cycle.select_g0_training_rows
        def mutate_after_destination(root, *args, **kwargs):
            result = original(root, *args, **kwargs)
            if pathlib.Path(root) != self.root:
                target = self.root / 'features/road-source.txt'
                target.write_bytes(target.read_bytes() + b'late change')
            return result
        with patch.object(qualified_cycle, 'select_g0_training_rows', side_effect=mutate_after_destination):
            with self.assertRaises(ValueError):
                self.execute()
        self.assertFalse((self.output / 'preparations').exists())

    def test_expiry_before_execution_audit_cannot_leave_a_completed_receipt(self):
        from prospective_inputs import ProspectiveReadContext
        context = ProspectiveReadContext(20, 2*1024**2)
        original = qualified_cycle._preparation_save
        def expire(output, relative, *args, **kwargs):
            if relative.startswith('checks/'):
                context.deadline = 0
            return original(output, relative, *args, **kwargs)
        with patch.object(qualified_cycle, '_preparation_save', side_effect=expire):
            with self.assertRaises(TimeoutError):
                self.execute(_read_context=context)
        self.assertFalse(any((self.output / 'preparations').glob('*.json')))

    def test_expiry_after_completion_write_removes_only_new_completion(self):
        from prospective_inputs import ProspectiveReadContext
        context = ProspectiveReadContext(20, 2*1024**2)
        original = qualified_cycle._preparation_write
        def expire(path, *args, **kwargs):
            result = original(path, *args, **kwargs)
            if pathlib.Path(path).parent.name == 'preparations':
                context.deadline = 0
            return result
        with patch.object(qualified_cycle, '_preparation_write', side_effect=expire):
            with self.assertRaises(TimeoutError):
                self.execute(_read_context=context)
        self.assertFalse(any((self.output / 'preparations').glob('*.json')))

    def test_prior_completion_survives_a_late_failed_rerun(self):
        from prospective_inputs import ProspectiveReadContext
        first = self.execute()
        path = self.output / first['receipt_ref']['path']
        before = path.read_bytes()
        context = ProspectiveReadContext(20, 2*1024**2)
        original = qualified_cycle._preparation_write
        def expire(target, *args, **kwargs):
            result = original(target, *args, **kwargs)
            if pathlib.Path(target).parent.name == 'preparations':
                context.deadline = 0
            return result
        with patch.object(qualified_cycle, '_preparation_write', side_effect=expire):
            with self.assertRaises(TimeoutError):
                self.execute(_read_context=context)
        self.assertEqual(path.read_bytes(), before)

    def test_creation_owner_close_failure_rolls_back_its_new_completion(self):
        import private_pdca_intake as intake
        ref = self.research_ref()
        marker = OSError('controlled first owner close failure')
        original = intake._TempOwner.close
        failed = []
        def fail_once(owner):
            if not failed:
                failed.append(True)
                raise marker
            return original(owner)
        with patch.object(intake._TempOwner, 'close', new=fail_once):
            with self.assertRaises(OSError) as raised:
                self.execute(research_refs=(ref,), manifest_path=None,
                             manifest_sha256=None, feature_sha256=None)
        self.assertIs(raised.exception, marker)
        self.assertFalse(any((self.output / 'preparations').glob('*.json')))

    def test_foreign_completion_generation_is_preserved_on_late_failure(self):
        from prospective_inputs import ProspectiveReadContext
        context = ProspectiveReadContext(20, 2*1024**2)
        original = qualified_cycle._preparation_write
        foreign = []
        def replace(target, *args, **kwargs):
            result = original(target, *args, **kwargs)
            path = pathlib.Path(target)
            if path.parent.name == 'preparations':
                path.unlink()
                path.write_bytes(b'preserved foreign generation')
                foreign.append(path)
                context.deadline = 0
            return result
        with patch.object(qualified_cycle, '_preparation_write', side_effect=replace):
            with self.assertRaises(TimeoutError):
                self.execute(_read_context=context)
        self.assertEqual(len(foreign), 1)
        self.assertEqual(foreign[0].read_bytes(), b'preserved foreign generation')

    def test_duplicate_event_or_physical_unit_is_not_reweighted(self):
        import copy
        old = copy.deepcopy(self.fx.fixture.rows)
        for kind in ('unit', 'event'):
            self.fx.fixture.rows[:] = copy.deepcopy(old)
            rows = self.fx.fixture.rows
            if kind == 'unit':
                for key in ('cell_x', 'cell_y', 'night', 'window_start_jst'):
                    rows[1][key] = rows[0][key]
                message = 'Duplicate or conflicting 100m'
            else:
                rows[2]['capture_event_ids'] = list(rows[0]['capture_event_ids'])
                message = 'Cross-row capture event duplicate'
            self.fx.fixture.publish()
            self.fx.build_manifest()
            self.binding['manifest_sha256'] = self.fx.ref['sha256']
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, message):
                self.execute()
        self.assertFalse(self.output.exists())

    def test_positive_only_declaration_does_not_require_negative_scope_or_fit(self):
        f = self.fx.fixture
        f.rows[:] = [row for row in f.rows if row['label'] == 1]
        for row in f.rows:
            row.update(search_role='UNKNOWN', all_captures_recorded=False,
                       gpx_segment_eligible=False)
        f.publish()
        self.fx.build_manifest()
        self.binding['manifest_sha256'] = self.fx.ref['sha256']
        result = self.execute()
        self.assertEqual(result['receipt']['declared_training_units'], 2)
        ref = result['execution']['blocked_fit_report_ref']
        report = json.loads((self.output / ref['path']).read_bytes())
        self.assertEqual(report['reason'], 'INSUFFICIENT_SOURCE_QUALIFIED_TRAINING_UNITS')
        self.assertEqual(report['counts']['positives'], 2)
        self.assertEqual(report['counts']['negatives'], 0)
        self.assertFalse((self.output / 'candidates').exists())

    def test_unexpected_child_authority_is_rejected_without_resealing_it(self):
        from master_contracts import digest
        original = qualified_cycle.select_g0_training_rows
        for phase in ('source', 'destination'):
            def escalate(root, *args, **kwargs):
                result = original(root, *args, **kwargs)
                if (pathlib.Path(root) == self.root) == (phase == 'source'):
                    result['receipt']['production_authorized'] = True
                    result['receipt']['receipt_sha256'] = digest({
                        k: v for k, v in result['receipt'].items() if k != 'receipt_sha256'})
                return result
            with patch.object(qualified_cycle, 'select_g0_training_rows', side_effect=escalate):
                with self.subTest(phase=phase), self.assertRaises(ValueError):
                    self.execute()
        self.assertFalse(any((self.output / 'preparations').glob('*.json')))

    def preparation_cli(self, *, include_manifest=True, extra=()):
        args = [sys.executable, '-B', '-X', 'utf8', str(ROOT / 'scripts/habu_qualified_fit_cycle.py'),
                '--root', str(self.root), '--private-output', str(self.output), '--prepare-only']
        options = dict(self.parameters)
        if include_manifest:
            options.update(self.binding)
        for key, value in options.items():
            args.extend(['--'+key.replace('_', '-'), value])
        return subprocess.run(args + list(extra), cwd=self.fx.fixture.work,
                              capture_output=True, text=True, encoding='utf-8', timeout=30)

    def test_preparation_cli_validates_an_existing_declaration_without_fitting(self):
        result = self.preparation_cli()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')
        value = json.loads(result.stdout)
        self.assertEqual(value['status'], 'DECLARATION_PREPARED')
        self.assertEqual(value['source_authentication'], 'NOT_ATTESTED')
        self.assertEqual(value['new_real_fits'], 0)
        self.assertNotIn(str(self.fx.fixture.work), result.stdout)
        self.assertFalse((self.output / 'candidates').exists())

    def test_preparation_cli_missing_declaration_preserves_a_bound_private_ref_list(self):
        import hashlib
        ref = self.research_ref()
        path = self.root / 'evidence/research-sources.json'
        raw = canonical_bytes([ref]) + b'\n'
        path.write_bytes(raw)
        result = self.preparation_cli(include_manifest=False, extra=(
            '--research-sources-path', 'evidence/research-sources.json',
            '--research-sources-sha256', hashlib.sha256(raw).hexdigest()))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, '')
        value = json.loads(result.stdout)
        self.assertEqual(value['reason'], 'MISSING_SOURCE_QUALIFIED_G0_MANIFEST')
        self.assertNotIn(str(self.fx.fixture.work), result.stdout)
        prepared = self.output / 'inputs' / value['preparation_id']
        self.assertEqual((prepared / ref['path']).read_bytes(), (self.root / ref['path']).read_bytes())
        self.assertEqual((prepared / 'evidence/research-sources.json').read_bytes(), raw)

    def test_preparation_cli_duplicate_or_tampered_ref_list_fails_privately(self):
        import hashlib
        ref = self.research_ref()
        path = self.root / 'evidence/research-sources.json'
        raw = ('[{"path":"evidence/research-route.json","path":"other",'
               '"sha256":"'+ref['sha256']+'","size_bytes":'+str(ref['size_bytes'])+'}]').encode()
        path.write_bytes(raw)
        for sha in (hashlib.sha256(raw).hexdigest(), 'a'*64):
            result = self.preparation_cli(include_manifest=False, extra=(
                '--research-sources-path', 'evidence/research-sources.json',
                '--research-sources-sha256', sha))
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stderr, '')
            value = json.loads(result.stdout)
            self.assertEqual(value['status'], 'BLOCKED')
            self.assertNotIn(str(self.fx.fixture.work), result.stdout)
            self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
