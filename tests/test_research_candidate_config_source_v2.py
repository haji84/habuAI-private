"""Synthetic guarded cfgv3 bytes: consistency, never actual fit/source authority."""
import copy
import hashlib
import importlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
import subprocess
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import codex_cycle_contract as cycle
import research_candidate_config_source as old
import prospective_inputs as pi
from g0_forecast_contract import G0ArtifactReader
from master_contracts import digest
from models import hba1_feature_candidate as a1,hba2_feature_candidate as a2
from test_research_candidate_config_source import ConfigSourceFixture,NIGHT,FIT,FORECAST
from test_g0_forecast_contract import base_ref
from test_hba2_feature_candidate import recipe as a2_recipe


class Source2Fixture(ConfigSourceFixture):
    def __init__(self,root):
        self.source2=False
        super().__init__(root)
        # Physical synthetic code payloads are declarations, not the Python
        # modules actually executing this fixture. Every byte is really read.
        for path in a2.CODE_PATHS|{'src/research_candidate_preparation_v3.py','src/research_candidate_config_source_v2.py'}:
            if not (root/path).exists():base_ref(root,path,('# synthetic '+path+'\n').encode())
        self.config.update(schema_version='habu-research-candidate-config-v3',
            candidate_ids=['uniform','HB-A1','HB-A2'],hba2_recipe=a2_recipe(a2))
        self.profile['schema_version']='habu-research-candidate-config-source-v2'
        self.source2=True;self.publish()

    def publish(self):
        if self.source2:
            recipe=self.config['hba2_recipe']
            for key,paths in (('implementation_sha256',a2.CODE_PATHS),('requirements_sha256',a2.REQUIREMENT_PATHS)):
                recipe[key]={path:hashlib.sha256((self.root/path).read_bytes()).hexdigest() for path in sorted(paths)}
        return super().publish()


class CandidateConfigSourceV2Tests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('research_candidate_config_source_v2'),
            'Explicit source-v2 loader is missing')
        self.api=importlib.import_module('research_candidate_config_source_v2')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.f=Source2Fixture(self.root);self.context=pi.ProspectiveReadContext(300,2*1024**3)

    def call(self,ref=None,context=None):
        return self.api.load_research_candidate_config_v2(self.root,self.f.ref if ref is None else ref,
            heldout_night=NIGHT,fit_cutoff=FIT,forecast_cutoff=FORECAST,
            expected_feature_definition_sha256='f'*64,context=self.context if context is None else context)

    def test_exact_explicit_profile_and_all_declared_maps_match_actual_raw_bytes(self):
        f=self.f;f.publish_config(json.dumps(f.config,indent=2).encode());f.profile_only()
        before=copy.deepcopy((f.ref,f.config,f.profile))
        result=self.call();receipt=result['receipt']
        self.assertEqual(set(result),{'config','receipt'});self.assertEqual(result['config'],f.config)
        self.assertEqual(receipt['schema_version'],'habu-research-candidate-config-source-v2')
        self.assertEqual(receipt['status'],'DECLARED_CONSISTENCY_ONLY')
        self.assertEqual(receipt['config_sha256'],digest(f.config))
        self.assertNotEqual(receipt['config_sha256'],receipt['config_ref']['sha256'])
        self.assertEqual(receipt['validation_read_bytes'],2*sum(r['size_bytes'] for r in receipt['consumed_refs']))
        self.assertEqual(receipt['actual_read_bytes'],self.context.bytes_read)
        for recipe,key in ((f.config['hba1_recipe'],'implementation_sha256'),(f.config['hba2_recipe'],'implementation_sha256'),(f.config['hba2_recipe'],'requirements_sha256')):
            for path,sha in recipe[key].items():self.assertEqual(receipt['code_sha256_by_path'][path],sha)
        self.assertEqual(receipt['receipt_sha256'],digest({k:v for k,v in receipt.items() if k!='receipt_sha256'}))
        self.assertEqual((f.ref,f.config,f.profile),before)
        self.assertTrue(all(value is False for key,value in receipt.items() if key.endswith(('_authorized','_authenticated'))))

    def test_each_rehashed_recipe_contradiction_rejects_before_consistent_lateness(self):
        cases=[('hba1_recipe','implementation_sha256',p) for p in self.f.config['hba1_recipe']['implementation_sha256']]
        cases += [('hba2_recipe','implementation_sha256',p) for p in a2.CODE_PATHS]
        cases += [('hba2_recipe','requirements_sha256',p) for p in a2.REQUIREMENT_PATHS]
        for recipe,key,path in cases:
            self.f.publish();self.context=pi.ProspectiveReadContext(300,2*1024**3)
            original=self.f.config[recipe][key][path]
            self.f.config[recipe][key][path]='e'*64
            self.assertNotEqual(original,self.f.config[recipe][key][path])
            self.f.publish_config();self.f.profile['readiness']['audited_at']=FIT;self.f.profile['usable_at']=FIT;self.f.profile_only()
            with self.subTest(recipe=recipe,key=key,path=path),self.assertRaises(ValueError) as caught:self.call()
            self.assertNotIsInstance(caught.exception,old.CandidateConfigSourceBlocked)
            self.f.config[recipe][key][path]=original

    def test_existing_context_preserves_actual_prior_charges_and_rejects_broader_or_exhausted(self):
        prior=base_ref(self.root,'config/prior.bin',b'prior')
        G0ArtifactReader(self.root,self.context).read(prior,parse=False)
        before=(self.context.deadline,self.context.max_bytes,self.context.bytes_read)
        result=self.call();receipt=result['receipt']
        self.assertEqual((self.context.deadline,self.context.max_bytes),before[:2])
        self.assertEqual(receipt['actual_read_bytes']-receipt['validation_read_bytes'],before[2])
        for context,error in ((pi.ProspectiveReadContext(300,2*1024**3+1),ValueError),(None,ValueError)):
            with self.subTest(context=type(context).__name__),patch.object(Path,'open',side_effect=AssertionError('broad/invalid context opened payload')),self.assertRaises(error):
                self.api.load_research_candidate_config_v2(self.root,self.f.ref,heldout_night=NIGHT,fit_cutoff=FIT,
                    forecast_cutoff=FORECAST,expected_feature_definition_sha256='f'*64,context=context)
        exhausted=pi.ProspectiveReadContext(300,5);G0ArtifactReader(self.root,exhausted).read(prior,parse=False)
        with patch.object(Path,'open',side_effect=AssertionError('exhausted context opened payload')),self.assertRaises(pi.InputCapacityError):self.call(context=exhausted)
        expired=pi.ProspectiveReadContext(.001,2*1024**3);time.sleep(.01)
        with patch.object(Path,'open',side_effect=AssertionError('expired context opened payload')),self.assertRaises(TimeoutError):self.call(context=expired)

    def test_consistent_late_profile_is_closure_barrier_and_old_loader_is_not_widened(self):
        self.f.profile['readiness']['audited_at']=FIT;self.f.profile['usable_at']=FIT;self.f.profile_only()
        with self.assertRaises(old.CandidateConfigSourceBlocked):self.call()
        self.assertGreater(self.context.bytes_read,0)
        self.assertEqual(self.context.bytes_read,2*sum(r['size_bytes'] for r in [self.f.ref,self.f.profile['candidate_config']['ref'],
            self.f.profile['cycle']['ref'],dict(self.f.cycle['policy_ref'],size_bytes=self.f.profile['cycle']['policy']['size_bytes']),
            *[dict(path=x['path'],size_bytes=x['size_bytes'],sha256=next(c['sha256'] for c in self.f.cycle['code_manifest'] if c['path']==x['path'])) for x in self.f.profile['code_availability']]]))
        with self.assertRaises(ValueError):old.load_research_candidate_config(self.root,self.f.ref,heldout_night=NIGHT,
            fit_cutoff=FIT,forecast_cutoff=FORECAST,expected_feature_definition_sha256='f'*64,
            context=pi.ProspectiveReadContext(300,2*1024**3))

    def test_no_old_loader_fitter_or_backend_probe_and_earlier_receipt_is_immutable_on_recheck(self):
        with (patch.object(old,'load_research_candidate_config',side_effect=AssertionError('old loader widened')),
                patch.object(a1,'fit_hba1',side_effect=AssertionError('A1 fitted')),
                patch.object(a2,'fit_hba2',side_effect=AssertionError('A2 fitted')),
                patch.object(a2,'_backend',side_effect=AssertionError('backend probed'))):
            result=self.call()
        before=copy.deepcopy(result);charged=self.context.bytes_read
        old.recheck_research_candidate_config(self.root,result['receipt'],context=self.context)
        self.assertGreater(self.context.bytes_read,charged);self.assertEqual(result,before)
        result['config']['candidate_ids'].reverse();self.assertEqual(self.f.config['candidate_ids'],['uniform','HB-A1','HB-A2'])

    def test_exact_profile_and_cfgv3_schema_never_fallback_or_admit_fourth_or_ablation(self):
        for mode in ('profile_v1','extra_profile','cfgv2','reversed','fourth','null_a1','null_a2','ablation','definition'):
            self.f.publish();config=copy.deepcopy(self.f.config);profile=copy.deepcopy(self.f.profile)
            if mode=='profile_v1':self.f.profile['schema_version']=old.VERSION
            elif mode=='extra_profile':self.f.profile['trusted']=True
            elif mode=='cfgv2':self.f.config['schema_version']='habu-research-candidate-config-v2'
            elif mode=='reversed':self.f.config['candidate_ids'].reverse()
            elif mode=='fourth':self.f.config['candidate_ids'].append('HB-A0')
            elif mode=='null_a1':self.f.config['hba1_recipe']=None
            elif mode=='null_a2':self.f.config['hba2_recipe']=None
            elif mode=='ablation':self.f.config['hba1_recipe']['feature_mask'][0]=False
            else:self.f.config['feature_definition_sha256']='e'*64
            self.f.publish_config();self.f.profile_only();self.context=pi.ProspectiveReadContext(300,2*1024**3)
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.call()
            self.f.config=config;self.f.profile=profile

    def test_omitted_extra_duplicate_helper_or_requirements_closure_cannot_be_hidden(self):
        for mode in ('omit_helper','omit_requirement','duplicate','extra_availability'):
            self.f.publish();self.context=pi.ProspectiveReadContext(300,2*1024**3)
            if mode.startswith('omit'):
                name='src/research_candidate_config_source_v2.py' if mode=='omit_helper' else 'requirements-osm.txt'
                self.f.cycle['code_manifest']=[r for r in self.f.cycle['code_manifest'] if r['path']!=name]
                self.f.profile['code_availability']=[r for r in self.f.profile['code_availability'] if r['path']!=name]
            elif mode=='duplicate':self.f.cycle['code_manifest'].append(copy.deepcopy(self.f.cycle['code_manifest'][0]))
            else:self.f.profile['code_availability'].append(dict(self.f.profile['code_availability'][0],path='src/extra.py'))
            self.f.profile['cycle']['ref']=base_ref(self.root,'protocols/development/cycles/synthetic.json',
                json.dumps(self.f.cycle,separators=(',',':'),sort_keys=True).encode())
            self.f.profile_only()
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.call()

    def test_every_readiness_level_and_field_strict_boundary_and_bad_max(self):
        for level in ('profile','config','cycle','policy','code'):
            for key in pi.READINESS_FIELDS:
                self.f.publish();self.context=pi.ProspectiveReadContext(300,2*1024**3)
                node=self.f.profile if level=='profile' else self.f.profile['candidate_config'] if level=='config' else (
                    self.f.profile['cycle'] if level=='cycle' else self.f.profile['cycle']['policy'] if level=='policy' else self.f.profile['code_availability'][-1])
                node['readiness'][key]=FIT;node['usable_at']=FIT
                if level in ('policy','code'):
                    self.f.profile['cycle']['usable_at']=FIT;self.f.profile['candidate_config']['usable_at']=FIT
                self.f.profile['usable_at']=FIT;self.f.profile_only()
                with self.subTest(level=level,key=key),self.assertRaises(old.CandidateConfigSourceBlocked):self.call()
        self.f.publish();self.f.profile['readiness']['audited_at']=FIT;self.f.profile_only()
        with self.assertRaises(ValueError) as caught:self.call(context=pi.ProspectiveReadContext(300,2*1024**3))
        self.assertNotIsInstance(caught.exception,old.CandidateConfigSourceBlocked)

    def test_original_parent_objects_at_real_first_copy_recipe_reader_and_final_seal(self):
        import research_candidate_preparation_v3 as pure
        for site in ('first','copy','recipe','reader','final'):
            for cls in (OverflowError,KeyError,pure.ResearchCapacityBlocked,pi.InputCapacityError,KeyboardInterrupt,SystemExit):
                original=cls('source2 actual parent');entered=[];context=pi.ProspectiveReadContext(300,2*1024**3)
                native=context.check
                def check():
                    native();match=site=='first'
                    frame=inspect.currentframe().f_back
                    while frame is not None and not match:
                        name=Path(frame.f_code.co_filename).name;function=frame.f_code.co_name
                        match=(site=='copy' and name=='research_candidate_preparation_v3.py' and function=='_copy' or
                               site=='recipe' and name=='hba2_feature_candidate.py' and function=='_recipe' or
                               site=='reader' and name=='g0_forecast_contract.py' and function=='read' or
                               site=='final' and name=='research_candidate_config_source_v2.py' and function=='load_research_candidate_config_v2'
                                   and type(frame.f_locals.get('receipt')) is dict and 'receipt_sha256' in frame.f_locals['receipt'])
                        frame=frame.f_back
                    if match:entered.append(True);raise original
                context.check=check;before=(context.deadline,context.max_bytes,context.check)
                with self.subTest(site=site,cls=cls),self.assertRaises(BaseException) as caught:self.call(context=context)
                self.assertIs(caught.exception,original);self.assertEqual(entered,[True])
                self.assertEqual((context.deadline,context.max_bytes,context.check),before)

    def test_falsey_first_origin_is_sticky_even_if_owned_helper_wraps_or_swallows(self):
        import research_candidate_preparation_v3 as pure
        class Falsey(pure.ResearchCapacityBlocked):
            def __bool__(self):return False
            def __eq__(self,other):raise AssertionError('origin is identity')
        for mode in ('swallow','wrap'):
            original=Falsey('first');armed=[];events=[];context=pi.ProspectiveReadContext(300,2*1024**3);native=context.check
            def parent():
                native()
                if armed:events.append(True);raise original
            def broken_copy(value,guard):
                armed.append(True)
                try:guard()
                except BaseException as error:
                    if mode=='wrap':raise pure.ResearchCapacityBlocked('child normalized') from error
                return value
            context.check=parent
            with self.subTest(mode=mode),patch.object(pure,'_copy',side_effect=broken_copy),self.assertRaises(BaseException) as caught:self.call(context=context)
            self.assertIs(caught.exception,original);self.assertEqual(events,[True])

    def test_internal_owned_capacity_and_declared_phase_limit_are_source_capacity(self):
        self.f.config['oversize']='x'*4097;self.f.publish_config();self.f.profile_only()
        with self.assertRaises(pi.InputCapacityError):self.call()
        self.f.config.pop('oversize');self.f.publish()
        for entry in self.f.profile['code_availability']:entry['size_bytes']=4*1024**2
        self.f.profile_only();context=pi.ProspectiveReadContext(300,2*1024**3);before=(context.deadline,context.max_bytes)
        actual=Path.open
        def opening(path,*args,**kwargs):
            if path.suffix=='.py':raise AssertionError('declared oversized closure opened code')
            return actual(path,*args,**kwargs)
        with patch.object(Path,'open',new=opening),self.assertRaises(pi.InputCapacityError):self.call(context=context)
        self.assertEqual((context.deadline,context.max_bytes),before)

    def test_actual_shared_phase_charges_are_counted_without_reset_or_global_restrict(self):
        # The caller's actual read during an in-flight phase is not fictitious
        # accounting. It exceeds16MiB but remains below the existing2GiB global.
        raw=b'x'*(16*1024**2+1);prior=base_ref(self.root,'config/inflight-prior.bin',raw)
        context=pi.ProspectiveReadContext(300,2*1024**3);native=context.check;entered=[]
        def check():
            native()
            if not entered:
                entered.append(True);G0ArtifactReader(self.root,context).read(prior,parse=False)
        context.check=check;before=(context.deadline,context.max_bytes,context.check)
        with self.assertRaises(pi.InputCapacityError):self.call(context=context)
        self.assertEqual(context.bytes_read,len(raw));self.assertEqual((context.deadline,context.max_bytes,context.check),before)

    def test_final_actual_expiry_and_late_original_bytes_or_membership_publish_nothing(self):
        for mode in ('expiry','bytes','membership'):
            self.f.publish();context=pi.ProspectiveReadContext(1 if mode=='expiry' else 300,2*1024**3);native=context.check;entered=[]
            original=(self.root/'requirements-osm.txt').read_bytes()
            def check():
                native();frame=inspect.currentframe().f_back
                while frame is not None and not entered:
                    name=Path(frame.f_code.co_filename).name;function=frame.f_code.co_name
                    if mode=='expiry' and name=='research_candidate_config_source_v2.py' and function=='load_research_candidate_config_v2':
                        receipt=frame.f_locals.get('receipt')
                        if type(receipt) is dict and 'receipt_sha256' in receipt:entered.append(True);time.sleep(1.05)
                    elif mode!='expiry' and name=='g0_forecast_contract.py' and function=='rescan':
                        entered.append(True)
                        if mode=='bytes':(self.root/'requirements-osm.txt').write_bytes(original+b'changed')
                        else:base_ref(self.root,'src/late-code.py',b'# late\n')
                    frame=frame.f_back
                native()
            context.check=check
            with self.subTest(mode=mode),self.assertRaises(TimeoutError if mode=='expiry' else ValueError):self.call(context=context)
            self.assertEqual(entered,[True]);(self.root/'requirements-osm.txt').write_bytes(original)
            if (self.root/'src/late-code.py').exists():(self.root/'src/late-code.py').unlink()

    def test_actual_native_junction_or_symlink_is_rejected_before_external_payload_open(self):
        with tempfile.TemporaryDirectory() as outside:
            target=Path(outside);(target/'config.json').write_text('{}',encoding='utf8');link=self.root/'config/link'
            if os.name=='nt':subprocess.run(['cmd','/c','mklink','/J',str(link),str(target)],check=True,capture_output=True)
            else:link.symlink_to(target,target_is_directory=True)
            try:
                self.f.profile['candidate_config']['ref'].update(path='config/link/config.json',sha256=hashlib.sha256(b'{}').hexdigest(),size_bytes=2)
                self.f.profile_only();actual=Path.open;outside_opens=[]
                def opening(path,*args,**kwargs):
                    if 'link' in path.parts or path.is_relative_to(target):outside_opens.append(str(path));raise AssertionError('external payload opened')
                    return actual(path,*args,**kwargs)
                with patch.object(Path,'open',new=opening),self.assertRaises(ValueError):self.call()
                self.assertEqual(outside_opens,[])
            finally:
                if os.name=='nt':os.rmdir(link)
                else:link.unlink()

    def test_each_declared_file_and_reference_cap_precedes_its_payload(self):
        for mode in ('profile','config','cycle','policy','code','references'):
            self.f.publish();ref=copy.deepcopy(self.f.ref);self.context=pi.ProspectiveReadContext(300,2*1024**3)
            if mode=='profile':ref['size_bytes']=256*1024+1
            elif mode=='config':self.f.profile['candidate_config']['ref']['size_bytes']=64*1024+1
            elif mode=='cycle':self.f.profile['cycle']['ref']['size_bytes']=4*1024**2+1
            elif mode=='policy':self.f.profile['cycle']['policy']['size_bytes']=4*1024**2+1
            elif mode=='code':self.f.profile['code_availability'][-1]['size_bytes']=4*1024**2+1
            else:
                self.f.cycle['code_manifest']=[dict(path=f'src/code-{n}.py',sha256='a'*64) for n in range(257)]
                self.f.profile['cycle']['ref']=base_ref(self.root,'protocols/development/cycles/synthetic.json',json.dumps(self.f.cycle).encode())
            if mode!='profile':self.f.profile_only();ref=self.f.ref
            with self.subTest(mode=mode),self.assertRaises(pi.InputCapacityError):self.call(ref)

    def test_nested_duplicate_json_and_nonfinite_and_forged_canonical_hash_are_invalid(self):
        for mode in ('duplicate','nonfinite','canonical'):
            self.f.publish();raw=json.dumps(self.f.config,separators=(',',':')).encode()
            if mode=='duplicate':raw=raw.replace(b'"random_state":0',b'"random_state":0,"random_state":0')
            elif mode=='nonfinite':raw=raw.replace(b'"learning_rate":0.1',b'"learning_rate":NaN')
            self.f.publish_config(raw)
            if mode=='canonical':self.f.profile['candidate_config']['config_sha256']='e'*64
            self.f.profile_only();self.context=pi.ProspectiveReadContext(300,2*1024**3)
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.call()

    def test_complete_actual_native_runtime_closure_is_physically_read_and_rescanned(self):
        # Native current software bytes with explicitly synthetic declared
        # dates. This is not historical availability, issuer or loaded-code
        # attestation, and no backend/fitter/data-source payload is invoked.
        paths=cycle.code_paths(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in paths:
                base_ref(root,name,(ROOT/name).read_bytes())
            base_ref(root,cycle.POLICY_PATH,(ROOT/cycle.POLICY_PATH).read_bytes())
            f=Source2Fixture(root)
            for name in ('scripts/synthetic.py','schemas/synthetic.json'):
                if name not in paths:(root/name).unlink()
            f.publish();context=pi.ProspectiveReadContext(300,2*1024**3)
            result=self.api.load_research_candidate_config_v2(root,f.ref,heldout_night=NIGHT,fit_cutoff=FIT,
                forecast_cutoff=FORECAST,expected_feature_definition_sha256='f'*64,context=context)
            receipt=result['receipt'];self.assertEqual(set(receipt['code_sha256_by_path']),set(paths))
            self.assertEqual(receipt['validation_read_bytes'],2*sum(r['size_bytes'] for r in receipt['consumed_refs']))
            for name in paths:self.assertEqual(receipt['code_sha256_by_path'][name],hashlib.sha256((ROOT/name).read_bytes()).hexdigest())
            self.assertIs(receipt['loaded_bytecode_authenticated'],False);self.assertIs(receipt['python_native_runtime_authenticated'],False)

    def test_real_caller_read_after_receipt_hash_cannot_return_stale_execution_counters(self):
        prior=base_ref(self.root,'config/final-prior.bin',b'x')
        context=pi.ProspectiveReadContext(300,2*1024**3);native=context.check;entered=[];before=(context.deadline,context.max_bytes)
        def check():
            native();frame=inspect.currentframe().f_back
            while frame is not None and not entered:
                if Path(frame.f_code.co_filename).name=='research_candidate_config_source_v2.py' and frame.f_code.co_name=='load_research_candidate_config_v2':
                    receipt=frame.f_locals.get('receipt')
                    if type(receipt) is dict and 'receipt_sha256' in receipt:
                        entered.append(True);G0ArtifactReader(self.root,context).read(prior,parse=False)
                frame=frame.f_back
        context.check=check;result=None
        try:result=self.call(context=context)
        except ValueError as error:self.assertIn('ledger',str(error).lower())
        if result is not None:self.assertEqual(result['receipt']['actual_read_bytes'],context.bytes_read,
            'A successful source receipt may not omit real bytes charged at the final caller guard')
        self.assertEqual(entered,[True]);self.assertEqual((context.deadline,context.max_bytes),before)


if __name__=='__main__':unittest.main()
