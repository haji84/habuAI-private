"""Synthetic source bindings: consistency never authenticates source/runner."""
import copy
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import codex_cycle_contract as cycle
from master_contracts import canonical_bytes, digest
from prospective_inputs import ProspectiveReadContext, READINESS_FIELDS
from test_g0_forecast_contract import base_ref
from test_hba1_feature_candidate import recipe

READY = '2026-10-01T00:00:00+09:00'
NIGHT = '2026-10-14'
FIT = '2026-10-13T18:00:00+09:00'
FORECAST = NIGHT+'T18:00:00+09:00'


class ConfigSourceFixture:
    def __init__(self, root, definition='f'*64):
        self.root = root
        for folder in ('src', 'scripts', 'schemas'):
            (root/folder).mkdir(exist_ok=True)
        for path in ('src/prospective_candidate_model.py', 'src/models/hba1_feature_candidate.py',
                     'scripts/synthetic.py', 'schemas/synthetic.json',
                     'requirements-analysis.txt', 'requirements-osm.txt'):
            if not (root/path).exists():
                base_ref(root, path, ('synthetic '+path+'\n').encode())
        if not (root/cycle.POLICY_PATH).exists():
            base_ref(root, cycle.POLICY_PATH, (ROOT/cycle.POLICY_PATH).read_bytes())
        self.config = dict(schema_version='habu-research-candidate-config-v2', mode='DEVELOPMENT_ONLY',
            candidate_ids=['uniform', 'HB-A0', 'HB-A1'], hba1_recipe=recipe(),
            feature_definition_sha256=definition)
        self.cycle = dict(schema_version=cycle.VERSION, kind='DEVELOPMENT_CONTRACT_ONLY',
            cycle_id='synthetic-fixed', base_main_sha='a'*40, frozen_at=READY,
            policy_ref=dict(path=cycle.POLICY_PATH,
                sha256=hashlib.sha256((root/cycle.POLICY_PATH).read_bytes()).hexdigest()), code_manifest=[])
        self.profile = dict(schema_version='habu-research-candidate-config-source-v1',
            kind='DEVELOPMENT_CANDIDATE_CONFIG_SOURCE', feature_definition_sha256=definition,
            candidate_config={}, cycle={}, code_availability=[], readiness=self.ready(), usable_at=READY)
        self.publish()

    @staticmethod
    def ready(stamp=READY):
        return dict.fromkeys(READINESS_FIELDS, stamp)

    def publish(self):
        self.profile.update(readiness=self.ready(), usable_at=READY)
        refs = [base_ref(self.root, path, (self.root/path).read_bytes()) for path in cycle.code_paths(self.root)]
        self.cycle['code_manifest'] = [{k:r[k] for k in ('path','sha256')} for r in refs]
        self.config['hba1_recipe'] and self.config['hba1_recipe'].update(implementation_sha256={
            path:hashlib.sha256((self.root/path).read_bytes()).hexdigest()
            for path in ('src/prospective_candidate_model.py','src/models/hba1_feature_candidate.py')})
        self.profile['code_availability'] = [dict(path=r['path'], size_bytes=r['size_bytes'],
            readiness=self.ready(), usable_at=READY) for r in refs]
        self.profile['cycle'] = dict(ref=base_ref(self.root, 'protocols/development/cycles/synthetic.json', canonical_bytes(self.cycle)),
            policy=dict(size_bytes=(self.root/cycle.POLICY_PATH).stat().st_size, readiness=self.ready(), usable_at=READY),
            readiness=self.ready(), usable_at=READY)
        self.publish_config()
        return self.profile_only()

    def publish_config(self, raw=None):
        self.profile['candidate_config'] = dict(ref=base_ref(self.root, 'config/synthetic-candidates.json',
            canonical_bytes(self.config) if raw is None else raw), config_sha256=digest(self.config),
            readiness=self.ready(), usable_at=READY)

    def profile_only(self, raw=None):
        self.ref = base_ref(self.root, 'config/synthetic-candidate-source.json',
            canonical_bytes(self.profile) if raw is None else raw)
        return self.ref


class CandidateConfigSourceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('research_candidate_config_source'), 'source-bound config loader missing')
        self.module = importlib.import_module('research_candidate_config_source')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture = ConfigSourceFixture(self.root)
        self.context = ProspectiveReadContext(300, 2*1024**3)

    def call(self, ref=None, **kwargs):
        return self.module.load_research_candidate_config(self.root, self.fixture.ref if ref is None else ref,
            heldout_night=NIGHT, fit_cutoff=FIT, forecast_cutoff=FORECAST,
            expected_feature_definition_sha256=kwargs.pop('expected_feature_definition_sha256','f'*64),
            context=self.context, **kwargs)

    def test_full_raw_code_closure_physical_and_canonical_hashes_are_distinct_and_accounted(self):
        f=self.fixture
        f.publish_config(json.dumps(f.config, indent=2).encode())
        f.profile_only()
        before=copy.deepcopy((f.ref,f.profile,f.config))
        value=self.call()
        receipt=value['receipt']
        self.assertEqual(value['config'], f.config)
        self.assertEqual(receipt['config_sha256'], digest(f.config))
        self.assertNotEqual(receipt['config_ref']['sha256'], receipt['config_sha256'])
        self.assertEqual(receipt['boundary'], FIT)
        self.assertEqual(receipt['actual_read_bytes'],self.context.bytes_read)
        self.assertEqual(receipt['validation_read_bytes'],2*sum(r['size_bytes'] for r in receipt['consumed_refs']))
        self.assertEqual(receipt['policy_canonical_sha256'],cycle.POLICY_DIGEST)
        self.assertEqual(receipt['receipt_sha256'],digest({k:v for k,v in receipt.items() if k!='receipt_sha256'}))
        for key in ('fit_authorized','selection_authorized','promotion_authorized','production_activation_authorized',
                    'loaded_bytecode_authenticated','trusted_campaign_authorized','trusted_pre_reveal_authorized'):
            self.assertIs(receipt[key],False)
        self.assertEqual(before,(f.ref,f.profile,f.config))

    def test_missing_readiness_unknown_fields_or_malformed_claims_are_invalid_not_data_gaps(self):
        for target in ('profile','config','cycle','policy','code'):
            original=copy.deepcopy(self.fixture.profile)
            node=self.fixture.profile if target=='profile' else self.fixture.profile['candidate_config'] if target=='config' else (
                self.fixture.profile['cycle'] if target=='cycle' else self.fixture.profile['cycle']['policy'] if target=='policy' else self.fixture.profile['code_availability'][0])
            node['readiness'].pop('audited_at')
            self.fixture.profile_only()
            with self.subTest(target=target),self.assertRaises(ValueError) as error: self.call()
            self.assertNotIsInstance(error.exception,self.module.CandidateConfigSourceBlocked)
            self.fixture.profile=original
        self.fixture.profile['trusted']=True
        self.fixture.profile_only()
        with self.assertRaises(ValueError): self.call()

    def test_late_each_readiness_equality_is_source_blocked_after_consistency_checks(self):
        for target in ('profile','config','cycle','policy','code'):
            for field in READINESS_FIELDS:
                f=self.fixture
                f.publish()
                node=f.profile if target=='profile' else f.profile['candidate_config'] if target=='config' else (
                    f.profile['cycle'] if target=='cycle' else f.profile['cycle']['policy'] if target=='policy' else f.profile['code_availability'][0])
                node['readiness'][field]=FIT
                node['usable_at']=FIT
                if target in ('code','policy'):
                    f.profile['cycle']['usable_at']=FIT
                    f.profile['candidate_config']['usable_at']=FIT
                f.profile['usable_at']=FIT
                f.profile_only()
                with self.subTest(target=target,field=field),self.assertRaises(self.module.CandidateConfigSourceBlocked): self.call()

    def test_bad_max_cannot_be_hidden_by_late_availability(self):
        self.fixture.profile['readiness']['audited_at']=FIT
        self.fixture.profile_only()
        with self.assertRaises(ValueError) as error:self.call()
        self.assertNotIsInstance(error.exception,self.module.CandidateConfigSourceBlocked)

    def test_omitted_extra_duplicate_code_or_wrong_recipe_bytes_are_invalid(self):
        f=self.fixture
        for mutation in ('omitted','extra','duplicate','recipe'):
            f.publish()
            if mutation=='omitted':f.profile['code_availability'].pop()
            elif mutation=='extra':f.profile['code_availability'].append(dict(f.profile['code_availability'][0],path='src/extra.py'))
            elif mutation=='duplicate':f.profile['code_availability'].append(copy.deepcopy(f.profile['code_availability'][0]))
            else:
                f.config['hba1_recipe']['implementation_sha256']['src/prospective_candidate_model.py']='e'*64
                f.publish_config()
            f.profile_only()
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.call()

    def test_reserved_namespaces_are_rejected_before_payload_open(self):
        for key,path in (('manifest','config/sealed/profile.json'),('config','config/ORIGINAL/a.json'),
                         ('cycle','protocols/development/current-cycle.json')):
            f=self.fixture;f.publish()
            ref=copy.deepcopy(f.ref)
            if key=='manifest':ref['path']=path
            else:
                f.profile['candidate_config' if key=='config' else 'cycle']['ref']['path']=path
                f.profile_only();ref=f.ref
            actual=Path.open
            def opening(target,*args,**kwargs):
                if target.as_posix().endswith(path):raise AssertionError('forbidden payload opened')
                return actual(target,*args,**kwargs)
            with self.subTest(key=key),patch.object(Path,'open',new=opening),self.assertRaises(ValueError):self.call(ref)

    def test_duplicate_json_keys_at_nested_depth_and_config_hash_or_policy_drift_reject(self):
        f=self.fixture
        raw=canonical_bytes(f.config).replace(b'"mode":"DEVELOPMENT_ONLY"',b'"mode":"CONFIRMATION","mode":"DEVELOPMENT_ONLY"')
        f.publish_config(raw);f.profile_only()
        with self.assertRaises(ValueError):self.call()
        f.publish();f.profile['candidate_config']['config_sha256']='e'*64;f.profile_only()
        with self.assertRaises(ValueError):self.call()
        f.publish();base_ref(self.root,cycle.POLICY_PATH,b'{}')
        f.cycle['policy_ref']['sha256']=hashlib.sha256(b'{}').hexdigest()
        f.publish()
        with self.assertRaises(ValueError):self.call()

    def test_code_bytes_mutation_and_membership_addition_at_rescan_are_rejected(self):
        import g0_forecast_contract as g0
        original=g0.G0ArtifactReader.rescan
        for mutation in ('bytes','membership'):
            self.fixture.publish()
            def rescan(reader):
                if mutation=='bytes':base_ref(self.root,'scripts/synthetic.py',b'late')
                original(reader)
                if mutation=='membership':base_ref(self.root,'src/late.py',b'late')
            with self.subTest(mutation=mutation),patch.object(g0.G0ArtifactReader,'rescan',new=rescan),self.assertRaises(ValueError):self.call()
            if (self.root/'src/late.py').exists():(self.root/'src/late.py').unlink()

    def test_missing_code_is_a_file_gap_and_malformed_readiness_is_not_hidden_by_it(self):
        target=self.root/'scripts/synthetic.py'
        target.unlink()
        with self.assertRaises(FileNotFoundError):self.call()
        self.fixture.profile['readiness'].pop('audited_at')
        self.fixture.profile_only()
        with self.assertRaises(ValueError) as error:self.call()
        self.assertNotIsInstance(error.exception,self.module.CandidateConfigSourceBlocked)

    def test_effective_readiness_includes_policy_and_code_in_both_config_and_cycle(self):
        stamp='2026-10-02T00:00:00+09:00'
        for source in ('policy','code'):
            self.fixture.publish()
            node=self.fixture.profile['cycle']['policy'] if source=='policy' else self.fixture.profile['code_availability'][0]
            node.update(readiness=self.fixture.ready(stamp),usable_at=stamp)
            for omitted in ('cycle','candidate_config','profile'):
                p=self.fixture.profile
                p['cycle']['usable_at']=stamp
                p['candidate_config']['usable_at']=stamp
                p['usable_at']=stamp
                (p if omitted=='profile' else p[omitted])['usable_at']=READY
                self.fixture.profile_only()
                with self.subTest(source=source,omitted=omitted),self.assertRaises(ValueError):self.call()

    def test_cycle_frozen_envelope_code_hash_and_strict_definition_reject(self):
        f=self.fixture
        for field,bad in (('schema_version','other'),('kind','LIVE'),('cycle_id','../unsafe'),('base_main_sha','a'*39)):
            original=f.cycle[field];f.cycle[field]=bad;f.publish()
            with self.subTest(field=field),self.assertRaises(ValueError):self.call()
            f.cycle[field]=original
        f.publish()
        with self.assertRaises(ValueError):self.call(expected_feature_definition_sha256='e'*64)
        f.cycle['frozen_at']='2026-10-02T00:00:00+09:00';f.publish()
        with self.assertRaises(ValueError):self.call()

    def test_reserved_or_control_runtime_code_path_rejects_before_any_payload(self):
        f=self.fixture
        for path in ('src/ORIGINAL/secret.py','src/control\nname.py'):
            f.publish()
            original=f.cycle['code_manifest'][0]['path']
            f.cycle['code_manifest'][0]['path']=path
            f.profile['code_availability'][0]['path']=path
            f.profile['cycle']['ref']=base_ref(self.root,'protocols/development/cycles/synthetic.json',canonical_bytes(f.cycle))
            f.profile_only()
            with self.subTest(path=path),self.assertRaises(ValueError) as error:self.call()
            self.assertNotIsInstance(error.exception,self.module.CandidateConfigSourceBlocked)
            f.cycle['code_manifest'][0]['path']=original

    def test_native_root_link_is_rejected_before_any_bytes_open(self):
        link=self.root.parent/(self.root.name+'-link')
        if os.name=='nt':
            result=subprocess.run(['cmd','/c','mklink','/J',str(link),str(self.root)],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
        else:link.symlink_to(self.root,target_is_directory=True)
        try:
            with patch.object(Path,'open',side_effect=AssertionError('root link reached byte open')),self.assertRaises(ValueError):
                self.module.load_research_candidate_config(link,self.fixture.ref,heldout_night=NIGHT,
                    fit_cutoff=FIT,forecast_cutoff=FORECAST,expected_feature_definition_sha256='f'*64,context=self.context)
        finally:
            self.assertEqual(link.absolute().parent,self.root.absolute().parent)
            if os.name=='nt':os.rmdir(link)
            else:link.unlink()

    def test_declared_closure_capacity_blocks_before_code_read_without_restricting_parent(self):
        f=self.fixture
        for entry in f.profile['code_availability']:entry['size_bytes']=4*1024**2
        f.profile_only()
        max_bytes,deadline=self.context.max_bytes,self.context.deadline
        actual=Path.open
        def opening(path,*args,**kwargs):
            if path.suffix=='.py':raise AssertionError('oversized declared closure reached code read')
            return actual(path,*args,**kwargs)
        with patch.object(Path,'open',new=opening),self.assertRaises(Exception) as error:self.call()
        self.assertIsInstance(error.exception,importlib.import_module('prospective_inputs').InputCapacityError)
        self.assertEqual((max_bytes,deadline),(self.context.max_bytes,self.context.deadline))

    def test_code_reference_resource_limit_is_capacity_blocked(self):
        import prospective_inputs as pi
        f=self.fixture
        f.cycle['code_manifest']=[dict(path=f'src/code-{i}.py',sha256='a'*64) for i in range(257)]
        f.profile['cycle']['ref']=base_ref(self.root,'protocols/development/cycles/synthetic.json',canonical_bytes(f.cycle))
        f.profile_only()
        with self.assertRaises(pi.InputCapacityError):self.call()

    def test_final_hash_expiry_and_caller_reference_mutation_cannot_escape(self):
        f=self.fixture
        original=self.module.digest
        def hashing(value):
            answer=original(value)
            if type(value) is dict and value.get('status')=='DECLARED_CONSISTENCY_ONLY':self.context.deadline=0
            return answer
        with patch.object(self.module,'digest',side_effect=hashing),self.assertRaises(TimeoutError):self.call()
        self.context=ProspectiveReadContext(300,2*1024**3)
        original_check=self.context.check
        def check():
            f.ref['sha256']='e'*64
            return original_check()
        original_ref=copy.deepcopy(f.ref)
        self.context.check=check
        result=self.call()
        self.assertEqual(result['receipt']['manifest_ref'],original_ref)


if __name__=='__main__':unittest.main()
