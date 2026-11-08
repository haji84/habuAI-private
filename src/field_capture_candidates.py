"""Byte-bound PRIVATE adapter for native habu-field-session-v1 exports.

build_field_capture_candidates(raw_bytes, *, source_sha256, budget_seconds=30)
does no I/O. Source hashes establish byte consistency, not owner identity or
scientific qualification. No IDs for animals, search proofs, or outcomes are
invented. Original event IDs and array indices are retained.

An event's native `time` is its recorded clock. Optional `observation` has
exactly observed_at (aware ISO, <=6 fractional digits, minute timezone offset)
and uncertainty_seconds (finite number 0..31536000). Its nominal instant must
lie between session start and recorded time. These remain owner declarations,
not sensor-certified event times. Without it, timing uncertainty stays null.
Legacy recorded clocks may precede session start by at most 60 seconds;
this recording grace never extends the observation declaration's bounds.

All candidate coordinates remain null: the native separately timed device fix
does not establish the animal's observed location. Original fix metadata and
recorded clock are preserved privately in source_metadata, not discarded or
replaced by the observation declaration. This adapter cannot qualify TRAIN/P0.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import math
import re
import time

MAX_BYTES = 20_000_000  # Also the existing route parser's byte bound.
MAX_EVENTS = 10_000
MAX_POINTS = 100_000
MAX_NODES = 500_000
MAX_DEPTH = 32
_SHA = re.compile(r'[0-9a-f]{64}\Z')
_TIME = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})\Z')


def _fail(code='FIELD_CAPTURE_SCHEMA_INVALID'):
    raise ValueError(code)


def _text(value, limit, *, empty=False):
    if type(value) is not str or len(value) > limit or (not value and not empty):
        _fail()
    if any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        _fail()
    return value


def _stamp(value):
    _text(value, 40)
    if not _TIME.fullmatch(value):
        _fail('FIELD_CAPTURE_TIME_INVALID')
    # datetime accepts some invalid timezone spellings by normalizing them.
    if value[-1] != 'Z' and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
        _fail('FIELD_CAPTURE_TIME_INVALID')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        _fail('FIELD_CAPTURE_TIME_INVALID')


def _number(value, low, high):
    typ = type(value)
    if (typ is not int and typ is not float) or not low <= value <= high or not math.isfinite(value):
        _fail()
    return value


def _fields(value, required, optional=()):
    if type(value) is not dict or not required <= value.keys() or value.keys()-required-set(optional):
        _fail()


def _fix(value):
    _fields(value, {'time', 'lat', 'lon', 'accuracy'}, {'altitude', 'speed'})
    stamp = _stamp(value['time'])
    _number(value['lat'], -90, 90); _number(value['lon'], -180, 180)
    _number(value['accuracy'], 0, 100000)
    if 'altitude' in value:
        _number(value['altitude'], -1e12, 1e12)
    if 'speed' in value:
        _number(value['speed'], 0, 1e12)
    return stamp


def _decode(raw, check):
    # Bound structure before recursive json parsing, including strings/escapes.
    depth = 0; quoted = False; escape = False
    for i, char in enumerate(raw):
        if i % 65536 == 0:
            check()
        if quoted:
            if escape: escape = False
            elif char == 92: escape = True
            elif char == 34: quoted = False
        elif char == 34: quoted = True
        elif char in (91, 123):
            depth += 1
            if depth > MAX_DEPTH: _fail('FIELD_CAPTURE_JSON_CAPACITY')
        elif char in (93, 125): depth -= 1
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: _fail('FIELD_CAPTURE_DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def bad(_): _fail('FIELD_CAPTURE_NONFINITE_JSON')
    def integer(token):
        if len(token) > 20: _fail('FIELD_CAPTURE_INTEGER_CAPACITY')
        return int(token)
    try:
        result = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                            parse_constant=bad, parse_int=integer)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        _fail('FIELD_CAPTURE_JSON_INVALID')
    pending = [result]; count = 0
    while pending:
        check(); item = pending.pop(); count += 1
        if count > MAX_NODES: _fail('FIELD_CAPTURE_JSON_CAPACITY')
        if type(item) is dict: pending.extend(item.values())
        elif type(item) is list: pending.extend(item)
        elif type(item) is float and not math.isfinite(item): bad(None)
    check()
    return result


def build_field_capture_candidates(raw_bytes, *, source_sha256, budget_seconds=30):
    """Return native candidate rows and separate lossless source-event metadata."""
    typ = type(budget_seconds)
    if ((typ is not int and typ is not float) or not 0 < budget_seconds <= 30
            or not math.isfinite(budget_seconds)):
        _fail('FIELD_CAPTURE_BUDGET_INVALID')
    deadline = time.monotonic() + budget_seconds
    def check():
        if time.monotonic() >= deadline: _fail('FIELD_CAPTURE_DEADLINE')
    if type(raw_bytes) is not bytes or not 0 < len(raw_bytes) <= MAX_BYTES:
        _fail('FIELD_CAPTURE_BYTE_CAPACITY')
    if type(source_sha256) is not str or not _SHA.fullmatch(source_sha256):
        _fail('FIELD_CAPTURE_HASH_INVALID')
    check()
    if hashlib.sha256(raw_bytes).hexdigest() != source_sha256:
        _fail('FIELD_CAPTURE_HASH_MISMATCH')
    session = _decode(raw_bytes, check)
    _fields(session, {'schema_version','id','startedAt','endedAt','status','points','events','gaps'}, {'revision','conditions'})
    if session['schema_version'] != 'habu-field-session-v1': _fail()
    if not re.fullmatch(r'[A-Za-z0-9-]{16,90}', _text(session['id'], 90)): _fail()
    start = _stamp(session['startedAt'])
    if session['status'] not in ('active', 'stopped'): _fail()
    end = None if session['endedAt'] is None else _stamp(session['endedAt'])
    if (session['status'] == 'active') != (end is None) or (end is not None and end < start): _fail()
    if 'revision' in session and (type(session['revision']) is not int or not 0 <= session['revision'] < 2**53-1): _fail()
    for key, cap in [('events',MAX_EVENTS),('points',MAX_POINTS),('gaps',MAX_POINTS)]:
        if type(session[key]) is not list or len(session[key]) > cap: _fail('FIELD_CAPTURE_ROW_CAPACITY')
    # Session v1 gained optional environment observations. These records are
    # private contextual evidence, never capture events or scientific labels.
    conditions = session.get('conditions', [])
    if type(conditions) is not list or len(conditions) > MAX_EVENTS:
        _fail('FIELD_CAPTURE_ROW_CAPACITY')
    prior = start
    source_fixes = set()
    for point in session['points']:
        check(); instant = _fix(point)
        if instant < prior or (end is not None and instant > end): _fail('FIELD_CAPTURE_POINT_CLOCK')
        source_fixes.add((point['time'], point['lat'], point['lon'], point['accuracy'],
                          point.get('altitude')))
        prior = instant
    for gap in session['gaps']:
        check(); _fields(gap, {'time','reason'}); _stamp(gap['time']); _text(gap['reason'], 80, empty=True)
    environment_values = {
        'road_surface': {'dry', 'damp', 'wet', 'puddle'},
        'weather': {'clear', 'cloudy', 'rain', 'fog'},
    }
    for observation in conditions:
        check()
        _fields(observation, {'time','category','value','source'}, {'position'})
        recorded = _stamp(observation['time'])
        if recorded < start or (end is not None and recorded > end):
            _fail('FIELD_CAPTURE_CONDITION_CLOCK')
        category = observation['category']
        if type(category) is not str:
            _fail()
        if category == 'air_temperature':
            if observation['source'] != 'thermometer':
                _fail('FIELD_CAPTURE_CONDITION_SOURCE')
            _number(observation['value'], -30, 60)
        elif category in environment_values:
            if observation['source'] != 'owner_visual' or type(observation['value']) is not str:
                _fail('FIELD_CAPTURE_CONDITION_SOURCE')
            if observation['value'] not in environment_values[category]: _fail()
        else:
            _fail('FIELD_CAPTURE_CONDITION_CATEGORY')
        position = observation.get('position')
        if position is not None:
            fix_at = _fix(position)
            if not 0 <= (recorded - fix_at).total_seconds() <= 90:
                _fail('FIELD_CAPTURE_CONDITION_FIX_CLOCK')
            key = (position['time'], position['lat'], position['lon'],
                   position['accuracy'], position.get('altitude'))
            if key not in source_fixes:
                _fail('FIELD_CAPTURE_CONDITION_FIX_NOT_IN_SOURCE')
    events = []; metadata = []; seen = set()
    for index, event in enumerate(session['events']):
        check()
        _fields(event, {'id','type','species','count','time','owner'}, {'note','position','observation'})
        ident = _text(event['id'],256)
        if len(ident) < 16 or ident in seen: _fail('FIELD_CAPTURE_IDENTITY_CONFLICT')
        seen.add(ident)
        recorded = _stamp(event['time'])
        if (recorded < start and ('observation' in event or (start-recorded).total_seconds() > 60)) or (end is not None and recorded > end):
            _fail('FIELD_CAPTURE_EVENT_CLOCK')
        species = _text(event['species'],80)
        if species != species.strip(): _fail()
        if 'note' in event:
            # Native notes can contain newlines; keep the original in private metadata.
            note=event['note']
            if type(note) is not str or len(note)>300 or any(0xD800<=ord(c)<=0xDFFF for c in note): _fail()
        if type(event['count']) is not int or not 1 <= event['count'] <= 100: _fail()
        if event['owner'] not in ('self','other'): _fail()
        if event['type'] not in ('capture','sighting','roadkill','other'): _fail()
        fix = event.get('position')
        if fix is not None:
            fix_time = _fix(fix)
            if abs((recorded-fix_time).total_seconds()) > 90: _fail('FIELD_CAPTURE_FIX_CLOCK')
        clock=event['time']; semantics='RECORDED_AT'; uncertainty=None
        observation=event.get('observation')
        if 'observation' in event:
            _fields(observation, {'observed_at','uncertainty_seconds'})
            instant=_stamp(observation['observed_at'])
            if not start <= instant <= recorded: _fail('FIELD_CAPTURE_OBSERVATION_CLOCK')
            uncertainty=_number(observation['uncertainty_seconds'],0,31536000)
            clock=observation['observed_at'];semantics='OBSERVED_AT'
        events.append(dict(event_id=ident, individual_ids=[], source_sha256=source_sha256,
            recorded_at=clock,time_semantics=semantics,uncertainty_seconds=uncertainty,
            latitude=None,longitude=None,owner_role='OWNER' if event['owner']=='self' else 'OTHER',
            species={'ハブ':'HABU','ヒメハブ':'HIMEHABU'}.get(species,'UNKNOWN'),
            event_type={'capture':'CAPTURE','sighting':'SIGHTING','roadkill':'ROADKILL','other':'UNKNOWN'}[event['type']],
            count=event['count'],source_reference=f'field_session_sha256={source_sha256};event_index={index}'))
        metadata.append(dict(event_id=ident,event_index=index,source_sha256=source_sha256,
            session_id=session['id'],recorded_at=event['time'],observation=observation,
            gps_fix=fix,source_event=event,location_semantics='DEVICE_FIX_NOT_OBSERVED_ANIMAL_LOCATION',
            observation_semantics='OWNER_DECLARATION_NOT_INDEPENDENT_MEASUREMENT' if observation is not None else 'NOT_SUPPLIED'))
    check()
    return dict(schema_version='habu-capture-event-candidates-v1',source_sha256=source_sha256,
                events=events,source_metadata=metadata,source_authentication='NOT_ATTESTED',
                formal_positive_qualified=False,formal_negative_qualified=False,
                production_authorized=False,model_updated=False)
