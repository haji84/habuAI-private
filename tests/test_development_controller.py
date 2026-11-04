"""Synthetic declared staging; no receipt grants controller/production authority."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
REPO='https://api.github.com/repos/haji84/habuAI-private'
HEAD='a'*40
MAIN='b'*40
WORKFLOW='.github/workflows/data-intake-tests.yml'


def binding():
    return dict(path='scripts/production_controller_host.js',role='PRIVILEGED_CONTROLLER_READONLY',
        git_commit_sha='c'*40,git_blob_sha1='d'*40,source_sha256='e'*64)


def request(operation='prepare_activation'):
    return dict(operation=operation,pr_number=155,expected_head_sha=HEAD)


def observation(operation='prepare_activation'):
    fetches=[]
    def add(kind,url,value,page=None,text=False):
        fetches.append(dict(kind=kind,url=url,page=page,format='TEXT' if text else 'JSON',
            raw_utf8=value if text else json.dumps(value,separators=(',',':'))))
    repo=dict(id=1386591822,full_name='haji84/habuAI-private',default_branch='main',private=False)
    pr=dict(number=155,head=dict(sha=HEAD,repo=dict(id=repo['id'])),
        base=dict(sha=MAIN,ref='main',repo=dict(id=repo['id'])),state='open',draft=True,
        merged=False,merge_commit_sha=None,changed_files=1)
    run=dict(id=11,workflow_id=366603831,path=WORKFLOW,head_sha=HEAD,event='pull_request',
        run_attempt=1,run_number=1,status='completed',conclusion='success')
    job=dict(id=101,run_id=11,run_attempt=1,name='test',status='completed',conclusion='success',
        steps=[dict(name='Verify exact source commit',number=2,status='completed',conclusion='success'),
               dict(name='Verify current frozen development code',number=7,status='completed',conclusion='success')])
    workflow='name: data-intake-tests\n# reviewed synthetic definition\nEXPECTED_HABU_SOURCE_SHA\ngit rev-parse HEAD\n'
    add('REPOSITORY',REPO,repo)
    add('PR_BEFORE',REPO+'/pulls/155',pr)
    add('MAIN',REPO+'/branches/main',dict(commit=dict(sha=MAIN)))
    for kind,sha in [('HEAD_COMMIT',HEAD),('MAIN_COMMIT',MAIN)]:
        add(kind,REPO+'/git/commits/'+sha,dict(sha=sha,tree=dict(sha='f'*40),parents=[dict(sha='0'*40)]))
    add('FILES',REPO+'/pulls/155/files?per_page=100&page=1',
        [dict(filename='src/example.py',status='modified')],1)
    add('REVIEWS',REPO+'/pulls/155/reviews?per_page=100&page=1',[],1)
    add('RUNS',REPO+'/actions/runs?head_sha='+HEAD+'&event=pull_request&per_page=100&page=1',
        dict(total_count=1,workflow_runs=[run]),1)
    add('RUN_BEFORE',REPO+'/actions/runs/11',run)
    add('JOBS',REPO+'/actions/runs/11/attempts/1/jobs?per_page=100&page=1',dict(total_count=1,jobs=[job]),1)
    add('JOB_LOG',REPO+'/actions/jobs/101/logs','2026-11-04T01:00:00.000Z EXACT_SOURCE_HEAD='+HEAD+'\n',101,True)
    add('WORKFLOW_MAIN',REPO+'/contents/'+WORKFLOW+'?ref='+MAIN,workflow,text=True)
    add('WORKFLOW_HEAD',REPO+'/contents/'+WORKFLOW+'?ref='+HEAD,workflow,text=True)
    add('RUN_AFTER',REPO+'/actions/runs/11',run)
    add('RUNS_AFTER',REPO+'/actions/runs?head_sha='+HEAD+'&event=pull_request&per_page=100&page=1',
        dict(total_count=1,workflow_runs=[run]),1)
    add('MAIN_AFTER',REPO+'/branches/main',dict(commit=dict(sha=MAIN)))
    add('PR_AFTER',REPO+'/pulls/155',pr)
    return dict(schema_version='habu-controller-host-observation-v1',request=request(operation),
        observed_at='2026-11-04T10:00:00+00:00',controller_code_binding=binding(),
        collection_status='COMPLETE',reason_codes=[],fetches=fetches,writes_attempted=0)


def change(raw,kind,mutate):
    row=next(r for r in raw['fetches'] if r['kind']==kind)
    data=json.loads(row['raw_utf8']);mutate(data)
    row['raw_utf8']=json.dumps(data,separators=(',',':'))


class DevelopmentControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path=ROOT/'scripts/development_controller.py'

    def module(self):
        self.assertTrue(self.path.is_file(),'Fixed read-only staging helper absent')
        spec=importlib.util.spec_from_file_location('controller_under_test',self.path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def call(self,obs=None,operation='prepare_activation',journal=None,**kw):
        obs=observation(operation) if obs is None else obs
        result=self.module().stage_operation(operation,request(operation),obs,journal=journal,
            controller_code_binding=binding(),**kw)
        for flag in ('production_authorized','official_issuance_authorized','registry_activated',
                     'github_facts_authenticated','write_executor_implemented'):
            self.assertIs(result[flag],False)
        self.assertEqual(result['source_authentication'],'NOT_ATTESTED_BY_STAGING_HELPER')
        return result

    def test_all_four_operations_are_honestly_blocked_without_layout_or_science(self):
        for op in ('prepare_activation','verify_merged_intent','activate_reviewed_intent','issue_current_prediction'):
            r=self.call(operation=op)
            self.assertEqual(r['status'],'BLOCKED',r)
            self.assertIn('PRIVATE_DURABLE_LAYOUT_NOT_APPROVED',r['reason_codes'])
            self.assertEqual(r['facts']['checkout_sha'],HEAD)
            self.assertEqual(r['facts']['visibility'],'PUBLIC')
            self.assertEqual(r['write_status'],'BLOCKED')

    def test_operations_preserve_their_fixed_unimplemented_stage_dependencies(self):
        expected={'prepare_activation':'SOURCE_QUALIFIED_REPRODUCTION',
            'verify_merged_intent':'VERIFY_MERGED_INTENT_TREE_AND_POLICY',
            'activate_reviewed_intent':'DIRECT_PARENT_REMOTE_CAS',
            'issue_current_prediction':'EXECUTE_REGISTERED_COMPOSITE_AND_IMMUTABLE_ISSUANCE'}
        for operation,required in expected.items():
            result=self.call(operation=operation)
            self.assertIn(required,result.get('required_stages',[]))
            self.assertEqual(result['completed_stage'],'READ_ONLY_FACTS_OBSERVED_UNATTESTED')

    def test_journal_hash_chain_idempotent_replay_fresh_resume_and_immutability(self):
        obs=observation();before=copy.deepcopy(obs);first=self.call(obs)
        self.assertEqual([e['state'] for e in first['journal']['events']],
                         ['REQUESTED','READ_ONLY_FACTS_OBSERVED','ADMISSION_BLOCKED'])
        replay=self.call(obs,journal=first['journal']);self.assertEqual(first,replay)
        obs['observed_at']='2026-11-04T10:01:00+00:00'
        resumed=self.call(obs,journal=first['journal'])
        self.assertEqual(len(resumed['journal']['events']),5)
        self.assertEqual(first['journal']['events'],resumed['journal']['events'][:3])
        self.assertEqual(before,observation())

    def test_actual_fact_identity_revision_workflow_and_latest_attempt_guards(self):
        for kind,mutate in [('REPOSITORY',lambda d:d.update(id=1)),
                            ('PR_AFTER',lambda d:d['head'].update(sha='0'*40)),
                            ('RUN_AFTER',lambda d:d.update(run_attempt=2)),
                            ('RUN_BEFORE',lambda d:d.update(path='other.yml')),
                            ('JOBS',lambda d:d['jobs'][0].update(run_attempt=2))]:
            obs=observation();change(obs,kind,mutate)
            self.assertIn(self.call(obs)['status'],('FAIL','BLOCKED'))
            self.assertNotEqual(self.call(obs)['facts'].get('checkout_sha'),HEAD)

    def test_checkout_missing_duplicate_conflicting_or_truncated_never_proves_head(self):
        for log in ('no checkout marker\n','EXACT_SOURCE_HEAD='+HEAD+'\nEXACT_SOURCE_HEAD='+HEAD+'\n',
                    'EXACT_SOURCE_HEAD='+'0'*40+'\n','Warning: truncated output\nEXACT_SOURCE_HEAD='+HEAD+'\n'):
            obs=observation();next(r for r in obs['fetches'] if r['kind']=='JOB_LOG')['raw_utf8']=log
            r=self.call(obs);self.assertEqual(r['status'],'BLOCKED')
            self.assertIsNone(r['facts'].get('checkout_sha'))

    def test_unreviewed_workflow_definition_change_blocks_checkout_admission(self):
        obs=observation();next(r for r in obs['fetches'] if r['kind']=='WORKFLOW_HEAD')['raw_utf8']+='changed\n'
        r=self.call(obs);self.assertIn('WORKFLOW_DEFINITION_CHANGED',r['reason_codes'])
        self.assertIsNone(r['facts'].get('checkout_sha'))

    def test_incomplete_duplicate_wrong_page_or_unknown_get_url_fails_closed(self):
        for mutate in (lambda o:o['fetches'].append(copy.deepcopy(next(r for r in o['fetches'] if r['kind']=='JOBS'))),
                       lambda o:change(o,'JOBS',lambda d:d.update(total_count=2)),
                       lambda o:next(r for r in o['fetches'] if r['kind']=='REVIEWS').update(page=2),
                       lambda o:o['fetches'][0].update(url='https://example.invalid/proof')):
            obs=observation();mutate(obs);r=self.call(obs)
            self.assertIn(r['status'],('FAIL','BLOCKED'))
            self.assertIsNone(r['facts'].get('checkout_sha'))

    def test_raw_duplicate_nonfinite_and_deep_json_are_rejected_before_normalization(self):
        for raw in ('{"id":1,"id":1386591822}', '{"id":NaN}', '['*40+'0'+']'*40):
            obs=observation();obs['fetches'][0]['raw_utf8']=raw
            self.assertIn(self.call(obs)['status'],('FAIL','BLOCKED'))

    def test_context_trust_source_override_and_journal_tamper_never_authenticate(self):
        obs=observation();obs['trusted']=True
        self.assertEqual(self.call(obs)['status'],'FAIL')
        first=self.call();journal=copy.deepcopy(first['journal'])
        journal['events'][-1]['state']='ACTIVATED'
        self.assertEqual(self.call(journal=journal)['status'],'FAIL')
        module=self.module();req=request();req['transport']='fake'
        r=module.stage_operation(req['operation'],req,observation(),controller_code_binding=binding())
        self.assertEqual(r['status'],'FAIL');self.assertIs(r['production_authorized'],False)

    def test_exact_types_budgets_no_callbacks_and_no_io(self):
        obs=observation();module=self.module();calls=[]
        class Meta(type):
            def __eq__(self,other):calls.append('eq');raise AssertionError('callback')
        class Foreign(metaclass=Meta):pass
        for value in (Foreign(),True,0,-1,31,10**1000,float('nan')):
            r=module.stage_operation('prepare_activation',request(),obs,controller_code_binding=binding(),budget_seconds=value)
            self.assertEqual(r['status'],'FAIL')
        obs['probe']=Foreign()
        with (patch('builtins.open',side_effect=AssertionError('file')),
              patch('socket.socket',side_effect=AssertionError('network')),
              patch('subprocess.run',side_effect=AssertionError('process'))):
            self.assertEqual(self.call(obs)['status'],'FAIL')
            self.assertEqual(self.call()['status'],'BLOCKED')
        self.assertEqual(calls,[])

    def test_actual_stdin_cli_has_no_transport_root_or_authority_switch(self):
        self.assertTrue(self.path.is_file(),'Fixed read-only staging helper absent')
        payload=dict(operation='prepare_activation',request=request(),observation=observation(),
                     controller_code_binding=binding(),journal=None)
        process=subprocess.run([sys.executable,'-X','utf8','-B',str(self.path)],
            input=json.dumps(payload).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=ROOT.parent)
        self.assertEqual(process.returncode,2,process.stderr.decode())
        result=json.loads(process.stdout);self.assertIs(result['production_authorized'],False)
        self.assertNotIn('raw_utf8',process.stdout.decode())

    def test_unittest_names_containing_truncated_are_not_truncation_annotations(self):
        obs=observation();row=next(r for r in obs['fetches'] if r['kind']=='JOB_LOG')
        row['raw_utf8']='test_truncated_pages_are_blocked ... ok\n'+row['raw_utf8']
        self.assertEqual(self.call(obs)['facts'].get('checkout_sha'),HEAD)

    def test_resealed_journal_pair_or_reason_type_contradictions_fail(self):
        def seal(journal):
            header={k:v for k,v in journal.items() if k not in ('events','tip_sha256')}
            prior=hashlib.sha256(json.dumps(header,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            for event in journal['events']:
                event['previous_sha256']=prior
                body={k:v for k,v in event.items() if k!='event_sha256'}
                prior=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                event['event_sha256']=prior
            journal['tip_sha256']=prior
        for mutate in (lambda j:j['events'][1].update(observation_sha256='0'*64),
                       lambda j:j['events'][-1].update(reason_codes=[True])):
            journal=copy.deepcopy(self.call()['journal']);mutate(journal);seal(journal)
            self.assertEqual(self.call(journal=journal)['status'],'FAIL')

    def test_real_cli_help_and_unknown_authority_arguments_do_not_consume_facts(self):
        self.assertTrue(self.path.is_file(),'Fixed read-only staging helper absent')
        help_result=subprocess.run([sys.executable,'-B',str(self.path),'--help'],
            input=b'',stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=ROOT.parent)
        self.assertEqual(help_result.returncode,0)
        rejected=subprocess.run([sys.executable,'-B',str(self.path),'--trusted'],
            input=b'',stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=ROOT.parent)
        self.assertEqual(rejected.returncode,2)

    def test_supplied_optional_job_and_step_names_have_real_string_types(self):
        for mutate in (lambda d:d['jobs'].append(dict(id=102,run_id=11,run_attempt=1,name={},
                            status='completed',conclusion='skipped',steps=[])),
                       lambda d:d['jobs'][0]['steps'].append(dict(name=False,number=9,status='completed',conclusion='skipped'))):
            obs=observation()
            def alter(data):
                mutate(data);data['total_count']=len(data['jobs'])
            change(obs,'JOBS',alter)
            self.assertEqual(self.call(obs)['status'],'FAIL')

    def test_bounded_large_unused_api_patch_and_real_sized_log_are_supported(self):
        obs=observation();change(obs,'FILES',lambda rows:rows[0].update(patch='synthetic patch\n'*7000))
        row=next(r for r in obs['fetches'] if r['kind']=='JOB_LOG')
        row['raw_utf8']='synthetic test output\n'*28000+row['raw_utf8']
        r=self.call(obs);self.assertEqual(r['facts'].get('checkout_sha'),HEAD,r['reason_codes'])


if __name__=='__main__':unittest.main()
