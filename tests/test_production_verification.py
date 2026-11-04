"""Synthetic data-only exact-fact checks never authenticate a production action."""
import copy
import importlib
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from master_contracts import digest


def page(items, **scope):
    return dict(scope, total_count=len(items), per_page=100,
                pages=[dict(page=1, has_next=False, items=items)])


def fixture(method='MERGE', mode='HEAD'):
    """Every identifier/hash below is invented; none is authenticated evidence."""
    a, h, merged, current, synthetic = [c * 40 for c in 'abcde']
    head_tree, base_tree = 'f' * 40, '0' * 40
    repository = dict(id=123, full_name='example/research', default_branch='main')
    code = [{'path': 'src/example.py', 'sha256': '1' * 64}]
    policy = dict(schema_version='habu-exact-fact-policy-v1',
        repository=copy.deepcopy(repository), task_id='example/goal#1',
        allowed_operations=['PROMOTE', 'ROLLBACK'],
        allowed_merge_methods=['MERGE', 'SQUASH', 'REBASE'],
        allowed_paths=['src/', 'protocols/intent.json'],
        required_workflows=[dict(workflow_id=10,
            path='.github/workflows/verify.yml', definition_sha256='2' * 64,
            event='push' if mode == 'MERGED' else 'pull_request',
            checkout_mode=mode,
            required_jobs=[dict(name='verify', steps=['Checkout', 'Assert revision', 'Test'])])],
        allowed_reviewer_ids=[7, 8], min_approvals=1,
        max_fact_age_seconds=3600)
    bindings = dict(code_sha256=digest({x['path']: x['sha256'] for x in code}),
        policy_sha256=digest(policy), model_sha256='3' * 64,
        evidence_sha256='4' * 64, protocol_sha256='5' * 64)
    tested = synthetic if mode == 'PR_MERGE' else merged if mode == 'MERGED' else h
    intent = dict(schema_version='habu-exact-fact-intent-v1',
        repository=copy.deepcopy(repository), task_id='example/goal#1',
        operation='PROMOTE', pr_number=42, base_sha=a, head_sha=h,
        head_tree_sha=head_tree, merge_tree_sha=head_tree,
        code_manifest=copy.deepcopy(code), artifact_bindings=copy.deepcopy(bindings),
        ci_runs=[dict(workflow_id=10, run_id=100, attempt=1,
            tested_sha=tested, tested_tree_sha=head_tree, definition_commit_sha=h)],
        assessed_at='2026-11-04T12:00:00+09:00')
    parents = [a, h] if method == 'MERGE' else [a]
    commits = [dict(sha=a, tree_sha=base_tree, parents=[]),
        dict(sha=h, tree_sha=head_tree, parents=[a]),
        dict(sha=merged, tree_sha=head_tree, parents=parents),
        dict(sha=current, tree_sha='6' * 40, parents=[merged]),
        dict(sha=synthetic, tree_sha=head_tree, parents=[a, h])]
    steps = [dict(number=n, name=name, status='completed', conclusion='success')
             for n, name in zip((1, 3, 9), ('Checkout', 'Assert revision', 'Test'))]
    job = dict(id=1000, name='verify', run_id=100, attempt=1,
        status='completed', conclusion='success', steps_complete=True, steps=steps,
        checkout=dict(sha=tested, tree_sha=head_tree, evidence_sha256='7' * 64))
    check = dict(workflow_id=10, workflow_path='.github/workflows/verify.yml',
        definition_sha256='2' * 64, definition_commit_sha=h,
        repository_id=123, run_id=100, attempt=1, latest_attempt=1,
        event='push' if mode == 'MERGED' else 'pull_request',
        head_branch='main' if mode == 'MERGED' else 'feature',
        pr_number=None if mode == 'MERGED' else 42,
        run_head_sha=merged if mode == 'MERGED' else h,
        status='completed', conclusion='success',
        jobs=page([job], run_id=100, attempt=1))
    review = dict(id=200, actor_id=7, state='APPROVED', commit_sha=h,
                  submitted_at='2026-11-04T11:00:00+09:00')
    facts = dict(schema_version='habu-exact-facts-v1',
        observed_at='2026-11-04T11:59:00+09:00',
        repository=dict(repository, default_head_sha=current),
        pr=dict(number=42, base_repository_id=123, head_repository_id=123,
            base_branch='main', head_branch='feature', base_sha=a, head_sha=h,
            author_id=9, state='closed', draft=False, merged=True,
            merge_commit_sha=merged), commits=commits,
        changed_files=page([dict(path='src/example.py', status='modified', previous_path=None)],
                           repository_id=123, pr_number=42),
        ci=[check], reviews=page([review], repository_id=123, pr_number=42),
        workflow_definitions=[dict(commit_sha=h, tree_sha=head_tree,
            path='.github/workflows/verify.yml', sha256='2' * 64)],
        closures=[dict(commit_sha=s, files=copy.deepcopy(code),
            artifact_bindings=copy.deepcopy(bindings)) for s in dict.fromkeys((h, tested, merged))],
        merge=dict(method=method, prior_default_sha=a, commit_sha=merged))
    return facts, intent, policy


def optional_job(facts):
    required = facts['ci'][0]['jobs']['pages'][0]['items'][0]
    extra = copy.deepcopy(required)
    extra.update(id=1001, name='optional', checkout=None)
    facts['ci'][0]['jobs'] = page([required, extra], run_id=100, attempt=1)
    return extra


class ProductionVerificationTests(unittest.TestCase):
    def verify(self, facts, intent, policy, **kwargs):
        try:
            module = importlib.import_module('production_verification')
        except ModuleNotFoundError:
            self.fail('The pure exact-fact verifier is not implemented')
        result = module.verify_exact_facts(facts, intent=intent, policy=policy, **kwargs)
        self.assertEqual(result['source_authentication'], 'NOT_ATTESTED_BY_PURE_VALIDATOR')
        self.assertEqual(result['scientific_reproduction'], 'NOT_REPRODUCED')
        self.assertIs(result['production_authorized'], False)
        self.assertIs(result['official_issuance_authorized'], False)
        return result

    def consistent(self, facts, intent, policy):
        result = self.verify(facts, intent, policy)
        self.assertEqual(result['fact_consistency'], 'CONSISTENT_NOT_AUTHENTICATED', result)
        self.assertEqual(result['reason_codes'], [])
        return result

    def blocked(self, facts, intent, policy, code=None, **kwargs):
        result = self.verify(facts, intent, policy, **kwargs)
        self.assertEqual(result['fact_consistency'], 'BLOCKED', result)
        if code:
            self.assertIn(code, result['reason_codes'])
        return result

    def failed(self, facts, intent, policy, code=None, **kwargs):
        result = self.verify(facts, intent, policy, **kwargs)
        self.assertEqual(result['fact_consistency'], 'FAIL', result)
        if code:
            self.assertIn(code, result['reason_codes'])
        return result

    def test_invented_coherent_json_is_consistent_never_authenticated(self):
        facts, intent, policy = fixture()
        original = copy.deepcopy((facts, intent, policy))
        result = self.consistent(facts, intent, policy)
        self.assertEqual((facts, intent, policy), original)
        self.assertEqual(result['computed']['intent_sha256'], digest(intent))
        self.assertEqual(result['computed']['policy_sha256'], digest(policy))
        self.assertEqual(result['computed']['facts_sha256'], digest(facts))

    def test_merge_squash_and_rebase_do_not_require_old_head_ancestry(self):
        for method in ('MERGE', 'SQUASH', 'REBASE'):
            with self.subTest(method=method):
                facts, intent, policy = fixture(method)
                self.consistent(facts, intent, policy)

    def test_exact_head_synthetic_merge_and_fresh_main_are_distinct(self):
        for mode in ('HEAD', 'PR_MERGE', 'MERGED'):
            with self.subTest(mode=mode):
                self.consistent(*fixture(mode=mode))

    def test_missing_facts_and_open_pr_are_blocked(self):
        facts, intent, policy = fixture()
        self.blocked({}, intent, policy, 'MISSING_FIELDS')
        facts['pr'].update(state='open', merged=False, merge_commit_sha=None)
        facts['merge'] = None
        intent['merge_tree_sha'] = None
        self.blocked(facts, intent, policy, 'PR_NOT_MERGED')

    def test_unrelated_workflow_and_old_attempt_are_rejected(self):
        facts, intent, policy = fixture()
        facts['ci'][0]['workflow_path'] = '.github/workflows/other.yml'
        self.failed(facts, intent, policy, 'WORKFLOW_IDENTITY')
        facts, intent, policy = fixture()
        facts['ci'][0]['latest_attempt'] = 2
        self.blocked(facts, intent, policy, 'STALE_CI_ATTEMPT')

    def test_truncated_jobs_and_missing_required_step_are_blocked(self):
        facts, intent, policy = fixture()
        facts['ci'][0]['jobs']['pages'][0]['has_next'] = True
        self.blocked(facts, intent, policy, 'INCOMPLETE_PAGINATION')
        facts, intent, policy = fixture()
        facts['ci'][0]['jobs']['pages'][0]['items'][0]['steps'].pop()
        self.blocked(facts, intent, policy, 'REQUIRED_STEP_MISSING')

    def test_neutral_comment_does_not_erase_current_approval(self):
        facts, intent, policy = fixture()
        comment = dict(facts['reviews']['pages'][0]['items'][0], id=201,
            state='COMMENTED', submitted_at='2026-11-04T11:30:00+09:00')
        facts['reviews'] = page(facts['reviews']['pages'][0]['items'] + [comment],
                               repository_id=123, pr_number=42)
        self.consistent(facts, intent, policy)

    def test_bool_identifiers_and_injected_authority_fail(self):
        facts, intent, policy = fixture()
        facts['pr']['number'] = True
        self.failed(facts, intent, policy, 'INTEGER_REQUIRED')
        facts, intent, policy = fixture()
        facts['production_authorized'] = True
        self.failed(facts, intent, policy, 'UNEXPECTED_FIELDS')

    def test_repository_fork_head_and_default_branch_mismatches(self):
        changes = [('head_repository_id', 999, 'PR_IDENTITY_OR_FORK'),
                   ('head_sha', '9' * 40, 'PR_REVISION_MOVED'),
                   ('base_branch', 'other', 'PR_BASE_BRANCH')]
        for key, value, code in changes:
            with self.subTest(key=key):
                facts, intent, policy = fixture()
                facts['pr'][key] = value
                self.failed(facts, intent, policy, code)
        facts, intent, policy = fixture()
        facts['repository']['id'] = 999
        self.failed(facts, intent, policy, 'REPOSITORY_IDENTITY')

    def test_changed_scope_includes_both_rename_paths_and_prefix_boundary(self):
        for name, previous, status in [('src-other/x.py', None, 'added'),
                ('src/new.py', 'data/raw/original', 'renamed'),
                ('data/raw/original', 'src/old.py', 'renamed')]:
            facts, intent, policy = fixture()
            facts['changed_files']['pages'][0]['items'][0] = dict(path=name, previous_path=previous, status=status)
            self.failed(facts, intent, policy, 'CHANGED_PATH_SCOPE')
        facts, intent, policy = fixture()
        facts['changed_files']['pages'][0]['items'][0].update(
            path='src/new.py', previous_path='src/old.py', status='renamed')
        self.consistent(facts, intent, policy)

    def test_canonical_paths_reject_traversal_controls_and_backslashes(self):
        for path in ('/src/a', 'src/../a', 'src/./a', 'src//a', 'src\\a', 'C:/src/a', 'src/a\n'):
            facts, intent, policy = fixture()
            facts['changed_files']['pages'][0]['items'][0]['path'] = path
            self.failed(facts, intent, policy)

    def test_policy_code_and_relevant_closure_hashes_are_recomputed(self):
        facts, intent, policy = fixture()
        intent['code_manifest'][0]['sha256'] = '9' * 64
        self.failed(facts, intent, policy, 'INTENT_BINDING')
        facts, intent, policy = fixture()
        policy['allowed_paths'].append('extra/')
        self.failed(facts, intent, policy, 'INTENT_BINDING')
        facts, intent, policy = fixture()
        facts['closures'][0]['files'][0]['sha256'] = '9' * 64
        self.failed(facts, intent, policy, 'CLOSURE_BINDING')
        facts, intent, policy = fixture()
        facts['closures'].pop()
        self.blocked(facts, intent, policy, 'CLOSURE_FACT_MISSING')

    def test_complete_two_page_collections_are_accepted(self):
        facts, intent, policy = fixture()
        old = facts['changed_files']['pages'][0]['items'][0]
        facts['changed_files'] = dict(repository_id=123, pr_number=42, total_count=2, per_page=1,
            pages=[dict(page=1, has_next=True, items=[old]),
                   dict(page=2, has_next=False, items=[dict(path='src/second.py', status='added', previous_path=None)])])
        self.consistent(facts, intent, policy)

    def test_missing_pages_conflicting_counts_and_duplicate_items(self):
        for collection in ('changed_files', 'reviews'):
            facts, intent, policy = fixture()
            facts[collection]['pages'][0]['page'] = 2
            self.blocked(facts, intent, policy, 'INCOMPLETE_PAGINATION')
            facts, intent, policy = fixture()
            facts[collection]['total_count'] = 2
            self.blocked(facts, intent, policy, 'INCOMPLETE_PAGINATION')
            facts, intent, policy = fixture()
            facts[collection]['pages'][0]['items'] *= 2
            facts[collection]['total_count'] = 2
            self.failed(facts, intent, policy)
        facts, intent, policy = fixture()
        facts['ci'][0]['jobs']['attempt'] = 2
        self.failed(facts, intent, policy, 'COLLECTION_SCOPE')

    def test_run_head_cannot_substitute_for_actual_checkout(self):
        facts, intent, policy = fixture()
        facts['ci'][0]['jobs']['pages'][0]['items'][0]['checkout']['sha'] = 'e' * 40
        self.failed(facts, intent, policy, 'ACTUAL_CHECKOUT_MISMATCH')
        facts, intent, policy = fixture(mode='MERGED')
        facts['ci'][0]['run_head_sha'] = intent['head_sha']
        self.failed(facts, intent, policy, 'RUN_HEAD_SHA')

    def test_synthetic_merge_needs_ordered_base_head_parents_and_exact_tree(self):
        facts, intent, policy = fixture(mode='PR_MERGE')
        synthetic = next(c for c in facts['commits'] if c['sha'] == 'e' * 40)
        synthetic['parents'].reverse()
        self.failed(facts, intent, policy, 'SYNTHETIC_MERGE_MAPPING')
        facts, intent, policy = fixture(mode='PR_MERGE')
        next(c for c in facts['commits'] if c['sha'] == 'e' * 40)['tree_sha'] = '8' * 40
        self.failed(facts, intent, policy, 'TESTED_TREE')

    def test_missing_or_unrelated_workflow_definition_revision_is_not_a_binding(self):
        facts, intent, policy = fixture()
        unrelated = dict(sha='8' * 40, tree_sha='9' * 40, parents=[])
        facts['commits'].append(unrelated)
        intent['ci_runs'][0]['definition_commit_sha'] = unrelated['sha']
        facts['ci'][0]['definition_commit_sha'] = unrelated['sha']
        self.failed(facts, intent, policy, 'WORKFLOW_DEFINITION_REVISION')
        facts, intent, policy = fixture()
        intent['ci_runs'][0]['definition_commit_sha'] = '8' * 40
        facts['ci'][0]['definition_commit_sha'] = '8' * 40
        self.blocked(facts, intent, policy, 'COMMIT_FACT_MISSING')

    def test_definition_file_tree_path_and_bytes_are_bound_separately_from_checkout(self):
        for key, value, code in [('tree_sha', '9' * 40, 'WORKFLOW_DEFINITION_TREE'),
                ('sha256', '9' * 64, 'WORKFLOW_DEFINITION_HASH')]:
            facts, intent, policy = fixture()
            facts['workflow_definitions'][0][key] = value
            self.failed(facts, intent, policy, code)
        facts, intent, policy = fixture()
        facts['workflow_definitions'][0]['path'] = '.github/workflows/other.yml'
        self.blocked(facts, intent, policy, 'WORKFLOW_DEFINITION_MISSING')
        facts, intent, policy = fixture()
        facts['workflow_definitions'] = []
        self.blocked(facts, intent, policy, 'WORKFLOW_DEFINITION_MISSING')
        # MERGED checkout is c, but the explicitly provided reviewed definition
        # is at h; no global equation of definition SHA and checkout SHA.
        self.consistent(*fixture(mode='MERGED'))

    def test_latest_current_attempt_failure_and_pending_are_not_old_success(self):
        facts, intent, policy = fixture()
        ci = facts['ci'][0]
        ci.update(attempt=2, latest_attempt=2, conclusion='failure')
        intent['ci_runs'][0]['attempt'] = 2
        self.failed(facts, intent, policy, 'REQUIRED_CI_NOT_SUCCESS')
        facts, intent, policy = fixture()
        facts['ci'][0].update(status='in_progress', conclusion=None)
        self.blocked(facts, intent, policy, 'CI_NOT_COMPLETED')

    def test_required_skipped_neutral_failed_jobs_or_steps_do_not_pass(self):
        for level in ('job', 'step'):
            for conclusion in ('failure', 'skipped', 'neutral'):
                facts, intent, policy = fixture()
                job = facts['ci'][0]['jobs']['pages'][0]['items'][0]
                row = job if level == 'job' else job['steps'][1]
                row['conclusion'] = conclusion
                self.failed(facts, intent, policy, 'REQUIRED_CI_NOT_SUCCESS')

    def test_missing_jobs_steps_or_checkout_do_not_pass(self):
        facts, intent, policy = fixture()
        facts['ci'][0]['jobs'] = page([], run_id=100, attempt=1)
        self.blocked(facts, intent, policy, 'REQUIRED_JOB_MISSING')
        facts, intent, policy = fixture()
        facts['ci'][0]['jobs']['pages'][0]['items'][0]['steps_complete'] = False
        self.blocked(facts, intent, policy, 'STEPS_INCOMPLETE')
        facts, intent, policy = fixture()
        facts['ci'][0]['jobs']['pages'][0]['items'][0]['checkout'] = None
        self.blocked(facts, intent, policy, 'MISSING_FACT')

    def test_duplicate_job_step_and_wrong_attempt_ids_reject(self):
        facts, intent, policy = fixture()
        jobs = facts['ci'][0]['jobs']['pages'][0]['items']
        facts['ci'][0]['jobs'] = page(jobs * 2, run_id=100, attempt=1)
        self.failed(facts, intent, policy, 'DUPLICATE_JOB')
        facts, intent, policy = fixture()
        job = facts['ci'][0]['jobs']['pages'][0]['items'][0]
        job['steps'][1]['number'] = 1
        self.failed(facts, intent, policy, 'DUPLICATE_STEP')
        facts, intent, policy = fixture()
        facts['ci'][0]['jobs']['pages'][0]['items'][0]['attempt'] = 2
        self.failed(facts, intent, policy, 'JOB_ATTEMPT_SCOPE')

    def test_same_name_matrix_jobs_all_need_success(self):
        facts, intent, policy = fixture()
        job = facts['ci'][0]['jobs']['pages'][0]['items'][0]
        other = dict(copy.deepcopy(job), id=1001, conclusion='failure')
        facts['ci'][0]['jobs'] = page([job, other], run_id=100, attempt=1)
        self.failed(facts, intent, policy, 'REQUIRED_CI_NOT_SUCCESS')

    def test_stale_dismissed_author_and_nonallowed_approvals_cannot_count(self):
        for key, value in [('commit_sha', 'a' * 40), ('state', 'DISMISSED'),
                           ('actor_id', 9), ('actor_id', 999)]:
            facts, intent, policy = fixture()
            facts['reviews']['pages'][0]['items'][0][key] = value
            self.blocked(facts, intent, policy, 'INDEPENDENT_APPROVALS_MISSING')

    def test_later_changes_or_dismissal_do_not_resurrect_old_approval(self):
        for state, code in [('CHANGES_REQUESTED', 'UNRESOLVED_CHANGES_REQUESTED'),
                            ('DISMISSED', 'INDEPENDENT_APPROVALS_MISSING')]:
            facts, intent, policy = fixture()
            review = facts['reviews']['pages'][0]['items'][0]
            later = dict(review, id=201, state=state, commit_sha='a' * 40,
                         submitted_at='2026-11-04T11:30:00+09:00')
            facts['reviews'] = page([review, later], repository_id=123, pr_number=42)
            self.blocked(facts, intent, policy, code)

    def test_pending_review_and_shuffled_order_are_neutral(self):
        facts, intent, policy = fixture()
        review = facts['reviews']['pages'][0]['items'][0]
        pending = dict(review, id=201, state='PENDING', submitted_at=None, commit_sha=None)
        for rows in ([review, pending], [pending, review]):
            facts['reviews'] = page(rows, repository_id=123, pr_number=42)
            self.consistent(facts, intent, policy)

    def test_ambiguous_same_time_decisive_reviews_block_regardless_of_ids(self):
        facts, intent, policy = fixture()
        review = facts['reviews']['pages'][0]['items'][0]
        conflict = dict(review, id=201, state='CHANGES_REQUESTED')
        for rows in ([review, conflict], [conflict, review]):
            facts['reviews'] = page(rows, repository_id=123, pr_number=42)
            self.blocked(facts, intent, policy, 'AMBIGUOUS_EFFECTIVE_REVIEW')

    def test_default_ancestry_must_be_proven_not_just_matching_branch_name(self):
        facts, intent, policy = fixture()
        facts['commits'] = [x for x in facts['commits'] if x['sha'] != 'd' * 40]
        self.blocked(facts, intent, policy, 'ANCESTRY_FACTS_INCOMPLETE')
        facts, intent, policy = fixture()
        next(x for x in facts['commits'] if x['sha'] == 'd' * 40)['parents'] = ['a' * 40]
        self.failed(facts, intent, policy, 'NOT_ANCESTOR')

    def test_squash_tree_and_merge_parent_mappings_are_exact(self):
        facts, intent, policy = fixture('SQUASH')
        next(x for x in facts['commits'] if x['sha'] == 'c' * 40)['tree_sha'] = '8' * 40
        self.failed(facts, intent, policy, 'COMMIT_TREE_MAPPING')
        facts, intent, policy = fixture()
        next(x for x in facts['commits'] if x['sha'] == 'c' * 40)['parents'].reverse()
        self.failed(facts, intent, policy, 'MERGE_PARENTS')

    def test_rebase_multi_commit_chain_can_omit_original_head_ancestry(self):
        facts, intent, policy = fixture('REBASE')
        intermediate = dict(sha='8' * 40, tree_sha='9' * 40, parents=['a' * 40])
        facts['commits'].append(intermediate)
        next(x for x in facts['commits'] if x['sha'] == 'c' * 40)['parents'] = [intermediate['sha']]
        self.consistent(facts, intent, policy)

    def test_freshness_and_timezone_are_explicit_supplied_time_comparisons(self):
        facts, intent, policy = fixture()
        facts['observed_at'] = '2026-11-03T11:59:00+09:00'
        self.blocked(facts, intent, policy, 'STALE_FACTS')
        facts, intent, policy = fixture()
        facts['observed_at'] = '2099-01-01T00:00:00Z'
        self.failed(facts, intent, policy, 'FUTURE_FACTS')
        facts, intent, policy = fixture()
        facts['observed_at'] = '2026-11-04T11:59:00'
        self.failed(facts, intent, policy, 'AWARE_TIME_REQUIRED')

    def test_null_required_facts_block_instead_of_demanding_invented_values(self):
        for target, key in [('pr', 'number'), ('facts', 'reviews'), ('facts', 'ci')]:
            facts, intent, policy = fixture()
            (facts if target == 'facts' else facts[target])[key] = None
            self.blocked(facts, intent, policy)

    def test_all_numeric_identifiers_counts_attempts_reject_boolean_and_float(self):
        for value in (True, 1.0):
            for target, key in [('ci', 'attempt'), ('page', 'total_count'), ('review', 'actor_id')]:
                facts, intent, policy = fixture()
                row = facts['ci'][0] if target == 'ci' else facts['reviews'] if target == 'page' else facts['reviews']['pages'][0]['items'][0]
                row[key] = value
                self.failed(facts, intent, policy, 'INTEGER_REQUIRED')

    def test_input_is_exact_builtin_data_and_never_invokes_custom_methods(self):
        class ExecutableDict(dict):
            def items(self):
                raise AssertionError('Candidate code executed')
        facts, intent, policy = fixture()
        self.failed(ExecutableDict(facts), intent, policy, 'JSON_BUILTIN_TYPES_REQUIRED')
        facts['extra'] = object()
        self.failed(facts, intent, policy, 'JSON_BUILTIN_TYPES_REQUIRED')

    def test_nonfinite_scalar_integer_range_and_cycles_reject(self):
        for value in (math.nan, math.inf, -math.inf):
            facts, intent, policy = fixture()
            facts['extra'] = value
            self.failed(facts, intent, policy, 'NONFINITE_NUMBER')
        facts, intent, policy = fixture()
        facts['pr']['number'] = 2**100
        self.failed(facts, intent, policy, 'INTEGER_RANGE')
        facts, intent, policy = fixture()
        facts['cycle'] = facts
        self.failed(facts, intent, policy, 'CYCLIC_INPUT')

    def test_resource_limits_and_deadline_are_blocked(self):
        facts, intent, policy = fixture()
        deep = 0
        for _ in range(30):
            deep = [deep]
        facts['extra'] = deep
        self.blocked(facts, intent, policy, 'STRUCTURE_LIMIT')
        facts, intent, policy = fixture()
        facts['extra'] = ['x' * 16_000] * 300
        self.blocked(facts, intent, policy, 'BYTE_LIMIT')
        facts, intent, policy = fixture()
        facts['extra'] = [list(range(4096)) for _ in range(13)]
        self.blocked(facts, intent, policy, 'STRUCTURE_LIMIT')
        module = importlib.import_module('production_verification')
        with patch.object(module.time, 'monotonic', side_effect=[0.0, 2.0]):
            self.blocked(*fixture(), code='DEADLINE')

    def test_budget_is_typed_finite_and_bounded(self):
        for budget in (True, math.nan, math.inf, 0, -1, 6, '1'):
            self.failed(*fixture(), max_seconds=budget, code='INVALID_BUDGET')

    def test_positive_calculation_has_no_network_process_or_filesystem_io(self):
        import os
        import socket
        import subprocess
        importlib.import_module('production_verification')
        facts, intent, policy = fixture()
        with patch('builtins.open', side_effect=AssertionError('file IO')), \
                patch.object(os, 'open', side_effect=AssertionError('file IO')), \
                patch.object(socket.socket, 'connect', side_effect=AssertionError('network')), \
                patch.object(subprocess, 'Popen', side_effect=AssertionError('process')), \
                patch.object(Path, 'write_text', side_effect=AssertionError('write')):
            self.consistent(facts, intent, policy)

    def test_rejected_metaclasses_cannot_execute_equality_or_conversion_callbacks(self):
        calls = []
        class Meta(type):
            def __eq__(cls, other):
                calls.append('metaclass equality')
                return False
        class Probe(metaclass=Meta):
            def __float__(self):
                calls.append('float conversion')
                return 1.0
        facts, intent, policy = fixture()
        facts['probe'] = Probe()
        self.failed(facts, intent, policy, 'JSON_BUILTIN_TYPES_REQUIRED')
        self.assertEqual(calls, [])
        self.failed(*fixture(), max_seconds=Probe(), code='INVALID_BUDGET')
        self.assertEqual(calls, [])

    def test_oversize_builtin_string_rejects_before_secondary_encoding_allocation(self):
        import tracemalloc
        importlib.import_module('production_verification')
        facts, intent, policy = fixture()
        facts['oversize'] = 'x' * 1_000_000
        tracemalloc.start()
        try:
            self.blocked(facts, intent, policy, 'STRING_LIMIT')
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertLess(peak, 256_000)

    def test_rebase_mapping_is_a_single_parent_replacement_chain(self):
        facts, intent, policy = fixture('REBASE')
        next(c for c in facts['commits'] if c['sha'] == 'c' * 40)['parents'] = ['a' * 40, 'b' * 40]
        self.failed(facts, intent, policy, 'REBASE_PARENT_CHAIN')

    def test_duplicate_job_ids_across_distinct_workflow_runs_reject(self):
        facts, intent, policy = fixture()
        rule = copy.deepcopy(policy['required_workflows'][0])
        rule.update(workflow_id=11, path='.github/workflows/second.yml')
        policy['required_workflows'].append(rule)
        intent['ci_runs'].append(dict(intent['ci_runs'][0], workflow_id=11, run_id=101))
        second = copy.deepcopy(facts['ci'][0])
        second.update(workflow_id=11, workflow_path=rule['path'], run_id=101)
        second['jobs']['run_id'] = 101
        second['jobs']['pages'][0]['items'][0]['run_id'] = 101
        facts['ci'].append(second)
        facts['workflow_definitions'].append(dict(facts['workflow_definitions'][0], path=rule['path']))
        checksum = digest(policy)
        intent['artifact_bindings']['policy_sha256'] = checksum
        for closure in facts['closures']:
            closure['artifact_bindings']['policy_sha256'] = checksum
        self.failed(facts, intent, policy, 'DUPLICATE_JOB')
        second['jobs']['pages'][0]['items'][0]['id'] = 1001
        self.consistent(facts, intent, policy)

    def test_malformed_optional_job_status_conclusion_and_steps_reject(self):
        for key, value in [('status', True), ('conclusion', {'bad': 'shape'}), ('steps', False),
                           ('steps_complete', 1)]:
            with self.subTest(key=key):
                facts, intent, policy = fixture()
                optional_job(facts)[key] = value
                self.failed(facts, intent, policy)

    def test_optional_steps_have_typed_status_conclusion_ids_and_closed_fields(self):
        for key, value in [('number', True), ('status', False),
                           ('conclusion', {'bad': 'shape'}), ('authority', True)]:
            with self.subTest(key=key):
                facts, intent, policy = fixture()
                optional_job(facts)['steps'][0][key] = value
                self.failed(facts, intent, policy)
        facts, intent, policy = fixture()
        job = optional_job(facts)
        job['steps'][1]['number'] = job['steps'][0]['number']
        self.failed(facts, intent, policy, 'DUPLICATE_STEP')

    def test_supplied_optional_checkout_has_a_strict_hash_bound_shape(self):
        for checkout in (True, {'sha': False, 'tree_sha': '8' * 40, 'evidence_sha256': '7' * 64},
                         {'sha': '9' * 40, 'tree_sha': '8' * 40, 'evidence_sha256': '7' * 64, 'trusted': True}):
            facts, intent, policy = fixture()
            optional_job(facts)['checkout'] = checkout
            self.failed(facts, intent, policy)
        facts, intent, policy = fixture()
        optional_job(facts)['checkout'] = {'sha': '9' * 40, 'evidence_sha256': '7' * 64}
        self.blocked(facts, intent, policy, 'MISSING_FIELDS')

    def test_optional_failure_skipped_cancelled_and_other_checkout_are_valid(self):
        for conclusion in ('failure', 'skipped', 'cancelled', 'neutral'):
            facts, intent, policy = fixture()
            job = optional_job(facts)
            job['conclusion'] = conclusion
            job['steps'] = [] if conclusion == 'skipped' else [dict(
                number=4, name='Optional check', status='completed', conclusion=conclusion)]
            self.consistent(facts, intent, policy)
        facts, intent, policy = fixture()
        optional_job(facts)['checkout'] = dict(sha='9' * 40, tree_sha='8' * 40, evidence_sha256='7' * 64)
        self.consistent(facts, intent, policy)


if __name__ == '__main__':
    unittest.main()
