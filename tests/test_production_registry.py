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


def core_document(path, value):
    raw = encoded(value) + b'\n'
    return dict(path=path, sha256=hashlib.sha256(raw).hexdigest(),
                size_bytes=len(raw), content_utf8=raw.decode('utf-8'))


def core_fixture():
    """Declared existing anchor, never a genesis constructor or real model."""
    root = 'example/state'
    manifest = [{'path': 'src/example.py', 'sha256': 'c' * 64}]
    code = checksum({r['path']: r['sha256'] for r in manifest})
    event = dict(schema_version='habu-registry-activation-v1', operation_id='anchor-op',
        operation='PROMOTE', previous_event_sha256='9' * 64, model_sha256='d' * 64,
        code_sha256=code, code_manifest=manifest, protocol_sha256='e' * 64,
        policy_sha256='f' * 64, evidence_sha256='a' * 64,
        intent_sha256='b' * 64, gate_decision_sha256='c' * 64,
        reviewed_ref=dict(commit_sha='2' * 40, path='protocols/intents/anchor.json', sha256='b' * 64),
        merged_ref=dict(commit_sha='3' * 40, tree_sha='4' * 40, facts_sha256='5' * 64,
                        merged_at='2026-11-03T00:00:00+00:00'),
        observed_at='2026-11-03T01:00:00+00:00')
    event['event_sha256'] = checksum(event)
    pointer = dict(schema_version='habu-registry-pointer-v1', event_sha256=event['event_sha256'])
    index = dict(schema_version='habu-registry-version-index-v1', nights=[])
    files = [core_document(root+'/events/'+event['event_sha256']+'.json', event),
             core_document(root+'/current.json', pointer), core_document(root+'/versions.json', index)]
    policy = dict(schema_version='habu-registry-core-policy-v1',
        repository=dict(id=123, full_name='example/research'), task_id='example/goal#1',
        state_ref='refs/heads/example-state', registry_root=root,
        event_directory=root+'/events', issuance_directory=root+'/issuances',
        pointer_path=root+'/current.json', version_index_path=root+'/versions.json',
        intent_prefix='protocols/intents',
        anchor=dict(commit_sha='1' * 40, root_event_sha256=event['event_sha256'],
                    files_sha256=checksum({d['path']:d['sha256'] for d in files})),
        compatible_code_sha256=[code], required_gate_ids=['source', 'confirmation'])
    snapshot = dict(schema_version='habu-registry-core-snapshot-v1',
        repository=copy.deepcopy(policy['repository']), state_ref=policy['state_ref'],
        history_complete=True,
        commits=[dict(commit_sha='1' * 40, parents=['0' * 40], files=files)], transition_proofs=[])
    document = dict(schema_version='habu-registry-intent-v1',
        repository=copy.deepcopy(policy['repository']), task_id=policy['task_id'],
        operation='PROMOTE', operation_id='next-op', expected_previous_event_sha256=event['event_sha256'],
        model_sha256='6' * 64, code_sha256=code, code_manifest=copy.deepcopy(manifest),
        protocol_sha256='e' * 64, evidence_sha256='7' * 64, policy_sha256=checksum(policy))
    intent = dict(document=document,
        reviewed_ref=dict(commit_sha='7' * 40, path='protocols/intents/next.json', sha256=checksum(document, True)),
        merged_ref=dict(commit_sha='8' * 40, tree_sha='9' * 40, facts_sha256='a' * 64,
                        merged_at='2026-11-04T09:00:00+09:00'))
    gate = dict(schema_version='habu-registry-gate-decision-v1', intent_sha256=checksum(document, True),
        evidence_sha256=document['evidence_sha256'], policy_sha256=checksum(policy),
        reproduction_sha256='b' * 64, evaluated_at='2026-11-04T09:30:00+09:00',
        gates=[dict(gate_id=g, status='PASS') for g in policy['required_gate_ids']])
    return snapshot, policy, intent, gate


def core_apply(snapshot, result, commit_sha='a' * 40, proof=None):
    result = copy.deepcopy(result)
    next_snapshot = copy.deepcopy(snapshot)
    spec = result['commit_spec']
    files = {d['path']:d for d in next_snapshot['commits'][-1]['files']}
    for item in spec['immutable_additions']+spec['updates']:
        files[item['path']] = {k:item[k] for k in ('path','sha256','size_bytes','content_utf8')}
    next_snapshot['commits'].append(dict(commit_sha=commit_sha, parents=spec['parents'],
                                       files=list(files.values())))
    if proof is not None:
        next_snapshot['transition_proofs'].append(copy.deepcopy(proof))
    return next_snapshot


def core_inference(snapshot):
    pointer = next(json.loads(d['content_utf8']) for d in snapshot['commits'][-1]['files']
                   if d['path'].endswith('/current.json'))
    event = next(json.loads(d['content_utf8']) for d in snapshot['commits'][-1]['files']
                 if '/events/' in d['path'] and json.loads(d['content_utf8'])['event_sha256']==pointer['event_sha256'])
    return dict(schema_version='habu-registry-inference-v1', operation_id='issue-op',
        operational_night='2026-11-04', cutoff_time='2026-11-04T17:00:00+09:00',
        training_cutoff='2026-11-03T07:00:00+09:00',
        forecast_windows=['2026-11-04T19:00:00+09:00'],
        selected_event_sha256=event['event_sha256'], model_sha256=event['model_sha256'],
        code_sha256=event['code_sha256'], input_bundle_sha256='1'*64,
        component_receipts_sha256='2'*64, output={'unit_score':[0.25]})


class ProductionRegistryCoreTests(unittest.TestCase):
    def module(self):
        module = importlib.import_module('production_registry')
        for name in ('validate_registry_snapshot','prepare_activation_commit',
                     'prepare_issuance_commit','reconcile_publication'):
            self.assertTrue(callable(getattr(module,name,None)), 'Missing conditional core API: '+name)
        return module

    def safe(self, result):
        for name in ('production_authorized','official_issuance_authorized','registry_activated'):
            self.assertIs(result[name],False)
        self.assertEqual(result['source_authentication'],'NOT_ATTESTED')
        self.assertEqual(result['scientific_reproduction'],'NOT_REPRODUCED')
        self.assertEqual(result['observed_time_authentication'],'NOT_ATTESTED')
        return result

    def validate(self, snapshot, policy, **kw):
        return self.safe(self.module().validate_registry_snapshot(snapshot,policy=policy,**kw))

    def activate(self, snapshot, policy, intent, gate, **kw):
        return self.safe(self.module().prepare_activation_commit(snapshot,intent,gate,policy=policy,
            observed_at=kw.pop('observed_at','2026-11-04T10:00:00+09:00'),
            expected_ref_sha=kw.pop('expected_ref_sha',snapshot['commits'][-1]['commit_sha']),
            expected_previous_event_sha256=kw.pop('expected_previous_event_sha256',intent['document']['expected_previous_event_sha256']),**kw))

    def issue(self, snapshot, policy, record=None, **kw):
        record=core_inference(snapshot) if record is None else record
        return self.safe(self.module().prepare_issuance_commit(snapshot,record,policy=policy,
            observed_at=kw.pop('observed_at','2026-11-04T18:00:00+09:00'),
            expected_ref_sha=kw.pop('expected_ref_sha',snapshot['commits'][-1]['commit_sha']),
            expected_event_sha256=kw.pop('expected_event_sha256',record['selected_event_sha256']),**kw))

    def reconcile(self, pending, observed, policy, **kw):
        return self.safe(self.module().reconcile_publication(pending,observed,policy=policy,**kw))

    def test_existing_anchor_consistency_and_no_authority(self):
        s,p,_,_=core_fixture()
        r=self.validate(s,p)
        self.assertEqual(r['status'],'CONSISTENT_NOT_AUTHENTICATED',r)
        self.assertEqual(r['computed']['tip_commit_sha'],'1'*40)
        self.assertEqual(r['computed']['activated_model_count'],1)

    def test_activation_exact_bytes_single_parent_and_input_immutability(self):
        s,p,i,g=core_fixture(); before=copy.deepcopy((s,p,i,g))
        r=self.activate(s,p,i,g)
        self.assertEqual(r['status'],'ACTIVATION_COMMIT_PROPOSED',r)
        self.assertEqual(r['commit_spec']['parents'],['1'*40])
        self.assertEqual(r,self.activate(s,p,i,g))
        self.assertEqual((s,p,i,g),before)
        self.assertEqual(len(r['commit_spec']['immutable_additions']),1)
        for d in r['commit_spec']['immutable_additions']+r['commit_spec']['updates']:
            self.assertEqual(hashlib.sha256(d['content_utf8'].encode()).hexdigest(),d['sha256'])
        event=json.loads(r['commit_spec']['immutable_additions'][0]['content_utf8'])
        self.assertNotIn('commit_sha',event)
        self.assertEqual(event['observed_at'],'2026-11-04T10:00:00+09:00')
        observed=core_apply(s,r,proof=dict(intent=i,gate_decision=g))
        self.assertEqual(self.validate(observed,p)['status'],'CONSISTENT_NOT_AUTHENTICATED')

    def test_missing_anchor_or_incomplete_history_is_blocked(self):
        for mutate in (lambda s,p:s.update(history_complete=False),
                       lambda s,p:s.update(commits=[]),lambda s,p:p.update(anchor=None)):
            s,p,i,g=core_fixture(); mutate(s,p)
            self.assertEqual(self.validate(s,p)['status'],'BLOCKED')
        self.assertEqual(self.validate(None,core_fixture()[1])['status'],'BLOCKED')

    def test_null_existing_anchor_is_missing_not_genesis(self):
        for field in ('commit_sha','root_event_sha256','files_sha256'):
            s,p,_,_=core_fixture();p['anchor'][field]=None
            self.assertEqual(self.validate(s,p)['status'],'BLOCKED')

    def test_tampered_file_hash_size_noncanonical_and_unknown_file_fail(self):
        for mutate in (lambda d:d.update(sha256='0'*64),lambda d:d.update(size_bytes=True),
                       lambda d:d.update(content_utf8=d['content_utf8']+' ')):
            s,p,_,_=core_fixture(); mutate(s['commits'][0]['files'][0])
            self.assertEqual(self.validate(s,p)['status'],'FAIL')
        s,p,_,_=core_fixture(); s['commits'][0]['files'].append(core_document(p['registry_root']+'/other.json',{}))
        self.assertEqual(self.validate(s,p)['status'],'FAIL')

    def test_ref_anchor_scope_and_pointer_contradictions_fail(self):
        for mutate in (lambda s,p:s.update(state_ref='refs/heads/other'),
                       lambda s,p:p['anchor'].update(commit_sha='f'*40),
                       lambda s,p:p['anchor'].update(files_sha256='f'*64),
                       lambda s,p:p.update(pointer_path='data/raw/current.json'),
                       lambda s,p:p.update(event_directory=p['pointer_path']+'/child')):
            s,p,_,_=core_fixture(); mutate(s,p)
            self.assertEqual(self.validate(s,p)['status'],'FAIL')

    def test_activation_stale_expected_state_and_code_digest_fail(self):
        for kw in ({'expected_ref_sha':'f'*40},{'expected_previous_event_sha256':'f'*64}):
            s,p,i,g=core_fixture(); self.assertEqual(self.activate(s,p,i,g,**kw)['status'],'CONFLICT')
        s,p,i,g=core_fixture(); i['document']['code_manifest'][0]['sha256']='f'*64
        self.assertEqual(self.activate(s,p,i,g)['status'],'FAIL')

    def test_missing_failed_unknown_gate_does_not_prepare_activation(self):
        for status,expected in [('FAIL','FAIL'),('BLOCKED','BLOCKED'),('NOT_VALIDATED','BLOCKED')]:
            s,p,i,g=core_fixture();g['gates'][0]['status']=status
            self.assertEqual(self.activate(s,p,i,g)['status'],expected)
        s,p,i,g=core_fixture();g['gates'].pop()
        self.assertEqual(self.activate(s,p,i,g)['status'],'BLOCKED')

    def test_gate_intent_policy_review_binding_and_injected_authority_fail(self):
        for mutate in (lambda i,g:i['reviewed_ref'].update(sha256='0'*64),
                       lambda i,g:i['merged_ref'].update(tree_sha='wrong'),
                       lambda i,g:g.update(evidence_sha256='0'*64),
                       lambda i,g:g.update(policy_sha256='0'*64),
                       lambda i,g:i['document'].update(production_authorized=True)):
            s,p,i,g=core_fixture();mutate(i,g)
            self.assertEqual(self.activate(s,p,i,g)['status'],'FAIL')

    def test_activation_clock_cannot_precede_merge_gate_or_prior_state(self):
        for when in ('2026-11-04T08:59:59+09:00','2026-11-04T09:29:59+09:00',
                     '2026-11-02T01:00:00+00:00','2026-11-04T10:00:00'):
            s,p,i,g=core_fixture();self.assertEqual(self.activate(s,p,i,g,observed_at=when)['status'],'FAIL')

    def test_rollback_never_active_model_and_incompatible_code_blocked(self):
        s,p,i,g=core_fixture();i['document']['operation']='ROLLBACK'
        i['reviewed_ref']['sha256']=checksum(i['document'],True);g['intent_sha256']=i['reviewed_ref']['sha256']
        self.assertEqual(self.activate(s,p,i,g)['status'],'BLOCKED')
        s,p,i,g=core_fixture();p['compatible_code_sha256']=['0'*64]
        i['document']['policy_sha256']=checksum(p);i['reviewed_ref']['sha256']=checksum(i['document'],True)
        g.update(policy_sha256=checksum(p),intent_sha256=i['reviewed_ref']['sha256'])
        self.assertEqual(self.activate(s,p,i,g)['status'],'BLOCKED')

    def test_issuance_allocates_contiguous_versions_and_binds_actual_output(self):
        s,p,_,_=core_fixture();r=self.issue(s,p)
        self.assertEqual(r['status'],'ISSUANCE_COMMIT_PROPOSED',r)
        self.assertEqual(r['computed']['version'],'P0')
        self.assertEqual(len(r['commit_spec']['immutable_additions']),2)
        next_s=core_apply(s,r)
        self.assertEqual(self.validate(next_s,p)['status'],'CONSISTENT_NOT_AUTHENTICATED')
        record=core_inference(next_s);record['operation_id']='issue-next'
        self.assertEqual(self.issue(next_s,p,record)['computed']['version'],'P1')
        self.assertEqual(next_s['commits'][0]['files'],s['commits'][0]['files'])

    def test_issuance_rejects_historical_expired_unaligned_and_wrong_model(self):
        for mutate in (lambda r:r.update(operational_night='2026-11-02'),
                       lambda r:r.update(forecast_windows=['2026-11-04T18:00:00+09:00']),
                       lambda r:r.update(forecast_windows=['2026-11-04T19:01:00+09:00']),
                       lambda r:r.update(model_sha256='0'*64),
                       lambda r:r.update(code_sha256='0'*64),
                       lambda r:r.update(training_cutoff=r['cutoff_time']),
                       lambda r:r.update(cutoff_time='2026-11-04T18:00:01+09:00')):
            s,p,_,_=core_fixture();rec=core_inference(s);mutate(rec)
            self.assertEqual(self.issue(s,p,rec)['status'],'FAIL')

    def test_same_operation_never_creates_second_event_or_version(self):
        s,p,_,_=core_fixture();rec=core_inference(s);r=self.issue(s,p,rec);s2=core_apply(s,r)
        self.assertEqual(self.issue(s2,p,rec)['status'],'BLOCKED')

    def test_reconcile_unknown_child_and_descendant_without_rebasing(self):
        s,p,_,_=core_fixture();r=self.issue(s,p);pending=r['pending']
        self.assertIsNone(pending['commit_sha'])
        self.assertEqual(self.reconcile(pending,s,p)['status'],'ACK_UNKNOWN')
        s2=core_apply(s,r)
        self.assertEqual(self.reconcile(pending,s2,p)['status'],'ACK_ONLY')
        rec=core_inference(s2);rec['operation_id']='issue-next';r2=self.issue(s2,p,rec)
        s3=core_apply(s2,r2,commit_sha='b'*40)
        self.assertEqual(self.reconcile(pending,s3,p)['status'],'ACK_ONLY')
        pending['commit_sha']='a'*40
        self.assertEqual(self.reconcile(pending,s3,p)['status'],'ACK_ONLY')

    def test_reconcile_competing_child_and_known_wrong_commit_conflict(self):
        s,p,_,_=core_fixture();first=self.issue(s,p)
        rec=core_inference(s);rec['operation_id']='sibling';rec['output']={'unit_score':[.5]}
        second=self.issue(s,p,rec);observed=core_apply(s,second,commit_sha='b'*40)
        self.assertEqual(self.reconcile(first['pending'],observed,p)['status'],'CONFLICT')
        observed=core_apply(s,first);pending=copy.deepcopy(first['pending']);pending['commit_sha']='c'*40
        self.assertEqual(self.reconcile(pending,observed,p)['status'],'CONFLICT')

    def test_pending_tamper_multiple_parents_and_output_overwrite_fail(self):
        s,p,_,_=core_fixture();r=self.issue(s,p)
        for change in (lambda q:q['commit_spec'].update(parents=['1'*40,'2'*40]),
                       lambda q:q['commit_spec']['immutable_additions'][0].update(sha256='0'*64),
                       lambda q:q.update(operation_id='other')):
            pending=copy.deepcopy(r['pending']);change(pending)
            self.assertEqual(self.reconcile(pending,s,p)['status'],'FAIL')
        s2=core_apply(s,r);s2['commits'][-1]['files'][0]=core_document(s2['commits'][-1]['files'][0]['path'],{})
        self.assertEqual(self.validate(s2,p)['status'],'FAIL')

    def test_history_merge_missing_proof_mutation_and_version_gap_fail_closed(self):
        s,p,i,g=core_fixture();r=self.activate(s,p,i,g);s2=core_apply(s,r,proof=dict(intent=i,gate_decision=g))
        for mutate in (lambda v:v['commits'][-1]['parents'].append('2'*40),
                       lambda v:v['commits'][-1].update(parents=['2'*40]),
                       lambda v:v['commits'][-1]['files'].pop(0)):
            v=copy.deepcopy(s2);mutate(v);self.assertEqual(self.validate(v,p)['status'],'FAIL')
        s2['transition_proofs']=[]
        self.assertEqual(self.validate(s2,p)['status'],'BLOCKED')

    def test_declared_fabricated_consistency_no_io_callbacks_or_authority(self):
        s,p,i,g=core_fixture();before=copy.deepcopy((s,p,i,g))
        with (patch('builtins.open',side_effect=AssertionError('file')),
              patch('socket.socket',side_effect=AssertionError('network'))):
            self.assertEqual(self.activate(s,p,i,g)['status'],'ACTIVATION_COMMIT_PROPOSED')
        self.assertEqual((s,p,i,g),before)

    def test_budget_foreign_types_depth_and_nan_fail_closed(self):
        s,p,i,g=core_fixture();calls=[]
        class Meta(type):
            def __eq__(self,other): calls.append(1);raise AssertionError('callback')
            def __hash__(self): calls.append(1);raise AssertionError('callback')
        class Probe(metaclass=Meta): pass
        for value in (True,0,-1,31,10**1000,float('nan'),Probe()):
            self.assertEqual(self.validate(s,p,budget_seconds=value)['status'],'FAIL')
        s['probe']=Probe();self.assertEqual(self.validate(s,p)['status'],'FAIL');self.assertEqual(calls,[])
        s,p,_,_=core_fixture();s['history_complete']=1
        self.assertEqual(self.validate(s,p)['status'],'FAIL')
        self.assertEqual(self.validate(s,p,budget_seconds=1e-300)['status'],'BLOCKED')

    def test_genesis_anchor_is_unsupported_not_invented_or_claimed_complete(self):
        s,p,_,_=core_fixture()
        self.assertEqual(self.validate(s,p)['supported_scope'],'SUPPORTED_ANCHORED_SUFFIX_ONLY')
        event=json.loads(s['commits'][0]['files'][0]['content_utf8'])
        event['previous_event_sha256']=None
        event['event_sha256']=checksum({k:v for k,v in event.items() if k!='event_sha256'})
        s['commits'][0]['files'][0]=core_document(p['event_directory']+'/'+event['event_sha256']+'.json',event)
        pointer=dict(schema_version='habu-registry-pointer-v1',event_sha256=event['event_sha256'])
        s['commits'][0]['files'][1]=core_document(p['pointer_path'],pointer)
        p['anchor'].update(root_event_sha256=event['event_sha256'],
            files_sha256=checksum({d['path']:d['sha256'] for d in s['commits'][0]['files']}))
        r=self.validate(s,p);self.assertEqual(r['status'],'BLOCKED')
        self.assertIn('GENESIS_ANCHOR_UNSUPPORTED',r['reason_codes'])

    def test_ref_must_be_a_canonical_git_branch_declaration(self):
        for ref in ('refs/heads/bad ref','refs/heads/a..b','refs/heads/.hidden',
                    'refs/heads/a.lock','refs/heads/a@{b','refs/heads/a?b'):
            s,p,_,_=core_fixture();s['state_ref']=p['state_ref']=ref
            self.assertEqual(self.validate(s,p)['status'],'FAIL',ref)

    def test_resealed_pending_wrong_kind_and_invalid_record_fail_before_unknown_ack(self):
        s,p,_,_=core_fixture();r=self.issue(s,p)
        pending=copy.deepcopy(r['pending']);pending['kind']='ACTIVATE'
        self.assertEqual(self.reconcile(pending,s,p)['status'],'FAIL')
        pending=copy.deepcopy(r['pending']);spec=pending['commit_spec']
        old=spec['immutable_additions'][0]
        spec['immutable_additions'][0]=dict(core_document(old['path'],{'operation_id':'issue-op'}),expected_absent=True)
        pending['spec_sha256']=checksum(spec)
        self.assertEqual(self.reconcile(pending,s,p)['status'],'FAIL')

    def test_resealed_pending_version_and_predecessor_content_must_match_parent(self):
        s,p,_,_=core_fixture();r=self.issue(s,p)
        pending=copy.deepcopy(r['pending']);spec=pending['commit_spec']
        record=json.loads(spec['immutable_additions'][0]['content_utf8']);record['version']='P9'
        old=spec['immutable_additions'][0]
        spec['immutable_additions'][0]=dict(core_document(old['path'],record),expected_absent=True)
        pending['spec_sha256']=checksum(spec)
        self.assertEqual(self.reconcile(pending,s,p)['status'],'FAIL')

    def test_valid_rollback_and_equal_time_serial_issuance_promotion(self):
        s,p,i,g=core_fixture();a=self.activate(s,p,i,g);s2=core_apply(s,a,proof=dict(intent=i,gate_decision=g))
        old=json.loads(s['commits'][0]['files'][0]['content_utf8'])
        back=copy.deepcopy(i);back['document'].update(operation='ROLLBACK',operation_id='rollback',
            model_sha256=old['model_sha256'],expected_previous_event_sha256=a['computed']['next_event_sha256'])
        back['reviewed_ref']['sha256']=checksum(back['document'],True)
        bg=copy.deepcopy(g);bg['intent_sha256']=back['reviewed_ref']['sha256']
        b=self.activate(s2,p,back,bg,observed_at='2026-11-04T10:30:00+09:00')
        self.assertEqual(b['status'],'ACTIVATION_COMMIT_PROPOSED',b)
        s3=core_apply(s2,b,commit_sha='b'*40,proof=dict(intent=back,gate_decision=bg))
        self.assertEqual(self.validate(s3,p)['status'],'CONSISTENT_NOT_AUTHENTICATED')
        self.assertEqual(self.issue(s3,p)['status'],'ISSUANCE_COMMIT_PROPOSED')

    def test_same_operation_different_bytes_and_activation_race_reconcile_conflict(self):
        s,p,i,g=core_fixture();issued=self.issue(s,p)
        activation=self.activate(s,p,i,g,observed_at='2026-11-04T18:00:00+09:00')
        active=core_apply(s,activation,proof=dict(intent=i,gate_decision=g))
        self.assertEqual(self.reconcile(issued['pending'],active,p)['status'],'CONFLICT')
        issued_state=core_apply(s,issued)
        self.assertEqual(self.reconcile(activation['pending'],issued_state,p)['status'],'CONFLICT')

    def test_same_model_digest_cannot_be_rebound_to_a_different_protocol(self):
        s,p,i,g=core_fixture()
        old=json.loads(s['commits'][0]['files'][0]['content_utf8'])
        i['document'].update(model_sha256=old['model_sha256'],protocol_sha256='0'*64)
        i['reviewed_ref']['sha256']=checksum(i['document'],True);g['intent_sha256']=i['reviewed_ref']['sha256']
        self.assertEqual(self.activate(s,p,i,g)['status'],'FAIL')

    def test_pending_self_commit_and_incomplete_observation_keep_original_desired_bytes(self):
        s,p,_,_=core_fixture();r=self.issue(s,p);pending=copy.deepcopy(r['pending'])
        pending['commit_sha']=pending['parent_sha']
        self.assertEqual(self.reconcile(pending,s,p)['status'],'FAIL')
        incomplete=copy.deepcopy(s);incomplete['history_complete']=False
        result=self.reconcile(r['pending'],incomplete,p)
        self.assertEqual(result['status'],'ACK_UNKNOWN')
        self.assertEqual(result['pending'],r['pending'])

    def test_all_new_entrypoints_reject_foreign_context_without_callbacks_or_io(self):
        s,p,i,g=core_fixture();m=self.module();calls=[]
        class Probe:
            def __iter__(self):calls.append('iter');raise AssertionError('foreign')
            def __str__(self):calls.append('str');raise AssertionError('foreign')
            def __eq__(self,other):calls.append('eq');raise AssertionError('foreign')
        with (patch('builtins.open',side_effect=AssertionError('file')),
              patch('socket.socket',side_effect=AssertionError('network')),
              patch('subprocess.run',side_effect=AssertionError('process'))):
            self.assertEqual(self.validate(Probe(),p)['status'],'FAIL')
            self.assertEqual(m.prepare_activation_commit(s,Probe(),g,policy=p,
                observed_at='2026-11-04T18:00:00+09:00',expected_ref_sha='1'*40,
                expected_previous_event_sha256=i['document']['expected_previous_event_sha256'])['status'],'FAIL')
            self.assertEqual(m.prepare_issuance_commit(s,Probe(),policy=p,
                observed_at='2026-11-04T18:00:00+09:00',expected_ref_sha='1'*40,
                expected_event_sha256=i['document']['expected_previous_event_sha256'])['status'],'FAIL')
            self.assertEqual(self.reconcile(Probe(),s,p)['status'],'FAIL')
        self.assertEqual(calls,[])

    def test_pending_record_container_variants_return_structured_failure(self):
        s,p,_,_=core_fixture();r=self.issue(s,p)
        for invalid in (None,False,[],[1],0,'record'):
            pending=copy.deepcopy(r['pending']);spec=pending['commit_spec']
            old=spec['immutable_additions'][0]
            spec['immutable_additions'][0]=dict(core_document(old['path'],invalid),expected_absent=True)
            pending['spec_sha256']=checksum(spec)
            try:
                result=self.reconcile(pending,s,p)
            except Exception as exc:
                self.fail('Malformed pending container escaped: '+type(exc).__name__)
            self.assertEqual(result['status'],'FAIL')


if __name__ == '__main__':
    unittest.main()
