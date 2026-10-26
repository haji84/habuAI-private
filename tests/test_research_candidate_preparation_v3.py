"""Pure fixed-three preparation controls; no real/source-qualified TRAIN claim."""
import copy
import importlib
import importlib.util
import inspect
import json
import time
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from master_contracts import digest
from test_hba1_feature_candidate import fixture,recipe as a1_recipe
from test_hba2_feature_candidate import recipe as a2_recipe,selection,synthetic_model
from test_research_selection import bind_selection
from models import hba1_feature_candidate as a1,hba2_feature_candidate as a2


class PreparationV3Tests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('research_candidate_preparation_v3'),
            'approved fixed-three preparation v3 is missing')
        self.api=importlib.import_module('research_candidate_preparation_v3')
        protocol,folds=fixture();self.train=folds[0]['training_selection'];self.rows=folds[0]['forecast_rows']
        self.cutoff=protocol['folds'][0]['cutoff_time'];self.definition='f'*64
        self.config=dict(schema_version='habu-research-candidate-config-v3',mode='DEVELOPMENT_ONLY',
            candidate_ids=['uniform','HB-A1','HB-A2'],hba1_recipe=a1_recipe(),hba2_recipe=a2_recipe(a2),
            feature_definition_sha256=self.definition)

    def call(self,**kw):
        expected=kw.pop('expected_config_sha256') if 'expected_config_sha256' in kw else digest(self.config)
        joined=kw.pop('joined_universe_sha256') if 'joined_universe_sha256' in kw else digest(self.rows)
        return self.api.prepare_research_candidates_v3(self.train,self.rows,candidate_config=self.config,
            expected_config_sha256=expected,cutoff_time=self.cutoff,
            joined_universe_sha256=joined,
            feature_definition_sha256=kw.pop('feature_definition_sha256',self.definition),**kw)

    def partial(self,names):
        self.train['feature_names']=sorted(names)
        for row in self.train['accepted']:row['features']={k:v for k,v in row['features'].items() if k in names}
        for row in self.rows:
            for key in ('features','feature_source_refs','feature_available_at'):
                row[key]={k:v for k,v in row[key].items() if k in names}
        bind_selection(self.train)

    def test_zero_train_returns_whole_need_without_native_fit(self):
        self.train=selection([]);before=copy.deepcopy((self.train,self.rows,self.config))
        with patch.object(a1,'fit_hba1',side_effect=AssertionError('partial A1')),\
                patch.object(a2,'fit_hba2',side_effect=AssertionError('NMD imported backend')):
            result=self.call()
        self.assertEqual(result['status'],'NEED_MORE_DATA');self.assertEqual(result['candidates'],[])
        self.assertEqual(result['candidate_ids'],['uniform','HB-A1','HB-A2'])
        self.assertIsNone(result['capability_receipt']);self.assertTrue(result['blockers'])
        self.assertEqual((self.train,self.rows,self.config),before)
        self.assertEqual(result['receipt_sha256'],digest({k:v for k,v in result.items() if k!='receipt_sha256'}))
        for key in ('fit_authorized','selection_authorized','promotion_authorized','scientific_execution_authorized',
                'official_issuance_authorized','production_activation_authorized'):
            self.assertIs(result[key],False)

    def test_exact_six_config_fixed_order_and_full_recipes_even_on_need(self):
        mutations=[lambda c:c['candidate_ids'].append('HB-A0'),lambda c:c['candidate_ids'].reverse(),
            lambda c:c.update(hba1_recipe=None),lambda c:c.update(hba2_recipe=None),
            lambda c:c.update(trusted=True),lambda c:c['hba1_recipe']['feature_mask'].__setitem__(0,False),
            lambda c:c['hba2_recipe']['params'].update(n_estimators=31)]
        for mutate in mutations:
            self.setUp();self.train=selection([]);mutate(self.config)
            with self.subTest(config=self.config),self.assertRaises(ValueError):self.call()

    def test_known_physical_and_finite32_last_values_precede_missing_schema(self):
        for name,number in [('humidity_pct',101),('precipitation_mm',-.1),('slope_deg',90),
                ('road_length_m',0),('wind_cross_road_proxy',1.01),('temperature_c',1e100),('tpi_m',1e100)]:
            for location in ('train','future'):
                self.setUp();self.partial({name})
                target=self.train['accepted'][-1] if location=='train' else self.rows[-1]
                target['features'][name]=number;bind_selection(self.train)
                with self.subTest(name=name,location=location),\
                        patch.object(a2,'fit_hba2',side_effect=AssertionError('contradiction reached fit')),\
                        self.assertRaises(ValueError):self.call()

    def test_valid_partial_and_small_full_support_release_no_candidates(self):
        self.partial({'humidity_pct'})
        self.assertEqual(self.call()['status'],'NEED_MORE_DATA')
        self.setUp();self.train['accepted']=self.train['accepted'][:16]
        self.train['counts'].update(accepted_rows=16,nights=4,positives=4,negatives=12);bind_selection(self.train)
        with patch.object(a2,'fit_hba2',side_effect=AssertionError('small set fitted')):
            result=self.call()
        self.assertEqual(result['status'],'NEED_MORE_DATA');self.assertEqual(result['candidates'],[])

    def test_all_known_row_identity_label_source_and_readiness_assertions_precede_need(self):
        for mode in ('availability','label','duplicate_future','counts','unknown_label','duplicate_train','source','nonfinite'):
            self.setUp();self.partial(set(a1.FEATURES)-{'temperature_c'})
            if mode=='availability':self.rows[-1]['feature_available_at']['humidity_pct']=self.cutoff
            elif mode=='label':self.rows[-1]['label']=1
            elif mode=='duplicate_future':self.rows[-1]=copy.deepcopy(self.rows[0])
            elif mode=='counts':self.train['counts']['accepted_rows']=True
            elif mode=='unknown_label':self.train['accepted'][-1]['label']=None
            elif mode=='duplicate_train':self.train['accepted'][-1]['row_id']=self.train['accepted'][0]['row_id']
            elif mode=='source':self.rows[-1]['feature_source_refs']['humidity_pct']=[]
            else:self.rows[-1]['features']['humidity_pct']=float('nan')
            bind_selection(self.train)
            joined='e'*64 if mode=='nonfinite' else digest(self.rows)
            with self.subTest(mode=mode),patch.object(a2,'fit_hba2',side_effect=AssertionError('contradiction reached fit')),\
                    self.assertRaises(ValueError):self.call(joined_universe_sha256=joined)

    def test_empty_future_and_unknown_schema_are_invalid_not_data_gap(self):
        self.rows=[]
        with self.assertRaises(ValueError):self.call()
        self.setUp();self.partial({'temperature_c'})
        self.train['feature_names']=['rain_mm']
        for row in self.train['accepted']:row['features']={'rain_mm':.5}
        for row in self.rows:
            row['features']={'rain_mm':.5};row['feature_source_refs']={'rain_mm':['features/synthetic.json']}
            row['feature_available_at']={'rain_mm':'2026-10-11T17:00:00+09:00'}
        bind_selection(self.train)
        with self.assertRaises(ValueError):self.call()

    def test_first_parent_abort_retains_original_instance(self):
        from research_model_adapter import ResearchCapacityBlocked
        for cls in (OverflowError,ResearchCapacityBlocked,KeyboardInterrupt,SystemExit):
            original=cls('original parent')
            def stop():raise original
            with self.subTest(cls=cls),self.assertRaises(BaseException) as caught:self.call(check=stop)
            self.assertIs(caught.exception,original)

    def test_invalid_large_budget_and_noncallable_parent_are_value_errors(self):
        self.train=selection([])
        for value in (True,0,-1,301,10**1000,float('nan'),float('inf'),'30'):
            caught=None
            try:self.call(budget_seconds=value)
            except BaseException as error:caught=error
            with self.subTest(kind=type(value).__name__):self.assertIsInstance(caught,ValueError)
        for value in (False,0,'check'):
            with self.subTest(check=value),self.assertRaises(ValueError):self.call(check=value)

    def test_caps_precede_parse_and_never_truncate_oversize_inputs(self):
        for kind in ('train','future','depth','string','bytes','nodes'):
            self.setUp()
            if kind=='train':self.train['accepted']=[None]*20001
            elif kind=='future':self.rows=[None]*120001
            elif kind=='depth':
                item=None
                for _ in range(14):item=[item]
                self.config['oversize']=item
            elif kind=='string':self.config['oversize']='x'*4097
            elif kind=='bytes':self.config['oversize']=['x'*4096]*4300
            else:self.config['oversize']=[None]*2000001
            with self.subTest(cap=kind),patch.object(self.api.json,'loads',side_effect=AssertionError('parsed before cap')),\
                    self.assertRaises(self.api.ResearchCapacityBlocked):self.call()

    def test_need_has_no_source_network_or_backend_activity(self):
        import socket
        self.train=selection([])
        with patch('builtins.open',side_effect=AssertionError('source file')),\
                patch.object(Path,'open',side_effect=AssertionError('source path')),\
                patch.object(socket,'socket',side_effect=AssertionError('network')),\
                patch.object(a2,'fit_hba2',side_effect=AssertionError('NMD backend')):
            result=self.call()
        self.assertEqual(result['status'],'NEED_MORE_DATA')

    def test_real_expiry_and_post_hash_parent_abort_release_nothing(self):
        self.train=selection([])
        with self.assertRaises(self.api.ResearchBudgetExhausted):self.call(budget_seconds=5e-324)
        original=TimeoutError('actual final parent');entered=[]
        def late():
            frame=inspect.currentframe().f_back
            while frame is not None:
                if frame.f_code.co_name=='_finish' and Path(frame.f_code.co_filename).name=='research_candidate_preparation_v3.py':
                    value=frame.f_locals.get('value')
                    if type(value) is dict and 'receipt_sha256' in value:
                        entered.append(True);raise original
                frame=frame.f_back
        with self.assertRaises(TimeoutError) as caught:self.call(check=late)
        self.assertIs(caught.exception,original);self.assertEqual(entered,[True])

    def test_real_deadline_is_rechecked_after_the_actual_final_callback(self):
        self.train=selection([]);entered=[]
        def spend_remaining():
            frame=inspect.currentframe().f_back
            while frame is not None:
                if frame.f_code.co_name=='_finish' and Path(frame.f_code.co_filename).name=='research_candidate_preparation_v3.py':
                    value=frame.f_locals.get('value')
                    if type(value) is dict and 'receipt_sha256' in value and not entered:
                        entered.append(True);time.sleep(1.05)
                frame=frame.f_back
        with self.assertRaises(self.api.ResearchBudgetExhausted):self.call(budget_seconds=1,check=spend_remaining)
        self.assertEqual(entered,[True])

    def test_actual_ready_runtime_is_whole_capability_or_complete_three(self):
        result=self.call()
        if result['status']=='CAPABILITY_BLOCKED':
            self.assertEqual(result['candidates'],[]);blocked=result['capability_receipt']
            self.assertEqual(blocked['status'],'CAPABILITY_BLOCKED');self.assertIsNone(blocked['model'])
            self.assertEqual(blocked['assessment']['counts']['accepted_rows'],20)
            self.assertEqual(blocked['runtime']['status'],'CAPABILITY_BLOCKED')
            self.assertTrue(blocked['runtime']['issues']);self.assertEqual(result['blockers'],blocked['blockers'])
        else:
            self.assertEqual(result['status'],'DIAGNOSTIC_CANDIDATES_PREPARED')
            self.assertEqual([c['candidate_id'] for c in result['candidates']],['uniform','HB-A1','HB-A2'])

    def test_pinned_numeric_gate_is_mandatory_on_actual_CI(self):
        import importlib.metadata
        versions={}
        for name in a2.PINS:
            try:versions[name]=importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:versions[name]=None
        if versions!=a2.PINS:
            if os.environ.get('GITHUB_ACTIONS','').lower()=='true':self.fail('Genuine required numeric pins missing: '+repr(versions))
            self.skipTest('Genuine pinned backend unavailable locally; actual CI required')
        result=self.call()
        self.assertEqual(result['status'],'DIAGNOSTIC_CANDIDATES_PREPARED')
        for c in result['candidates']:
            self.assertEqual(c['forecast_row_ids'],sorted(r['row_id'] for r in self.rows))
            self.assertEqual(c['training_rows_sha256'],digest(self.train['accepted']))
            self.assertEqual(c['training_selection_sha256'],self.train['selection_sha256'])
        native=a2.fit_hba2(self.train,recipe=self.config['hba2_recipe'],
            expected_recipe_sha256=digest(self.config['hba2_recipe']))
        self.assertEqual(result['candidates'][2]['model'],native['model'])
        self.assertEqual(result['candidates'][2]['fit_receipt']['export_consistency']['status'],'NATIVE_JSON_AGREEMENT')
        original=TimeoutError('genuine boosting monitor parent');entered=[]
        def stop_at_actual_monitor():
            frame=inspect.currentframe().f_back
            while frame is not None:
                if frame.f_code.co_name=='monitor' and Path(frame.f_code.co_filename).name=='hba2_feature_candidate.py':
                    entered.append(True);raise original
                frame=frame.f_back
        with self.assertRaises(TimeoutError) as caught:self.call(check=stop_at_actual_monitor)
        self.assertIs(caught.exception,original);self.assertEqual(entered,[True])


_GENUINE_A1_FIT=a1.fit_hba1
_A1_RECEIPT_CACHE={}


class NativeReturnAdmissionTests(unittest.TestCase):
    """Controlled declared JSON-return seams, never a native A2 fitter PASS.

    A2 uses the existing explicit constant-leaf interpreter fixture. A1 receipt
    is genuinely computed once. Only the separate pinned test above proves the
    full real-library fit path; none of these controls substitutes for it.
    """
    setUp=PreparationV3Tests.setUp
    call=PreparationV3Tests.call
    partial=PreparationV3Tests.partial

    def declared_a2(self):
        spec=self.config['hba2_recipe'];assessment=a2.assess_hba2(self.train,recipe=spec,expected_recipe_sha256=digest(spec))
        model=synthetic_model(a2)
        for field in a2.TRAIN_FIELDS:model[field]=copy.deepcopy(assessment[field])
        model['model_sha256']=digest({k:v for k,v in model.items() if k!='model_sha256'})
        value=dict(schema_version='habu-hba2-standalone-fit-v1',status='DEVELOPMENT_FIT_ONLY',
            recipe_sha256=digest(spec),assessment=assessment,model=model,runtime=copy.deepcopy(model['runtime']),
            export_consistency=dict(status='NATIVE_JSON_AGREEMENT',method='PUBLIC_DECISION_FUNCTION_AND_PREDICT_PROBA',
                rows_checked=20,tolerance=1e-12,max_abs_raw_error=0.0,max_abs_probability_error=0.0),
            blockers=[],**a2._common())
        value['receipt_sha256']=digest(value);return value

    def genuine_a1(self):
        key=(self.train['selection_sha256'],digest(self.config['hba1_recipe']))
        if key not in _A1_RECEIPT_CACHE:
            _A1_RECEIPT_CACHE[key]=_GENUINE_A1_FIT(self.train,recipe=self.config['hba1_recipe'],expected_recipe_sha256=key[1])
        return copy.deepcopy(_A1_RECEIPT_CACHE[key])

    def controlled_call(self,**kw):
        value2=self.declared_a2();value1=self.genuine_a1()
        with patch.object(a2,'fit_hba2',return_value=value2),patch.object(a1,'fit_hba1',return_value=value1):
            return self.call(**kw)

    def test_controlled_return_pipeline_retains_complete_three_native_artifacts(self):
        result=self.controlled_call()
        self.assertEqual([c['candidate_id'] for c in result['candidates']],['uniform','HB-A1','HB-A2'])
        self.assertEqual(result['candidates'][0]['model']['probability'],6/22)
        self.assertTrue(all(x['probability']==.68997448 for x in result['candidates'][2]['prediction']['unit_predictions']))
        for candidate in result['candidates'][1:]:
            fit=candidate['fit_receipt']
            self.assertEqual(fit['receipt_sha256'],digest({k:v for k,v in fit.items() if k!='receipt_sha256'}))
            self.assertEqual(fit['model'],candidate['model'])

    def test_returned_model_and_embedded_native_fit_receipt_are_independent_owned_values(self):
        result=self.controlled_call();candidate=result['candidates'][2]
        original=copy.deepcopy(candidate['fit_receipt'])
        candidate['model']['trees'][0]['nodes'][0]['value']=99.0
        self.assertEqual(candidate['fit_receipt'],original)

    def test_rehashed_uniform_model_score_or_unknown_authority_cannot_escape(self):
        native=self.api.legacy._uniform
        for mode in ('wrong_beta','wrong_unit','extra_authority'):
            def wrong(*args,**kwargs):
                model,prediction=native(*args,**kwargs)
                if mode=='wrong_beta':
                    model['probability']=.99;model['model_sha256']=digest({k:v for k,v in model.items() if k!='model_sha256'})
                    prediction['model_sha256']=model['model_sha256']
                    for row in prediction['unit_predictions']:row.update(probability=.99,spatial_score=.99)
                elif mode=='wrong_unit':prediction['unit_predictions'][-1].update(probability=.99,spatial_score=.99)
                else:prediction['fit_authorized']=True
                prediction['prediction_sha256']=digest({k:v for k,v in prediction.items() if k!='prediction_sha256'})
                return model,prediction
            with self.subTest(mode=mode),patch.object(self.api.legacy,'_uniform',side_effect=wrong),self.assertRaises(ValueError):
                self.controlled_call()

    def test_fully_sealed_outer_hash_overhead_is_counted_in_output_cap(self):
        self.train=selection([]);normal=self.call();body={k:v for k,v in normal.items() if k!='receipt_sha256'}
        size=len(json.dumps(body,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
        with patch.object(self.api,'MAX_OUTPUT_BYTES',size),self.assertRaises(self.api.ResearchCapacityBlocked):self.call()

    def test_actual_nested_A1_numeric_abort_restores_first_parent_object(self):
        receipt=self.declared_a2()
        for cls in (OverflowError,KeyError,a1.HBA1CapacityBlocked,KeyboardInterrupt):
            original=cls('actual nested parent');entered=[]
            def stop():
                frame=inspect.currentframe().f_back
                while frame is not None:
                    if frame.f_code.co_name=='_fit_numeric' and Path(frame.f_code.co_filename).name=='prospective_candidate_model.py':
                        entered.append(True);raise original
                    frame=frame.f_back
            with self.subTest(cls=cls),patch.object(a2,'fit_hba2',return_value=receipt),self.assertRaises(BaseException) as caught:
                self.call(check=stop)
            self.assertIs(caught.exception,original);self.assertEqual(entered,[True])

    def test_first_abort_is_sticky_even_when_child_swallows_it_and_parent_is_falsey(self):
        class FalseyOrigin(OverflowError):
            def __bool__(self):return False
            def __eq__(self,other):raise AssertionError('equality is not origin')
        original=FalseyOrigin('first');events=[];armed=[]
        def parent():
            if armed:
                events.append(True)
                if len(events)==1:raise original
                raise KeyError('replacement must not become origin')
        def swallowing(*args,**kwargs):
            armed.append(True)
            for _ in range(2):
                try:kwargs['check']()
                except BaseException:pass
            return None
        with patch.object(a2,'fit_hba2',side_effect=swallowing),self.assertRaises(BaseException) as caught:
            self.call(check=parent)
        self.assertIs(caught.exception,original);self.assertEqual(events,[True])

    def test_actual_blocked_receipt_is_validated_before_whole_capability_return(self):
        import importlib.metadata
        with patch.object(a2.importlib.metadata,'version',side_effect=importlib.metadata.PackageNotFoundError('control')):
            blocked=a2.fit_hba2(self.train,recipe=self.config['hba2_recipe'],expected_recipe_sha256=digest(self.config['hba2_recipe']))
        self.assertEqual(blocked['status'],'CAPABILITY_BLOCKED')
        for mode in ('model','assessment','runtime','blockers','authority'):
            value=copy.deepcopy(blocked)
            if mode=='model':value['model']={}
            elif mode=='assessment':value['assessment']['counts']['positives']=True
            elif mode=='runtime':value['runtime']['observed_versions']['numpy']=a2.PINS['numpy']
            elif mode=='blockers':value['blockers']=[]
            else:value['official_issuance_authorized']=True
            value['receipt_sha256']=digest({k:v for k,v in value.items() if k!='receipt_sha256'})
            with self.subTest(mode=mode),patch.object(a2,'fit_hba2',return_value=value),\
                    patch.object(a1,'fit_hba1',side_effect=AssertionError('partial A1')),self.assertRaises(ValueError):self.call()

    def test_native_fit_or_prediction_contradictions_reject_whole_set(self):
        for mode in ('assessment','recipe','rows','authority','export','prediction','prediction_order'):
            value=self.declared_a2();value1=self.genuine_a1()
            if mode=='assessment':
                value['assessment']['counts']['accepted_rows']=21
                value['assessment']['receipt_sha256']=digest({k:v for k,v in value['assessment'].items() if k!='receipt_sha256'})
            elif mode=='recipe':value['model']['recipe']['implementation_sha256']['src/models/hba2_feature_candidate.py']='c'*64
            elif mode=='rows':value['model']['training_row_ids_sha256']='d'*64
            elif mode=='authority':value['fit_authorized']=0
            elif mode=='export':value['export_consistency']['rows_checked']=True
            value['model']['model_sha256']=digest({k:v for k,v in value['model'].items() if k!='model_sha256'})
            value['receipt_sha256']=digest({k:v for k,v in value.items() if k!='receipt_sha256'})
            native=a2.predict_hba2
            def wrong_prediction(*args,**kwargs):
                result=native(*args,**kwargs)
                if mode=='prediction_order':result['unit_predictions'].reverse()
                else:result['unit_predictions'][-1]['probability']=.12
                result['prediction_sha256']=digest({k:v for k,v in result.items() if k!='prediction_sha256'})
                return result
            context=patch.object(a2,'predict_hba2',side_effect=wrong_prediction) if mode.startswith('prediction') else patch.object(a2,'predict_hba2',wraps=native)
            with self.subTest(mode=mode),patch.object(a2,'fit_hba2',return_value=value),\
                    patch.object(a1,'fit_hba1',return_value=value1),context,self.assertRaises(ValueError):self.call()


if __name__=='__main__':unittest.main()
