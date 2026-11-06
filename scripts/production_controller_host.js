/* Fixed active-host READ-ONLY runner, not a production writer or Context factory.
 * The reviewed outer loader reads this exact Git blob, verifies its pinned SHA,
 * then evaluates it in the existing functions.exec host. It supplies only a
 * primitive JSON string in HABU_CONTROLLER_CODE_OBSERVATION: fixed path/role,
 * actual git_commit_sha/git_blob_sha1/source_sha256. That metadata is not trust
 * or portable authentication. Never load source chosen by candidate input.
 *
 * Usage in that host: await HabuProductionReadOnlyController.runReadOnly(
 *   JSON.stringify({operation,pr_number,expected_head_sha})). Pass the returned
 * bounded raw observations to the separately pinned development_controller.py
 * staging helper. Neither saved result can restore an authenticated context.
 * Only the separate Node/VM test harness supplies fake globals. This source has
 * no transport argument, fake switch, shell, filesystem or GitHub write mapping.
 * PUBLIC repository: raw responses/logs stay private; do not publish private
 * routes/models/inference. Actual durable layout/registry/genesis unapproved.
 */
(function () {
  'use strict';
  const BASE='https://api.github.com/repos/haji84/habuAI-private';
  const REPOSITORY_ID=1386591822, WORKFLOW_ID=366603831;
  const WORKFLOW='.github/workflows/data-intake-tests.yml';
  const OPERATIONS=['prepare_activation','verify_merged_intent','activate_reviewed_intent','issue_current_prediction'];
  const MAX_RAW=2*1024*1024, MAX_TOTAL=4*1024*1024, MAX_PAGES=4, MAX_CALLS=40;
  class Stop extends Error { constructor(code,status='BLOCKED'){super(code);this.code=code;this.status=status;} }
  function utf8Length(text){
    let size=0;
    for(let i=0;i<text.length;i++){
      const n=text.charCodeAt(i);
      if(n<128)size++;else if(n<2048)size+=2;
      else if(n>=0xd800&&n<=0xdbff){
        const low=text.charCodeAt(++i);if(!(low>=0xdc00&&low<=0xdfff))throw new Stop('INVALID_UTF8','FAIL');size+=4;
      } else if(n>=0xdc00&&n<=0xdfff)throw new Stop('INVALID_UTF8','FAIL');else size+=3;
    }
    return size;
  }
  function strictJSON(text,limit=MAX_RAW){
    if(typeof text!=='string')throw new Stop('PRIMITIVE_JSON_STRING_REQUIRED','FAIL');
    if(text.length>limit||utf8Length(text)>limit)throw new Stop('JSON_CAPACITY');
    let at=0,nodes=0;
    const ws=()=>{while(at<text.length&&/\s/.test(text[at])){if(!' \r\n\t'.includes(text[at]))throw new Stop('INVALID_JSON','FAIL');at++;}};
    function string(){
      const start=at++;let escape=false;
      while(at<text.length){const c=text[at++];if(c==='"'&&!escape){
        let value;try{value=JSON.parse(text.slice(start,at));}catch(_){throw new Stop('INVALID_JSON','FAIL');}
        utf8Length(value);return value;
      }if(c==='\\'&&!escape)escape=true;else escape=false;}
      throw new Stop('INVALID_JSON','FAIL');
    }
    function value(depth){
      if(++nodes>100000||depth>32)throw new Stop('JSON_CAPACITY');ws();const c=text[at];
      if(c==='"')return string();
      if(c==='{'){
        at++;ws();const out=Object.create(null),keys=new Set();if(text[at]==='}'){at++;return out;}
        while(true){ws();if(text[at]!=='"')throw new Stop('INVALID_JSON','FAIL');const key=string();
          if(keys.has(key))throw new Stop('DUPLICATE_JSON_KEY','FAIL');keys.add(key);ws();
          if(text[at++]!==':')throw new Stop('INVALID_JSON','FAIL');out[key]=value(depth+1);ws();
          if(text[at]==='}'){at++;return out;}if(text[at++]!==',')throw new Stop('INVALID_JSON','FAIL');}
      }
      if(c==='['){at++;ws();const out=[];if(text[at]===']'){at++;return out;}
        while(true){out.push(value(depth+1));ws();if(text[at]===']'){at++;return out;}if(text[at++]!==',')throw new Stop('INVALID_JSON','FAIL');}}
      for(const [word,result] of [['true',true],['false',false],['null',null]])if(text.startsWith(word,at)){at+=word.length;return result;}
      const match=/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/.exec(text.slice(at));
      if(!match)throw new Stop('INVALID_JSON','FAIL');at+=match[0].length;const result=Number(match[0]);
      if(!Number.isFinite(result)||Number.isInteger(result)&&!Number.isSafeInteger(result))throw new Stop('UNSAFE_JSON_NUMBER','FAIL');return result;
    }
    const result=value(0);ws();if(at!==text.length)throw new Stop('INVALID_JSON','FAIL');return result;
  }
  function fields(value,names){if(value===null||typeof value!=='object'||Array.isArray(value)||
      Object.keys(value).sort().join('|')!==names.slice().sort().join('|'))throw new Stop('EXACT_FIELDS','FAIL');}
  function integer(value){if(!Number.isSafeInteger(value)||value<=0)throw new Stop('INTEGER_REQUIRED','FAIL');return value;}
  function sha(value,n=40){if(typeof value!=='string'||!(new RegExp('^[0-9a-f]{'+n+'}$')).test(value))throw new Stop('HASH_REQUIRED','FAIL');return value;}
  function identity(pr){return JSON.stringify([pr.number,pr.head?.sha,pr.head?.repo?.id,pr.base?.sha,pr.base?.ref,pr.base?.repo?.id,pr.state,pr.draft,pr.merged,pr.merge_commit_sha]);}
  function latest(runs,head){
    const selected=runs.filter(r=>r.workflow_id===WORKFLOW_ID&&r.path===WORKFLOW&&r.head_sha===head&&r.event==='pull_request');
    if(!selected.length)throw new Stop('REQUIRED_WORKFLOW_RUN_NOT_OBSERVED');
    for(const run of selected){integer(run.id);integer(run.run_number);integer(run.run_attempt);}
    const number=Math.max(...selected.map(r=>r.run_number)),best=selected.filter(r=>r.run_number===number);
    if(best.length!==1)throw new Stop('AMBIGUOUS_LATEST_RUN');return best[0];
  }
  async function runReadOnly(requestJSON){
    const started=Date.now(),deadline=started+30000;let bytes=0,calls=0,request=null,binding=null;const fetches=[];
    function check(){if(Date.now()>=deadline)throw new Stop('HOST_DEADLINE');}
    function result(status,reasons=[]){return {schema_version:'habu-controller-host-observation-v1',request,
      observed_at:new Date().toISOString(),controller_code_binding:binding,collection_status:status,
      reason_codes:reasons,fetches,writes_attempted:0};}
    async function get(kind,url,page=null,format='JSON',jobId=null){
      check();if(++calls>MAX_CALLS)throw new Stop('HOST_REQUEST_CAPACITY');let timer;
      try{
        const task=jobId===null?tools.mcp__codex_apps__github_fetch({url}):
          tools.mcp__codex_apps__github_fetch_workflow_job_logs({repo_full_name:'haji84/habuAI-private',job_id:jobId});
        const response=await Promise.race([task,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Stop('HOST_DEADLINE')),Math.max(1,deadline-Date.now()));})]);
        check();if(response?.isError||response?.structuredContent?.truncated===true)throw new Stop('HOST_GET_UNAVAILABLE_OR_TRUNCATED');
        const raw=response?.structuredContent?.content;
        if(typeof raw!=='string')throw new Stop('HOST_RAW_TEXT_REQUIRED','FAIL');
        if(raw.length>MAX_RAW)throw new Stop('HOST_RAW_CAPACITY');const size=utf8Length(raw);bytes+=size;
        if(size>MAX_RAW||bytes>MAX_TOTAL)throw new Stop('HOST_RAW_CAPACITY');
        const value=format==='JSON'?strictJSON(raw):raw;
        fetches.push({kind,url,page,format,raw_utf8:raw});return value;
      }catch(error){if(error instanceof Stop)throw error;throw new Stop('HOST_GET_FAILED');}
      finally{if(timer!==undefined)clearTimeout(timer);}
    }
    async function pages(kind,path,key=null,total=null){
      const out=[],ids=new Set();let declared=total;
      for(let page=1;page<=MAX_PAGES;page++){
        const raw=await get(kind,BASE+path+(path.includes('?')?'&':'?')+'per_page=100&page='+page,page);
        const rows=key===null?raw:raw?.[key];if(!Array.isArray(rows)||rows.length>100)throw new Stop('INVALID_COLLECTION','FAIL');
        if(key!==null){if(!Number.isSafeInteger(raw.total_count)||raw.total_count<0)throw new Stop('INVALID_TOTAL','FAIL');
          if(declared!==null&&declared!==raw.total_count)throw new Stop('COLLECTION_TOTAL_MOVED');declared=raw.total_count;}
        for(const row of rows){const id=kind==='FILES'?row.filename:integer(row.id);
          if(typeof id!=='string'&&typeof id!=='number'||ids.has(id))throw new Stop('DUPLICATE_COLLECTION_ID','FAIL');ids.add(id);out.push(row);}
        if(declared!==null&&out.length>declared)throw new Stop('COLLECTION_COUNT_CONTRADICTION','FAIL');
        if(rows.length<100){if(declared!==null&&out.length!==declared)throw new Stop('COLLECTION_INCOMPLETE');return out;}
        if(declared!==null&&out.length===declared)return out;
      }throw new Stop('COLLECTION_PAGE_CAPACITY');
    }
    try{
      request=strictJSON(requestJSON,4096);fields(request,['operation','pr_number','expected_head_sha']);
      if(!OPERATIONS.includes(request.operation))throw new Stop('FIXED_OPERATION_REQUIRED','FAIL');integer(request.pr_number);sha(request.expected_head_sha);
      binding=strictJSON(globalThis.HABU_CONTROLLER_CODE_OBSERVATION,4096);
      fields(binding,['path','role','git_commit_sha','git_blob_sha1','source_sha256']);
      if(binding.path!=='scripts/production_controller_host.js'||binding.role!=='PRIVILEGED_CONTROLLER_READONLY')throw new Stop('FIXED_CODE_BINDING_REQUIRED','FAIL');
      sha(binding.git_commit_sha);sha(binding.git_blob_sha1);sha(binding.source_sha256,64);
      const repository=await get('REPOSITORY',BASE);
      if(repository.id!==REPOSITORY_ID||repository.full_name!=='haji84/habuAI-private'||repository.default_branch!=='main'||typeof repository.private!=='boolean')throw new Stop('REPOSITORY_IDENTITY','FAIL');
      const path='/pulls/'+request.pr_number,pr=await get('PR_BEFORE',BASE+path);
      if(pr.number!==request.pr_number||pr.head?.repo?.id!==REPOSITORY_ID||pr.base?.repo?.id!==REPOSITORY_ID||pr.base?.ref!=='main')throw new Stop('PR_IDENTITY','FAIL');
      if(pr.head.sha!==request.expected_head_sha)throw new Stop('PR_HEAD_MOVED');
      const main=await get('MAIN',BASE+'/branches/main');sha(main.commit?.sha);sha(pr.base.sha);
      await get('HEAD_COMMIT',BASE+'/git/commits/'+request.expected_head_sha);
      await get('MAIN_COMMIT',BASE+'/git/commits/'+main.commit.sha);
      if(pr.merged===true)await get('MERGED_COMMIT',BASE+'/git/commits/'+sha(pr.merge_commit_sha));
      await pages('FILES',path+'/files',null,integer(pr.changed_files));
      await pages('REVIEWS',path+'/reviews');
      const runPath='/actions/runs?head_sha='+request.expected_head_sha+'&event=pull_request';
      const selected=latest(await pages('RUNS',runPath,'workflow_runs'),request.expected_head_sha);
      const run=await get('RUN_BEFORE',BASE+'/actions/runs/'+selected.id);
      if(run.id!==selected.id||run.run_attempt!==selected.run_attempt||run.head_sha!==request.expected_head_sha||run.workflow_id!==WORKFLOW_ID||run.path!==WORKFLOW||run.event!=='pull_request')throw new Stop('RUN_IDENTITY_MOVED');
      const jobs=await pages('JOBS','/actions/runs/'+run.id+'/attempts/'+integer(run.run_attempt)+'/jobs','jobs');
      for(const job of jobs){if(job.run_id!==run.id||job.run_attempt!==run.run_attempt)throw new Stop('JOB_ATTEMPT_IDENTITY','FAIL');
        if(job.name==='test')await get('JOB_LOG',BASE+'/actions/jobs/'+job.id+'/logs',job.id,'TEXT',job.id);}
      await get('WORKFLOW_MAIN',BASE+'/contents/'+WORKFLOW+'?ref='+main.commit.sha,null,'TEXT');
      await get('WORKFLOW_HEAD',BASE+'/contents/'+WORKFLOW+'?ref='+request.expected_head_sha,null,'TEXT');
      const after=await get('RUN_AFTER',BASE+'/actions/runs/'+run.id);
      if(after.id!==run.id||after.run_attempt!==run.run_attempt||after.head_sha!==run.head_sha||after.status!==run.status||after.conclusion!==run.conclusion)throw new Stop('RUN_ATTEMPT_MOVED');
      const latestAfter=latest(await pages('RUNS_AFTER',runPath,'workflow_runs'),request.expected_head_sha);
      if(latestAfter.id!==run.id||latestAfter.run_attempt!==run.run_attempt)throw new Stop('LATEST_RUN_MOVED');
      const mainAfter=await get('MAIN_AFTER',BASE+'/branches/main');
      if(mainAfter.commit?.sha!==main.commit.sha)throw new Stop('DEFAULT_SOURCE_MOVED');
      const prAfter=await get('PR_AFTER',BASE+path);
      if(identity(prAfter)!==identity(pr))throw new Stop('PR_REVISION_MOVED');
      check();return result('COMPLETE');
    }catch(error){return result(error instanceof Stop?error.status:'FAIL',[error instanceof Stop?error.code:'HOST_PROTOCOL_ERROR']);}
  }
  globalThis.HabuProductionReadOnlyController=Object.freeze({runReadOnly});
})();
