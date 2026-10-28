import hashlib
import json
import copy
import os
import shutil
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


class B2PortableTests(unittest.TestCase):
    def test_committed_partial_stage_wrapper_must_satisfy_native_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp);budget=intake_module._ReadBudget(30,error_type=PrivateRunError)
            contracts,_=runner_module._b1_modules(budget)
            identity=dict(night='2000-01-01',inputs={},code='1'*64,policy={},runtime={},inventory_error=None)
            rid=contracts.digest(identity);directory=work/'reports/pdca/2000-01-01/runs'/rid;directory.mkdir(parents=True)
            path=directory/'stages/evidence_audit.json';path.parent.mkdir()
            raw=contracts.canonical_bytes(dict(stage=None,payload=None))+b'\n';path.write_bytes(raw)
            cp=dict(schema_version='1.0',run_id=rid,outputs={'stages/evidence_audit.json':hashlib.sha256(raw).hexdigest()},
                    elapsed_seconds=.1,round_number=0,created_at='2000-01-01T00:00:00+00:00',result_sha256=None,
                    active_stage=None,active_since=None,attempt_deadline=None)
            (directory/'checkpoint.json').write_bytes(contracts.canonical_bytes(cp)+b'\n')
            (directory/'checkpoint.sha256.json').write_bytes(contracts.canonical_bytes({'sha256':contracts.digest(cp)})+b'\n')
            with self.assertRaisesRegex(PrivateRunError,'PARTIAL_CHECKPOINT_STAGE'):
                runner_module._b2_known_checkpoint(work,identity,budget)

    def test_partial_checkpoint_required_fields_before_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace=Path(tmp);budget=intake_module._ReadBudget(30,error_type=PrivateRunError)
            contracts,_=runner_module._b1_modules(budget)
            identity=dict(night='2000-01-01',inputs={},code='1'*64,policy={},runtime={},inventory_error=None)
            runid=contracts.digest(identity);directory=workspace/'reports'/'pdca'/identity['night']/'runs'/runid
            directory.mkdir(parents=True)
            original=dict(schema_version='1.0',run_id=runid,outputs={},elapsed_seconds=.1,round_number=0,
                          created_at='2000-01-01T00:00:00+00:00',result_sha256=None,active_stage=None,active_since=None,attempt_deadline=None)
            def save(cp):
                (directory/'checkpoint.json').write_bytes(contracts.canonical_bytes(cp)+b'\n')
                (directory/'checkpoint.sha256.json').write_bytes(contracts.canonical_bytes({'sha256':contracts.digest(cp)})+b'\n')
            save(original)
            self.assertIsNone(runner_module._b2_known_checkpoint(workspace,identity,budget)['result'])
            for key,value in (('created_at',None),('created_at',False),('created_at','2000-01-01'),
                              ('active_since','1999-01-01T00:00:00+00:00'),('active_stage',[])):
                with self.subTest(key=key,value=value):
                    changed=dict(original);changed[key]=value;save(changed)
                    with self.assertRaises(PrivateRunError):runner_module._b2_known_checkpoint(workspace,identity,budget)
            missing=dict(original);del missing['created_at'];save(missing)
            with self.assertRaises(PrivateRunError):runner_module._b2_known_checkpoint(workspace,identity,budget)

    def test_owned_native_decoder_does_not_reclassify_budget_first(self):
        marker=PrivateRunError('SYNTHETIC_CALLER_FIRST')
        class Budget:
            def check(self):raise marker
        with self.assertRaises(PrivateRunError) as caught:
            runner_module._b1_document(b'{}',Budget(),error_type=runner_module._B2NativeRejected)
        self.assertIs(caught.exception,marker)
        self.assertNotIsInstance(caught.exception,runner_module._B2NativeRejected)
        with self.assertRaises(runner_module._B2NativeRejected):
            runner_module._b1_document(b'{',intake_module._ReadBudget(30),error_type=runner_module._B2NativeRejected)

    def failure_history(self):
        # Hand-declared structural private failure, never executed native output.
        f=B1HelperTests();f.setUp();self.addCleanup(f.doCleanups)
        scope,aid,source,binding=f.binding_fixture();budget=f.budget;store=f.store
        bh=runner_module._b1_hash('habu-private-pdca-binding-v2',binding,budget)
        directory=store/'private_pdca_runs'/'v2'/'scopes'/scope/'attempts'/aid
        (directory/'streams').mkdir(parents=True)
        stamp='2000-01-01T00:00:00+00:00';nonce='a'*32
        claim=dict(schema='habu-private-pdca-claim-v2',scope_id=scope,attempt_id=aid,revision='r1',binding_sha256=bh,
                   claim_nonce=nonce,created_at_utc=stamp,phase='RESERVED_PRESPAWN')
        def save(name,value,lf=True):
            path=directory/name;raw=runner_module._b1_canonical(value,budget)+(b'\n' if lf else b'');path.write_bytes(raw)
            return dict(path=path.relative_to(store).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),size_bytes=len(raw))
        save('binding.json',binding,False);save('claim.json',claim,False)
        streams={};h=hashlib.sha256(b'').hexdigest()
        for name in ('stdout','stderr'):
            path=directory/'streams'/(name+'.bin');path.write_bytes(b'')
            streams[name]=dict(artifact_ref=dict(path=path.relative_to(store).as_posix(),sha256=h,size_bytes=0),
                observed_read_bytes=0,retained_size_bytes=0,retained_sha256=h,eof=False,complete=False,overflow_detected=False,
                full_stream_sha256=None,error_code='SPAWN_FAILURE')
        failure=dict(code='SPAWN_FAILURE',origin='OS_SPAWN_OR_EXIT',phase='SUPERVISE_OR_NATIVE_VALIDATION',residual='')
        sup=dict(schema='habu-private-pdca-supervisor-v2',scope_id=scope,attempt_id=aid,binding_sha256=bh,claim_nonce=nonce,
                 execution_policy='private-pdca-bound-execution-v2',argv=[sys.executable,str(f.view/'scripts/run_pdca.py'),'--root',str(f.view),'--night','2000-01-01','--budget-seconds','10'],
                 cwd=str(f.view),runtime={},pid=None,pgid=None,started_at_utc=stamp,finished_at_utc=stamp,
                 entry_deadline_monotonic_ns=100*10**9,run_deadline_monotonic_ns=75*10**9,cleanup_deadline_monotonic_ns=80*10**9,
                 scientific_budget_seconds=10,reserves=dict(terminate_seconds=5,validate_persist_seconds=20,final_read_reserve_bytes=0,
                   pipe_read_ceiling_bytes=6291458,read_plan_sha256='1'*64),returncode=None,signal=None,spawn_status='SPAWN_FAILED',
                 stop_reason='SPAWN_FAILURE',stop_origin='OS_SPAWN_OR_EXIT',stdout=streams['stdout'],stderr=streams['stderr'],
                 capture_read_bytes=0,artifact_read_bytes_at_spawn=0,artifact_read_bytes_after_capture=0,
                 report_validation=dict(status='NOT_RUN',native_result_ref=None,report_view_sha256=None,reason_code='SPAWN_FAILURE'),
                 cleanup=dict(direct_child='NOT_SPAWNED',process_group='NOT_SPAWNED',stdout_closed=True,stderr_closed=True,
                   selector_closed=True,owned_temps_verified=True,signal_events=[],residual_codes=[]),failure=failure,code_sha256=binding['complete_code_sha256'])
        def finish():
            sr=save('supervisor.json',sup);save('result.json',runner_module._b2_private_result(scope,aid,bh,sr,sup,None))
            terminal=dict(schema='habu-private-pdca-terminal-v2',scope_id=scope,attempt_id=aid,binding_sha256=bh,claim_nonce=nonce,
                kind='SUPERVISOR_FAILURE',phase='SPAWN_FAILURE',child_returncode=None,backend_status=None,private_status='FAIL',
                native_run_id=None,native_completed=None,result_ref=None,report_view_sha256=None,supervisor_ref=sr,failure=failure,
                finished_at_utc=stamp,artifact_read_bytes=0,cleanup_verified=True,**runner_module.B2_FLAGS)
            save('terminal.json',terminal);return terminal
        terminal=finish()
        return f,directory,source,claim,sup,terminal,save,finish

    def test_history_requires_complete_canonical_generation_and_typed_times(self):
        f,directory,source,claim,sup,terminal,save,finish=self.failure_history()
        validate=lambda:runner_module._b2_validate_attempt(f.store,directory,source,f.budget)
        self.assertEqual(validate()['result']['private_status'],'FAIL')
        path=directory/'terminal.json';raw=path.read_bytes();path.write_bytes(raw[:-1])
        with self.assertRaisesRegex(PrivateRunError,'INCOMPLETE_TERMINAL'):validate()
        path.write_bytes(raw)
        for which,key,bad in (('claim','created_at_utc',{}),('sup','started_at_utc',[]),('sup','finished_at_utc',None),
                              ('terminal','finished_at_utc',False),('terminal','phase',None)):
            with self.subTest(key=key):
                owner={'claim':claim,'sup':sup,'terminal':terminal}[which]
                old=owner[key];owner[key]=bad
                if owner is claim:save('claim.json',claim,False)
                elif owner is sup:terminal=finish()
                else:save('terminal.json',terminal)
                with self.assertRaises(PrivateRunError):validate()
                owner[key]=old;save('claim.json',claim,False);terminal=finish()

    def test_history_requires_matching_native_validation_failure_reason(self):
        f,directory,source,claim,sup,terminal,save,finish=self.failure_history()
        for key,bad in (('reason_code','NATIVE_EXIT'),('status','REJECTED')):
            with self.subTest(key=key):
                old=sup['report_validation'][key];sup['report_validation'][key]=bad;finish()
                with self.assertRaises(PrivateRunError):
                    runner_module._b2_validate_attempt(f.store,directory,source,f.budget)
                sup['report_validation'][key]=old

    def test_nonspawned_history_cannot_be_rebound_to_child_signal(self):
        f,directory,source,claim,sup,terminal,save,finish=self.failure_history()
        for reason,origin in (('CHILD_SIGNAL','OS_SPAWN_OR_EXIT'),('OWNED_TIMEOUT','CLOSED_TIMER_OBSERVATION'),
                              ('STDOUT_CAPACITY','CLOSED_PIPE_READ_OBSERVATION')):
            with self.subTest(reason=reason):
                sup['stop_reason']=reason;sup['stop_origin']=origin
                sup['failure'].update(code=reason,origin=origin);sup['report_validation']['reason_code']=reason
                terminal=finish();terminal['phase']=reason;save('terminal.json',terminal)
                with self.assertRaisesRegex(PrivateRunError,'SPAWN_FACTS'):
                    runner_module._b2_validate_attempt(f.store,directory,source,f.budget)

    def test_fresh_native_budget_must_equal_actual_grant(self):
        fixture=B1HelperTests();fixture.setUp()
        try:
            directory,identity,result=fixture.report_fixture()
            contracts,_=runner_module._b1_modules(fixture.budget)
            result['budget']['limit_seconds']=299
            raw=contracts.canonical_bytes(result)+b'\n';(directory/'run_manifest.json').write_bytes(raw)
            cp=json.loads((directory/'checkpoint.json').read_bytes());cp['result_sha256']=hashlib.sha256(raw).hexdigest()
            (directory/'checkpoint.json').write_bytes(contracts.canonical_bytes(cp)+b'\n')
            (directory/'checkpoint.sha256.json').write_bytes(contracts.canonical_bytes({'sha256':contracts.digest(cp)})+b'\n')
            work=fixture.root/'work';target=work/'reports'/'pdca'/'2000-01-01'/'runs'/contracts.digest(identity)
            target.parent.mkdir(parents=True);directory.rename(target)
            (work/'reports'/'pdca'/'2000-01-01'/'pdca_result.json').write_bytes(raw)
            binding={'master_identity':identity,'master_run_id':contracts.digest(identity),'workspace_root':str(work)}
            capture={'stdout':{'raw':raw,'complete':True},'returncode':2,'started_at_utc':'2000-01-01T00:00:00+00:00'}
            with self.assertRaises(PrivateRunError):runner_module._b2_native(capture,binding,fixture.budget,300)
            # A whole identical already-complete result is the only live exception.
            checked=runner_module._b2_native(capture,binding,fixture.budget,300,{'result':result,'checkpoint':cp})
            self.assertEqual(checked['result'],result)
        finally:fixture.doCleanups()

    def test_postwrite_fsync_and_close_failures_are_ack_unknown(self):
        class FalseyError(OSError):
            def __bool__(self):return False
        for mode in ('fsync','close'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp:
                store=Path(tmp);path=store/'terminal.json';marker=FalseyError('SYNTHETIC_POSTWRITE')
                budget=intake_module._ReadBudget(30,error_type=PrivateRunError)
                original_open=Path.open;original_fsync=os.fsync
                def synced(fd):
                    original_fsync(fd)
                    if mode=='fsync':raise marker
                class ClosingStream:
                    def __init__(self,stream):self.stream=stream
                    def __getattr__(self,name):return getattr(self.stream,name)
                    def __enter__(self):return self
                    def __exit__(self,*args):self.close()
                    def close(self):
                        self.stream.close()
                        if mode=='close':raise marker
                def opening(p,*args,**kwargs):
                    stream=original_open(p,*args,**kwargs)
                    return ClosingStream(stream) if p==path and args==('xb',) else stream
                with patch.object(Path,'open',opening),patch.object(os,'fsync',synced):
                    with self.assertRaises(FalseyError) as caught:
                        runner_module._b2_publish_terminal(store,path,{'schema':'SYNTHETIC_PHASE_ONLY'},budget)
                self.assertIs(caught.exception,marker)
                self.assertEqual(json.loads(path.read_bytes())['artifact_read_bytes'],0)
                self.assertTrue(any('COMMITTED_ACK_UNKNOWN' in n for n in getattr(marker,'__notes__',[])))

    def test_partial_terminal_never_resumed(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Path(tmp);path=store/'terminal.json';path.write_bytes(b'{')
            budget=intake_module._ReadBudget(30,error_type=PrivateRunError)
            with self.assertRaises(FileExistsError):runner_module._b2_publish_terminal(store,path,{'schema':'SYNTHETIC_PHASE_ONLY'},budget)
            self.assertEqual(path.read_bytes(),b'{')

    def test_actual_short_terminal_write_is_retained_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Path(tmp);path=store/'terminal.json';native=Path.open
            class ShortStream:
                def __init__(self,stream):self.stream=stream
                def __getattr__(self,key):return getattr(self.stream,key)
                def write(self,raw):return self.stream.write(raw[:7])
            def opening(p,*args,**kwargs):
                stream=native(p,*args,**kwargs)
                return ShortStream(stream) if p==path and args==('xb',) else stream
            with patch.object(Path,'open',opening),self.assertRaises(OSError) as caught:
                runner_module._b2_publish_terminal(store,path,{'schema':'SYNTHETIC_ONLY'},intake_module._ReadBudget(30))
            self.assertEqual(len(path.read_bytes()),7)
            self.assertTrue(any('INCOMPLETE_TERMINAL' in note for note in caught.exception.__notes__))
            self.assertFalse(any('COMMITTED_ACK_UNKNOWN' in note for note in caught.exception.__notes__))

    def test_complete_lost_ack_generation_freshly_validates_without_rewrite(self):
        f,directory,source,claim,sup,terminal,save,finish=self.failure_history()
        path=directory/'terminal.json';path.unlink();primary=OSError('SYNTHETIC_LOST_ACK');native=os.fsync
        def fsync(fd):native(fd);raise primary
        with patch.object(os,'fsync',fsync),self.assertRaises(OSError) as caught:
            runner_module._b2_publish_terminal(f.store,path,terminal,f.budget)
        self.assertIs(caught.exception,primary)
        self.assertTrue(any('COMMITTED_ACK_UNKNOWN' in n for n in primary.__notes__))
        before=(path.read_bytes(),path.stat().st_ino,path.stat().st_mtime_ns)
        value=runner_module._b2_validate_attempt(f.store,directory,source,f.budget)
        self.assertEqual(value['result']['private_status'],'FAIL')
        self.assertEqual((path.read_bytes(),path.stat().st_ino,path.stat().st_mtime_ns),before)

    def test_same_native_id_revision_collision(self):
        row={'claim':{'attempt_id':'a'*64},'binding':{'revision':'r1'},
             'terminal':{'kind':'VALIDATED_CHILD_TERMINAL','native_run_id':'b'*64}}
        with self.assertRaisesRegex(PrivateRunError,'NATIVE_NAMESPACE_ALREADY_BOUND'):
            runner_module._b2_revision_guard([row],{'revision':'r2','master_run_id':'b'*64},'c'*64)
        # A supervisor failure has no fabricated native namespace ownership.
        failed=copy.deepcopy(row);failed['terminal']={'kind':'SUPERVISOR_FAILURE','native_run_id':None}
        runner_module._b2_revision_guard([failed],{'revision':'r2','master_run_id':'b'*64},'c'*64)

    @unittest.skipIf(os.name=='posix','Actual Windows unsupported-capability control')
    def test_public_runner_blocks_real_unsupported_platform_before_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store=root/'store';work=root/'work'
            store.mkdir(mode=0o700);work.mkdir(mode=0o700)
            source=root/'synthetic.txt';source.write_text('2000/01/01 19:00\n目撃\nハブ\n',encoding='utf-8')
            code=Path(runner_module.__file__).resolve().parents[1]
            received=intake(code,store,log_file=source)
            receipt=store/'receipts'/(received['receipt_id']+'.json')
            with patch.object(runner_module.subprocess,'run',side_effect=AssertionError('unsupported engine boundary reached')):
                with self.assertRaisesRegex(PrivateRunError,'CAPABILITY'):
                    run_private(code,work,store,receipt,'2000-01-01')
            self.assertFalse((store/'private_pdca_runs').exists())


@unittest.skipUnless(os.name=='posix','Requires genuine POSIX waitid/WNOWAIT/process groups; mandatory on Ubuntu')
class B2PosixTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.store=self.root/'store';self.store.mkdir(mode=0o700)
        self.directory=self.store/'attempt';self.directory.mkdir(mode=0o700)
        self.budget=intake_module._ReadBudget(30,error_type=PrivateRunError)
        runner_module._b2_capability(self.budget)  # missing real primitives FAIL, never substitute

    def capture(self,program,seconds=5):
        now=time.monotonic()
        return runner_module._b2_capture([sys.executable,'-c',program],self.root,self.store,self.directory,
                                         self.budget,now+seconds,now+seconds+5)

    def test_simultaneous_stream_caps_and_plus_one(self):
        # Two actual child writers; no substitute process, selector or pipe reader.
        program="import os,threading\ndef out(fd):\n while True:os.write(fd,b'x'*4096)\nt=threading.Thread(target=out,args=(2,),daemon=True);t.start();out(1)"
        with patch.object(runner_module,'B2_STDOUT_BYTES',32768),patch.object(runner_module,'B2_STDERR_BYTES',32768):
            captured=self.capture(program)
        self.assertIn(captured['stop_reason'],('STDOUT_CAPACITY','STDERR_CAPACITY'))
        for name in ('stdout','stderr'):
            row=captured[name];self.assertLessEqual(row['observed_read_bytes'],32769)
            self.assertLessEqual(row['retained_size_bytes'],32768)
        selected='stdout' if captured['stop_reason']=='STDOUT_CAPACITY' else 'stderr'
        self.assertEqual(captured[selected]['observed_read_bytes'],32769)
        self.assertEqual(captured['capture_read_bytes'],sum(captured[k]['observed_read_bytes'] for k in ('stdout','stderr')))
        self.assertEqual(captured['cleanup']['direct_child'],'REAPED')
        self.assertEqual(captured['cleanup']['process_group'],'ABSENT')

    def test_fast_exit_descendant_pipes_keep_generation_until_last_signal(self):
        # Leader stays waitable while a forked descendant retains its pipes.
        captured=self.capture("import os,time\np=os.fork()\nif p==0:time.sleep(20);os._exit(0)\nos._exit(0)",seconds=.25)
        self.assertEqual(captured['stop_reason'],'OWNED_TIMEOUT')
        self.assertEqual(captured['cleanup']['direct_child'],'REAPED')
        self.assertEqual(captured['cleanup']['process_group'],'ABSENT')
        self.assertLessEqual(len(captured['cleanup']['signal_events']),2)
        with self.assertRaises(ChildProcessError):os.waitpid(captured['pid'],os.WNOHANG)

    def test_owned_timeout_reaps_without_late_signal(self):
        captured=self.capture("import time;time.sleep(20)",seconds=.2)
        self.assertEqual(captured['stop_reason'],'OWNED_TIMEOUT')
        self.assertEqual(captured['stop_origin'],'CLOSED_TIMER_OBSERVATION')
        self.assertEqual(captured['cleanup']['direct_child'],'REAPED')
        with self.assertRaises(ChildProcessError):os.waitpid(captured['pid'],os.WNOHANG)

    def test_first_and_all_local_cleanup_resources_after_selector_failure(self):
        native=runner_module.selectors.DefaultSelector;primary=KeyboardInterrupt('SYNTHETIC_FIRST')
        residual=OSError('SYNTHETIC_SELECTOR_CLOSE');events=[];actual_temp=runner_module.NamedTemporaryFile
        class ClosingSelector:
            def __init__(self):self.actual=native()
            def __getattr__(self,name):return getattr(self.actual,name)
            def select(self,*args):raise primary
            def close(self):self.actual.close();events.append('selector');raise residual
        def tempfile_created(*args,**kwargs):
            stream=actual_temp(*args,**kwargs);events.append(stream);return stream
        with patch.object(runner_module.selectors,'DefaultSelector',ClosingSelector),patch.object(runner_module,'NamedTemporaryFile',tempfile_created):
            with self.assertRaises(KeyboardInterrupt) as caught:self.capture('import time;time.sleep(20)')
        self.assertIs(caught.exception,primary);self.assertEqual(events.count('selector'),1)
        self.assertTrue(all(f.closed for f in events if f!='selector'))
        self.assertEqual(list((self.directory/'streams').iterdir()),[])
        self.assertTrue(any('SELECTOR_CLOSE_RESIDUAL' in s for s in primary.__notes__))

    def test_chmod_failure_tracks_created_temp_before_spawn(self):
        primary=OSError('SYNTHETIC_CHMOD');native=os.chmod;observed=[]
        def chmod(path,mode):
            if Path(path).name.startswith('.capture-'):
                observed.append(Path(path));raise primary
            return native(path,mode)
        with patch.object(os,'chmod',chmod),self.assertRaises(OSError) as caught:self.capture('raise SystemExit(0)')
        self.assertIs(caught.exception,primary);self.assertEqual(len(observed),1)
        self.assertFalse(observed[0].exists())

    def test_two_process_claim_race_preserves_shared_artifacts(self):
        fixture=B1HelperTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        scope,aid,source,binding=fixture.binding_fixture()
        args=fixture.root/'arguments.json';args.write_text(json.dumps([str(fixture.store),scope,aid,source,binding]))
        gate=fixture.root/'gate';scripts=Path(runner_module.__file__).parent
        code=("import json,sys,time\nfrom pathlib import Path\nsys.path.insert(0,sys.argv[1])\nimport private_pdca_runner as r\n"
              "p,scope,aid,s,b=json.loads(Path(sys.argv[2]).read_text());gate=Path(sys.argv[3])\n"
              "while not gate.exists():time.sleep(.005)\n"
              "try:r._b1_claim_files(Path(p),scope,aid,s,b,'r1',r._ReadBudget(30,error_type=r.PrivateRunError));print('WON')\n"
              "except r.PrivateRunError:print('CONFLICT')\n")
        children=[]
        try:
            for _ in range(2):children.append(subprocess.Popen([sys.executable,'-c',code,str(scripts),str(args),str(gate)],stdout=subprocess.PIPE,stderr=subprocess.PIPE))
            gate.write_bytes(b'SYNTHETIC_GO')
            values=[c.communicate(timeout=30) for c in children]
        finally:
            for c in children:
                if c.poll() is None:c.kill();c.wait(timeout=5)
        self.assertEqual(sorted(out.strip() for out,err in values),[b'CONFLICT',b'WON'])
        for c,(out,err) in zip(children,values):self.assertEqual(c.returncode,0,err.decode())
        base=fixture.store/'private_pdca_runs/v2/scopes'/scope
        self.assertEqual(json.loads((base/'source.json').read_bytes()),source)
        self.assertEqual(json.loads((base/'attempts'/aid/'binding.json').read_bytes()),binding)
        self.assertEqual((base/'active.json').read_bytes(),(base/'attempts'/aid/'claim.json').read_bytes())

    def installed_fixture(self):
        installed=self.root/'installed';installed.mkdir(mode=0o700);actual=Path(runner_module.__file__).resolve().parents[1]
        paths=[]
        for folder,suffix in (('src','.py'),('scripts','.py'),('schemas','.json')):
            (installed/folder).mkdir()
            paths.extend(p for p in (actual/folder).rglob('*'+suffix) if '__pycache__' not in p.parts)
        paths.extend(actual/name for name in ('requirements-analysis.txt','requirements-osm.txt'))
        rows=[]
        for path in sorted(paths):
            relative=path.relative_to(actual);dest=installed/relative;dest.parent.mkdir(parents=True,exist_ok=True)
            raw=path.read_bytes();dest.write_bytes(raw);rows.append(dict(path=relative.as_posix(),sha256=hashlib.sha256(raw).hexdigest()))
        policy_path=Path('protocols/development/g0-policy-v1.json');policy=(actual/policy_path).read_bytes()
        (installed/policy_path).parent.mkdir(parents=True);(installed/policy_path).write_bytes(policy)
        # A visibly synthetic fixture cycle declares the complete actual selected code.
        relative='protocols/development/cycles/SYNTHETIC_B2_TEST.json'
        body=dict(schema_version='habu-codex-cycle-v1',kind='DEVELOPMENT_CONTRACT_ONLY',cycle_id='SYNTHETIC_B2_TEST',
                  base_main_sha='0'*40,frozen_at='2000-01-01T00:00:00+00:00',
                  policy_ref=dict(path=policy_path.as_posix(),sha256=hashlib.sha256(policy).hexdigest()),code_manifest=rows)
        raw=json.dumps(body,sort_keys=True,separators=(',',':')).encode()+b'\n'
        dest=installed/relative;dest.parent.mkdir();dest.write_bytes(raw)
        (installed/'protocols/development/current-cycle.json').write_text(json.dumps(dict(path=relative,sha256=hashlib.sha256(raw).hexdigest())))
        return installed

    def test_genuine_canonical_missing_data_blocked_and_reuse_engine_zero(self):
        installed=self.installed_fixture();work=self.root/'workspace';work.mkdir(mode=0o700)
        source=self.root/'SYNTHETIC_ONLY.txt';source.write_text('2000/01/01 19:00\n目撃\nハブ\n',encoding='utf-8')
        receipt=intake(installed,self.store,log_file=source);path=self.store/'receipts'/(receipt['receipt_id']+'.json')
        # The real installed runner imports the real POSIX engine; no fcntl facade.
        program=("import json,sys\nfrom pathlib import Path\nsys.path.insert(0,sys.argv[1]+'/scripts')\n"
                 "from private_pdca_runner import run_private\n"
                 "print(json.dumps(run_private(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]),Path(sys.argv[4]),'2000-01-01',60)))")
        argv=[sys.executable,'-c',program,str(installed),str(work),str(self.store),str(path)]
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
        first=subprocess.run(argv,capture_output=True,timeout=75,env=env)
        self.assertEqual(first.returncode,0,first.stderr.decode())
        result=json.loads(first.stdout);self.assertEqual(result['backend_status'],'BLOCKED')
        self.assertEqual(result['private_status'],'BLOCKED')
        for name in runner_module.B2_FLAGS:self.assertIs(result[name],False)
        base=self.store/'private_pdca_runs/v2/scopes'/result['scope_id']
        directory=base/'attempts'/result['attempt_id'];sup=json.loads((directory/'supervisor.json').read_bytes())
        self.assertEqual(sup['cleanup']['direct_child'],'REAPED');self.assertEqual(sup['report_validation']['status'],'VALIDATED')
        before={p:(p.read_bytes(),p.stat().st_mtime_ns) for root in (base,work/'reports') for p in root.rglob('*') if p.is_file()}
        second=subprocess.run(argv,capture_output=True,timeout=75,env=env)
        self.assertEqual(second.returncode,0,second.stderr.decode());self.assertEqual(json.loads(second.stdout),result)
        after={p:(p.read_bytes(),p.stat().st_mtime_ns) for root in (base,work/'reports') for p in root.rglob('*') if p.is_file()}
        self.assertEqual(before,after)  # actual immutable native/stream/terminal generation, engine0


class B1HelperTests(unittest.TestCase):
    def test_b1_report_growth_after_outer_size_check_is_rejected(self):
        directory,identity,result=self.report_fixture(growing_report=True)
        extra=directory/'zz-generated.bin';native=runner_module._b1_file_ref;changed=[]
        cap=sum(p.stat().st_size for p in directory.rglob('*') if p.is_file() and p!=directory/'snapshot'/'data'/'a')
        def growing(path,*args,**kwargs):
            if Path(path)==extra and not changed:
                extra.write_bytes(b'B'*1000);changed.append(True)
            return native(path,*args,**kwargs)
        with patch.object(runner_module,'B1_MAX_REPORT',cap),patch.object(runner_module,'_b1_file_ref',growing):
            with self.assertRaises(PrivateRunError):runner_module._b1_report(directory,identity,self.budget)
        self.assertEqual(changed,[True])

    def test_b1_code_growth_after_aggregate_precheck_is_rejected(self):
        for folder in ('src','scripts','schemas'):(self.view/folder).mkdir()
        for i in range(4):
            with (self.view/'src'/('synthetic'+str(i)+'.py')).open('wb') as stream:
                stream.truncate(4*1024*1024)
        for name in ('requirements-analysis.txt','requirements-osm.txt'):(self.view/name).write_bytes(b'')
        target=self.view/'requirements-osm.txt';native=runner_module._b1_file_ref;changed=[]
        def growing(path,*args,**kwargs):
            if Path(path)==target and not changed:
                target.write_bytes(b'x');changed.append(True)
            return native(path,*args,**kwargs)
        with patch.object(runner_module,'_b1_file_ref',growing),self.assertRaises(PrivateRunError):
            runner_module._b1_view(self.view,self.budget,code=True)
        self.assertEqual(changed,[True])

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

    def report_fixture(self, *, bool_size=False, growing_report=False):
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
        if growing_report:
            (directory/'zz-generated.bin').write_bytes(b'A')
            outputs['zz-generated.bin']=hashlib.sha256(b'B'*1000).hexdigest()
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
    def preflight(self,budget=None):
        if budget is None:budget=intake_module._ReadBudget(30,error_type=PrivateRunError)
        runner_module._guard_private_path(self.store,self.store/'private_pdca_runs')
        rid,rows=runner_module._receipt_sources(self.rec,self.store,budget)
        for row in rows:
            target=self.workspace/'incoming'/'private_pdca'/(row['sha256']+('.txt' if row['type']=='log' else '.gpx'))
            runner_module._copy_verified(Path(row['private_archive']),target,row['sha256'],self.workspace,budget,row['size_bytes'])
        return rid,rows

    def test_bounded_receipt_decoder_rejects_excessive_integer_and_nesting(self):
        for raw in (b'{"n":'+b'9'*5000+b'}', b'['*65+b'0'+b']'*65):
            with self.subTest(prefix=raw[:8]):
                self.rec.write_bytes(raw)
                with patch.object(runner_module.subprocess, 'run', side_effect=AssertionError('engine forbidden')):
                    with self.assertRaises(PrivateRunError):
                        self.preflight()

    def test_same_whole_entry_clock_covers_receipt_then_copy(self):
        budget=intake_module._ReadBudget(1,error_type=PrivateRunError);deadline=budget.deadline
        actual=Path.open
        def opening(path,*args,**kwargs):
            stream=actual(path,*args,**kwargs)
            if path==self.rec:time.sleep(.02)
            return stream
        with patch.object(Path,'open',opening):self.preflight(budget)
        self.assertEqual(budget.deadline,deadline)
        self.assertGreater(deadline-time.monotonic(),0)
        self.assertLess(deadline-time.monotonic(),.99)

    def test_receipt_copy_and_readback_share_actual_ledger(self):
        budget=intake_module._ReadBudget(30,error_type=PrivateRunError)
        self.preflight(budget)
        self.assertEqual(budget.bytes_read,self.rec.stat().st_size+4*self.source.stat().st_size)

    def test_oversized_existing_inbox_is_rejected_without_engine(self):
        digest = self.manifest['sources'][0]['sha256']
        target = self.workspace/'incoming'/'private_pdca'/(digest+'.txt')
        target.parent.mkdir(parents=True)
        target.write_bytes(self.source.read_bytes()+b' ')
        with patch.object(runner_module.subprocess, 'run', side_effect=AssertionError('engine forbidden')):
            with self.assertRaises(PrivateRunError):
                self.preflight()

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
                    self.preflight()
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
                self.preflight(intake_module._ReadBudget(.005,error_type=PrivateRunError))

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
                if selected_parent=='private_pdca':self.preflight()
                else:
                    self.preflight()
                    target=self.store/'private_pdca_runs'/'SYNTHETIC_HELPER_ONLY.json';target.parent.mkdir()
                    runner_module._b1_publish(self.store,target,b'{}',intake_module._ReadBudget(30,error_type=PrivateRunError))
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

    def test_owned_inbox_and_bounded_metadata_temps_are_removed_normally(self):
        self.preflight()
        budget=intake_module._ReadBudget(30,error_type=PrivateRunError)
        target=self.store/'private_pdca_runs'/'SYNTHETIC_HELPER_ONLY.json';target.parent.mkdir()
        runner_module._b1_publish(self.store,target,b'{"SYNTHETIC_ONLY":true}',budget)
        digest=self.manifest['sources'][0]['sha256']
        self.assertEqual([p.name for p in (self.workspace/'incoming'/'private_pdca').iterdir()],[digest+'.txt'])
        self.assertEqual([p.name for p in target.parent.iterdir()],[target.name])

    def assert_bad_receipt(self, manifest):
        self.rec.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(PrivateRunError):
            self.preflight()

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
        legacy_id=hashlib.sha256(json.dumps(self.manifest['sources'],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        self.assertEqual(self.manifest['receipt_id'],legacy_id)
        receipt_before,source_before=self.rec.read_bytes(),self.source.read_bytes()
        self.preflight()
        self.assertEqual(self.rec.read_bytes(),receipt_before);self.assertEqual(self.source.read_bytes(),source_before)

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
        gpx=self.base/'synthetic.gpx';gpx.write_text('<gpx creator="SYNTHETIC_TEST_ONLY"/>',encoding='utf-8')
        received=intake(self.code,self.store,log_file=self.source,gpx_file=gpx)
        receipt=self.store/'receipts'/(received['receipt_id']+'.json');before=receipt.read_bytes()
        rid,rows=runner_module._receipt_sources(receipt,self.store,intake_module._ReadBudget(30,error_type=PrivateRunError))
        self.assertEqual(len(rows),2);self.assertEqual(rid,received['receipt_id']);self.assertEqual(receipt.read_bytes(),before)

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
            self.preflight()
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.workspace / "incoming").exists())

    def test_result_parent_symlink_cannot_escape_private_store(self):
        self.result_alias_rejected()

    def test_result_parent_junction_cannot_escape_private_store(self):
        self.result_alias_rejected(junction=True)

    def test_existing_metadata_leaf_symlink_is_not_reused(self):
        dest=self.store/'private_pdca_runs'/'SYNTHETIC_HELPER_ONLY.json';dest.parent.mkdir()
        outside=self.code/'synthetic-receipt.json';outside.write_bytes(b'SYNTHETIC_UNOWNED')
        try:dest.symlink_to(outside)
        except (OSError,NotImplementedError) as exc:self.skipTest('Actual symlink unavailable: '+str(exc))
        with self.assertRaises(PrivateRunError):
            runner_module._b1_publish(self.store,dest,b'{}',intake_module._ReadBudget(30,error_type=PrivateRunError))
        self.assertEqual(outside.read_bytes(),b'SYNTHETIC_UNOWNED')

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

    def test_repeated_verified_copy_preserves_one_inbox_and_source(self):
        self.preflight();target=self.workspace/'incoming'/'private_pdca'/(self.manifest['sources'][0]['sha256']+'.txt')
        before=(target.read_bytes(),target.stat().st_ino,target.stat().st_mtime_ns)
        self.preflight()
        self.assertEqual((target.read_bytes(),target.stat().st_ino,target.stat().st_mtime_ns),before)
        self.assertEqual(len(list(target.parent.iterdir())),1)

    def test_modified_original_rejected(self):
        self.source.write_text("tampered")
        with self.assertRaises(PrivateRunError):
            self.preflight()

    def test_private_path_cannot_be_public_repo(self):
        with self.assertRaises(PrivateRunError):runner_module._validate_roots(self.code,self.code,self.store)

    def test_bad_night_rejected(self):
        contracts,_=runner_module._b1_modules(intake_module._ReadBudget(30,error_type=PrivateRunError))
        with self.assertRaises(ValueError):contracts.validate_night('2026-10-26;rm')

    def test_symlink_to_external_raw_rejected(self):
        outside = self.workspace / "outside.txt"
        outside.write_bytes(self.source.read_bytes())
        self.source.unlink()
        try:
            self.source.symlink_to(outside)
        except (OSError, NotImplementedError) as exc:
            self.skipTest("Actual symlink unavailable without elevation: " + str(exc))
        with self.assertRaises(PrivateRunError):
            self.preflight()

    def test_pure_native_pass_remains_private_partial_without_permissions(self):
        supervisor=dict(report_validation=dict(native_result_ref={'SYNTHETIC_ONLY':True},report_view_sha256='a'*64),
                        stop_reason='NATIVE_EXIT',stop_origin='NONE')
        native=dict(overall_status='PASS',run_id='b'*64,completed=True)
        result=runner_module._b2_private_result('c'*64,'d'*64,'e'*64,{},supervisor,native)
        self.assertEqual(result['private_status'],'PARTIAL')
        for name in runner_module.B2_FLAGS:self.assertIs(result[name],False)


if __name__ == "__main__":
    unittest.main()
