"""Caller aborts remain caller objects; internal A2 classification stays intact."""
import builtins
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests'),str(ROOT)]
from models import hba2_feature_candidate as model
from models import hba1_feature_candidate as base
from models.research_selection import ResearchInputCapacity
from master_contracts import canonical_bytes
import test_hba2_feature_candidate as fixtures
from test_hba1_feature_candidate import fixture,sha

# Genuine immutable pre-repair00f7 _run source, not a rewritten expectation.
# All other production bodies are unchanged by this repair; public operations
# below execute their real current code with this independently compiled runner.
OLD_RUN_SOURCE="""def _run(function, seconds, check):
    try:
        return function(base._budget(seconds, check))
    except (base.HBA1CapacityBlocked, ResearchInputCapacity) as exc:
        raise HBA2CapacityBlocked('CAPACITY_BLOCKED: '+str(exc)) from exc
    except (KeyError, TypeError, IndexError, OverflowError, RecursionError) as exc:
        raise ValueError('Invalid HB-A2 contract structure') from exc
"""
WRAPPED=(base.HBA1CapacityBlocked,ResearchInputCapacity,KeyError,TypeError,IndexError,OverflowError,RecursionError)
CONTROLS=(model.HBA2CapacityBlocked,ValueError,TimeoutError,OSError,KeyboardInterrupt,SystemExit,MemoryError)
SCHEMAS={'assess':'habu-hba2-feasibility-v1','fit_NMD':'habu-hba2-standalone-fit-v1',
         'predict_JSON':'habu-hba2-unit-prediction-v1'}


class HBA2CallbackOriginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipe=fixtures.recipe(model)
        cls.training=fixtures.selection()
        cls.insufficient=fixtures.selection(fixtures.history_rows()[:4])
        cls.hand_model=fixtures.synthetic_model(model)
        protocol,folds=fixture()
        cls.rows=folds[0]['forecast_rows'];cls.cutoff=protocol['folds'][0]['cutoff_time']
        namespace=dict(base=base,ResearchInputCapacity=ResearchInputCapacity,HBA2CapacityBlocked=model.HBA2CapacityBlocked)
        exec(compile(OLD_RUN_SOURCE,'<genuine-native00f7-A2-run>','exec'),namespace)
        cls.old_run=staticmethod(namespace['_run'])

    def operations(self):
        return {
            'assess':lambda check:model.assess_hba2(self.training,recipe=self.recipe,
                expected_recipe_sha256=sha(self.recipe),check=check),
            'fit_NMD':lambda check:model.fit_hba2(self.insufficient,recipe=self.recipe,
                expected_recipe_sha256=sha(self.recipe),check=check),
            'predict_JSON':lambda check:model.predict_hba2(self.hand_model,self.rows,cutoff_time=self.cutoff,
                joined_universe_sha256=sha(self.rows),check=check),
        }

    def assert_origin_at(self,site):
        for name,operation in self.operations().items():
            for kind in WRAPPED+CONTROLS:
                with self.subTest(API=name,site=site,caller=kind.__name__):
                    marker=kind('caller abort must retain this instance')
                    calls=0;hash_returned=False;native_digest=base._digest
                    def check():
                        nonlocal calls
                        calls+=1
                        if site=='first' or site=='later' and calls>=10 or site=='after_hash' and hash_returned:
                            raise marker
                    def observing_digest(value,guard):
                        nonlocal hash_returned
                        result=native_digest(value,guard)
                        if type(value) is dict and value.get('schema_version')==SCHEMAS[name]:hash_returned=True
                        return result
                    caught=None
                    try:
                        # Delegating observer: it returns the actual complete
                        # production digest before the final real caller check.
                        with patch.object(base,'_digest',new=observing_digest):operation(check)
                    except BaseException as error:caught=error
                    self.assertIs(caught,marker)
                    self.assertGreaterEqual(calls,10 if site=='later' else 1)
                    if site=='after_hash':self.assertTrue(hash_returned)

    def test_first_parent_failure_preserves_original_object_for_all_public_apis(self):
        self.assert_origin_at('first')

    def test_later_parent_failure_preserves_original_object_for_all_public_apis(self):
        self.assert_origin_at('later')

    def test_real_final_output_hash_parent_failure_preserves_original_object(self):
        self.assert_origin_at('after_hash')

    def test_falsey_callable_is_forwarded_without_truthiness_substitution(self):
        for name,operation in self.operations().items():
            marker=OverflowError('falsey callable actual caller')
            class Caller:
                def __bool__(self):return False
                def __call__(self):raise marker
            with self.subTest(API=name):
                caught=None
                try:operation(Caller())
                except BaseException as error:caught=error
                self.assertIs(caught,marker)

    def test_complete_public_outputs_order_hashes_and_callback_counts_match_genuine_old_runner(self):
        for name,operation in self.operations().items():
            for callable_check in (False,True):
                values=[]
                for old in (True,False):
                    calls=0
                    def check():
                        nonlocal calls
                        calls+=1
                    runner=self.old_run if old else model._run
                    with patch.object(model,'_run',new=runner):
                        value=operation(check if callable_check else None)
                    # Complete output body and insertion order, no hash/field
                    # exclusion or expected output regenerated from new code.
                    values.append((json.dumps(value,ensure_ascii=False,allow_nan=False).encode(),
                        canonical_bytes(value),calls,list(value)))
                with self.subTest(API=name,callable_check=callable_check):self.assertEqual(values[0],values[1])

    def test_internal_capacity_and_bad_check_classification_match_old_runner(self):
        for name,operation in self.operations().items():
            for kind,bad in [('actual256bytecap',None),('false',False),('zero',0),('string','not callable')]:
                observed=[]
                for old in (True,False):
                    runner=self.old_run if old else model._run
                    try:
                        with patch.object(model,'_run',new=runner):
                            if kind=='actual256bytecap':
                                with patch.object(base,'MAX_JSON_BYTES',256):operation(bad)
                            else:operation(bad)
                    except BaseException as error:
                        observed.append((type(error),str(error),type(error.__cause__) if error.__cause__ else None))
                    else:self.fail('Internal capacity/noncallable input was accepted')
                with self.subTest(API=name,case=kind):
                    self.assertEqual(observed[0],observed[1])
                    self.assertIs(observed[1][0],model.HBA2CapacityBlocked if kind=='actual256bytecap' else ValueError)

    def test_import_operation_origin_capacity_still_uses_internal_normalization(self):
        native_import=builtins.__import__
        marker=ResearchInputCapacity('import operation capacity, not caller check')
        def opening(name,*args,**kwargs):
            if name=='numpy':raise marker
            return native_import(name,*args,**kwargs)
        with (patch.object(model.importlib.metadata,'version',side_effect=lambda name:model.PINS.get(name,'controlled-auxiliary')),
              patch.object(builtins,'__import__',side_effect=opening)):
            with self.assertRaises(model.HBA2CapacityBlocked) as caught:
                model.fit_hba2(self.training,recipe=self.recipe,expected_recipe_sha256=sha(self.recipe))
        self.assertIs(caught.exception.__cause__,marker)

    def test_caller_failure_after_import_error_keeps_identity(self):
        native_import=builtins.__import__
        for kind in WRAPPED:
            with self.subTest(caller=kind.__name__):
                marker=kind('caller after import failure')
                failed=False
                def opening(name,*args,**kwargs):
                    nonlocal failed
                    if name=='numpy':failed=True;raise ValueError('controlled binary ABI import failure')
                    return native_import(name,*args,**kwargs)
                def check():
                    if failed:raise marker
                caught=None
                try:
                    with (patch.object(model.importlib.metadata,'version',side_effect=lambda name:model.PINS.get(name,'controlled-auxiliary')),
                          patch.object(builtins,'__import__',side_effect=opening)):
                        model.fit_hba2(self.training,recipe=self.recipe,expected_recipe_sha256=sha(self.recipe),check=check)
                except BaseException as error:caught=error
                self.assertTrue(failed)
                self.assertIs(caught,marker)

    def test_caller_failure_after_real_numpy_return_prevents_later_imports(self):
        native_import=builtins.__import__
        try:native_import('numpy')
        except ImportError:
            if os.environ.get('GITHUB_ACTIONS','').lower()=='true':self.fail('CI requires real NumPy')
            self.skipTest('Actual NumPy import return is unavailable in this local runtime')
        for kind in WRAPPED:
            with self.subTest(caller=kind.__name__):
                marker=kind('caller after genuine NumPy import return')
                returned=False;later=[]
                def opening(name,*args,**kwargs):
                    nonlocal returned
                    if name in ('scipy','sklearn','sklearn.ensemble'):
                        later.append(name);raise AssertionError('Later import after caller abort')
                    value=native_import(name,*args,**kwargs)
                    if name=='numpy':returned=True
                    return value
                def check():
                    if returned:raise marker
                caught=None
                try:
                    with (patch.object(model.importlib.metadata,'version',side_effect=lambda name:model.PINS.get(name,'controlled-auxiliary')),
                          patch.object(builtins,'__import__',side_effect=opening)):
                        model.fit_hba2(self.training,recipe=self.recipe,expected_recipe_sha256=sha(self.recipe),check=check)
                except BaseException as error:caught=error
                self.assertTrue(returned)
                self.assertIs(caught,marker)
                self.assertEqual(later,[])


if __name__=='__main__':unittest.main()
