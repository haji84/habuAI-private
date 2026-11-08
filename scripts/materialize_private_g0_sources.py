"""Native Task6a observations -> private, declared G0 inputs; never a certifier.

Use the existing corpus/manifest pair or a private label-free packet of physical
feature rows and source references in the existing G0 shapes. Missing components
produce a private BLOCKED audit. Labels, features and historical availability
are never invented, and the materializer does not fit or authenticate sources.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import evidence_audit as ea
import g0_forecast_contract as g0
import g0_training_source_contract as training_gate
import training_corpus as tc
from master_contracts import canonical_bytes, digest, validate_night
from master_inventory import local_path
from prospective_inputs import ProspectiveReadContext, InputCapacityError
from habu_qualified_fit_cycle import _private_output

VERSION = 'habu-private-task6a-g0-materializer-v1'
COMPONENTS_VERSION = 'habu-private-task6a-g0-components-v1'
COMPONENT_FIELDS = {'policy', 'features', 'feature_definition_sha256', 'source_nodes'}
COMPONENT_ROW_FIELDS = {'night', 'cell_x', 'cell_y', 'window_start_jst', 'source_refs',
                        'features', 'feature_available_at', 'feature_source_refs',
                        'row_validity', 'negative_scope'}
SCOPE_FIELDS = {'active_search_ref', 'complete_outcome_ref', 'outcome_source_ref'}
MAX_ACTUAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_ROWS = tc.MAX_ROWS


def _time(value):
    if type(value) is not str or len(value) > 64:
        raise ValueError('MATERIALIZER_AWARE_TIME_REQUIRED')
    if re.search(r'[.,]\d{7}', value):
        raise ValueError('MATERIALIZER_UNREPRESENTABLE_TIME_PRECISION')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('MATERIALIZER_AWARE_TIME_REQUIRED')
    return result.astimezone(timezone.utc)


def _unit(row):
    cx, cy = row['cell_x'], row['cell_y']
    if type(cx) is not int or type(cy) is not int:
        raise ValueError('MATERIALIZER_INTEGER_CELL_REQUIRED')
    instant = _time(row['window_start_jst'])
    if instant.minute % 10 or instant.second or instant.microsecond:
        raise ValueError('MATERIALIZER_COMPLETE_WINDOW_REQUIRED')
    night = row.get('night', row.get('night_date'))
    validate_night(night)
    if ea.night_for(instant) != night:
        raise ValueError('MATERIALIZER_NIGHT_MISMATCH')
    return cx, cy, instant.isoformat()


def _reference(path, raw):
    return dict(path=path, sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _owned_ref(value, purpose):
    if type(value) is not dict or any(type(k) is not str for k in value):
        raise ValueError('MATERIALIZER_PRIMITIVE_REFERENCE_REQUIRED')
    if set(value) != {'path', 'sha256', 'size_bytes'}:
        raise ValueError('MATERIALIZER_EXACT_REFERENCE_REQUIRED')
    if (type(value['path']) is not str or type(value['sha256']) is not str or
            type(value['size_bytes']) is not int):
        raise ValueError('MATERIALIZER_PRIMITIVE_REFERENCE_REQUIRED')
    owned = dict(value)
    training_gate._reference(owned, purpose)
    return owned


def _reference_json(text):
    if len(text) > 4096:
        raise ValueError('MATERIALIZER_REFERENCE_CAPACITY')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('MATERIALIZER_DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=unique)


def _write(output, relative, raw, context, *, _created=None):
    context.check()
    target = local_path(output, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    target = local_path(output, relative)
    created = False
    try:
        with target.open('xb') as stream:
            created = True
            identity = target.stat()
            if _created is not None:
                _created.append((relative, identity.st_dev, identity.st_ino))
            for start in range(0, len(raw), 65536):
                context.check()
                stream.write(raw[start:start + 65536])
        ref = _reference(relative, raw)
        actual = g0.G0ArtifactReader(output, context).read(ref, parse=False)
        if actual != raw:
            raise ValueError('MATERIALIZER_OUTPUT_CHANGED')
        context.check()
        return ref
    except FileExistsError:
        ref = _reference(relative, raw)
        if g0.G0ArtifactReader(output, context).read(ref, parse=False) != raw:
            raise ValueError('MATERIALIZER_IMMUTABLE_CONFLICT')
        return ref
    except BaseException:
        # Compensate only a newly created, still-owned incomplete artifact.
        if created:
            current = local_path(output, relative)
            try:
                stat = current.stat()
                if (stat.st_dev, stat.st_ino) == (identity.st_dev, identity.st_ino):
                    current.unlink()
            except FileNotFoundError:
                pass
        raise


def _save(output, relative, value, context, *, _created=None):
    return _write(output, relative, canonical_bytes(value) + b'\n', context, _created=_created)


def _discard_owned(output, owned):
    """Revoke only this invocation's incomplete completion, never foreign data."""
    for relative, device, inode in owned:
        try:
            path = local_path(output, relative)
            current = path.stat()
            if (current.st_dev, current.st_ino) == (device, inode):
                path.unlink()
        except (FileNotFoundError, ValueError):
            pass


def _precise_owner_capture(root, event, reader, context):
    """Check explicit byte-bound record columns; missing uncertainty stays unknown.

    This is a conservative projection of source declarations, not independent
    authentication. Native source-role review is still required upstream.
    """
    if event.get('canonical_eligible') is not True:
        return False
    for ref in event['source_refs']:
        verified = False
        context.check()
        selector = ref.get('selector', {})
        index = selector.get('csv_row')
        if type(index) is not int or index < 2:
            continue
        path = local_path(root, ref['path'])
        binding = dict(path=ref['path'], sha256=ref['sha256'], size_bytes=path.stat().st_size)
        raw = reader.read(binding, parse=False)
        table = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
        if table.fieldnames is None or len(set(table.fieldnames)) != len(table.fieldnames):
            raise ValueError('MATERIALIZER_CAPTURE_COLUMNS')
        for line, row in enumerate(table, 2):
            context.check()
            if line != index:
                continue
            if (None in row or any(v is None for v in row.values()) or
                    row.get('event_id', row.get('id')) != event['event_id']):
                raise ValueError('MATERIALIZER_CAPTURE_SELECTOR')
            if (row.get('owner_role') != 'OWNER' or row.get('species') != 'HABU' or
                    row.get('time_semantics') != 'OBSERVED_AT'):
                break
            recorded = next((row[k] for k in ('datetime_jst', 'event_time_local', 'datetime', 'time_jst', 'timestamp')
                             if row.get(k)), None)
            try:
                if _time(recorded) != _time(event['datetime_jst']):
                    break
            except ValueError:
                break
            try:
                uncertainty = float(row['uncertainty_seconds'])
                accuracy = float(row['accuracy_m'])
            except (KeyError, TypeError, ValueError):
                break
            if not all(math.isfinite(x) and x >= 0 for x in (uncertainty, accuracy)):
                break
            if uncertainty > 31536000 or accuracy > 1000000:
                break
            instant = _time(event['datetime_jst'])
            key = ea.unit_key(event['latitude'], event['longitude'], instant)
            start = _time(key[2])
            if (instant - timedelta(seconds=uncertainty) < start or
                    instant + timedelta(seconds=uncertainty) >= start + timedelta(seconds=600)):
                break
            x, y = ea.utm52n(event['latitude'], event['longitude'])
            if (x - accuracy < key[0] * 100 or x + accuracy >= (key[0] + 1) * 100 or
                    y - accuracy < key[1] * 100 or y + accuracy >= (key[1] + 1) * 100):
                break
            verified = True
            break
        if not verified:
            return False
    return bool(event['source_refs'])


def _observations(root, audit, reader, context):
    ledger = audit['outcome_ledger']
    if ledger.get('ledger_sha256'):
        body = {k: v for k, v in ledger.items() if k != 'ledger_sha256'}
        if digest(body) != ledger['ledger_sha256']:
            raise ValueError('MATERIALIZER_LEDGER_SEAL')
    units = {}
    for unit in audit['observation_units']:
        context.check()
        key = _unit(unit)
        if key in units:
            raise ValueError('MATERIALIZER_DUPLICATE_NATIVE_UNIT')
        units[key] = unit
    events, seen_ids = {}, set()
    canonical = {e['event_id']: e for e in audit['capture_audit']['events']
                 if e.get('canonical_eligible') is True}
    for event in ledger['events']:
        context.check()
        identity = event['event_id']
        if identity in seen_ids or identity not in canonical or canonical[identity] != event:
            raise ValueError('MATERIALIZER_CANONICAL_EVENT_CONFLICT')
        seen_ids.add(identity)
        key = ea.unit_key(event['latitude'], event['longitude'], _time(event['datetime_jst']))
        normalized_key = key[0], key[1], _time(key[2]).isoformat()
        if normalized_key not in units:
            raise ValueError('MATERIALIZER_ORPHAN_CANONICAL_EVENT')
        events.setdefault(normalized_key, []).append(event)
    if seen_ids != set(canonical):
        raise ValueError('MATERIALIZER_CANONICAL_LEDGER_MISMATCH')
    if len(units) > MAX_ROWS:
        raise InputCapacityError('MATERIALIZER_ROW_CAPACITY')
    rows = []
    for key, unit in sorted(units.items()):
        context.check()
        captured = sorted(events.get(key, []), key=lambda e: e['event_id'])
        precise = bool(captured) and all(_precise_owner_capture(root, e, reader, context) for e in captured)
        reasons = []
        if captured and not precise:
            reasons.append('CAPTURE_ROLE_OR_PRECISION_NOT_ESTABLISHED')
        if not captured and unit.get('label') == 0:
            reasons.append('G0_COMPLETE_NEGATIVE_SCOPE_NOT_ESTABLISHED')
        if not captured and unit.get('label') is None:
            reasons.append('UNKNOWN_NOT_NEGATIVE')
        ids = [e['event_id'] for e in captured]
        rows.append(dict(row_id='task6a-' + digest(list(key)), night=unit['night_date'],
            cell_x=key[0], cell_y=key[1], window_start_jst=key[2],
            observation='capture_observed' if precise else 'UNKNOWN', label=1 if precise else None,
            quality='AUDITED_OBSERVED' if precise else None, capture_event_ids=ids,
            recorded_quantity=sum(e['capture_count'] for e in captured) if captured else None,
            individual_ids=sorted({i for e in captured for i in e['individual_ids']}),
            outcome_source_refs=sorted({r['path'] for e in captured for r in e['source_refs']}),
            source_refs=sorted({r['path'] for r in unit['source_refs']} |
                               {r['path'] for e in captured for r in e['source_refs']}),
            native_negative_candidate=not captured and unit.get('label') == 0,
            reason_codes=reasons))
    return rows


def _bound(ref, stamp, parents=()):
    latest = max([_time(stamp), *(_time(t) for t in parents)]).isoformat()
    return dict(ref=ref, readiness={k: latest for k in g0.pi.READINESS_FIELDS}, usable_at=latest)


def _component_time(value):
    if type(value) is not str or not re.fullmatch(
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?'
            r'(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])', value):
        raise ValueError('MATERIALIZER_COMPONENT_TIME_REQUIRED')
    return _time(value)


def _source_components(reader, reference, context):
    """Project a label-free private packet into the existing materialization inputs.

    Policy, features, source nodes and physical validity use existing G0 shapes.
    Rows bind explicit feature values to physical units and optionally reference
    existing scope receipts. The packet cannot declare labels or eligibility.
    """
    if reference['size_bytes'] > tc.MAX_BYTES:
        raise InputCapacityError('MATERIALIZER_COMPONENT_BYTE_CAPACITY')
    packet = reader.read(reference)
    if set(packet) != {'schema_version', 'rows'} | COMPONENT_FIELDS or packet['schema_version'] != COMPONENTS_VERSION:
        raise ValueError('MATERIALIZER_COMPONENT_FIELDS')
    if type(packet['rows']) is not list or type(packet['source_nodes']) is not list:
        raise ValueError('MATERIALIZER_COMPONENT_LISTS_REQUIRED')
    if len(packet['rows']) > MAX_ROWS or not 0 < len(packet['source_nodes']) <= g0.MAX_SOURCE_NODES:
        raise InputCapacityError('MATERIALIZER_COMPONENT_ROW_OR_SOURCE_CAPACITY')
    manifest = dict(schema_version=training_gate.VERSION, kind='TRAIN_ONLY_SOURCE_CLOSURE',
                    **{key: packet[key] for key in COMPONENT_FIELDS})
    source_manifest = []
    for node in manifest['source_nodes']:
        context.check()
        training_gate._fields(node, training_gate.NODE_FIELDS)
        training_gate._reference(node['ref'], 'source')
        g0._object(node['readiness'], g0.pi.READINESS_FIELDS, 'Required four readiness timestamps')
        source_manifest.append(dict(path=node['ref']['path'], sha256=node['ref']['sha256'],
                                    role=node['source_role'], received_at=node['readiness']['source_received_at']))
    rows, validity = [], {}
    for source in packet['rows']:
        context.check()
        if type(source) is not dict or set(source) != COMPONENT_ROW_FIELDS:
            raise ValueError('MATERIALIZER_COMPONENT_ROW_FIELDS')
        _component_time(source['window_start_jst'])
        key = _unit(source)
        row_id = 'component-' + digest(list(key))
        if row_id in validity:
            raise ValueError('MATERIALIZER_DUPLICATE_FEATURE_UNIT_OR_ID')
        refs = source['source_refs']
        if (type(refs) is not list or not refs or any(type(ref) is not str for ref in refs) or
                len(set(refs)) != len(refs)):
            raise ValueError('MATERIALIZER_COMPONENT_ROW_SOURCE_REFS')
        row = {k: v for k, v in source.items() if k not in ('row_validity', 'negative_scope')}
        # Full-window validity remains an explicit strict selector check.
        row.update(row_id=row_id, feature_valid_for_night=True)
        scope = source['negative_scope']
        if scope is not None:
            if type(scope) is not dict or set(scope) != SCOPE_FIELDS:
                raise ValueError('MATERIALIZER_COMPONENT_NEGATIVE_SCOPE_FIELDS')
            # These legacy fields only reach the scope verifier for a native candidate.
            row.update(**scope, search_role='SEARCH', all_captures_recorded=True, gpx_segment_eligible=True)
        rows.append(row)
        validity[row_id] = source['row_validity']
    return manifest, dict(source_manifest=source_manifest, rows=rows), dict(
        schema_version='habu-g0-training-validity-v1',
        feature_definition_sha256=manifest['feature_definition_sha256'], rows=validity)


def _complete(root, output, prefix, audit, observations, reader, context,
              feature_ref, manifest_ref, heldout_night, fit_cutoff, forecast_cutoff, *, components_ref=None):
    """Project literal existing component shapes, then run the unchanged G0 gate."""
    if None in (heldout_night, fit_cutoff, forecast_cutoff):
        raise ValueError('MATERIALIZER_FUTURE_FIT_CONTEXT_REQUIRED')
    validate_night(heldout_night)
    if components_ref is None:
        template = reader.read(feature_ref)
        manifest = reader.read(manifest_ref, small=True)
        training_gate._fields(manifest, training_gate.FIELDS)
        if (manifest['schema_version'] != training_gate.VERSION or
                manifest['kind'] != 'TRAIN_ONLY_SOURCE_CLOSURE' or
                manifest['corpus']['ref'] != feature_ref):
            raise ValueError('MATERIALIZER_EXISTING_COMPONENT_BINDING')
        if (template.get('schema_version') != '1.0' or
                template.get('qualification') != 'AUDITED_TRAIN_ONLY' or
                type(template.get('rows')) is not list or len(template['rows']) > MAX_ROWS):
            raise ValueError('MATERIALIZER_EXISTING_CORPUS_REQUIRED')
        clock = _time
    else:
        manifest, template, physical = _source_components(reader, components_ref, context)
        clock = _component_time
    for node in manifest['source_nodes']:
        context.check()
        training_gate._reference(node['ref'], 'source')
    for feature in manifest['features']:
        training_gate._reference(g0._base_ref(feature['code_ref']), 'code')
    training_gate._reference(manifest['policy']['ref'], 'policy')
    original_artifacts = []
    if components_ref is None:
        training_gate._reference(manifest['row_validity']['ref'], 'source')
        physical = reader.read(manifest['row_validity']['ref'])
        training_gate._fields(physical, {'schema_version', 'corpus_sha256', 'feature_definition_sha256', 'rows'})
        if (physical['schema_version'] != 'habu-g0-training-validity-v1' or
                physical['corpus_sha256'] != feature_ref['sha256'] or
                physical['feature_definition_sha256'] != manifest['feature_definition_sha256']):
            raise ValueError('MATERIALIZER_EXISTING_VALIDITY_BINDING')
        original_artifacts = [manifest, manifest['corpus'], manifest['row_validity']]
    for bound in [*original_artifacts, manifest['policy'],
                  *manifest['source_nodes'], *(f['code_ref'] for f in manifest['features'])]:
        for value in bound['readiness'].values():
            clock(value)
        clock(bound['usable_at'])
    for source in template['source_manifest']:
        clock(source['received_at'])
    for row_values in physical['rows'].values():
        for feature_value in row_values.values():
            clock(feature_value['valid_time']['start'])
            clock(feature_value['valid_time']['end'])
    source_map = tc.source_manifest(root, template, _read_context=context)
    projected, by_key, template_ids = [], {}, set()
    for row in template['rows']:
        context.check()
        key = _unit(row)
        if key in by_key or type(row.get('row_id')) is not str or row['row_id'] in template_ids:
            raise ValueError('MATERIALIZER_DUPLICATE_FEATURE_UNIT_OR_ID')
        by_key[key] = row
        template_ids.add(row['row_id'])
    if set(by_key) != {_unit(row) for row in observations}:
        raise ValueError('MATERIALIZER_FEATURE_PHYSICAL_COVERAGE')
    checked = datetime.now(timezone.utc).isoformat()
    cutoff_now = _time(checked) + timedelta(microseconds=1)
    # Rebinding new derived artifacts must not repair invalid original readiness.
    original_graph = g0.validate_readiness_graph([
        {k: n[k] for k in ('id', 'parents', 'readiness', 'usable_at')}
        for n in manifest['source_nodes']], cutoff_now, check=context.check)
    definitions, code_ready, _ = g0._definitions(manifest['features'],
        manifest['feature_definition_sha256'], reader, cutoff_now)
    if components_ref is None:
        corpus_ready = training_gate._ready(manifest['corpus']['readiness'], manifest['corpus']['usable_at'],
            cutoff_now, parents=[*original_graph['ready_by_id'].values(), *code_ready.values()])
        validity_ready = training_gate._ready(manifest['row_validity']['readiness'],
            manifest['row_validity']['usable_at'], cutoff_now, parents=[corpus_ready])
    policy_ready = training_gate._ready(manifest['policy']['readiness'], manifest['policy']['usable_at'], cutoff_now)
    if components_ref is None:
        training_gate._ready(manifest['readiness'], manifest['usable_at'], cutoff_now,
                             parents=[corpus_ready, validity_ready, policy_ready])
    source_nodes = {n['id']: n for n in manifest['source_nodes']}
    nodes_by_path = {n['ref']['path']: n for n in manifest['source_nodes']}
    raw_cache = {}
    cached_members = 0
    def raw_ancestors(identifier):
        nonlocal cached_members
        context.check()
        if identifier in raw_cache:
            return raw_cache[identifier]
        node = source_nodes[identifier]
        values = set()
        if node['source_kind'] == 'RAW':
            if node['parents']:
                raise ValueError('MATERIALIZER_RAW_SOURCE_HAS_PARENTS')
            values.add(node['ref']['sha256'])
        else:
            if not node['parents']:
                raise ValueError('MATERIALIZER_DERIVED_SOURCE_MISSING_PARENTS')
            for parent in node['parents']:
                context.check()
                inherited = raw_ancestors(parent)
                if cached_members + len(values) + len(inherited) > 1000000:
                    raise InputCapacityError('MATERIALIZER_RAW_LINEAGE_CAPACITY')
                values.update(inherited)
        if cached_members + len(values) > 1000000:
            raise InputCapacityError('MATERIALIZER_RAW_LINEAGE_CAPACITY')
        cached_members += len(values)
        raw_cache[identifier] = values
        return values
    names = {f['name'] for f in manifest['features']}
    updated_physical = copy.deepcopy(physical)
    updated_physical['rows'] = {}
    for observed in observations:
        context.check()
        original = by_key[_unit(observed)]
        if set(original.get('features', {})) != names:
            raise ValueError('MATERIALIZER_REGISTERED_FEATURE_SET')
        for value in original.get('feature_available_at', {}).values():
            clock(value)
        # Preserve all Task6a diagnostic/protocol lineage separately; a recording
        # policy is not a G0 label/feature source or an independent scope proof.
        if any(p not in source_map or source_map[p]['role'] != 'label'
               for p in observed['outcome_source_refs']):
            raise ValueError('MATERIALIZER_MISSING_BOUND_LABEL_SOURCE')
        refs = sorted(set(original.get('source_refs', [])) |
                      {p for p in observed['source_refs'] if p in source_map})
        if not refs or any(p not in source_map for p in refs):
            raise ValueError('MATERIALIZER_MISSING_OBSERVATION_SOURCE_BINDING')
        for path in observed['source_refs']:
            known = next((s for s in audit['source_manifest'] if s['path'] == path), None)
            if known is not None and path in source_map:
                received = known.get('first_verified_received_at') or audit['verified_at']
                if source_map[path]['received_at'] < _time(received):
                    raise ValueError('MATERIALIZER_BACKDATED_SOURCE_RECEIPT')
        row = dict(row_id=observed['row_id'], night=observed['night'], cell_x=observed['cell_x'],
            cell_y=observed['cell_y'], window_start_jst=observed['window_start_jst'],
            observation=observed['observation'], label=observed['label'], quality=observed['quality'],
            capture_event_ids=list(observed['capture_event_ids']), source_refs=refs,
            label_available_at=checked, audit_available_at=checked,
            features=copy.deepcopy(original['features']),
            feature_available_at=copy.deepcopy(original.get('feature_available_at', {})),
            feature_source_refs=copy.deepcopy(original.get('feature_source_refs', {})),
            feature_valid_for_night=original.get('feature_valid_for_night'),
            task6a_source_refs=list(observed['source_refs']))
        outcome = original.get('outcome_source_ref')
        if observed['capture_event_ids']:
            possible = [p for p in observed['source_refs'] if source_map[p]['role'] == 'label']
            if not possible:
                raise ValueError('MATERIALIZER_MISSING_BOUND_LABEL_SOURCE')
            outcome = sorted(possible)[0]
        if outcome is not None:
            row['outcome_source_ref'] = outcome
        # Scope declarations are not features. Only the existing native verifier
        # may permit an already observed Negative in the precise whole window.
        if observed['native_negative_candidate']:
            for key in ('active_search_ref', 'complete_outcome_ref', 'search_role',
                        'all_captures_recorded', 'gpx_segment_eligible'):
                if key in original:
                    row[key] = copy.deepcopy(original[key])
            row.update(observation='observed_negative', label=0, quality='AUDITED_OBSERVED')
            try:
                for scope_key in ('active_search_ref', 'complete_outcome_ref'):
                    node = nodes_by_path[row[scope_key]['path']]
                    proof = reader.read(node['ref'])
                    clock(proof['qualified_at'])
                    clock(proof['scope']['start'])
                    clock(proof['scope']['end'])
                problems = tc.negative_eligibility_reasons(root, row, source_map,
                    min(_time(fit_cutoff), _time(forecast_cutoff)), _read_context=context)
                if not problems:
                    search_node = nodes_by_path[row['active_search_ref']['path']]
                    outcome_node = nodes_by_path[row['complete_outcome_ref']['path']]
                    if raw_ancestors(search_node['id']) & raw_ancestors(outcome_node['id']):
                        problems.append('NEGATIVE_RAW_LINEAGE_NOT_INDEPENDENT')
            except (ValueError, KeyError, OSError):
                context.check()
                problems = ['G0_COMPLETE_NEGATIVE_SCOPE_NOT_ESTABLISHED']
            if problems:
                row.update(observation='UNKNOWN', label=None, quality=None)
                observed['reason_codes'] = sorted(set(problems))
            else:
                observed.update(observation='observed_negative', label=0, quality='AUDITED_OBSERVED',
                                reason_codes=[])
        projected.append(row)
        if original['row_id'] not in physical['rows']:
            raise ValueError('MATERIALIZER_MISSING_PHYSICAL_VALIDITY')
        updated_physical['rows'][row['row_id']] = copy.deepcopy(physical['rows'][original['row_id']])
    corpus = dict(schema_version='1.0', qualification='AUDITED_TRAIN_ONLY',
        source_manifest=copy.deepcopy(template['source_manifest']), rows=projected,
        task6a_provenance=dict(implementation_version=audit['implementation_version'],
            audit_sha256=audit['audit_sha256'], verified_at=audit['verified_at'],
            source_authentication='NOT_ATTESTED'))
    if components_ref is not None:
        corpus['task6a_provenance']['components_ref'] = components_ref
    new_manifest = copy.deepcopy(manifest)
    # Only the newly performed label audit changes source qualification time;
    # original source receipt times and all actual feature declarations remain.
    for node in new_manifest['source_nodes']:
        if node['source_role'] == 'label':
            node['readiness']['audited_at'] = max(_time(node['readiness']['audited_at']), _time(checked)).isoformat()
    by_id = {n['id']: n for n in new_manifest['source_nodes']}
    active, ready = set(), {}
    def node_ready(identifier):
        context.check()
        if identifier in active or identifier not in by_id:
            raise ValueError('MATERIALIZER_SOURCE_DAG')
        if identifier in ready:
            return ready[identifier]
        active.add(identifier)
        node = by_id[identifier]
        own = [_time(v) for v in node['readiness'].values()]
        parent = [node_ready(p) for p in node['parents']]
        value = max(own + parent)
        if value > _time(checked):
            raise ValueError('MATERIALIZER_FUTURE_COMPONENT_READINESS')
        node['usable_at'] = value.isoformat()
        ready[identifier] = value
        active.remove(identifier)
        return value
    for identifier in by_id:
        node_ready(identifier)
    reader.read(new_manifest['policy']['ref'], small=True)
    for node in new_manifest['source_nodes']:
        reader.read(node['ref'], parse=False)
    reader.rescan()
    workspace = output / prefix / 'workspace'
    workspace.mkdir(parents=True, exist_ok=True)
    # A valid G0 workspace needs its literal dependencies. This copy does not
    # reinterpret them; portable packaging remains prepare_source's operation.
    for ref in tuple(reader.refs.values()):
        context.check()
        _write(workspace, ref['path'], reader.read(ref, parse=False), context)
    context.check()
    audit_copy = _save(workspace, 'evidence/materialized-task6a/' + audit['audit_sha256'] + '-audit.json',
                       audit, context)
    observation_copy = _save(workspace, 'evidence/materialized-task6a/' + audit['audit_sha256'] + '-observations.json',
        dict(schema_version=VERSION, observations=observations, source_authentication='NOT_ATTESTED'), context)
    corpus['task6a_provenance']['audit_ref'] = audit_copy
    new_ref = _save(workspace, 'data/processed/materialized/' + audit['audit_sha256'] + '.json', corpus, context)
    new_manifest['corpus'] = _bound(new_ref, datetime.now(timezone.utc).isoformat(),
        [t.isoformat() for t in ready.values()] + [t.isoformat() for t in code_ready.values()])
    updated_physical['corpus_sha256'] = new_ref['sha256']
    validity_ref = _save(workspace, 'features/materialized/' + audit['audit_sha256'] + '.json', updated_physical, context)
    new_manifest['row_validity'] = _bound(validity_ref, datetime.now(timezone.utc).isoformat(),
                                          [new_manifest['corpus']['usable_at']])
    stamp = datetime.now(timezone.utc).isoformat()
    final_ready = max([_time(stamp), _time(new_manifest['corpus']['usable_at']),
                      _time(new_manifest['row_validity']['usable_at']),
                      _time(new_manifest['policy']['usable_at'])]).isoformat()
    new_manifest['readiness'] = {k: final_ready for k in g0.pi.READINESS_FIELDS}
    new_manifest['usable_at'] = final_ready
    strict_ref = _save(workspace, 'protocols/development/materialized/' + audit['audit_sha256'] + '.json',
                       new_manifest, context)
    selection = training_gate.select_g0_training_rows(workspace, strict_ref, heldout_night,
        fit_cutoff, forecast_cutoff, expected_feature_definition_sha256=manifest['feature_definition_sha256'],
        budget_seconds=min(300, context.remaining_seconds), _read_context=context)
    destination = g0.G0ArtifactReader(workspace, context)
    for ref in [*reader.refs.values(), new_ref, validity_ref, strict_ref, audit_copy, observation_copy]:
        destination.read(ref, parse=False)
    destination.rescan()
    reader.rescan()
    if datetime.now(timezone.utc) >= training_gate.training_boundary(heldout_night, fit_cutoff, forecast_cutoff):
        raise training_gate.G0TrainingInputBlocked('New artifacts are not available before requested fit boundary')
    context.check()
    research_refs = [audit_copy, observation_copy]
    if components_ref is not None:
        research_refs.append(components_ref)
    return workspace, strict_ref, selection, manifest['feature_definition_sha256'], destination, research_refs


def materialize_sources(source_root, private_output, *, night, feature_corpus_ref=None,
                        strict_manifest_ref=None, heldout_night=None, fit_cutoff=None,
                        forecast_cutoff=None, budget_seconds=300, _read_context=None,
                        components_ref=None):
    budget_type = type(budget_seconds)
    if (type(night) is not str or (budget_type is not int and budget_type is not float) or
            not 0 < budget_seconds <= 300):
        raise ValueError('MATERIALIZER_PRIMITIVE_CONTEXT_REQUIRED')
    validate_night(night)
    for value in (heldout_night, fit_cutoff, forecast_cutoff):
        if value is not None and type(value) is not str:
            raise ValueError('MATERIALIZER_PRIMITIVE_CONTEXT_REQUIRED')
    if fit_cutoff is not None:
        _time(fit_cutoff)
    if forecast_cutoff is not None:
        _time(forecast_cutoff)
    if _read_context is not None:
        if type(_read_context) is not ProspectiveReadContext:
            raise ValueError('MATERIALIZER_NATIVE_READ_CONTEXT_REQUIRED')
        state = vars(_read_context)
        if (any(type(k) is not str for k in state) or
                set(state) != {'deadline', 'max_bytes', 'bytes_read'} or
                type(state['deadline']) is not float or not math.isfinite(state['deadline']) or
                type(state['max_bytes']) is not int or state['max_bytes'] <= 0 or
                type(state['bytes_read']) is not int or state['bytes_read'] < 0):
            raise ValueError('MATERIALIZER_NATIVE_READ_CONTEXT_REQUIRED')
        _read_context.restrict(budget_seconds, MAX_ACTUAL_BYTES)
    context = _read_context if _read_context is not None else ProspectiveReadContext(budget_seconds, MAX_ACTUAL_BYTES)
    root = local_path(Path(source_root).absolute(), '')
    output = _private_output(root, Path(private_output))
    if components_ref is not None and (feature_corpus_ref is not None or strict_manifest_ref is not None):
        raise ValueError('MATERIALIZER_COMPONENT_MODE_CONFLICT')
    components_ref = None if components_ref is None else _owned_ref(components_ref, 'manifest')
    if components_ref is not None:
        root = _private_output(ROOT, root)
        if None in (heldout_night, fit_cutoff, forecast_cutoff):
            raise ValueError('MATERIALIZER_FUTURE_FIT_CONTEXT_REQUIRED')
        validate_night(heldout_night)
        _component_time(fit_cutoff)
        _component_time(forecast_cutoff)
    feature_corpus_ref = None if feature_corpus_ref is None else _owned_ref(feature_corpus_ref, 'corpus')
    strict_manifest_ref = None if strict_manifest_ref is None else _owned_ref(strict_manifest_ref, 'manifest')
    now = datetime.now(timezone.utc).isoformat()
    reader = g0.G0ArtifactReader(root, context)
    audit = ea.audit_evidence(root, night, verified_at=now,
        budget_seconds=min(float(budget_seconds), context.remaining_seconds), _read_context=context)
    context.check()
    body = {k: v for k, v in audit.items() if k != 'audit_sha256'}
    if audit.get('implementation_version') != ea.VERSION or digest(body) != audit.get('audit_sha256'):
        raise ValueError('MATERIALIZER_NATIVE_AUDIT_SEAL')
    for path, expected in audit['input_hashes'].items():
        context.check()
        actual = local_path(root, path)
        reader.read(dict(path=path, sha256=expected, size_bytes=actual.stat().st_size), parse=False)
    observations = _observations(root, audit, reader, context)
    reasons = []
    if audit['status'] in {'FAIL', 'BLOCKED'}:
        reasons.append('NATIVE_AUDIT_NOT_ACCEPTED')
    if components_ref is None and feature_corpus_ref is None:
        reasons.append('FEATURE_CORPUS_NOT_SUPPLIED')
    if components_ref is None and strict_manifest_ref is None:
        reasons.append('STRICT_G0_COMPONENTS_NOT_SUPPLIED')
    receipt = dict(schema_version=VERSION, status='BLOCKED', reason_codes=reasons,
        source_authentication='NOT_ATTESTED', scientific_status='NOT_VALIDATED',
        scientific_fit_authorized=False, production_authorized=False,
        official_issuance_authorized=False, new_real_fits=0, new_real_models=0,
        new_negative_rows=0, eligible_training_units=None, manifest_ref=None,
        counts=dict(observation_units=len(observations),
                    canonical_source_events=sum(len(r['capture_event_ids']) for r in observations),
                    recorded_quantity=sum(r['recorded_quantity'] or 0 for r in observations),
                    unknown_units=sum(r['label'] is None for r in observations)),
        checked_at=now, audit_sha256=audit['audit_sha256'])
    prefix = 'runs/' + digest(dict(audit=audit['audit_sha256'], checked_at=now))
    selection = None
    destination = None
    research_refs = None
    workspace = output
    if not reasons:
        output.mkdir(parents=True, exist_ok=True)
        try:
            workspace, strict_ref, selection, definition_sha, destination, research_refs = _complete(root, output, prefix,
                audit, observations, reader, context, feature_corpus_ref, strict_manifest_ref,
                heldout_night, fit_cutoff, forecast_cutoff, components_ref=components_ref)
        except training_gate.G0TrainingInputBlocked:
            context.check()
            receipt['reason_codes'].append('G0_INPUTS_NOT_READY_OR_CAPABILITY_BLOCKED')
        else:
            receipt.update(status='DECLARATION_MATERIALIZED', manifest_ref=strict_ref,
                feature_definition_sha256=definition_sha,
                declared_training_units=selection['selection']['counts']['accepted_rows'],
                declared_selection_status=selection['selection']['status'],
                training_selection_sha256=selection['selection']['selection_sha256'],
                new_negative_rows=selection['selection']['counts']['negatives'])
    receipt['counts']['unknown_units'] = sum(r['label'] is None for r in observations)
    reader.rescan()
    context.check()
    output.mkdir(parents=True, exist_ok=True)
    receipt['audit_ref'] = _save(output, prefix + '/audit.json', audit, context)
    receipt['observations_ref'] = _save(output, prefix + '/observations.json',
        dict(schema_version=VERSION, observations=observations, source_authentication='NOT_ATTESTED'), context)
    receipt['research_refs'] = research_refs if research_refs is not None else [receipt['audit_ref'], receipt['observations_ref']]
    reader.rescan()
    if destination is not None:
        destination.rescan()
    diagnostic_outputs = g0.G0ArtifactReader(output, context)
    diagnostic_outputs.read(receipt['audit_ref'], parse=False)
    diagnostic_outputs.read(receipt['observations_ref'], parse=False)
    diagnostic_outputs.rescan()
    context.check()
    receipt['actual_read_bytes_before_completion_read'] = context.bytes_read
    receipt['receipt_sha256'] = digest(receipt)
    owned = []
    try:
        receipt_ref = _save(output, prefix + '/receipt.json', receipt, context, _created=owned)
        # Fencing includes every original, copied dependency and generated output
        # after all writes. A failure revokes our newly written completion only.
        reader.rescan()
        if destination is not None:
            destination.rescan()
        diagnostic_outputs.read(receipt_ref, parse=False)
        diagnostic_outputs.rescan()
        context.check()
    except BaseException:
        _discard_owned(output, owned)
        raise
    return dict(receipt=receipt, receipt_ref=receipt_ref, observations=observations,
                private_workspace=str(workspace), selector_result=selection,
                execution=dict(actual_read_bytes=context.bytes_read,
                               after_completion_read_bytes=context.bytes_read - receipt['actual_read_bytes_before_completion_read'] - receipt_ref['size_bytes'],
                               scope='INCLUDES_FINAL_COMPLETION_READ'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--night', required=True)
    parser.add_argument('--budget-seconds', type=float, default=300)
    parser.add_argument('--feature-corpus-ref')
    parser.add_argument('--strict-manifest-ref')
    parser.add_argument('--components-ref', help='Bound private label-free G0 component packet')
    parser.add_argument('--heldout-night')
    parser.add_argument('--fit-cutoff')
    parser.add_argument('--forecast-cutoff')
    args = parser.parse_args()
    try:
        result = materialize_sources(args.root, args.output, night=args.night,
            budget_seconds=args.budget_seconds,
            feature_corpus_ref=None if args.feature_corpus_ref is None else _reference_json(args.feature_corpus_ref),
            strict_manifest_ref=None if args.strict_manifest_ref is None else _reference_json(args.strict_manifest_ref),
            components_ref=None if args.components_ref is None else _reference_json(args.components_ref),
            heldout_night=args.heldout_night, fit_cutoff=args.fit_cutoff,
            forecast_cutoff=args.forecast_cutoff)['receipt']
        print(json.dumps({k: result[k] for k in ('status', 'reason_codes', 'counts', 'new_real_fits')}))
        return 2 if result['status'] == 'BLOCKED' else 0
    except (TimeoutError, InputCapacityError):
        print(json.dumps(dict(status='BLOCKED', reason_codes=['RUNTIME_OR_CAPACITY_BLOCKED'])))
        return 2
    except (ValueError, OSError, KeyError, TypeError):
        print(json.dumps(dict(status='FAIL', reason_codes=['INVALID_SOURCE_OR_COMPONENTS'])))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
