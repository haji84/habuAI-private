import hashlib
import json
import copy
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from private_pdca_runner import run_private, PrivateRunError
from private_pdca_intake import intake
import private_pdca_intake as intake_module
import private_pdca_runner as runner_module


class B1HelperTests(unittest.TestCase):
    def test_b1_claim_temp_fsync_late_orphan_blocks_active(self):
        scope,attempt,source,binding=self.binding_fixture()
        base=self.store/'private_pdca_runs'/'v2'/'scopes'/scope
        native=os.fsync;calls=[];orphan=base/'attempts'/('c'*64)
        def fsync_then_orphan(fd):
            native(fd);calls.append(fd)
            if len(calls)==3:
                orphan.mkdir();(orphan/'binding.json').write_bytes(b'SYNTHETIC_LATE_ORPHAN')
        with patch.object(os,'fsync',fsync_then_orphan),self.assertRaises(PrivateRunError):
            runner_module._b1_claim_files(self.store,scope,attempt,source,binding,'r1',self.budget)
        self.assertEqual(len(calls),3)
        self.assertFalse((base/'active.json').exists())
        self.assertFalse((base/'attempts'/attempt/'claim.json').exists())
        self.assertTrue((base/'source.json').is_file())
        self.assertTrue((base/'attempts'/attempt/'binding.json').is_file())
        self.assertEqual((orphan/'binding.json').read_bytes(),b'SYNTHETIC_LATE_ORPHAN')
        self.assertEqual(list((base/'attempts'/attempt).glob('.b1-claim-*')),[])

    def report_fixture(self, *, bool_size=False):
        contracts,_=runner_module._b1_modules(self.budget)
        directory=self.root/'report';directory.mkdir()
        data=directory/'snapshot'/'data'/'a';data.parent.mkdir(parents=True);data.write_bytes(b'x')
        ref=dict(sha256=hashlib.sha256(b'x').hexdigest(),size_bytes=1)
        identity=dict(night='2000-01-01',inputs={'data/a':ref},code='1'*64,policy={},runtime={},inventory_error=None)
        runid=contracts.digest(identity)
        def save(name,value):
            path=directory/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(contracts.canonical_bytes(value)+b'\n')
            return hashlib.sha256(path.read_bytes()).hexdigest()
        outputs={}
        evidence=dict(schema_version='1.0',entries=[dict(path='data/a',sha256=ref['sha256'],size_bytes=True if bool_size else 1)],
                      missing=['SYNTHETIC_ONLY'],input_snapshot_sha256=contracts.digest(identity['inputs']))
        outputs['evidence_manifest.json']=save('evidence_manifest.json',evidence)
        stages=[]
        for name in contracts.STAGE_NAMES:
            stage=contracts.stage(name,'BLOCKED','SYNTHETIC_MISSING_INPUT',blocker_kind='DATA_BLOCKED');stages.append(stage)
            relative='stages/'+name+'.json';outputs[relative]=save(relative,dict(stage=stage,payload=None))
        final=dict(schema_version='1.0',run_id=runid,outputs=dict(outputs),elapsed_seconds=.25,round_number=0,
                   created_at='2000-01-01T00:00:00+00:00',result_sha256=None,active_stage=None,active_since=None,attempt_deadline=None)
        outputs['finalization_checkpoint.json']=save('finalization_checkpoint.json',final)
        result=dict(schema_version='1.0',run_id=runid,operational_night='2000-01-01',code_sha256=identity['code'],
                    input_manifest_sha256=contracts.digest(evidence),policy_sha256=contracts.digest(identity['policy']),
                    runtime={},stages=stages,overall_status='BLOCKED',completed=False,checkpoint_sha256=contracts.digest(final),
                    budget=dict(limit_seconds=300,elapsed_seconds=.25,round_number=0,max_rounds=2,max_candidates=3))
        result_sha=save('run_manifest.json',result)
        cp=dict(final,outputs=outputs,elapsed_seconds=.3,result_sha256=result_sha)
        save('checkpoint.json',cp);save('checkpoint.sha256.json',dict(sha256=contracts.digest(cp)))
        return directory,identity,result

    def test_b1_full_native_chain_shape_and_unknown_artifact(self):
        directory,identity,result=self.report_fixture()
        value=runner_module._b1_report(directory,identity,self.budget)
        self.assertEqual(value['state'],'NATIVE_CHAIN_ONLY_B2_NOT_INSTALLED')
        self.assertEqual(value['result'],result)
        (directory/'uncommitted.txt').write_bytes(b'x')
        with self.assertRaises(PrivateRunError):runner_module._b1_report(directory,identity,self.budget)

    def test_b1_report_cap_preserves_all_or_none(self):
        directory,identity,result=self.report_fixture()
        with patch.object(runner_module,'B1_MAX_REPORT',20),self.assertRaises(PrivateRunError):
            runner_module._b1_report(directory,identity,self.budget)

    def test_b1_native_evidence_size_bool_is_not_integer(self):
        directory,identity,result=self.report_fixture(bool_size=True)
        with self.assertRaises(PrivateRunError):runner_module._b1_report(directory,identity,self.budget)

    def test_b1_checkpoint_unrepresentable_elapsed_is_typed_rejection(self):
        directory,identity,result=self.report_fixture()
        contracts,_=runner_module._b1_modules(self.budget)
        cp=json.loads((directory/'checkpoint.json').read_bytes());cp['elapsed_seconds']=10**400
        (directory/'checkpoint.json').write_bytes(contracts.canonical_bytes(cp)+b'\n')
        (directory/'checkpoint.sha256.json').write_bytes(contracts.canonical_bytes({'sha256':contracts.digest(cp)})+b'\n')
        with self.assertRaises(PrivateRunError):runner_module._b1_report(directory,identity,self.budget)

    def test_b1_view_failed_read_charges_parent_plus_one(self):
        with patch.object(intake_module,'MAX_READ_BYTES',5),self.assertRaises(PrivateRunError):
            runner_module._b1_view(self.view,self.budget)
        self.assertEqual(self.budget.bytes_read,6)

    def test_b1_real_deadline_is_shared_with_file_open(self):
        actual=Path.open;observed=[]
        def delayed(path,*a,**k):
            f=actual(path,*a,**k)
            if path==self.view/'data'/'synthetic.txt':
                observed.append(path);time.sleep(.35)
            return f
        budget=intake_module._ReadBudget(.3,error_type=PrivateRunError)
        with patch.object(Path,'open',delayed),self.assertRaises(PrivateRunError):
            runner_module._b1_view(self.view,budget)
        self.assertEqual(observed,[self.view/'data'/'synthetic.txt'])

    def test_b1_physical_cycle_binding_rejects_omitted_new_helper(self):
        for name in ('src','scripts','schemas'):(self.view/name).mkdir()
        (self.view/'src'/'synthetic.py').write_bytes(b'SYNTHETIC_ONLY')
        for name in ('requirements-analysis.txt','requirements-osm.txt'):(self.view/name).write_bytes(b'')
        contracts,_=runner_module._b1_modules(self.budget)
        code=runner_module._b1_view(self.view,self.budget,code=True)
        policy=self.view/'protocols'/'development'/'g0-policy-v1.json';policy.parent.mkdir(parents=True)
        original=(Path(__file__).resolve().parents[1]/'protocols'/'development'/'g0-policy-v1.json').read_bytes()
        policy.write_bytes(original)
        pref=dict(path='protocols/development/g0-policy-v1.json',sha256=hashlib.sha256(original).hexdigest())
        manifest=dict(schema_version='habu-codex-cycle-v1',kind='DEVELOPMENT_CONTRACT_ONLY',cycle_id='SYNTHETIC',base_main_sha='1'*40,
                      frozen_at='2000-01-01T00:00:00+00:00',policy_ref=pref,code_manifest=[dict(path=p,sha256=v['sha256']) for p,v in code.items()])
        raw=contracts.canonical_bytes(manifest)+b'\n'
        path=self.view/'protocols'/'development'/'cycles'/'synthetic.json';path.parent.mkdir();path.write_bytes(raw)
        pointer=policy.parent/'current-cycle.json';pointer.write_bytes(contracts.canonical_bytes(dict(path='protocols/development/cycles/synthetic.json',sha256=hashlib.sha256(raw).hexdigest()))+b'\n')
        value=runner_module._b1_cycle(self.view,code,self.budget)
        self.assertEqual(value['manifest']['sha256'],hashlib.sha256(raw).hexdigest())
        malformed=dict(manifest,frozen_at=[])
        changed_raw=contracts.canonical_bytes(malformed)+b'\n';path.write_bytes(changed_raw)
        pointer.write_bytes(contracts.canonical_bytes(dict(path='protocols/development/cycles/synthetic.json',sha256=hashlib.sha256(changed_raw).hexdigest()))+b'\n')
        with self.assertRaises(PrivateRunError):runner_module._b1_cycle(self.view,code,self.budget)
        path.write_bytes(raw)
        pointer.write_bytes(contracts.canonical_bytes(dict(path='protocols/development/cycles/synthetic.json',sha256=hashlib.sha256(raw).hexdigest()))+b'\n')
        (self.view/'src'/'extra.py').write_bytes(b'')
        changed=runner_module._b1_view(self.view,self.budget,code=True)
        with self.assertRaises(PrivateRunError):runner_module._b1_cycle(self.view,changed,self.budget)

    def test_b1_node_cap_precedes_decoder(self):
        with patch.object(runner_module,'B1_MAX_NODES',2),patch.object(json,'loads',side_effect=AssertionError('decoder must not allocate')):
            with self.assertRaises(PrivateRunError):runner_module._b1_document(b'{"x":[1,2]}',self.budget)

    def test_b1_old_terminal_claims_cannot_mint_b2_evidence(self):
        base=self.store/'private_pdca_runs'/'v2'/'scopes'/('a'*64)
        directory=base/'attempts'/('b'*64);directory.mkdir(parents=True)
        for name in ('source.json',):(base/name).write_bytes(b'{}')
        for name in ('binding.json','claim.json'):(directory/name).write_bytes(b'{}')
        # A class-like label/Boolean is not real supervisor evidence.
        (directory/'terminal.json').write_bytes(b'{"private_status":"BLOCKED","owned":true,"origin":"TimeoutError"}')
        with self.assertRaisesRegex(PrivateRunError,'B2_REQUIRED'):
            runner_module._b1_history(base,self.budget)

    def test_b1_shape_rejects_bool_ref_and_portable_alias(self):
        scope,attempt,source,binding=self.binding_fixture()
        for field,value in (('size_bytes',True),('path','receipts./synthetic.json')):
            changed=copy.deepcopy(source);changed['intake_receipt_ref'][field]=value
            with self.subTest(field=field),self.assertRaises(PrivateRunError):
                runner_module._b1_binding_shape(changed,binding,self.budget)

    def test_b1_legacy_receipt_blocks_before_new_metadata(self):
        scope,attempt,source,binding=self.binding_fixture()
        oldid=hashlib.sha256(('2000-01-01:'+source['source_receipt_id']).encode()).hexdigest()
        old=self.store/'private_pdca_runs'/(oldid+'.json');old.parent.mkdir();old.write_bytes(b'SYNTHETIC_LEGACY')
        with self.assertRaises(PrivateRunError):
            runner_module._b1_claim_files(self.store,scope,attempt,source,binding,'r1',self.budget)
        self.assertEqual(old.read_bytes(),b'SYNTHETIC_LEGACY')
        self.assertFalse((self.store/'private_pdca_runs'/'v2').exists())

    def test_b1_late_orphan_before_active_blocks_reservation(self):
        scope,attempt,source,binding=self.binding_fixture()
        native=os.link
        def orphan(src,dest):
            result=native(src,dest)
            if Path(dest).name=='binding.json':
                other=Path(dest).parent.parent/('c'*64);other.mkdir();(other/'binding.json').write_bytes(b'{}')
            return result
        with patch.object(os,'link',orphan),self.assertRaises(PrivateRunError):
            runner_module._b1_claim_files(self.store,scope,attempt,source,binding,'r1',self.budget)
        self.assertFalse((self.store/'private_pdca_runs'/'v2'/'scopes'/scope/'active.json').exists())

    def binding_fixture(self, revision='r1'):
        def digest(value):
            return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
        def framed(domain,value):
            return hashlib.sha256(domain.encode()+b'\0'+json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
        archive=self.store/'synthetic.txt';archive.write_bytes(b'SYNTHETIC_ONLY')
        h=hashlib.sha256(archive.read_bytes()).hexdigest()
        rows=[dict(type='log',sha256=h,size_bytes=14,private_archive=str(archive))]
        rid=hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        source=dict(schema='habu-private-pdca-source-scope-v2',night='2000-01-01',
                    intake_receipt_ref=dict(path='receipts/synthetic.json',sha256='1'*64,size_bytes=2),
                    source_receipt_id=rid,sources=rows,
                    verified_inbox=[dict(type='log',path='incoming/private_pdca/'+h+'.txt',sha256=h,size_bytes=14)])
        scope=framed('habu-private-pdca-source-scope-v2',source)
        code={'src/synthetic.py':dict(sha256=h,size_bytes=14)}
        identity=dict(night='2000-01-01',inputs={},code=digest({'src/synthetic.py':h}),policy={},runtime={},inventory_error=None)
        binding=dict(schema='habu-private-pdca-binding-v2',scope_id=scope,revision=revision,
                     selected_code_root=str(self.view),workspace_root=str(self.view),tool_input_view={},workspace_input_view={},
                     complete_code_view=code,complete_code_sha256=digest({'src/synthetic.py':h}),protocol_policy_refs=[],
                     cycle_refs={k:dict(path='protocols/'+k+'.json',sha256='2'*64,size_bytes=2) for k in ('pointer','manifest','policy')},
                     master_identity=identity,master_run_id=digest(identity),execution_policy=dict(runner_module.B1_EXECUTION_POLICY))
        bh=framed('habu-private-pdca-binding-v2',binding)
        attempt=framed('habu-private-pdca-attempt-v2',dict(scope_id=scope,revision=revision,binding_sha256=bh))
        return scope,attempt,source,binding

    def test_b1_real_claim_is_exclusive_and_not_completed(self):
        scope,attempt,source,binding=self.binding_fixture()
        value=runner_module._b1_claim_files(self.store,scope,attempt,source,binding,'r1',self.budget)
        self.assertEqual(value['state'],'RESERVED_ONLY_B2_NOT_INSTALLED')
        base=Path(value['base'])
        self.assertEqual((base/'active.json').read_bytes(),(base/'attempts'/attempt/'claim.json').read_bytes())
        self.assertFalse((base/'attempts'/attempt/'terminal.json').exists())
        with self.assertRaises(PrivateRunError):
            runner_module._b1_claim_files(self.store,scope,attempt,source,binding,'r1',self.budget)

    def test_b1_losing_race_keeps_shared_source_binding(self):
        scope,attempt,source,binding=self.binding_fixture()
        native=os.link;published=[]
        def racing(src,dest):
            dest=Path(dest)
            if dest.name=='active.json':
                dest.write_bytes(b'SYNTHETIC_OTHER_CLAIM')
            result=native(src,dest)
            if dest.name in ('source.json','binding.json'):
                published.append((dest,dest.read_bytes(),dest.stat().st_ino))
            return result
        with patch.object(os,'link',racing),self.assertRaises(PrivateRunError):
            runner_module._b1_claim_files(self.store,scope,attempt,source,binding,'r1',self.budget)
        self.assertEqual(len(published),2)
        for path,raw,inode in published:
            self.assertEqual(path.read_bytes(),raw);self.assertEqual(path.stat().st_ino,inode)

    def test_b1_failure_after_publication_keeps_primary_and_shared_files(self):
        scope,attempt,source,binding=self.binding_fixture()
        native=os.link;marker=KeyboardInterrupt('SYNTHETIC_FIRST')
        def cancel(src,dest):
            result=native(src,dest)
            if Path(dest).name=='binding.json':
                raise marker
            return result
        with patch.object(os,'link',cancel),self.assertRaises(KeyboardInterrupt) as caught:
            runner_module._b1_claim_files(self.store,scope,attempt,source,binding,'r1',self.budget)
        self.assertIs(caught.exception,marker)
        base=self.store/'private_pdca_runs'/'v2'/'scopes'/scope
        self.assertTrue((base/'source.json').is_file())
        self.assertTrue((base/'attempts'/attempt/'binding.json').is_file())
        with self.assertRaises(PrivateRunError):runner_module._b1_history(base,self.budget)

    def test_b1_zero_growth_charges_failed_byte(self):
        path=self.view/'data'/'empty';path.write_bytes(b'')
        actual=Path.open
        class Stream:
            def __init__(self,stream):self.stream=stream
            def __enter__(self):return self
            def __exit__(self,*args):return self.stream.__exit__(*args)
            def fileno(self):return self.stream.fileno()
            def read(wrapped,n):
                with actual(path,'ab') as f:f.write(b'x')
                return wrapped.stream.read(n)
        def opening(p,*a,**k):
            f=actual(p,*a,**k)
            return Stream(f) if p==path and a==('rb',) else f
        with patch.object(Path,'open',opening),self.assertRaises(PrivateRunError):
            runner_module._b1_raw(path,10,self.budget)
        self.assertEqual(self.budget.bytes_read,1)

    def test_b1_entry_limit_includes_ignored_cache(self):
        (self.view/'data'/'__pycache__').mkdir()
        with patch.object(runner_module,'B1_MAX_ENTRIES',1),self.assertRaises(PrivateRunError):
            runner_module._b1_view(self.view,self.budget)

    def test_b1_code_membership_keeps_cache_named_python_and_requirements(self):
        for name in ('src','scripts','schemas'):(self.view/name).mkdir()
        cache=self.view/'src'/'__pycache__';cache.mkdir();(cache/'extra.py').write_bytes(b'')
        for name in ('requirements-analysis.txt','requirements-osm.txt'):(self.view/name).write_bytes(b'')
        code=runner_module._b1_view(self.view,self.budget,code=True)
        self.assertEqual(set(code),{'src/__pycache__/extra.py','requirements-analysis.txt','requirements-osm.txt'})
        (self.view/'schemas'/'new.json').write_bytes(b'{}')
        self.assertNotEqual(code,runner_module._b1_view(self.view,self.budget,code=True))

    def test_b1_metadata_cap_bool_and_revision_rejection_before_write(self):
        scope,attempt,source,binding=self.binding_fixture()
        binding['execution_policy']['max_rounds']=2.0
        with self.assertRaises(PrivateRunError):
            runner_module._b1_claim_files(self.store,scope,attempt,source,binding,'r1',self.budget)
        self.assertFalse((self.store/'private_pdca_runs').exists())
        with patch.object(runner_module,'B1_MAX_JSON',10),self.assertRaises(PrivateRunError):
            runner_module._b1_canonical({'x':'large'*20},self.budget)

    def test_b1_platform_capability_is_real(self):
        if os.name=='posix':self.skipTest('Windows-only absence control; actual POSIX parity separate')
        with self.assertRaisesRegex(PrivateRunError,'NOT_STARTED_CAPABILITY'):
            runner_module._b1_modules(self.budget,engine=True)

    @unittest.skipUnless(os.name=='posix','Actual POSIX master import required; no fcntl substitute')
    def test_b1_actual_installed_master_identity_parity(self):
        contracts,_,master=runner_module._b1_modules(self.budget,engine=True)
        code={'src/synthetic.py':dict(sha256='1'*64,size_bytes=1),'schemas/s.json':dict(sha256='2'*64,size_bytes=2)}
        value,runid=runner_module._b1_identity('2000-01-01',{},code,self.budget)
        expected=master._scientific_identity('2000-01-01',{},contracts.digest({'src/synthetic.py':'1'*64}),master._runtime(),None)
        self.assertEqual(contracts.canonical_bytes(value),contracts.canonical_bytes(expected))
        self.assertEqual(runid,contracts.digest(expected))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = self.root/'store'
        self.store.mkdir(mode=0o700)
        self.view = self.root/'view'
        self.view.mkdir()
        (self.view/'data').mkdir()
        (self.view/'data'/'synthetic.txt').write_bytes(b'SYNTHETIC_ONLY')
        self.budget = intake_module._ReadBudget(30, error_type=PrivateRunError)

    def test_b1_hashes_real_empty_and_nonempty_inventory_bytes(self):
        (self.view/'data'/'empty.txt').write_bytes(b'')
        result = runner_module._b1_view(self.view, self.budget)
        self.assertEqual(result['data/empty.txt'], {'sha256':hashlib.sha256(b'').hexdigest(),'size_bytes':0})
        self.assertEqual(result['data/synthetic.txt']['sha256'], hashlib.sha256(b'SYNTHETIC_ONLY').hexdigest())
        self.assertEqual(self.budget.bytes_read, len(b'SYNTHETIC_ONLY'))

    def test_b1_view_file_cap_fails_all_or_none(self):
        (self.view/'data'/'second.txt').write_bytes(b'x')
        with patch.object(runner_module, 'B1_MAX_FILES', 1, create=True):
            with self.assertRaises(PrivateRunError):
                runner_module._b1_view(self.view, self.budget)

    def test_b1_document_rejects_duplicate_nonfinite_and_depth(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'['*33+b'0'+b']'*33):
            with self.subTest(raw=raw[:15]), self.assertRaises(PrivateRunError):
                runner_module._b1_document(raw, self.budget)

    def test_b1_published_binding_survives_failed_active_claim(self):
        scope='a'*64; attempt='b'*64
        base=self.store/'private_pdca_runs'/'v2'/'scopes'/scope
        base.mkdir(parents=True)
        winner=base/'active.json';winner.write_bytes(b'SYNTHETIC_OTHER_CLAIM')
        with self.assertRaises(PrivateRunError):
            runner_module._b1_claim_files(self.store,scope,attempt,{'x':1},{'y':2},'r1',self.budget)
        self.assertEqual(winner.read_bytes(),b'SYNTHETIC_OTHER_CLAIM')

    def test_b1_absent_active_does_not_allow_orphan_revision(self):
        base=self.store/'private_pdca_runs'/'v2'/'scopes'/('a'*64)
        orphan=base/'attempts'/('b'*64);orphan.mkdir(parents=True)
        (orphan/'binding.json').write_bytes(b'{}')
        with self.assertRaises(PrivateRunError):
            runner_module._b1_history(base,self.budget)

    def test_b1_external_root_cannot_be_selected_by_hash_claim(self):
        with self.assertRaises(PrivateRunError):
            runner_module._b1_selected_root(self.view,self.budget)


class RunnerTests(unittest.TestCase):
    def test_bounded_receipt_decoder_rejects_excessive_integer_and_nesting(self):
        for raw in (b'{"n":'+b'9'*5000+b'}', b'['*65+b'0'+b']'*65):
            with self.subTest(prefix=raw[:8]):
                self.rec.write_bytes(raw)
                with patch.object(runner_module.subprocess, 'run', side_effect=AssertionError('engine forbidden')):
                    with self.assertRaises(PrivateRunError):
                        run_private(self.code, self.workspace, self.store, self.rec, '2000-01-01')

    def test_remaining_child_wait_uses_the_same_whole_entry_clock(self):
        actual = Path.open
        def opening(path, *args, **kwargs):
            stream = actual(path, *args, **kwargs)
            if path == self.rec:
                time.sleep(.02)
            return stream
        marker = BaseException('SYNTHETIC_ENGINE_BOUNDARY_ONLY')
        waits = []
        def no_engine(*args, **kwargs):
            waits.append(kwargs['timeout'])
            raise marker
        with patch.object(Path, 'open', opening), patch.object(runner_module.subprocess, 'run', no_engine):
            with self.assertRaises(BaseException) as caught:
                run_private(self.code, self.workspace, self.store, self.rec, '2000-01-01', timeout_seconds=1)
        self.assertIs(caught.exception, marker)
        self.assertEqual(len(waits), 1)
        self.assertGreater(waits[0], 0)
        self.assertLess(waits[0], .99)

    def test_runner_budget_counts_receipt_source_copy_and_readback_before_engine(self):
        budgets, actual = [], runner_module._ReadBudget
        def budget(*args, **kwargs):
            item = actual(*args, **kwargs)
            budgets.append(item)
            return item
        marker = KeyboardInterrupt('SYNTHETIC_ENGINE_BOUNDARY_ONLY')
        with patch.object(runner_module, '_ReadBudget', budget), patch.object(runner_module.subprocess, 'run', side_effect=marker):
            with self.assertRaises(KeyboardInterrupt) as caught:
                run_private(self.code, self.workspace, self.store, self.rec, '2000-01-01')
        self.assertIs(caught.exception, marker)
        self.assertEqual(budgets[0].bytes_read, self.rec.stat().st_size+4*self.source.stat().st_size)

    def test_oversized_existing_inbox_is_rejected_without_engine(self):
        digest = self.manifest['sources'][0]['sha256']
        target = self.workspace/'incoming'/'private_pdca'/(digest+'.txt')
        target.parent.mkdir(parents=True)
        target.write_bytes(self.source.read_bytes()+b' ')
        with patch.object(runner_module.subprocess, 'run', side_effect=AssertionError('engine forbidden')):
            with self.assertRaises(PrivateRunError):
                run_private(self.code, self.workspace, self.store, self.rec, '2000-01-01')

    def test_invalid_whole_entry_timeout_rejected_before_any_receipt_open(self):
        for seconds in (True, False, 0, -1, float('inf'), float('nan'), 331, '1'):
            with self.subTest(timeout=seconds), patch.object(runner_module.subprocess, 'run', side_effect=AssertionError('engine forbidden')):
                with self.assertRaises(PrivateRunError):
                    run_private(self.code, self.workspace, self.store, self.rec, '2000-01-01', timeout_seconds=seconds)

    def test_receipt_consumer_rejects_oversize_before_open_or_engine(self):
        self.rec.write_bytes(b' '*65)
        actual = Path.open
        opens = []
        def opening(path, *args, **kwargs):
            if path == self.rec:
                opens.append(True)
            return actual(path, *args, **kwargs)
        with patch.object(runner_module, 'MAX_RECEIPT_BYTES', 64, create=True), patch.object(Path, 'open', opening):
            with patch.object(runner_module.subprocess, 'run', side_effect=AssertionError('engine must remain unopened')):
                with self.assertRaises(PrivateRunError):
                    run_private(self.code, self.workspace, self.store, self.rec, '2000-01-01')
        self.assertEqual(opens, [])

    def test_whole_runner_deadline_includes_receipt_preflight(self):
        actual = Path.open
        def opening(path, *args, **kwargs):
            stream = actual(path, *args, **kwargs)
            if path == self.rec:
                time.sleep(.015)
            return stream
        with patch.object(Path, 'open', opening), patch.object(runner_module.subprocess, 'run', side_effect=AssertionError('expired before engine')):
            with self.assertRaises(PrivateRunError):
                run_private(self.code, self.workspace, self.store, self.rec, '2000-01-01', timeout_seconds=.005)

    def replaced_temp_control(self, selected_parent, *, primary=None):
        native_link = os.link
        replacements = []
        marker = b"SYNTHETIC_UNOWNED_REPLACEMENT_DO_NOT_DELETE"
        def link_then_replace(source, target):
            source, target = Path(source), Path(target)
            self.assertTrue(source.is_relative_to(self.base))
            self.assertTrue(target.is_relative_to(self.base))
            native_link(source, target)
            if target.parent.name == selected_parent:
                source.unlink()
                source.write_bytes(marker)
                replacements.append(source)
                if primary is not None:
                    raise primary
        caught = None
        try:
            with patch.object(os, "link", link_then_replace):
                run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")
        except BaseException as exc:
            caught = exc
        self.assertEqual(len(replacements), 1)
        self.assertTrue(replacements[0].is_file(), "Cleanup deleted an unowned regular replacement")
        self.assertEqual(replacements[0].read_bytes(), marker)
        digest = self.manifest["sources"][0]["sha256"]
        self.assertEqual((self.workspace / "incoming" / "private_pdca" / (digest + ".txt")).read_bytes(), self.source.read_bytes())
        if primary is not None:
            self.assertIs(caught, primary)
            self.assertTrue(any("TEMP_CLEANUP_RESIDUAL" in x for x in caught.__notes__))
        else:
            self.assertIsInstance(caught, PrivateRunError)
            self.assertIn("TEMP_CLEANUP_RESIDUAL", str(caught))

    def test_inbox_cleanup_preserves_replaced_regular_temp(self):
        self.replaced_temp_control("private_pdca")

    def test_result_cleanup_preserves_replaced_regular_temp(self):
        self.replaced_temp_control("private_pdca_runs")

    def test_inbox_cleanup_preserves_primary_and_explicit_residual(self):
        self.replaced_temp_control("private_pdca", primary=RuntimeError("SYNTHETIC_PRIMARY"))

    def test_result_cleanup_preserves_primary_and_explicit_residual(self):
        self.replaced_temp_control("private_pdca_runs", primary=RuntimeError("SYNTHETIC_PRIMARY"))

    def test_owned_inbox_and_result_temps_are_removed_normally(self):
        result = run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")
        digest = self.manifest["sources"][0]["sha256"]
        self.assertEqual([p.name for p in (self.workspace / "incoming" / "private_pdca").iterdir()], [digest + ".txt"])
        self.assertEqual([p.name for p in (self.store / "private_pdca_runs").iterdir()], [result["run_receipt"] + ".json"])

    def assert_bad_receipt(self, manifest):
        self.rec.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(PrivateRunError):
            run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")

    def test_receipt_id_must_bind_actual_source_rows(self):
        altered = copy.deepcopy(self.manifest)
        other = self.store / "same-bytes-new-source.txt"
        other.write_bytes(self.source.read_bytes())
        altered["sources"][0]["private_archive"] = str(other)
        self.assert_bad_receipt(altered)

    def test_receipt_schema_is_required(self):
        altered = copy.deepcopy(self.manifest)
        altered["schema"] = "unrecognized"
        self.assert_bad_receipt(altered)

    def test_extra_manifest_and_row_fields_are_rejected(self):
        for level in ("manifest", "row"):
            with self.subTest(level=level):
                altered = copy.deepcopy(self.manifest)
                target = altered if level == "manifest" else altered["sources"][0]
                target["unexpected"] = True
                # Independent legacy canonical-ID definition; not a product helper.
                altered["receipt_id"] = hashlib.sha256(json.dumps(
                    altered["sources"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                self.assert_bad_receipt(altered)

    def test_bool_and_zero_source_sizes_are_not_valid_receipt_rows(self):
        for data, bad_size in ((b"x", True), (b"", 0)):
            with self.subTest(size=bad_size):
                self.source.write_bytes(data)
                altered = copy.deepcopy(self.manifest)
                altered["sources"][0].update(sha256=hashlib.sha256(data).hexdigest(), size_bytes=bad_size)
                altered["receipt_id"] = hashlib.sha256(json.dumps(
                    altered["sources"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                self.assert_bad_receipt(altered)

    def test_non_dict_or_empty_or_duplicate_rows_raise_typed_rejection(self):
        for rows in ([], [None], self.manifest["sources"] * 2):
            with self.subTest(rows=rows):
                altered = copy.deepcopy(self.manifest)
                altered["sources"] = rows
                self.assert_bad_receipt(altered)

    def test_legacy_intake_id_and_bytes_remain_compatible(self):
        legacy_id = hashlib.sha256(json.dumps(self.manifest["sources"],
            ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        self.assertEqual(self.manifest["receipt_id"], legacy_id)
        receipt_before, source_before = self.rec.read_bytes(), self.source.read_bytes()
        result = run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")
        self.assertEqual(result["overall_status"], "BLOCKED")
        self.assertEqual(self.rec.read_bytes(), receipt_before)
        self.assertEqual(self.source.read_bytes(), source_before)

    def test_invalid_receipt_types_and_size_bounds_are_rejected(self):
        for field, value in (("size_bytes", "1"), ("size_bytes", 200*1024*1024+1),
                             ("private_archive", True), ("sha256", True), ("type", "other")):
            with self.subTest(field=field, value=value):
                altered = copy.deepcopy(self.manifest)
                altered["sources"][0][field] = value
                altered["receipt_id"] = hashlib.sha256(json.dumps(
                    altered["sources"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                self.assert_bad_receipt(altered)

    def test_two_real_intake_rows_roundtrip_without_rewriting_receipt(self):
        gpx = self.base / "synthetic.gpx"
        gpx.write_text('<gpx creator="SYNTHETIC_TEST_ONLY"/>', encoding="utf-8")
        result = intake(self.code, self.store, log_file=self.source, gpx_file=gpx)
        receipt = self.store / "receipts" / (result["receipt_id"] + ".json")
        before = receipt.read_bytes()
        run = run_private(self.code, self.workspace, self.store, receipt, "2000-01-01")
        self.assertEqual(run["overall_status"], "BLOCKED")
        self.assertEqual(receipt.read_bytes(), before)

    def result_alias_rejected(self, *, junction=False):
        outside = self.code / "forbidden-test-output"
        outside.mkdir()
        link = self.store / "private_pdca_runs"
        if junction:
            if os.name != "nt":
                self.skipTest("Actual Windows junction control requires Windows")
            proc = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(outside)],
                                  capture_output=True, check=False)
            if proc.returncode:
                self.skipTest("Junction unavailable without elevation: " + str(proc.returncode))
        else:
            try:
                link.symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest("Actual symlink unavailable without elevation: " + str(exc))
        def remove_alias():
            try:
                os.rmdir(link) if junction else link.unlink()
            except FileNotFoundError:
                pass
        self.addCleanup(remove_alias)
        with self.assertRaises(PrivateRunError):
            run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.workspace / "incoming").exists())

    def test_result_parent_symlink_cannot_escape_private_store(self):
        self.result_alias_rejected()

    def test_result_parent_junction_cannot_escape_private_store(self):
        self.result_alias_rejected(junction=True)

    def test_existing_result_leaf_symlink_is_not_reused(self):
        result = run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")
        dest = self.store / "private_pdca_runs" / (result["run_receipt"] + ".json")
        outside = self.code / "synthetic-run-receipt.json"
        dest.rename(outside)
        before = outside.read_bytes()
        try:
            dest.symlink_to(outside)
        except (OSError, NotImplementedError) as exc:
            self.skipTest("Actual symlink unavailable without elevation: " + str(exc))
        with self.assertRaises(PrivateRunError):
            run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")
        self.assertEqual(outside.read_bytes(), before)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.code, self.store, self.workspace = (base / v for v in ("code", "store", "work"))
        for p in (self.code, self.store, self.workspace):
            p.mkdir(mode=0o700)
        (self.code / "scripts").mkdir()
        (self.code / "scripts" / "run_pdca.py").write_text(
            'import json\nprint(json.dumps({"overall_status":"BLOCKED"}))\nraise SystemExit(2)\n')
        # Genuine intake receipt over explicit synthetic bytes, never private source.
        original = base / "synthetic-log.txt"
        original.write_text("2000/01/01 19:55\n捕獲\nハブ捕獲~90幼体\n", encoding="utf-8")
        received = intake(self.code, self.store, log_file=original)
        self.rec = self.store / "receipts" / (received["receipt_id"] + ".json")
        self.manifest = json.loads(self.rec.read_text(encoding="utf-8"))
        self.source = Path(self.manifest["sources"][0]["private_archive"])
        self.base = base

    def test_repeated_run_same_sources_no_double_count(self):
        x = run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")
        y = run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")
        self.assertEqual(x, y)
        self.assertEqual(x["overall_status"], "BLOCKED")
        self.assertEqual(len(list((self.store/"private_pdca_runs").glob("*.json"))), 1)

    def test_modified_original_rejected(self):
        self.source.write_text("tampered")
        with self.assertRaises(PrivateRunError):
            run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")

    def test_private_path_cannot_be_public_repo(self):
        with self.assertRaises(PrivateRunError):
            run_private(self.code, self.code, self.store, self.rec, "2000-01-01")

    def test_bad_night_rejected(self):
        with self.assertRaises(PrivateRunError):
            run_private(self.code, self.workspace, self.store, self.rec, "2026-10-26;rm")

    def test_symlink_to_external_raw_rejected(self):
        outside = self.workspace / "outside.txt"
        outside.write_bytes(self.source.read_bytes())
        self.source.unlink()
        try:
            self.source.symlink_to(outside)
        except (OSError, NotImplementedError) as exc:
            self.skipTest("Actual symlink unavailable without elevation: " + str(exc))
        with self.assertRaises(PrivateRunError):
            run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")

    def test_engine_success_does_not_grant_scientific_certification(self):
        (self.code / "scripts" / "run_pdca.py").write_text(
            'import json\nprint(json.dumps({"overall_status":"PASS"}))\n')
        result = run_private(self.code, self.workspace, self.store, self.rec, "2000-01-01")
        self.assertEqual(result["model_validation"], "NOT_CERTIFIED")
        self.assertEqual(result["p0"], "NOT_CERTIFIED")


if __name__ == "__main__":
    unittest.main()
