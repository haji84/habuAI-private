"""Synthetic standalone tree mechanics; no real fit or registered candidate."""
import copy
import importlib
import importlib.metadata
import importlib.util
import math
import os
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from test_hba1_feature_candidate import fixture, sha
from test_prospective_candidate_model import history_rows, selection_for, rebind


def selection(rows=None):
    value = selection_for(history_rows()[:20] if rows is None else rows)
    counts = value['counts']
    ready = counts['nights'] >= 3 and min(counts['positives'], counts['negatives']) >= 2
    value.update(status='DEVELOPMENT_TRAINING_ELIGIBLE' if ready else 'NEED_MORE_DATA',
                 blockers=[] if ready else ['Insufficient known synthetic binary rows'])
    return rebind(value)


def recipe(module):
    return dict(schema_version='habu-hba2-gbc-recipe-v1', target=module.TARGET,
        algorithm='SKLEARN_GBC_BINARY_LOG_LOSS_ZERO_INIT_V1', feature_names=list(module.FEATURES),
        params=copy.deepcopy(module.PARAMS), runtime_versions=dict(module.PINS),
        requirements_sha256={path:'a'*64 for path in module.REQUIREMENT_PATHS},
        implementation_sha256={path:'b'*64 for path in module.CODE_PATHS})


def synthetic_model(module):
    """Hand-declared interpreter fixture, not a claim of library-fitted bytes."""
    spec = recipe(module)
    assessment = module.assess_hba2(selection(), recipe=spec, expected_recipe_sha256=sha(spec))
    runtime = dict(schema_version='habu-hba2-runtime-v1', status='PINNED_BACKEND_READY',
        expected_versions=dict(module.PINS), observed_versions=dict(module.PINS),
        auxiliary_versions={'joblib':'synthetic-declaration', 'threadpoolctl':'synthetic-declaration'},
        python_version='synthetic-declaration', python_implementation='synthetic-declaration',
        platform='synthetic-declaration', input_dtype='IEEE754_BINARY32',
        requirements_sha256=spec['requirements_sha256'], issues=[])
    fields = ('training_selection_sha256', 'corpus_sha256', 'source_sha256', 'source_received_at',
        'fit_cutoff', 'heldout_night', 'training_nights', 'training_window_start_max', 'counts',
        'training_rows_sha256', 'training_row_ids_sha256', 'raw_feature_rows_sha256')
    model = dict(schema_version='habu-hba2-research-model-v1', status='DEVELOPMENT_RESEARCH_FIT_ONLY',
        candidate_id='HB-A2', target_semantics=module.TARGET, recipe=spec, recipe_sha256=sha(spec),
        feature_names=list(module.FEATURES), input_dtype='IEEE754_BINARY32', initial_raw_score=0.0,
        learning_rate=0.1, classes=[0,1], runtime=runtime,
        trees=[dict(nodes=[dict(left=-1, right=-1, feature=None, threshold=None, value=.25)]) for _ in range(32)],
        **{key:copy.deepcopy(assessment[key]) for key in fields}, **module._flags())
    model['model_sha256'] = sha(model)
    return model


class HBA2PureTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('models.hba2_feature_candidate'), 'Missing approved HB-A2 module')
        self.module = importlib.import_module('models.hba2_feature_candidate')
        self.spec = recipe(self.module)

    def assess(self, value=None, **kw):
        return self.module.assess_hba2(selection() if value is None else value,
            recipe=self.spec, expected_recipe_sha256=sha(self.spec), **kw)

    def fit(self, value=None, **kw):
        return self.module.fit_hba2(selection() if value is None else value,
            recipe=self.spec, expected_recipe_sha256=sha(self.spec), **kw)

    def predict(self, model=None, rows=None, **kw):
        protocol, folds = fixture()
        rows = folds[0]['forecast_rows'] if rows is None else rows
        return self.module.predict_hba2(synthetic_model(self.module) if model is None else model,
            rows, cutoff_time=protocol['folds'][0]['cutoff_time'], joined_universe_sha256=sha(rows), **kw)

    def test_assessment_ready_is_not_a_fit_or_backend_probe(self):
        with patch.object(self.module, '_backend', side_effect=AssertionError('assessment imported backend')):
            result = self.assess()
        self.assertEqual(result['status'], 'SOFTWARE_INPUTS_READY')
        self.assertEqual((result['backend_status'], result['runtime']), ('NOT_PROBED', None))
        self.assertEqual(result['counts']['accepted_rows'], 20)
        self.assertEqual(result['receipt_sha256'], sha({k:v for k,v in result.items() if k != 'receipt_sha256'}))
        for key, value in self.module._flags().items(): self.assertEqual(result[key], value)

    def test_empty_single_class_and_small_valid_sets_need_without_backend(self):
        for rows in ([], history_rows()[:16], [r for r in history_rows()[:20] if not r['owner_capture_count']]):
            with self.subTest(rows=len(rows)), patch.object(self.module, '_backend', side_effect=AssertionError('insufficient imported backend')):
                value = selection(rows)
                result = self.fit(value)
                self.assertEqual(result['status'], 'NEED_MORE_DATA')
                self.assertEqual((result['model'], result['runtime'], result['export_consistency']), (None,None,None))

    def test_all_train_f32_preflight_before_insufficiency_or_backend(self):
        for rows in (history_rows()[:4], history_rows()[:20]):
            value = selection(rows)
            value['accepted'][-1]['features']['temperature_c'] = 1e300
            rebind(value)
            with patch.object(self.module, '_backend', side_effect=AssertionError('overflow imported backend')):
                with self.assertRaises(ValueError): self.fit(value)

    def test_known_contradictions_precede_need(self):
        baseline = selection(history_rows()[:4])
        for mutate in (lambda s:s['counts'].update(accepted_rows=True),
                lambda s:s['accepted'][0].update(label=None),
                lambda s:s['accepted'][0]['features'].update(humidity_pct=101),
                lambda s:s['accepted'][0].update(night=s['heldout_night'])):
            value = copy.deepcopy(baseline); mutate(value); rebind(value)
            with self.assertRaises(ValueError): self.assess(value)

    def test_recipe_changes_and_extra_fields_fail_even_empty(self):
        for mutate in (lambda s:s['params'].update(n_estimators=31),
                lambda s:s['params'].update(random_state=True),
                lambda s:s.update(extra=True), lambda s:s['feature_names'].reverse(),
                lambda s:s['runtime_versions'].update(numpy='2.3.5')):
            self.spec = recipe(self.module); mutate(self.spec)
            with self.assertRaises(ValueError): self.fit(selection([]))

    def test_pure_interpreter_scales_each_leaf_once_and_keeps_all_future_units(self):
        with patch.object(self.module, '_backend', side_effect=AssertionError('pure prediction imported backend')):
            result = self.predict()
        expected = round(1/(1+math.exp(-sum(.1*.25 for _ in range(32)))), 8)
        self.assertEqual(len(result['unit_predictions']), 4)
        self.assertTrue(all(r['probability'] == expected == r['spatial_score'] for r in result['unit_predictions']))
        self.assertIs(result['production_activation_authorized'], False)

    def test_rehashed_bad_model_and_tree_structure_fail(self):
        baseline = synthetic_model(self.module)
        mutations = [lambda m:m.update(official_issuance_authorized=True),
            lambda m:m['trees'].pop(), lambda m:m.update(initial_raw_score=1.0),
            lambda m:m.update(fit_cutoff='2026-10-12T00:00:00+09:00'),
            lambda m:m['counts'].update(positives=True),
            lambda m:m['trees'][0]['nodes'][0].update(value=True),
            lambda m:m['trees'][0]['nodes'][0].update(left=0, right=0, feature=0, threshold=22.0, value=None)]
        for mutate in mutations:
            model=copy.deepcopy(baseline); mutate(model)
            model['model_sha256']=sha({k:v for k,v in model.items() if k!='model_sha256'})
            with self.assertRaises(ValueError): self.predict(model)

    def test_future_raw_f32_and_strict_availability(self):
        _, folds = fixture()
        for value in (1e300, True):
            rows=copy.deepcopy(folds[0]['forecast_rows']); rows[-1]['features']['temperature_c']=value
            with self.assertRaises(ValueError): self.predict(rows=rows)
        rows=copy.deepcopy(folds[0]['forecast_rows'])
        rows[-1]['feature_available_at']['temperature_c']=rows[-1]['cutoff_time']
        with self.assertRaises(ValueError): self.predict(rows=rows)

    def test_shared_deadline_and_actual_combined_cap_release_nothing(self):
        with self.assertRaises(TimeoutError): self.fit(check=lambda: (_ for _ in ()).throw(TimeoutError('parent expired')))
        from models import hba1_feature_candidate as base
        with patch.object(base, 'MAX_JSON_BYTES', 256):
            with self.assertRaises(self.module.HBA2CapacityBlocked): self.assess()

    def test_current_native_missing_backend_is_explicit_not_a_fake_fit(self):
        result = self.fit()
        if result['status']=='CAPABILITY_BLOCKED':
            self.assertIsNone(result['model']); self.assertTrue(result['runtime']['issues'])
        else:
            self.assertEqual(result['status'], 'DEVELOPMENT_FIT_ONLY')

    def test_genuine_binary32_branch_neighbors_use_f64_threshold_without_extra_scaling(self):
        model=synthetic_model(self.module)
        model['trees']=[dict(nodes=[dict(left=-1,right=-1,feature=None,threshold=None,value=0.0)]) for _ in range(32)]
        model['trees'][0]=dict(nodes=[dict(left=1,right=2,feature=0,threshold=22.00000005,value=None),
            dict(left=-1,right=-1,feature=None,threshold=None,value=-.25),
            dict(left=-1,right=-1,feature=None,threshold=None,value=.5)])
        model['model_sha256']=sha({k:v for k,v in model.items() if k!='model_sha256'})
        _,folds=fixture(); rows=copy.deepcopy(folds[0]['forecast_rows'])
        # The first double lies ABOVE the double threshold but rounds down to
        # the lower binary32; the next float32 must take the other branch.
        rows[0]['features']['temperature_c']=22.00000008
        bits=struct.unpack('<I',struct.pack('<f',22.0))[0]
        rows[1]['features']['temperature_c']=struct.unpack('<f',struct.pack('<I',bits+1))[0]
        result=self.predict(model,rows)
        self.assertEqual(result['unit_predictions'][0]['probability'],round(1/(1+math.exp(.025)),8))
        self.assertEqual(result['unit_predictions'][1]['probability'],round(1/(1+math.exp(-.05)),8))

    def test_rehashed_nonfinite_partial_sum_never_becomes_clipped_probability(self):
        model=synthetic_model(self.module)
        for tree in model['trees']: tree['nodes'][0]['value']=1e308
        model['model_sha256']=sha({k:v for k,v in model.items() if k!='model_sha256'})
        with self.assertRaises(ValueError): self.predict(model)

    def test_invalid_tree_depth_shared_children_and_unreachable_nodes(self):
        leaf=dict(left=-1,right=-1,feature=None,threshold=None,value=.1)
        split=lambda a,b:dict(left=a,right=b,feature=0,threshold=22.0,value=None)
        for nodes in ([split(1,2),split(2,3),copy.deepcopy(leaf),copy.deepcopy(leaf)],
                      [copy.deepcopy(leaf),copy.deepcopy(leaf)],
                      [split(1,2),split(3,4),copy.deepcopy(leaf),split(5,6),copy.deepcopy(leaf),copy.deepcopy(leaf),copy.deepcopy(leaf)]):
            model=synthetic_model(self.module); model['trees'][0]['nodes']=nodes
            model['model_sha256']=sha({k:v for k,v in model.items() if k!='model_sha256'})
            with self.assertRaises(ValueError): self.predict(model)

    def test_final_seal_expiry_is_checked_for_all_public_apis(self):
        from models import hba1_feature_candidate as base
        actual=base._digest
        for version,action in [('habu-hba2-feasibility-v1',lambda check:self.assess(check=check)),
                ('habu-hba2-standalone-fit-v1',lambda check:self.fit(selection([]),check=check)),
                ('habu-hba2-unit-prediction-v1',lambda check:self.predict(check=check))]:
            expired=False
            def guard():
                if expired: raise TimeoutError('parent expired after seal')
            def digest(value,check):
                nonlocal expired
                result=actual(value,check)
                if type(value) is dict and value.get('schema_version')==version: expired=True
                return result
            with patch.object(base,'_digest',side_effect=digest):
                with self.assertRaises(TimeoutError): action(guard)

    def test_rows_caps_are_checked_before_copy_and_backend(self):
        value=selection(); value['accepted']*=1001
        with patch.object(self.module.base,'_own',side_effect=AssertionError('oversized TRAIN copied')):
            with self.assertRaises(self.module.HBA2CapacityBlocked): self.assess(value)
        model=synthetic_model(self.module)
        with patch.object(self.module.base,'_own',side_effect=AssertionError('oversized future copied')):
            with self.assertRaises(self.module.HBA2CapacityBlocked): self.predict(model=model,rows=[{}]*120001)

    def test_github_numeric_gate_fails_instead_of_skip_when_pins_missing(self):
        if all(self._version(name)==expected for name,expected in self.module.PINS.items()):
            return  # Real pinned case is exercised by the mandatory class.
        case=HBA2PinnedNumericTests('test_pinned_numeric_gate_cannot_skip_on_github_actions')
        result=unittest.TestResult()
        with patch.dict(os.environ,{'GITHUB_ACTIONS':'true'}): case.run(result)
        self.assertEqual(len(result.skipped),0)
        self.assertEqual(len(result.failures),1)

    def test_exact_receipt_fieldsets_and_no_registry_mutation(self):
        import research_model_adapter as registered
        before=registered.CANDIDATES
        flags=set(self.module._flags())
        assessment=self.assess()
        self.assertEqual(set(assessment),set(self.module.TRAIN_FIELDS)|flags|{
            'schema_version','status','purpose','registration_status','candidate_id','target_semantics',
            'recipe_sha256','backend_status','runtime','blockers','receipt_sha256'})
        result=self.fit(selection([]))
        self.assertEqual(set(result),flags|{'schema_version','status','purpose','registration_status',
            'candidate_id','target_semantics','recipe_sha256','assessment','model','runtime',
            'export_consistency','blockers','receipt_sha256'})
        prediction=self.predict()
        self.assertEqual(set(prediction),flags|{'schema_version','purpose','registration_status','candidate_id',
            'target_semantics','model_sha256','recipe_sha256','training_selection_sha256','universe_sha256',
            'cutoff_time','operational_night','unit_predictions','prediction_sha256'})
        self.assertEqual(registered.CANDIDATES,before)
        self.assertNotIn('HB-A2',registered.CANDIDATES)

    def test_future_outcome_leak_and_actual_geometry_cannot_be_rehashed_away(self):
        _,folds=fixture()
        for mutate in (lambda r:r.update(owner_capture_count=1),
                       lambda r:r.update(cell_x=True), lambda r:r['features'].update(actual_capture=1)):
            rows=copy.deepcopy(folds[0]['forecast_rows']); mutate(rows[-1])
            with self.assertRaises(ValueError): self.predict(rows=rows)

    @staticmethod
    def _version(name):
        try:return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:return None


class HBA2PinnedNumericTests(unittest.TestCase):
    def test_pinned_numeric_gate_cannot_skip_on_github_actions(self):
        self.assertIsNotNone(importlib.util.find_spec('models.hba2_feature_candidate'), 'Missing approved HB-A2 module')
        module=importlib.import_module('models.hba2_feature_candidate')
        exact=True
        for name, expected in module.PINS.items():
            try: actual=importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError: actual=None
            exact &= actual==expected
        if not exact and os.environ.get('GITHUB_ACTIONS','').lower()!='true':
            self.skipTest('Genuine pinned numerical backend unavailable locally; Ubuntu CI mandatory')
        self.assertTrue(exact, 'CI requires genuine exact existing numerical pins; skipping forbidden')
        from sklearn.ensemble import GradientBoostingClassifier
        import numpy as np
        spec=recipe(module); selected=selection()
        result=module.fit_hba2(selected, recipe=spec, expected_recipe_sha256=sha(spec))
        self.assertEqual(result['status'], 'DEVELOPMENT_FIT_ONLY')
        self.assertEqual(result['export_consistency']['rows_checked'],20)
        matrix=np.asarray([[r['features'][n] for n in module.FEATURES] for r in selected['accepted']],dtype=np.float32)
        labels=[r['label'] for r in selected['accepted']]
        reference=GradientBoostingClassifier(**module.PARAMS).fit(matrix,labels)
        _, folds=fixture(); future=folds[0]['forecast_rows']
        full=[*matrix.tolist(), *[[r['features'][n] for n in module.FEATURES] for r in future]]
        f32=np.asarray(full,dtype=np.float32)
        raw, prob=module._raw_prob(result['model']['trees'],f32.tolist(),lambda:None)
        self.assertTrue(np.allclose(raw,reference.decision_function(f32),rtol=0,atol=1e-12))
        self.assertTrue(np.allclose(prob,reference.predict_proba(f32)[:,1],rtol=0,atol=1e-12))
        # Genuine float32 neighbors, not float64 neighbors that collapse on cast.
        boundary=[]
        for tree in reference.estimators_[:,0]:
            native=tree.tree_; paths=tree.decision_path(matrix)
            for index in range(native.node_count):
                if native.children_left[index]==-1: continue
                threshold=float(native.threshold[index]); feature=int(native.feature[index])
                middle=np.float32(threshold)
                if float(middle)<=threshold:
                    lower=middle; upper=np.nextafter(middle,np.float32(math.inf),dtype=np.float32)
                else:
                    upper=middle; lower=np.nextafter(middle,np.float32(-math.inf),dtype=np.float32)
                self.assertLessEqual(float(lower),threshold); self.assertGreater(float(upper),threshold)
                source=next(i for i in range(len(matrix)) if paths[i,index])
                for value in (lower,upper):
                    row=matrix[source].copy(); row[feature]=value; boundary.append(row)
        self.assertTrue(boundary,'Synthetic fit should produce actual splits')
        boundary=np.asarray(boundary,dtype=np.float32)
        raw,prob=module._raw_prob(result['model']['trees'],boundary.tolist(),lambda:None)
        self.assertTrue(np.allclose(raw,reference.decision_function(boundary),rtol=0,atol=1e-12))
        self.assertTrue(np.allclose(prob,reference.predict_proba(boundary)[:,1],rtol=0,atol=1e-12))
        repeated=module.fit_hba2(selected,recipe=spec,expected_recipe_sha256=sha(spec))
        self.assertEqual(result['model']['model_sha256'],repeated['model']['model_sha256'])
        predicted=module.predict_hba2(result['model'],future,cutoff_time=future[0]['cutoff_time'],joined_universe_sha256=sha(future))
        future_matrix=np.asarray([[r['features'][n] for n in module.FEATURES] for r in future],dtype=np.float32)
        self.assertEqual([r['probability'] for r in predicted['unit_predictions']],
                         [round(float(p),8) for p in reference.predict_proba(future_matrix)[:,1]])
        # Fixed nonlinear family mechanic: two raw fields interact; no search,
        # held-out labels or accuracy certification is involved.
        history=history_rows()[:20]
        for i,row in enumerate(history):
            a,b=i%4&1,(i%4)>>1
            row.update(temperature_c=20.0+5*a,humidity_pct=60.0+30*b,
                precipitation_mm=0.0,slope_deg=10.0,tpi_m=0.0,road_length_m=30.0,
                wind_cross_road_proxy=.5,owner_capture_count=int(bool(a and b)))
        nonlinear=selection(history)
        fitted=module.fit_hba2(nonlinear,recipe=spec,expected_recipe_sha256=sha(spec))
        nonlinear_matrix=np.asarray([[r['features'][n] for n in module.FEATURES] for r in nonlinear['accepted']],dtype=np.float32)
        nonlinear_reference=GradientBoostingClassifier(**module.PARAMS).fit(nonlinear_matrix,[r['label'] for r in nonlinear['accepted']])
        raw,prob=module._raw_prob(fitted['model']['trees'],nonlinear_matrix.tolist(),lambda:None)
        self.assertGreater(abs(raw[3]-raw[2]-raw[1]+raw[0]),.1)
        self.assertTrue(np.allclose(raw,nonlinear_reference.decision_function(nonlinear_matrix),rtol=0,atol=1e-12))
        self.assertTrue(np.allclose(prob,nonlinear_reference.predict_proba(nonlinear_matrix)[:,1],rtol=0,atol=1e-12))
        # Actual public library stage callback raises the same parent timeout.
        expired=False; native_fit=GradientBoostingClassifier.fit
        def guard():
            if expired:raise TimeoutError('native stage parent expiry')
        def fit_with_expiry(estimator,x,y,**kwargs):
            monitor=kwargs['monitor']
            def wrapped(i,model,local):
                nonlocal expired
                expired=True
                return monitor(i,model,local)
            kwargs['monitor']=wrapped
            return native_fit(estimator,x,y,**kwargs)
        with patch.object(GradientBoostingClassifier,'fit',new=fit_with_expiry):
            with self.assertRaises(TimeoutError):
                module.fit_hba2(selected,recipe=spec,expected_recipe_sha256=sha(spec),check=guard)


if __name__=='__main__': unittest.main()
