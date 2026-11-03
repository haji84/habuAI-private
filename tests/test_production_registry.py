"""Pure proposal construction cannot activate a registry or authenticate data."""
import copy
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def checksum(value, newline=False):
    return hashlib.sha256(encoded(value) + (b'\n' if newline else b'')).hexdigest()


def fixture():
    """Invented metadata only; no real repository/ref/model or source payload."""
    repository = {'id': 123, 'full_name': 'example/research'}
    policy = {
        'schema_version': 'habu-production-proposal-policy-v1',
        'repository': repository, 'task_id': 'example/goal#1',
        'registry_root': 'registry/production',
        'record_directory': 'registry/production/proposals',
        'pointer_path': 'registry/production/current.json',
        'intent_prefix': 'protocols/production-intents',
        'allowed_operations': ['PROMOTE', 'ROLLBACK'], 'code_sha256': 'c' * 64,
    }
    pointer = {'event_sha256': 'b' * 64}
    predecessor = {
        'schema_version': 'habu-production-registry-predecessor-v1',
        'ref_commit_sha': 'a' * 40, 'current_event_sha256': 'b' * 64,
        'files': [
            {'path': 'registry/production/current.json', 'sha256': checksum(pointer, True)},
            {'path': 'registry/production/events/old.json', 'sha256': 'b' * 64},
        ],
        'current_pointer': pointer,
    }
    intent = {
        'schema_version': 'habu-production-transition-request-v1',
        'repository': copy.deepcopy(repository), 'task_id': 'example/goal#1',
        'operation': 'PROMOTE', 'expected_previous_event_sha256': 'b' * 64,
        'reviewed_intent': {'repository': copy.deepcopy(repository),
            'commit_sha': '8' * 40, 'path': 'protocols/production-intents/intent.json',
            'sha256': '9' * 64},
        'artifact_bindings': {'code_sha256': 'c' * 64,
            'policy_sha256': checksum(policy), 'model_sha256': 'd' * 64,
            'evidence_sha256': 'e' * 64, 'protocol_sha256': 'f' * 64},
    }
    return predecessor, intent, policy


class ProductionRegistryProposalTests(unittest.TestCase):
    def module(self):
        try:
            return importlib.import_module('production_registry')
        except ModuleNotFoundError:
            self.fail('Pure single-parent proposal constructor is not implemented')
    def call(self, predecessor, intent, policy, **kwargs):
        module = self.module()
        result = module.prepare_transition_proposal(predecessor, intent, policy=policy,
            expected_ref_sha=kwargs.pop('expected_ref_sha', 'a' * 40),
            expected_previous_event_sha256=kwargs.pop('expected_previous_event_sha256', 'b' * 64),
            **kwargs)
        self.assertIs(result['production_authorized'], False)
        self.assertIs(result['official_issuance_authorized'], False)
        self.assertIs(result['registry_activated'], False)
        self.assertEqual(result['source_authentication'], 'NOT_ATTESTED')
        self.assertEqual(result['scientific_reproduction'], 'NOT_REPRODUCED')
        return result

    def test_constructs_one_parent_addition_and_inert_pointer_descriptor(self):
        predecessor, intent, policy = fixture()
        result = self.call(predecessor, intent, policy)
        self.assertEqual(result['status'], 'PROPOSAL_NOT_ACTIVATED', result)
        self.assertEqual(result['reason_codes'], [])
        spec = result['commit_spec']
        self.assertEqual(spec['parents'], ['a' * 40])
        self.assertEqual(len(spec['immutable_additions']), 1)
        addition = spec['immutable_additions'][0]
        self.assertIs(addition.get('expected_absent'), True)
        raw = addition['content_utf8'].encode('utf-8')
        self.assertEqual(hashlib.sha256(raw).hexdigest(), addition['sha256'])
        self.assertEqual(len(raw), addition['size_bytes'])
        self.assertTrue(raw.endswith(b'\n'))
        self.assertEqual(addition['path'], 'registry/production/proposals/' + addition['sha256'] + '.json')
        record = json.loads(raw)
        self.assertEqual(record['status'], 'PROPOSAL_NOT_ACTIVATED')
        self.assertEqual(record['reviewed_intent'], intent['reviewed_intent'])
        self.assertEqual(record['artifact_bindings'], intent['artifact_bindings'])
        self.assertNotIn('activated_at', record)
        self.assertEqual(spec['pointer_update'], {
            'path': 'registry/production/current.json',
            'expected_file_sha256': checksum(predecessor['current_pointer'], True),
            'expected_previous_event_sha256': 'b' * 64,
            'next_proposal_sha256': addition['sha256'],
        })
        self.assertNotIn('content_utf8', spec['pointer_update'])
        self.assertNotIn('ref', spec)

    def test_deterministic_detached_output_and_unchanged_inputs(self):
        predecessor, intent, policy = fixture()
        before = copy.deepcopy((predecessor, intent, policy))
        first = self.call(predecessor, intent, policy)
        second = self.call(predecessor, intent, policy)
        self.assertEqual(first, second)
        self.assertEqual((predecessor, intent, policy), before)
        first['commit_spec']['parents'].append('0' * 40)
        self.assertEqual(second['commit_spec']['parents'], ['a' * 40])
        self.assertEqual(self.call(predecessor, intent, policy), second)

    def test_sibling_proposals_share_only_the_exact_observed_parent(self):
        predecessor, intent, policy = fixture()
        first = self.call(predecessor, intent, policy)
        intent['artifact_bindings']['model_sha256'] = '6' * 64
        second = self.call(predecessor, intent, policy)
        self.assertNotEqual(first['commit_spec']['immutable_additions'], second['commit_spec']['immutable_additions'])
        for result in (first, second):
            self.assertEqual(result['commit_spec']['parents'], ['a' * 40])
            self.assertEqual(result['commit_spec']['pointer_update']['expected_previous_event_sha256'], 'b' * 64)
            self.assertFalse(result['registry_activated'])

    def test_absent_predecessor_or_pointer_proof_never_bootstraps(self):
        for mutate in (lambda p: None, lambda p: dict(p, current_pointer=None),
                       lambda p: dict(p, files=p['files'][1:])):
            predecessor, intent, policy = fixture()
            result = self.call(mutate(predecessor), intent, policy)
            self.assertEqual(result['status'], 'BLOCKED', result)
            self.assertIsNone(result['commit_spec'])
        result = self.call(*fixture(), expected_ref_sha=None)
        self.assertEqual(result['status'], 'BLOCKED', result)

    def test_unavailable_predecessor_and_pointer_fields_are_not_contradictions(self):
        changes = (
            lambda p: p.pop('ref_commit_sha'),
            lambda p: p.update(ref_commit_sha=None),
            lambda p: p.pop('current_event_sha256'),
            lambda p: p.update(current_event_sha256=None),
            lambda p: p['current_pointer'].clear(),
            lambda p: p['current_pointer'].update(event_sha256=None),
            lambda p: p['files'][0].pop('sha256'),
            lambda p: p['files'][0].update(sha256=None),
        )
        for change in changes:
            with self.subTest(change=change):
                predecessor, intent, policy = fixture()
                change(predecessor)
                result = self.call(predecessor, intent, policy)
                self.assertEqual(result['status'], 'BLOCKED', result)
                self.assertIsNone(result['commit_spec'])

    def test_ref_event_pointer_and_request_contradictions_fail(self):
        mutations = (
            lambda p, i, _: p.update(ref_commit_sha='1' * 40),
            lambda p, i, _: p.update(current_event_sha256='1' * 64),
            lambda p, i, _: p['current_pointer'].update(event_sha256='1' * 64),
            lambda p, i, _: p['files'][0].update(sha256='1' * 64),
            lambda p, i, _: i.update(expected_previous_event_sha256='1' * 64),
        )
        for mutate in mutations:
            predecessor, intent, policy = fixture()
            mutate(predecessor, intent, policy)
            self.assertEqual(self.call(predecessor, intent, policy)['status'], 'FAIL')

    def test_reviewed_intent_repo_commit_path_hash_and_artifact_bindings(self):
        mutations = (
            lambda p, i, _: i['reviewed_intent'].update(commit_sha='wrong'),
            lambda p, i, _: i['reviewed_intent'].update(path='elsewhere/intent.json'),
            lambda p, i, _: i['reviewed_intent'].update(sha256='wrong'),
            lambda p, i, _: i['reviewed_intent']['repository'].update(id=999),
            lambda p, i, _: i['artifact_bindings'].update(code_sha256='1' * 64),
            lambda p, i, _: i['artifact_bindings'].update(policy_sha256='1' * 64),
            lambda p, i, _: i['artifact_bindings'].update(model_sha256=None),
        )
        for mutate in mutations:
            predecessor, intent, policy = fixture()
            mutate(predecessor, intent, policy)
            self.assertEqual(self.call(predecessor, intent, policy)['status'], 'FAIL')

    def test_scope_rejects_traversal_ambiguous_and_protected_paths(self):
        for path in ('../registry', '/registry', 'registry//x', 'registry/./x',
                     'registry\\x', 'C:registry', 'registry/\x00x', '.git/registry',
                     'data/raw/registry', 'predictions/original/registry'):
            predecessor, intent, policy = fixture()
            policy['registry_root'] = path
            intent['artifact_bindings']['policy_sha256'] = checksum(policy)
            self.assertEqual(self.call(predecessor, intent, policy)['status'], 'FAIL', path)
        predecessor, intent, policy = fixture()
        predecessor['files'][1]['path'] = 'registry/production-other/old.json'
        self.assertEqual(self.call(predecessor, intent, policy)['status'], 'FAIL')

    def test_pointer_and_record_layout_must_be_disjoint_inside_declared_scope(self):
        for changes in ({'record_directory': 'elsewhere/proposals'},
                        {'pointer_path': 'elsewhere/current.json'},
                        {'pointer_path': 'registry/production/proposals/current.json'},
                        {'pointer_path': 'registry/production'}):
            predecessor, intent, policy = fixture()
            policy.update(changes)
            intent['artifact_bindings']['policy_sha256'] = checksum(policy)
            self.assertEqual(self.call(predecessor, intent, policy)['status'], 'FAIL')

    def test_generated_record_path_must_fit_the_same_canonical_path_limit(self):
        predecessor, intent, policy = fixture()
        policy['record_directory'] = 'registry/production/' + 'x' * 235
        intent['artifact_bindings']['policy_sha256'] = checksum(policy)
        result = self.call(predecessor, intent, policy)
        self.assertEqual(result['status'], 'FAIL', result['status'])
        self.assertIsNone(result['commit_spec'])

    def test_existing_record_conflict_or_duplicate_never_overwrites(self):
        predecessor, intent, policy = fixture()
        addition = self.call(predecessor, intent, policy)['commit_spec']['immutable_additions'][0]
        for digest, status in ((addition['sha256'], 'BLOCKED'), ('0' * 64, 'FAIL')):
            source = copy.deepcopy(predecessor)
            source['files'].append({'path': addition['path'], 'sha256': digest})
            result = self.call(source, intent, policy)
            self.assertEqual(result['status'], status, result)
            self.assertIsNone(result['commit_spec'])

    def test_file_directory_conflicts_and_duplicate_paths_fail(self):
        for path in ('registry/production/proposals', 'registry/production/current.json/child'):
            predecessor, intent, policy = fixture()
            predecessor['files'].append({'path': path, 'sha256': '0' * 64})
            self.assertEqual(self.call(predecessor, intent, policy)['status'], 'FAIL')
        predecessor, intent, policy = fixture()
        predecessor['files'].append(copy.deepcopy(predecessor['files'][0]))
        self.assertEqual(self.call(predecessor, intent, policy)['status'], 'FAIL')

    def test_closed_contract_rejects_trust_delete_parent_and_clock_injection(self):
        for field, value in (('production_authorized', True), ('trusted', True),
                             ('parents', ['0' * 40, 'a' * 40]), ('delete', ['old.json']),
                             ('activated_at', '2026-11-04T12:00:00+09:00')):
            predecessor, intent, policy = fixture()
            intent[field] = value
            self.assertEqual(self.call(predecessor, intent, policy)['status'], 'FAIL', field)

    def test_exact_builtin_types_reject_bool_ids_and_custom_callbacks(self):
        predecessor, intent, policy = fixture()
        intent['repository']['id'] = True
        self.assertEqual(self.call(predecessor, intent, policy)['status'], 'FAIL')
        callbacks = []
        class Meta(type):
            def __eq__(self, other):
                callbacks.append('metaclass equality')
                raise AssertionError('custom metaclass called')
            def __hash__(self):
                callbacks.append('metaclass hash')
                raise AssertionError('custom metaclass called')
        class Foreign(metaclass=Meta):
            def __deepcopy__(self, memo):
                callbacks.append('copy')
                raise AssertionError('custom copy called')
        class ForeignDict(dict):
            def items(self):
                callbacks.append('mapping')
                raise AssertionError('custom mapping called')
        for foreign in (Foreign(), ForeignDict()):
            predecessor, intent, policy = fixture()
            intent['artifact_bindings']['model_sha256'] = foreign
            self.assertEqual(self.call(predecessor, intent, policy)['status'], 'FAIL')
        self.assertEqual(callbacks, [])

    def test_cycles_depth_strings_and_file_count_are_bounded(self):
        predecessor, intent, policy = fixture()
        intent['extra'] = intent
        self.assertNotEqual(self.call(predecessor, intent, policy)['status'], 'PROPOSAL_NOT_ACTIVATED')
        for value in ('x' * (65536 + 1), '\ud800'):
            predecessor, intent, policy = fixture()
            intent['task_id'] = value
            self.assertNotEqual(self.call(predecessor, intent, policy)['status'], 'PROPOSAL_NOT_ACTIVATED')
        predecessor, intent, policy = fixture()
        nested = []
        for _ in range(30):
            nested = [nested]
        intent['extra'] = nested
        self.assertEqual(self.call(predecessor, intent, policy)['status'], 'BLOCKED')
        predecessor, intent, policy = fixture()
        predecessor['files'] += [{'path': 'registry/production/events/' + str(i) + '.json', 'sha256': '0' * 64} for i in range(4097)]
        self.assertEqual(self.call(predecessor, intent, policy)['status'], 'BLOCKED')

    def test_invalid_budget_and_expired_budget_cannot_prepare(self):
        for seconds in (True, 0, -1, math.nan, math.inf, 31, 10**1000):
            self.assertEqual(self.call(*fixture(), max_seconds=seconds)['status'], 'FAIL')
        self.assertEqual(self.call(*fixture(), max_seconds=1e-12)['status'], 'BLOCKED')

    def test_hash_work_remains_inside_the_same_deadline(self):
        module = self.module()
        values = fixture()
        actual_sha = hashlib.sha256
        clock = [0.0]
        class SlowHash:
            def __init__(self, data=b''):
                self.actual = actual_sha(data)
                if data:
                    clock[0] = 2.0
            def update(self, data):
                self.actual.update(data)
                clock[0] = 2.0
            def hexdigest(self):
                return self.actual.hexdigest()
        with patch.object(module, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(module.hashlib, 'sha256', SlowHash):
            self.assertEqual(self.call(*values)['status'], 'BLOCKED')

    def test_constructor_never_opens_files_or_starts_process_or_network(self):
        self.module()
        values = fixture()
        with patch('builtins.open', side_effect=AssertionError('file I/O')), \
             patch('os.open', side_effect=AssertionError('file I/O')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')), \
             patch('socket.socket', side_effect=AssertionError('network')):
            self.assertEqual(self.call(*values)['status'], 'PROPOSAL_NOT_ACTIVATED')

    def test_rollback_is_an_unexecuted_intention_and_policy_can_forbid_it(self):
        predecessor, intent, policy = fixture()
        intent['operation'] = 'ROLLBACK'
        result = self.call(predecessor, intent, policy)
        self.assertEqual(result['status'], 'PROPOSAL_NOT_ACTIVATED')
        policy['allowed_operations'] = ['PROMOTE']
        intent['artifact_bindings']['policy_sha256'] = checksum(policy)
        self.assertEqual(self.call(predecessor, intent, policy)['status'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
