"""Synthetic Gamma-Poisson mechanics, never real source/forecast authority."""
import copy
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from master_contracts import digest
from tests.test_count_feasibility import fixture as count_fixture
from tests.test_count_feasibility import seal
from tests.test_research_selection import bind_selection
from tests.test_g0_planned_effort_projection import PlanFixture, ASOF


def protocol():
    """Explicit invented test parameters, not defaults for any real prediction."""
    return dict(schema_version='habu-gamma-poisson-protocol-v1',
        family='GAMMA_POISSON_SHAPE_RATE',
        target='OWNER_CAPTURED_HABU_INDIVIDUALS_DURING_MEASURED_ACTIVE_SEARCH',
        frozen_at='2026-09-01T00:00:00+09:00',
        prior=dict(alpha=2.0, beta_active_search_hours=3.0),
        quantiles=[0.05, 0.5, 0.95],
        numerics=dict(cdf_absolute_tolerance=1e-12, log_tail_tolerance=1e-10),
        capacities=dict(min_shape=1e-8, max_shape=1e8, min_rate_hours=1e-8,
            max_rate_hours=1e8, max_exposure_hours=100.0,
            max_training_units=20000, max_planned_units=120000,
            max_quantiles=32, max_output_count=1000000,
            max_json_bytes=16*1024**2, max_json_nodes=2000000,
            max_fit_seconds=30.0, max_predict_seconds=30.0),
        reference=dict(active_search_hours=1.0, owner_id='synthetic-owner',
            observer_id='synthetic-observer', method_version='independent-clock-v1'),
        runtime_versions={'numpy':'2.2.6','scipy':'1.15.3','scikit-learn':'1.5.2'})


def plan_fixture():
    p = PlanFixture()
    p.identity['method_version'] = 'independent-clock-v1'
    p.plan['method_version'] = p.identity['method_version']
    p.publish()
    return p


def plan_inputs(p):
    return dict(raw_plan_utf8=p.raw.decode('utf-8'), domain=copy.deepcopy(p.domain),
        bindings=copy.deepcopy(p.bindings), expected_domain_sha256=digest(p.domain),
        expected_identity=copy.deepcopy(p.identity), as_of_time=ASOF)


class CountActivityTests(unittest.TestCase):
    def setUp(self):
        try:
            self.module = importlib.import_module('count_activity')
        except ModuleNotFoundError:
            self.fail('Gamma-Poisson baseline is not implemented')
        self.inputs = count_fixture()
        self.protocol = protocol()

    def flags(self, result):
        for name in ('fit_authorized','scientific_execution_authorized',
                     'selection_authorized','promotion_authorized','confirmation_authorized',
                     'official_issuance_authorized','production_authorized'):
            self.assertIs(result[name], False)
        self.assertEqual(result['source_authenticity'], 'NOT_ATTESTED')
        self.assertEqual(result['scientific_status'], 'NOT_VALIDATED')

    def fit(self, **kwargs):
        result = self.module.fit_gamma_poisson(*self.inputs, protocol=self.protocol, **kwargs)
        self.flags(result)
        return result

    def predict(self, model, p=None, **kwargs):
        result = self.module.predict_gamma_poisson(model, plan_inputs(p or plan_fixture()),
            protocol=self.protocol, **kwargs)
        self.flags(result)
        return result

    def test_actual_shape_rate_posterior_is_whole_declared_cohort(self):
        before = copy.deepcopy(self.inputs)
        result = self.fit()
        self.assertEqual(result['status'], 'POSTERIOR_COMPUTED')
        model = result['model']
        self.flags(model)
        self.assertEqual(model['posterior'], dict(shape=8.0, rate_active_search_hours=3.5))
        self.assertEqual(model['sufficient_statistics']['total_individuals'], 6)
        self.assertEqual(model['sufficient_statistics']['total_active_search_seconds'], 1800.0)
        self.assertEqual(model['sufficient_statistics']['total_active_search_hours'], 0.5)
        self.assertEqual(model['protocol_sha256'], digest(self.protocol))
        self.assertEqual(model['model_sha256'], digest({k:v for k,v in model.items() if k!='model_sha256'}))
        self.assertEqual(self.inputs, before)

    def test_planned_prediction_and_literal_quantiles_and_shared_rate_variance(self):
        model = self.fit()['model']
        result = self.predict(model)
        self.assertEqual(result['status'], 'PREDICTED')
        count = result['predictions']['conditional_capture_count']
        self.assertAlmostEqual(count['mean'], 4/7, delta=1e-14)
        self.assertAlmostEqual(count['variance'], 30/49, delta=1e-14)
        self.assertAlmostEqual(count['probability_zero'], (14/15)**8, delta=1e-14)
        self.assertAlmostEqual(count['probability_at_least_one'], 1-(14/15)**8, delta=1e-14)
        self.assertEqual([q['count'] for q in count['quantiles']], [0,0,2])
        marginal_variance_sum = 4/7 + 3*(1/12)**2*8/3.5**2
        self.assertGreater(count['variance'], marginal_variance_sum)
        proxy = result['predictions']['capture_activity_proxy']
        self.assertAlmostEqual(proxy['mean'], 16/7, delta=1e-14)
        self.assertEqual(result['produced_outputs'], ['planned_capture_count','capture_activity_proxy'])
        self.assertFalse(result['biological_tonight_activity_validated'])
        self.assertFalse(result['detection_probability_produced'])

    def test_explicit_empty_future_plan_is_degenerate_not_measured_zero(self):
        model = self.fit()['model']
        p = plan_fixture(); p.plan['allocations']=[]; p.publish()
        result = self.predict(model,p)
        count = result['predictions']['conditional_capture_count']
        self.assertEqual((count['mean'],count['variance'],count['probability_zero'],count['probability_at_least_one']), (0,0,1,0))
        self.assertEqual([q['count'] for q in count['quantiles']], [0,0,0])

    def test_missing_count_effort_and_raw_plan_block_instead_of_inventing(self):
        for index in (1,2):
            inputs = list(self.inputs); inputs[index]=None
            result=self.module.fit_gamma_poisson(*inputs,protocol=self.protocol)
            self.assertEqual(result['status'],'DATA_BLOCKED');self.assertIsNone(result['model']);self.flags(result)
        model=self.fit()['model'];inputs=plan_inputs(plan_fixture());inputs['raw_plan_utf8']=None
        result=self.module.predict_gamma_poisson(model,inputs,protocol=self.protocol)
        self.assertEqual(result['status'],'DATA_BLOCKED');self.assertIsNone(result['predictions']);self.flags(result)

    def test_model_posterior_tamper_fails_even_after_rehash(self):
        model=self.fit()['model'];model['posterior']['shape']+=1
        model['model_sha256']=digest({k:v for k,v in model.items() if k!='model_sha256'})
        with self.assertRaises(ValueError):
            self.module.validate_gamma_poisson_model(model,protocol=self.protocol)

    def test_prior_quantiles_and_tolerances_are_mandatory(self):
        for name in ('prior','quantiles','numerics','capacities','runtime_versions'):
            p=protocol();p.pop(name)
            with self.subTest(name=name),self.assertRaises(ValueError):
                self.module.fit_gamma_poisson(*self.inputs,protocol=p)

    def test_quantile_capacity_preserves_verified_mean_without_fake_interval(self):
        self.protocol['capacities']['max_output_count']=0
        result=self.predict(self.fit()['model'])
        self.assertEqual(result['status'],'NUMERICAL_CAPACITY_EXCEEDED')
        count=result['predictions']['conditional_capture_count']
        self.assertAlmostEqual(count['mean'],4/7,delta=1e-14)
        self.assertIsNone(count['quantiles'])

    def test_wrong_actual_scipy_version_never_uses_fallback(self):
        import scipy
        with patch.object(scipy,'__version__','0.0.0'):
            result=self.fit()
        self.assertEqual(result['status'],'RUNTIME_BINDING_ERROR')
        self.assertIsNone(result['model'])

    def zero_cohort(self):
        selected,count,effort=self.inputs
        for row in selected['accepted']:row.update(label=0,capture_event_ids=[])
        for row in count['rows']:row.update(count=0,events=[],individual_source_ids=[])
        count['source_nodes']=[n for n in count['source_nodes'] if n['id']!='outcomes']
        selected['counts'].update(positives=0,negatives=6)
        selected.update(status='NEED_MORE_DATA',blockers=['Synthetic binary support missing'])
        bind_selection(selected)
        for value in (count,effort):value['selection_sha256']=selected['selection_sha256'];seal(value)

    def test_fractional_prior_and_verified_zero_counts_still_have_a_posterior(self):
        self.zero_cohort();self.protocol['prior']=dict(alpha=0.5,beta_active_search_hours=0.25)
        model=self.fit()['model'];self.assertEqual(model['posterior'],dict(shape=0.5,rate_active_search_hours=0.75))
        result=self.predict(model);self.assertEqual(result['status'],'PREDICTED')
        from scipy.stats import nbinom
        for quantile in result['predictions']['conditional_capture_count']['quantiles']:
            q,k=quantile['probability'],quantile['count']
            self.assertGreaterEqual(nbinom.cdf(k,0.5,0.75),q)
            self.assertLess(nbinom.cdf(k-1,0.5,0.75),q)

    def test_cohort_hash_and_posterior_do_not_accept_boolean_zero_statistics(self):
        self.zero_cohort();model=self.fit()['model']
        model['sufficient_statistics']['total_individuals']=False
        model['model_sha256']=digest({k:v for k,v in model.items() if k!='model_sha256'})
        with self.assertRaises(ValueError):self.module.validate_gamma_poisson_model(model,protocol=self.protocol)

    def test_unavailable_moments_do_not_claim_a_produced_count_output(self):
        self.protocol['capacities']['max_exposure_hours']=0.1
        self.protocol['reference']['active_search_hours']=0.05
        result=self.predict(self.fit()['model'])
        self.assertEqual(result['status'],'NUMERICAL_CAPACITY_EXCEEDED')
        self.assertIsNone(result['predictions']['conditional_capture_count']['mean'])
        self.assertNotIn('planned_capture_count',result['produced_outputs'])
        self.assertIn('capture_activity_proxy',result['produced_outputs'])

    def test_utf8_whitespace_preserved_and_unsupported_surrogate_blocks(self):
        p=plan_fixture();p.publish(json.dumps(p.plan,ensure_ascii=False,indent=2).encode())
        result=self.predict(self.fit()['model'],p)
        self.assertEqual(result['planned_source_sha256'],hashlib.sha256(p.raw).hexdigest())
        self.assertNotEqual(result['planned_source_sha256'],digest(p.plan))
        inputs=plan_inputs(p);inputs['raw_plan_utf8']='\ud800'
        result=self.module.predict_gamma_poisson(self.fit()['model'],inputs,protocol=self.protocol)
        self.assertEqual(result['status'],'DATA_BLOCKED');self.assertIsNone(result['predictions'])

    def test_bom_is_never_stripped_to_change_original_hash(self):
        p=plan_fixture();p.publish(b'\xef\xbb\xbf'+p.raw)
        result=self.predict(self.fit()['model'],p)
        self.assertEqual(result['status'],'DATA_BLOCKED')
        self.assertIn('PLAN_BOM_UNSUPPORTED_BY_EXISTING_PROJECTOR',result['missing_requirements'])
        p.bindings['source']['ref']['sha256']='0'*64
        with self.assertRaises(ValueError):self.predict(self.fit()['model'],p)

    def test_plan_gates_reject_late_wrong_hash_identity_and_crew(self):
        model=self.fit()['model']
        p=plan_fixture();p.delay('source','source_received_at',p.domain['cutoff_time'])
        result=self.predict(model,p);self.assertEqual(result['status'],'DATA_BLOCKED')
        p=plan_fixture();p.bindings['source']['ref']['sha256']='0'*64
        with self.assertRaises(ValueError):self.predict(model,p)
        p=plan_fixture();p.identity['observer_id']='other';p.plan['observer_id']='other';p.publish()
        with self.assertRaises(ValueError):self.predict(model,p)
        p=plan_fixture();p.identity['crew_size']=2;p.plan['crew_size']=2;p.publish()
        with self.assertRaises(ValueError):self.predict(model,p)

    def test_missing_or_unknown_plan_never_becomes_an_actual_zero_outcome(self):
        p=plan_fixture();p.plan['coverage']='UNKNOWN';p.publish()
        result=self.predict(self.fit()['model'],p)
        self.assertEqual(result['status'],'DATA_BLOCKED');self.assertIsNone(result['predictions'])

    def test_scipy_bad_ppf_never_manufactures_an_interval(self):
        from scipy.stats import nbinom
        model=self.fit()['model']
        for value in (math.nan,1.5,-1,1e100):
            with self.subTest(value=value),patch.object(nbinom,'ppf',return_value=value):
                result=self.predict(model)
                self.assertNotEqual(result['status'],'PREDICTED')
                self.assertIsNone(result['predictions']['conditional_capture_count']['quantiles'])
                self.assertAlmostEqual(result['predictions']['conditional_capture_count']['mean'],4/7,delta=1e-14)

    def test_scipy_wrong_integer_quantile_and_nonmonotonicity_are_detected(self):
        from scipy.stats import nbinom
        model=self.fit()['model']
        with patch.object(nbinom,'ppf',return_value=1):
            result=self.predict(model)
        self.assertEqual(result['status'],'NUMERICAL_NONCONVERGENCE')
        self.assertIsNone(result['predictions']['conditional_capture_count']['quantiles'])

    def test_source_count_effort_contract_is_not_replaced_by_availability_flags(self):
        self.inputs[1]['rows'][0]['count']=True;seal(self.inputs[1])
        with self.assertRaises(ValueError):self.fit()
        self.inputs=count_fixture();self.inputs[2]['rows'][0]['active_search_seconds']=0;seal(self.inputs[2])
        with self.assertRaises(ValueError):self.fit()
        self.inputs=count_fixture();self.inputs[1]['rows'][0]['complete_scope']['declaration']='UNKNOWN';seal(self.inputs[1])
        result=self.fit();self.assertEqual(result['status'],'DATA_BLOCKED');self.assertIsNone(result['model'])

    def test_model_protocol_and_authority_fields_cannot_be_rewritten(self):
        model=self.fit()['model']
        model['production_authorized']=True;model['model_sha256']=digest({k:v for k,v in model.items() if k!='model_sha256'})
        with self.assertRaises(ValueError):self.predict(model)
        model=self.fit()['model'];self.protocol['prior']['alpha']=3
        with self.assertRaises(ValueError):self.predict(model)

    def test_protocol_capacities_and_numerics_are_typed_finite_and_explicit(self):
        for field,value in [('alpha',True),('alpha',0),('beta_active_search_hours',math.inf)]:
            self.protocol=protocol();self.protocol['prior'][field]=value
            with self.assertRaises(ValueError):self.fit()
        for quantiles in ([0],[1],[0.5,0.05],[True],[math.nan]):
            self.protocol=protocol();self.protocol['quantiles']=quantiles
            with self.assertRaises(ValueError):self.fit()
        self.protocol=protocol();self.protocol['capacities']['max_json_nodes']=True
        with self.assertRaises(ValueError):self.fit()

    def test_frozen_protocol_and_training_must_precede_heldout_and_prediction(self):
        self.protocol['frozen_at']=self.inputs[0]['fit_cutoff']
        with self.assertRaises(ValueError):self.fit()
        self.protocol=protocol();model=self.fit()['model']
        model['training_units'][0]['night']='2026-10-26'
        model['model_sha256']=digest({k:v for k,v in model.items() if k!='model_sha256'})
        with self.assertRaises(ValueError):self.predict(model)

    def test_rejected_foreign_types_never_execute_methods_or_metaclass_equality(self):
        calls=[]
        class Meta(type):
            def __eq__(cls,other):calls.append('eq');raise AssertionError('candidate code')
            def __hash__(cls):calls.append('hash');raise AssertionError('candidate code')
        class Probe(metaclass=Meta):
            def __float__(self):calls.append('float');raise AssertionError('candidate code')
        class Mapping(dict):
            def items(self):calls.append('items');raise AssertionError('candidate code')
        for value in (Probe(),Mapping()):
            self.protocol=protocol();self.protocol['prior']['alpha']=value
            with self.assertRaises(ValueError):self.fit()
        self.protocol=protocol()
        with self.assertRaises(ValueError):self.fit(budget_seconds=Probe())
        self.assertEqual(calls,[])

    def test_deadline_and_invalid_huge_budgets_cannot_reset_or_escape(self):
        for seconds in (True,0,-1,301,math.nan,math.inf,10**1000):
            with self.assertRaises(ValueError):self.fit(budget_seconds=seconds)
        with patch.object(self.module.time,'monotonic',side_effect=[0.0,400.0]):
            with self.assertRaises(self.module.CountActivityCapacityError):self.fit()

    def test_fit_and_prediction_make_no_model_source_network_or_process_writes(self):
        import socket,subprocess
        # Runtime imports and version reads are permitted; no input data file,
        # registry, model, credentials or network transport is selected.
        self.fit()
        with patch.object(Path,'write_bytes',side_effect=AssertionError('write')), \
             patch.object(Path,'write_text',side_effect=AssertionError('write')), \
             patch.object(socket.socket,'connect',side_effect=AssertionError('network')), \
             patch.object(subprocess,'Popen',side_effect=AssertionError('process')):
            self.predict(self.fit()['model'])

    def test_numeric_protocol_runtime_and_elapsed_are_recorded_separately(self):
        first=self.fit()['model'];second=self.fit()['model']
        self.assertEqual(first,second)
        value=self.predict(first)
        self.assertEqual(value['runtime_versions'],self.protocol['runtime_versions'])
        self.assertGreaterEqual(value['runtime_elapsed_seconds'],0)
        self.assertEqual(value['numerical_protocol'],{k:self.protocol[k] for k in ('quantiles','numerics','capacities')})
        prediction=value['predictions']['conditional_capture_count']
        self.assertAlmostEqual(prediction['log_probability_zero'],-8*math.log1p(0.25/3.5),delta=1e-14)

    def test_upper_tail_inverse_check_does_not_trust_a_rounded_cdf_of_one(self):
        from scipy.stats import nbinom
        self.protocol['quantiles']=[math.nextafter(1.0,0.0)]
        model=self.fit()['model']
        with patch.object(nbinom,'ppf',return_value=0), \
             patch.object(nbinom,'cdf',side_effect=lambda k,*args: 0.0 if k<0 else 1.0), \
             patch.object(nbinom,'logcdf',return_value=0.0):
            result=self.predict(model)
        self.assertEqual(result['status'],'NUMERICAL_NONCONVERGENCE')
        self.assertIsNone(result['predictions']['conditional_capture_count']['quantiles'])

    def test_real_extreme_tail_quantiles_pass_independent_survival_inverse_checks(self):
        from scipy.stats import nbinom
        self.protocol['quantiles']=[1e-12,0.5,1-1e-12]
        result=self.predict(self.fit()['model']);self.assertEqual(result['status'],'PREDICTED')
        for q in result['predictions']['conditional_capture_count']['quantiles']:
            k,prob=q['count'],q['probability']
            self.assertLessEqual(nbinom.logsf(k,8,14/15),math.log1p(-prob)+1e-10)
            self.assertGreater(nbinom.logsf(k-1,8,14/15),math.log1p(-prob))

    def test_numerical_probability_underflow_is_exposed_with_its_finite_log(self):
        self.protocol['prior']['alpha']=99999994.0
        result=self.predict(self.fit()['model'])
        count=result['predictions']['conditional_capture_count']
        self.assertEqual(count['probability_zero'],0.0)
        self.assertTrue(count['probability_zero_underflowed'])
        self.assertTrue(math.isfinite(count['log_probability_zero']))
        self.assertLess(count['log_probability_zero'],-1000)

    def test_model_training_table_shape_and_capacity_are_checked_before_iteration(self):
        model=self.fit()['model']
        for table in (None,False,1,{},[]):
            value=copy.deepcopy(model);value['training_units']=table
            with self.subTest(kind=type(table).__name__),self.assertRaises(ValueError):
                self.module.validate_gamma_poisson_model(value,protocol=self.protocol)
        self.protocol['capacities']['max_training_units']=3
        model['protocol']=copy.deepcopy(self.protocol);model['protocol_sha256']=digest(self.protocol)
        model['model_sha256']=digest({k:v for k,v in model.items() if k!='model_sha256'})
        with self.assertRaises(self.module.CountActivityCapacityError):
            self.module.validate_gamma_poisson_model(model,protocol=self.protocol)


if __name__ == '__main__':
    unittest.main()
