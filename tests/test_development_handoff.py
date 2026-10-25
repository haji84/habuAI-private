"""Synthetic accounting contracts; no authenticated controller execution."""
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import development_handoff as h

NOW = '2026-10-25T08:00:00+00:00'
LATER = '2026-10-25T08:10:00+00:00'
RECIPES = {'uniform': 'a'*64, 'HB-A0': 'b'*64, 'HB-A1': 'c'*64}


def origin():
    return h.new_science_ledger('1'*64, '2026-10-25', RECIPES)


def reserve(ledger, **changes):
    args = dict(expected_tip=ledger['tip_sha256'], operation_id='2'*64,
        child_command_id='3'*64, source_commit='4'*40, attempt_id='5'*64,
        round_id='6'*64, recipes=RECIPES, milliseconds=200000,
        now=NOW, lease_until=LATER)
    args.update(changes)
    return h.reserve_science(ledger, **args)


class ScienceRootLedgerTests(unittest.TestCase):
    def test_origin_and_every_proposal_have_no_execution_authority(self):
        ledger = origin()
        self.assertEqual(h.inspect_science_ledger(ledger)['remaining_ms'], 300000)
        result = reserve(ledger)
        for key in ('execution_authorized', 'scientific_authorized', 'selection_authorized', 'production_authorized'):
            self.assertIs(result[key], False)
        self.assertEqual(result['persistence'], 'UNPUBLISHED_PROPOSAL')

    def test_reserve_then_settle_parent200s_child_gets_only100s(self):
        first = reserve(origin())
        settled = h.settle_science(first, expected_tip=first['tip_sha256'], attempt_id='5'*64,
            generation=1, elapsed_ms=200000, now=NOW)
        self.assertEqual(h.inspect_science_ledger(settled)['remaining_ms'], 100000)
        second = reserve(settled, operation_id='7'*64, child_command_id='8'*64,
            source_commit='9'*40, attempt_id='a'*64, round_id='b'*64, milliseconds=100000)
        self.assertEqual(h.inspect_science_ledger(second)['remaining_ms'], 0)
        with self.assertRaises(ValueError):
            reserve(settled, operation_id='7'*64, attempt_id='a'*64, round_id='b'*64, milliseconds=100001)

    def test_reserved_compute_and_round_cannot_be_double_spent(self):
        first = reserve(origin())
        with self.assertRaises(ValueError): reserve(first, attempt_id='a'*64)
        with self.assertRaises(ValueError): reserve(first, operation_id='7'*64,
            child_command_id='8'*64, attempt_id='a'*64, round_id='b'*64, milliseconds=100001)

    def test_stale_tip_and_two_writer_proposals_are_distinct_no_atomicity_claim(self):
        base = origin(); first = reserve(base)
        other = reserve(base, operation_id='7'*64, child_command_id='8'*64, attempt_id='a'*64)
        self.assertNotEqual(first['tip_sha256'], other['tip_sha256'])
        self.assertEqual(first['events'][0]['previous_sha256'], base['tip_sha256'])
        with self.assertRaises(ValueError): reserve(first, expected_tip=base['tip_sha256'], attempt_id='a'*64)

    def test_expired_lease_charges_full_reservation_and_fences_late_settlement(self):
        first = reserve(origin())
        late = '2026-10-25T08:10:00.001+00:00'
        expired = h.expire_science(first, expected_tip=first['tip_sha256'], attempt_id='5'*64,
            generation=1, now=late)
        info = h.inspect_science_ledger(expired)
        self.assertEqual(info['used_ms'], 200000)
        self.assertEqual(info['remaining_ms'], 100000)
        with self.assertRaises(ValueError): h.settle_science(expired, expected_tip=expired['tip_sha256'],
            attempt_id='5'*64, generation=1, elapsed_ms=1, now=late)

    def test_settlement_idempotency_and_mismatch(self):
        first = reserve(origin())
        kwargs = dict(attempt_id='5'*64, generation=1, elapsed_ms=120000, now=NOW)
        settled = h.settle_science(first, expected_tip=first['tip_sha256'], **kwargs)
        self.assertEqual(h.settle_science(settled, expected_tip=settled['tip_sha256'], **kwargs), settled)
        with self.assertRaises(ValueError): h.settle_science(settled, expected_tip=settled['tip_sha256'], **dict(kwargs, elapsed_ms=119999))
        self.assertEqual(h.inspect_science_ledger(settled)['remaining_ms'], 180000)

    def test_third_round_and_unregistered_or_changed_recipe_reject(self):
        ledger = origin()
        for index in (1, 2):
            digit = str(index)
            ledger = reserve(ledger, operation_id=digit*64, child_command_id=digit*64,
                attempt_id=digit*64, round_id=digit*64, milliseconds=1)
            ledger = h.settle_science(ledger, expected_tip=ledger['tip_sha256'], attempt_id=digit*64,
                generation=len(ledger['events']), elapsed_ms=1, now=NOW)
        with self.assertRaises(ValueError): reserve(ledger, attempt_id='f'*64, round_id='f'*64, milliseconds=1)
        for recipes in (dict(RECIPES, **{'HB-B1': 'd'*64}), dict(RECIPES, **{'HB-A1':'e'*64})):
            with self.assertRaises(ValueError): reserve(origin(), recipes=recipes)

    def test_canonical_operation_child_source_cannot_change_after_settlement(self):
        first = reserve(origin())
        settled = h.settle_science(first, expected_tip=first['tip_sha256'], attempt_id='5'*64,
            generation=1, elapsed_ms=1, now=NOW)
        for changes in ({'child_command_id':'d'*64}, {'source_commit':'e'*40}):
            with self.assertRaises(ValueError): reserve(settled, attempt_id='f'*64, milliseconds=1, **changes)

    def test_invalid_types_timestamps_and_unknown_execution_fields_reject(self):
        for value in (True, 0, -1, 300001, 1.5, float('nan')):
            with self.assertRaises(ValueError): reserve(origin(), milliseconds=value)
        for changes in ({'now':'2026-10-25T08:00:00'}, {'lease_until':NOW}, {'lease_until':'2026-10-25T07:59:00Z'},
                        {'expected_tip':'0'*64}, {'source_commit':'4'*64}, {'recipes':{'uniform':'f'*64}}):
            with self.subTest(changes=changes), self.assertRaises(ValueError): reserve(origin(), **changes)
        ledger = origin(); ledger['trusted'] = True
        with self.assertRaises(ValueError): reserve(ledger)

    def test_origin_requires_three_slots_reservation_can_use_frozen_subset(self):
        with self.assertRaises(ValueError): h.new_science_ledger('1'*64, '2026-10-25', {'uniform':'a'*64})
        one = reserve(origin(), recipes={'uniform':'a'*64})
        self.assertEqual(one['events'][0]['recipes'], {'uniform':'a'*64})

    def test_event_history_and_summary_cannot_be_forged(self):
        first = reserve(origin())
        for change in ('history', 'tip', 'summary'):
            bad = copy.deepcopy(first)
            if change == 'history': bad['events'][0]['milliseconds'] = 1
            elif change == 'tip': bad['tip_sha256'] = '0'*64
            else: bad['used_ms'] = 0
            with self.assertRaises(ValueError): h.inspect_science_ledger(bad)

    def test_output_and_inputs_are_detached(self):
        ledger = origin(); before = copy.deepcopy(ledger)
        recipes = copy.deepcopy(RECIPES)
        first = reserve(ledger, recipes=recipes)
        recipes.clear(); first['events'][0]['recipes'].clear()
        self.assertEqual(ledger, before)
        self.assertEqual(h.inspect_science_ledger(ledger)['remaining_ms'], 300000)

    def test_lease_generation_time_and_overrun_reject_without_releasing_allowance(self):
        first = reserve(origin())
        for changes in ({'generation':2}, {'elapsed_ms':200001}, {'elapsed_ms':True},
                        {'now':'2026-10-25T07:59:59Z'}, {'now':'2026-10-25T08:10:00.001Z'}):
            args = dict(expected_tip=first['tip_sha256'], attempt_id='5'*64, generation=1,
                elapsed_ms=1, now=NOW)
            args.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError): h.settle_science(first, **args)
        self.assertEqual(h.inspect_science_ledger(first)['reserved_ms'], 200000)
        with self.assertRaises(ValueError): reserve(origin(), lease_until='2026-10-25T08:10:00.001Z')
        with self.assertRaises(ValueError): h.expire_science(first, expected_tip=first['tip_sha256'],
            attempt_id='5'*64, generation=1, now=LATER)

    def test_retry_cannot_reset_same_operation_attempt_limit_or_consumed_round(self):
        ledger = origin()
        for index in range(2):
            ident = str(index+1)*64
            ledger = reserve(ledger, attempt_id=ident, milliseconds=1)
            generation = len(ledger['events'])
            ledger = h.settle_science(ledger, expected_tip=ledger['tip_sha256'], attempt_id=ident,
                generation=generation, elapsed_ms=1, now=NOW)
        self.assertEqual(len(h.inspect_science_ledger(ledger)['rounds']), 1)
        with self.assertRaises(ValueError): reserve(ledger, attempt_id='f'*64, milliseconds=1)
        with self.assertRaises(ValueError): reserve(ledger, attempt_id='f'*64, operation_id='d'*64,
            child_command_id='e'*64, milliseconds=1)

    def test_rehashed_invalid_history_still_fails_semantic_replay(self):
        from master_contracts import digest
        first = reserve(origin())
        first['events'][0]['milliseconds'] = 300001
        event = first['events'][0]
        event['event_sha256'] = digest({k:v for k,v in event.items() if k!='event_sha256'})
        first['tip_sha256'] = event['event_sha256']
        with self.assertRaises(ValueError): h.inspect_science_ledger(first)

    def test_capacity_and_cycles_block_before_owned_parse(self):
        from unittest.mock import patch
        for name in ('MAX_BYTES', 'MAX_NODES'):
            ledger = origin()
            with self.subTest(name=name), patch.object(h, name, 1), \
                    patch.object(h.json, 'loads', side_effect=AssertionError('parse before capacity')), \
                    self.assertRaises(ValueError): h.inspect_science_ledger(ledger)
        ledger = origin(); ledger['events'].append(ledger)
        with self.assertRaises(ValueError): h.inspect_science_ledger(ledger)

    def test_no_io_and_foreign_authority_or_limit_flags(self):
        from unittest.mock import patch
        import socket
        with patch('builtins.open', side_effect=AssertionError('file I/O')), \
                patch.object(socket, 'socket', side_effect=AssertionError('network I/O')):
            self.assertEqual(h.inspect_science_ledger(reserve(origin()))['reserved_ms'], 200000)
        for change in ('repository', 'master_issue', 'limits', 'authority'):
            ledger = origin()
            if change == 'limits': ledger['origin']['limits']['rounds'] = 3
            elif change == 'authority': ledger['execution_authorized'] = True
            else: ledger['origin'][change] = 'foreign'
            with self.subTest(change=change), self.assertRaises(ValueError): h.inspect_science_ledger(ledger)


def development_provenance():
    run = '3'*64
    return dict(master_issue='haji84/AI-#1642', repository='haji84/habuAI-private',
        root_command_id='1'*64, parent_command_id='2'*64, parent_run_id=run,
        operational_night='2026-10-25', source_commit='4'*40,
        protocol_sha256='5'*64, observed_at=NOW, expires_at='2026-10-26T08:00:00+00:00',
        evidence=[dict(path=f'reports/pdca/2026-10-25/runs/{run}/stages/development.json',
                       sha256='6'*64, size_bytes=100)])


def development_need():
    return dict(kind='CODE_CAPABILITY', capability_id='CONFIGURED_STAGE1_PARENT_DISPATCH_V2',
        capability_installed=False, prerequisite_schema='habu-stage1-source-contract-v2',
        prerequisite_deployed=True)


class DevelopmentRequestProposalTests(unittest.TestCase):
    def setUp(self):
        self.context, self.need = development_provenance(), development_need()

    def propose(self):
        function = getattr(h, 'propose_development_request', None)
        self.assertTrue(callable(function), 'typed development proposal API missing')
        return function(self.context, self.need)

    def inspect(self, request):
        function = getattr(h, 'inspect_development_request', None)
        self.assertTrue(callable(function), 'strict development request inspector missing')
        return function(request)

    def test_exact_derived_scope_and_false_authority_are_not_executable_admission(self):
        proposal = self.propose()
        self.assertEqual(proposal['status'], 'DECLARED_SCOPE_PROPOSAL')
        request = proposal['request']
        self.assertEqual(request['purpose'], 'IMPLEMENTATION_COMPLETENESS')
        self.assertEqual(request['capability_id'], self.need['capability_id'])
        self.assertEqual(request['strategy_id'], 'REUSE_SOURCE_STAGE1_V2')
        self.assertEqual(request['requirement_ids'], ['R005', 'R026'])
        self.assertEqual(request['allowed_paths'], ['src/research_pdca_adapter.py',
            'tests/test_research_pdca_adapter.py',
            'docs/specs/research-configured-stage1-parent-v2.md',
            'docs/reviews/research_configured_stage1_parent_v2_20261025.md'])
        self.assertEqual(request['limits'], dict(attempts=2, active_seconds_per_attempt=3600,
            active_seconds_total=7200, lease_seconds=600))
        self.assertEqual(request['verification_profile'], 'HABU_PYTHON_EXACT_HEAD_REVIEW_V1')
        for value in (proposal, request):
            for flag in ('request_admitted', 'execution_authorized', 'scientific_authorized',
                         'selection_authorized', 'production_authorized', 'github_facts_authenticated'):
                self.assertIs(value[flag], False)
        self.assertEqual(request['source_authenticity'], 'NOT_ATTESTED')
        self.assertEqual(self.inspect(request), request)
        self.assertEqual(request['request_sha256'], h.digest({
            k:v for k,v in request.items() if k != 'request_sha256'}))

    def test_changed_source_evidence_and_expiry_preserve_strategy_identity_not_request(self):
        first = self.propose()['request']
        self.context['source_commit'] = 'a'*40
        self.context['evidence'][0]['sha256'] = 'b'*64
        self.context['expires_at'] = '2026-10-26T07:00:00+00:00'
        second = self.propose()['request']
        self.assertEqual(first['strategy_key'], second['strategy_key'])
        self.assertNotEqual(first['request_sha256'], second['request_sha256'])
        self.context['root_command_id'] = 'c'*64
        self.assertNotEqual(second['strategy_key'], self.propose()['request']['strategy_key'])

    def test_data_unknown_already_present_and_prerequisite_cases_have_no_request(self):
        cases = [(dict(kind='DATA_REQUIREMENT'), 'DATA_REQUIREMENT'),
            (dict(kind='UNMAPPED'), 'UNMAPPED_REQUIREMENT'),
            (dict(capability_id='free-text: please run shell'), 'UNMAPPED_REQUIREMENT'),
            (dict(capability_installed=True), 'ALREADY_IMPLEMENTED'),
            (dict(prerequisite_schema=None, prerequisite_deployed=False), 'PREREQUISITE_REQUIRED'),
            (dict(prerequisite_deployed=False), 'PREREQUISITE_REQUIRED'),
            (dict(prerequisite_schema='unknown-version'), 'PREREQUISITE_REQUIRED')]
        for change, status in cases:
            self.need = dict(development_need(), **change)
            result = self.propose()
            self.assertEqual(result['status'], status)
            self.assertIsNone(result['request'])
            self.assertIs(result['execution_authorized'], False)

    def test_unknown_fields_and_command_or_trust_flags_reject_before_no_job_return(self):
        for target, field, value in [('context','command','python anything'),
                ('need','allowed_paths',['data/raw/x']), ('need','trusted',True),
                ('need','ci_conclusion','success'), ('need','shell','ignored')]:
            self.setUp()
            self.need['kind'] = 'DATA_REQUIREMENT'
            (self.context if target == 'context' else self.need)[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): self.propose()

    def test_wrong_master_ids_dates_timestamps_and_declared_boolean_types_reject(self):
        changes = [('master_issue','haji84/AI-#1'), ('repository','haji84/AI-'),
            ('root_command_id','1'*63), ('source_commit','A'*40),
            ('protocol_sha256',True), ('operational_night','2026-02-30'),
            ('observed_at','2026-10-25T08:00:00'), ('expires_at',NOW),
            ('expires_at','2026-10-26T08:00:01+00:00')]
        for field, value in changes:
            self.setUp(); self.context[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): self.propose()
        for field, value in [('capability_installed',0), ('prerequisite_deployed',1),
                ('prerequisite_schema',1), ('kind','anything'), ('capability_id',None)]:
            self.setUp(); self.need[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): self.propose()

    def test_evidence_must_belong_to_exact_parent_night_run_and_safe_json_namespace(self):
        original = self.context['evidence'][0]['path']
        paths = [original.replace('2026-10-25','2026-10-24'), original.replace('3'*64,'4'*64),
            'data/raw/x.json', 'reports/pdca/2026-10-25/ORIGINAL/x.json',
            '/'+original, original.replace('/stages/','/../stages/'),
            original.replace('/stages/','//stages/'), original.replace('/','\\'),
            original[:-5]+'.py', original.replace('development.json','confirmation.json'),
            original.replace('development.json','sealed-labels.json'), original+':secret']
        for path in paths:
            self.context['evidence'][0]['path'] = path
            with self.subTest(path=path), self.assertRaises(ValueError): self.propose()

    def test_evidence_count_size_duplicates_and_known_malformed_early_data_reject(self):
        for change in ('empty', 'duplicate', 'count', 'size_bool', 'size_zero', 'size_cap',
                       'sum_cap', 'hash', 'foreignfield', 'deep'):
            self.setUp(); self.need['kind'] = 'DATA_REQUIREMENT'
            ref = self.context['evidence'][0]
            if change == 'empty': self.context['evidence'] = []
            elif change == 'duplicate': self.context['evidence'].append(copy.deepcopy(ref))
            elif change in ('count','sum_cap'):
                self.context['evidence'] = [dict(ref, path=ref['path'].replace('development.json',f'x{i}.json'),
                    size_bytes=1 if change == 'count' else 262144) for i in range(17 if change == 'count' else 5)]
            elif change == 'size_bool': ref['size_bytes'] = True
            elif change == 'size_zero': ref['size_bytes'] = 0
            elif change == 'size_cap': ref['size_bytes'] = 262145
            elif change == 'hash': ref['sha256'] = 'F'*64
            elif change == 'foreignfield': ref['trusted'] = True
            else:
                self.context['evidence'] = self.context
            with self.subTest(change=change), self.assertRaises(ValueError): self.propose()

    def test_rehashed_scope_profile_limits_or_authority_cannot_pass_inspection(self):
        request = self.propose()['request']
        changes = [('allowed_paths',['data/raw/x.json']), ('verification_profile','ALL_GREEN'),
            ('limits',dict(request['limits'],attempts=3)), ('strategy_id','NEW_RETRY'),
            ('strategy_key','a'*64), ('requirement_ids',['R001']), ('acceptance_ids',[]),
            ('request_admitted',True), ('execution_authorized',True),
            ('github_facts_authenticated',True), ('execution_authorized',0),
            ('source_authenticity','ATTESTED'),
            ('purpose','SCIENTIFIC_IMPROVEMENT')]
        for field, value in changes:
            forged = copy.deepcopy(request); forged[field] = value
            forged['request_sha256'] = h.digest({k:v for k,v in forged.items() if k != 'request_sha256'})
            with self.subTest(field=field), self.assertRaises(ValueError): self.inspect(forged)
        forged = copy.deepcopy(request); forged['request_sha256'] = '0'*64
        with self.assertRaises(ValueError): self.inspect(forged)

    def test_no_files_network_or_existing_science_accounting_mutation(self):
        from unittest.mock import patch
        import socket
        ledger = reserve(origin()); before = copy.deepcopy(ledger)
        with patch('builtins.open', side_effect=AssertionError('file')), \
                patch.object(Path,'open',side_effect=AssertionError('path')), \
                patch.object(socket,'socket',side_effect=AssertionError('net')):
            result = self.propose(); inspected = self.inspect(result['request'])
        self.assertEqual(inspected, result['request'])
        self.assertEqual(ledger, before)
        self.assertEqual(h.inspect_science_ledger(ledger)['reserved_ms'], 200000)

    def test_owned_results_and_inspection_leave_prior_values_unchanged(self):
        result = self.propose(); saved = copy.deepcopy(result)
        self.context['evidence'][0]['sha256'] = 'f'*64
        self.need['capability_installed'] = True
        self.assertEqual(result, saved)
        inspected = self.inspect(result['request']); inspected['limits']['attempts'] = 99
        self.assertEqual(result, saved)

    def test_declared_prerequisite_contradiction_and_missing_fields_reject_even_data(self):
        self.need.update(kind='DATA_REQUIREMENT', prerequisite_schema=None, prerequisite_deployed=True)
        with self.assertRaises(ValueError): self.propose()
        for target, field in (('context','source_commit'), ('need','prerequisite_schema')):
            self.setUp(); self.need['kind'] = 'DATA_REQUIREMENT'
            del (self.context if target == 'context' else self.need)[field]
            with self.subTest(field=field), self.assertRaises(ValueError): self.propose()

    def test_declared_expiry_does_not_assert_actual_clock_or_deployment_admission(self):
        # Deliberately past relative to the session: valid declared ordering, not a live lease.
        self.context.update(observed_at='2020-01-01T00:00:00+00:00',
            expires_at='2020-01-01T01:00:00+00:00')
        result = self.propose()
        self.assertEqual(result['status'], 'DECLARED_SCOPE_PROPOSAL')
        self.assertIs(result['request_admitted'], False)
        self.assertIs(result['github_facts_authenticated'], False)

    def test_extreme_aware_declared_year_preserves_valid_one_hour_duration(self):
        self.context.update(observed_at='9999-12-31T00:00:00+00:00',
            expires_at='9999-12-31T01:00:00+00:00')
        try:
            result = self.propose()
        except OverflowError:
            self.fail('Bounded one-hour declared interval overflowed')
        self.assertEqual(result['status'], 'DECLARED_SCOPE_PROPOSAL')
        self.assertIs(result['request_admitted'], False)

    def test_schema_defers_aware_iso_clock_semantics_to_inspector(self):
        import json
        self.context.update(observed_at='2026-10-25 08:00:00+0000',
            expires_at='2026-10-25 09:00:00+0000')
        request = self.propose()['request']
        self.assertEqual(self.inspect(request), request)
        schema = json.loads((Path(__file__).resolve().parents[1]/'schemas/development-job.json').read_bytes())
        for field in ('observed_at','expires_at'):
            self.assertNotIn('format', schema['$defs']['provenance']['properties'][field])

    def test_published_shape_contract_agrees_with_all_fixed_scope_fields(self):
        import json
        schema = json.loads((Path(__file__).resolve().parents[1]/'schemas/development-job.json').read_bytes())
        request = self.propose()['request']
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual(set(schema['required']), set(request))
        self.assertEqual(set(schema['properties']), set(request))
        for key, field in schema['properties'].items():
            if 'const' in field:
                self.assertEqual(h.canonical_bytes(request[key]), h.canonical_bytes(field['const']))
        for key in ('need','provenance'):
            nested = schema['$defs'][key]
            self.assertFalse(nested['additionalProperties'])
            self.assertEqual(set(nested['required']), set(request[key]))
        self.assertRegex(request['provenance']['evidence'][0]['path'],
            schema['$defs']['evidence']['properties']['path']['pattern'])


if __name__ == '__main__':
    unittest.main()
