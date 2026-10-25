"""Science accounting proposals and fixed report-only persistence.

This is not the authenticated controller or a durable CAS publisher. The caller
must bind one authorized origin per root command and publish one direct-parent
transition atomically before execution. Saved JSON is declared consistency only.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import re

from master_contracts import canonical_bytes, digest, validate_night

# Additive implementation-completeness declarations. These do not create jobs.
DEVELOPMENT_REQUEST_VERSION = 'habu-development-request-proposal-v1'
DEVELOPMENT_DECISION_VERSION = 'habu-development-request-decision-v1'
DEVELOPMENT_CAPABILITY = 'CONFIGURED_STAGE1_PARENT_DISPATCH_V2'
DEVELOPMENT_STRATEGY = 'REUSE_SOURCE_STAGE1_V2'
DEVELOPMENT_SCOPE_VERSION = 'habu-development-capability-map-v1'
DEVELOPMENT_FLAGS = dict(request_admitted=False, execution_authorized=False,
    scientific_authorized=False, selection_authorized=False, production_authorized=False,
    github_facts_authenticated=False)
DEVELOPMENT_PROVENANCE_FIELDS = {'master_issue', 'repository', 'root_command_id',
    'parent_command_id', 'parent_run_id', 'operational_night', 'source_commit',
    'protocol_sha256', 'observed_at', 'expires_at', 'evidence'}
DEVELOPMENT_NEED_FIELDS = {'kind', 'capability_id', 'capability_installed',
    'prerequisite_schema', 'prerequisite_deployed'}

VERSION = 'habu-science-root-ledger-proposal-v1'
LIMIT_MS = 300_000
MAX_ROUNDS = 2
MAX_ATTEMPTS_PER_OPERATION = 2
MAX_LEASE_SECONDS = 600
MAX_EVENTS = 32
MAX_BYTES = 1024 * 1024
MAX_NODES = 10_000
FLAGS = dict(execution_authorized=False, scientific_authorized=False,
             selection_authorized=False, production_authorized=False)
TOP_FIELDS = {'schema_version', 'persistence', 'origin', 'events', 'tip_sha256', *FLAGS}
ORIGIN_FIELDS = {'master_issue', 'repository', 'root_command_id', 'operational_night',
                 'preregistered_recipes', 'limits'}
COMMON_EVENT = {'kind', 'sequence', 'previous_sha256', 'event_sha256', 'generation', 'attempt_id', 'now'}
RESERVE_FIELDS = COMMON_EVENT | {'operation_id', 'child_command_id', 'source_commit', 'round_id',
                                 'recipes', 'milliseconds', 'lease_until'}
SETTLE_FIELDS = COMMON_EVENT | {'elapsed_ms'}


def _fields(value, expected):
    if type(value) is not dict or set(value) != expected:
        raise ValueError('Exact science ledger fields required')


def _hash(value, length=64):
    if type(value) is not str or not re.fullmatch('[a-f0-9]{'+str(length)+'}', value):
        raise ValueError('Canonical lowercase content identity required')
    return value


def _integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError('Bounded exact integer milliseconds/count required')
    return value


def _time(value):
    if type(value) is not str or len(value) > 64:
        raise ValueError('Aware ledger clock required')
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if stamp.utcoffset() is None:
            raise ValueError('Aware ledger clock required')
        return stamp.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise ValueError('Aware ledger clock required') from exc


def _own(value):
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if count > MAX_NODES or depth > 12:
            raise ValueError('Science ledger capacity exceeded')
        kind = type(item)
        if kind in (dict, list):
            if count + len(pending) + len(item) > MAX_NODES:
                raise ValueError('Science ledger capacity exceeded')
            if kind is dict and any(type(key) is not str or len(key) > 128 for key in item):
                raise ValueError('Bounded ledger string keys required')
            pending.extend((child, depth + 1) for child in (item.values() if kind is dict else item))
        elif kind is str:
            if len(item) > 1024:
                raise ValueError('Science ledger string capacity exceeded')
        elif kind is int:
            if item.bit_length() > 64:
                raise ValueError('Science ledger integer capacity exceeded')
        elif kind not in (bool, type(None)):
            raise ValueError('Integer/string JSON-only science ledger required')
    raw = bytearray()
    encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    for chunk in encoder.iterencode(value):
        encoded = chunk.encode('utf-8')
        if len(raw) + len(encoded) > MAX_BYTES:
            raise ValueError('Science ledger byte capacity exceeded')
        raw.extend(encoded)
    return json.loads(raw)


def _development_inputs(provenance, need):
    provenance, need = _own([provenance, need])
    _fields(provenance, DEVELOPMENT_PROVENANCE_FIELDS)
    _fields(need, DEVELOPMENT_NEED_FIELDS)
    if (provenance['master_issue'] != 'haji84/AI-#1642' or
            provenance['repository'] != 'haji84/habuAI-private'):
        raise ValueError('Canonical development master/repository required')
    for field in ('root_command_id', 'parent_command_id', 'parent_run_id', 'protocol_sha256'):
        _hash(provenance[field])
    _hash(provenance['source_commit'], 40)
    if type(provenance['operational_night']) is not str:
        raise ValueError('Explicit operational night required')
    validate_night(provenance['operational_night'])
    observed, expires = _time(provenance['observed_at']), _time(provenance['expires_at'])
    if not observed < expires or expires - observed > timedelta(hours=24):
        raise ValueError('Declared request expiry must be within24h after observation')
    refs = provenance['evidence']
    if type(refs) is not list or not 1 <= len(refs) <= 16:
        raise ValueError('Bounded nonempty parent evidence refs required')
    prefix = f"reports/pdca/{provenance['operational_night']}/runs/{provenance['parent_run_id']}/"
    seen, total = set(), 0
    for ref in refs:
        _fields(ref, {'path', 'sha256', 'size_bytes'})
        path = ref['path']
        if (type(path) is not str or len(path) > 512 or
                not re.fullmatch(r'[a-zA-Z0-9_./-]+\.json', path) or
                not path.startswith(prefix) or
                any(part in ('', '.', '..') for part in path.split('/')) or
                any(word in path.lower() for word in ('original', 'sealed', 'confirmation', 'labels')) or
                path in seen):
            raise ValueError('Canonical unique nonlabel parent-run JSON evidence path required')
        _hash(ref['sha256'])
        _integer(ref['size_bytes'], 1, 262144)
        total += ref['size_bytes']
        if total > 1048576:
            raise ValueError('Declared evidence aggregate byte limit exceeded')
        seen.add(path)
    if (type(need['kind']) is not str or need['kind'] not in
            ('CODE_CAPABILITY', 'DATA_REQUIREMENT', 'UNMAPPED')):
        raise ValueError('Typed development need kind required')
    if type(need['capability_id']) is not str or not 1 <= len(need['capability_id']) <= 128:
        raise ValueError('Bounded capability identifier required')
    for field in ('capability_installed', 'prerequisite_deployed'):
        if type(need[field]) is not bool:
            raise ValueError('Exact declared capability boolean required')
    schema = need['prerequisite_schema']
    if schema is not None and (type(schema) is not str or not 1 <= len(schema) <= 128):
        raise ValueError('Nullable bounded prerequisite schema required')
    if schema is None and need['prerequisite_deployed']:
        raise ValueError('Deployed prerequisite contradicts absent schema declaration')
    return provenance, need


def propose_development_request(provenance, need):
    """Propose fixed scope from declarations; never authenticate or admit a job."""
    provenance, need = _development_inputs(provenance, need)
    result = dict(schema_version=DEVELOPMENT_DECISION_VERSION, request=None,
        source_authenticity='NOT_ATTESTED', provenance_sha256=digest(provenance),
        need_sha256=digest(need), **DEVELOPMENT_FLAGS)
    if need['kind'] == 'DATA_REQUIREMENT':
        status = 'DATA_REQUIREMENT'
    elif need['kind'] == 'UNMAPPED' or need['capability_id'] != DEVELOPMENT_CAPABILITY:
        status = 'UNMAPPED_REQUIREMENT'
    elif need['capability_installed']:
        status = 'ALREADY_IMPLEMENTED'
    elif need['prerequisite_schema'] != 'habu-stage1-source-contract-v2' or not need['prerequisite_deployed']:
        status = 'PREREQUISITE_REQUIRED'
    else:
        status = 'DECLARED_SCOPE_PROPOSAL'
        strategy_identity = dict(master_issue=provenance['master_issue'],
            repository=provenance['repository'], root_command_id=provenance['root_command_id'],
            capability_id=DEVELOPMENT_CAPABILITY, strategy_id=DEVELOPMENT_STRATEGY)
        request = dict(schema_version=DEVELOPMENT_REQUEST_VERSION,
            persistence='UNPUBLISHED_PROPOSAL', purpose='IMPLEMENTATION_COMPLETENESS',
            scope_version=DEVELOPMENT_SCOPE_VERSION, capability_id=DEVELOPMENT_CAPABILITY,
            strategy_id=DEVELOPMENT_STRATEGY, strategy_key=digest(strategy_identity),
            provenance=provenance, need=need, requirement_ids=['R005', 'R026'],
            allowed_paths=['src/research_pdca_adapter.py', 'tests/test_research_pdca_adapter.py',
                'docs/specs/research-configured-stage1-parent-v2.md',
                'docs/reviews/research_configured_stage1_parent_v2_20261025.md'],
            verification_profile='HABU_PYTHON_EXACT_HEAD_REVIEW_V1',
            acceptance_ids=['PRESERVE_REQUEST_V1_V2_V3', 'CALL_REVIEWED_SOURCE_STAGE1_V2',
                'BIND_EXACT_CONFIGURED_THREE', 'SHARE_CONTEXT_FINAL_RESCAN',
                'KEEP_AUTHORITY_FALSE', 'INDEPENDENT_REVIEW_EXACT_HEAD_UBUNTU_FRESH_MAIN'],
            risk_class='ORDINARY_CODE_ONLY',
            limits=dict(attempts=2, active_seconds_per_attempt=3600,
                active_seconds_total=7200, lease_seconds=600),
            source_authenticity='NOT_ATTESTED', **DEVELOPMENT_FLAGS)
        request['request_sha256'] = digest(request)
        result['request'] = request
    result['status'] = status
    return result


def inspect_development_request(request):
    """Validate detached declared consistency, including every derived scope field."""
    request = _own(request)
    if type(request) is not dict or not {'provenance', 'need'} <= request.keys():
        raise ValueError('Exact declared development request required')
    expected = propose_development_request(request['provenance'], request['need'])['request']
    # Canonical bytes distinguish False/0 and True/1; Python equality cannot.
    if expected is None or canonical_bytes(request) != canonical_bytes(expected):
        raise ValueError('Development request scope/content digest mismatch')
    return request


def _recipes(value, *, initial=False):
    if type(value) is not dict or not 1 <= len(value) <= 3:
        raise ValueError('Bounded explicit preregistered recipes required')
    allowed = {'uniform', 'HB-A0', 'HB-A1', 'HB-B1'}
    if initial and (len(value) != 3 or 'uniform' not in value):
        raise ValueError('Exactly three preregistered slots including uniform required')
    if any(name not in allowed for name in value):
        raise ValueError('Unknown science candidate recipe')
    for sha in value.values():
        _hash(sha)
    return value


def new_science_ledger(root_command_id, operational_night, preregistered_recipes):
    """Propose an origin; does not authorize creating a replacement root."""
    root, night, recipes = _own([root_command_id, operational_night, preregistered_recipes])
    _hash(root)
    validate_night(night)
    _recipes(recipes, initial=True)
    origin = dict(master_issue='haji84/AI-#1642', repository='haji84/habuAI-private',
        root_command_id=root, operational_night=night, preregistered_recipes=recipes,
        limits=dict(milliseconds=LIMIT_MS, rounds=MAX_ROUNDS, attempts_per_operation=MAX_ATTEMPTS_PER_OPERATION))
    return dict(schema_version=VERSION, persistence='UNPUBLISHED_PROPOSAL', origin=origin,
                events=[], tip_sha256=digest(origin), **FLAGS)


def _apply(event, state, origin):
    kind = event['kind']
    fields = RESERVE_FIELDS if kind == 'RESERVE' else SETTLE_FIELDS if kind == 'SETTLE' else COMMON_EVENT if kind == 'EXPIRE' else set()
    _fields(event, fields)
    _integer(event['generation'], 1, MAX_EVENTS)
    _hash(event['attempt_id'])
    now = _time(event['now'])
    if state['clock'] is not None and now < state['clock']:
        raise ValueError('Ledger clock cannot move backwards')
    state['clock'] = now
    attempt = event['attempt_id']
    if kind == 'RESERVE':
        for key in ('operation_id', 'child_command_id', 'round_id'):
            _hash(event[key])
        _hash(event['source_commit'], 40)
        _recipes(event['recipes'])
        if any(origin['preregistered_recipes'].get(name) != sha for name, sha in event['recipes'].items()):
            raise ValueError('Recipe was not frozen in this root')
        milliseconds = _integer(event['milliseconds'], 1, LIMIT_MS)
        if milliseconds > LIMIT_MS - state['used_ms'] - state['reserved_ms']:
            raise ValueError('Cumulative science budget exhausted')
        lease = _time(event['lease_until'])
        try:
            limit = now + timedelta(seconds=MAX_LEASE_SECONDS)
        except OverflowError as exc:
            raise ValueError('Reservation clock exceeds supported horizon') from exc
        if not now < lease <= limit:
            raise ValueError('Reservation lease must be positive and bounded to 600 seconds')
        if event['generation'] != event['sequence'] or attempt in state['attempts']:
            raise ValueError('Duplicate attempt or invalid fencing generation')
        operation, round_id = event['operation_id'], event['round_id']
        binding = {key: event[key] for key in ('child_command_id', 'source_commit', 'round_id')}
        old = state['operations'].get(operation)
        if old is not None and old != binding:
            raise ValueError('Canonical operation child/source/round already fixed')
        if state['operation_attempts'].get(operation, 0) >= MAX_ATTEMPTS_PER_OPERATION:
            raise ValueError('Cumulative operation attempts exhausted')
        if any(item['operation_id'] == operation and item['state'] == 'RESERVED' for item in state['attempts'].values()):
            raise ValueError('Operation already has an active reservation')
        if round_id in state['rounds'] and state['rounds'][round_id] != operation:
            raise ValueError('A consumed round belongs to another operation')
        if round_id not in state['rounds'] and len(state['rounds']) >= MAX_ROUNDS:
            raise ValueError('Cumulative improvement rounds exhausted')
        state['operations'][operation] = binding
        state['operation_attempts'][operation] = state['operation_attempts'].get(operation, 0) + 1
        state['rounds'][round_id] = operation
        state['reserved_ms'] += milliseconds
        state['attempts'][attempt] = dict(event, state='RESERVED')
        return
    record = state['attempts'].get(attempt)
    if record is None or record['state'] != 'RESERVED' or event['generation'] != record['generation']:
        raise ValueError('Stale, missing or already settled reservation')
    if kind == 'SETTLE':
        if now > _time(record['lease_until']):
            raise ValueError('Expired lease cannot publish completion')
        charge = _integer(event['elapsed_ms'], 0, record['milliseconds'])
        record.update(state='SETTLED', elapsed_ms=charge)
    else:
        if now <= _time(record['lease_until']):
            raise ValueError('Only an expired lease can be conservatively charged')
        charge = record['milliseconds']
        record.update(state='EXPIRED', elapsed_ms=charge)
    state['reserved_ms'] -= record['milliseconds']
    state['used_ms'] += charge


def _validated(value):
    ledger = _own(value)
    _fields(ledger, TOP_FIELDS)
    if ledger['schema_version'] != VERSION or ledger['persistence'] != 'UNPUBLISHED_PROPOSAL' or any(ledger[key] is not False for key in FLAGS):
        raise ValueError('Pure ledger cannot grant execution or authenticated persistence')
    origin = ledger['origin']
    _fields(origin, ORIGIN_FIELDS)
    if origin['master_issue'] != 'haji84/AI-#1642' or origin['repository'] != 'haji84/habuAI-private':
        raise ValueError('Wrong root authority/repository')
    _hash(origin['root_command_id'])
    validate_night(origin['operational_night'])
    _recipes(origin['preregistered_recipes'], initial=True)
    expected_limits = dict(milliseconds=LIMIT_MS, rounds=MAX_ROUNDS, attempts_per_operation=MAX_ATTEMPTS_PER_OPERATION)
    if type(origin['limits']) is not dict or canonical_bytes(origin['limits']) != canonical_bytes(expected_limits):
        raise ValueError('Scientific limits cannot be expanded')
    events = ledger['events']
    if type(events) is not list or len(events) > MAX_EVENTS:
        raise ValueError('Bounded append-only event history required')
    state = dict(used_ms=0, reserved_ms=0, attempts={}, operations={}, operation_attempts={}, rounds={}, clock=None)
    tip = digest(origin)
    for sequence, event in enumerate(events, 1):
        if (type(event) is not dict or type(event.get('sequence')) is not int or event['sequence'] != sequence or
                event.get('previous_sha256') != tip or event.get('event_sha256') != digest({k:v for k,v in event.items() if k != 'event_sha256'})):
            raise ValueError('Altered ledger event/hash/sequence')
        _apply(event, state, origin)
        tip = event['event_sha256']
    if _hash(ledger['tip_sha256']) != tip:
        raise ValueError('Ledger tip does not match complete history')
    return ledger, state


def inspect_science_ledger(ledger):
    """Recompute accounting; no saved summary or supplied PASS is trusted."""
    value, state = _validated(ledger)
    return dict(used_ms=state['used_ms'], reserved_ms=state['reserved_ms'],
        remaining_ms=LIMIT_MS-state['used_ms']-state['reserved_ms'],
        rounds=list(state['rounds']), operations=state['operations'],
        attempts=state['attempts'], tip_sha256=value['tip_sha256'], **FLAGS)


def _append(ledger, expected_tip, event):
    value, state = _validated(ledger)
    if _hash(expected_tip) != value['tip_sha256']:
        raise ValueError('Stale expected ledger tip; reconcile before publication')
    if len(value['events']) >= MAX_EVENTS:
        raise ValueError('Ledger event capacity exceeded')
    event = _own(event)
    event.update(sequence=len(value['events'])+1, previous_sha256=value['tip_sha256'])
    event['event_sha256'] = digest(event)
    _apply(event, state, value['origin'])
    value['events'].append(event)
    value['tip_sha256'] = event['event_sha256']
    _validated(value)
    return value


def reserve_science(ledger, *, expected_tip, operation_id, child_command_id, source_commit,
                    attempt_id, round_id, recipes, milliseconds, now, lease_until):
    value, _ = _validated(ledger)
    event = dict(kind='RESERVE', generation=len(value['events'])+1, operation_id=operation_id,
        child_command_id=child_command_id, source_commit=source_commit, attempt_id=attempt_id,
        round_id=round_id, recipes=recipes, milliseconds=milliseconds, now=now, lease_until=lease_until)
    return _append(value, expected_tip, event)


def _close(ledger, *, expected_tip, attempt_id, generation, now, kind, elapsed_ms=None):
    value, state = _validated(ledger)
    if _hash(expected_tip) != value['tip_sha256']:
        raise ValueError('Stale expected ledger tip')
    _hash(attempt_id)
    _integer(generation, 1, MAX_EVENTS)
    observed = _time(now)
    if state['clock'] is not None and observed < state['clock']:
        raise ValueError('Ledger clock cannot move backwards')
    record = state['attempts'].get(attempt_id)
    target = 'SETTLED' if kind == 'SETTLE' else 'EXPIRED'
    if record is not None and record['state'] == target and record['generation'] == generation:
        if kind == 'EXPIRE' or type(elapsed_ms) is int and elapsed_ms == record['elapsed_ms']:
            return value
        raise ValueError('Conflicting repeated settlement')
    event = dict(kind=kind, attempt_id=attempt_id, generation=generation, now=now)
    if kind == 'SETTLE':
        event['elapsed_ms'] = elapsed_ms
    return _append(value, expected_tip, event)


def settle_science(ledger, *, expected_tip, attempt_id, generation, elapsed_ms, now):
    return _close(ledger, expected_tip=expected_tip, attempt_id=attempt_id, generation=generation,
                  elapsed_ms=elapsed_ms, now=now, kind='SETTLE')


def expire_science(ledger, *, expected_tip, attempt_id, generation, now):
    return _close(ledger, expected_tip=expected_tip, attempt_id=attempt_id, generation=generation,
                  now=now, kind='EXPIRE')


# Transport-only persistence. No stored record or successful write admits an
# authorized root, a live lease, a scientific execution or backend continuation.
MAX_REPORT_BLOB_BYTES = 1024 * 1024
MAX_REPORT_READ_BYTES = 16 * 1024 * 1024
MAX_REPORT_FILES = MAX_EVENTS + 2
REPORT_VERSION = 'habu-science-report-v1'


def _report_bytes(value):
    raw = canonical_bytes(value) + b'\n'
    if len(raw) > MAX_REPORT_BLOB_BYTES:
        raise ValueError('Science report blob capacity exceeded')
    return raw


def _science_publication_records(proposal, root_report_source_commit):
    """Own one proposal and reconstruct every immutable canonical prefix record."""
    proposal, _ = _validated(proposal)
    source = _hash(root_report_source_commit, 40)
    origin = proposal['origin']
    root, night = origin['root_command_id'], origin['operational_night']
    branch = 'pdca/science-' + root
    prefix = f'reports/pdca/{night}/bridge/science/{root}/'
    common = dict(schema_version=REPORT_VERSION, root_command_id=root,
        operational_night=night, root_report_source_commit=source, **FLAGS)
    zero = dict(proposal, events=[], tip_sha256=digest(origin))
    origin_record = dict(common, kind='ORIGIN', origin=origin, proposal_sha256=digest(zero))
    origin_sha = digest(origin_record)
    records = {prefix+'origin.json': _report_bytes(origin_record)}
    for index, event in enumerate(proposal['events'], 1):
        prior = dict(proposal, events=proposal['events'][:index], tip_sha256=event['event_sha256'])
        record = dict(common, kind='EVENT', origin_record_sha256=origin_sha,
            proposal_sha256=digest(prior), event=event)
        records[prefix+f"events/{index:04d}-{event['event_sha256']}.json"] = _report_bytes(record)
    records[prefix+'state.json'] = _report_bytes(dict(common, kind='STATE',
        origin_record_sha256=origin_sha, proposal_sha256=digest(proposal), proposal=proposal))
    if len(records) > MAX_REPORT_FILES or sum(map(len, records.values())) > MAX_REPORT_READ_BYTES:
        raise ValueError('Science report record capacity exceeded')
    return branch, prefix, records


def _report_tree(transport, commit, prefix):
    """Read bounded object metadata, never reconstruct source or execute reports."""
    _hash(commit, 40)
    records = transport.git('ls-tree', '-rz', '--full-tree', commit, '--', prefix).split(b'\0')
    result = {}
    for record in records:
        if not record:
            continue
        try:
            header, name = record.split(b'\t', 1)
            mode, kind, blob = header.decode('ascii').split()
            path = name.decode('utf-8')
        except (ValueError, UnicodeError) as exc:
            raise ValueError('Malformed committed science record metadata') from exc
        if mode != '100644' or kind != 'blob' or len(path) > 512 or not path.startswith(prefix) or path in result:
            raise ValueError('Science records must be unique regular nonexecutable blobs')
        _hash(blob, 40)
        if len(result) >= MAX_REPORT_FILES:
            raise ValueError('Science report path capacity exceeded')
        result[path] = blob
    return result


def _read_report_blob(transport, commit, path, blob, budget):
    import hashlib
    key = (commit, path)
    if key in budget['cache']:
        return budget['cache'][key]
    try:
        size = int(transport.git('cat-file', '-s', _hash(blob, 40)))
    except (ValueError, OverflowError) as exc:
        raise ValueError('Invalid committed blob size') from exc
    if not 0 < size <= MAX_REPORT_BLOB_BYTES or size > MAX_REPORT_READ_BYTES-budget['bytes']:
        raise ValueError('Science report blob/read capacity exceeded before materialization')
    raw = transport.read(_hash(commit, 40), path)
    budget['bytes'] += len(raw)
    if len(raw) != size:
        raise ValueError('Committed science record size discrepancy')
    budget['reads'].append(dict(commit=commit, path=path, size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    budget['cache'][key] = raw
    return raw


def _report_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate science record JSON key')
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=unique,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite science record JSON')))
        return _own(value)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError('Malformed science report JSON') from exc


def _report_view(transport, head, source, proposed_origin, budget):
    """Verify full snapshot, raw immutable records and one-event linear history."""
    source, head = _hash(source, 40), _hash(head, 40)
    root, night = proposed_origin['root_command_id'], proposed_origin['operational_night']
    prefix = f'reports/pdca/{night}/bridge/science/{root}/'
    if _report_tree(transport, source, prefix):
        raise ValueError('Root report base already contains this campaign namespace')
    transport.assert_report_tree(head, source)
    tree = _report_tree(transport, head, prefix)
    state_path = prefix+'state.json'
    if state_path not in tree:
        raise ValueError('Missing science report state; cannot bootstrap over existing branch')
    state = _report_json(_read_report_blob(transport, head, state_path, tree[state_path], budget))
    common_keys = {'schema_version', 'kind', 'root_command_id', 'operational_night',
                   'root_report_source_commit', *FLAGS}
    _fields(state, common_keys | {'origin_record_sha256', 'proposal_sha256', 'proposal'})
    proposal, _ = _validated(state['proposal'])
    if proposal['origin'] != proposed_origin:
        raise ValueError('Root science origin cannot change')
    _, _, expected = _science_publication_records(proposal, source)
    if set(tree) != set(expected):
        raise ValueError('Missing, extra or foreign science report paths')
    changed = [path.decode('utf-8') for path in transport.git('diff', '--name-only', '--no-renames',
        '-z', source, head, '--').split(b'\0') if path]
    if len(changed) != len(set(changed)) or set(changed) != set(expected):
        raise ValueError('Science report branch contains foreign source/campaign/report changes')
    for path, required in expected.items():
        raw = _read_report_blob(transport, head, path, tree[path], budget)
        if raw != required:
            raise ValueError('Science report immutable/canonical byte binding changed')
    lines = transport.git('rev-list', '--first-parent', '--reverse', '--parents', head, '^'+source).decode('ascii').splitlines()
    if len(lines) != len(proposal['events'])+1:
        raise ValueError('Science report history must contain one bootstrap and one commit per event')
    previous = source
    for index, line in enumerate(lines):
        words = line.split()
        if len(words) != 2 or words[1] != previous:
            raise ValueError('Merged, divergent or rewritten science report ancestry')
        commit = _hash(words[0], 40)
        prefix_proposal = dict(proposal, events=proposal['events'][:index],
            tip_sha256=proposal['events'][index-1]['event_sha256'] if index else digest(proposal['origin']))
        _, _, prefix_records = _science_publication_records(prefix_proposal, source)
        current_tree = _report_tree(transport, commit, prefix)
        if set(current_tree) != set(prefix_records):
            raise ValueError('Historical science report snapshot is not its exact event prefix')
        raw = _read_report_blob(transport, commit, state_path, current_tree[state_path], budget)
        if raw != prefix_records[state_path]:
            raise ValueError('Historical science report state changed or reset its budget')
        delta = transport.git('diff', '--name-status', '--no-renames', '-z', previous, commit, '--').split(b'\0')
        if delta and delta[-1] == b'':
            delta.pop()
        if len(delta) % 2:
            raise ValueError('Malformed science report commit delta')
        changes = {delta[i+1].decode('utf-8'): delta[i].decode('ascii') for i in range(0, len(delta), 2)}
        if index:
            event = proposal['events'][index-1]
            expected_changes = {state_path:'M', prefix+f"events/{index:04d}-{event['event_sha256']}.json":'A'}
        else:
            expected_changes = {state_path:'A', prefix+'origin.json':'A'}
        if changes != expected_changes:
            raise ValueError('Science report commit rewrites history or changes unrelated files')
        previous = commit
    return proposal


def _is_proposal_prefix(proposal, latest):
    return (proposal['origin'] == latest['origin'] and len(proposal['events']) <= len(latest['events']) and
        proposal['events'] == latest['events'][:len(proposal['events'])])


def _report_ack(head, latest, source, budget):
    return dict(schema_version='habu-science-report-transport-observation-v1', status='TRANSPORT_ACK_ONLY',
        observed_head=head, latest_tip=latest['tip_sha256'], latest_proposal=latest,
        root_report_source_commit=source, actual_blob_bytes_read=budget['bytes'], blob_reads=budget['reads'],
        persistence='OBSERVED_GIT_REPORT_HISTORY_NOT_AUTHENTICATED_ROOT_OR_EXECUTION',
        limitations=['NO_OWNER_ROOT_OR_SOURCE_ADMISSION', 'NO_CLOCK_OR_RUNTIME_ACCOUNTING_ATTESTATION',
            'NO_LIVE_LEASE_OR_EXECUTION_PERMISSION', 'NO_BACKEND_CONTINUATION',
            'NONFORCE_APPEND_WRITERS_NOT_SERVER_EXACT_CAS_AGAINST_EXTERNAL_REF_RESET',
            'GIT_METADATA_NETWORK_AND_SUBPROCESS_NOT_HARD_PREEMPTIBLE',
            'COMMIT_AUTHOR_TEXT_NOT_ACTIONS_OR_CONTROLLER_AUTHENTICATION'], **FLAGS)


def _publish_science_ledger(transport, proposal, *, root_report_source_commit, expected_remote_head, expected_tip):
    """Private injected-transport seam; ordinary callers use the fixed factory."""
    proposal, _ = _validated(proposal)
    source = _hash(root_report_source_commit, 40)
    _hash(expected_tip)
    if expected_remote_head is not None:
        _hash(expected_remote_head, 40)
    branch, prefix, records = _science_publication_records(proposal, source)
    budget = dict(bytes=0, reads=[], cache={})
    head = transport.head(branch)
    if head is not None:
        latest = _report_view(transport, head, source, proposal['origin'], budget)
        if _is_proposal_prefix(proposal, latest):
            allowed_tips = {proposal['tip_sha256']}
            if proposal['events']:
                allowed_tips.add(proposal['events'][-1]['previous_sha256'])
            if expected_tip not in allowed_tips:
                raise ValueError('Expected semantic predecessor does not match published proposal')
            return _report_ack(head, latest, source, budget)
        if expected_remote_head != head or expected_remote_head is None:
            raise ValueError('Science report predecessor conflict; reconcile actual history')
        if (expected_tip != latest['tip_sha256'] or len(proposal['events']) != len(latest['events'])+1 or
                not _is_proposal_prefix(latest, proposal)):
            raise ValueError('Science report transition must append exactly one event')
        event = proposal['events'][-1]
        files = {prefix+'state.json':records[prefix+'state.json'],
                 prefix+f"events/{event['sequence']:04d}-{event['event_sha256']}.json":records[
                     prefix+f"events/{event['sequence']:04d}-{event['event_sha256']}.json"]}
    else:
        if expected_remote_head is not None or proposal['events'] or expected_tip != proposal['tip_sha256']:
            raise ValueError('Only an empty absent campaign may bootstrap')
        if _report_tree(transport, source, prefix):
            raise ValueError('Existing campaign evidence in report base cannot be reset')
        files = records
    publication_error = None
    try:
        transport.publish(branch, source, head, files)
    except Exception as exc:
        publication_error = exc  # Could have succeeded remotely; reconcile before any retry.
    observed = transport.head(branch)
    if observed is None:
        if publication_error is not None:
            raise ValueError('Science report publication unconfirmed; no new attempt authorized') from publication_error
        raise ValueError('Science report remote head absent after publication')
    latest = _report_view(transport, observed, source, proposal['origin'], budget)
    if not _is_proposal_prefix(proposal, latest):
        raise ValueError('Science report publication diverged; no automatic retry or budget reset') from publication_error
    return _report_ack(observed, latest, source, budget)


def publish_science_ledger(root, proposal, *, root_report_source_commit, expected_remote_head, expected_tip):
    """Persist fixed report data; never authorize root admission or execution.

    The real transport is deliberately imported lazily. Its existing POSIX
    dependency is not emulated on Windows. There is no CLI/facts/remote override.
    """
    from pdca_bridge import GitTransport
    return _publish_science_ledger(GitTransport(root, 'origin'), proposal,
        root_report_source_commit=root_report_source_commit,
        expected_remote_head=expected_remote_head, expected_tip=expected_tip)
