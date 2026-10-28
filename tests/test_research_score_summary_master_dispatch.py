"""Synthetic engineering integration; no source/scientific/production grant."""
from pathlib import Path
import copy
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src'), str(ROOT/'tests')]


class NewEntryTests(unittest.TestCase):
    def test_closed_parent_entry_exists_without_changing_cli(self):
        import research_score_summary_request as api
        self.assertTrue(callable(getattr(api, 'evaluate_master_score_summary_request', None)),
                        'Missing explicit master diagnostic connection')


class _PhysicalFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_research_score_summary_request import materialize
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name)
        cls.request, cls.execution, cls.p2 = materialize(cls.base)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        import prospective_inputs as pi
        import research_score_summary_request as api
        self.api, self.pi = api, pi
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'fixture'
        shutil.copytree(self.base, self.root)
        self.context = pi.ProspectiveReadContext(300, 2*1024**3)

    def call(self, context=None):
        return self.api.evaluate_master_score_summary_request(self.root, '2026-10-14',
            context=self.context if context is None else context)


class ParentContractTests(_PhysicalFixture):

    def test_real_single_artifact_original_command_and_small_four_payloads(self):
        from master_contracts import canonical_bytes, digest
        actual = self.api._command
        commands = []
        def command(*a, **kw):
            raw = actual(*a, **kw); commands.append(raw); return raw
        deadline = self.context.deadline
        self.context.account(1)
        with patch.object(self.api, '_command', command):
            value = self.call()
        self.assertEqual(len(commands), 1)
        self.assertEqual(set(value), {'schema_version','stages','candidates','folds','replay',
            'research_questions','implementation_blockers','data_blockers','decision',
            'diagnostic_observation','scientific_status','authorities'})
        o = value['diagnostic_observation']; ref = o['artifact_ref']
        self.assertEqual((self.root/ref['path']).read_bytes(), commands[0])
        original = json.loads(commands[0]); self.assertEqual(o['command_receipt_sha256'], original['receipt_sha256'])
        self.assertEqual(o['entry_read_bytes'], 1)
        self.assertEqual(o['command_final_read_bytes'], original['final_read_bytes'])
        self.assertEqual(o['parent_final_read_bytes'], self.context.bytes_read)
        self.assertEqual(sum(o['phase_read_ledger'].values()), self.context.bytes_read-1)
        self.assertEqual(self.context.deadline, deadline)
        self.assertEqual(o['receipt_sha256'], digest({k:v for k,v in o.items() if k!='receipt_sha256'}))
        self.assertEqual(o['publication_disposition'], 'CREATED')
        wrappers = [canonical_bytes(dict(stage=row,payload=value))+b'\n' for row in value['stages']]
        self.assertLessEqual(sum(map(len,wrappers)), 65536)
        self.assertEqual([s['status'] for s in value['stages']], ['NOT_VALIDATED']*3+['BLOCKED'])
        self.assertFalse(any(value['authorities'].values())); self.assertEqual(value['candidates'], [])

    def test_whole_nmd_unadmitted_manifest_never_opened_even_final_rescan(self):
        from master_contracts import canonical_bytes
        from test_g0_forecast_contract import base_ref
        profile = json.loads((self.root/'config/summary-v2.json').read_bytes())
        profile['fit_lineage']=None; profile['models'][2]['artifact']=None
        request = copy.deepcopy(self.request)
        request['summary_manifest']=base_ref(self.root,'config/summary-v2.json',canonical_bytes(profile))
        request['stage1_manifest']=base_ref(self.root,request['stage1_manifest']['path'],b'valid-ref-unadmitted-manifest-poison')
        (self.root/self.api.REQUEST_PATH).write_bytes(canonical_bytes(request))
        actual=Path.open; opened=[]; target=self.root/request['stage1_manifest']['path']
        def opening(p,*a,**kw):
            if p==target: opened.append(str(p))
            return actual(p,*a,**kw)
        with patch.object(Path,'open',opening): value=self.call()
        self.assertEqual(opened, [])
        self.assertEqual(value['diagnostic_observation']['status'], 'NEED_MORE_DATA')
        self.assertTrue(all(s['status']=='BLOCKED' and s['blocker_kind']=='DATA_BLOCKED' for s in value['stages']))

    def test_first_falsey_object_through_direct_and_reporting_boundary(self):
        class Marker(BaseException):
            def __bool__(self): return False
        marker=Marker('original')
        pi=self.pi
        class Context(pi.ProspectiveReadContext):
            def check(c): raise marker
        c=Context(300,2*1024**3)
        with self.assertRaises(Marker) as caught: self.call(c)
        self.assertIs(caught.exception, marker)
        with self.assertRaises(self.api._MasterDiagnosticFailure) as boundary:
            self.api._evaluate_for_master(self.root,'2026-10-14',context=c)
        self.assertIs(boundary.exception.primary,marker)
        result=self.api._failure_adapter(boundary.exception)
        self.assertIsNone(result['diagnostic_observation'])
        self.assertEqual(result['decision']['decision'],'REJECT_CANDIDATE')
        self.assertTrue(all(s['status']=='FAIL' for s in result['stages']))

    def test_existing_model_default_no_new_optional_import_or_probe(self):
        import model_evaluation as model
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(sys.modules,{'research_score_summary_request':None}):
                value=model.evaluate_models(Path(td),'2026-10-14')
        self.assertEqual(value['decision']['decision'],'NEED_MORE_DATA')

    def test_explicit_context_dispatch_does_not_invoke_legacy_loader(self):
        import model_evaluation as model
        with patch.object(model,'_validate',side_effect=AssertionError('legacy learning read')):
            value=model.evaluate_models(self.root,'2026-10-14',_score_summary_context=self.context)
        self.assertIsNotNone(value['diagnostic_observation'])

    def test_genuine_first_and_post_command_one_byte_charges(self):
        pi=self.pi; one=self.root/'config/one-byte.bin';one.write_bytes(b'x')
        class Context(pi.ProspectiveReadContext):
            first=True
            def check(c):
                if c.first:
                    c.first=False
                    pi._bounded_bytes(one,pi._LocalByteBudget(c,1),lambda:None)
                super().check()
        c=Context(300,2*1024**3);decode=self.api._decode;post=[]
        def decoding(raw,guard):
            if raw.startswith(b'{"schema_version":"habu-research-score-summary-command-v1"'):
                pi._bounded_bytes(one,pi._LocalByteBudget(c,1),lambda:None);post.append(c.bytes_read)
            return decode(raw,guard)
        with patch.object(self.api,'_decode',decoding):value=self.call(c)
        o=value['diagnostic_observation']
        self.assertEqual(o['phase_read_ledger']['before_command_bytes'],1)
        self.assertEqual(post,[o['command_final_read_bytes']+1])
        self.assertEqual(c.bytes_read,o['parent_final_read_bytes'])

    def test_genuine_final_guard_read_rejects_and_cleans_only_new_file(self):
        pi=self.pi; one=self.root/'config/final-one.bin';one.write_bytes(b'x')
        class Context(pi.ProspectiveReadContext):
            armed=False
            def check(c):
                if c.armed:
                    c.armed=False;pi._bounded_bytes(one,pi._LocalByteBudget(c,1),lambda:None)
                super().check()
        c=Context(300,2*1024**3);actual=self.api._parent_wrappers
        def wrappers(value,*args):
            result=actual(value,*args)
            if value['diagnostic_observation']['receipt_sha256']!='0'*64: c.armed=True
            return result
        with patch.object(self.api,'_parent_wrappers',wrappers):
            with self.assertRaisesRegex(ValueError,'ledger changed'):self.call(c)
        folder=self.root/'reports/pdca/2026-10-14/diagnostics/score-summary-v1'
        self.assertEqual(list(folder.iterdir()),[])

    def test_reuse_never_owned_and_failed_reuse_is_not_deleted(self):
        first=self.call();ref=first['diagnostic_observation']['artifact_ref'];raw=(self.root/ref['path']).read_bytes()
        second=self.call(self.pi.ProspectiveReadContext(300,2*1024**3))
        self.assertEqual(second['diagnostic_observation']['publication_disposition'],'REUSED')
        self.assertEqual((self.root/ref['path']).read_bytes(),raw)
        actual=self.api._recheck;marker=OSError('post-read failure')
        def fail(*a,**kw):actual(*a,**kw);raise marker
        with patch.object(self.api,'_recheck',fail):
            with self.assertRaises(OSError) as caught:self.call(self.pi.ProspectiveReadContext(300,2*1024**3))
        self.assertIs(caught.exception,marker)
        self.assertEqual((self.root/ref['path']).read_bytes(),raw)

    def test_owned_limit_and_opaque_child_error_report_differently(self):
        with patch.object(self.api,'PARENT_MAX_BYTES',1):
            with self.assertRaises(self.api._MasterDiagnosticFailure) as caught:
                self.api._evaluate_for_master(self.root,'2026-10-14',context=self.context)
        value=self.api._failure_adapter(caught.exception)
        self.assertTrue(all(s['blocker_kind']=='RUNTIME_BLOCKED' for s in value['stages']))
        self.assertIsNone(value['diagnostic_observation'])
        marker=self.pi.InputCapacityError('caller, not locally proven')
        with patch.object(self.api,'_command',side_effect=marker):
            with self.assertRaises(self.api._MasterDiagnosticFailure) as caught:
                self.api._evaluate_for_master(self.root,'2026-10-14',context=self.pi.ProspectiveReadContext(300,2*1024**3))
        self.assertIs(caught.exception.primary,marker)
        value=self.api._failure_adapter(caught.exception)
        self.assertTrue(all(s['status']=='FAIL' for s in value['stages']))
        self.assertEqual(value['data_blockers'],[])

    def test_failure_rows_recovery_and_interrupt_reason(self):
        from master_contracts import canonical_bytes
        for origin in self.api._MASTER_ORIGINS:
            marker=KeyboardInterrupt() if origin=='INTERRUPTED' else ValueError()
            failure=self.api._MasterDiagnosticFailure(marker,origin)
            value=self.api._failure_adapter(failure)
            recovered=json.loads(canonical_bytes(dict(stage=value['stages'][0],payload=value)))['payload']
            self.assertEqual(recovered,value);self.assertIsNone(value['diagnostic_observation'])
            self.assertEqual(value['data_blockers'],[])
            if origin=='INTERRUPTED':self.assertTrue(all('INTERRUPTED' in s['reason'] for s in value['stages']))
        value=self.api._failure_adapter(self.api._MasterDiagnosticFailure(KeyboardInterrupt(),'INTERRUPTED',['reports/residual']))
        self.assertTrue(all('INTERRUPTED' in s['reason'] and s['status']=='FAIL' for s in value['stages']))

    @unittest.skipIf(os.name=='nt','Actual Champion import uses fcntl; mandatory on Ubuntu')
    def test_actual_champion_decision_matches_recovered_failure_payload(self):
        import champion_registry as champion
        from master_contracts import canonical_bytes
        for origin in self.api._MASTER_ORIGINS:
            value=self.api._failure_adapter(self.api._MasterDiagnosticFailure(ValueError(),origin))
            recovered=json.loads(canonical_bytes(value))
            self.assertEqual(champion.evaluate_promotion(self.root,'2026-10-14',value),
                             champion.evaluate_promotion(self.root,'2026-10-14',recovered))

    def test_context_and_complete_wrapper_bounds(self):
        for bad in [None,False,object()]:
            with self.assertRaises(ValueError):self.call(bad if bad is not None else object())
        value=self.api._failure_adapter(self.api._MasterDiagnosticFailure(ValueError(),'INPUT_IO_OR_CALLER'))
        state=self.api._ParentState();guard=self.api._ParentGuard(self.context,state)
        with patch.object(self.api,'PARENT_WRAPPER_BYTES',len(json.dumps(value))):
            with self.assertRaises(self.pi.InputCapacityError):self.api._parent_wrappers(value,guard,state)
        self.assertIsNotNone(state.owned)

    def test_true_source2_late_retains_barrier_and_conservative_failure(self):
        from master_contracts import canonical_bytes
        from test_g0_forecast_contract import base_ref
        profile=json.loads((self.root/'config/summary-v2.json').read_bytes())
        path=profile['candidate_config_manifest']['path'];source=json.loads((self.root/path).read_bytes())
        source['readiness']['audited_at']=source['usable_at']=profile['fit_cutoff']
        profile['candidate_config_manifest']=base_ref(self.root,path,canonical_bytes(source))
        request=copy.deepcopy(self.request)
        request['summary_manifest']=base_ref(self.root,'config/summary-v2.json',canonical_bytes(profile))
        (self.root/self.api.REQUEST_PATH).write_bytes(canonical_bytes(request))
        (self.root/profile['forecast_manifest']['path']).write_bytes(b'{}')
        opens=[];actual=Path.open
        def opening(p,*a,**kw):
            if p.is_relative_to(self.root) and p.relative_to(self.root).parts[0] in ('features','models'):opens.append(p)
            return actual(p,*a,**kw)
        with patch.object(Path,'open',opening):
            with self.assertRaises(self.api._MasterDiagnosticFailure) as caught:
                self.api._evaluate_for_master(self.root,'2026-10-14',context=self.context)
        self.assertIs(type(caught.exception.primary),self.api.source.CandidateConfigSourceBlocked)
        self.assertEqual(opens,[])
        value=self.api._failure_adapter(caught.exception)
        self.assertTrue(all(s['status']=='FAIL' for s in value['stages']))

    def test_post_publication_original_size_and_code_membership_reject(self):
        actual=self.api.g0.G0ArtifactReader.read
        for mode in ('request_size','code_member'):
            with self.subTest(mode=mode):
                with tempfile.TemporaryDirectory() as td:
                    root=Path(td)/'fixture';shutil.copytree(self.base,root);seen=[]
                    def read(reader,ref,**kw):
                        raw=actual(reader,ref,**kw)
                        if ref['path'].startswith('reports/') and not seen:
                            seen.append(1)
                            target=root/(self.api.REQUEST_PATH if mode=='request_size' else 'src/new-member.py')
                            with target.open('ab') as stream:stream.write(b' ')
                        return raw
                    with patch.object(self.api.g0.G0ArtifactReader,'read',read):
                        with self.assertRaises(ValueError):
                            self.api.evaluate_master_score_summary_request(root,'2026-10-14',context=self.pi.ProspectiveReadContext(300,2*1024**3))
                    self.assertEqual(seen,[1])
                    self.assertEqual(list((root/'reports/pdca/2026-10-14/diagnostics/score-summary-v1').iterdir()),[])

    def test_cleanup_residual_keeps_first_primary_and_reports_fail(self):
        class Marker(BaseException):
            def __bool__(self):return False
        marker=Marker('primary');actual=self.api._parent_wrappers
        def wrappers(value,*args):
            if value['diagnostic_observation']['receipt_sha256']!='0'*64:raise marker
            return actual(value,*args)
        cleanup=self.api._parent_cleanup;calls=[]
        def clean(root,ownership):
            calls.extend(row[0] for row in ownership)
            if any(not Path(row[0]).name.startswith('.score-summary-') for row in ownership):
                return [row[0] for row in ownership]
            return cleanup(root,ownership)
        with patch.object(self.api,'_parent_wrappers',wrappers),patch.object(self.api,'_parent_cleanup',clean):
            with self.assertRaises(Marker) as caught:self.call()
        self.assertIs(caught.exception,marker)
        self.assertTrue(any('residual' in note for note in marker.__notes__))
        self.assertEqual(len(calls),len(set(calls)))

    def test_real_account_csv_and_parent_hash_errors_keep_original(self):
        pi=self.pi
        class Marker(BaseException):
            def __bool__(self):return False
        marker=Marker('account')
        class Context(pi.ProspectiveReadContext):
            def account(c,n):super().account(n);raise marker
        c=Context(300,2*1024**3)
        with self.assertRaises(Marker) as caught:self.call(c)
        self.assertIs(caught.exception,marker);self.assertGreater(c.bytes_read,0)
        error=self.api.pure.Stage1CapacityBlocked('original CSV');actual=Path.open
        def opened(p,*a,**kw):
            if p.name=='captures.csv':raise error
            return actual(p,*a,**kw)
        with patch.object(Path,'open',opened):
            with self.assertRaises(self.api.pure.Stage1CapacityBlocked) as caught:self.call()
        self.assertIs(caught.exception,error)
        error=self.api.pure.Stage1BudgetBlocked('original parent hash');digest=self.api._digest
        def hashing(value,guard):
            if type(value)is dict and value.get('schema_version')==self.api.MASTER_OBSERVATION_VERSION:raise error
            return digest(value,guard)
        with patch.object(self.api,'_digest',hashing):
            with self.assertRaises(self.api.pure.Stage1BudgetBlocked) as caught:
                self.call(pi.ProspectiveReadContext(300,2*1024**3))
        self.assertIs(caught.exception,error)

    def test_actual_master_owned_first_deadline_and_failed_read_allowance(self):
        import time
        c=self.pi.ProspectiveReadContext(300,1);c.deadline=time.monotonic()-1
        with self.assertRaises(self.api._MasterDiagnosticFailure) as caught:
            self.api._evaluate_for_master(self.root,'2026-10-14',context=c)
        self.assertEqual(caught.exception.origin,'PARENT_OWNED_DEADLINE');self.assertEqual(c.bytes_read,0)
        tiny=self.root/'config/two-bytes.bin';tiny.write_bytes(b'xx')
        c=self.pi.ProspectiveReadContext(300,1)
        with self.assertRaises(self.pi.InputCapacityError):
            self.pi._bounded_bytes(tiny,self.pi._LocalByteBudget(c,2),lambda:None)
        self.assertEqual(c.bytes_read,2)
        with self.assertRaises(self.api._MasterDiagnosticFailure) as caught:
            self.api._evaluate_for_master(self.root,'2026-10-14',context=c)
        self.assertEqual(caught.exception.origin,'PARENT_OWNED_BYTE_LIMIT');self.assertEqual(c.bytes_read,2)


@unittest.skipIf(os.name=='nt','Genuine master fcntl/bare-Git recovery runs on Ubuntu; no Windows facade')
class ActualMasterTests(_PhysicalFixture):
    def test_master_snapshot_one_core_checkpoint_and_recovery(self):
        import subprocess
        def git(*args):
            return subprocess.check_output(['git','-C',str(self.root),*args],stderr=subprocess.DEVNULL)
        git('init','-b','main'); git('config','core.autocrlf','false')
        git('config','maintenance.auto','false'); git('config','gc.auto','0')
        git('add','.');git('-c','user.name=Synthetic','-c','user.email=test@example.invalid','commit','-m','Synthetic authorized request/code')
        source=git('rev-parse','HEAD').decode().strip()
        remote=self.root.parent/'origin.git'
        subprocess.run(['git','init','--bare',str(remote)],check=True,capture_output=True)
        git('remote','add','origin',str(remote));git('push','origin','main')
        # Import the ACTUAL complete physical program, including explicit
        # synthetic feature helpers. No loaded-code/hash substitution.
        script=r'''
import sys,json
from pathlib import Path
from unittest.mock import patch
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'src'))
from master_orchestrator import run_master
import research_score_summary_request as api
from pdca_bridge import GitTransport,build_bundle,restore_bundle
calls=[];actual=api._command
def command(*a,**kw):calls.append(a[0]);return actual(*a,**kw)
with patch.object(api,'_command',command),patch('learning_snapshot.build_learning_snapshot',side_effect=AssertionError('legacy builder')):
 result=run_master(root,'2026-10-14')
assert len(calls)==1 and not result['completed'] and result['overall_status']!='PASS',result
directory=root/'reports/pdca/2026-10-14/runs'/result['run_id']
payloads=[json.loads((directory/'stages'/f'{n}.json').read_bytes())['payload'] for n in api.MASTER_NAMES]
assert all(p==payloads[0] for p in payloads) and payloads[0]['diagnostic_observation'] is not None
with patch.object(api,'_command',side_effect=AssertionError('duplicate rerun')):
 assert run_master(root,'2026-10-14')==result
bundle=build_bundle(root,'2026-10-14',result['run_id'],sys.argv[2],GitTransport(root))
assert sum(map(len,bundle['files'].values()))<=20*1024**2
transport=GitTransport(root)
commit=transport.publish('pdca/run-'+result['run_id'],sys.argv[2],None,bundle['files'])
restored=root.parent/'restored'
restore_bundle(transport,commit,bundle['manifest_path'],restored,sys.argv[2])
with patch.object(api,'_command',side_effect=AssertionError('restored duplicate rerun')):
 assert run_master(restored,'2026-10-14')==result
# A changed declared request creates a separate identity; a real failed caller
# survives the common four-payload checkpoint and later Champion assessment.
request=root/api.REQUEST_PATH;request.write_bytes(request.read_bytes()+b' ')
marker=ValueError('caller')
with patch.object(api,'_command',side_effect=marker): failed=run_master(root,'2026-10-14')
assert failed['overall_status']=='FAIL',failed
fd=root/'reports/pdca/2026-10-14/runs'/failed['run_id']
payloads=[json.loads((fd/'stages'/f'{n}.json').read_bytes())['payload'] for n in api.MASTER_NAMES]
assert all(p==payloads[0] for p in payloads) and payloads[0]['diagnostic_observation'] is None
assert payloads[0]['decision']['decision']=='REJECT_CANDIDATE'
with patch.object(api,'_command',side_effect=AssertionError('failed checkpoint rerun')):
 assert run_master(root,'2026-10-14')==failed
print(json.dumps({'run_id':result['run_id'],'calls':len(calls),'status':result['overall_status']}))
'''
        result=subprocess.run([sys.executable,'-c',script,str(self.root),source],capture_output=True,text=True,timeout=300)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
