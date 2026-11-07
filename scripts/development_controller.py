#!/usr/bin/env python3
"""Fixed READ-ONLY TaskH observation normalization and declarative resume journal.

Ordinary stdin CLI and Python inputs are UNATTESTED data. No Context is created
or restored; coherent invented observations remain production-ineligible. The
approved outer host loads a pinned JS Git blob, performs actual connector GETs,
then calls this separately pinned helper. It must retain its real execution
receipt outside Git; this JSON cannot authenticate that execution after replay.
Controller code binding is separate from any model/inference code closure.

Current write stages always BLOCKED: no approved existing registry/private
durability layout, merged intent/frozen gate policy or qualified reproduction
was supplied by this slice. The fixed Python issue stage can run a bounded local
composite and return an unpublished proposal using supplied registry declarations.
No publication, promotion or fake backend switch exists. The actual repository is PUBLIC: private GPS/log/model/inference
and search routes must not be emitted to its refs. Actual layout/genesis/storage
or visibility decisions are not made here. No new service/SDK/credential needed.

Bounds: four operations; fixed repository/workflow/path; 4 pages/collection,
40 GET records, 2MiB/raw body, 4MiB cumulative input/encoding, shared30s budget,
64 journal events. Shared exact-builtin guards reject callbacks/custom objects.
Raw GET payloads and their parsed strings have the explicit larger cap. Other data reuse
production_registry's 100k-node/24-depth/64KiB-string bounds. Cooperative limits
do not promise hard preemption. Raw API/log bodies are never returned in journal.
"""
from __future__ import annotations

import hashlib
import argparse
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
from datetime import datetime, timedelta, timezone
from time import monotonic

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from master_contracts import canonical_bytes,digest
from production_registry import _Budget,_Rejected,_owned,_fields,_sha,_stamp,_path

BASE='https://api.github.com/repos/haji84/habuAI-private'
REPOSITORY_ID=1386591822
WORKFLOW='.github/workflows/data-intake-tests.yml'
WORKFLOW_ID=366603831
OPERATIONS=('prepare_activation','verify_merged_intent','activate_reviewed_intent','issue_current_prediction')
REQUIRED_STAGES={
    'prepare_activation':('SOURCE_QUALIFIED_REPRODUCTION','FROZEN_GATE_POLICY','PREPARE_REVIEWED_INTENT'),
    'verify_merged_intent':('VERIFY_MERGED_INTENT_TREE_AND_POLICY','EXACT_REVIEWED_CI_AND_CLOSURE'),
    'activate_reviewed_intent':('VERIFY_MERGED_INTENT_TREE_AND_POLICY','SOURCE_QUALIFIED_REPRODUCTION',
        'VERIFY_EXISTING_REGISTRY','APPROVED_PRIVATE_DURABILITY','DIRECT_PARENT_REMOTE_CAS'),
    'issue_current_prediction':('VERIFY_CURRENT_REGISTRY_EVENT','LOAD_REVIEWED_COMPATIBLE_CODE',
        'VERIFY_PROSPECTIVE_INPUTS','APPROVED_PRIVATE_DURABILITY',
        'EXECUTE_REGISTERED_COMPOSITE_AND_IMMUTABLE_ISSUANCE'),
}
RAW_LIMIT=2*1024*1024
TOTAL_LIMIT=4*1024*1024
FLAGS=dict(source_authentication='NOT_ATTESTED_BY_STAGING_HELPER',
    scientific_reproduction='NOT_REPRODUCED',github_facts_authenticated=False,
    production_authorized=False,official_issuance_authorized=False,
    registry_activated=False,write_executor_implemented=False)
MISSING_GATES={'PRIVATE_DURABLE_LAYOUT_NOT_APPROVED','ACTUAL_REGISTRY_ANCHOR_NOT_SUPPLIED',
    'IMMUTABLE_REVIEWED_ACTIVATION_INTENT_NOT_SUPPLIED','FROZEN_PRODUCTION_GATE_POLICY_NOT_SUPPLIED',
    'SOURCE_QUALIFIED_SCIENTIFIC_REPRODUCTION_NOT_SUPPLIED'}


def _blocked(code):raise _Rejected(code,'BLOCKED')
def _fail(code):raise _Rejected(code)


def _integer(value,minimum=1):
    if type(value) is not int or not minimum<=value<2**53:_fail('SAFE_INTEGER_REQUIRED')
    return value


def _object(value,keys):
    if type(value) is not dict:_fail('SOURCE_OBJECT_REQUIRED')
    if not keys<=set(value):_blocked('SOURCE_FIELD_MISSING')
    return value


def _json(raw):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:_fail('DUPLICATE_SOURCE_JSON_KEY')
            result[key]=value
        return result
    try:
        return json.loads(raw,object_pairs_hook=unique,
            parse_constant=lambda _:(_ for _ in ()).throw(_Rejected('NONFINITE_SOURCE_JSON')))
    except _Rejected:raise
    except RecursionError:_blocked('SOURCE_JSON_CAPACITY')
    except (ValueError,UnicodeError):_fail('INVALID_SOURCE_JSON')


def _binding(value):
    _fields(value,{'path','role','git_commit_sha','git_blob_sha1','source_sha256'})
    if value['path']!='scripts/production_controller_host.js' or value['role']!='PRIVILEGED_CONTROLLER_READONLY':
        _fail('FIXED_CONTROLLER_CODE_BINDING_REQUIRED')
    _sha(value['git_commit_sha'],40);_sha(value['git_blob_sha1'],40);_sha(value['source_sha256'])


def _source_json(raw,budget):
    # json.loads constructs only new builtin JSON containers. Validate the whole
    # bounded response, including unused fields, without copying large API patch
    # strings through the smaller ordinary request/journal string contract.
    value=_json(raw);pending=[(value,0)]
    while pending:
        budget.check();item,depth=pending.pop();budget.nodes+=1
        if budget.nodes>100000 or depth>24:_blocked('SOURCE_JSON_CAPACITY')
        kind=type(item)
        if kind is dict:
            pending.extend((child,depth+1) for pair in item.items() for child in pair)
        elif kind is list:pending.extend((child,depth+1) for child in item)
        elif kind is str:
            if len(item)>RAW_LIMIT or len(item.encode('utf-8'))>RAW_LIMIT:_blocked('SOURCE_STRING_CAPACITY')
        elif kind is float:
            if not math.isfinite(item):_fail('NONFINITE_SOURCE_JSON')
        elif kind is int:
            if not -(2**63)<=item<2**63:_fail('SOURCE_INTEGER_RANGE')
        elif kind is not bool and item is not None:_fail('SOURCE_JSON_TYPE')
    return value


def _request(operation,value):
    _fields(value,{'operation','pr_number','expected_head_sha'})
    if type(operation) is not str or operation not in OPERATIONS or value['operation']!=operation:
        _fail('FIXED_OPERATION_REQUIRED')
    _integer(value['pr_number']);_sha(value['expected_head_sha'],40)


def _observation_copy(value,budget):
    if type(value) is not dict:_fail('OBSERVATION_OBJECT_REQUIRED')
    if any(type(key) is not str for key in value):_fail('OBSERVATION_KEY_TYPE')
    copied=_owned({k:v for k,v in value.items() if k!='fetches'},budget)
    rows=value.get('fetches')
    if type(rows) is not list or len(rows)>40:_fail('BOUNDED_GET_COLLECTION_REQUIRED')
    copied['fetches']=[]
    for row in rows:
        budget.check()
        if type(row) is not dict:_fail('GET_RECORD_REQUIRED')
        if any(type(key) is not str for key in row):_fail('GET_RECORD_KEY_TYPE')
        _fields(row,{'kind','url','page','format','raw_utf8'})
        meta=_owned({k:v for k,v in row.items() if k!='raw_utf8'},budget)
        raw=row['raw_utf8']
        if type(raw) is not str:_fail('RAW_UTF8_STRING_REQUIRED')
        if len(raw)>RAW_LIMIT:_blocked('RAW_GET_CAPACITY')
        size=len(raw.encode('utf-8'))
        budget.input_bytes+=size
        if size>RAW_LIMIT or budget.input_bytes>TOTAL_LIMIT:_blocked('RAW_GET_CAPACITY')
        meta['raw_utf8']=raw;copied['fetches'].append(meta)
    return copied


def _normalize(obs,req,code,budget):
    _fields(obs,{'schema_version','request','observed_at','controller_code_binding','collection_status',
                 'reason_codes','fetches','writes_attempted'})
    if obs['schema_version']!='habu-controller-host-observation-v1':_fail('OBSERVATION_SCHEMA')
    if canonical_bytes(obs['request'])!=canonical_bytes(req):_fail('OBSERVATION_REQUEST_BINDING')
    if canonical_bytes(obs['controller_code_binding'])!=canonical_bytes(code):_fail('CONTROLLER_CODE_BINDING_CHANGED')
    _stamp(obs['observed_at'])
    if type(obs['writes_attempted']) is not int or obs['writes_attempted']!=0:_fail('READONLY_WRITE_CONTRADICTION')
    if obs['collection_status'] not in ('COMPLETE','BLOCKED','FAIL'):_fail('COLLECTION_STATUS')
    if type(obs['reason_codes']) is not list or any(type(r) is not str for r in obs['reason_codes']):_fail('REASON_CODES')
    if obs['collection_status']!='COMPLETE':
        raise _Rejected('HOST_COLLECTION_'+obs['collection_status'],obs['collection_status'])
    if obs['reason_codes']:_fail('COMPLETE_COLLECTION_WITH_ERRORS')
    groups={};refs=[]
    for row in obs['fetches']:
        budget.check();kind=row['kind']
        if type(kind) is not str:_fail('FIXED_GET_KIND_REQUIRED')
        if row['format'] not in ('JSON','TEXT'):_fail('GET_FORMAT')
        body=_source_json(row['raw_utf8'],budget) if row['format']=='JSON' else row['raw_utf8']
        groups.setdefault(kind,[]).append((row,body))
        raw=row['raw_utf8'].encode('utf-8')
        refs.append(dict(kind=kind,url=row['url'],page=row['page'],size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    allowed={'REPOSITORY','PR_BEFORE','MAIN','HEAD_COMMIT','MAIN_COMMIT','MERGED_COMMIT',
        'FILES','REVIEWS','RUNS','RUN_BEFORE','JOBS','JOB_LOG','WORKFLOW_MAIN','WORKFLOW_HEAD',
        'RUN_AFTER','RUNS_AFTER','MAIN_AFTER','PR_AFTER'}
    if set(groups)-allowed:_fail('UNEXPECTED_GET_KIND')
    def exact(row,url,format='JSON',page=None):
        if (row['url']!=url or row['format']!=format or type(row['page']) is not type(page)
                or row['page']!=page):_fail('FIXED_GET_RESOURCE_BINDING')
    def one(kind,url,format='JSON'):
        rows=groups.get(kind,[])
        if not rows:_blocked('REQUIRED_GET_NOT_SUPPLIED')
        if len(rows)!=1:_fail('DUPLICATE_GET_OBSERVATION')
        row,body=rows[0];exact(row,url,format);return body
    def pages(kind,path,key=None,total=None):
        rows=groups.get(kind,[])
        if not rows:_blocked('REQUIRED_COLLECTION_NOT_SUPPLIED')
        if len(rows)>4:_blocked('PAGE_CAPACITY')
        if any(type(r[0]['page']) is not int for r in rows):_fail('PAGE_INTEGER_REQUIRED')
        rows=sorted(rows,key=lambda r:r[0]['page']);out=[];seen=set();expected=total
        for page,(row,body) in enumerate(rows,1):
            budget.check();exact(row,BASE+path+('&' if '?' in path else '?')+f'per_page=100&page={page}',page=page)
            if key is not None:
                _object(body,{key,'total_count'});declared=_integer(body['total_count'],0)
                if expected is not None and expected!=declared:_blocked('COLLECTION_TOTAL_MOVED')
                expected=declared;items=body[key]
            else:items=body
            if type(items) is not list or len(items)>100:_fail('PAGE_ARRAY_REQUIRED')
            for item in items:
                _object(item,{'filename' if kind=='FILES' else 'id'})
                identity=_path(item['filename']) if kind=='FILES' else _integer(item['id'])
                if identity in seen:_fail('DUPLICATE_COLLECTION_ID')
                seen.add(identity);out.append(item)
            if page<len(rows) and len(items)!=100:_fail('PAGE_AFTER_TERMINAL')
        if expected is not None:
            if len(out)>expected:_fail('COLLECTION_COUNT_CONTRADICTION')
            if len(out)!=expected:_blocked('COLLECTION_INCOMPLETE')
        elif len(items)==100:_blocked('COLLECTION_TERMINATION_NOT_OBSERVED')
        return out
    repository=one('REPOSITORY',BASE);_object(repository,{'id','full_name','default_branch','private'})
    if (_integer(repository['id'])!=REPOSITORY_ID or repository['full_name']!='haji84/habuAI-private'
            or repository['default_branch']!='main' or type(repository['private']) is not bool):_fail('REPOSITORY_IDENTITY')
    path='/pulls/'+str(req['pr_number']);pr=one('PR_BEFORE',BASE+path);after=one('PR_AFTER',BASE+path)
    def pr_identity(value):
        _object(value,{'number','head','base','state','draft','merged','merge_commit_sha','changed_files'})
        _object(value['head'],{'sha','repo'});_object(value['base'],{'sha','repo','ref'})
        for side in ('head','base'):
            _object(value[side]['repo'],{'id'})
            if _integer(value[side]['repo']['id'])!=REPOSITORY_ID:_fail('PR_REPOSITORY_IDENTITY')
            _sha(value[side]['sha'],40)
        if _integer(value['number'])!=req['pr_number'] or value['base']['ref']!='main':_fail('PR_IDENTITY')
        if type(value['draft']) is not bool or type(value['merged']) is not bool:_fail('PR_BOOLEAN_REQUIRED')
        if value['state'] not in ('open','closed'):_fail('PR_STATE')
        if value['merged'] and value['state']!='closed':_fail('MERGE_STATE_CONTRADICTION')
        if value['merge_commit_sha'] is not None:_sha(value['merge_commit_sha'],40)
        return [value['number'],value['head']['sha'],value['base']['sha'],value['draft'],value['merged'],value['state'],value['merge_commit_sha']]
    if pr_identity(pr)!=pr_identity(after) or pr['head']['sha']!=req['expected_head_sha']:_blocked('PR_REVISION_MOVED')
    main=one('MAIN',BASE+'/branches/main');main_after=one('MAIN_AFTER',BASE+'/branches/main')
    for value in (main,main_after):_object(value,{'commit'});_object(value['commit'],{'sha'});_sha(value['commit']['sha'],40)
    main_sha=main['commit']['sha']
    if main_after['commit']['sha']!=main_sha:_blocked('DEFAULT_SOURCE_MOVED')
    for kind,sha in (('HEAD_COMMIT',req['expected_head_sha']),('MAIN_COMMIT',main_sha)):
        commit=one(kind,BASE+'/git/commits/'+sha);_object(commit,{'sha','tree','parents'})
        if commit['sha']!=sha:_fail('COMMIT_IDENTITY')
        _object(commit['tree'],{'sha'});_sha(commit['tree']['sha'],40)
        if type(commit['parents']) is not list:_fail('COMMIT_PARENTS')
        for parent in commit['parents']:_object(parent,{'sha'});_sha(parent['sha'],40)
    if pr['merged']:
        if pr['merge_commit_sha'] is None:_blocked('MERGED_COMMIT_NOT_SUPPLIED')
        merge=one('MERGED_COMMIT',BASE+'/git/commits/'+pr['merge_commit_sha'])
        _object(merge,{'sha','tree','parents'})
        if merge['sha']!=pr['merge_commit_sha']:_fail('MERGED_COMMIT_IDENTITY')
    elif groups.get('MERGED_COMMIT'):_fail('UNEXPECTED_MERGED_COMMIT')
    files=pages('FILES',path+'/files',total=_integer(pr['changed_files'],0))
    for row in files:
        if 'previous_filename' in row:_path(row['previous_filename'])
    reviews=pages('REVIEWS',path+'/reviews')
    run_path='/actions/runs?head_sha='+req['expected_head_sha']+'&event=pull_request'
    def select(rows):
        matched=[]
        for row in rows:
            _object(row,{'id','workflow_id','path','head_sha','event','run_number','run_attempt'})
            if (row['workflow_id']==WORKFLOW_ID and row['path']==WORKFLOW
                    and row['head_sha']==req['expected_head_sha'] and row['event']=='pull_request'):
                _integer(row['run_number']);_integer(row['run_attempt']);matched.append(row)
        if not matched:_blocked('REQUIRED_WORKFLOW_NOT_OBSERVED')
        number=max(row['run_number'] for row in matched);best=[r for r in matched if r['run_number']==number]
        if len(best)!=1:_blocked('AMBIGUOUS_LATEST_RUN')
        return best[0]
    selected=select(pages('RUNS',run_path,'workflow_runs'))
    selected_after=select(pages('RUNS_AFTER',run_path,'workflow_runs'))
    if (selected['id'],selected['run_attempt'])!=(selected_after['id'],selected_after['run_attempt']):_blocked('LATEST_RUN_MOVED')
    run=one('RUN_BEFORE',BASE+'/actions/runs/'+str(selected['id']))
    later=one('RUN_AFTER',BASE+'/actions/runs/'+str(selected['id']))
    def status(row):
        _object(row,{'status','conclusion'})
        if row['status'] not in ('queued','in_progress','completed'):_fail('CI_STATUS')
        if row['conclusion'] not in (None,'success','failure','skipped','neutral','cancelled','timed_out','action_required','stale','startup_failure'):_fail('CI_CONCLUSION')
        if row['status']!='completed' and row['conclusion'] is not None:_fail('CI_STATUS_CONTRADICTION')
        if row['status']=='completed' and row['conclusion'] is None:_blocked('CI_CONCLUSION_NOT_SUPPLIED')
    for value in (run,later):
        _object(value,{'id','workflow_id','path','head_sha','event','run_attempt','status','conclusion'})
        if (value['id']!=selected['id'] or value['workflow_id']!=WORKFLOW_ID or value['path']!=WORKFLOW
                or value['head_sha']!=req['expected_head_sha'] or value['event']!='pull_request'):_fail('RUN_IDENTITY')
        _integer(value['run_attempt']);status(value)
    if any(run[k]!=later[k] for k in ('id','run_attempt','head_sha','status','conclusion')) or run['run_attempt']!=selected['run_attempt']:_blocked('RUN_ATTEMPT_MOVED')
    jobs=pages('JOBS',f"/actions/runs/{run['id']}/attempts/{run['run_attempt']}/jobs",'jobs')
    required=[]
    for job in jobs:
        _object(job,{'id','run_id','run_attempt','name','status','conclusion','steps'})
        if type(job['name']) is not str or not job['name']:_fail('JOB_NAME_REQUIRED')
        if _integer(job['run_id'])!=run['id'] or _integer(job['run_attempt'])!=run['run_attempt']:_fail('JOB_ATTEMPT_IDENTITY')
        status(job)
        if run['status']=='completed' and job['status']!='completed':_fail('TERMINAL_CI_HIERARCHY')
        if type(job['steps']) is not list:_fail('JOB_STEPS_REQUIRED')
        numbers=set()
        for step in job['steps']:
            _object(step,{'number','name','status','conclusion'});number=_integer(step['number']);status(step)
            if type(step['name']) is not str or not step['name']:_fail('STEP_NAME_REQUIRED')
            if number in numbers:_fail('DUPLICATE_STEP_NUMBER')
            numbers.add(number)
            if job['status']=='completed' and step['status']!='completed':_fail('TERMINAL_CI_HIERARCHY')
        if job['name']=='test':required.append(job)
    if len(required)!=1:_blocked('REQUIRED_TEST_JOB_NOT_OBSERVED')
    test=required[0]
    if run['status']!='completed' or run['conclusion']!='success' or test['status']!='completed' or test['conclusion']!='success':_blocked('REQUIRED_CI_NOT_SUCCESS')
    for name in ('Verify exact source commit','Verify current frozen development code'):
        steps=[s for s in test['steps'] if s['name']==name]
        if len(steps)!=1 or steps[0]['status']!='completed' or steps[0]['conclusion']!='success':_blocked('REQUIRED_CI_STEP_NOT_SUCCESS')
    approved=one('WORKFLOW_MAIN',BASE+'/contents/'+WORKFLOW+'?ref='+main_sha,'TEXT')
    candidate=one('WORKFLOW_HEAD',BASE+'/contents/'+WORKFLOW+'?ref='+req['expected_head_sha'],'TEXT')
    if approved!=candidate:_blocked('WORKFLOW_DEFINITION_CHANGED')
    if 'EXPECTED_HABU_SOURCE_SHA' not in approved or 'git rev-parse HEAD' not in approved:_blocked('TRUSTED_CHECKOUT_DEFINITION_NOT_ESTABLISHED')
    logs=groups.get('JOB_LOG',[])
    if len(logs)!=1:_blocked('CHECKOUT_LOG_NOT_SUPPLIED')
    log_row,log=logs[0];exact(log_row,BASE+f"/actions/jobs/{test['id']}/logs",'TEXT',test['id'])
    markers=[]
    for line in log.splitlines():
        budget.check();line=re.sub(r'^\d{4}-\d{2}-\d{2}T\S+\s+','',line)
        if (re.match(r'(?i)^(?:warning:\s*)?truncated output\b',line)
                or re.match(r'(?i)^\[.{0,10}(?:output|content|log)\b.{0,60}\btruncated\b',line)):
            _blocked('CHECKOUT_LOG_TRUNCATED')
        match=re.fullmatch(r'EXACT_SOURCE_HEAD=([0-9a-f]{40})',line)
        if match:markers.append(match.group(1))
    if markers!=[req['expected_head_sha']]:_blocked('CHECKOUT_NOT_UNIQUELY_PROVEN')
    return dict(repository_id=REPOSITORY_ID,repository='haji84/habuAI-private',
        visibility='PRIVATE' if repository['private'] else 'PUBLIC',pr_number=req['pr_number'],
        head_sha=req['expected_head_sha'],base_sha=pr['base']['sha'],main_sha=main_sha,
        merged=pr['merged'],merge_commit_sha=pr['merge_commit_sha'],
        merge_ancestry_status='NOT_VERIFIED_BY_THIS_SLICE',
        draft=pr['draft'],changed_path_count=len(files),review_count=len(reviews),
        run_id=run['id'],run_attempt=run['run_attempt'],job_count=len(jobs),checkout_sha=markers[0],
        workflow_sha256=hashlib.sha256(approved.encode()).hexdigest()),refs


def _journal(previous,operation,req,code,obs,observation_sha,reasons):
    header=dict(schema_version='habu-controller-readonly-journal-v1',
        operation_id=digest(dict(operation=operation,request=req)),operation=operation,
        request_sha256=digest(req),controller_code_binding=code)
    origin=digest(header)
    if previous is None:journal=dict(header,events=[],tip_sha256=origin)
    else:
        _fields(previous,set(header)|{'events','tip_sha256'})
        if canonical_bytes({k:previous[k] for k in header})!=canonical_bytes(header):_fail('JOURNAL_REQUEST_OR_CODE_BINDING')
        if type(previous['events']) is not list or not 3<=len(previous['events'])<=64:_fail('JOURNAL_EVENTS')
        tip=origin;clock=None
        for number,event in enumerate(previous['events'],1):
            _fields(event,{'sequence','previous_sha256','event_sha256','state','observation_sha256','observed_at','reason_codes'})
            expected='REQUESTED' if number==1 else ('READ_ONLY_FACTS_OBSERVED' if number%2==0 else 'ADMISSION_BLOCKED')
            if (type(event['sequence']) is not int or event['sequence']!=number or event['state']!=expected
                    or event['previous_sha256']!=tip):_fail('JOURNAL_TRANSITION')
            event_reasons=event['reason_codes']
            if (type(event_reasons) is not list or any(type(r) is not str for r in event_reasons)
                    or event_reasons!=sorted(set(event_reasons))):_fail('JOURNAL_REASON_TYPES')
            if number==1:
                if event['observation_sha256'] is not None or event_reasons:_fail('JOURNAL_REQUEST_EVENT')
            else:
                _sha(event['observation_sha256'])
                if number%2==0:
                    if event_reasons:_fail('JOURNAL_OBSERVATION_REASONS')
                else:
                    prior_event=previous['events'][number-2]
                    if (event['observation_sha256']!=prior_event['observation_sha256']
                            or event['observed_at']!=prior_event['observed_at']):_fail('JOURNAL_OBSERVATION_PAIR')
                    if not MISSING_GATES<=set(event_reasons) or set(event_reasons)-(MISSING_GATES|{
                            'PRIVATE_ARTIFACT_PUBLICATION_NOT_APPROVED','PR_DRAFT','PR_NOT_MERGED'}):
                        _fail('JOURNAL_REQUIRED_BLOCKERS')
            if digest({k:v for k,v in event.items() if k!='event_sha256'})!=event['event_sha256']:_fail('JOURNAL_HASH')
            when=_stamp(event['observed_at'])
            if clock is not None and when<clock:_fail('JOURNAL_CLOCK_REVERSED')
            clock=when;tip=event['event_sha256']
        if len(previous['events'])%2!=1 or previous['tip_sha256']!=tip:_fail('JOURNAL_TIP')
        journal=previous
        if previous['events'][-1]['observation_sha256']==observation_sha:
            if previous['events'][-1]['reason_codes']!=reasons:_fail('JOURNAL_CURRENT_BLOCKER_CONTRADICTION')
            return journal
        if _stamp(obs['observed_at'])<clock:_fail('OBSERVATION_CLOCK_REVERSED')
    def append(state,sha,why):
        if len(journal['events'])>=64:_blocked('JOURNAL_CAPACITY')
        body=dict(sequence=len(journal['events'])+1,previous_sha256=journal['tip_sha256'],state=state,
            observation_sha256=sha,observed_at=obs['observed_at'],reason_codes=why)
        event=dict(body,event_sha256=digest(body));journal['events'].append(event);journal['tip_sha256']=event['event_sha256']
    if not journal['events']:append('REQUESTED',None,[])
    append('READ_ONLY_FACTS_OBSERVED',observation_sha,[])
    append('ADMISSION_BLOCKED',observation_sha,reasons)
    return journal



def _check_issuance_runtime(closure, read_context, budget):
    from codex_cycle_contract import MAX_FILE_BYTES, code_paths
    from prospective_inputs import _LocalByteBudget, _bounded_bytes, _local_path

    if set(code_paths(ROOT)) != set(closure):
        _blocked('REVIEWED_RUNTIME_CLOSURE_MISMATCH')
    for relative, expected in closure.items():
        target = _local_path(ROOT, relative, budget.check)
        raw = _bounded_bytes(target, _LocalByteBudget(read_context, MAX_FILE_BYTES), budget.check)
        if hashlib.sha256(raw).hexdigest() != expected:
            _blocked('REVIEWED_RUNTIME_CODE_MISMATCH')
    budget.check()


def _issuance_remaining(budget):
    seconds = budget.deadline - monotonic()
    if seconds <= 0:
        _blocked('DEADLINE_EXCEEDED')
    return seconds


_ISSUANCE_NUMERIC_OFFSET = re.compile(
    r'[0-9]{4}-?[0-9]{2}-?[0-9]{2}[Tt ][0-9]{2}(?::?[0-9]{2}){0,2}'
    r'(?:[.,][0-9]+)?[+-]([0-9]{2})(?::?([0-9]{2}))?'
    r'(?::?([0-9]{2}))?(?:[.,][0-9]+)?'
)


def _require_issuance_offsets(value, budget):
    """Reject normalized-away offsets in owned structured staging inputs."""
    pending = [value]
    while pending:
        budget.check()
        current = pending.pop()
        if type(current) is dict:
            pending.extend(current.values())
        elif type(current) is list:
            pending.extend(current)
        elif type(current) is str and len(current) <= 64:
            match = _ISSUANCE_NUMERIC_OFFSET.fullmatch(current)
            if match and any(int(part) >= limit for part, limit in
                             zip(match.groups(default='0'), (24, 60, 60))):
                _fail('ISSUANCE_TIMESTAMP_OFFSET_INVALID')


def _first_forecast_window(cutoff):
    return cutoff.replace(minute=cutoff.minute // 10 * 10, second=0, microsecond=0) + timedelta(minutes=10)


def _check_private_issuance_clock(observed, prospective_until, budget, *, previous=None):
    # Wall time gates only the private command. It does not authenticate the
    # supplied observation, introduce a caller clock, or authorize issuance.
    budget.check()
    now = datetime.now(timezone.utc)
    if previous is not None and now < previous:
        _blocked('PRIVATE_ISSUANCE_WALL_CLOCK_REVERSED')
    if now < observed:
        _blocked('PRIVATE_ISSUANCE_OBSERVATION_IN_FUTURE')
    if now >= prospective_until:
        _blocked('PRIVATE_ISSUANCE_WALL_WINDOW_CLOSED')
    return now


def _issuance_preparation(data, facts, observed_at, previous_journal, budget):
    """Execute with declared state and the selected model's immutable mandatory set.

    Local file equality does not attest the supplied policy, times, loaded
    historical runtime, or eligibility for official P0. No write is attempted.
    """
    from codex_cycle_contract import MAX_TOTAL_BYTES
    from production_registry import (_JST, _core_policy, _core_result, _digest,
        _expected, _night, _operational_night, _snapshot, prepare_issuance_commit)
    from prospective_inputs import InputCapacityError, ProspectiveReadContext

    try:
        data = _owned(data, budget)
        _fields(data, {'snapshot', 'policy', 'expected_ref_sha', 'expected_event_sha256',
                       'operation_id', 'planned_start', 'model', 'bundle'})
        policy = data['policy']
        policy_sha = _core_policy(policy, budget)
        if policy['repository'] != {'id': facts['repository_id'], 'full_name': facts['repository']}:
            _fail('ISSUANCE_REPOSITORY_MISMATCH')
        state = _snapshot(data['snapshot'], policy, policy_sha, budget)[-1]
        _expected(state, data['expected_ref_sha'], data['expected_event_sha256'])
        event = state['events'][state['pointer']['event_sha256']]
        if (not facts['merged'] or facts['draft'] or
                event['merged_ref']['commit_sha'] != facts['merge_commit_sha']):
            _blocked('SELECTED_EVENT_MERGE_NOT_ESTABLISHED')
        if event['code_sha256'] not in policy['compatible_code_sha256']:
            _blocked('CODE_COMPATIBILITY_NOT_ESTABLISHED')

        model, bundle = data['model'], data['bundle']
        if type(model) is not dict or type(bundle) is not dict:
            _fail('COMPOSITE_OBJECT_REQUIRED')
        _require_issuance_offsets([observed_at, data['planned_start'], model, bundle,
            previous_journal, state['events'], state['issuances'], state['proofs']], budget)
        identity = _digest({k: v for k, v in model.items() if k not in ('model_id', 'model_sha256')}, budget)
        if (model['model_id'] != identity or model['model_sha256'] != identity or
                event['model_sha256'] != identity or model['protocol_sha256'] != event['protocol_sha256']):
            _fail('SELECTED_COMPOSITE_IDENTITY_MISMATCH')
        mandatory = model['mandatory_capabilities']
        if type(mandatory) is not list:
            _fail('MANDATORY_CAPABILITIES_REQUIRED')
        if not mandatory:
            _blocked('MANDATORY_CAPABILITIES_REQUIRED')
        closure = {row['path']: row['sha256'] for row in event['code_manifest']}
        observed = _stamp(observed_at)
        planned_start = _stamp(data['planned_start'])
        cutoff, end = _stamp(bundle['cutoff_time']), _stamp(bundle['forecast_end'])
        night = _night(bundle['operational_night'])
        first_window = _first_forecast_window(cutoff)
        if (not cutoff <= observed < min(planned_start, first_window) or
                not planned_start < end or _operational_night(planned_start) != night):
            _blocked('PRE_EXPLORATION_ISSUANCE_WINDOW_CLOSED')

        read_context = ProspectiveReadContext(_issuance_remaining(budget), MAX_TOTAL_BYTES)
        read_context.deadline = budget.deadline
        _check_issuance_runtime(closure, read_context, budget)
        import composite_inference as composite
        if Path(getattr(composite, '__file__', '')).resolve() != ROOT / 'src/composite_inference.py':
            _blocked('REVIEWED_RUNTIME_MODULE_ORIGIN_MISMATCH')
        if Path(getattr(composite.adapters, '__file__', '')).resolve() != ROOT / 'src/output_adapters.py':
            _blocked('REVIEWED_RUNTIME_MODULE_ORIGIN_MISMATCH')
        _fields(model, composite.MODEL_FIELDS)
        _fields(bundle, composite.BUNDLE_FIELDS)
        _fields(model['code_manifest'], set(composite.adapters.required_code_paths()))
        if any(closure.get(path) != sha for path, sha in model['code_manifest'].items()):
            _fail('SELECTED_COMPOSITE_CLOSURE_MISMATCH')
        actual = composite.predict_composite(model, bundle, budget_seconds=_issuance_remaining(budget))
        budget.check()
        if actual['status'] != 'EXECUTED':
            raise _Rejected('REGISTERED_COMPOSITE_DID_NOT_EXECUTE',
                            'FAIL' if actual['status'] == 'FAIL' else 'BLOCKED')
        windows = set()
        for capability, source in (('spatial_rows', 'universe_rows'), ('unit_predictions', 'forecast_rows')):
            if actual['outputs'].get(capability, {}).get('execution_status') == 'EXECUTED':
                component = model['output_bindings'][capability]['component_id']
                for row in bundle['inputs'][component][source]:
                    budget.check()
                    if 'window_start_jst' not in row:
                        _blocked('EXECUTED_SPATIAL_WINDOW_NOT_SUPPLIED')
                    when = _stamp(row['window_start_jst'])
                    if not observed < when or when + timedelta(minutes=10) > end:
                        _blocked('EXECUTED_SPATIAL_WINDOW_EXPIRED')
                    windows.add(when)
        if not windows:
            _blocked('EXECUTED_SPATIAL_WINDOW_NOT_SUPPLIED')
        if max(windows) + timedelta(minutes=10) <= planned_start:
            _blocked('EXECUTED_SPATIAL_WINDOWS_END_BEFORE_PLANNED_START')

        record = dict(schema_version='habu-registry-inference-v1', operation_id=data['operation_id'],
            operational_night=night, cutoff_time=bundle['cutoff_time'], training_cutoff=model['training_cutoff'],
            forecast_windows=[when.astimezone(_JST).isoformat() for when in sorted(windows)],
            selected_event_sha256=event['event_sha256'], model_sha256=identity, code_sha256=event['code_sha256'],
            input_bundle_sha256=actual['input_bundle_sha256'],
            component_receipts_sha256=_digest(actual['component_receipts'], budget),
            output=dict(prediction=actual, planned_start=data['planned_start'],
                        formal_product_policy_status='NOT_ATTESTED'))
        proposal = prepare_issuance_commit(data['snapshot'], record, policy=policy, observed_at=observed_at,
            expected_ref_sha=data['expected_ref_sha'], expected_event_sha256=data['expected_event_sha256'],
            budget_seconds=_issuance_remaining(budget))
        if proposal['status'] == 'ISSUANCE_COMMIT_PROPOSED':
            _check_issuance_runtime(closure, read_context, budget)
        return proposal
    except _Rejected as exc:
        return _core_result(exc.status, exc.code)
    except (TimeoutError, InputCapacityError):
        return _core_result('BLOCKED', 'ISSUANCE_RUNTIME_BUDGET')
    except OSError:
        return _core_result('BLOCKED', 'REVIEWED_RUNTIME_SOURCE_UNAVAILABLE')
    except (ValueError, KeyError, TypeError, OverflowError, RecursionError, UnicodeError):
        return _core_result('FAIL', 'MALFORMED_ISSUANCE_PREPARATION')


def _read_private_issuance(reference, budget):
    from master_inventory import local_path

    root, relative, expected = reference
    _sha(expected)
    relative = _path(relative)
    if (not relative.startswith('config/') or not relative.endswith('.json') or
            any(part.casefold() in {'incoming', 'original'} for part in relative.split('/'))):
        _fail('PRIVATE_ISSUANCE_CONFIG_PATH_REQUIRED')
    budget.check()
    try:
        root = local_path(root)
        if not root.is_dir():
            _blocked('PRIVATE_ISSUANCE_INPUT_UNAVAILABLE')
        path = local_path(root.resolve(strict=True), relative)
        for parent in path.parents:
            budget.check()
            marker = parent / '.git'
            if (marker.exists() or marker.is_symlink() or
                    ((parent / 'HEAD').is_file() and (parent / 'objects').is_dir() and
                     (parent / 'refs').is_dir())):
                _fail('PRIVATE_ISSUANCE_GIT_ROOT_FORBIDDEN')
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            _fail('PRIVATE_ISSUANCE_REGULAR_UNLINKED_FILE_REQUIRED')
        limit = TOTAL_LIMIT - budget.input_bytes
        if info.st_size > limit:
            _blocked('PRIVATE_ISSUANCE_INPUT_CAPACITY')
        with path.open('rb') as source:
            opened = os.fstat(source.fileno())
            if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or
                    (info.st_dev, info.st_ino) != (opened.st_dev, opened.st_ino)):
                _fail('PRIVATE_ISSUANCE_INPUT_CHANGED')
            raw = source.read(limit + 1)
        budget.check()
    except _Rejected:
        raise
    except OSError:
        _blocked('PRIVATE_ISSUANCE_INPUT_UNAVAILABLE')
    except ValueError:
        _fail('PRIVATE_ISSUANCE_PATH_INVALID')
    budget.input_bytes += len(raw)
    if len(raw) > limit:
        _blocked('PRIVATE_ISSUANCE_INPUT_CAPACITY')
    if hashlib.sha256(raw).hexdigest() != expected:
        _fail('PRIVATE_ISSUANCE_INPUT_HASH_MISMATCH')
    budget.check()
    return raw


def stage_operation(operation,request,observation,*,journal=None,controller_code_binding,
                    budget_seconds=30,issuance_preparation=None):
    """Normalize declared facts and optionally prepare an unpublished issue proposal."""
    return _stage_operation(operation, request, observation, journal=journal,
        controller_code_binding=controller_code_binding, budget_seconds=budget_seconds,
        issuance_preparation=issuance_preparation)


def _stage_operation(operation, request, observation, *, journal, controller_code_binding,
                     budget_seconds, issuance_preparation=None, private_reference=None):
    result=dict(schema_version='habu-controller-readonly-result-v1',status='FAIL',write_status='BLOCKED',
        decision='NEED_MORE_DATA',reason_codes=[],facts={},source_refs=[],journal=None,
        completed_stage=None,required_stages=[],**FLAGS)
    try:
        budget=_Budget(budget_seconds)
        small=_owned(dict(operation=operation,request=request,journal=journal,code=controller_code_binding),budget)
        operation,request,journal,code=(small[k] for k in ('operation','request','journal','code'))
        _request(operation,request);_binding(code)
        if (issuance_preparation is not None or private_reference is not None) and operation != 'issue_current_prediction':
            _fail('ISSUANCE_PREPARATION_OPERATION_MISMATCH')
        result['required_stages']=list(REQUIRED_STAGES[operation])
        obs=_observation_copy(observation,budget)
        facts,refs=_normalize(obs,request,code,budget)
        reasons=list(MISSING_GATES)
        if facts['visibility']=='PUBLIC':reasons.append('PRIVATE_ARTIFACT_PUBLICATION_NOT_APPROVED')
        if not facts['merged']:reasons.append('PR_NOT_MERGED')
        if facts['draft']:reasons.append('PR_DRAFT')
        reasons=sorted(reasons)
        obs_sha=digest(dict(facts=facts,source_refs=refs,observed_at=obs['observed_at'],controller_code_binding=code))
        staged=_journal(journal,operation,request,code,obs,obs_sha,reasons)
        budget.check()
        if len(canonical_bytes(staged))>TOTAL_LIMIT:_blocked('JOURNAL_CAPACITY')
        result.update(status='BLOCKED',reason_codes=reasons,facts=facts,source_refs=refs,journal=staged,
                      completed_stage='READ_ONLY_FACTS_OBSERVED_UNATTESTED')
        if private_reference is not None:
            raw = _read_private_issuance(private_reference, budget)
            issuance_preparation = _json(raw.decode('utf-8'))
            if type(issuance_preparation) is not dict:
                _fail('PRIVATE_ISSUANCE_INPUT_OBJECT_REQUIRED')
            clocks = [obs['observed_at'], issuance_preparation['bundle']['cutoff_time'],
                      issuance_preparation['planned_start']]
            _require_issuance_offsets(clocks, budget)
            observed, cutoff, planned_start = map(_stamp, clocks)
            if observed < cutoff:
                _blocked('PRIVATE_ISSUANCE_CUTOFF_AFTER_OBSERVATION')
            prospective_until = min(planned_start, _first_forecast_window(cutoff))
            wall_started = _check_private_issuance_clock(observed, prospective_until, budget)
        if issuance_preparation is not None:
            prepared = _issuance_preparation(issuance_preparation, facts, obs['observed_at'], journal, budget)
            if private_reference is not None:
                if prepared['status'] == 'ISSUANCE_COMMIT_PROPOSED':
                    _read_private_issuance(private_reference, budget)
                    _check_private_issuance_clock(observed, prospective_until, budget, previous=wall_started)
                result['preparation_sha256'] = private_reference[2]
            result['issuance_preparation'] = prepared
    except _Rejected as exc:result.update(status=exc.status,reason_codes=[exc.code])
    except (ValueError,TypeError,KeyError,IndexError,OverflowError,UnicodeError,RecursionError):
        result.update(status='FAIL',reason_codes=['MALFORMED_CONTROLLER_DATA'])
    return result


def _private_issuance_summary(result):
    proposal = result.get('issuance_preparation', {})
    computed = proposal.get('computed', {})
    pending = proposal.get('pending') or {}
    status = 'FAIL' if proposal.get('status') == 'FAIL' else result['status']
    return dict(schema_version='habu-private-issuance-preparation-v1',
        status=status, write_status='BLOCKED', reason_codes=result['reason_codes'],
        proposal_status=proposal.get('status', 'NOT_PREPARED'),
        proposal_reason_codes=proposal.get('reason_codes', []), version=computed.get('version'),
        output_sha256=computed.get('output_sha256'), commit_spec_sha256=pending.get('spec_sha256'),
        preparation_sha256=result.get('preparation_sha256'), **FLAGS)


def main():
    parser = argparse.ArgumentParser(description='Read JSON staging request on stdin; no authentication or write authority.')
    parser.add_argument('--private-issuance-root', type=Path, help='Private preparation directory outside Git')
    parser.add_argument('--private-issuance-path', help='Relative config/*.json preparation input')
    parser.add_argument('--private-issuance-sha256', help='SHA-256 of the exact private preparation bytes')
    args = parser.parse_args()
    reference = args.private_issuance_root, args.private_issuance_path, args.private_issuance_sha256
    private = any(value is not None for value in reference)
    if private and not all(reference):
        parser.error('Private issuance preparation requires root, relative path and SHA-256 together.')
    try:
        raw=sys.stdin.buffer.read(TOTAL_LIMIT+1)
        if len(raw)>TOTAL_LIMIT:_blocked('CLI_INPUT_CAPACITY')
        value=_json(raw);_fields(value,{'operation','request','observation','journal','controller_code_binding'})
        result=_stage_operation(value['operation'], value['request'], value['observation'],
            journal=value['journal'], controller_code_binding=value['controller_code_binding'],
            budget_seconds=30, private_reference=reference if private else None)
    except _Rejected as exc:
        result=dict(status=exc.status,reason_codes=[exc.code],**FLAGS)
    if private:
        result = _private_issuance_summary(result)
    print(json.dumps(result,ensure_ascii=False,separators=(',',':')))
    return 1 if result['status']=='FAIL' else 2


if __name__=='__main__':raise SystemExit(main())
