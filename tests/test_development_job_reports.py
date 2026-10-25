"""Actual local bare-Git mechanics with synthetic unauthenticated jobs."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path[:0] = [str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
import development_job_ledger as jobs
from test_development_job_ledger import request,clock
try:
    import development_job_reports as reports
except ModuleNotFoundError as exc:
    if exc.name != 'development_job_reports': raise
    reports = None


def ledger(): return jobs.new_development_job(request())
def start(value, **changes):
    args = dict(kind='START',request=request(),now=clock(),lease_until=clock(600))
    args.update(changes)
    return jobs.append_development_job(value,expected_tip=value['tip_sha256'],transition=args)


class JobReportRecordTests(unittest.TestCase):
    def test_fixed_canonical_records_bind_full_proposal_without_authority(self):
        self.assertIsNotNone(reports,'fixed development report publisher missing')
        value = start(ledger())
        branch,prefix,files = reports._publication_records(value,'a'*40)
        job = value['origin']['job_id']
        self.assertEqual(branch,'pdca/development-'+job)
        self.assertEqual(prefix,f'reports/pdca/2026-10-25/bridge/development/{job}/')
        self.assertEqual(len(files),3)
        state = json.loads(files[prefix+'state.json'])
        self.assertEqual(state['proposal'],value)
        for flag in jobs.FLAGS: self.assertIs(state[flag],False)
        self.assertEqual(state['proposal_sha256'],jobs.digest(value))
        self.assertNotEqual(state['origin_record_sha256'],hashlib.sha256(files[prefix+'origin.json']).hexdigest())
        for raw in files.values():
            self.assertTrue(raw.endswith(b'\n'))
            self.assertEqual(raw,jobs.canonical_bytes(json.loads(raw))+b'\n')


class ActualJobReportGitTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(reports,'fixed development report publisher missing')
        self.directory = tempfile.TemporaryDirectory(prefix='habu-job-report-test-')
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name)
        self.checkout,self.remote = self.base/'checkout',self.base/'remote.git'
        self.checkout.mkdir()
        self.git('init','--bare',str(self.remote),root=self.base)
        self.git('init'); self.git('config','user.name','Synthetic job test')
        self.git('config','user.email','job@example.invalid')
        (self.checkout/'trusted.txt').write_bytes(b'Synthetic source\n')
        self.git('add','trusted.txt'); self.git('commit','-m','Synthetic source')
        self.git('branch','-M','main'); self.git('remote','add','origin',str(self.remote))
        self.git('push','-u','origin','main')
        self.source = self.git('rev-parse','HEAD').decode().strip()
        from pdca_bridge import GitTransport
        self.transport = GitTransport(self.checkout)

    def git(self,*args,root=None):
        return subprocess.check_output(['git','-C',str(root or self.checkout),*args],stderr=subprocess.PIPE)

    def publish(self,value,head=None,tip=None,**changes):
        args = dict(root_report_source_commit=self.source,expected_remote_head=head,
            expected_tip=tip or value['tip_sha256'])
        args.update(changes)
        return reports.publish_development_job(self.checkout,value,**args)

    def bootstrap(self):
        value=ledger(); receipt=self.publish(value)
        return value,receipt

    def append(self,value,receipt,kind,**changes):
        child=jobs.append_development_job(value,expected_tip=value['tip_sha256'],transition=dict(kind=kind,**changes))
        return child,self.publish(child,receipt['observed_head'],value['tip_sha256'])

    def test_real_bootstrap_append_and_reconstructed_clean_transport(self):
        value,boot=self.bootstrap(); child=start(value)
        done=self.publish(child,boot['observed_head'],value['tip_sha256'])
        restored=json.loads(json.dumps(child))
        again=self.publish(restored,boot['observed_head'],value['tip_sha256'])
        self.assertEqual(again['observed_head'],done['observed_head'])
        self.assertEqual(again['latest_ledger'],child)
        self.assertEqual(again['status'],'TRANSPORT_ACK_ONLY')
        self.assertGreater(again['actual_blob_bytes_read'],0)
        for flag in jobs.FLAGS: self.assertIs(again[flag],False)

    def test_two_real_sibling_writers_cannot_claim_one_predecessor(self):
        value,boot=self.bootstrap(); first=start(value)
        second=start(value,request=request(source_commit='b'*40))
        winner=self.publish(first,boot['observed_head'],value['tip_sha256'])
        with self.assertRaises(ValueError): self.publish(second,boot['observed_head'],value['tip_sha256'])
        observed=self.publish(first,winner['observed_head'],first['tip_sha256'])
        self.assertEqual(observed['latest_ledger'],first)

    def test_native_after_preparation_race_preserves_other_checkout_winner(self):
        value,boot=self.bootstrap(); first=start(value)
        second=start(value,request=request(source_commit='b'*40))
        clone=self.base/'second-checkout'; self.git('clone',str(self.remote),str(clone),root=self.base)
        from pdca_bridge import GitTransport
        other=GitTransport(clone)
        branch,_,files=reports._publication_records(second,self.source)
        prefix=reports._publication_records(second,self.source)[1]
        event=second['events'][-1]
        selected={prefix+'state.json':files[prefix+'state.json'],
            prefix+f"events/0001-{event['event_sha256']}.json":files[prefix+f"events/0001-{event['event_sha256']}.json"]}
        original=GitTransport.publish; injected=[False]
        def race(instance,*args,**kwargs):
            if not injected[0]:
                injected[0]=True
                original(other,branch,self.source,boot['observed_head'],selected)
            return original(instance,*args,**kwargs)
        with patch.object(GitTransport,'publish',race),self.assertRaises(ValueError):
            self.publish(first,boot['observed_head'],value['tip_sha256'])
        observed=self.publish(second,boot['observed_head'],value['tip_sha256'])
        self.assertEqual(observed['latest_ledger'],second)

    def test_ambiguous_actual_push_is_reconciled_without_duplicate_commit(self):
        value,boot=self.bootstrap(); child=start(value)
        from pdca_bridge import GitTransport
        original=GitTransport.publish
        def lost(instance,*args,**kwargs):
            original(instance,*args,**kwargs)
            raise OSError('Synthetic lost reply after actual push')
        with patch.object(GitTransport,'publish',lost):
            done=self.publish(child,boot['observed_head'],value['tip_sha256'])
        again=self.publish(child,boot['observed_head'],value['tip_sha256'])
        self.assertEqual(done['observed_head'],again['observed_head'])

    def test_old_prefix_ack_returns_latest_expired_accounting_never_old_live_lease(self):
        value,boot=self.bootstrap(); active=start(value)
        receipt=self.publish(active,boot['observed_head'],value['tip_sha256'])
        attempt=jobs.inspect_development_job(active)['attempts'][0]
        expired,done=self.append(active,receipt,'EXPIRE',attempt_id=attempt['attempt_id'],
            generation=attempt['generation'],now=clock(600))
        again=self.publish(active,boot['observed_head'],value['tip_sha256'])
        self.assertEqual(again['latest_ledger'],expired)
        self.assertEqual(again['observed_head'],done['observed_head'])
        self.assertEqual(jobs.inspect_development_job(again['latest_ledger'])['used_ms'],3600000)
        self.assertIs(again['execution_authorized'],False)

    def test_changed_anchor_night_or_report_source_cannot_reset_existing_job(self):
        value,boot=self.bootstrap()
        other=jobs.new_development_job(request(operational_night='2026-10-26'))
        self.assertEqual(other['origin']['job_id'],value['origin']['job_id'])
        with self.assertRaises(ValueError): self.publish(other)
        (self.checkout/'trusted.txt').write_bytes(b'Synthetic newer source\n')
        self.git('add','trusted.txt'); self.git('commit','-m','New source')
        newer=self.git('rev-parse','HEAD').decode().strip()
        with self.assertRaises(ValueError): self.publish(value,boot['observed_head'],
            root_report_source_commit=newer)

    def test_immutable_raw_bytes_and_foreign_report_paths_reject_without_repair(self):
        value,boot=self.bootstrap(); branch,prefix,files=reports._publication_records(value,self.source)
        bad=files[prefix+'state.json']+b' '
        self.transport.publish(branch,self.source,boot['observed_head'],{prefix+'state.json':bad})
        with self.assertRaises(ValueError): self.publish(value)
        actual=self.transport.head(branch)
        self.transport.publish(branch,self.source,actual,{prefix+'state.json':files[prefix+'state.json']})
        # Latest state is canonical again; the extra historical mutation still rejects.
        with self.assertRaises(ValueError): self.publish(value)

    def test_foreign_bridge_file_outside_job_prefix_rejects(self):
        value,boot=self.bootstrap(); branch,_,_=reports._publication_records(value,self.source)
        self.transport.publish(branch,self.source,boot['observed_head'],
            {'reports/pdca/2026-10-25/bridge/foreign.json':b'{}\n'})
        with self.assertRaises(ValueError): self.publish(value)

    def test_oversized_state_preflight_never_materializes_payload(self):
        value,boot=self.bootstrap(); branch,prefix,_=reports._publication_records(value,self.source)
        self.transport.publish(branch,self.source,boot['observed_head'],
            {prefix+'state.json':b' '*(1048576+1)})
        from pdca_bridge import GitTransport
        with patch.object(GitTransport,'read',side_effect=AssertionError('payload before sizecap')),self.assertRaises(ValueError):
            self.publish(value)

    def test_preexisting_base_namespace_cannot_bootstrap_new_zero_job(self):
        value=ledger(); _,prefix,_=reports._publication_records(value,self.source)
        path=self.checkout/prefix/'prior.json'; path.parent.mkdir(parents=True); path.write_bytes(b'{}\n')
        self.git('add',str(path.relative_to(self.checkout))); self.git('commit','-m','Existing accounting evidence')
        source=self.git('rev-parse','HEAD').decode().strip()
        with self.assertRaises(ValueError): self.publish(value,root_report_source_commit=source)

    def test_exhausted_job_in_other_base_night_cannot_reset_absent_or_existing_branch(self):
        self.git('config','core.longpaths','true')
        exhausted=ledger()
        for offset in (0,30):
            exhausted=start(exhausted,now=clock(offset),lease_until=clock(offset+600))
            attempt=jobs.inspect_development_job(exhausted)['attempts'][-1]
            exhausted=jobs.append_development_job(exhausted,expected_tip=exhausted['tip_sha256'],
                transition=dict(kind='SETTLE',attempt_id=attempt['attempt_id'],
                    generation=attempt['generation'],active_ms=3600000,now=clock(offset+20)))
        self.assertEqual(jobs.inspect_development_job(exhausted)['used_ms'],7200000)
        _,_,old_files=reports._publication_records(exhausted,self.source)
        for name,raw in old_files.items():
            path=self.checkout/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw)
        self.git('add','reports'); self.git('commit','-m','Archive exhausted old-night accounting in base')
        source=self.git('rev-parse','HEAD').decode().strip()
        fresh=jobs.new_development_job(request(operational_night='2026-10-26'))
        self.assertEqual(fresh['origin']['job_id'],exhausted['origin']['job_id'])
        self.assertEqual(jobs.inspect_development_job(fresh)['used_ms'],0)
        from pdca_bridge import GitTransport
        with patch.object(GitTransport,'read',side_effect=AssertionError('base reset payload read')):
            with self.assertRaises(ValueError): self.publish(fresh,root_report_source_commit=source)
        # Independently seed an otherwise canonical branch; validation must also reject its base.
        branch,_,files=reports._publication_records(fresh,source)
        self.transport.publish(branch,source,None,files)
        with patch.object(GitTransport,'read',side_effect=AssertionError('base reset payload read')):
            with self.assertRaises(ValueError): self.publish(fresh,root_report_source_commit=source)


if __name__=='__main__': unittest.main()
