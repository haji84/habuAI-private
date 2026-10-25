"""Replayable engineering accounting proposals; no authenticated job execution."""
from datetime import timedelta

from master_contracts import canonical_bytes, digest, validate_night
from development_handoff import (DEVELOPMENT_CAPABILITY, DEVELOPMENT_FLAGS,
    _fields, _hash, _integer, _own, _time, inspect_development_request)

VERSION = 'habu-development-job-ledger-proposal-v1'
ORIGIN_VERSION = 'habu-development-job-origin-v1'
PERSISTENCE = 'UNPUBLISHED_ACCOUNTING_PROPOSAL'
RUNTIME = 'CALLER_DECLARED_NOT_ATTESTED'
MAX_EVENTS = 32
MAX_REPORTED_MS = 86400000
LIMITS = dict(attempts=2, active_ms_per_attempt=3600000, active_ms_total=7200000, lease_seconds=600)
FLAGS = dict(DEVELOPMENT_FLAGS)
TOP = {'schema_version','persistence','runtime_accounting','origin','events','tip_sha256',*FLAGS}
ORIGIN_FIELDS = {'schema_version','master_issue','repository','root_command_id','capability_id',
                 'job_id','anchor_night','limits'}
COMMANDS = dict(START={'kind','request','now','lease_until'},
    CHECKPOINT={'kind','attempt_id','generation','active_ms','phase','now','lease_until'},
    SETTLE={'kind','attempt_id','generation','active_ms','now'},
    EXPIRE={'kind','attempt_id','generation','now'})
DERIVED = dict(START={'attempt_id','ordinal','operation_id','allowance_ms','generation'},
    CHECKPOINT={'next_generation'}, SETTLE={'next_generation','outcome'},
    EXPIRE={'next_generation','outcome'})
COMMON = {'sequence','previous_sha256','event_sha256'}


def _snapshot(value):
    try:
        return _own(value)
    except ValueError as exc:
        if 'capacity' in str(exc).lower():
            raise ValueError('CAPACITY_BLOCKED: development job snapshot') from exc
        raise


def _identity(value):
    return {key:value[key] for key in ('master_issue','repository','root_command_id','capability_id')}


def _origin_valid(origin):
    _fields(origin,ORIGIN_FIELDS)
    if (origin['schema_version'] != ORIGIN_VERSION or origin['master_issue'] != 'haji84/AI-#1642' or
            origin['repository'] != 'haji84/habuAI-private' or origin['capability_id'] != DEVELOPMENT_CAPABILITY):
        raise ValueError('Canonical fixed development job origin required')
    _hash(origin['root_command_id']); _hash(origin['job_id'])
    if type(origin['anchor_night']) is not str:
        raise ValueError('Explicit anchored storage night required')
    validate_night(origin['anchor_night'])
    if origin['job_id'] != digest(_identity(origin)) or canonical_bytes(origin['limits']) != canonical_bytes(LIMITS):
        raise ValueError('Development job identity or fixed budget mismatch')


def new_development_job(request):
    request = inspect_development_request(request)
    identity = dict(master_issue=request['provenance']['master_issue'],
        repository=request['provenance']['repository'],
        root_command_id=request['provenance']['root_command_id'], capability_id=request['capability_id'])
    origin = dict(identity,schema_version=ORIGIN_VERSION,job_id=digest(identity),
        anchor_night=request['provenance']['operational_night'],limits=dict(LIMITS))
    return dict(schema_version=VERSION,persistence=PERSISTENCE,runtime_accounting=RUNTIME,
        origin=origin,events=[],tip_sha256=digest(origin),**FLAGS)


def _totals(state):
    used = sum(attempt['charged_ms'] for attempt in state['attempts'])
    reserved = sum(attempt['allowance_ms']-attempt['charged_ms'] for attempt in state['attempts']
        if attempt['phase'] in ('ACTIVE','WAITING_CI'))
    return used,reserved


def _lease(now, until):
    expiry = _time(until)
    if not now < expiry or expiry-now > timedelta(seconds=LIMITS['lease_seconds']):
        raise ValueError('Bounded future development lease required')


def _fence(attempt, sequence, phase, lease=None):
    attempt.update(generation=sequence,phase=phase,lease_until=lease)
    attempt['generations'].append(sequence)
    if phase=='ACTIVE':
        attempt['active_generations'].append(sequence)


def _apply(command, state, origin, sequence):
    if type(command) is not dict or type(command.get('kind')) is not str or command['kind'] not in COMMANDS:
        raise ValueError('Strict development transition kind required')
    kind = command['kind']; _fields(command,COMMANDS[kind])
    now = _time(command['now'])
    if state['last_time'] is not None and now < _time(state['last_time']):
        raise ValueError('Development accounting clock reversed')
    used,reserved = _totals(state)
    if kind == 'START':
        request = inspect_development_request(command['request'])
        identity = dict(request['provenance'],capability_id=request['capability_id'])
        if _identity(identity) != _identity(origin):
            raise ValueError('Same root/capability budget required across requests')
        provenance = request['provenance']
        if not _time(provenance['observed_at']) <= now < _time(provenance['expires_at']):
            raise ValueError('Declared development request not yet available or expired')
        if (state['budget_exceeded'] or len(state['attempts']) >= LIMITS['attempts'] or
                any(a['phase'] in ('ACTIVE','WAITING_CI') for a in state['attempts'])):
            raise ValueError('Development job exhausted or already has an open attempt')
        _lease(now,command['lease_until'])
        allowance = min(LIMITS['active_ms_per_attempt'],LIMITS['active_ms_total']-used-reserved)
        if allowance <= 0:
            raise ValueError('Development active allowance exhausted')
        ordinal = len(state['attempts'])+1
        attempt_id = digest(dict(job_id=origin['job_id'],ordinal=ordinal))
        operation_id = digest(dict(job_id=origin['job_id'],strategy_id=request['strategy_id']))
        state['attempts'].append(dict(attempt_id=attempt_id,ordinal=ordinal,operation_id=operation_id,
            request_sha256=request['request_sha256'],source_commit=request['provenance']['source_commit'],
            strategy_id=request['strategy_id'],allowance_ms=allowance,charged_ms=0,reported_ms=0,
            generation=sequence,generations=[sequence],active_generations=[sequence],
            phase='ACTIVE',lease_until=command['lease_until']))
        payload = dict(command,attempt_id=attempt_id,ordinal=ordinal,operation_id=operation_id,
            allowance_ms=allowance,generation=sequence)
    else:
        _hash(command['attempt_id']); _integer(command['generation'],1,MAX_EVENTS)
        attempt = next((a for a in state['attempts'] if a['attempt_id']==command['attempt_id']),None)
        if attempt is None or command['generation'] not in attempt['generations']:
            raise ValueError('Unknown immutable development attempt/generation')
        active = command.get('active_ms')
        if kind in ('CHECKPOINT','SETTLE'):
            if type(active) is not int or active < 0:
                raise ValueError('Exact nonnegative active milliseconds required')
            if active > MAX_REPORTED_MS:
                raise ValueError('CAPACITY_BLOCKED: unreconciled active report exceeds metadata bound')
        projected = used-attempt['charged_ms']+active if kind=='SETTLE' else used
        overrun = kind=='SETTLE' and (active > attempt['allowance_ms'] or projected > LIMITS['active_ms_total'])
        if overrun:
            if command['generation'] not in attempt['active_generations']:
                raise ValueError('Fence-only generation cannot report additional active work')
            if active <= attempt['reported_ms']:
                raise ValueError('Overrun accounting must add a new actual report')
            attempt['reported_ms'] = active
            attempt['charged_ms'] = max(attempt['charged_ms'],active)
            for other in state['attempts']:
                if other is not attempt and other['phase'] in ('ACTIVE','WAITING_CI'):
                    if other['phase']=='ACTIVE':
                        other['charged_ms'] = max(other['charged_ms'],other['allowance_ms'])
                    _fence(other,sequence,'BLOCKED_OVER_BUDGET')
            _fence(attempt,sequence,'OVER_BUDGET')
            state['budget_exceeded'] = True
            payload = dict(command,next_generation=sequence,outcome='OVER_BUDGET')
        else:
            if (state['budget_exceeded'] or command['generation'] != attempt['generation'] or
                    attempt['phase'] not in ('ACTIVE','WAITING_CI')):
                raise ValueError('Stale/closed development worker cannot complete or renew')
            waiting = attempt['phase']=='WAITING_CI'
            if kind=='EXPIRE':
                if waiting or now < _time(attempt['lease_until']):
                    raise ValueError('Only an expired ACTIVE lease may be conservatively charged')
                attempt['charged_ms'] = attempt['allowance_ms']
                _fence(attempt,sequence,'EXPIRED')
                payload = dict(command,next_generation=sequence,outcome='EXPIRED')
            else:
                if not waiting and now >= _time(attempt['lease_until']):
                    raise ValueError('Expired development lease fenced normal completion')
                if active < attempt['reported_ms'] or active > attempt['allowance_ms']:
                    raise ValueError('Nondecreasing active report within allowance required')
                if waiting and active != attempt['reported_ms']:
                    raise ValueError('CI wait cannot add implementation active time')
                if kind=='CHECKPOINT':
                    if command['phase'] not in ('ACTIVE','WAITING_CI'):
                        raise ValueError('Exact development phase required')
                    if command['phase']=='ACTIVE':
                        _lease(now,command['lease_until'])
                    elif command['lease_until'] is not None or waiting:
                        raise ValueError('Pause must fence ACTIVE worker without a CI lease')
                    _fence(attempt,sequence,command['phase'],command['lease_until'])
                    payload = dict(command,next_generation=sequence)
                else:
                    _fence(attempt,sequence,'SETTLED')
                    payload = dict(command,next_generation=sequence,outcome='SETTLED')
                attempt.update(charged_ms=active,reported_ms=active)
    state['last_time'] = command['now']
    used,reserved = _totals(state)
    if not state['budget_exceeded'] and used+reserved > LIMITS['active_ms_total']:
        raise ValueError('Development job active budget exceeded')
    return payload


def _validated(ledger):
    ledger = _snapshot(ledger); _fields(ledger,TOP)
    if (ledger['schema_version'] != VERSION or ledger['persistence'] != PERSISTENCE or
            ledger['runtime_accounting'] != RUNTIME or any(ledger[k] is not False for k in FLAGS)):
        raise ValueError('Unauthenticated accounting proposal contract required')
    origin = ledger['origin']; _origin_valid(origin)
    events = ledger['events']
    if type(events) is not list or len(events)>MAX_EVENTS:
        raise ValueError('CAPACITY_BLOCKED: bounded development event history required')
    state = dict(attempts=[],last_time=None,budget_exceeded=False)
    previous = digest(origin)
    for sequence,event in enumerate(events,1):
        if type(event) is not dict or type(event.get('kind')) is not str or event['kind'] not in COMMANDS:
            raise ValueError('Malformed development accounting event')
        kind = event['kind']; _fields(event,COMMANDS[kind]|DERIVED[kind]|COMMON)
        if type(event['sequence']) is not int or event['sequence']!=sequence or event['previous_sha256']!=previous:
            raise ValueError('Development event sequence/previous hash mismatch')
        command = {k:event[k] for k in COMMANDS[kind]}
        expected = dict(_apply(command,state,origin,sequence),sequence=sequence,previous_sha256=previous)
        expected['event_sha256'] = digest(expected)
        if canonical_bytes(expected) != canonical_bytes(event):
            raise ValueError('Development semantic event/hash mismatch')
        previous = event['event_sha256']
    if _hash(ledger['tip_sha256']) != previous:
        raise ValueError('Development job tip mismatch')
    return ledger,state


def inspect_development_job(ledger):
    ledger,state = _validated(ledger)
    used,reserved = _totals(state)
    return _snapshot(dict(job_id=ledger['origin']['job_id'],attempts=state['attempts'],
        used_ms=used,reserved_ms=reserved,
        remaining_ms=0 if state['budget_exceeded'] else LIMITS['active_ms_total']-used-reserved,
        budget_exceeded=state['budget_exceeded'],last_time=state['last_time'],runtime_accounting=RUNTIME,**FLAGS))


def append_development_job(ledger, *, expected_tip, transition):
    ledger,transition = _snapshot([ledger,transition])
    ledger,state = _validated(ledger)
    if _hash(expected_tip)!=ledger['tip_sha256']:
        raise ValueError('Stale development accounting tip')
    if type(transition) is dict and transition.get('kind')=='SETTLE':
        for prior in ledger['events']:
            if prior['kind']=='SETTLE' and canonical_bytes({k:prior[k] for k in COMMANDS['SETTLE']})==canonical_bytes(transition):
                return ledger
    if len(ledger['events'])>=MAX_EVENTS:
        raise ValueError('CAPACITY_BLOCKED: development event history exhausted')
    sequence = len(ledger['events'])+1
    event = dict(_apply(transition,state,ledger['origin'],sequence),
        sequence=sequence,previous_sha256=ledger['tip_sha256'])
    event['event_sha256'] = digest(event)
    ledger['events'].append(event); ledger['tip_sha256'] = event['event_sha256']
    return _validated(ledger)[0]
