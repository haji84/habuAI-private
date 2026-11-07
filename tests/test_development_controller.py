"""Synthetic declared staging; no receipt grants controller/production authority."""
import copy
import hashlib
import importlib.util
import inspect
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

    def test_resume_uses_current_blockers_and_preserves_different_observation_history(self):
        def variant(private,draft,minute):
            obs=observation();obs['observed_at']=f'2026-11-04T10:{minute:02d}:00+00:00'
            change(obs,'REPOSITORY',lambda d:d.update(private=private))
            for kind in ('PR_BEFORE','PR_AFTER'):change(obs,kind,lambda d:d.update(draft=draft))
            return obs
        for before,after in ((variant(False,True,0),variant(True,False,1)),
                             (variant(True,False,0),variant(False,True,1))):
            with self.subTest(new_visibility=after['fetches'][0]['raw_utf8']):
                first=self.call(before);old=copy.deepcopy(first['journal'])
                resumed=self.call(after,journal=first['journal'])
                self.assertEqual(resumed['status'],'BLOCKED')
                self.assertEqual(resumed['journal']['events'][-1]['reason_codes'],resumed['reason_codes'])
                self.assertEqual(resumed['journal']['events'][:3],old['events'])
                self.assertEqual(self.call(after,journal=resumed['journal']),resumed)
                self.assertEqual(first['journal'],old)

    def test_resealed_current_observation_cannot_omit_current_public_or_draft_blocker(self):
        module=self.module()
        for blocker in ('PRIVATE_ARTIFACT_PUBLICATION_NOT_APPROVED','PR_DRAFT'):
            journal=copy.deepcopy(self.call()['journal'])
            journal['events'][-1]['reason_codes'].remove(blocker)
            prior=module.digest({k:v for k,v in journal.items() if k not in ('events','tip_sha256')})
            for event in journal['events']:
                event['previous_sha256']=prior
                prior=module.digest({k:v for k,v in event.items() if k!='event_sha256'})
                event['event_sha256']=prior
            journal['tip_sha256']=prior
            self.assertEqual(self.call(journal=journal)['status'],'FAIL')

    def test_observation_and_get_record_keys_are_checked_before_candidate_comparison(self):
        callbacks=[]
        class ForeignKey(str):
            def __ne__(self,other):callbacks.append('ne');return str.__ne__(self,other)
            def __eq__(self,other):callbacks.append('eq');return str.__eq__(self,other)
            def __hash__(self):callbacks.append('hash');return str.__hash__(self)
        for position in ('observation','get_record'):
            obs=observation()
            if position=='observation':obs[ForeignKey('extra')]=None
            else:
                row=obs['fetches'][0];body=row.pop('raw_utf8');row[ForeignKey('raw_utf8')]=body
            callbacks.clear()
            result=self.call(obs)
            self.assertEqual(result['status'],'FAIL')
            self.assertEqual(callbacks,[],position)


    def stage_issuance(self, data, *, observed_at='2026-11-04T10:00:00+00:00', budget_seconds=30):
        module=self.module()
        self.assertIn('issuance_preparation',inspect.signature(module.stage_operation).parameters,
                      'The fixed issue operation has no actual composite preparation')
        op='issue_current_prediction'
        obs=observation(op)
        obs['observed_at']=observed_at
        for kind in ('PR_BEFORE','PR_AFTER'):
            change(obs,kind,lambda pr:pr.update(state='closed',draft=False,merged=True,merge_commit_sha='3'*40))
        obs['fetches'].append(dict(kind='MERGED_COMMIT',url=REPO+'/git/commits/'+'3'*40,
            page=None,format='JSON',raw_utf8=json.dumps(dict(sha='3'*40,tree=dict(sha='4'*40),parents=[]))))
        r=module.stage_operation(op,request(op),obs,controller_code_binding=binding(),
            issuance_preparation=data,budget_seconds=budget_seconds)
        self.assertFalse(r['official_issuance_authorized'])
        self.assertFalse(r['production_authorized'])
        self.assertEqual(r['write_status'],'BLOCKED')
        self.assertEqual(r['status'],'BLOCKED')
        return r['issuance_preparation']

    def test_issue_stage_executes_native_adapter_and_builds_unpublished_p0(self):
        from tests.test_production_registry import checksum,core_apply
        data=issuance_fixture()
        from production_registry import validate_registry_snapshot
        unchanged=copy.deepcopy(data)
        prepared=self.stage_issuance(data)
        self.assertEqual(prepared['status'],'ISSUANCE_COMMIT_PROPOSED',prepared)
        self.assertEqual(prepared['computed']['version'],'P0')
        self.assertEqual(prepared['commit_spec']['parents'],['1'*40])
        documents=prepared['commit_spec']['immutable_additions']
        record,body=(json.loads(item['content_utf8']) for item in documents)
        actual=body['prediction']
        self.assertEqual(actual['outputs']['spatial_rows']['payload'][0]['spatial_score'],.25)
        self.assertEqual(actual['produced_outputs'],['spatial_rows'])
        self.assertEqual(record['input_bundle_sha256'],checksum(data['bundle']))
        self.assertEqual(record['component_receipts_sha256'],checksum(actual['component_receipts']))
        self.assertEqual(record['forecast_windows'],['2026-11-04T20:00:00+09:00'])
        self.assertEqual(record['output_ref']['sha256'],checksum(body,True))
        self.assertEqual(body['formal_product_policy_status'],'NOT_ATTESTED')
        self.assertEqual(body['planned_start'],data['planned_start'])
        next_snapshot=core_apply(data['snapshot'],prepared)
        readback=validate_registry_snapshot(next_snapshot,policy=data['policy'])
        self.assertEqual(readback['status'],'CONSISTENT_NOT_AUTHENTICATED')
        self.assertEqual(readback['computed']['issuance_count'],1)
        self.assertEqual(data,unchanged)

    def test_issue_stage_rejects_mismatched_model_or_runtime_code(self):
        data=issuance_fixture()
        data['model']['recipe_id']='changed-after-selection'
        r=self.stage_issuance(data)
        self.assertEqual(r['status'],'FAIL',r)
        self.assertIsNone(r['commit_spec'])
        data=issuance_fixture(code_mismatch=True)
        r=self.stage_issuance(data)
        self.assertEqual(r['status'],'BLOCKED',r)
        self.assertEqual(r['reason_codes'],['REVIEWED_RUNTIME_CODE_MISMATCH'])
        self.assertIsNone(r['commit_spec'])

    def test_issue_stage_blocks_foreign_module_and_discards_proposal_on_code_change(self):
        import composite_inference
        import prospective_inputs
        data=issuance_fixture()
        with patch.object(composite_inference,'__file__',str(ROOT/'outside.py')):
            result=self.stage_issuance(data)
        self.assertEqual(result['reason_codes'],['REVIEWED_RUNTIME_MODULE_ORIGIN_MISMATCH'])
        self.assertIsNone(result['commit_spec'])
        before=prospective_inputs._bounded_bytes
        reads=[]
        def changed_after_execution(path, budget, check):
            raw=before(path,budget,check)
            if path == ROOT/'src/composite_inference.py':
                reads.append(len(raw))
                if len(reads)==2:
                    return raw+b'\n'
            return raw
        with patch.object(prospective_inputs,'_bounded_bytes',changed_after_execution):
            result=self.stage_issuance(data)
        self.assertEqual(len(reads),2)
        self.assertEqual(result['reason_codes'],['REVIEWED_RUNTIME_CODE_MISMATCH'])
        self.assertIsNone(result['commit_spec'])
        self.assertIsNone(result['pending'])

    def test_issue_preparation_is_rejected_for_other_operations(self):
        result=self.call(issuance_preparation={})
        self.assertEqual(result['status'],'FAIL')
        self.assertEqual(result['reason_codes'],['ISSUANCE_PREPARATION_OPERATION_MISMATCH'])

    def test_issue_stage_cannot_stage_missing_or_vacuous_mandatory_outputs(self):
        missing=issuance_fixture()
        missing['bundle']['inputs'].clear()
        missing['bundle']['input_available_at'].clear()
        for data in (missing,issuance_fixture(mandatory=False)):
            with self.subTest(has_required=bool(data['model']['mandatory_capabilities'])):
                r=self.stage_issuance(data)
                self.assertEqual(r['status'],'BLOCKED',r)
                self.assertIsNone(r['commit_spec'])

    def test_issue_stage_rejects_stale_registry_and_elapsed_start_or_forecast_window(self):
        data=issuance_fixture()
        data['expected_ref_sha']='2'*40
        r=self.stage_issuance(data)
        self.assertEqual(r['status'],'CONFLICT',r)
        self.assertIsNone(r['commit_spec'])
        for start,now in (('2026-11-04T19:00:00+09:00','2026-11-04T10:00:00+00:00'),
                          ('2026-11-04T21:00:00+09:00','2026-11-04T11:00:00+00:00'),
                          ('2026-11-04T20:10:00+09:00','2026-11-04T10:00:00+00:00')):
            data=issuance_fixture()
            data['planned_start']=start
            r=self.stage_issuance(data,observed_at=now)
            self.assertEqual(r['status'],'BLOCKED',r)
            self.assertIsNone(r['commit_spec'])

    def test_issue_stage_keeps_inline_registry_document_capacity(self):
        data=issuance_fixture()
        rows=data['bundle']['inputs']['spatial']['universe_rows']
        sample=rows[0]
        rows[:]=[dict(sample,row_id=f'unit-{n:04d}',utm_x_m=500050.+100*n) for n in range(600)]
        r=self.stage_issuance(data)
        self.assertEqual(r['status'],'BLOCKED',r)
        self.assertEqual(r['reason_codes'],['DOCUMENT_CAPACITY_EXCEEDED'])
        self.assertIsNone(r['commit_spec'])


def issuance_fixture(*, code_mismatch=False,mandatory=True):
    """Anchor one declared event to actual local adapter code for synthetic staging."""
    from tests.test_output_adapters import legacy_fixture
    from tests.test_production_registry import checksum,core_document,core_fixture
    from codex_cycle_contract import code_paths
    from output_adapters import adapter_contract,required_code_paths

    closure={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in code_paths(ROOT)}
    if code_mismatch:
        closure['src/composite_inference.py']='0'*64
    state,inputs=legacy_fixture()
    cutoff='2026-11-04T19:00:00+09:00'
    night='2026-11-04'
    inputs['universe_rows'][0].update(operational_night=night,cutoff_time=cutoff,
                                      window_start_jst='2026-11-04T20:00:00+09:00')
    adapter=adapter_contract('legacy_spatial_v1')
    model=dict(schema_version='2.0',kind='registered_composite',recipe_id='synthetic-spatial',
        protocol_sha256='a'*64,policy_sha256='b'*64,training_cutoff=state['training_cutoff'],
        code_manifest={path:closure[path] for path in required_code_paths()},
        components=[dict(component_id='spatial',adapter_id=adapter['adapter_id'],adapter_version='1',
            role='spatial',state_sha256=checksum(state),config_sha256=checksum({}),
            input_schema_sha256=adapter['input_schema_sha256'],output_schema_sha256=adapter['output_schema_sha256'],
            dependencies={})],output_bindings={'spatial_rows':dict(component_id='spatial',output='spatial_rows')},
        mandatory_capabilities=['spatial_rows'] if mandatory else [])
    model['model_id']=model['model_sha256']=checksum(model)
    artifacts={checksum(state):state,checksum({}):{}}
    ready='2026-11-04T18:00:00+09:00'
    bundle=dict(schema_version='habu-composite-inference-input-v1',operational_night=night,
        cutoff_time=cutoff,forecast_end='2026-11-05T07:00:00+09:00',artifacts=artifacts,
        artifact_available_at={key:ready for key in artifacts},
        inputs={'spatial':inputs},input_available_at={'spatial':ready})

    snapshot,policy,_,_=core_fixture()
    policy['repository']=dict(id=1386591822,full_name='haji84/habuAI-private')
    snapshot['repository']=copy.deepcopy(policy['repository'])
    files=snapshot['commits'][0]['files']
    event=json.loads(files[0]['content_utf8'])
    event.pop('event_sha256')
    event.update(model_sha256=model['model_sha256'],protocol_sha256=model['protocol_sha256'],
        code_manifest=[dict(path=path,sha256=sha) for path,sha in closure.items()],code_sha256=checksum(closure))
    event['event_sha256']=checksum(event)
    files[0]=core_document(policy['event_directory']+'/'+event['event_sha256']+'.json',event)
    files[1]=core_document(policy['pointer_path'],dict(schema_version='habu-registry-pointer-v1',
                                                       event_sha256=event['event_sha256']))
    policy['anchor'].update(root_event_sha256=event['event_sha256'],
                            files_sha256=checksum({entry['path']:entry['sha256'] for entry in files}))
    policy['compatible_code_sha256']=[event['code_sha256']]
    return dict(snapshot=snapshot,policy=policy,expected_ref_sha='1'*40,
        expected_event_sha256=event['event_sha256'],operation_id='synthetic-issue',
        planned_start='2026-11-04T19:30:00+09:00',model=model,bundle=bundle)


if __name__=='__main__':unittest.main()
