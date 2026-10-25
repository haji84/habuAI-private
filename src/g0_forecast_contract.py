"""Bounded strict forecast declaration checks, without scientific/fit authority.

This additive API never upgrades a legacy v2 receipt. Hashes and caller-supplied
readiness are byte/declaration consistency, not historic source authentication.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from master_contracts import canonical_bytes, digest, validate_night
import prospective_inputs as pi

SCHEMA = 'habu-g0-forecast-contract-v1'
POLICY_PATH = 'protocols/development/g0-policy-v1.json'
POLICY_DIGEST = '741ce69c523a2d5cb1e010c4ca4ff49d02682fdd644d5aa4b9b54ed87c49a97a'
MAX_TOTAL_READ_BYTES = 2 * 1024**3
MAX_SMALL_BYTES = 8 * 1024**2
MAX_SHARDS = 256
MAX_DOMAIN_CELLS = 100_000
MAX_WINDOWS = 144
MAX_DOMAIN_ROWS = 4_000_000
MAX_SOURCE_NODES = 16_384
MAX_SOURCE_EDGES = 32_768
MAX_SOURCE_DEPTH = 32
MAX_MODEL_ROWS = 120_000
MAX_MODEL_ROW_BYTES = 16 * 1024**2
ForecastCapacityError = pi.InputCapacityError
IDENTIFIER = re.compile(r'[a-zA-Z0-9_-]{1,100}\Z')
NAME = re.compile(r'[a-z][a-z0-9_]{0,63}\Z')
REF_FIELDS = {'path', 'sha256', 'size_bytes'}
BOUND_FIELDS = REF_FIELDS | {'readiness', 'usable_at'}
NODE_FIELDS = {'id', 'ref', 'source_kind', 'role', 'allowed_use', 'parents',
               'readiness', 'usable_at', 'event_time', 'valid_time', 'source_class'}
FEATURE_FIELDS = {'name', 'units', 'version', 'definition', 'definition_sha256',
                  'code_ref', 'deployment', 'required_source_ids'}
KINDS = {'static': {'feature', 'universe'}, 'forecast': {'feature'},
         'cell_domain': {'universe'}, 'forecast_universe': {'universe'},
         'feature_values': {'feature'}, 'snapshot': {'protocol'}, 'validity': {'protocol'}}
UNIMPLEMENTED_KINDS = {'planned_effort', 'lagged_observation'}


class ForecastCapabilityError(ValueError):
    """A policy-permitted typed projection is not implemented by this adapter."""


def _object(value, fields, label):
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f'{label}: missing or unknown fields')
    return value


def _integer(value, low, high, label):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f'{label}: integer out of bounds')
    return value


def _capacity(count, maximum, label):
    if count > maximum:
        raise ForecastCapacityError(f'CAPACITY_BLOCKED: {label}')


def _stamp(value):
    return pi._time(value).astimezone(timezone.utc)


def _interval(value):
    _object(value, {'start', 'end'}, 'valid-time interval')
    start, end = _stamp(value['start']), _stamp(value['end'])
    if start >= end:
        raise ValueError('Empty/reversed valid-time interval')
    return start, end


def _cover(interval, start, end):
    first, last = _interval(interval)
    if first > start or last < end:
        raise ValueError('Physical valid-time does not cover the prediction window')


def validate_readiness(readiness, usable_at, cutoff, *, parent_usable_at=()):
    """Pure declared max/readiness consistency; does not authenticate any source.

    Parents must already be validated datetimes. Forecast/training callers own
    their different boundary and role rules; this helper only enforces max < cutoff.
    """
    _object(readiness, pi.READINESS_FIELDS, 'Required four readiness timestamps')
    required = [_stamp(readiness[key]) for key in sorted(pi.READINESS_FIELDS)]
    if not isinstance(cutoff, datetime) or cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError('Readiness cutoff must be timezone aware')
    for parent in parent_usable_at:
        if not isinstance(parent, datetime) or parent.tzinfo is None or parent.utcoffset() is None:
            raise ValueError('Parent readiness must be a validated aware datetime')
        required.append(parent)
    usable = _stamp(usable_at)
    if usable != max(required) or usable >= cutoff:
        raise ValueError('usable_at must equal required/parent readiness max strictly before cutoff')
    return usable


def validate_readiness_graph(nodes, cutoff, *, check=lambda: None):
    """Pure declared-readiness DAG, shared by distinct forecast/training gates.

    Nodes have exactly id/parents/readiness/usable_at. The caller owns byte,
    role, projection, source authenticity and boundary selection. No files read.
    Returned order is parents before children; ready_by_id contains aware UTC
    datetimes. All required/parent readiness must be strictly before cutoff.
    """
    if not callable(check):
        raise ValueError('Readiness graph check must be callable')
    check()
    if not isinstance(nodes, list) or not nodes:
        raise ValueError('Nonempty readiness graph required')
    _capacity(len(nodes), MAX_SOURCE_NODES, 'source nodes')
    by_id, edges = {}, 0
    for node in nodes:
        check()
        _object(node, {'id', 'parents', 'readiness', 'usable_at'}, 'Readiness graph node')
        identifier = node['id']
        if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier) or identifier in by_id:
            raise ValueError('Invalid/duplicate source identity')
        parents = node['parents']
        if not isinstance(parents, list):
            raise ValueError('Readiness graph parent list required')
        edges += len(parents)
        _capacity(edges, MAX_SOURCE_EDGES, 'source edges')
        if parents:
            _strings(parents, 'Readiness graph parents')
        by_id[identifier] = node
    ready, depth_by_id, order, active = {}, {}, [], set()

    def visit(identifier, depth):
        check()
        _capacity(depth, MAX_SOURCE_DEPTH, 'source graph depth')
        if identifier in ready:
            return ready[identifier]
        if identifier in active or identifier not in by_id:
            raise ValueError('Cyclic or missing source parent')
        active.add(identifier)
        node = by_id[identifier]
        parent_ready = []
        for parent in node['parents']:
            check()
            parent_ready.append(visit(parent, depth + 1))
        longest = 1 + max((depth_by_id[parent] for parent in node['parents']), default=0)
        _capacity(longest, MAX_SOURCE_DEPTH, 'source graph depth')
        depth_by_id[identifier] = longest
        ready[identifier] = validate_readiness(node['readiness'], node['usable_at'], cutoff, parent_usable_at=parent_ready)
        active.remove(identifier)
        order.append(identifier)
        return ready[identifier]

    for identifier in by_id:
        visit(identifier, 1)
    check()
    return {'ready_by_id': ready, 'topological_order': order}


def _ref(value):
    _object(value, REF_FIELDS, 'Bound byte reference')
    path = value['path']
    if (not isinstance(path, str) or not path or len(path) > 512 or '\\' in path or ':' in path or
            any(part in ('', '.', '..') for part in path.split('/')) or path.startswith('/')):
        raise ValueError('Unsafe portable input path')
    if not isinstance(value['sha256'], str) or not pi.SHA256.fullmatch(value['sha256']):
        raise ValueError('Invalid source SHA-256')
    _integer(value['size_bytes'], 1, pi.MAX_SOURCE_BYTES, 'Source byte size')
    return value


def _input_ref(value):
    _ref(value)
    if not (value['path'].startswith('features/') or value['path'].startswith('data/processed/')):
        raise ValueError('Unsupported strict forecast source namespace')
    return value


def _base_ref(bound):
    return {key: bound[key] for key in REF_FIELDS}


class _Reader:
    def __init__(self, root, context):
        self.root = Path(root).absolute()
        self.context = context
        self.refs = {}

    def read(self, ref, *, small=False, parse=True):
        self.context.check()
        _ref(ref)
        path = ref['path']
        if path in self.refs and self.refs[path] != ref:
            raise ValueError('Conflicting bindings for one source path')
        limit = MAX_SMALL_BYTES if small else pi.MAX_SOURCE_BYTES
        _capacity(ref['size_bytes'], limit, 'source file size')
        target = pi._local_path(self.root, path, self.context.check)
        raw = pi._bounded_bytes(target, pi._LocalByteBudget(self.context, limit), self.context.check)
        if len(raw) != ref['size_bytes'] or hashlib.sha256(raw).hexdigest() != ref['sha256']:
            raise ValueError('Source size/hash changed or mismatched')
        self.context.check()
        self.refs[path] = dict(ref)
        if not parse:
            return raw
        value = json.loads(raw, object_pairs_hook=lambda pairs: pi._unique_json_object(pairs, self.context.check))
        self.context.check()
        canonical_bytes(value)  # Reject nonfinite JSON constants at every depth.
        self.context.check()
        if not isinstance(value, dict):
            raise ValueError('Source JSON must be an object')
        return value

    def rescan(self):
        for ref in tuple(self.refs.values()):
            self.context.check()
            self.read(ref, parse=False)
        self.context.check()


def _bound_readiness(ref, cutoff):
    _object(ref, BOUND_FIELDS, 'Readiness-bound reference')
    _ref(_base_ref(ref))
    return validate_readiness(ref['readiness'], ref['usable_at'], cutoff)


def _strings(value, label):
    if not isinstance(value, list) or not value or any(not isinstance(x, str) or not IDENTIFIER.fullmatch(x) for x in value):
        raise ValueError(f'{label}: nonempty identifier list required')
    if len(set(value)) != len(value):
        raise ValueError(f'{label}: duplicate identifiers')
    return value


def _definitions(features, expected, reader, cutoff):
    if not isinstance(features, list) or not features:
        raise ValueError('Explicit nonempty feature definitions required')
    _capacity(len(features), pi.MAX_FEATURES, 'feature count')
    identities, names, code_ready = [], set(), {}
    for feature in features:
        reader.context.check()
        _object(feature, FEATURE_FIELDS, 'Feature definition')
        name = feature['name']
        if (not isinstance(name, str) or not NAME.fullmatch(name) or name in names or
                name.casefold() in pi.POST_OUTCOME_FIELDS):
            raise ValueError('Duplicate, invalid or target-derived feature name')
        names.add(name)
        for key in ('units', 'version', 'definition'):
            if not isinstance(feature[key], str) or not feature[key].strip() or len(feature[key]) > 4096:
                raise ValueError('Missing/bounded feature definition text required')
        if hashlib.sha256(feature['definition'].encode('utf-8')).hexdigest() != feature['definition_sha256']:
            raise ValueError('Feature definition text hash mismatch')
        if feature['deployment'] in {'planned_effort', 'lagged_observation'}:
            raise ForecastCapabilityError('CAPABILITY_BLOCKED: typed planned/lagged projection not implemented')
        if feature['deployment'] not in {'forecast_predictor', 'static_predictor'}:
            raise ValueError('Unsupported/untyped feature deployment')
        _strings(feature['required_source_ids'], 'Required feature sources')
        ready = _bound_readiness(feature['code_ref'], cutoff)
        code = _base_ref(feature['code_ref'])
        if not code['path'].startswith(('src/', 'scripts/')) or not code['path'].endswith('.py'):
            raise ValueError('Feature code identity must bind local implementation bytes')
        reader.read(code, parse=False)
        code_ready[name] = ready
        identities.append(dict(feature, code_ref=code))
    actual = digest(sorted(identities, key=lambda item: item['name']))
    if not isinstance(expected, str) or not pi.SHA256.fullmatch(expected) or actual != expected:
        raise ValueError('Registered strict feature definition hash mismatch')
    return {feature['name']: feature for feature in features}, code_ready, actual


def _source_graph(nodes, reader, cutoff):
    if not isinstance(nodes, list) or not nodes:
        raise ValueError('Complete source/derivation closure required')
    _capacity(len(nodes), MAX_SOURCE_NODES, 'source nodes')
    by_id, by_path, edges = {}, {}, 0
    for node in nodes:
        reader.context.check()
        _object(node, NODE_FIELDS, 'Source node')
        identifier = node['id']
        if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier) or identifier in by_id:
            raise ValueError('Invalid/duplicate source identity')
        _input_ref(node['ref'])
        if node['ref']['path'] in by_path:
            raise ValueError('Duplicate role binding for one source file')
        kind = node['source_kind']
        if not isinstance(kind, str):
            raise ValueError('Source kind must be explicit')
        if kind in UNIMPLEMENTED_KINDS:
            raise ForecastCapabilityError('CAPABILITY_BLOCKED: typed planned/lagged projection not implemented')
        if kind not in KINDS or node['role'] not in KINDS[kind] or node['allowed_use'] != 'FORECAST_INPUT':
            raise ValueError('Forbidden/untyped source kind, role or allowed use')
        if node['source_class'] not in {'official', 'auxiliary', 'mixed'}:
            raise ValueError('Explicit official/auxiliary source classification required')
        parents = node['parents']
        if not isinstance(parents, list) or (parents and _strings(parents, 'Source parents') != parents):
            raise ValueError('Source parent list required')
        if kind in {'static', 'forecast'}:
            if parents or node['source_class'] == 'mixed' or _stamp(node['event_time']) >= cutoff:
                raise ValueError('Raw source issue/event time must precede cutoff without hidden parents')
        elif not parents or node['event_time'] is not None:
            raise ValueError('Derived source requires parents and no invented event time')
        _interval(node['valid_time'])
        edges += len(parents)
        _capacity(edges, MAX_SOURCE_EDGES, 'source edges')
        by_id[identifier] = node
        by_path[node['ref']['path']] = node
    projection = [{key: node[key] for key in ('id', 'parents', 'readiness', 'usable_at')} for node in nodes]
    validated = validate_readiness_graph(projection, cutoff, check=reader.context.check)
    ready, ancestry = validated['ready_by_id'], {}
    for identifier in validated['topological_order']:
        reader.context.check()
        node = by_id[identifier]
        classes = set().union(*(ancestry[parent] for parent in node['parents'])) if node['parents'] else {node['source_class']}
        expected_class = next(iter(classes)) if len(classes) == 1 else 'mixed'
        if node['source_class'] != expected_class:
            raise ValueError('Derived source class hides auxiliary/official ancestry')
        ancestry[identifier] = classes
    return by_id, by_path, ready


def _partitions(value, total, context):
    if not isinstance(value, list) or not value:
        raise ValueError('Complete partitions required')
    _capacity(len(value), MAX_SHARDS, 'partition count')
    cursor = 0
    for pair in value:
        context.check()
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError('Partition must have two endpoints')
        start = _integer(pair[0], 0, total, 'Partition start')
        end = _integer(pair[1], 0, total, 'Partition end')
        if start != cursor or end <= start:
            raise ValueError('Partition overlap/gap/order')
        cursor = end
    if cursor != total:
        raise ValueError('Partition coverage is incomplete')
    return value


def _horizon(value, night, as_of):
    start, end = _interval(value)
    duration = (end - start).total_seconds()
    if (start <= as_of or pi._night(start) != night or pi._night(end - timedelta(microseconds=1)) != night or
            start.second or start.microsecond or start.minute % 10 or duration % 600):
        raise ValueError('Horizon must be aligned future 600s half-open windows in the operational night')
    windows = int(duration // 600)
    _capacity(windows, MAX_WINDOWS, 'horizon windows')
    return start, end, windows


def _raw_source(node, reader):
    value = reader.read(node['ref'])
    _object(value, {'schema_version', 'source_kind', 'source_class', 'event_time', 'valid_time', 'data'}, 'Raw source envelope')
    if (value['schema_version'] != 'habu-g0-source-v1' or value['source_kind'] != node['source_kind'] or
            value['source_class'] != node['source_class'] or _stamp(value['event_time']) != _stamp(node['event_time']) or
            _interval(value['valid_time']) != _interval(node['valid_time'])):
        raise ValueError('Raw source metadata does not match bound role declaration')
    pi._reject_outcome_fields(value, reader.context.check)


def _domain(node, nodes, reader, first, last):
    if node['source_kind'] != 'cell_domain':
        raise ValueError('Domain must bind an ex-ante cell-domain source')
    value = reader.read(node['ref'], small=True)
    _object(value, {'schema_version', 'crs', 'source_class', 'required_source_ids', 'cells'}, 'Cell domain')
    if value['schema_version'] != 'habu-g0-cell-domain-v1' or value['crs'] != 'EPSG:32652':
        raise ValueError('Physical EPSG:32652 100m cell domain required')
    required = _strings(value['required_source_ids'], 'Required domain sources')
    if set(required) != set(node['parents']) or value['source_class'] != node['source_class']:
        raise ValueError('Domain source binding mismatch')
    for identifier in required:
        source = nodes[identifier]
        if source['source_kind'] != 'static' or source['role'] != 'universe':
            raise ValueError('Raw actual GPX/label cannot define a prospective universe')
        _cover(source['valid_time'], first, last)
    _cover(node['valid_time'], first, last)
    cells = value['cells']
    if not isinstance(cells, list) or not cells:
        raise ValueError('Nonempty declared physical domain required')
    _capacity(len(cells), MAX_DOMAIN_CELLS, 'domain cell count')
    previous = None
    for cell in cells:
        reader.context.check()
        if not isinstance(cell, list) or len(cell) != 2:
            raise ValueError('Physical cell must be [100m x index,100m y index]')
        key = (_integer(cell[0], 1000, 8999, 'Cell x'), _integer(cell[1], 0, 99999, 'Cell y'))
        if previous is not None and key <= previous:
            raise ValueError('Cell domain must be sorted and physically unique')
        previous = key
    return cells


def _legacy_ref(value, nodes_by_path, kind, cutoff):
    _object(value, REF_FIELDS | {'available_at'}, 'Strict v2 source reference')
    _input_ref(_base_ref(value))
    node = nodes_by_path.get(value['path'])
    available = _stamp(value['available_at'])
    if (node is None or node['ref'] != _base_ref(value) or node['source_kind'] != kind or
            available < _stamp(node['usable_at']) or available >= cutoff):
        raise ValueError('Legacy source reference is not bound to required strict node/readiness')
    return node


def _row_id(cell, stamp):
    return f'{cell[0]}:{cell[1]}@{stamp.strftime("%Y-%m-%dT%H:%M:%SZ")}'


def _model_row(row, cutoff):
    """Explicit canonical projection; model normalization must not change its hash."""
    cx, cy = int(row['utm_x_m'] // 100), int(row['utm_y_m'] // 100)
    return dict(row_id=row['row_id'], operational_night=row['operational_night'],
                cutoff_time=cutoff.isoformat(), window_start_jst=_stamp(row['window_start_jst']).isoformat(),
                utm_x_m=cx * 100 + 50, utm_y_m=cy * 100 + 50, cell_x=cx, cell_y=cy,
                features=row['features'], feature_source_refs=row['feature_source_refs'],
                feature_available_at={name: _stamp(value).isoformat() for name, value in row['feature_available_at'].items()})


def _shard(shard, cp, tp, cells, first, nodes, by_path, definitions, code_ready, reader, night, cutoff, as_of):
    snapshot = nodes.get(shard['snapshot_id'])
    validity = nodes.get(shard['validity_id'])
    if snapshot is None or validity is None or snapshot['source_kind'] != 'snapshot' or validity['source_kind'] != 'validity':
        raise ValueError('Shard snapshot/validity node missing or wrong role')
    snap = reader.read(snapshot['ref'])
    _object(snap, {'schema_version', 'operational_night', 'cutoff_time', 'universe', 'features', 'feature_schema_sha256'}, 'Strict v2 snapshot')
    if snap['schema_version'] != '2.0' or not isinstance(snap['features'], list):
        raise ValueError('Legacy v2 snapshot envelope required')
    _capacity(len(snap['features']), pi.MAX_FEATURES, 'shard feature count')
    universe = _legacy_ref(snap['universe'], by_path, 'forecast_universe', cutoff)
    if universe['parents'] != [shard['_domain_id']]:
        raise ValueError('Forecast universe must bind exactly the declared physical domain')
    start, end = first + timedelta(seconds=600 * tp[0]), first + timedelta(seconds=600 * tp[1])
    for node in (snapshot, validity, universe):
        _cover(node['valid_time'], start, end)
    feature_nodes, seen = {}, set()
    for ref in snap['features']:
        reader.context.check()
        node = _legacy_ref(ref, by_path, 'feature_values', cutoff)
        feature = reader.read(node['ref'])
        _object(feature, {'schema_version', 'operational_night', 'cutoff_time', 'available_at', 'feature_name', 'use_role', 'values'}, 'Strict v2 feature')
        name = feature['feature_name']
        if not isinstance(name, str) or name not in definitions or name in seen:
            raise ValueError('Missing/duplicate/unregistered required feature')
        seen.add(name)
        definition = definitions[name]
        required = definition['required_source_ids']
        if set(node['parents']) != set(required) or feature['use_role'] != definition['deployment']:
            raise ValueError('Feature source binding/deployment mismatch')
        for identifier in required:
            source = nodes.get(identifier)
            expected_kind = 'forecast' if definition['deployment'] == 'forecast_predictor' else 'static'
            if source is None or source['source_kind'] != expected_kind or source['role'] != 'feature':
                raise ValueError('Feature source kind/role does not match its deployment')
            _cover(source['valid_time'], start, end)
        validate_readiness(node['readiness'], node['usable_at'], cutoff,
                           parent_usable_at=[_stamp(nodes[x]['usable_at']) for x in required] + [code_ready[name]])
        _cover(node['valid_time'], start, end)
        feature_nodes[name] = node['id']
    if seen != set(definitions):
        raise ValueError('All registered required features must cover every shard')
    ids = set(feature_nodes.values())
    if set(snapshot['parents']) != ids | {universe['id']} or set(validity['parents']) != ids:
        raise ValueError('Snapshot/validity derivation binding mismatch')
    payload = reader.read(universe['ref'])
    _object(payload, {'schema_version', 'source_type', 'geographic_domain', 'rows'}, 'Strict v2 universe')
    _object(payload['geographic_domain'], {'crs', 'name'}, 'Universe geographic domain')
    if (payload['geographic_domain']['crs'] != 'EPSG:32652' or
            not isinstance(payload['geographic_domain']['name'], str) or not payload['geographic_domain']['name'].strip()):
        raise ValueError('Universe geographic domain identity required')
    count = (cp[1] - cp[0]) * (tp[1] - tp[0])
    _capacity(count, pi.MAX_FORECAST_ROWS, 'per-shard rows')
    _capacity(count * len(definitions), pi.MAX_JOIN_CELLS, 'per-shard joined numeric cells')
    units = payload['rows']
    if not isinstance(units, list) or len(units) != count:
        raise ValueError('Shard physical candidate coverage is incomplete')
    index = 0
    for cell_index in range(*cp):
        cell = cells[cell_index]
        for time_index in range(*tp):
            reader.context.check()
            unit = units[index]
            _object(unit, {'row_id', 'operational_night', 'cutoff_time', 'window_start_jst', 'utm_x_m', 'utm_y_m'}, 'Physical universe row')
            stamp = first + timedelta(seconds=time_index * 600)
            if (unit['row_id'] != _row_id(cell, stamp) or _stamp(unit['window_start_jst']) != stamp or
                    isinstance(unit['utm_x_m'], bool) or isinstance(unit['utm_y_m'], bool) or
                    unit['utm_x_m'] != cell[0] * 100 + 50 or unit['utm_y_m'] != cell[1] * 100 + 50):
                raise ValueError('Noncanonical/duplicate physical row identity or coordinates')
            index += 1
    sidecar = reader.read(validity['ref'])
    _object(sidecar, {'schema_version', 'feature_sources', 'rows'}, 'Row physical validity sidecar')
    if sidecar['schema_version'] != 'habu-g0-validity-v1' or sidecar['feature_sources'] != {name: [identifier] for name, identifier in feature_nodes.items()}:
        raise ValueError('Physical validity feature source binding mismatch')
    validity_rows = sidecar['rows']
    if not isinstance(validity_rows, dict) or len(validity_rows) != count:
        raise ValueError('Physical validity row coverage mismatch')
    for unit in units:
        reader.context.check()
        physical = validity_rows.get(unit['row_id'])
        _object(physical, set(definitions), 'Per-row feature validity')
        stamp = _stamp(unit['window_start_jst'])
        for interval in physical.values():
            reader.context.check()
            _cover(interval, stamp, stamp + timedelta(seconds=600))
    joined = pi.load_prospective_inputs(reader.root, snapshot['ref']['path'], snapshot['ref']['sha256'], night, as_of,
                                       model_feature_names=tuple(sorted(definitions)), _read_context=reader.context,
                                       budget_seconds=pi.MAX_BUDGET_SECONDS)
    return joined['rows'], {snapshot['id'], validity['id']}


def _validate(root, manifest_ref, operational_night, as_of, expected, budget_seconds, collect):
    context = pi.ProspectiveReadContext(budget_seconds, MAX_TOTAL_READ_BYTES)
    reader = _Reader(root, context)
    validate_night(operational_night)
    if not isinstance(as_of, datetime) or as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError('Actual issuance time must be timezone aware')
    _input_ref(manifest_ref)
    manifest = reader.read(manifest_ref, small=True)
    _object(manifest, {'schema_version', 'operational_night', 'cutoff_time', 'readiness', 'usable_at', 'policy_ref',
                       'domain_id', 'source_nodes', 'features', 'feature_definition_sha256', 'horizon',
                       'cell_partitions', 'time_partitions', 'shards'}, 'Strict forecast manifest')
    cutoff = _stamp(manifest['cutoff_time'])
    if (manifest['schema_version'] != SCHEMA or manifest['operational_night'] != operational_night or
            cutoff > as_of or pi._night(cutoff) != operational_night):
        raise ValueError('Forecast manifest night/cutoff mismatch')
    policy_ready = _bound_readiness(manifest['policy_ref'], cutoff)
    if manifest['policy_ref']['path'] != POLICY_PATH:
        raise ValueError('Fixed G0 policy path required')
    policy = reader.read(_base_ref(manifest['policy_ref']), small=True)
    if digest(policy) != POLICY_DIGEST:
        raise ValueError('Fixed G0 policy canonical digest mismatch')
    definitions, code_ready, definition_sha = _definitions(manifest['features'], expected, reader, cutoff)
    if manifest['feature_definition_sha256'] != definition_sha:
        raise ValueError('Manifest strict feature definition hash mismatch')
    nodes, by_path, ready = _source_graph(manifest['source_nodes'], reader, cutoff)
    if manifest['domain_id'] not in nodes:
        raise ValueError('Declared cell domain is absent from source closure')
    first, last, windows = _horizon(manifest['horizon'], operational_night, as_of)
    cells = _domain(nodes[manifest['domain_id']], nodes, reader, first, last)
    total_rows = len(cells) * windows
    _capacity(total_rows, MAX_DOMAIN_ROWS, 'declared domain rows')
    if collect:
        _capacity(total_rows, MAX_MODEL_ROWS, 'whole-domain model collector rows')
    cell_parts = _partitions(manifest['cell_partitions'], len(cells), context)
    time_parts = _partitions(manifest['time_partitions'], windows, context)
    expected_shards = len(cell_parts) * len(time_parts)
    _capacity(expected_shards, MAX_SHARDS, 'whole-domain shard count')
    shards = manifest['shards']
    if not isinstance(shards, list) or len(shards) != expected_shards:
        raise ValueError('Missing/extra complete rectangular shard coverage')
    shard_ids, slots, output_nodes = set(), set(), set()
    for shard in shards:
        context.check()
        _object(shard, {'shard_id', 'cell_partition', 'time_partition', 'snapshot_id', 'validity_id'}, 'Shard declaration')
        sid = shard['shard_id']
        if not isinstance(sid, str) or not IDENTIFIER.fullmatch(sid) or sid in shard_ids:
            raise ValueError('Invalid/duplicate shard identity')
        shard_ids.add(sid)
        ci = _integer(shard['cell_partition'], 0, len(cell_parts) - 1, 'Cell partition index')
        ti = _integer(shard['time_partition'], 0, len(time_parts) - 1, 'Time partition index')
        if (ci, ti) in slots or any(not isinstance(shard[key], str) for key in ('snapshot_id', 'validity_id')):
            raise ValueError('Overlapping shard rectangle or invalid node identity')
        slots.add((ci, ti))
        for key in ('snapshot_id', 'validity_id'):
            if shard[key] in output_nodes:
                raise ValueError('Source artifact reused across physical shard rectangles')
            output_nodes.add(shard[key])
    # All source bytes are validated even when they are only declared ancestors.
    for node in nodes.values():
        context.check()
        if node['source_kind'] in {'static', 'forecast'}:
            _raw_source(node, reader)
    all_ready = [policy_ready, *code_ready.values(), *ready.values()]
    validate_readiness(manifest['readiness'], manifest['usable_at'], cutoff, parent_usable_at=all_ready)
    result_rows, row_bytes, seen_count = [], 2, 0
    joined_hash = hashlib.sha256(b'[')
    snapshot_refs = []
    roots = {manifest['domain_id']}
    for shard in sorted(shards, key=lambda item: (item['cell_partition'], item['time_partition'])):
        context.check()
        ci, ti = shard['cell_partition'], shard['time_partition']
        rows, consumed_roots = _shard(dict(shard, _domain_id=manifest['domain_id']), cell_parts[ci], time_parts[ti],
                                     cells, first, nodes, by_path, definitions, code_ready, reader,
                                     operational_night, cutoff, as_of)
        roots.update(consumed_roots)
        snapshot_refs.append(dict(nodes[shard['snapshot_id']]['ref']))
        for raw_row in rows:
            context.check()
            row = _model_row(raw_row, cutoff)
            raw = canonical_bytes(row)
            if seen_count:
                joined_hash.update(b',')
            joined_hash.update(raw)
            seen_count += 1
            if collect:
                row_bytes += len(raw) + (1 if result_rows else 0)
                _capacity(row_bytes, MAX_MODEL_ROW_BYTES, 'whole-domain model collector canonical row bytes')
                result_rows.append(row)
    joined_hash.update(b']')
    reachable, pending = set(), list(roots)
    while pending:
        context.check()
        identifier = pending.pop()
        if identifier not in reachable:
            reachable.add(identifier)
            pending.extend(nodes[identifier]['parents'])
    if reachable != set(nodes) or seen_count != total_rows:
        raise ValueError('Unbound/orphan source nodes or incomplete domain coverage')
    # Every declared source, plus policy/code/manifest, must have been read.
    if any(node['ref']['path'] not in reader.refs for node in nodes.values()):
        raise ValueError('Unconsumed required source reference')
    reader.rescan()
    context.check()
    receipt = dict(schema_version=SCHEMA, qualification='STRICT_G0_FORECAST_DECLARATION_VALIDATED',
                   operational_night=operational_night, cutoff_time=cutoff.isoformat(),
                   manifest_ref=dict(manifest_ref), policy_file_sha256=manifest['policy_ref']['sha256'],
                   policy_canonical_sha256=POLICY_DIGEST, feature_definition_sha256=definition_sha,
                   legacy_feature_names_sha256=digest(sorted(definitions)), row_count=total_rows,
                   canonical_joined_rows_sha256=joined_hash.hexdigest(), snapshot_refs=snapshot_refs,
                   cell_count=len(cells), window_count=windows, shard_count=len(shards),
                   actual_read_bytes=context.bytes_read, consumed_sha256={path: ref['sha256'] for path, ref in reader.refs.items()},
                   source_class_by_path={node['ref']['path']: node['source_class'] for node in nodes.values()},
                   model_rows='COMPLETE_BOUNDED_COLLECTION' if collect else 'NOT_LOADED',
                   coverage='DECLARED_DOMAIN_ONLY', source_authenticity='NOT_ATTESTED',
                   fit_authorized=False, scientific_execution_authorized=False, production_authorized=False)
    return {'receipt': receipt, 'rows': result_rows} if collect else receipt


def validate_g0_forecast(root, manifest_ref, operational_night, as_of, *, expected_feature_definition_sha256,
                         budget_seconds=pi.DEFAULT_BUDGET_SECONDS):
    """Validate the entire bounded shard set; no rows or model capability granted."""
    return _validate(root, manifest_ref, operational_night, as_of, expected_feature_definition_sha256, budget_seconds, False)


def load_g0_forecast_rows(root, manifest_ref, operational_night, as_of, *, expected_feature_definition_sha256,
                          budget_seconds=pi.DEFAULT_BUDGET_SECONDS):
    """Return {receipt,rows} only after complete validation and final rescan.

    Whole-domain collection is capped at 120000 rows and 16MiB canonical JSON.
    Larger domain receipts do not authorize subset ranks or model chunk concat.
    """
    return _validate(root, manifest_ref, operational_night, as_of, expected_feature_definition_sha256, budget_seconds, True)
