"""Bounded command-scoped declared requests; no job/root/execution admission."""
from datetime import timedelta
import hashlib
import json
import math

from master_contracts import canonical_bytes,digest
from development_handoff import (DEVELOPMENT_FLAGS as FLAGS, _fields, _hash, _integer,
    _time, _own, _report_tree, _read_report_blob, _report_json, _report_bytes,
    propose_development_request)

VERSION='habu-backend-development-request-v1'
PARENT='src/research_pdca_adapter.py'
ADAPTER='src/evaluation/stage1_source_adapter.py'
PROTOCOL='schemas/development-job.json'
ABSENT_PARENT='0a98ed940e461b49dd85802e2dd4f0006f3245a1e8ff55c831120aec9b8ba104'
PRESENT_PARENTS=frozenset()  # Add only exact independently reviewed/deployed versions.
PROFILE_REFS={
    PARENT:dict(path=PARENT,sha256=ABSENT_PARENT,size_bytes=29644),
    ADAPTER:dict(path=ADAPTER,sha256='388bf18b1f4f90fb29d48fe0c4f58579bae925d281f99b27eb0e79baa038ada6',size_bytes=37345),
    PROTOCOL:dict(path=PROTOCOL,sha256='637b352c6106415c3a2c1ba5b6990749fd599264d23f2e48747d556210473ab8',size_bytes=4894),
}


def _budget(): return dict(bytes=0,reads=[],cache={})
def _ref(path,raw): return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),size_bytes=len(raw))
def _none(status): return dict(status=status,record=None,**FLAGS)


def _document(raw):
    """Bounded terminal metadata can contain real finite elapsed/policy floats."""
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result: raise ValueError('Duplicate backend metadata JSON key')
            result[key]=value
        return result
    try:
        result=json.loads(raw,object_pairs_hook=unique,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite backend metadata')))
        pending=[(result,0)]; count=0
        while pending:
            value,depth=pending.pop(); count+=1
            if count>10000 or depth>12: raise ValueError('CAPACITY_BLOCKED: backend metadata nodes/depth')
            kind=type(value)
            if kind in (dict,list):
                if count+len(pending)+len(value)>10000: raise ValueError('CAPACITY_BLOCKED: backend metadata width')
                if kind is dict and any(type(k) is not str or len(k)>512 for k in value):
                    raise ValueError('Backend metadata key capacity')
                pending.extend((child,depth+1) for child in (value.values() if kind is dict else value))
            elif kind is str:
                if len(value)>1024: raise ValueError('Backend metadata string capacity')
            elif kind is int:
                if value.bit_length()>64: raise ValueError('Backend metadata integer capacity')
            elif kind is float:
                if not math.isfinite(value): raise ValueError('Nonfinite backend metadata float')
            elif kind not in (bool,type(None)): raise ValueError('Backend metadata JSON type')
        return result
    except (UnicodeError,RecursionError) as exc: raise ValueError('Invalid backend metadata JSON') from exc


def _command(command):
    command=_own(command)
    _fields(command,{'repository','issue','night','text_sha256','command_id'})
    if command['repository']!='haji84/habuAI-private':
        raise ValueError('Canonical backend development repository required')
    _integer(command['issue'],1,2**53-1)
    from master_contracts import validate_night
    validate_night(command['night']); _hash(command['text_sha256']); _hash(command['command_id'])
    if digest({k:v for k,v in command.items() if k!='command_id'})!=command['command_id']:
        raise ValueError('Backend command identity mismatch')
    return command


def _binding(command,receipt):
    command=_command(command)
    if (canonical_bytes(receipt['command'])!=canonical_bytes(command) or
            receipt.get('schema_version')!='1.0' or receipt.get('state') not in ('COMPUTED','HANDLED')):
        raise ValueError('Terminal command receipt required')
    run=_hash(receipt['run_id'])
    if receipt['run_branch']!='pdca/run-'+run:
        raise ValueError('Terminal run branch mismatch')
    return dict(command=command,parent_run_id=run,source_commit=_hash(receipt['source_commit'],40),
        command_source_commit=_hash(receipt.get('command_source_commit',receipt['source_commit']),40),
        bundle_commit=_hash(receipt['bundle_commit'],40),result_sha256=_hash(receipt['result_sha256']))


def _paths(binding):
    command=binding['command']; night=command['night']; identity=command['command_id']
    return ('pdca/command-'+identity,
        f'reports/pdca/{night}/bridge/command-{identity}.json',
        f'reports/pdca/{night}/bridge/development-request-{identity}.json',
        f"reports/pdca/{night}/runs/{binding['parent_run_id']}/")


def _read(transport,commit,path,budget):
    tree=_report_tree(transport,commit,path)
    if not tree: return None
    if set(tree)!={path}: raise ValueError('Exact fixed backend artifact path required')
    return _read_report_blob(transport,commit,path,tree[path],budget)


def _evidence_ref(value,path):
    _fields(value,{'path','sha256','size_bytes'})
    if value['path']!=path: raise ValueError('Fixed finalization evidence path required')
    _hash(value['sha256']); _integer(value['size_bytes'],1,262144)
    return value


def _envelope(binding,evidence,observed,expires):
    _,_,_,prefix=_paths(binding)
    _evidence_ref(evidence,prefix+'finalization_checkpoint.json')
    source_profiles=[dict(PROFILE_REFS[p]) for p in (PARENT,ADAPTER)]
    protocol=dict(kind='ENGINEERING_REQUEST_CONTRACT_V1',ref=dict(PROFILE_REFS[PROTOCOL]))
    command=binding['command']
    provenance=dict(master_issue='haji84/AI-#1642',repository=command['repository'],
        root_command_id=command['command_id'],parent_command_id=command['command_id'],
        parent_run_id=binding['parent_run_id'],operational_night=command['night'],
        source_commit=binding['source_commit'],protocol_sha256=protocol['ref']['sha256'],
        observed_at=observed,expires_at=expires,evidence=[evidence])
    need=dict(kind='CODE_CAPABILITY',capability_id='CONFIGURED_STAGE1_PARENT_DISPATCH_V2',
        capability_installed=False,prerequisite_schema='habu-stage1-source-contract-v2',prerequisite_deployed=True)
    decision=propose_development_request(provenance,need)
    identity=dict(schema_version=VERSION,binding=binding,protocol=protocol,
        source_profiles=source_profiles,evidence=[evidence])
    return dict(schema_version=VERSION,binding=binding,protocol=protocol,
        source_profiles=source_profiles,observation_id=digest(identity),
        observed_at=observed,expires_at=expires,decision=decision,decision_sha256=digest(decision),**FLAGS)


def inspect_backend_development_record(record):
    """Reconstruct declared consistency only; saved JSON is never authentication."""
    record=_own(record)
    _fields(record,{'schema_version','binding','protocol','source_profiles','observation_id',
        'observed_at','expires_at','decision','decision_sha256',*FLAGS})
    binding=record['binding']
    _fields(binding,{'command','parent_run_id','source_commit','command_source_commit','bundle_commit','result_sha256'})
    _command(binding['command'])
    for key in ('parent_run_id','result_sha256'): _hash(binding[key])
    for key in ('source_commit','command_source_commit','bundle_commit'): _hash(binding[key],40)
    try: evidence=record['decision']['request']['provenance']['evidence']
    except (KeyError,TypeError) as exc: raise ValueError('Exact backend request decision required') from exc
    if type(evidence) is not list or len(evidence)!=1: raise ValueError('One bound finalization ref required')
    expected=_envelope(binding,evidence[0],record['observed_at'],record['expires_at'])
    if canonical_bytes(expected)!=canonical_bytes(record):
        raise ValueError('Backend observation scope/identity/typed flags changed')
    return record


def _prepare(transport,command,receipt,*,trusted_default_source,observed_at,budget):
    """Verify actual terminal Git evidence and observe closed software profiles."""
    if command.get('repository')!='haji84/habuAI-private': return _none('OUT_OF_SCOPE')
    if receipt.get('state')=='HANDLED': return _none('LEGACY_HANDLED_NO_BACKFILL')
    binding=_binding(command,receipt); source=binding['source_commit']
    if source!=_hash(trusted_default_source,40): return _none('SOURCE_RECONCILIATION_REQUIRED')
    raw_profiles={}
    for path in (PARENT,ADAPTER,PROTOCOL):
        raw=_read(transport,source,path,budget)
        if raw is None: return _none('PREREQUISITE_REQUIRED')
        raw_profiles[path]=raw
    parent_sha=hashlib.sha256(raw_profiles[PARENT]).hexdigest()
    if parent_sha in PRESENT_PARENTS: return _none('ALREADY_IMPLEMENTED')
    if parent_sha!=ABSENT_PARENT: return _none('UNMAPPED_SOURCE_PROFILE')
    for path in (ADAPTER,PROTOCOL):
        if _ref(path,raw_profiles[path])!=PROFILE_REFS[path]: return _none('PREREQUISITE_REQUIRED')
    from pdca_bridge import verify_handled_receipt
    terminal=dict(receipt,state='HANDLED'); terminal.pop('development_request_ref',None)
    result=verify_handled_receipt(transport,command,terminal,trusted_default_source)
    _,_,_,prefix=_paths(binding)
    manifest_path=f"reports/pdca/{command['night']}/bridge/recovery-{binding['parent_run_id']}.json"
    raw=_read(transport,binding['bundle_commit'],manifest_path,budget)
    if raw is None: raise ValueError('Missing terminal recovery manifest')
    manifest=_document(raw)
    if (manifest['source_commit']!=source or manifest['run_id']!=binding['parent_run_id'] or
            manifest['night']!=command['night']): raise ValueError('Terminal recovery identity changed')
    evidence_raw=_read(transport,binding['bundle_commit'],prefix+'evidence_manifest.json',budget)
    if evidence_raw is None: raise ValueError('Missing terminal source evidence')
    evidence=_document(evidence_raw); inventory=manifest['identity']['inputs']
    if (digest(evidence)!=result['input_manifest_sha256'] or
            digest(inventory)!=evidence['input_snapshot_sha256']):
        raise ValueError('Terminal source inventory changed')
    for path,raw in raw_profiles.items():
        expected=dict(sha256=hashlib.sha256(raw).hexdigest(),size_bytes=len(raw))
        if canonical_bytes(inventory.get(path))!=canonical_bytes(expected):
            raise ValueError('Pinned source/schema differs from verified inventory')
    final_path=prefix+'finalization_checkpoint.json'
    entries=[item for item in manifest['files'] if item.get('path')==final_path]
    if len(entries)!=1: raise ValueError('One complete finalization evidence ref required')
    final_ref=_evidence_ref(entries[0],final_path)
    final_raw=_read(transport,binding['bundle_commit'],final_path,budget)
    if final_raw is None or canonical_bytes(_ref(final_path,final_raw))!=canonical_bytes(final_ref):
        raise ValueError('Finalization evidence raw bytes changed')
    # The actual bridge verifier above already checked the checkpoint/result chain.
    observed=_time(observed_at)
    try: expires=observed+timedelta(hours=24)
    except OverflowError as exc: raise ValueError('Backend observation expiry outside supported clock') from exc
    record=_envelope(binding,final_ref,observed.isoformat(),expires.isoformat())
    return dict(status='DECLARED_SCOPE_PROPOSAL',record=inspect_backend_development_record(record),**FLAGS)


def prepare_backend_development_request(transport,command,receipt,*,trusted_default_source,observed_at):
    return _prepare(transport,command,receipt,trusted_default_source=trusted_default_source,
        observed_at=observed_at,budget=_budget())


def _immutable_history(transport,head,source,path):
    additions=0
    lines=transport.git('rev-list','--first-parent','--parents',head,'^'+source).decode('ascii').splitlines()
    for line in lines:
        words=line.split()
        if len(words)!=2: raise ValueError('Merged development-request command history')
        delta=transport.git('diff','--name-status','--no-renames','-z',words[1],words[0],'--',path)
        if delta:
            if delta!=b'A\0'+path.encode()+b'\0':
                raise ValueError('Immutable development request was modified/deleted')
            additions+=1
    if additions!=1: raise ValueError('Development request must be added exactly once after its source')


def _verify(transport,head,command,receipt,budget):
    binding=_binding(command,receipt); _,_,path,_=_paths(binding)
    reference=receipt['development_request_ref']
    _fields(reference,{'path','sha256','size_bytes'})
    if reference['path']!=path: raise ValueError('Fixed command development ref required')
    _hash(reference['sha256']); _integer(reference['size_bytes'],1,1048576)
    transport.assert_report_tree(head,binding['command_source_commit'])
    raw=_read(transport,head,path,budget)
    if raw is None or canonical_bytes(_ref(path,raw))!=canonical_bytes(reference):
        raise ValueError('Development request physical hash/size changed')
    value=inspect_backend_development_record(_report_json(raw))
    if canonical_bytes(value['binding'])!=canonical_bytes(binding) or _report_bytes(value)!=raw:
        raise ValueError('Development request changed terminal binding/canonical bytes')
    _immutable_history(transport,head,binding['command_source_commit'],path)
    # Recheck exact code/schema bytes; neither declaration nor commit author is authentication.
    for reference in [*value['source_profiles'],value['protocol']['ref']]:
        source_raw=_read(transport,binding['source_commit'],reference['path'],budget)
        if source_raw is None or canonical_bytes(_ref(reference['path'],source_raw))!=canonical_bytes(reference):
            raise ValueError('Historical development source profile changed')
    _,_,_,prefix=_paths(binding)
    manifest_path=f"reports/pdca/{command['night']}/bridge/recovery-{binding['parent_run_id']}.json"
    manifest_raw=_read(transport,binding['bundle_commit'],manifest_path,budget)
    if manifest_raw is None: raise ValueError('Historical terminal recovery manifest absent')
    manifest=_document(manifest_raw)
    if (manifest.get('source_commit')!=binding['source_commit'] or
            manifest.get('run_id')!=binding['parent_run_id'] or manifest.get('night')!=command['night']):
        raise ValueError('Historical terminal recovery identity changed')
    for reference in [*value['source_profiles'],value['protocol']['ref']]:
        expected={key:reference[key] for key in ('sha256','size_bytes')}
        if canonical_bytes(manifest['identity']['inputs'].get(reference['path']))!=canonical_bytes(expected):
            raise ValueError('Historical source profile differs from terminal inventory')
    path=prefix+'finalization_checkpoint.json'
    entries=[item for item in manifest['files'] if item.get('path')==path]
    if len(entries)!=1: raise ValueError('Historical finalization ref missing/duplicate')
    reference=_evidence_ref(entries[0],path)
    declared=value['decision']['request']['provenance']['evidence']
    if canonical_bytes(declared)!=canonical_bytes([reference]):
        raise ValueError('Declared finalization evidence differs from terminal bundle')
    raw=_read(transport,binding['bundle_commit'],path,budget)
    if raw is None or canonical_bytes(_ref(path,raw))!=canonical_bytes(reference):
        raise ValueError('Historical finalization evidence bytes changed')
    return value


def verify_backend_development_request(transport,command,receipt):
    """Verify a new receipt's optional historical ref, without refreshing expiry."""
    binding=_binding(command,receipt); branch,_,_,_=_paths(binding)
    head=transport.head(branch)
    if head is None: raise ValueError('Development request command branch absent')
    return _verify(transport,head,command,receipt,_budget())


def emit_backend_development_request(transport,api,command,receipt,*,expected_head,observed_at):
    """Atomically add a fixed proposal plus COMPUTED receipt; no execution dispatch."""
    if command.get('repository')!='haji84/habuAI-private': return expected_head,receipt
    if receipt.get('state')=='HANDLED': return expected_head,receipt
    from pdca_bridge import RecoveryBlocked
    binding=_binding(command,receipt); branch,command_path,path,_=_paths(binding)
    _hash(expected_head,40)
    head=transport.head(branch)
    if head is None: raise RecoveryBlocked('Development command receipt absent; retry required')
    budget=_budget()
    raw=_read(transport,head,command_path,budget)
    if raw is None: raise ValueError('Development command receipt missing')
    # Existing receipts contain measured float time; do not use integer-only proposal parsing.
    remote=_document(raw)
    if (remote.get('schema_version')!='1.0' or
            canonical_bytes(remote.get('command'))!=canonical_bytes(command) or
            remote.get('run_id')!=binding['parent_run_id'] or
            remote.get('command_source_commit',remote.get('source_commit'))!=binding['command_source_commit']):
        raise ValueError('Observed command receipt identity/base changed')
    if 'development_request_ref' in remote:
        _verify(transport,head,command,remote,budget)
        if canonical_bytes(_binding(command,remote))!=canonical_bytes(binding):
            raise ValueError('Existing development request has a different terminal binding')
        return head,remote
    if head!=expected_head: raise RecoveryBlocked('Development command changed; reconcile before publication')
    prepared=_prepare(transport,command,receipt,
        trusted_default_source=api.default_source(),observed_at=observed_at,budget=budget)
    if prepared['record'] is None: return head,receipt
    if _hash(api.default_source(),40)!=binding['source_commit']: return head,receipt
    # A fixed orphaned/archived path cannot be adopted as a fresh observation.
    if _report_tree(transport,head,path): raise ValueError('Unreferenced existing development request cannot reset')
    data=_report_bytes(prepared['record']); updated=dict(receipt,development_request_ref=_ref(path,data))
    failure=None
    try:
        transport.publish(branch,binding['command_source_commit'],head,
            {path:data,command_path:canonical_bytes(updated)+b'\n'})
    except Exception as exc: failure=exc
    actual=transport.head(branch)
    if actual is None: raise RecoveryBlocked('Development publication unconfirmed; retry required') from failure
    observed_raw=_read(transport,actual,command_path,budget)
    if observed_raw is None or observed_raw!=canonical_bytes(updated)+b'\n':
        raise RecoveryBlocked('Development atomic receipt unconfirmed; retry computed run') from failure
    _verify(transport,actual,command,updated,budget)
    return actual,updated
