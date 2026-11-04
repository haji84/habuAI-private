"""Explicit Node/VM sandbox only. Fake globals are never production API input."""
import copy
import json
from pathlib import Path
import subprocess
import unittest

from tests.test_development_controller import ROOT,HEAD,binding,request,observation,change

HARNESS=r'''
const fs=require('fs'),vm=require('vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const source=fs.readFileSync(process.argv[1],'utf8');
let calls=[],callbacks=0,queues=new Map();
for(const row of input.observation.fetches){
 if(!queues.has(row.url))queues.set(row.url,[]);queues.get(row.url).push(row);
}
async function get(url,tool){
 calls.push({url,tool});const rows=queues.get(url);
 if(!rows||!rows.length)throw Error('Unknown sandbox endpoint');
 const row=rows.length>1?rows.shift():rows[0];
 return {structuredContent:{content:row.raw_utf8}};
}
const allowed={
 mcp__codex_apps__github_fetch:async({url})=>get(url,'github_fetch'),
 mcp__codex_apps__github_fetch_workflow_job_logs:async({repo_full_name,job_id})=>{
  if(repo_full_name!=='haji84/habuAI-private'||job_id!==101)throw Error('Bad sandbox log identity');
  return get('https://api.github.com/repos/'+repo_full_name+'/actions/jobs/'+job_id+'/logs','github_fetch_workflow_job_logs');
 }
};
const tools=new Proxy(allowed,{get(t,k){if(!(k in t))throw Error('Forbidden tool '+String(k));return t[k];}});
const context={tools,setTimeout,clearTimeout,Date,
 HABU_CONTROLLER_CODE_OBSERVATION:input.code_binding===undefined?JSON.stringify(input.observation.controller_code_binding):input.code_binding};
if(input.expired){let t=0;context.Date=class extends Date{static now(){t+=60000;return t;}};}
vm.runInNewContext(source,context,{timeout:1000});
let req=input.request_json;
if(input.foreign)req=new Proxy({},{get(){callbacks++;throw Error('Candidate getter');}});
(async()=>{
 try{const result=await context.HabuProductionReadOnlyController.runReadOnly(req);
 process.stdout.write(JSON.stringify({result,calls,callbacks}));}
 catch(error){process.stdout.write(JSON.stringify({escaped:String(error),calls,callbacks}));}
})();
'''


class ProductionControllerHostTests(unittest.TestCase):
    def run_host(self,obs=None,req=None,**extra):
        path=ROOT/'scripts/production_controller_host.js'
        self.assertTrue(path.is_file(),'Fixed actual-host readonly runner absent')
        payload=dict(observation=observation() if obs is None else obs,
                     request_json=json.dumps(request()) if req is None else req,**extra)
        process=subprocess.run(['node','-e',HARNESS,str(path)],input=json.dumps(payload).encode(),
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
        self.assertEqual(process.returncode,0,process.stderr.decode())
        value=json.loads(process.stdout);self.assertNotIn('escaped',value,value)
        return value

    def test_fixed_actual_source_loop_all_operations_and_python_staging_connection(self):
        from tests.test_development_controller import DevelopmentControllerTests
        helper=DevelopmentControllerTests();helper.path=ROOT/'scripts/development_controller.py'
        module=helper.module()
        for operation in ('prepare_activation','verify_merged_intent','activate_reviewed_intent','issue_current_prediction'):
            obs=observation(operation);value=self.run_host(obs,json.dumps(request(operation)))
            result=value['result'];self.assertEqual(result['collection_status'],'COMPLETE',result)
            self.assertEqual(result['writes_attempted'],0)
            self.assertGreater(len(value['calls']),10)
            staged=module.stage_operation(operation,request(operation),result,controller_code_binding=binding())
            self.assertEqual(staged['status'],'BLOCKED',staged)
            self.assertEqual(staged['facts']['checkout_sha'],HEAD)
            self.assertIs(staged['production_authorized'],False)

    def test_foreign_request_getters_are_not_invoked_and_no_tool_called(self):
        value=self.run_host(foreign=True)
        self.assertEqual(value['callbacks'],0);self.assertEqual(value['calls'],[])
        self.assertEqual(value['result']['collection_status'],'FAIL')

    def test_closed_duplicate_nonfinite_oversize_and_transport_requests_fail_before_get(self):
        for req in ('{"operation":"prepare_activation","operation":"issue_current_prediction","pr_number":155,"expected_head_sha":"'+HEAD+'"}',
                    '{"operation":"prepare_activation","pr_number":NaN,"expected_head_sha":"'+HEAD+'"}',
                    json.dumps(dict(request(),transport='fake')),json.dumps(dict(request(),trusted=True)),
                    ' '*300000):
            value=self.run_host(req=req)
            self.assertEqual(value['calls'],[])
            self.assertIn(value['result']['collection_status'],('FAIL','BLOCKED'))

    def test_pr_or_attempt_movement_is_not_a_coherent_snapshot(self):
        for kind,mutate in [('PR_AFTER',lambda d:d['head'].update(sha='0'*40)),
                            ('RUN_AFTER',lambda d:d.update(run_attempt=2))]:
            obs=observation();change(obs,kind,mutate)
            self.assertEqual(self.run_host(obs)['result']['collection_status'],'BLOCKED')

    def test_incomplete_collection_duplicate_identity_and_expired_budget_block(self):
        obs=observation();change(obs,'JOBS',lambda d:d.update(total_count=2))
        self.assertNotEqual(self.run_host(obs)['result']['collection_status'],'COMPLETE')
        obs=observation();change(obs,'JOBS',lambda d:d['jobs'].append(copy.deepcopy(d['jobs'][0])))
        self.assertNotEqual(self.run_host(obs)['result']['collection_status'],'COMPLETE')
        self.assertEqual(self.run_host(expired=True)['result']['collection_status'],'BLOCKED')

    def test_binding_is_loader_metadata_and_has_no_candidate_context_switch(self):
        value=self.run_host(code_binding=json.dumps(dict(binding(),role='PRODUCTION_CONTEXT')))
        self.assertEqual(value['result']['collection_status'],'FAIL')
        self.assertEqual(value['calls'],[])

    def test_merged_pr_actually_reads_merge_commit_without_claiming_admission(self):
        from tests.test_development_controller import DevelopmentControllerTests,REPO,change
        obs=observation()
        for kind in ('PR_BEFORE','PR_AFTER'):
            change(obs,kind,lambda d:d.update(merged=True,state='closed',merge_commit_sha='9'*40))
        obs['fetches'].append(dict(kind='MERGED_COMMIT',url=REPO+'/git/commits/'+'9'*40,page=None,
            format='JSON',raw_utf8=json.dumps(dict(sha='9'*40,tree=dict(sha='8'*40),parents=[dict(sha='0'*40)]))))
        result=self.run_host(obs)['result']
        self.assertTrue(any(r['kind']=='MERGED_COMMIT' for r in result['fetches']))
        helper=DevelopmentControllerTests();helper.path=ROOT/'scripts/development_controller.py'
        staged=helper.module().stage_operation('prepare_activation',request(),result,controller_code_binding=binding())
        self.assertEqual(staged['status'],'BLOCKED')
        self.assertEqual(staged['facts'].get('merge_commit_sha'),'9'*40)
        self.assertIs(staged['production_authorized'],False)


if __name__=='__main__':unittest.main()
