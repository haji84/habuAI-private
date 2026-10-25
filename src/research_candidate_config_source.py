"""Guarded candidate configuration declarations, never runner/source authority.

Every payload/code byte uses the caller's existing actual-byte ledger/deadline.
Cycle enumeration checks membership only: it cannot authenticate loaded Python,
native dependencies, historic availability, an issuer or a pre-reveal campaign.
"""
from __future__ import annotations

from pathlib import Path
import re

import codex_cycle_contract as cycle
import g0_forecast_contract as g0
from master_contracts import digest
from master_inventory import local_path
import prospective_inputs as pi
import research_model_adapter as models

VERSION = 'habu-research-candidate-config-source-v1'
FIELDS = {'schema_version', 'kind', 'feature_definition_sha256', 'candidate_config',
          'cycle', 'code_availability', 'readiness', 'usable_at'}
MAX_PROFILE_BYTES = 256*1024
MAX_CONFIG_BYTES = 64*1024
MAX_PHASE_BYTES = cycle.MAX_TOTAL_BYTES
RESERVED = {'sealed', 'confirmation', 'original', 'incoming', 'reports'}


class CandidateConfigSourceBlocked(ValueError):
    """A consistent declared configuration was not available before its boundary."""


def _fields(value, fields):
    if type(value) is not dict or set(value) != fields:
        raise ValueError('Exact candidate-config source fields required')


def _sha(value):
    if type(value) is not str or not pi.SHA256.fullmatch(value):
        raise ValueError('Candidate-config SHA-256 required')
    return value


def input_ref(value, *, purpose='profile'):
    g0._ref(value)
    path = value['path']
    if (any(part.casefold() in RESERVED for part in path.split('/')) or
            any(ord(char)<32 or ord(char)==127 for char in path)):
        raise ValueError('Reserved candidate-config source namespace')
    allowed = path.startswith(('config/', 'protocols/development/'))
    if purpose == 'cycle':
        allowed = path.startswith('protocols/development/cycles/') and path.endswith('.json')
    if not allowed:
        raise ValueError('Unsupported candidate-config source namespace')
    return value


def _runtime_path(path):
    cycle._relative(path)
    if (any(part.casefold() in RESERVED for part in path.split('/')) or
            any(ord(char)<32 or ord(char)==127 for char in path) or
            not ((path.startswith(('src/','scripts/')) and path.endswith('.py')) or
                 (path.startswith('schemas/') and path.endswith('.json')) or
                 path in {'requirements-analysis.txt','requirements-osm.txt'})):
        raise ValueError('Unsupported/reserved runtime code closure path')
    return path


def _stamps(node, check):
    _fields(node['readiness'], pi.READINESS_FIELDS)
    stamps = []
    for key in sorted(pi.READINESS_FIELDS):
        check()
        stamps.append(pi._time(node['readiness'][key]))
    return stamps, pi._time(node['usable_at'])


def _ready(node, check, *, parents=()):
    # Parse/check the entire declaration before classifying a valid late value.
    stamps, usable = _stamps(node, check)
    if usable != max(*stamps, *parents):
        raise ValueError('Declared usable_at differs from required readiness maximum')
    return usable


def _membership(root, expected, check):
    check()
    local_path(root)
    if expected is not None:
        for path in expected:
            check()
            target = local_path(root,path)
            if not target.exists():
                raise FileNotFoundError('Missing immutable runtime code: '+path)
    actual = set(cycle.code_paths(root))
    local_path(root)
    check()
    if expected is not None and actual != expected:
        raise ValueError('Current runtime code membership differs from immutable cycle')
    return actual


def recheck_research_candidate_config(root, receipt, *, context):
    """Parent post-fit/post-evaluation scan of original sizes and code membership.

    These additional reads use the same global ledger, outside the loader's
    first-read plus first-rescan 16MiB phase. No readiness or receipt is resealed.
    """
    if not isinstance(context, pi.ProspectiveReadContext):
        raise ValueError('Shared prospective read context required')
    expected = set(receipt['code_sha256_by_path'])
    _membership(root, expected, context.check)
    reader = g0.G0ArtifactReader(root, context)
    for ref in receipt['consumed_refs']:
        context.check()
        reader.read(ref, parse=False)
    _membership(root, expected, context.check)
    context.check()


def load_research_candidate_config(root, manifest_ref, *, heldout_night, fit_cutoff,
        forecast_cutoff, expected_feature_definition_sha256, context):
    """Return owned {config,receipt} only after the complete source closure scan.

    Missing files propagate as data gaps. Malformed declarations/hash/max drift
    raise ValueError; consistent late availability raises SourceBlocked. Neither
    a successful receipt nor its timestamps authenticate historic availability.
    """
    # Snapshot primitives before the first caller-controlled deadline callback.
    input_ref(manifest_ref)
    manifest_ref = dict(manifest_ref)
    if not isinstance(context, pi.ProspectiveReadContext):
        raise ValueError('Shared prospective read context required')
    expected_feature_definition_sha256 = _sha(expected_feature_definition_sha256)
    boundary = cycle.training_boundary(heldout_night, fit_cutoff, forecast_cutoff)
    initial_bytes = context.bytes_read

    def check():
        context.check()
        if context.bytes_read-initial_bytes > MAX_PHASE_BYTES:
            raise pi.InputCapacityError('CAPACITY_BLOCKED: candidate-config source phase actual bytes')

    class Reader(g0.G0ArtifactReader):
        def read(self, ref, **kwargs):
            check()
            result = super().read(ref, **kwargs)
            check()
            return result

    check()
    g0._capacity(manifest_ref['size_bytes'], MAX_PROFILE_BYTES, 'candidate source profile bytes')
    reader = Reader(root, context)
    profile = reader.read(manifest_ref, small=True)
    _fields(profile, FIELDS)
    if (profile['schema_version'] != VERSION or profile['kind'] != 'DEVELOPMENT_CANDIDATE_CONFIG_SOURCE' or
            _sha(profile['feature_definition_sha256']) != expected_feature_definition_sha256):
        raise ValueError('Candidate source profile version/kind/strict definition mismatch')
    config_binding, cycle_binding = profile['candidate_config'], profile['cycle']
    _fields(config_binding, {'ref','config_sha256','readiness','usable_at'})
    _fields(cycle_binding, {'ref','policy','readiness','usable_at'})
    _fields(cycle_binding['policy'], {'size_bytes','readiness','usable_at'})
    for node in (profile,config_binding,cycle_binding,cycle_binding['policy']):
        _stamps(node,check)
    input_ref(config_binding['ref'])
    input_ref(cycle_binding['ref'], purpose='cycle')
    g0._capacity(config_binding['ref']['size_bytes'], MAX_CONFIG_BYTES, 'candidate config bytes')
    g0._capacity(cycle_binding['ref']['size_bytes'], cycle.MAX_FILE_BYTES, 'immutable cycle bytes')
    # Namespace and ancestor preflight all known requested refs before payloads.
    for ref in (config_binding['ref'], cycle_binding['ref']):
        check()
        local_path(root, ref['path'])
    manifest = reader.read(cycle_binding['ref'], small=True)
    _fields(manifest, cycle.MANIFEST_FIELDS)
    if (manifest['schema_version'] != cycle.VERSION or manifest['kind'] != 'DEVELOPMENT_CONTRACT_ONLY' or
            type(manifest['cycle_id']) is not str or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',manifest['cycle_id']) or
            type(manifest['base_main_sha']) is not str or not re.fullmatch(r'[a-f0-9]{40}',manifest['base_main_sha'])):
        raise ValueError('Immutable cycle version/kind/identity/base SHA invalid')
    frozen = pi._time(manifest['frozen_at'])
    _fields(manifest['policy_ref'], {'path','sha256'})
    if manifest['policy_ref']['path'] != cycle.POLICY_PATH:
        raise ValueError('Fixed G0 policy path required')
    policy_ref = dict(manifest['policy_ref'], size_bytes=cycle_binding['policy']['size_bytes'])
    g0._ref(policy_ref)
    g0._capacity(policy_ref['size_bytes'], cycle.MAX_FILE_BYTES, 'G0 policy bytes')
    code_refs, availability = manifest['code_manifest'], profile['code_availability']
    if type(code_refs) is not list or type(availability) is not list:
        raise ValueError('Code closure/availability arrays required')
    g0._capacity(len(code_refs),cycle.MAX_REFERENCES,'runtime code references')
    g0._capacity(len(availability),cycle.MAX_REFERENCES,'code availability references')
    if not code_refs or len(availability)!=len(code_refs):
        raise ValueError('Bounded exact code closure/availability required')
    code_map, available = {}, {}
    for ref in code_refs:
        check()
        _fields(ref, {'path','sha256'})
        path = _runtime_path(ref['path'])
        if path in code_map:
            raise ValueError('Duplicate immutable code reference')
        code_map[path] = _sha(ref['sha256'])
    for node in availability:
        check()
        _fields(node, {'path','size_bytes','readiness','usable_at'})
        path = cycle._relative(node['path'])
        if path in available or path not in code_map:
            raise ValueError('Duplicate/extra code availability')
        ref = dict(path=path,sha256=code_map[path],size_bytes=node['size_bytes'])
        g0._ref(ref)
        g0._capacity(ref['size_bytes'],cycle.MAX_FILE_BYTES,'runtime code file bytes')
        local_path(root,path)
        available[path] = (ref, _ready(node,check))
    expected_paths = _membership(root,set(code_map),check)
    policy_usable = _ready(cycle_binding['policy'],check)
    prerequisites = [policy_usable, *(ready for ref,ready in available.values())]
    cycle_usable = _ready(cycle_binding,check,parents=prerequisites)
    config_usable = _ready(config_binding,check,parents=prerequisites)
    profile_usable = _ready(profile,check,parents=(cycle_usable,config_usable))
    if frozen > cycle_usable:
        raise ValueError('Cycle frozen_at follows its effective usable_at')
    all_refs = [manifest_ref,config_binding['ref'],cycle_binding['ref'],policy_ref,
                *(ref for ref,ready in available.values())]
    if len({ref['path'] for ref in all_refs}) != len(all_refs):
        raise ValueError('Source config/cycle/policy/code paths must be distinct')
    g0._capacity(2*sum(ref['size_bytes'] for ref in all_refs),MAX_PHASE_BYTES,
                 'candidate source complete declared first-read plus rescan bytes')
    config = reader.read(config_binding['ref'],small=True)
    config_sha = digest(config)
    check()
    models._v2_config(config,_sha(config_binding['config_sha256']),expected_feature_definition_sha256,check)
    if config_sha != config_binding['config_sha256']:
        raise ValueError('Candidate config canonical SHA differs from bound content')
    policy = reader.read(policy_ref,small=True)
    policy_sha = digest(policy)
    check()
    if policy_sha != cycle.POLICY_DIGEST:
        raise ValueError('Fixed G0 policy canonical digest drift')
    for ref,ready in available.values():
        check()
        reader.read(ref,parse=False)
    if 'HB-A1' in config['candidate_ids']:
        for path,sha in config['hba1_recipe']['implementation_sha256'].items():
            check()
            if code_map.get(path) != sha:
                raise ValueError('HB-A1 recipe differs from actual snapshot code bytes')
    _membership(root,expected_paths,check)
    reader.rescan()
    _membership(root,expected_paths,check)
    if profile_usable >= boundary or frozen >= boundary:
        raise CandidateConfigSourceBlocked('SOURCE_BLOCKED: configuration not available strictly before training boundary')
    receipt = dict(schema_version=VERSION,status='DECLARED_CONSISTENCY_ONLY',
        manifest_ref=manifest_ref,config_ref=dict(config_binding['ref']),cycle_ref=dict(cycle_binding['ref']),
        manifest_canonical_sha256=digest(profile),config_sha256=config_sha,cycle_canonical_sha256=digest(manifest),
        code_sha256_by_path=code_map,code_map_sha256=digest(code_map),
        policy_ref=policy_ref,policy_canonical_sha256=policy_sha,boundary=boundary.isoformat(),
        readiness=profile['readiness'],usable_at=profile_usable.isoformat(),
        consumed_refs=list(reader.refs.values()),consumed_sha256={path:ref['sha256'] for path,ref in reader.refs.items()},
        actual_read_bytes=context.bytes_read,validation_read_bytes=context.bytes_read-initial_bytes,
        source_authentication='NOT_ATTESTED',source_availability_authentication='CALLER_DEPENDENCY_REQUIRED',
        fit_authorized=False,selection_authorized=False,promotion_authorized=False,
        scientific_execution_authorized=False,official_issuance_authorized=False,production_activation_authorized=False,
        loaded_bytecode_authenticated=False,python_native_runtime_authenticated=False,
        trusted_campaign_authorized=False,trusted_pre_reveal_authorized=False,source_issuer_authenticated=False,
        confirmation_authorized=False)
    receipt['receipt_sha256'] = digest(receipt)
    result = dict(config=config,receipt=receipt)
    check()
    return result
