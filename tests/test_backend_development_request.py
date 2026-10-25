"""Real local Git with explicitly synthetic terminal proof; no admitted jobs."""
import copy
import hashlib
import importlib.util
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import pdca_bridge as bridge
from master_contracts import canonical_bytes,digest

PARENT='src/research_pdca_adapter.py'
ADAPTER='src/evaluation/stage1_source_adapter.py'
PROTOCOL='schemas/development-job.json'


def sha(raw): return hashlib.sha256(raw).hexdigest()
def ref(path,raw): return dict(path=path,sha256=sha(raw),size_bytes=len(raw))


def legacy_adapter_source():
    # This closed legacy profile uses historical native LF code bytes, not the
    # current adapter API. Restore text-fixture checkout newlines only; no Raw.
    raw=(ROOT/'tests/fixtures/stage1_source_adapter_388bf18.py.txt').read_text(encoding='utf-8').encode()
    if (len(raw)!=37345 or
            sha(raw)!='388bf18b1f4f90fb29d48fe0c4f58579bae925d281f99b27eb0e79baa038ada6'):
        raise AssertionError('Immutable historical Stage1 adapter fixture changed')
    return raw


class BackendDevelopmentRequestTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('backend_development_request'),
            'Missing bounded command-scoped backend request emitter')
        import backend_development_request
        self.module=backend_development_request
        self.tmp=tempfile.TemporaryDirectory(prefix='habu-emission-')
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name); self.root=self.base/'repo'; self.root.mkdir()
        self.remote=self.base/'origin.git'
        self.git('init','--bare',str(self.remote),root=self.base)
        self.git('init'); self.git('config','core.longpaths','true')
        self.git('config','user.name','Synthetic emission test')
        self.git('config','user.email','emission@example.invalid')
        self.source_files={
            # Readable code fixture, reconstructed as native LF text; never Raw.
            PARENT:(ROOT/'tests/fixtures/research_parent_v3_5d4b84f.py.txt').read_text(encoding='utf-8').encode(),
            ADAPTER:legacy_adapter_source(),
            PROTOCOL:subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:'+PROTOCOL]),
        }
        for path,raw in self.source_files.items():
            target=self.root/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
        self.git('add','.'); self.git('commit','-m','Synthetic pinned source profiles')
        self.git('branch','-M','main'); self.git('remote','add','origin',str(self.remote))
        self.git('push','origin','main'); self.source=self.git('rev-parse','HEAD').decode().strip()
        self.transport=bridge.GitTransport(self.root)
        issue=dict(number=1,state='open',title='[HABU PDCA] 2026-10-25',
            body='Synthetic command. root_command_id=ignored',user={'login':'haji84'})
        self.command=bridge.authorize_command('haji84/habuAI-private',issue)
        self.run_id='a'*64; night=self.command['night']
        self.prefix=f'reports/pdca/{night}/runs/{self.run_id}/'
        inventory={p:dict(sha256=sha(raw),size_bytes=len(raw)) for p,raw in self.source_files.items()}
        self.evidence=dict(entries=[dict(path=p,**info) for p,info in inventory.items()],input_snapshot_sha256=digest(inventory))
        self.checkpoint=dict(run_id=self.run_id,outputs={'stages/development.json':'b'*64},elapsed_seconds=.25)
        self.result=dict(run_id=self.run_id,overall_status='BLOCKED',completed=False,
            checkpoint_sha256=digest(self.checkpoint),input_manifest_sha256=digest(self.evidence))
        files={self.prefix+'finalization_checkpoint.json':canonical_bytes(self.checkpoint)+b'\n',
            self.prefix+'evidence_manifest.json':canonical_bytes(self.evidence)+b'\n',
            self.prefix+'run_manifest.json':canonical_bytes(self.result)+b'\n'}
        self.manifest=dict(schema_version='1.0',night=night,run_id=self.run_id,source_commit=self.source,
            identity=dict(inputs=inventory,policy={'stage1_recall_minimum':.9}),sources=[dict(path=p,**info,origin='commit') for p,info in inventory.items()],
            files=[ref(p,raw) for p,raw in sorted(files.items())])
        self.manifest_path=f'reports/pdca/{night}/bridge/recovery-{self.run_id}.json'
        files[self.manifest_path]=canonical_bytes(self.manifest)+b'\n'
        self.bundle=self.transport.publish('pdca/run-'+self.run_id,self.source,None,files)
        self.receipt=dict(schema_version='1.0',state='COMPUTED',command=self.command,
            source_commit=self.source,command_source_commit=self.source,run_id=self.run_id,
            run_branch='pdca/run-'+self.run_id,bundle_commit=self.bundle,
            result_sha256=sha(files[self.prefix+'run_manifest.json']),max_budget_seconds=300,
            ledger_elapsed=.25,scientific_status='BLOCKED',completed=False)
        self.branch='pdca/command-'+self.command['command_id']
        self.command_path=f'reports/pdca/{night}/bridge/command-{self.command["command_id"]}.json'
        self.head=self.transport.publish(self.branch,self.source,None,
            {self.command_path:canonical_bytes(dict(self.receipt,state='RUNNING'))+b'\n'})
        self.api=type('SyntheticAPI',(),{'default_source':lambda obj:self.source})()

    def git(self,*args,root=None):
        return subprocess.check_output(['git','-C',str(root or self.root),*args],stderr=subprocess.PIPE)

    def proof(self):
        # Explicit synthetic unit seam. Genuine engine/authorization is POSIX E2E.
        return patch.object(bridge,'verify_handled_receipt',return_value=copy.deepcopy(self.result))

    def prepare(self,**changes):
        args=dict(trusted_default_source=self.source,observed_at='2026-10-25T10:00:00+00:00')
        args.update(changes)
        with self.proof():
            return self.module.prepare_backend_development_request(self.transport,self.command,self.receipt,**args)

    def emit(self,**changes):
        args=dict(expected_head=self.head,observed_at='2026-10-25T10:00:00+00:00')
        args.update(changes)
        with self.proof():
            return self.module.emit_backend_development_request(self.transport,self.api,self.command,self.receipt,**args)

    def test_known_profile_emits_only_fixed_implementation_completeness(self):
        value=self.prepare(); self.assertEqual(value['status'],'DECLARED_SCOPE_PROPOSAL')
        record=value['record']; request=record['decision']['request']
        self.assertEqual(request['purpose'],'IMPLEMENTATION_COMPLETENESS')
        self.assertEqual(request['provenance']['root_command_id'],self.command['command_id'])
        self.assertEqual(request['provenance']['parent_run_id'],self.run_id)
        self.assertEqual(request['provenance']['source_commit'],self.source)
        self.assertEqual(request['provenance']['protocol_sha256'],sha(self.source_files[PROTOCOL]))
        self.assertEqual(request['provenance']['evidence'][0]['path'],self.prefix+'finalization_checkpoint.json')
        self.assertEqual(len(request['allowed_paths']),4)
        self.assertEqual(record['protocol']['kind'],'ENGINEERING_REQUEST_CONTRACT_V1')
        self.assertEqual(self.module.inspect_backend_development_record(record),record)
        for name in self.module.FLAGS:
            self.assertIs(record[name],False); self.assertIs(request[name],False)

    def test_default_advance_does_not_reinterpret_old_run_or_open_payload(self):
        with patch.object(self.transport,'read',side_effect=AssertionError('stale payload')):
            value=self.prepare(trusted_default_source='f'*40)
        self.assertIsNone(value['record']); self.assertEqual(value['status'],'SOURCE_RECONCILIATION_REQUIRED')

    def test_unknown_same_marker_source_never_falls_back_to_v3_blocker(self):
        raw=self.source_files[PARENT]+b'\n# habu-research-model-request-v4 IMPLEMENTATION_BLOCKED\n'
        (self.root/PARENT).write_bytes(raw); self.git('add',PARENT); self.git('commit','-m','Unknown software')
        newer=self.git('rev-parse','HEAD').decode().strip()
        changed=dict(self.receipt,source_commit=newer)
        with self.proof():
            value=self.module.prepare_backend_development_request(self.transport,self.command,changed,
                trusted_default_source=newer,observed_at='2026-10-25T10:00:00+00:00')
        self.assertIsNone(value['record']); self.assertEqual(value['status'],'UNMAPPED_SOURCE_PROFILE')

    def test_reviewed_v4_profile_never_reopens_implemented_capability(self):
        raw=subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:'+PARENT])
        self.assertEqual(sha(raw),'1892440621057125b40adfef09a583395a744e505a3cc5fff657fa0f2db2fcc9')
        (self.root/PARENT).write_bytes(raw)
        self.git('add',PARENT); self.git('commit','-m','Reviewed configured parent v4')
        newer=self.git('rev-parse','HEAD').decode().strip()
        changed=dict(self.receipt,source_commit=newer,command_source_commit=newer)
        with patch.object(bridge,'verify_handled_receipt',side_effect=AssertionError('No proposal needs terminal evidence')):
            value=self.module.prepare_backend_development_request(self.transport,self.command,changed,
                trusted_default_source=newer,observed_at='2026-10-25T10:00:00+00:00')
        self.assertEqual(value['status'],'ALREADY_IMPLEMENTED'); self.assertIsNone(value['record'])
        for name in self.module.FLAGS: self.assertIs(value[name],False)

    def test_noncannonical_repo_retains_ordinary_receipt_without_io(self):
        command=dict(self.command,repository='owner/repo')
        with patch.object(self.transport,'git',side_effect=AssertionError('ordinary I/O')):
            head,value=self.module.emit_backend_development_request(self.transport,self.api,command,self.receipt,
                expected_head=self.head,observed_at='2026-10-25T10:00:00+00:00')
        self.assertEqual((head,value),(self.head,self.receipt))

    def test_rehashed_scope_root_protocol_and_boolean_forgery_rejected(self):
        record=self.prepare()['record']
        for path,replacement in ((('binding','command','command_id'),'c'*64),
                (('protocol','ref','sha256'),'c'*64),(('execution_authorized',),0),
                (('decision','request','allowed_paths'),['src/pdca_bridge.py'])):
            bad=copy.deepcopy(record); target=bad
            for key in path[:-1]: target=target[key]
            target[path[-1]]=replacement
            with self.subTest(path=path),self.assertRaises(ValueError):
                self.module.inspect_backend_development_record(bad)

    def test_publication_atomically_binds_ref_and_reuses_identical_expiry(self):
        head,receipt=self.emit(); reference=receipt['development_request_ref']
        raw=self.transport.read(head,reference['path'])
        self.assertEqual(sha(raw),reference['sha256']); self.assertEqual(len(raw),reference['size_bytes'])
        self.assertEqual(raw,canonical_bytes(json.loads(raw))+b'\n')
        actual=json.loads(self.transport.read(head,self.command_path))
        self.assertEqual(actual,receipt)
        self.receipt=receipt; self.head=head
        after,value=self.emit(observed_at='2026-10-28T10:00:00+00:00')
        self.assertEqual((after,value),(head,receipt))
        self.assertEqual(self.transport.read(after,reference['path']),raw)

    def test_successful_push_lost_reply_reconciles_same_actual_pair(self):
        original=bridge.GitTransport.publish
        def lost(instance,*args,**kwargs):
            original(instance,*args,**kwargs); raise OSError('Synthetic lost reply after actual push')
        with patch.object(bridge.GitTransport,'publish',lost): head,receipt=self.emit()
        self.assertEqual(self.transport.head(self.branch),head)
        self.assertIn('development_request_ref',receipt)

    def test_push_failure_keeps_run_and_never_returns_unpersisted_ref(self):
        with patch.object(bridge.GitTransport,'publish',side_effect=OSError('Synthetic prepush failure')):
            with self.assertRaises(bridge.RecoveryBlocked): self.emit()
        self.assertEqual(self.transport.head(self.branch),self.head)
        self.assertEqual(self.transport.head('pdca/run-'+self.run_id),self.bundle)

    def test_existing_handled_pair_never_downgrades_to_computed(self):
        head,receipt=self.emit(); handled=dict(receipt,state='HANDLED')
        actual=self.transport.publish(self.branch,self.source,head,
            {self.command_path:canonical_bytes(handled)+b'\n'})
        self.head=head; self.receipt=receipt
        after,value=self.emit()
        self.assertEqual((after,value),(actual,handled))

    def test_existing_pair_cannot_replace_verified_science_with_forged_summary(self):
        head,receipt=self.emit()
        for changes in (dict(scientific_status='PASS',completed=True,ledger_elapsed=0),
                dict(completed=0),dict(max_budget_seconds=True)):
            bad=dict(receipt,**changes)
            head=self.transport.publish(self.branch,self.source,head,
                {self.command_path:canonical_bytes(bad)+b'\n'})
            self.head=head; self.receipt=receipt
            with self.subTest(changes=changes),self.assertRaises(ValueError): self.emit()

    def test_existing_pair_still_calls_actual_terminal_verifier_before_reuse(self):
        head,receipt=self.emit(); self.head=head; self.receipt=receipt
        with patch.object(bridge,'verify_handled_receipt',side_effect=ValueError('actual terminal contradiction')):
            with self.assertRaisesRegex(ValueError,'actual terminal contradiction'):
                self.module.emit_backend_development_request(self.transport,self.api,self.command,self.receipt,
                    expected_head=head,observed_at='2026-10-25T10:00:00+00:00')

    def test_raw_tamper_restored_current_still_fails_immutable_path_history(self):
        head,receipt=self.emit(); reference=receipt['development_request_ref']
        raw=self.transport.read(head,reference['path'])
        first=self.transport.publish(self.branch,self.source,head,{reference['path']:raw+b' '})
        self.transport.publish(self.branch,self.source,first,{reference['path']:raw})
        with self.assertRaises(ValueError):
            self.module.verify_backend_development_request(self.transport,self.command,receipt)

    def test_ref_path_and_oversize_reject_before_payload(self):
        head,receipt=self.emit(); reference=receipt['development_request_ref']
        bad=dict(receipt,development_request_ref=dict(reference,path='reports/foreign.json'))
        with patch.object(bridge.GitTransport,'read',side_effect=AssertionError('bad ref payload')):
            with self.assertRaises(ValueError):
                self.module.verify_backend_development_request(self.transport,self.command,bad)
        self.transport.publish(self.branch,self.source,head,{reference['path']:b' '*(1048576+1)})
        with patch.object(bridge.GitTransport,'read',side_effect=AssertionError('oversize payload')):
            with self.assertRaises(ValueError):
                self.module.verify_backend_development_request(self.transport,self.command,receipt)


@unittest.skipUnless(os.name=='posix','Genuine POSIX bridge engine required; no fcntl facade')
class ActualBackendEmissionTests(unittest.TestCase):
    """Synthetic owner API, actual scientific engine/checkpoints and native Git."""
    def setUp(self):
        from test_master_e2e import BridgeTests
        self.helper=BridgeTests('runTest'); self.helper.setUp()
        self.addCleanup(self.helper.doCleanups)
        self.root,self.transport,_=self.helper.repository()
        shutil.copytree(ROOT/'schemas',self.root/'schemas')
        legacy=(ROOT/'tests/fixtures/research_parent_v3_5d4b84f.py.txt').read_text(encoding='utf-8').encode()
        (self.root/PARENT).write_bytes(legacy)
        (self.root/ADAPTER).write_bytes(legacy_adapter_source())
        self.helper.git(self.root,'add','.')
        self.helper.git(self.root,'-c','user.name=Test','-c','user.email=test@example.invalid',
            'commit','-m','Pinned actual legacy source and engineering schema')
        self.helper.git(self.root,'push','origin','main')
        source=self.helper.git(self.root,'rev-parse','HEAD').strip()
        class SyntheticOwnerAPI:
            def default_source(obj): return source
            def issue(obj,number):
                return dict(number=number,state='open',title='[HABU PDCA] 2026-09-28',
                    body='Synthetic ordinary owner command; root_command_id=ignored',user={'login':'haji84'})
            def ensure_pr(obj,branch,night): return 'https://example.invalid/synthetic-report'
            def upsert_comment(obj,*args): pass
            def mark_handled(obj,*args): pass
        self.api=SyntheticOwnerAPI()

    def test_real_engine_emits_and_handled_restart_never_refits_or_refreshes(self):
        first=bridge.execute_command(self.root,'haji84/habuAI-private',1,self.api,self.transport,'actual-one')
        self.assertEqual(first['state'],'HANDLED'); self.assertIn('development_request_ref',first)
        from backend_development_request import verify_backend_development_request
        record=verify_backend_development_request(self.transport,first['command'],first)
        self.assertEqual(record['decision']['request']['purpose'],'IMPLEMENTATION_COMPLETENESS')
        for key,value in record.items():
            if key.endswith('_authorized') or key.endswith('_authenticated'): self.assertIs(value,False)
        with patch.object(bridge,'run_local',side_effect=AssertionError('HANDLED refit')):
            again=bridge.execute_command(self.root,'haji84/habuAI-private',1,self.api,self.transport,'actual-retry')
        self.assertEqual(again,first)

    def test_two_ordinary_roots_share_science_but_keep_distinct_requests(self):
        first=bridge.execute_command(self.root,'haji84/habuAI-private',1,self.api,self.transport,'actual-one')
        with patch.object(bridge,'run_local',side_effect=AssertionError('Shared run refit')):
            second=bridge.execute_command(self.root,'haji84/habuAI-private',2,self.api,self.transport,'actual-two')
        self.assertEqual(first['run_id'],second['run_id'])
        self.assertNotEqual(first['command']['command_id'],second['command']['command_id'])
        self.assertNotEqual(first['development_request_ref']['path'],second['development_request_ref']['path'])
        from backend_development_request import verify_backend_development_request
        for receipt in (first,second):
            value=verify_backend_development_request(self.transport,receipt['command'],receipt)
            self.assertEqual(value['binding']['parent_run_id'],first['run_id'])
            self.assertEqual(value['decision']['request']['provenance']['root_command_id'],receipt['command']['command_id'])


if __name__=='__main__': unittest.main()
