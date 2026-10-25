"""Source-bound declared-consistency Stage1 projection; never source authentication.

Only the existing guarded snapshot namespaces and the parent's cumulative context
are used. Outcome lineage in v1 means actual observational records, not standing
policy. A complete declaration remains an unauthenticated issuer assertion.
"""
from __future__ import annotations

import csv
from datetime import timedelta
import io
import math
import re
from statistics import mean

import g0_forecast_contract as g0
from gpx_audit import utm52n
from master_contracts import validate_night
from master_inventory import local_path
import prospective_inputs as pi
import research_model_adapter as models
from evaluation import full_ledger_stage1 as pure

VERSION = 'habu-stage1-source-contract-v1'
MANIFEST_FIELDS = {'schema_version', 'purpose', 'operational_night', 'evaluation_as_of',
    'forecast_manifest_sha256', 'joined_universe_sha256', 'scope_id', 'captures_id',
    'individuals_id', 'coverage_id', 'source_nodes', 'readiness', 'usable_at'}
NODE_FIELDS = {'id', 'ref', 'source_kind', 'role', 'parents', 'readiness', 'usable_at'}
ROLES = ('scope', 'captures', 'individuals', 'coverage')
SCOPE_FIELDS = {'schema_version', 'operational_night', 'cutoff_time', 'horizon_start', 'horizon_end', 'scope'}
COVERAGE_FIELDS = {'schema_version', 'declaration', 'operational_night', 'scope_sha256',
    'horizon_start', 'horizon_end', 'captures_ref', 'individuals_ref', 'event_ids', 'individual_ids'}
POSITIVE = re.compile(r'[1-9][0-9]{0,6}\Z')


def input_ref(value):
    """Transport is intentionally narrower than G0ArtifactReader's arbitrary refs."""
    g0._ref(value)
    path = value['path']
    parts = path.split('/')
    if (any(part.casefold() in {'sealed', 'confirmation'} for part in parts) or
            any(ord(c) < 32 or ord(c) == 127 for c in path) or
            not (parts[0] in {'data', 'evidence', 'features', 'policies', 'src', 'scripts'} or
                 path.startswith('protocols/development/'))):
        raise ValueError('Unsupported Stage1 snapshot namespace or reveal reference')
    return value


def _hash(value, check):
    return pure._digest(value, check)


def _integer(value):
    if type(value) is not str or not POSITIVE.fullmatch(value):
        raise ValueError('Explicit positive canonical CSV integer required')
    return int(value)


def _text(value):
    return pure._text(value)


def _csv(raw, required, maximum, check, *, coordinates=False):
    """Bound bytes before transport; reject row/header ambiguity before projection."""
    try:
        reader = csv.reader(io.StringIO(raw.decode('utf-8-sig'), newline=''), strict=True)
        header = next(reader)
        if (len(header) > 64 or len(set(header)) != len(header) or
                any(not h or len(h) > 128 for h in header) or not set(required) <= set(header)):
            raise ValueError('Canonical CSV required headers/unique columns')
        if coordinates:
            geo, utm = {'latitude', 'longitude'}, {'utm_x_m', 'utm_y_m'}
            columns = set(header)
            if not ((geo <= columns and not utm & columns) or (utm <= columns and not geo & columns)):
                raise ValueError('One unambiguous explicit coordinate pair required')
        for count, values in enumerate(reader, 1):
            check()
            if count > maximum:
                raise pi.InputCapacityError('CAPACITY_BLOCKED: complete Stage1 CSV rows')
            if len(values) != len(header) or any(len(v) > 4096 for v in values):
                raise ValueError('Ragged or unbounded canonical CSV row')
            yield dict(zip(header, values))
    except (StopIteration, UnicodeError, csv.Error) as exc:
        raise ValueError('Invalid canonical CSV bytes') from exc


def _captures(raw, check):
    result, total = {}, 0
    for row in _csv(raw, {'event_id', 'operational_date', 'event_time_local', 'event_type', 'event_count'}, pure.MAX_EVENTS, check, coordinates=True):
        ident = _text(row['event_id'])
        stamp = pi._time(row['event_time_local'])
        night = row['operational_date']
        validate_night(night)
        if ident in result or pi._night(stamp) != night or row['event_type'] != 'capture':
            raise ValueError('Canonical capture ID/night/type mismatch')
        count = _integer(row['event_count'])
        total += count
        if total > pure.MAX_INDIVIDUALS:
            raise pi.InputCapacityError('CAPACITY_BLOCKED: event individual count')
        geo, utm = {'latitude', 'longitude'}, {'utm_x_m', 'utm_y_m'}
        if geo <= row.keys() and not utm & row.keys():
            lat, lon = map(float, (row['latitude'], row['longitude']))
            if not (math.isfinite(lat) and math.isfinite(lon) and 0 <= lat < 84 and 126 <= lon <= 132):
                raise ValueError('WGS84 point outside UTM52N geographic domain')
            x, y = utm52n(lat, lon)
        elif utm <= row.keys() and not geo & row.keys():
            x, y = map(float, (row['utm_x_m'], row['utm_y_m']))
        else:
            raise ValueError('One unambiguous explicit coordinate pair required')
        if not (math.isfinite(x) and math.isfinite(y) and 100000 <= x < 900000 and 0 <= y < 10000000):
            raise ValueError('Finite bounded UTM52N point required')
        result[ident] = dict(event_id=ident, operational_night=night, datetime=stamp.isoformat(),
                            utm_x_m=x, utm_y_m=y, count=count, individual_ids=[])
    return result


def _individuals(raw, captures, check):
    result, indices = {}, {}
    for row in _csv(raw, {'individual_id', 'event_id', 'individual_index', 'operational_date', 'event_time_local'}, pure.MAX_INDIVIDUALS, check):
        ident, event = _text(row['individual_id']), _text(row['event_id'])
        index = _integer(row['individual_index'])
        stamp, night = pi._time(row['event_time_local']), row['operational_date']
        validate_night(night)
        if ident in result or pi._night(stamp) != night or index in indices.setdefault(event, set()):
            raise ValueError('Duplicate/conflicting canonical individual identity/night/index')
        indices[event].add(index)
        if captures is not None:
            capture = captures.get(event)
            if (capture is None or capture['operational_night'] != night or pi._time(capture['datetime']) != stamp):
                raise ValueError('Individual event/time/night link mismatch')
            capture['individual_ids'].append(ident)
        result[ident] = dict(event_id=event, datetime=stamp.isoformat())
    if captures is not None:
        for ident, event in captures.items():
            check()
            if (len(event['individual_ids']) != event['count'] or
                    indices.get(ident, set()) != set(range(1, event['count'] + 1))):
                raise ValueError('Individual registry must exactly match each capture count')
            event['individual_ids'].sort()
    return result


def _prepared(forecast, prepared, check):
    """Own/hash-bind predictions before the first outcome payload is opened."""
    if (type(forecast) is not dict or type(forecast.get('rows')) is not list or
            type(prepared) is not dict or type(prepared.get('candidates')) is not list):
        raise ValueError('Strict forecast and fixed prepared JSON objects required')
    if len(forecast['rows']) > g0.MAX_MODEL_ROWS:
        raise pi.InputCapacityError('CAPACITY_BLOCKED: complete Stage1 forecast rows')
    if len(prepared['candidates']) != 3:
        raise ValueError('Exact existing fixed3 candidates required')
    for candidate in prepared['candidates']:
        check()
        prediction = candidate.get('prediction') if type(candidate) is dict else None
        if type(prediction) is not dict:
            raise ValueError('Prepared prediction JSON object required')
        units = prediction.get('unit_scores' if candidate.get('candidate_id') == 'HB-B1' else 'unit_predictions')
        if type(units) is not list:
            raise ValueError('Complete native prediction units required')
        if len(units) > g0.MAX_MODEL_ROWS:
            raise pi.InputCapacityError('CAPACITY_BLOCKED: complete Stage1 prediction units')
    forecast, prepared = pure._copy_json([forecast, prepared], check)
    rows, receipt = forecast['rows'], forecast['receipt']
    input_ref(receipt['manifest_ref'])
    if (receipt.get('schema_version') != g0.SCHEMA or
            receipt.get('qualification') != 'STRICT_G0_FORECAST_DECLARATION_VALIDATED' or
            receipt.get('model_rows') != 'COMPLETE_BOUNDED_COLLECTION' or
            receipt.get('row_count') != len(rows) or
            any(receipt.get(flag) is not False for flag in ('fit_authorized', 'scientific_execution_authorized', 'production_authorized'))):
        raise ValueError('Strict complete forecast receipt required')
    if not rows or len(rows) > g0.MAX_MODEL_ROWS or _hash(rows, check) != receipt['canonical_joined_rows_sha256']:
        raise ValueError('Strict joined forecast digest/row bound mismatch')
    if (prepared.get('status') != 'DIAGNOSTIC_CANDIDATES_PREPARED' or
            prepared.get('receipt_sha256') != _hash({k: v for k, v in prepared.items() if k != 'receipt_sha256'}, check)):
        raise ValueError('Complete hash-bound fixed candidates required')
    if any(prepared.get(flag) is not False for flag in ('official_issuance_authorized', 'production_activation_authorized')):
        raise ValueError('Diagnostic candidate preparation cannot carry authority')
    joined = receipt['canonical_joined_rows_sha256']
    cutoff = receipt['cutoff_time']
    if prepared.get('joined_universe_sha256') != joined or pi._time(prepared['cutoff_time']) != pi._time(cutoff):
        raise ValueError('Prepared forecast/cutoff mismatch')
    expected = {}
    night, areas = rows[0]['operational_night'], set()
    windows = set()
    for row in rows:
        check()
        ident, cx, cy = row['row_id'], row['cell_x'], row['cell_y']
        if (type(cx) is not int or type(cy) is not int or ident in expected or
                row['operational_night'] != night or pi._time(row['cutoff_time']) != pi._time(cutoff) or
                row['utm_x_m'] != cx * 100 + 50 or row['utm_y_m'] != cy * 100 + 50):
            raise ValueError('Strict forecast physical identity mismatch')
        expected[ident] = row
        areas.add(models.area_id(cx, cy))
        windows.add(pi._time(row['window_start_jst']))
    if [c.get('candidate_id') for c in prepared['candidates']] != list(models.CANDIDATES):
        raise ValueError('Exact existing fixed3 candidates required')
    projections = []
    for candidate in prepared['candidates']:
        check()
        ident = candidate['candidate_id']
        bound = models._candidate(ident, candidate['model'], candidate['prediction'], joined, expected,
            {'selection_sha256': prepared['training_selection_sha256']}, cutoff, check)
        if any(candidate.get(key) != bound[key] for key in ('model_sha256', 'prediction_sha256',
                'joined_universe_sha256', 'forecast_row_ids', 'forecast_units')):
            raise ValueError('Prepared candidate metadata binding mismatch')
        # Existing model output hashes are checked above; use native per-unit
        # scores, with the same arithmetic mean for every candidate and area.
        groups = {area: [] for area in areas}
        for unit in candidate['prediction']['unit_scores' if ident == 'HB-B1' else 'unit_predictions']:
            check()
            row = expected[unit['row_id']]
            area = models.area_id(row['cell_x'], row['cell_y'])
            if ident == 'HB-B1' and unit.get('area_1km') != area:
                raise ValueError('Hierarchy area geometry mismatch')
            groups[area].append(pure._number(unit['rank_score_diagnostic' if ident == 'HB-B1' else 'spatial_score']))
        projections.append(dict(candidate_id=ident, score_semantics='MEAN_NATIVE_UNIT_RANK_SCORE' if ident == 'HB-B1'
            else 'MEAN_NATIVE_UNIT_SPATIAL_SCORE', model_sha256=bound['model_sha256'],
            prediction_sha256=bound['prediction_sha256'], scores={night: {
                area: mean(values) for area, values in sorted(groups.items())}}))
    return forecast, prepared, night, sorted(areas), windows, projections


def _scope_projection(scope, forecast, night, areas, windows, candidates, reader, check):
    pure._fields(scope, SCOPE_FIELDS)
    cutoff = pi._time(forecast['receipt']['cutoff_time'])
    if (scope['schema_version'] != 'habu-stage1-scope-source-v1' or scope['operational_night'] != night or
            pi._time(scope['cutoff_time']) != cutoff):
        raise ValueError('Prior scope night/cutoff mismatch')
    original = reader.read(forecast['receipt']['manifest_ref'], small=True)
    first, last = pi._time(scope['horizon_start']), pi._time(scope['horizon_end'])
    if (first != pi._time(original['horizon']['start']) or last != pi._time(original['horizon']['end']) or
            first != min(windows) or last != max(windows) + timedelta(minutes=10)):
        raise ValueError('Scope differs from full strict forecast horizon')
    row = dict(operational_night=night, scope=scope['scope'], scope_sha256=_hash(scope['scope'], check),
        cutoff_time=scope['cutoff_time'], horizon_start=scope['horizon_start'], horizon_end=scope['horizon_end'], area_ids=areas)
    universe = dict(schema_version='habu-stage1-universe-v1', nights=[row])
    pure._universe(universe, check)
    x0, y0, x1, y1 = scope['scope']['bbox_utm']
    for forecast_row in forecast['rows']:
        check()
        # Scope contains the whole 100m forecast cell, not just its midpoint.
        x, y = forecast_row['cell_x'] * 100, forecast_row['cell_y'] * 100
        if not (x0 <= x and x + 100 <= x1 and y0 <= y and y + 100 <= y1):
            raise ValueError('Prior scope excludes a forecast unit')
    scores = dict(schema_version='habu-stage1-scores-v1', universe_sha256=_hash(universe, check), candidates=candidates)
    return universe, scores


def _evaluate(root, manifest_ref, forecast, prepared, *, context):
    """One-night, source-bound development consistency; no formal KPI or reveal."""
    if not isinstance(context, pi.ProspectiveReadContext):
        raise ValueError('Existing shared prospective context required')
    check = context.check
    check()
    forecast, prepared, night, areas, windows, candidates = _prepared(forecast, prepared, check)
    reader = g0.G0ArtifactReader(root, context)
    input_ref(manifest_ref)
    manifest_ref = dict(manifest_ref)
    manifest = reader.read(manifest_ref, small=True)
    pure._fields(manifest, MANIFEST_FIELDS)
    if (manifest['schema_version'] != VERSION or manifest['purpose'] != 'DEVELOPMENT_EVALUATION_ONLY' or
            manifest['operational_night'] != night or
            manifest['forecast_manifest_sha256'] != forecast['receipt']['manifest_ref']['sha256'] or
            manifest['joined_universe_sha256'] != forecast['receipt']['canonical_joined_rows_sha256']):
        raise ValueError('Stage1 manifest version/purpose/forecast identity mismatch')
    evaluation = pi._time(manifest['evaluation_as_of'])
    cutoff = pi._time(forecast['receipt']['cutoff_time'])
    if evaluation <= cutoff:
        raise ValueError('Development evaluation must be after forecast cutoff')
    nodes = manifest['source_nodes']
    if type(nodes) is not list or len(nodes) > g0.MAX_SOURCE_NODES:
        raise pi.InputCapacityError('CAPACITY_BLOCKED: Stage1 source graph')
    by_id, paths = {}, set()
    for node in nodes:
        check()
        pure._fields(node, NODE_FIELDS)
        ident = node['id']
        if type(ident) is not str or not g0.IDENTIFIER.fullmatch(ident) or ident in by_id:
            raise ValueError('Invalid/duplicate Stage1 source identity')
        input_ref(node['ref'])
        if node['ref']['size_bytes'] > pure.MAX_JSON_BYTES:
            raise pi.InputCapacityError('CAPACITY_BLOCKED: Stage1 source bytes')
        path = node['ref']['path']
        if path in paths or node['role'] not in (*ROLES, 'support'):
            raise ValueError('Duplicate source path or unknown source role')
        paths.add(path)
        if (node['source_kind'] not in ('RAW', 'DERIVED') or type(node['parents']) is not list or
                (node['source_kind'] == 'RAW') != (not node['parents'])):
            raise ValueError('Explicit RAW/DERIVED lineage required')
        # Preflight every path/ancestor before opening any source payload.
        local_path(root, path)
        by_id[ident] = node
    roots = {}
    for role in ROLES:
        ident = manifest[role + '_id']
        if ident is not None:
            if type(ident) is not str or ident not in by_id or by_id[ident]['role'] != role:
                raise ValueError('Missing or mistyped Stage1 root identity')
            roots[role] = ident
    if nodes:
        graph = g0.validate_readiness_graph([{key: node[key] for key in ('id', 'parents', 'readiness', 'usable_at')}
            for node in nodes], evaluation, check=check)
    else:
        graph = dict(ready_by_id={}, topological_order=[])
    g0.validate_readiness(manifest['readiness'], manifest['usable_at'], evaluation,
        parent_usable_at=graph['ready_by_id'].values())

    def closure(ident):
        found, pending = set(), [ident]
        while pending:
            check()
            current = pending.pop()
            if current not in found:
                found.add(current)
                pending.extend(by_id[current]['parents'])
        return found

    reachable = set()
    for ident in roots.values():
        reachable.update(closure(ident))
    if reachable != set(by_id):
        raise ValueError('Unreachable Stage1 source nodes')
    scope_closure = closure(roots['scope']) if 'scope' in roots else set()
    for ident in scope_closure:
        if by_id[ident]['role'] not in ('scope', 'support') or graph['ready_by_id'][ident] >= cutoff:
            raise ValueError('Scope and every ancestor must be ex ante')

    payloads, missing = {}, [role for role in ROLES if role not in roots]

    def read_node(ident):
        node = by_id[ident]
        try:
            payloads[ident] = reader.read(node['ref'], parse=node['role'] in ('scope', 'coverage'))
        except FileNotFoundError:
            missing.append('FILE:' + ident)
        except ValueError as exc:
            if type(exc) is ValueError and str(exc) == 'Missing prospective input':
                missing.append('FILE:' + ident)
            else:
                raise

    # Bind the entire prior scope/horizon before opening any outcome payload,
    # regardless of adversarial node-list ordering.
    for ident in graph['topological_order']:
        if ident in scope_closure:
            read_node(ident)
    scope = payloads.get(roots.get('scope'))
    universe, scores, ledger = None, None, None
    if scope is not None:
        universe, scores = _scope_projection(scope, forecast, night, areas, windows, candidates, reader, check)
    # Every non-root source byte is consumed too; no metadata-only source DAG.
    for ident in graph['topological_order']:
        if ident not in scope_closure:
            read_node(ident)
    coverage = payloads.get(roots.get('coverage'))
    captures_raw = payloads.get(roots.get('captures'))
    individual_raw = payloads.get(roots.get('individuals'))
    captures = _captures(captures_raw, check) if captures_raw is not None else None
    individuals = _individuals(individual_raw, captures, check) if individual_raw is not None else None

    # This v1 observational closure means actual records all the way to RAW.
    # It deliberately cannot mix standing policy/support prerequisites into an
    # outcome lineage: that requires a separate typed non-observational contract.
    required_after = {}
    for role, records in (('captures', captures), ('individuals', individuals)):
        if role in roots and records:
            bound = max(pi._time(row['datetime']) for row in records.values())
            for ident in closure(roots[role]):
                required_after[ident] = max(required_after.get(ident, bound), bound)
    if coverage is not None:
        pure._fields(coverage, COVERAGE_FIELDS)
        if (coverage['schema_version'] != 'habu-stage1-coverage-source-v1' or
                coverage['declaration'] not in ('DECLARED_COMPLETE', 'UNKNOWN', 'INCOMPLETE') or
                coverage['operational_night'] != night):
            raise ValueError('Invalid explicit Stage1 coverage declaration')
        pure._sha(coverage['scope_sha256'])
        start, end = pi._time(coverage['horizon_start']), pi._time(coverage['horizon_end'])
        night_start = pi._time(night + 'T07:00:00+09:00')
        if not night_start <= start < end <= night_start + timedelta(days=1):
            raise ValueError('Coverage horizon contradicts operational night')
        for key in ('event_ids', 'individual_ids'):
            values = coverage[key]
            if type(values) is not list:
                raise ValueError('Explicit coverage ID arrays required')
            if len(values) > (pure.MAX_EVENTS if key == 'event_ids' else pure.MAX_INDIVIDUALS):
                raise pi.InputCapacityError('CAPACITY_BLOCKED: coverage IDs')
            if any(type(value) is not str or not value or len(value) > 128 for value in values) or len(set(values)) != len(values):
                raise ValueError('Explicit unique coverage IDs required')
        known = []
        for key, records in (('event_ids', captures), ('individual_ids', individuals)):
            if records is not None:
                if not set(coverage[key]) <= set(records):
                    raise ValueError('Coverage references an ID absent from bound actual source')
                # The exact ref binds the whole actual CSV, even if this
                # UNKNOWN declaration has no listed IDs or scope is missing.
                known.extend(pi._time(row['datetime']) for row in records.values())
        if coverage['declaration'] == 'DECLARED_COMPLETE':
            known.append(end)
        if known:
            bound = max(known)
            for ident in closure(roots['coverage']):
                required_after[ident] = max(required_after.get(ident, bound), bound)
    for ident, bound in required_after.items():
        check()
        node = by_id[ident]
        if node['role'] in ('scope', 'support'):
            raise ValueError('CAPABILITY_BLOCKED: observational lineage cannot contain scope/standing support')
        if any(pi._time(node['readiness'][key]) < bound for key in pi.READINESS_FIELDS):
            raise ValueError('Actual source lineage readiness precedes bound observed record/horizon')
    if required_after and any(pi._time(manifest['readiness'][key]) < max(required_after.values()) for key in pi.READINESS_FIELDS):
        raise ValueError('Manifest readiness precedes bound actual record/horizon')

    selected = []
    if scope is not None:
        first, last = pi._time(scope['horizon_start']), pi._time(scope['horizon_end'])
        x0, y0, x1, y1 = scope['scope']['bbox_utm']
        if captures is not None:
            selected = [event for event in captures.values() if event['operational_night'] == night and
                first <= pi._time(event['datetime']) < last and
                x0 <= event['utm_x_m'] < x1 and y0 <= event['utm_y_m'] < y1]
        if coverage is not None:
            if (coverage['scope_sha256'] != universe['nights'][0]['scope_sha256'] or
                    pi._time(coverage['horizon_start']) != first or pi._time(coverage['horizon_end']) != last):
                raise ValueError('Coverage scope/horizon mismatch')
    if coverage is not None:
        for role in ('captures', 'individuals'):
            input_ref(coverage[role + '_ref'])
            if role in roots and coverage[role + '_ref'] != by_id[roots[role]]['ref']:
                raise ValueError('Coverage source byte binding mismatch')
        if scope is not None and captures is not None and individuals is not None:
            if (set(coverage['event_ids']) != {event['event_id'] for event in selected} or
                    set(coverage['individual_ids']) != {i for event in selected for i in event['individual_ids']}):
                raise ValueError('Coverage IDs differ from entire source scope, including outside-universe individuals')
    if not missing and captures is not None and individuals is not None:
        source_refs = [dict(path=by_id[roots[role]]['ref']['path'], sha256=by_id[roots[role]]['ref']['sha256'],
            bytes=by_id[roots[role]]['ref']['size_bytes']) for role in ('captures', 'individuals', 'coverage')]
        event_paths = [by_id[roots[role]]['ref']['path'] for role in ('captures', 'individuals')]
        ledger = dict(schema_version='habu-stage1-ledger-v1', source_refs=source_refs,
            complete_scopes=[dict(operational_night=night, scope_sha256=_hash(scope['scope'], check),
                horizon_start=scope['horizon_start'], horizon_end=scope['horizon_end'],
                declaration=coverage['declaration'], coverage_ref=source_refs[-1], source_paths=event_paths)],
            events=[dict({k: v for k, v in event.items() if k != 'count'}, source_paths=event_paths) for event in selected])
        ledger['ledger_sha256'] = _hash(ledger, check)
    result = pure.evaluate_full_ledger_stage1(universe, scores, ledger,
        budget_seconds=min(pure.MAX_BUDGET_SECONDS, context.remaining_seconds), check=check)
    reader.rescan()
    check()
    result.pop('receipt_sha256')
    result.update(source_contract_version=VERSION, source_authentication='NOT_ATTESTED',
        source_consistency='DECLARED_CONSISTENCY_ONLY', selection_authorized=False,
        promotion_authorized=False, confirmation_authorized=False,
        source_summary=dict(capture_events=len(captures or {}), individuals=len(individuals or {})),
        source_receipt=dict(manifest_ref=dict(manifest_ref), evaluation_as_of=manifest['evaluation_as_of'],
            readiness=manifest['readiness'], usable_at=manifest['usable_at'],
            prepared_receipt_sha256=prepared['receipt_sha256'],
            projection_sha256={name: _hash(value, check) if value is not None else None
                for name, value in (('universe', universe), ('scores', scores), ('ledger', ledger))},
            consumed_sha256={path: ref['sha256'] for path, ref in reader.refs.items()},
            consumed_refs=list(reader.refs.values()), missing_inputs=sorted(set(missing)),
            actual_read_bytes=context.bytes_read))
    return pure._finish(result, check)


def evaluate_stage1_sources(root, manifest_ref, forecast, prepared, *, context):
    """One absolute read/deadline budget; failures never release partial metrics."""
    try:
        return _evaluate(root, manifest_ref, forecast, prepared, context=context)
    except pure.Stage1CapacityBlocked as exc:
        raise pi.InputCapacityError(str(exc)) from exc
    except pure.Stage1BudgetBlocked as exc:
        raise TimeoutError(str(exc)) from exc
    except (TypeError, KeyError, OverflowError, RecursionError) as exc:
        raise ValueError('Invalid Stage1 source contract structure') from exc
