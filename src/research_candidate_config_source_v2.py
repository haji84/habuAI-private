"""Explicit cfgv3 source closure: declared consistency, never fit/authority.

The old loader/bodies are unchanged. All bytes use the caller's real context;
recipe maps bind physical snapshot files, not loaded code, packages or issuer.
"""
from __future__ import annotations

import re

import codex_cycle_contract as cycle
import g0_forecast_contract as g0
from master_inventory import local_path
import prospective_inputs as pi
import research_candidate_config_source as old
import research_candidate_preparation_v3 as preparation

VERSION='habu-research-candidate-config-source-v2'
FIELDS=old.FIELDS
MAX_PROFILE_BYTES=256*1024
MAX_CONFIG_BYTES=64*1024
MAX_PHASE_BYTES=16*1024**2
CandidateConfigSourceBlocked=old.CandidateConfigSourceBlocked


def load_research_candidate_config_v2(root,manifest_ref,*,heldout_night,fit_cutoff,
        forecast_cutoff,expected_feature_definition_sha256,context):
    """Return owned {config,receipt} after the fixed cfgv3 complete source scan.

    A valid late closure raises without a config/receipt. No backend, fitter,
    downstream forecast/evaluation reader or ambient cycle is invoked.
    """
    old.input_ref(manifest_ref)
    manifest_ref=dict(manifest_ref)  # Own primitives before the first callback.
    if not isinstance(context,pi.ProspectiveReadContext):
        raise ValueError('Existing shared prospective read context required')
    if type(context.max_bytes) is not int or not 0<context.max_bytes<=g0.MAX_TOTAL_READ_BYTES:
        raise ValueError('Existing global byte allowance must be positive and at most2GiB')
    if type(context.bytes_read) is not int or context.bytes_read<0:
        raise ValueError('Existing nonnegative actual byte ledger required')
    initial_bytes=context.bytes_read
    first_abort=None

    def check():
        nonlocal first_abort
        if first_abort is not None:raise first_abort
        try:
            context.check()
        except BaseException as error:
            if first_abort is None:first_abort=error
            raise
        if context.bytes_read-initial_bytes>MAX_PHASE_BYTES:
            raise pi.InputCapacityError('CAPACITY_BLOCKED: cfgv3 source phase actual bytes')

    def pure(function,*args):
        # Only this new pure helper's own JSON capacity is normalized. Reader
        # failures are outside this catch; an actual caller origin is sticky.
        try:
            value=function(*args,check)
        except preparation.ResearchCapacityBlocked as error:
            if first_abort is not None:raise first_abort
            raise pi.InputCapacityError('CAPACITY_BLOCKED: cfgv3 source owned JSON') from error
        if first_abort is not None:raise first_abort
        return value

    class Reader(g0.G0ArtifactReader):
        def read(self,ref,**kwargs):
            check();value=super().read(ref,**kwargs);check();return value

    check()
    if context.bytes_read>=context.max_bytes:
        raise pi.InputCapacityError('CAPACITY_BLOCKED: existing source allowance exhausted')
    remaining=context.remaining_seconds
    if not 0<remaining<=300:
        raise ValueError('Existing remaining elapsed allowance must be positive and at most300s')
    definition=old._sha(expected_feature_definition_sha256)
    # Only a delegated pure datetime conversion enters this narrow catch.
    # Caller checks remain outside it, so their own OverflowError is unchanged.
    check()
    try:
        boundary=cycle.training_boundary(heldout_night,fit_cutoff,forecast_cutoff)
    except OverflowError as error:
        raise ValueError('Candidate source training boundary exceeds datetime range') from error
    check()
    g0._capacity(manifest_ref['size_bytes'],MAX_PROFILE_BYTES,'cfgv3 source profile bytes')
    reader=Reader(root,context);profile=reader.read(manifest_ref,small=True)
    old._fields(profile,FIELDS)
    if (profile['schema_version']!=VERSION or profile['kind']!='DEVELOPMENT_CANDIDATE_CONFIG_SOURCE' or
            old._sha(profile['feature_definition_sha256'])!=definition):
        raise ValueError('Explicit source-v2 version/kind/definition required')
    config_binding,cycle_binding=profile['candidate_config'],profile['cycle']
    old._fields(config_binding,{'ref','config_sha256','readiness','usable_at'})
    old._fields(cycle_binding,{'ref','policy','readiness','usable_at'})
    old._fields(cycle_binding['policy'],{'size_bytes','readiness','usable_at'})
    for node in (profile,config_binding,cycle_binding,cycle_binding['policy']):
        old._stamps(node,check)
    old.input_ref(config_binding['ref']);old.input_ref(cycle_binding['ref'],purpose='cycle')
    g0._capacity(config_binding['ref']['size_bytes'],MAX_CONFIG_BYTES,'cfgv3 config bytes')
    g0._capacity(cycle_binding['ref']['size_bytes'],cycle.MAX_FILE_BYTES,'immutable cycle bytes')
    for ref in (config_binding['ref'],cycle_binding['ref']):
        check();local_path(root,ref['path'])
    manifest=reader.read(cycle_binding['ref'],small=True)
    old._fields(manifest,cycle.MANIFEST_FIELDS)
    if (manifest['schema_version']!=cycle.VERSION or manifest['kind']!='DEVELOPMENT_CONTRACT_ONLY' or
            type(manifest['cycle_id']) is not str or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',manifest['cycle_id']) or
            type(manifest['base_main_sha']) is not str or not re.fullmatch(r'[a-f0-9]{40}',manifest['base_main_sha'])):
        raise ValueError('Immutable cycle envelope invalid')
    frozen=pi._time(manifest['frozen_at'])
    old._fields(manifest['policy_ref'],{'path','sha256'})
    if manifest['policy_ref']['path']!=cycle.POLICY_PATH:
        raise ValueError('Fixed G0 policy path required')
    policy_ref=dict(manifest['policy_ref'],size_bytes=cycle_binding['policy']['size_bytes'])
    g0._ref(policy_ref);g0._capacity(policy_ref['size_bytes'],cycle.MAX_FILE_BYTES,'G0 policy bytes')
    code_refs,availability=manifest['code_manifest'],profile['code_availability']
    if type(code_refs) is not list or type(availability) is not list:
        raise ValueError('Explicit code closure and availability arrays required')
    g0._capacity(len(code_refs),cycle.MAX_REFERENCES,'runtime code references')
    g0._capacity(len(availability),cycle.MAX_REFERENCES,'code availability references')
    if not code_refs or len(availability)!=len(code_refs):
        raise ValueError('Exact complete code closure/availability required')
    code_map,available={},{}
    for ref in code_refs:
        check();old._fields(ref,{'path','sha256'});path=old._runtime_path(ref['path'])
        if path in code_map:raise ValueError('Duplicate immutable code path')
        code_map[path]=old._sha(ref['sha256'])
    for node in availability:
        check();old._fields(node,{'path','size_bytes','readiness','usable_at'})
        path=cycle._relative(node['path'])
        if path in available or path not in code_map:
            raise ValueError('Extra/duplicate code availability')
        ref=dict(path=path,sha256=code_map[path],size_bytes=node['size_bytes'])
        g0._ref(ref);g0._capacity(ref['size_bytes'],cycle.MAX_FILE_BYTES,'runtime code file bytes')
        local_path(root,path);available[path]=(ref,old._ready(node,check))
    expected_paths=old._membership(root,set(code_map),check)
    policy_usable=old._ready(cycle_binding['policy'],check)
    parents=[policy_usable,*(ready for ref,ready in available.values())]
    cycle_usable=old._ready(cycle_binding,check,parents=parents)
    config_usable=old._ready(config_binding,check,parents=parents)
    profile_usable=old._ready(profile,check,parents=(cycle_usable,config_usable))
    if frozen>cycle_usable:raise ValueError('Cycle freeze follows effective usable_at')
    all_refs=[manifest_ref,config_binding['ref'],cycle_binding['ref'],policy_ref,
              *(ref for ref,ready in available.values())]
    if len({ref['path'] for ref in all_refs})!=len(all_refs):
        raise ValueError('Source config/cycle/policy/code paths must be distinct')
    g0._capacity(2*sum(ref['size_bytes'] for ref in all_refs),MAX_PHASE_BYTES,
        'cfgv3 source complete first-read plus rescan declared bytes')
    config=pure(preparation._copy,reader.read(config_binding['ref'],small=True))
    config_sha=pure(preparation._digest,config)
    pure(preparation._config,config,old._sha(config_binding['config_sha256']),definition)
    if config_sha!=config_binding['config_sha256']:
        raise ValueError('Canonical config SHA differs from bound whole content')
    policy=reader.read(policy_ref,small=True);policy_sha=pure(preparation._digest,policy)
    if policy_sha!=cycle.POLICY_DIGEST:raise ValueError('Fixed canonical G0 policy drift')
    for ref,ready in available.values():
        check();reader.read(ref,parse=False)
    for recipe,key in ((config['hba1_recipe'],'implementation_sha256'),
                       (config['hba2_recipe'],'implementation_sha256'),
                       (config['hba2_recipe'],'requirements_sha256')):
        for path,sha in recipe[key].items():
            check()
            if code_map.get(path)!=sha:
                raise ValueError('Native recipe differs from actual snapshot code/requirement bytes: '+path)
    old._membership(root,expected_paths,check);reader.rescan();old._membership(root,expected_paths,check)
    if profile_usable>=boundary or frozen>=boundary:
        raise CandidateConfigSourceBlocked('SOURCE_BLOCKED: configuration not available strictly before training boundary')
    receipt=dict(schema_version=VERSION,status='DECLARED_CONSISTENCY_ONLY',
        manifest_ref=manifest_ref,config_ref=dict(config_binding['ref']),cycle_ref=dict(cycle_binding['ref']),
        manifest_canonical_sha256=pure(preparation._digest,profile),config_sha256=config_sha,
        cycle_canonical_sha256=pure(preparation._digest,manifest),code_sha256_by_path=code_map,
        code_map_sha256=pure(preparation._digest,code_map),policy_ref=policy_ref,policy_canonical_sha256=policy_sha,
        boundary=boundary.isoformat(),readiness=profile['readiness'],usable_at=profile_usable.isoformat(),
        consumed_refs=list(reader.refs.values()),consumed_sha256={path:ref['sha256'] for path,ref in reader.refs.items()},
        actual_read_bytes=context.bytes_read,validation_read_bytes=context.bytes_read-initial_bytes,
        source_authentication='NOT_ATTESTED',source_availability_authentication='CALLER_DEPENDENCY_REQUIRED',
        fit_authorized=False,selection_authorized=False,promotion_authorized=False,
        scientific_execution_authorized=False,official_issuance_authorized=False,production_activation_authorized=False,
        loaded_bytecode_authenticated=False,python_native_runtime_authenticated=False,
        trusted_campaign_authorized=False,trusted_pre_reveal_authorized=False,source_issuer_authenticated=False,
        confirmation_authorized=False)
    receipt['receipt_sha256']=pure(preparation._digest,receipt)
    result=pure(preparation._copy,dict(config=config,receipt=receipt))
    check()
    if context.bytes_read!=receipt['actual_read_bytes']:
        raise ValueError('Execution ledger changed after source receipt sealing')
    return result
