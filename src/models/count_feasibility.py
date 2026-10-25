"""Pure M3 count declaration diagnostic; no authentication, fitting or forecast.

The caller owns source bytes, independent search/outcome qualification and any
later statistical protocol. This module never opens those files or grants fit
authority, including when all supplied declarations are internally consistent.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from time import monotonic

from models.research_selection import validate_selection
from g0_forecast_contract import ForecastCapacityError, validate_readiness, validate_readiness_graph

VERSION = 'habu-count-feasibility-v1'
TARGET = 'OWNER_CAPTURED_HABU_INDIVIDUALS_DURING_MEASURED_ACTIVE_SEARCH'
MAX_JSON_BYTES = 16 * 1024**2
MAX_JSON_NODES = 2_000_000
MAX_ROWS = MAX_EVENTS = 20_000
MAX_INDIVIDUALS = 100_000
MAX_SOURCE_NODES = 16_384
MAX_SOURCE_EDGES = 32_768
MAX_SOURCE_DEPTH = 32
MAX_LINEAGE_MEMBERSHIPS = 1_000_000
READINESS = {'source_received_at', 'derived_at', 'materialized_at', 'audited_at'}
TOP = {'schema_version', 'selection_sha256', 'corpus_sha256', 'target', 'owner_id', 'observer_id',
       'method_version', 'units', 'source_nodes', 'readiness', 'usable_at', 'rows', 'projection_sha256'}
NODE = {'id', 'ref', 'source_role', 'source_kind', 'parents', 'readiness', 'usable_at'}
UNIT = {'row_id', 'night', 'cell_x', 'cell_y', 'window_start_jst'}
SCOPE = UNIT | {'owner_id', 'observer_id', 'method_version', 'declaration', 'active_intervals', 'source_ids'}
ROW = {'count': UNIT | {'count', 'events', 'individual_source_ids', 'complete_scope'},
       'effort': UNIT | {'active_search_seconds', 'active_intervals', 'measurement_source_ids', 'active_scope'}}
ROLES = {'count': {'label', 'complete_outcome'}, 'effort': {'search_evidence', 'active_search'}}


class CountCapacityBlocked(ValueError):
    """CAPACITY_BLOCKED: resource limit, without partial feasibility success."""


def _cap(value, limit, label):
    if value > limit:
        raise CountCapacityBlocked('CAPACITY_BLOCKED: ' + label)


def _fields(value, fields):
    if type(value) is not dict or set(value) != fields:
        raise ValueError('Exact count declaration fields required')


def _text(value, maximum=256):
    if type(value) is not str or not value.strip() or len(value) > maximum:
        raise ValueError('Bounded nonempty count declaration string required')
    return value


def _hash(value):
    if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('Explicit SHA-256 required')
    return value


def _time(value):
    _text(value, 64)
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if stamp.utcoffset() is None:
            raise ValueError('Aware count timestamp required')
        return stamp.astimezone(timezone.utc)
    except (OverflowError, TypeError) as exc:
        raise ValueError('Invalid count timestamp') from exc


def _encode(value, check):
    total = 0
    encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    for chunk in encoder.iterencode(value):
        check()
        raw = chunk.encode('utf-8')
        total += len(raw)
        _cap(total, MAX_JSON_BYTES, 'combined JSON bytes')
        yield raw
    check()


def _copy_inputs(values, check):
    pending, nodes = [(values, 0)], 0
    while pending:
        check()
        item, depth = pending.pop()
        nodes += 1
        _cap(depth, 12, 'JSON depth')
        _cap(nodes, MAX_JSON_NODES, 'JSON nodes')
        kind = type(item)
        if kind in (dict, list):
            _cap(nodes + len(pending) + len(item), MAX_JSON_NODES, 'JSON nodes')
            if kind is dict:
                for key in item:
                    check()
                    if type(key) is not str or len(key) > 512:
                        raise ValueError('Bounded string JSON keys required')
            for value in (item.values() if kind is dict else item):
                check()
                pending.append((value, depth + 1))
        elif kind is str:
            _cap(len(item), 4096, 'JSON string')
        elif kind is int:
            _cap(item.bit_length(), 16_384, 'JSON integer size')
        elif kind is float:
            if not math.isfinite(item):
                raise ValueError('Nonfinite count declaration')
        elif kind not in (bool, type(None)):
            raise ValueError('JSON-only count declarations required')
    # Bound the entire input before creating any owned Python object copy.
    raw = bytearray()
    for chunk in _encode(values, check):
        raw.extend(chunk)
    check()
    owned = json.loads(raw)
    check()
    return owned


def _digest(value, check):
    hashed = hashlib.sha256()
    for raw in _encode(value, check):
        hashed.update(raw)
    check()
    return hashed.hexdigest()


def _list(value, maximum, label):
    if type(value) is not list:
        raise ValueError('Explicit ' + label + ' list required')
    _cap(len(value), maximum, label)
    return value


def _unit(value, selected):
    for key in ('row_id', 'night'):
        if value[key] != selected[key]:
            raise ValueError('Count unit row/night differs from selection')
    for key in ('cell_x', 'cell_y'):
        if type(value[key]) is not int or value[key] != selected[key]:
            raise ValueError('Count physical cell differs from selection')
    start = _time(value['window_start_jst'])
    if start != _time(selected['window_start_jst']):
        raise ValueError('Count physical window differs from selection')
    return start


def _intervals(value, start, check):
    parsed, previous = [], None
    for interval in _list(value, 600, 'active intervals'):
        check()
        _fields(interval, {'start', 'end'})
        a, b = _time(interval['start']), _time(interval['end'])
        if a < start or b > start + timedelta(seconds=600) or a >= b or (previous is not None and a < previous):
            raise ValueError('Active intervals must be sorted/disjoint and inside the 600s unit')
        parsed.append((a, b))
        previous = b
    return parsed


def assess_count_feasibility(selection, count_projection=None, effort_projection=None, *, budget_seconds=30, check=None):
    """Assess supplied count declarations only, never source truth or fit adequacy.

    Missing data return NEED_MORE_DATA. Explicit contradictory declarations are
    ValueError. Oversized requests and expired budgets return no partial result.
    check may enforce a tighter caller deadline; it never replenishes this one.
    """
    if (type(budget_seconds) not in (int, float) or not 0 < budget_seconds <= 300 or
            (check is not None and not callable(check))):
        raise ValueError('Bounded count elapsed budget/callback required')
    deadline, caller_check = monotonic() + budget_seconds, check
    def guard():
        if caller_check is not None:
            caller_check()
        if monotonic() >= deadline:
            raise TimeoutError('Count feasibility elapsed budget exceeded')
    guard()
    selected, count, effort = _copy_inputs([selection, count_projection, effort_projection], guard)
    guard()
    selected = validate_selection(selected)
    guard()
    cutoff = _time(selected['fit_cutoff'])
    accepted = {row['row_id']: row for row in selected['accepted']}
    missing = set()
    def need(row_id, reason):
        guard()
        missing.add((row_id, reason))

    projections = {'count': count, 'effort': effort}
    row_maps, by_id, family_by_id, total_nodes, total_edges = {}, {}, {}, 0, 0
    sha_family, path_family, node_times, metadata = {}, {}, {}, None
    for family, p in projections.items():
        guard()
        if p is None:
            need('*', family.upper() + '_PROJECTION_REQUIRED')
            row_maps[family] = {}
            continue
        _fields(p, TOP)
        expected_schema = 'habu-count-ledger-projection-v1' if family == 'count' else 'habu-active-search-effort-projection-v1'
        units = 'individuals' if family == 'count' else 'active_search_seconds'
        if (p['schema_version'] != expected_schema or p['units'] != units or p['target'] != TARGET or
                p['selection_sha256'] != selected['selection_sha256'] or p['corpus_sha256'] != selected['corpus_sha256']):
            raise ValueError('Count target/units/selection identity mismatch')
        identity = tuple(_text(p[key]) for key in ('owner_id', 'observer_id', 'method_version'))
        if metadata is not None and metadata != identity:
            raise ValueError('Count and effort owner/observer/method disagree')
        metadata = identity
        body = {key: value for key, value in p.items() if key != 'projection_sha256'}
        if _hash(p['projection_sha256']) != _digest(body, guard):
            raise ValueError('Count projection digest mismatch')
        nodes = _list(p['source_nodes'], MAX_SOURCE_NODES, 'source nodes')
        total_nodes += len(nodes)
        _cap(total_nodes, MAX_SOURCE_NODES, 'combined source nodes')
        for node in nodes:
            guard()
            _fields(node, NODE)
            identifier = _text(node['id'], 100)
            if identifier in by_id or type(node['source_role']) is not str or node['source_role'] not in ROLES[family]:
                raise ValueError('Duplicate source ID or unsupported source role')
            if type(node['source_kind']) is not str or node['source_kind'] not in {'RAW', 'DERIVED'}:
                raise ValueError('Explicit RAW/DERIVED source kind required')
            parents = _list(node['parents'], MAX_SOURCE_NODES, 'source parents')
            if any(type(parent) is not str or not parent for parent in parents) or len(set(parents)) != len(parents):
                raise ValueError('Unique source parent IDs required')
            if bool(parents) != (node['source_kind'] == 'DERIVED'):
                raise ValueError('Source kind contradicts declared derivation parents')
            total_edges += len(parents)
            _cap(total_edges, MAX_SOURCE_EDGES, 'combined source edges')
            ref = node['ref']
            _fields(ref, {'path', 'sha256', 'size_bytes'})
            path, source_sha = _text(ref['path'], 512), _hash(ref['sha256'])
            parts = path.split('/')
            if ('\\' in path or ':' in path or parts[0] not in {'data', 'evidence', 'features'} or
                    any(part in {'', '.', '..'} or part.casefold() in {'sealed', 'confirmation'} for part in parts) or
                    any(ord(char) < 32 or ord(char) == 127 for char in path)):
                raise ValueError('Forbidden count source path, including sealed confirmation')
            if type(ref['size_bytes']) is not int or ref['size_bytes'] <= 0:
                raise ValueError('Positive source byte size required')
            _cap(ref['size_bytes'], 128 * 1024**2, 'source bytes')
            if source_sha in sha_family and sha_family[source_sha] != family:
                raise ValueError('Effort and outcome sources share byte SHA ancestry')
            if path in path_family:
                raise ValueError('Source path is ambiguously rebound')
            sha_family[source_sha], path_family[path] = family, family
            _fields(node['readiness'], READINESS)
            times = {key: _time(value) for key, value in node['readiness'].items()}
            if path not in selected['source_sha256']:
                need('*', 'SOURCE_NOT_REGISTERED_IN_SELECTION:' + path)
            elif (selected['source_sha256'][path] != source_sha or
                  _time(selected['source_received_at'][path]) != times['source_received_at']):
                raise ValueError('Count source hash/received time contradicts selection manifest')
            by_id[identifier], family_by_id[identifier] = node, family
            node_times[identifier] = times
        rows = {}
        for row in _list(p['rows'], MAX_ROWS, 'projection rows'):
            guard()
            _fields(row, ROW[family])
            rid = _text(row['row_id'])
            if rid not in accepted or rid in rows:
                raise ValueError('Extra or duplicate selected count row')
            _unit(row, accepted[rid])
            rows[rid] = row
        row_maps[family] = rows
        for rid in accepted:
            if rid not in rows:
                need(rid, family.upper() + '_ROW_REQUIRED')

    for identifier, node in by_id.items():
        guard()
        if any(parent not in by_id or family_by_id[parent] != family_by_id[identifier] for parent in node['parents']):
            raise ValueError('Missing source parent or effort/outcome lineage overlap')
    graph_nodes = [{key: node[key] for key in ('id', 'parents', 'readiness', 'usable_at')} for node in by_id.values()]
    try:
        validated = validate_readiness_graph(graph_nodes, cutoff, check=guard) if graph_nodes else {'ready_by_id': {}, 'topological_order': []}
    except ForecastCapacityError as exc:
        raise CountCapacityBlocked(str(exc)) from exc
    raw_ancestors, depths, memberships = {}, {}, 0
    for identifier in validated['topological_order']:
        guard()
        node = by_id[identifier]
        depth = 1 + max((depths[parent] for parent in node['parents']), default=0)
        _cap(depth, MAX_SOURCE_DEPTH, 'source depth')
        depths[identifier] = depth
        leaves = set()
        parents = node['parents']
        sources = (raw_ancestors[parent] for parent in parents) if parents else ([node['ref']['sha256']],)
        for parent_leaves in sources:
            for leaf in parent_leaves:
                guard()
                if leaf not in leaves:
                    _cap(memberships + 1, MAX_LINEAGE_MEMBERSHIPS, 'cumulative raw lineage memberships')
                    leaves.add(leaf)
                    memberships += 1
        raw_ancestors[identifier] = leaves
    for family, p in projections.items():
        if p is not None:
            guard()
            parent_ready = [validated['ready_by_id'][n['id']] for n in p['source_nodes']]
            validate_readiness(p['readiness'], p['usable_at'], cutoff, parent_usable_at=parent_ready)
    used, required_after = set(), {}
    def sources(ids, role, rid, *, optional=False, after=None):
        _list(ids, MAX_SOURCE_NODES, 'row source references')
        if any(type(identifier) is not str for identifier in ids) or len(set(ids)) != len(ids):
            raise ValueError('Unique string source IDs required')
        if not ids and not optional:
            need(rid, role.upper() + '_SOURCE_REQUIRED')
        for identifier in ids:
            guard()
            if identifier not in by_id or by_id[identifier]['source_role'] != role:
                raise ValueError('Row source role/binding mismatch')
            used.add(identifier)
            if after is not None and (identifier not in required_after or required_after[identifier] < after):
                required_after[identifier] = after

    def scope(value, row, p, declaration, role):
        if value is None:
            need(row['row_id'], role.upper() + '_SCOPE_REQUIRED')
            return None
        _fields(value, SCOPE)
        start = _unit(value, row)
        if any(value[key] != p[key] for key in ('owner_id', 'observer_id', 'method_version')):
            raise ValueError('Scope owner/observer/method mismatch')
        if type(value['declaration']) is not str or value['declaration'] not in {declaration, 'UNKNOWN'}:
            raise ValueError('Unsupported count scope declaration')
        if value['declaration'] == 'UNKNOWN':
            need(row['row_id'], role.upper() + '_SCOPE_UNKNOWN')
        intervals = _intervals(value['active_intervals'], start, guard)
        if not intervals:
            need(row['row_id'], role.upper() + '_INTERVAL_REQUIRED')
        sources(value['source_ids'], role, row['row_id'], after=intervals[-1][1] if intervals else None)
        return intervals

    events, individuals, counts, seconds_by_row, active_by_row = set(), set(), {}, {}, {}
    event_times, timeline = {}, []
    for rid, row in row_maps['effort'].items():
        guard()
        start = _unit(row, accepted[rid])
        intervals = _intervals(row['active_intervals'], start, guard)
        for a, b in intervals:
            guard()
            timeline.append((a, b, rid))
        active_by_row[rid] = intervals
        seconds = row['active_search_seconds']
        if seconds is not None:
            if type(seconds) not in (int, float) or not 0 <= seconds <= 600:
                raise ValueError('Finite measured active-search seconds in [0,600] required')
            if intervals and not math.isclose(seconds, sum((b - a).total_seconds() for a, b in intervals), rel_tol=0, abs_tol=1e-6):
                raise ValueError('Explicit measured effort differs from measured intervals')
        if seconds is None or seconds == 0 or not intervals:
            need(rid, 'POSITIVE_MEASURED_ACTIVE_SEARCH_EFFORT_REQUIRED')
        else:
            seconds_by_row[rid] = seconds
        sources(row['measurement_source_ids'], 'search_evidence', rid, after=intervals[-1][1] if intervals else None)
        declared = scope(row['active_scope'], row, effort, 'DECLARED_ACTIVE_SEARCH', 'active_search')
        if declared is not None and intervals and declared != intervals:
            raise ValueError('Active-search scope differs from measured intervals')

    # The projections describe one owner/observer/method. Different cells cannot
    # duplicate that observer's elapsed active search; no travel model is inferred.
    guard()
    timeline.sort()
    guard()
    previous_end = None
    for a, b, rid in timeline:
        guard()
        if previous_end is not None and a < previous_end:
            raise ValueError('Same observer active-search intervals overlap across selected rows')
        previous_end = b

    for rid, row in row_maps['count'].items():
        guard()
        number = row['count']
        if number is None:
            need(rid, 'EXPLICIT_INDIVIDUAL_COUNT_REQUIRED')
        elif type(number) is not int or number < 0:
            raise ValueError('Explicit nonboolean individual count required')
        else:
            _cap(number, MAX_INDIVIDUALS, 'declared individual count')
            if bool(number) != bool(accepted[rid]['label']):
                raise ValueError('Explicit count contradicts binary selection')
        own_events, individual_count, unresolved = set(), 0, False
        for event in _list(row['events'], MAX_EVENTS, 'capture events'):
            guard()
            _fields(event, {'event_id', 'event_time', 'individual_ids', 'outcome_source_ids'})
            identifier = _text(event['event_id'])
            if identifier in events:
                raise ValueError('Duplicate capture event ID')
            _cap(len(events) + 1, MAX_EVENTS, 'capture events')
            events.add(identifier)
            own_events.add(identifier)
            when = _time(event['event_time']) if event['event_time'] is not None else None
            if when is None:
                need(rid, 'EVENT_TIME_REQUIRED')
            elif not _time(row['window_start_jst']) <= when < _time(row['window_start_jst']) + timedelta(seconds=600):
                raise ValueError('Event outside selected physical window')
            event_times.setdefault(rid, []).append(when)
            sources(event['outcome_source_ids'], 'label', rid, after=when)
            ids = event['individual_ids']
            if ids is None:
                need(rid, 'CANONICAL_INDIVIDUAL_LEDGER_REQUIRED')
                unresolved = True
            else:
                _list(ids, MAX_INDIVIDUALS, 'individual IDs')
                if not ids:
                    need(rid, 'CANONICAL_INDIVIDUAL_LEDGER_REQUIRED')
                    unresolved = True
                for identity in ids:
                    guard()
                    _text(identity)
                    if identity in individuals:
                        raise ValueError('Duplicate canonical individual ID')
                    _cap(len(individuals) + 1, MAX_INDIVIDUALS, 'canonical individuals')
                    individuals.add(identity)
                    individual_count += 1
        if own_events != set(accepted[rid]['capture_event_ids']):
            raise ValueError('Count events do not exactly cover selected event IDs')
        if number is not None and not unresolved and number != individual_count:
            raise ValueError('Explicit count differs from independent individual ledger')
        known_times = [stamp for stamp in event_times.get(rid, []) if stamp is not None]
        sources(row['individual_source_ids'], 'label', rid, optional=number == 0,
                after=max(known_times) if known_times else None)
        complete = scope(row['complete_scope'], row, count, 'DECLARED_COMPLETE', 'complete_outcome')
        if complete and row['complete_scope']['declaration'] == 'DECLARED_COMPLETE':
            for when in known_times:
                guard()
                if not any(a <= when < b for a, b in complete):
                    raise ValueError('Count event outside its declared complete-outcome scope')
        active = active_by_row.get(rid)
        if active and complete is not None:
            scope_index = 0
            for a, b in active:
                guard()
                cursor = a
                while scope_index < len(complete) and complete[scope_index][1] <= cursor:
                    guard()
                    scope_index += 1
                while cursor < b:
                    guard()
                    if scope_index >= len(complete) or complete[scope_index][0] > cursor:
                        raise ValueError('Complete owner-outcome scope fails to cover active search')
                    cursor = complete[scope_index][1]
                    if cursor < b:
                        scope_index += 1
        if active:
            for when in event_times.get(rid, []):
                guard()
                if when is not None and not any(a <= when < b for a, b in active):
                    raise ValueError('Count event outside measured active-search intervals')
        if number is not None:
            counts[rid] = number
    # All kinds in these fixed role families are actual observation evidence.
    # Later derived metadata cannot launder an earlier impossible RAW ancestor.
    # One reverse-topological max pass costs O(nodes+edges), without expanding
    # per-row ancestor sets or multiplying the count of individual references.
    for identifier in reversed(validated['topological_order']):
        guard()
        after = required_after.get(identifier)
        if after is None:
            continue
        for stamp in node_times[identifier].values():
            guard()
            if stamp < after:
                raise ValueError('Count evidence readiness precedes its event or measured scope end')
        for parent in by_id[identifier]['parents']:
            guard()
            if parent not in required_after or required_after[parent] < after:
                required_after[parent] = after
    pending = list(used)
    while pending:
        guard()
        identifier = pending.pop()
        for parent in by_id[identifier]['parents']:
            if parent not in used:
                used.add(parent)
                pending.append(parent)
    if used != set(by_id):
        raise ValueError('Unbound count/effort source nodes')
    if not accepted:
        need('*', 'SELECTED_COUNT_UNITS_REQUIRED')
    guard()
    result = dict(schema_version=VERSION, target=TARGET,
                  status='NEED_MORE_DATA' if missing else 'DECLARED_CONSISTENCY_ONLY',
                  selection_sha256=selected['selection_sha256'], corpus_sha256=selected['corpus_sha256'],
                  count_projection_sha256=count['projection_sha256'] if count is not None else None,
                  effort_projection_sha256=effort['projection_sha256'] if effort is not None else None,
                  summary=dict(selected_units=len(accepted), covered_count_rows=len(row_maps['count']),
                               covered_effort_rows=len(row_maps['effort']),
                               declared_individual_count=None if missing else sum(counts.values()),
                               declared_active_search_seconds=None if missing else sum(seconds_by_row.values())),
                  blockers=[dict(row_id=rid, reason=reason) for rid, reason in sorted(missing)],
                  statistical_adequacy='NOT_ASSESSED', source_authenticity='NOT_ATTESTED',
                  source_authentication='CALLER_DEPENDENCY_REQUIRED',
                  limitations=['EVENT_GEOLOCATION_NOT_REATTESTED', 'SOURCE_QUALIFICATION_NOT_ATTESTED',
                               'RETROSPECTIVE_EFFORT_NOT_A_FORECAST_FEATURE'],
                  fit_authorized=False, scientific_execution_authorized=False,
                  official_issuance_authorized=False, production_authorized=False)
    result['assessment_sha256'] = _digest(result, guard)
    guard()
    return result
