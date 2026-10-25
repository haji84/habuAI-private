"""Synthetic constant-count mechanics; never source, forecast or fit authority."""
import copy
from datetime import datetime, timedelta
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import socket

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from tests.test_count_feasibility import fixture, seal, sha
from tests.test_research_selection import bind_selection

try:
    from models import constant_poisson_diagnostic as poisson
except ImportError:
    poisson = None


class ConstantPoissonTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(poisson, 'Missing standalone constant Poisson APIs')
        self.inputs = fixture()

    def fit(self, **kwargs):
        return poisson.fit_constant_poisson(*self.inputs, **kwargs)

    def rebind(self):
        selected, count, effort = self.inputs
        rows = selected['accepted']
        counts = dict(accepted_rows=len(rows), rejected_rows=len(selected['rejected']),
            nights=len({r['night'] for r in rows}), positives=sum(r['label'] for r in rows),
            negatives=sum(r['label'] == 0 for r in rows))
        ready = counts['nights'] >= 3 and counts['positives'] >= 2 and counts['negatives'] >= 2
        selected.update(counts=counts, status='DEVELOPMENT_TRAINING_ELIGIBLE' if ready else 'NEED_MORE_DATA',
                        blockers=[] if ready else ['Synthetic binary support missing'])
        bind_selection(selected)
        for value in (count, effort):
            value['selection_sha256'] = selected['selection_sha256']
            seal(value)

    def zero_cohort(self):
        selected, count, effort = self.inputs
        for row in selected['accepted']:
            row.update(label=0, capture_event_ids=[])
        for row in count['rows']:
            row.update(count=0, events=[], individual_source_ids=[])
        count['source_nodes'] = [n for n in count['source_nodes'] if n['id'] != 'outcomes']
        self.rebind()

    def resize_intervals(self, seconds):
        selected, counts, effort = self.inputs
        by_count = {r['row_id']: r for r in counts['rows']}
        for row, length in zip(effort['rows'], seconds):
            start = row['active_intervals'][0]['start']
            end = (datetime.fromisoformat(start) + timedelta(seconds=max(length, .000001))).isoformat()
            interval = dict(start=start, end=end)
            row.update(active_search_seconds=length, active_intervals=[interval])
            row['active_scope']['active_intervals'] = [copy.deepcopy(interval)]
            bound = by_count[row['row_id']]
            bound['complete_scope']['active_intervals'] = [copy.deepcopy(interval)]
            for event in bound['events']:
                event['event_time'] = start
        self.rebind()

    def test_analytic_whole_cohort_fit_and_independent_maximum(self):
        result = self.fit()
        self.assertEqual(result['status'], 'DECLARED_COHORT_FITTED')
        model = result['model']
        self.assertEqual(model['sufficient_statistics'], dict(rows=6, nights=3,
            total_individuals=6, total_active_search_seconds=1800.0))
        rate = model['parameters']['lambda_per_active_search_second']
        self.assertEqual(rate, 1 / 300)
        expected = -6 - 3 * math.log(2)
        self.assertAlmostEqual(result['training_log_likelihood'], expected, delta=1e-12)
        for alternative in (1 / 600, 1 / 150):
            # Independent analytic likelihood of this particular 2,0,2,0,2,0
            # fixture. No use of implementation's log-mass helper.
            value = 6 * math.log(alternative * 300) - 1800 * alternative - 3 * math.log(2)
            self.assertGreater(result['training_log_likelihood'], value)
        self.assertFalse(model['fit_authorized'])

    def test_safe_json_round_trip_is_checked_and_detached(self):
        model = self.fit()['model']
        checked = poisson.validate_constant_poisson_model(json.loads(json.dumps(model)))
        self.assertEqual(checked, model)
        self.assertIsNot(checked, model)
        checked['training_units'][0]['count'] = 99
        self.assertNotEqual(checked, model)

    def test_scenario_is_conditional_count_not_forecast(self):
        model = self.fit()['model']
        result = poisson.evaluate_constant_poisson_scenario(model, 300, count=2)
        self.assertEqual(result['status'], 'SCENARIO_ONLY')
        self.assertEqual(result['conditional_mean'], 1.0)
        self.assertAlmostEqual(result['probability_zero'], math.exp(-1), delta=1e-15)
        self.assertAlmostEqual(result['log_probability'], -1 - math.log(2), delta=1e-12)
        self.assertAlmostEqual(result['probability'], math.exp(-1) / 2, delta=1e-15)
        self.assertEqual(result['likelihood_status'], 'FINITE_LOG_MASS')
        self.assertFalse(result['production_authorized'])

    def test_complete_sealed_output_byte_cap(self):
        fitted = self.fit()
        model = fitted['model']
        operations = [lambda: self.fit(),
                      lambda: poisson.fit_constant_poisson(self.inputs[0]),
                      lambda: poisson.evaluate_constant_poisson_scenario(model, 300, count=2)]
        for operation in operations:
            complete = operation()
            maximum = len(json.dumps(complete, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()) - 1
            original = poisson._encoded
            def bounded(value, guard):
                if type(value) is dict and value.get('schema_version') == complete['schema_version']:
                    with patch.object(poisson, 'MAX_JSON_BYTES', maximum):
                        yield from original(value, guard)
                else:
                    yield from original(value, guard)
            with self.subTest(version=complete['schema_version']), patch.object(poisson, '_encoded', bounded):
                with self.assertRaises(poisson.PoissonCapacityBlocked):
                    operation()

    def test_whole_cohort_feasibility_exactly_once_and_unchanged(self):
        original = poisson.feasibility.assess_count_feasibility
        expected = original(*self.inputs)
        with patch.object(poisson.feasibility, 'assess_count_feasibility', wraps=original) as gate:
            result = self.fit()
        self.assertEqual(gate.call_count, 1)
        self.assertEqual(result['feasibility'], expected)
        self.assertEqual(result['feasibility']['fit_authorized'], False)
        self.assertEqual(result['feasibility']['assessment_sha256'], sha({k:v for k,v in expected.items() if k != 'assessment_sha256'}))
        self.assertEqual(result['input_digests'], dict(zip(('selection','count_projection','effort_projection'), map(sha,self.inputs))))
        self.assertEqual(result['model']['lineage']['feasibility_assessment_sha256'], expected['assessment_sha256'])

    def test_complete_zero_boundary_and_structural_zero_mass(self):
        self.zero_cohort()
        result = self.fit()
        self.assertEqual(self.inputs[0]['status'], 'NEED_MORE_DATA')
        self.assertEqual(result['status'], 'DECLARED_COHORT_FITTED')
        self.assertEqual(result['model']['parameters']['lambda_per_active_search_second'], 0.0)
        self.assertEqual(result['training_log_likelihood'], 0.0)
        for count, status, logp, p in ((0, 'FINITE_LOG_MASS', 0.0, 1.0), (1, 'ZERO_MASS', None, 0.0)):
            scenario = poisson.evaluate_constant_poisson_scenario(result['model'], 300, count=count)
            self.assertEqual((scenario['likelihood_status'], scenario['log_probability'], scenario['probability']), (status,logp,p))
            self.assertEqual(scenario['probability_zero'], 1.0)

    def test_positive_only_is_diagnostic_not_binary_adequacy(self):
        selected, count, effort = self.inputs
        keep = {r['row_id'] for r in selected['accepted'] if r['label']}
        selected['accepted'] = [r for r in selected['accepted'] if r['row_id'] in keep]
        for p in (count, effort):
            p['rows'] = [r for r in p['rows'] if r['row_id'] in keep]
        self.rebind()
        result = self.fit()
        self.assertEqual(selected['status'], 'NEED_MORE_DATA')
        self.assertEqual(result['status'], 'DECLARED_COHORT_FITTED')
        self.assertEqual(result['statistical_adequacy'], 'NOT_ASSESSED')

    def test_incomplete_whole_cohort_returns_no_partial_rate(self):
        for kind in ('count', 'effort', 'scope', 'individuals', 'row', 'zero_effort'):
            self.inputs = fixture()
            selected, count, effort = self.inputs
            if kind == 'count': count['rows'][0]['count'] = None
            elif kind == 'effort': effort['rows'][0]['active_search_seconds'] = None
            elif kind == 'scope': count['rows'][0]['complete_scope']['declaration'] = 'UNKNOWN'
            elif kind == 'individuals': count['rows'][0]['events'][0]['individual_ids'] = None
            elif kind == 'row': effort['rows'].pop()
            else: effort['rows'][0].update(active_search_seconds=0, active_intervals=[], active_scope=None)
            self.rebind()
            result = self.fit()
            self.assertEqual(result['status'], 'NEED_MORE_DATA', kind)
            self.assertIsNone(result['model'])
            self.assertIsNone(result['training_log_likelihood'])
        result = poisson.fit_constant_poisson(fixture()[0])
        self.assertEqual(result['status'], 'NEED_MORE_DATA')
        self.assertEqual(result['input_digests']['count_projection'], None)

    def test_known_invalid_plus_missing_and_duplicate_identity_fail(self):
        self.inputs[1]['rows'][0]['count'] = 1  # one event is actually two individuals
        seal(self.inputs[1])
        with self.assertRaises(ValueError):
            poisson.fit_constant_poisson(self.inputs[0], self.inputs[1], None)
        self.inputs = fixture()
        self.inputs[1]['rows'][2]['events'][0]['individual_ids'][0] = self.inputs[1]['rows'][0]['events'][0]['individual_ids'][0]
        seal(self.inputs[1])
        with self.assertRaises(ValueError): self.fit()

    def test_canonical_fsum_is_separate_from_unchanged_feasibility_sum(self):
        self.resize_intervals([.1, .1, .1, .3, .1, .1])
        result = self.fit()
        ordered = sorted(self.inputs[2]['rows'], key=lambda r:r['row_id'])
        expected = math.fsum(r['active_search_seconds'] for r in ordered)
        self.assertEqual(result['model']['sufficient_statistics']['total_active_search_seconds'], expected)
        self.assertEqual(result['model']['parameters']['lambda_per_active_search_second'], 6 / expected)
        self.assertEqual(result['feasibility']['summary']['declared_active_search_seconds'], sum(r['active_search_seconds'] for r in self.inputs[2]['rows']))
        original = self.fit()
        self.inputs[1]['rows'].reverse(); self.inputs[2]['rows'].reverse()
        seal(self.inputs[1]); seal(self.inputs[2])
        reordered = self.fit()
        self.assertEqual(reordered['model']['training_units'], original['model']['training_units'])
        self.assertEqual(reordered['model']['parameters'], original['model']['parameters'])
        self.assertNotEqual(reordered['model']['model_sha256'], original['model']['model_sha256'])

    def test_rehashed_inconsistent_model_table_recipe_statistics_and_authority_reject(self):
        model = self.fit()['model']
        mutations = [lambda m: m['parameters'].update(lambda_per_active_search_second=.5),
            lambda m: m['sufficient_statistics'].update(total_individuals=7),
            lambda m: m['sufficient_statistics'].update(rows=6.0),
            lambda m: m['training_units'][0].update(active_search_seconds=300),
            lambda m: m['training_units'][0].update(count=True),
            lambda m: m['training_units'][1].update(row_id=m['training_units'][0]['row_id']),
            lambda m: m['training_units'][0].update(window_start_jst='2026-09-01T20:01:00+09:00'),
            lambda m: m.update(fit_cutoff=m['heldout_night']+'T07:00:00+09:00'),
            lambda m: m.update(cohort_sha256='f'*64),
            lambda m: m['recipe'].update(estimator='OTHER_ESTIMATOR'),
            lambda m: m.update(recipe_sha256='f'*64),
            lambda m: m['lineage'].update(corpus_sha256=None),
            lambda m: m['input_digests'].update(extra='f'*64),
            lambda m: m.update(source_authenticity='AUTHENTICATED'),
            lambda m: m.update(production_authorized=0),
            lambda m: m.update(schema_version='other'),
            lambda m: m.update(training_log_likelihood=-1)]
        for change in mutations:
            bad = copy.deepcopy(model); change(bad)
            bad['model_sha256'] = sha({k:v for k,v in bad.items() if k != 'model_sha256'})
            with self.subTest(change=change), self.assertRaises(ValueError):
                poisson.validate_constant_poisson_model(bad)

    def test_stale_model_hash_and_exact_zero_sign_reject(self):
        model = self.fit()['model']
        model['parameters']['lambda_per_active_search_second'] += 1
        with self.assertRaises(ValueError): poisson.validate_constant_poisson_model(model)
        self.zero_cohort(); model = self.fit()['model']
        for replacement in (-0.0, 0, False):
            bad = copy.deepcopy(model)
            bad['parameters']['lambda_per_active_search_second'] = replacement
            bad['model_sha256'] = sha({k:v for k,v in bad.items() if k != 'model_sha256'})
            with self.assertRaises(ValueError): poisson.validate_constant_poisson_model(bad)

    def test_conditional_zero_exposure_and_finite_log_probability_underflow(self):
        model = self.fit()['model']
        result = poisson.evaluate_constant_poisson_scenario(model, 0, count=1)
        self.assertEqual((result['likelihood_status'],result['probability'],result['log_probability']), ('ZERO_MASS',0.0,None))
        result = poisson.evaluate_constant_poisson_scenario(model, 300000, count=0)
        self.assertAlmostEqual(result['conditional_mean'], 1000.0, delta=1e-12)
        self.assertEqual(result['likelihood_status'], 'FINITE_LOG_MASS')
        self.assertAlmostEqual(result['log_probability'], -1000.0, delta=1e-12)
        self.assertEqual(result['probability'], 0.0)
        absent = poisson.evaluate_constant_poisson_scenario(model, 300)
        self.assertEqual((absent['likelihood_status'],absent['probability'],absent['log_probability']), ('NOT_REQUESTED',None,None))

    def test_invalid_scenario_types_and_positive_product_underflow(self):
        model = self.fit()['model']
        for seconds in (True, -1, 12000001, 10**400, float('nan'), float('inf'), {'future_rows': []}):
            with self.assertRaises(ValueError): poisson.evaluate_constant_poisson_scenario(model, seconds)
        for count in (True, -1, 1.0, 100001, '2'):
            with self.assertRaises(ValueError): poisson.evaluate_constant_poisson_scenario(model, 300, count=count)
        with self.assertRaisesRegex(ValueError, 'NUMERIC_BLOCKED'):
            poisson.evaluate_constant_poisson_scenario(model, 5e-324)

    def test_nonrepresentable_fit_rate_is_numeric_not_missing(self):
        self.resize_intervals([5e-324] * 6)
        with self.assertRaisesRegex(ValueError, 'NUMERIC_BLOCKED'): self.fit()

    def test_finite_model_rate_can_still_overflow_a_scenario_mean(self):
        # A new internally coherent numerical declaration, not a claim that its
        # opaque historical source hashes prove these tiny exposure values.
        model = self.fit()['model']
        for row in model['training_units']: row['active_search_seconds'] = 1e-308
        exposure = math.fsum(row['active_search_seconds'] for row in model['training_units'])
        model['sufficient_statistics']['total_active_search_seconds'] = exposure
        model['parameters']['lambda_per_active_search_second'] = 6 / exposure
        keys = ('target','owner_id','observer_id','method_version','fit_cutoff','heldout_night','training_units')
        model['cohort_sha256'] = sha({key:model[key] for key in keys})
        model['model_sha256'] = sha({k:v for k,v in model.items() if k != 'model_sha256'})
        poisson.validate_constant_poisson_model(model)
        with self.assertRaisesRegex(ValueError,'NUMERIC_BLOCKED'):
            poisson.evaluate_constant_poisson_scenario(model, 12000000)

    def test_inputs_detach_and_models_contain_no_cached_likelihood(self):
        original = poisson.feasibility.assess_count_feasibility
        saved = copy.deepcopy(self.inputs)
        def mutate(*args, **kwargs):
            self.inputs[1]['rows'].clear()
            return original(*args, **kwargs)
        with patch.object(poisson.feasibility, 'assess_count_feasibility', mutate):
            result = self.fit()
        self.assertEqual(len(result['model']['training_units']), 6)
        self.assertEqual(result['input_digests']['count_projection'], sha(saved[1]))
        text = json.dumps(result['model'])
        for forbidden in ('training_log_likelihood','lgamma','platform','future_rows'):
            self.assertNotIn(forbidden, text)

    def test_same_runtime_repetition_and_false_flags_and_receipt_hashes(self):
        result = self.fit()
        self.assertEqual(result, self.fit())
        scenario = poisson.evaluate_constant_poisson_scenario(result['model'], 300, count=2)
        for value, key in ((result,'receipt_sha256'),(result['model'],'model_sha256'),(scenario,'receipt_sha256')):
            self.assertEqual(value[key], sha({k:v for k,v in value.items() if k != key}))
            for name in ('fit_authorized','scientific_execution_authorized','official_issuance_authorized',
                         'confirmation_authorized','selection_authorized','production_authorized'):
                self.assertIs(value[name], False)
            self.assertEqual(value['source_authenticity'], 'NOT_ATTESTED')
            self.assertEqual(value['source_authentication'], 'CALLER_DEPENDENCY_REQUIRED')
            self.assertEqual(value['statistical_adequacy'], 'NOT_ASSESSED')

    def test_no_files_or_network_used(self):
        with patch('builtins.open', side_effect=AssertionError('file')), patch.object(socket,'socket',side_effect=AssertionError('network')):
            fitted = self.fit()
            poisson.validate_constant_poisson_model(fitted['model'])
            poisson.evaluate_constant_poisson_scenario(fitted['model'], 300)

    def test_scenario_model_row_cap_is_before_any_owned_copy(self):
        model = self.fit()['model']
        with patch.object(poisson,'MAX_ROWS',5), patch.object(poisson,'_owned',side_effect=AssertionError('copy must not run')):
            with self.assertRaises(poisson.PoissonCapacityBlocked):
                poisson.evaluate_constant_poisson_scenario(model, 300)

    def test_empty_accepted_cohort_is_not_a_zero_rate_fit(self):
        self.inputs[0]['accepted'] = []
        for p in self.inputs[1:]: p.update(rows=[], source_nodes=[])
        self.rebind()
        result = self.fit()
        self.assertEqual(result['status'], 'NEED_MORE_DATA')
        self.assertIsNone(result['model'])

    def test_nonuniform_exposure_uses_pooled_rate_not_mean_of_rates(self):
        self.resize_intervals([100., 300., 200., 300., 300., 300.])
        result = self.fit()
        self.assertEqual(result['model']['parameters']['lambda_per_active_search_second'], 6 / 1500)
        incorrect = sum(r['count'] / e['active_search_seconds'] for r,e in zip(self.inputs[1]['rows'],self.inputs[2]['rows'])) / 6
        self.assertNotEqual(result['model']['parameters']['lambda_per_active_search_second'], incorrect)

    def test_caller_exception_identity_at_entry_and_inside_child_gate(self):
        failures = [RuntimeError('caller'), TimeoutError('caller'), MemoryError('caller'),
                    poisson.feasibility.CountCapacityBlocked('caller'),
                    poisson.selection_gate.ResearchInputCapacity('caller'),
                    poisson.ForecastCapacityError('caller')]
        original = poisson.feasibility.assess_count_feasibility
        for failure in failures:
            def check(): raise failure
            with self.assertRaises(type(failure)) as raised: self.fit(check=check)
            self.assertIs(raised.exception, failure)
            active = False
            def child(*args, **kwargs):
                nonlocal active
                active = True
                return original(*args, **kwargs)
            def nested_check():
                if active: raise failure
            with patch.object(poisson.feasibility, 'assess_count_feasibility', child):
                with self.assertRaises(type(failure)) as raised: self.fit(check=nested_check)
            self.assertIs(raised.exception, failure)

    def test_public_budget_and_check_types(self):
        model = self.fit()['model']
        operations = [lambda **kw:self.fit(**kw), lambda **kw:poisson.validate_constant_poisson_model(model,**kw),
                      lambda **kw:poisson.evaluate_constant_poisson_scenario(model,300,**kw)]
        for operation in operations:
            for seconds in (True,0,-1,31,10**400,float('nan'),float('inf')):
                with self.assertRaises(ValueError): operation(budget_seconds=seconds)
            with self.assertRaises(ValueError): operation(check=1)

    def test_caps_before_copy_and_named_child_capacity_failure(self):
        selected,count,effort = copy.deepcopy(self.inputs)
        selected['accepted'] = [None] * 20001
        with patch.object(poisson,'_owned',side_effect=AssertionError('copy must not run')):
            with self.assertRaisesRegex(poisson.PoissonCapacityBlocked,'CAPACITY_BLOCKED'):
                poisson.fit_constant_poisson(selected,count,effort)
        count['source_nodes'] = [None] * 16385
        with patch.object(poisson,'_owned',side_effect=AssertionError('copy must not run')):
            with self.assertRaises(poisson.PoissonCapacityBlocked):
                poisson.fit_constant_poisson(self.inputs[0],count,effort)
        with patch.object(poisson.feasibility,'MAX_LINEAGE_MEMBERSHIPS',0):
            with self.assertRaisesRegex(poisson.PoissonCapacityBlocked,'CAPACITY_BLOCKED'): self.fit()

    def test_combined_json_byte_node_depth_integer_and_recursive_bounds(self):
        raw=json.dumps(list(self.inputs),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        with patch.object(poisson,'MAX_JSON_BYTES',len(raw)-1):
            with self.assertRaises(poisson.PoissonCapacityBlocked): self.fit()
        with patch.object(poisson,'MAX_JSON_NODES',10):
            with self.assertRaises(poisson.PoissonCapacityBlocked): self.fit()
        recursive=[]; recursive.append(recursive)
        for value in (recursive,1<<16384,'x'*4097,[[[[[[[[[[[[[None]]]]]]]]]]]]]):
            with self.assertRaises(ValueError): poisson.validate_constant_poisson_model(value)
        for value in (float('nan'),float('inf'),{'x':object()},{1:'key'}):
            with self.assertRaises(ValueError): poisson.validate_constant_poisson_model(value)

    def test_child_receives_only_remaining_absolute_budget(self):
        clock=[0.]
        original_copy=poisson._owned
        original_gate=poisson.feasibility.assess_count_feasibility
        seen=[]
        def copied(value,guard):
            result=original_copy(value,guard)
            clock[0]=max(clock[0],5.)
            return result
        def gate(*args,**kwargs):
            seen.append(kwargs['budget_seconds'])
            return original_gate(*args,**kwargs)
        with patch.object(poisson,'monotonic',lambda:clock[0]), patch.object(poisson,'_owned',copied), patch.object(poisson.feasibility,'assess_count_feasibility',gate):
            self.fit()
        self.assertEqual(seen,[25.])

    def test_expiry_after_model_and_receipt_hashes_returns_nothing(self):
        model=self.fit()['model']
        operations=[(poisson.MODEL_VERSION,lambda:self.fit()),
                    (poisson.MODEL_VERSION,lambda:poisson.validate_constant_poisson_model(model)),
                    (poisson.FIT_VERSION,lambda:self.fit()),
                    (poisson.FIT_VERSION,lambda:poisson.fit_constant_poisson(self.inputs[0])),
                    (poisson.SCENARIO_VERSION,lambda:poisson.evaluate_constant_poisson_scenario(model,300))]
        original=poisson._digest
        for version,operation in operations:
            clock=[0.]
            def expired(value,guard):
                result=original(value,guard)
                if type(value) is dict and value.get('schema_version')==version:
                    clock[0]=31.
                return result
            with patch.object(poisson,'_digest',expired),patch.object(poisson,'monotonic',lambda:clock[0]):
                with self.assertRaises(TimeoutError): operation()

    def test_expiry_after_runtime_math_and_complete_export_is_checked(self):
        model=self.fit()['model']
        original_exp=poisson.math.exp
        clock=[0.]
        def expired_exp(value):
            result=original_exp(value); clock[0]=31.; return result
        with patch.object(poisson.math,'exp',expired_exp),patch.object(poisson,'monotonic',lambda:clock[0]):
            with self.assertRaises(TimeoutError): poisson.evaluate_constant_poisson_scenario(model,300)
        original_finish=poisson._finish
        def final_expiry(value,guard):
            result=original_finish(value,guard); clock[0]=31.; return result
        clock[0]=0.
        with patch.object(poisson,'_finish',final_expiry),patch.object(poisson,'monotonic',lambda:clock[0]):
            with self.assertRaises(TimeoutError): self.fit()


if __name__ == '__main__':
    unittest.main()
