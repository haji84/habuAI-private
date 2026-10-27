"""Closed fixed-three summary/source Stage1 diagnostics; no trusted authority.

One real context and two real Source2 admissions; immutable original child
receipts retain phase bytes. Only new local scope/admission is versioned.
"""
from __future__ import annotations
from datetime import datetime,timedelta
from pathlib import Path
import re
import codex_cycle_contract as cycle
import prospective_inputs as pi
import g0_forecast_contract as g0
import g0_full_universe_score_summary_v2 as producer
import research_candidate_config_source as old_source
import research_candidate_config_source_v2 as source2
import research_candidate_preparation_v3 as prep
import research_model_adapter as models
from evaluation import full_ledger_stage1 as pure
from evaluation import stage1_source_adapter as old

VERSION='habu-stage1-summary-source-result-v2'
SOURCE_VERSION='habu-stage1-summary-source-contract-v2'
SUMMARY_PROJECTION_VERSION='habu-g0-score-summary-projection-v2'
SUMMARY_SCORES_VERSION='habu-stage1-summary-scores-v2'
SUMMARY_PROJECTION_FIELDS=pure.SUMMARY_PROJECTION_FIELDS
SUMMARY_CONFIG_FIELDS=pure.SUMMARY_CONFIG_FIELDS
SUMMARY_SEMANTICS=pure.SUMMARY_SEMANTICS
POLICY_DIGEST=cycle.POLICY_DIGEST
AREA=pure.AREA
TOP_K=pure.TOP_K
_fields=pure._fields
_items=pure._items
_sha=pure._sha
_text=pure._text
_number=pure._number
_night=pure._night
_time=pure._time
_summary_ref=pure._summary_ref
_summary_binding=pure._summary_binding
ROLES=old.ROLES
NODE_FIELDS=old.NODE_FIELDS
COVERAGE_FIELDS=old.COVERAGE_FIELDS
_captures=old._captures
_individuals=old._individuals
local_path=old.local_path
_OWNED=object()
PHASE_FIELDS=('before_pre_admission_metadata','after_pre_admission_metadata','after_source2_load1',
 'after_post_admission_metadata','after_summary','after_compact_projection','after_stage1',
 'after_final_rescans','final_read_bytes')

class _Guard:
    __slots__=('context','first')
    def __init__(self,context):self.context=context;self.first=None
    def __call__(self):
        if self.first is not None:raise self.first
        try:self.context.check()
        except BaseException as error:
            self.first=error
            raise

def _shape_ref(ref):
    pure._summary_ref(ref)
    path=ref['path']
    # Lexical alias checks before any filesystem metadata, including absent refs.
    for part in path.split('/'):
        if (part.endswith(('.', ' ')) or re.search(r'~[0-9]+(?:\.|$)',part) or
            any(c in '<>"|?*'for c in part) or
            re.fullmatch(r'(?i:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?',part)):
            raise ValueError('Unsafe portable transport component')
    return ref

def _strong(root,ref,check):
    _shape_ref(ref);check();old._transport_ref(root,ref);check();return dict(ref)

class _Reader(g0.G0ArtifactReader):
    def __init__(self,root,context,guard):
        super().__init__(root,context);self._guard=guard
    def read(self,ref,**kwargs):
        _fields(ref,g0.REF_FIELDS);ref=dict(ref)
        _strong(self.root,ref,self._guard)
        value=super().read(ref,**kwargs)
        self._guard()
        if kwargs.get('parse',True):_bound(value,self._guard)
        return value

def _sealed(value,key,check):
    _bound(value,check)
    if value[key]!=_digest({k:v for k,v in value.items()if k!=key},check):
        raise ValueError('Original complete child receipt hash mismatch')
    check()

def _pure_site(check,function,*args,**kwargs):
    try:return function(*args,**kwargs)
    except (pure.Stage1CapacityBlocked,pure.Stage1BudgetBlocked) as error:
        first=getattr(check,'first',None)
        if first is not None:raise first
        if isinstance(error,pure.Stage1CapacityBlocked):raise pi.InputCapacityError(str(error))from error
        raise TimeoutError(str(error))from error

def _bound(value,check):return _pure_site(check,pure._summary_bound,value,check)
def _copy(value,check):return _pure_site(check,pure._summary_copy,value,check)
def _digest(value,check):return _pure_site(check,pure._digest,value,check)
_hash=_digest

def _finish(value,check):
    value=_copy(value,check)
    value=_pure_site(check,pure._finish,value,check);_bound(value,check);check();return value

def _projection_owned(value,choices,config_sha,definition_sha,recipe_sha,check):
    """Validate a declared content projection, without attesting absent files."""
    _fields(value,SUMMARY_PROJECTION_FIELDS)
    if (value['schema_version']!=SUMMARY_PROJECTION_VERSION or
            value['purpose']!='DEVELOPMENT_EVALUATION_ONLY' or value['candidate_ids']!=choices or
            _sha(value['candidate_config_sha256'])!=config_sha or
            _sha(value['feature_definition_sha256'])!=definition_sha):
        raise ValueError('Summary projection version/config/definition mismatch')
    if set(choices)!={'uniform','HB-A1','HB-A2'}:
        raise ValueError('IMPLEMENTATION_BLOCKED: summary supports uniform/A1/A2 only')
    night=value['operational_night'];_night(night)
    fit,cutoff=_time(value['fit_cutoff']),_time(value['forecast_cutoff'])
    night_start=_time(night+'T07:00:00+09:00')
    if not fit<night_start<=cutoff:
        raise ValueError('Summary fit/cutoff chronology mismatch')
    for key in ('summary_manifest_ref','forecast_manifest_ref','domain_ref'):_summary_ref(value[key])
    for key in ('summary_manifest_canonical_sha256','canonical_joined_rows_sha256','training_selection_sha256'):_sha(value[key])
    source=value['candidate_config_source'];_fields(source,SUMMARY_CONFIG_FIELDS)
    for key in ('manifest_ref','config_ref','cycle_ref','policy_ref'):_summary_ref(source[key])
    for key in ('manifest_canonical_sha256','config_sha256','cycle_canonical_sha256','code_map_sha256','policy_canonical_sha256'):_sha(source[key])
    if source['config_sha256']!=config_sha:
        raise ValueError('Summary source config identity mismatch')
    code=source['code_sha256_by_path']
    from codex_cycle_contract import MAX_REFERENCES,POLICY_PATH
    if type(code) is not dict or not code or len(code)>MAX_REFERENCES:
        raise ValueError('Bounded full summary code map required')
    for path,identity in code.items():
        check();_text(path,512);_sha(identity)
        if ('\\' in path or ':' in path or any(ord(c)<32 or ord(c)==127 for c in path) or
                any(part in ('','.','..') or part.casefold() in {'original','incoming','reports','sealed','confirmation'}
                    for part in path.split('/')) or not
                ((path.startswith(('src/','scripts/')) and path.endswith('.py')) or
                 (path.startswith('schemas/') and path.endswith('.json')) or
                 path in {'requirements-analysis.txt','requirements-osm.txt'})):
            raise ValueError('Summary runtime code path mismatch')
    if (_digest(code,check)!=source['code_map_sha256'] or source['policy_ref']['path']!=POLICY_PATH or
            source['policy_canonical_sha256']!=POLICY_DIGEST):
        raise ValueError('Summary code/policy identity mismatch')
    _summary_binding(value['fit_lineage'],'lineage_sha256',cutoff,check)
    # Reuse the original pure horizon rules, without materializing any units.
    from g0_forecast_contract import _horizon,MAX_DOMAIN_CELLS,MAX_WINDOWS,MAX_SHARDS,MAX_DOMAIN_ROWS
    try:first,last,windows=_horizon(value['horizon'],night,cutoff)
    except OverflowError as exc:raise ValueError('Summary horizon exceeds datetime range') from exc
    full=value['full_counts'];_fields(full,('cell_count','window_count','shard_count','unit_count','area_count'))
    limits=dict(cell_count=MAX_DOMAIN_CELLS,window_count=MAX_WINDOWS,shard_count=MAX_SHARDS,
                unit_count=MAX_DOMAIN_ROWS,area_count=10_000)
    if any(type(full[key]) is not int or not 0<full[key]<=limit for key,limit in limits.items()):
        raise ValueError('Summary full counts are invalid')
    if (full['window_count']!=windows or full['unit_count']!=full['cell_count']*windows or
            full['area_count']>full['cell_count']):
        raise ValueError('Summary full rectangular counts disagree')
    bindings=_items(value['model_bindings'],3);summaries=_items(value['model_summaries'],3)
    if (len(bindings)!=3 or len(summaries)!=3 or
            [b.get('candidate_id') if type(b) is dict else None for b in bindings]!=choices or
            [s.get('candidate_id') if type(s) is dict else None for s in summaries]!=choices):
        raise ValueError('Summary full ordered candidate set required')
    area_ids=None;area_unit_counts=None;models={}
    for binding,model in zip(bindings,summaries):
        check();_fields(binding,('candidate_id','artifact'))
        _summary_binding(binding['artifact'],'model_sha256',cutoff,check)
        _fields(model,('candidate_id','model_sha256','recipe_sha256','score_semantics','score_stream_sha256',
                      'unit_count','area_summaries','top10_area_ids'))
        ident=model['candidate_id'];expected_recipe=recipe_sha[ident]
        if (_sha(model['model_sha256'])!=binding['artifact']['model_sha256'] or
                model['recipe_sha256']!=expected_recipe or model['score_semantics']!=SUMMARY_SEMANTICS or
                type(model['unit_count']) is not int or model['unit_count']!=full['unit_count']):
            raise ValueError('Summary native model/recipe/score binding mismatch')
        _sha(model['score_stream_sha256'])
        areas=_items(model['area_summaries'],10_000);ids=[];total=0;means={};counts={}
        if len(areas)!=full['area_count']:raise ValueError('Incomplete summary area set')
        for area in areas:
            check();_fields(area,('area_id','unit_count','mean_native_score'))
            ident_area=area['area_id'];match=AREA.fullmatch(ident_area) if type(ident_area) is str else None
            if not match:raise ValueError('Canonical summary area required')
            ax,ay=map(int,match.groups())
            if not (100<=ax<900 and 0<=ay<10000):raise ValueError('Summary area outside UTM52N')
            number=area['unit_count'];score=_number(area['mean_native_score'])
            if type(number) is not int or number<=0 or number%windows or not 0<=score<=1:
                raise ValueError('Summary physical area count or native probability invalid')
            ids.append(ident_area);total+=number;means[ident_area]=score;counts[ident_area]=number
        if ids!=sorted(set(ids)) or total!=full['unit_count'] or area_ids is not None and ids!=area_ids:
            raise ValueError('Summary areas must cover the complete shared sorted domain')
        if area_unit_counts is not None and counts!=area_unit_counts:
            raise ValueError('All candidates must cover the same physical per-area unit counts')
        if ident=='uniform' and len(set(means.values()))!=1:raise ValueError('Uniform summary must be spatially constant')
        def rank(area):check();return (-means[area],area)
        if model['top10_area_ids']!=sorted(means,key=rank)[:TOP_K]:
            raise ValueError('Summary Top10 differs from complete native means')
        area_ids=ids;area_unit_counts=counts;models[ident]=model
    return night,area_ids,models

def _summary_projection(value,choices,config_sha,definition_sha,recipe_sha,check):
    return _pure_site(check,_projection_owned,value,choices,config_sha,definition_sha,recipe_sha,check)


def _summary_scores(value,universe,nights,choices,config_sha,definition_sha,recipe_sha,check):
    _fields(value,('schema_version','universe_sha256','candidate_config_sha256','feature_definition_sha256',
        'score_summary_projection','score_summary_projection_sha256','summary_execution_receipt_sha256','candidates'))
    if (value['schema_version']!=SUMMARY_SCORES_VERSION or _sha(value['candidate_config_sha256'])!=config_sha or
            _sha(value['feature_definition_sha256'])!=definition_sha):
        raise ValueError('Summary score header/config/definition mismatch')
    _sha(value['summary_execution_receipt_sha256'])
    body=value['score_summary_projection']
    if _sha(value['score_summary_projection_sha256'])!=_digest(body,check):
        raise ValueError('Summary stable whole projection digest mismatch')
    night,areas,models=_summary_projection(body,choices,config_sha,definition_sha,recipe_sha,check)
    if (_sha(value['universe_sha256'])!=(_digest(universe,check) if universe is not None else value['universe_sha256']) or
            nights is not None and (list(nights)!=[night] or nights[night]['area_ids']!=areas)):
        raise ValueError('Summary scores must bind exactly one complete forecast night')
    if nights is not None:
        scope=nights[night]
        if (any(_time(scope[key])!=_time(body[source]) for key,source in
                (('cutoff_time','forecast_cutoff'),)) or
                _time(scope['horizon_start'])!=_time(body['horizon']['start']) or
                _time(scope['horizon_end'])!=_time(body['horizon']['end'])):
            raise ValueError('Summary universe cutoff/horizon mismatch')
    rows=_items(value['candidates'],3)
    if len(rows)!=3 or [r.get('candidate_id') if type(r) is dict else None for r in rows]!=choices:
        raise ValueError('Exact ordered summary candidates required')
    result={}
    for row in rows:
        check();_fields(row,('candidate_id','score_semantics','model_sha256','recipe_sha256','score_stream_sha256','scores'))
        model=models[row['candidate_id']]
        for key in ('score_semantics','model_sha256','recipe_sha256','score_stream_sha256'):
            if row[key]!=model[key]:raise ValueError('Summary candidate identity differs from complete projection')
        values=row['scores']
        if type(values) is not dict or list(values)!=[night] or type(values[night]) is not dict or list(values[night])!=areas:
            raise ValueError('Summary score map must preserve the exact complete sorted areas')
        for area in model['area_summaries']:
            check()
            if _number(values[night][area['area_id']])!=area['mean_native_score']:
                raise ValueError('Summary candidate mean differs from content projection')
        result[row['candidate_id']]=row
    return result



# Source graph orchestration (unchanged numerical/CSV executors).
def _evaluate_sources(state,manifest_ref):
    root,context,reader,check=state.root,state.context,state.reader,state.guard
    config,expected,definitions=state.config,state.execution['candidate_config_sha256'],state.execution['feature_definition_sha256']
    projection=state.projection;night=projection['operational_night']
    forecast_ref=projection['forecast_manifest_ref'];joined=projection['canonical_joined_rows_sha256']
    cutoff_text=projection['forecast_cutoff'];configured=(config,expected,definitions)
    version=SOURCE_VERSION;fields=old.MANIFEST_FIELDS_V2|{'score_summary_projection_sha256'}
    _summary={'projection_sha256':state.projection_sha256}
    _shape_ref(manifest_ref)
    manifest_ref = dict(manifest_ref)
    manifest = reader.read(manifest_ref, small=True)
    pure._fields(manifest, fields)
    if (manifest['schema_version'] != version or manifest['purpose'] != 'DEVELOPMENT_EVALUATION_ONLY' or
            manifest['operational_night'] != night or
            manifest['forecast_manifest_sha256'] != forecast_ref['sha256'] or
            manifest['joined_universe_sha256'] != joined):
        raise ValueError('Stage1 manifest version/purpose/forecast identity mismatch')
    if configured is not None and (manifest['candidate_config_sha256'] != expected or
            manifest['feature_definition_sha256'] != definitions):
        raise ValueError('Stage1 manifest configured feature/config identity mismatch')
    if _summary is not None and manifest['score_summary_projection_sha256']!=_summary['projection_sha256']:
        raise ValueError('Stage1 manifest stable score-summary projection identity mismatch')
    evaluation = pi._time(manifest['evaluation_as_of'])
    cutoff = pi._time(cutoff_text)
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
        _shape_ref(node['ref'])
        _strong(root,node['ref'],check)
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
        target = pi._local_path(reader.root, node['ref']['path'], check)
        check()
        if not target.is_file():
            missing.append('FILE:' + ident)
            return
        payloads[ident] = reader.read(node['ref'], parse=node['role'] in ('scope', 'coverage'))

    # Bind the entire prior scope/horizon before opening any outcome payload,
    # regardless of adversarial node-list ordering.
    for ident in graph['topological_order']:
        if ident in scope_closure:
            read_node(ident)
    scope = payloads.get(roots.get('scope'))
    universe, scores, ledger = None, None, None
    if scope is not None:
        universe,scores=_scope_projection_v2(scope,state,check)
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

    if coverage is not None and (pi._time(coverage['horizon_start'])!=pi._time(projection['horizon']['start']) or pi._time(coverage['horizon_end'])!=pi._time(projection['horizon']['end'])):
        raise ValueError('Coverage differs from known complete summary horizon')
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
            _shape_ref(coverage[role + '_ref'])
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

    _combined(state,universe,scores,ledger)
    result=_pure(universe,scores,ledger,config,projection,check)
    source_receipt=dict(summary_manifest_ref=state.execution['source_manifest_ref'],
        score_summary_projection_sha256=state.projection_sha256,
        summary_execution_receipt_sha256=state.execution['summary_sha256'],
        forecast_manifest_ref=projection['forecast_manifest_ref'],domain_ref=projection['domain_ref'],
        candidate_config_manifest_ref=projection['candidate_config_source']['manifest_ref'],
        candidate_config_sha256=expected,feature_definition_sha256=definitions,
        training_selection_sha256=projection['training_selection_sha256'],
        model_sha256_by_id={m['candidate_id']:m['model_sha256']for m in projection['model_summaries']},
        forecast_counts=projection['full_counts'],summary_actual_read_bytes=state.execution['actual_read_bytes'],
        stage1_manifest_ref=dict(manifest_ref),evaluation_as_of=manifest['evaluation_as_of'],
        readiness=manifest['readiness'],usable_at=manifest['usable_at'],
        projection_sha256={n:_hash(v,check)if v is not None else None for n,v in (('universe',universe),('scores',scores),('ledger',ledger))},
        consumed_refs=[],consumed_sha256={},actual_read_bytes=0,transport_read_bytes=0,missing_inputs=sorted(set(missing)))
    return result,source_receipt,dict(capture_events=len(captures or {}),individuals=len(individuals or {}))


def _combined(state,*values):
    _bound([state.first,state.execution,state.projection,state.config,*values],state.guard)

def _pure(universe,scores,ledger,config,projection,check):
    expected=projection['candidate_config_sha256'];definition=projection['feature_definition_sha256']
    universe,scores,ledger,config=_copy([universe,scores,ledger,config],check)
    recipes=prep._config(config,expected,definition,check)
    choices=list(producer.CANDIDATES)
    _summary_projection(projection,choices,expected,definition,recipes,check)
    nights=_pure_site(check,pure._universe,universe,check)if universe is not None else None
    candidates=_summary_scores(scores,universe,nights,choices,expected,definition,recipes,check)if scores is not None else None
    events,incomplete=_pure_site(check,pure._ledger,ledger,nights,check)if ledger is not None else(None,True)
    if nights is None and ledger is not None:
        first,last=_time(projection['horizon']['start']),_time(projection['horizon']['end'])
        for row in ledger['complete_scopes']:
            check()
            if (row['operational_night']!=projection['operational_night'] or _time(row['horizon_start'])!=first or _time(row['horizon_end'])!=last):
                raise ValueError('Known ledger horizon differs from summary')
        for row in ledger['events']:
            check()
            if row['operational_night']!=projection['operational_night']or not first<=_time(row['datetime'])<last:
                raise ValueError('Known ledger actual time differs from summary')
    base=dict(pure._common(),schema_version='habu-full-ledger-stage1-summary-diagnostic-v2',
        candidate_ids=choices,candidate_config_sha256=expected,feature_definition_sha256=definition,
        score_identity_kind='G0_SCORE_SUMMARY_PROJECTION_V2',
        score_summary_projection_sha256=_digest(projection,check),
        summary_execution_receipt_sha256=scores['summary_execution_receipt_sha256']if scores is not None else None,
        source_authentication='NOT_ATTESTED',source_consistency='DECLARED_CONSISTENCY_ONLY',
        fit_lineage_authentication='CALLER_DEPENDENCY_REQUIRED',authorities=dict.fromkeys(pure.SUMMARY_AUTHORITIES,False),
        per_night=[],pooled={},paired_uncertainty={})
    base['limitations'].append('Framed content identities do not authenticate native predictions or prereveal execution')
    if any(v is None for v in(universe,scores,ledger)):
        result=dict(base,status='NEED_MORE_DATA',blockers=['MISSING_INPUT_PROJECTION'])
    elif not nights or incomplete:
        result=dict(base,status='NEED_MORE_DATA',blockers=['COMPLETE_MATCHING_LEDGER_SCOPE_REQUIRED'])
    else:result=_pure_site(check,pure._measure,universe,scores,ledger,nights,candidates,events,base,check,_summary_identity=True)
    if 'input_digests'not in result:
        result['input_digests']={n:_digest(v,check)if v is not None else None for n,v in(('universe',universe),('scores',scores),('ledger',ledger))}
    result['input_digests']['config']=expected
    return _finish(result,check)

def _scope_projection_v2(scope,state,check):
    projection=state.projection;night=projection['operational_night']
    _fields(scope,old.SCOPE_FIELDS)
    if (scope['schema_version']!='habu-stage1-scope-source-v1'or scope['operational_night']!=night or
        _time(scope['cutoff_time'])!=_time(projection['forecast_cutoff'])or
        _time(scope['horizon_start'])!=_time(projection['horizon']['start'])or
        _time(scope['horizon_end'])!=_time(projection['horizon']['end'])):
        raise ValueError('Scope differs from complete summary cutoff/horizon')
    universe=dict(schema_version='habu-stage1-universe-v1',nights=[dict(operational_night=night,
        scope=scope['scope'],scope_sha256=_digest(scope['scope'],check),cutoff_time=scope['cutoff_time'],
        horizon_start=scope['horizon_start'],horizon_end=scope['horizon_end'],area_ids=state.areas)])
    _pure_site(check,pure._universe,universe,check)
    x0,y0,x1,y1=scope['scope']['bbox_utm']
    for cx,cy in state.cells:
        check()
        if not(x0<=cx*100 and cx*100+100<=x1 and y0<=cy*100 and cy*100+100<=y1):
            raise ValueError('Prior scope excludes a whole forecast cell')
    candidates=[]
    for model in projection['model_summaries']:
        check();row={key:model[key]for key in('candidate_id','score_semantics','model_sha256','recipe_sha256','score_stream_sha256')}
        row['scores']={night:{a['area_id']:a['mean_native_score']for a in model['area_summaries']}};candidates.append(row)
    scores=dict(schema_version=SUMMARY_SCORES_VERSION,universe_sha256=_digest(universe,check),
        candidate_config_sha256=projection['candidate_config_sha256'],feature_definition_sha256=projection['feature_definition_sha256'],
        score_summary_projection=projection,score_summary_projection_sha256=state.projection_sha256,
        summary_execution_receipt_sha256=state.execution['summary_sha256'],candidates=candidates)
    _combined(state,universe,scores);return universe,scores

def _header(reader,ref,night,as_of,expected,definition,check):
    producer._cap(ref['size_bytes'],producer.MAX_PROFILE_BYTES,'summary profile bytes')
    profile=reader.read(ref,small=True);_fields(profile,producer.PROFILE_FIELDS)
    if(profile['schema_version']!=producer.SOURCE_VERSION or profile['kind']!='UNCONNECTED_DEVELOPMENT_SCORE_SUMMARY'or
        profile['operational_night']!=night or _sha(profile['feature_definition_sha256'])!=definition or
        _time(profile['forecast_cutoff'])>as_of):raise ValueError('Summary envelope identity mismatch')
    try:cycle.training_boundary(night,profile['fit_cutoff'],profile['forecast_cutoff'])
    except OverflowError as error:raise ValueError('Training boundary exceeds datetime range')from error
    old_source._ready(profile,check)
    # Downstream refs receive lexical checks only until Source2 admission.
    for key,purpose in(('forecast_manifest','forecast'),('candidate_config_manifest','profile')):
        producer._ref(profile[key],purpose);_shape_ref(profile[key])
    if type(profile['models'])is not list or len(profile['models'])!=3:raise ValueError('Fixed three models required')
    if [x.get('candidate_id')if type(x)is dict else None for x in profile['models']]!=list(producer.CANDIDATES):
        raise ValueError('Fixed ordered uniform/A1/A2 required')
    bindings=[]
    if profile['fit_lineage']is not None:bindings.append((profile['fit_lineage'],'lineage_sha256',producer.MAX_PROFILE_BYTES))
    for entry in profile['models']:
        _fields(entry,('candidate_id','artifact'))
        if entry['artifact']is not None:bindings.append((entry['artifact'],'model_sha256',producer.MAX_MODEL_BYTES))
    for binding,field,cap in bindings:
        _fields(binding,producer.BOUND_FIELDS|{field});_sha(binding[field]);_shape_ref(binding['ref'])
        producer._cap(binding['ref']['size_bytes'],cap,'bound model/lineage bytes');old_source._ready(binding,check)
    ref=profile['candidate_config_manifest'];_strong(reader.root,ref,check)
    producer._cap(ref['size_bytes'],source2.MAX_PROFILE_BYTES,'candidate profile bytes')
    src=reader.read(ref,small=True);_fields(src,old_source.FIELDS)
    if src['schema_version']!=source2.VERSION or src['kind']!='DEVELOPMENT_CANDIDATE_CONFIG_SOURCE'or src['feature_definition_sha256']!=definition:
        raise ValueError('Cfgv3 source header mismatch')
    _fields(src['candidate_config'],('ref','config_sha256','readiness','usable_at'));old_source._ready(src['candidate_config'],check)
    if _sha(src['candidate_config']['config_sha256'])!=expected:raise ValueError('Known source config identity mismatch')
    _fields(src['cycle'],('ref','policy','readiness','usable_at'));old_source._ready(src['cycle'],check)
    _fields(src['cycle']['policy'],('size_bytes','readiness','usable_at'));old_source._ready(src['cycle']['policy'],check)
    old_source._ready(src,check)
    cr=src['candidate_config']['ref'];old_source.input_ref(cr);_strong(reader.root,cr,check)
    producer._cap(cr['size_bytes'],source2.MAX_CONFIG_BYTES,'candidate config bytes')
    cr=src['cycle']['ref'];old_source.input_ref(cr,purpose='cycle');_strong(reader.root,cr,check)
    producer._cap(cr['size_bytes'],cycle.MAX_FILE_BYTES,'cycle bytes')
    immutable=reader.read(cr,small=True);_fields(immutable,cycle.MANIFEST_FIELDS)
    _fields(immutable['policy_ref'],('path','sha256'))
    if immutable['policy_ref']['path']!=cycle.POLICY_PATH:raise ValueError('Fixed policy required')
    policy_ref=dict(immutable['policy_ref'],size_bytes=src['cycle']['policy']['size_bytes'])
    _strong(reader.root,policy_ref,check);producer._cap(policy_ref['size_bytes'],cycle.MAX_FILE_BYTES,'policy bytes')
    code,availability=immutable['code_manifest'],src['code_availability']
    if(type(code)is not list or type(availability)is not list or not 0<len(code)<=cycle.MAX_REFERENCES or len(availability)!=len(code)):
        raise ValueError('Complete bounded code declarations required')
    bypath={}
    for item in code:
        check();_fields(item,('path','sha256'));old_source._runtime_path(item['path']);_sha(item['sha256'])
        if item['path']in bypath:raise ValueError('Duplicate code path')
        bypath[item['path']]=item['sha256']
    seen=set()
    for item in availability:
        check();_fields(item,('path','size_bytes','readiness','usable_at'));path=item['path']
        if type(path)is not str or path not in bypath or path in seen:raise ValueError('Code availability mismatch')
        seen.add(path);old_source._ready(item,check)
        ref=dict(path=path,size_bytes=item['size_bytes'],sha256=bypath[path]);_strong(reader.root,ref,check)
        producer._cap(ref['size_bytes'],cycle.MAX_FILE_BYTES,'code bytes')
    # No current model/forecast/TRAIN payload has been opened or stat'ed.
    return profile

def _forecast_header(reader,profile,check):
    bindings=[profile['forecast_manifest']]
    if profile['fit_lineage']is not None:bindings.append(profile['fit_lineage']['ref'])
    bindings.extend(b['artifact']['ref']for b in profile['models']if b['artifact']is not None)
    for ref in bindings:_strong(reader.root,ref,check)
    raw=reader.read(profile['forecast_manifest'],small=True)
    nodes,features=raw['source_nodes'],raw['features']
    if type(nodes)is not list or len(nodes)>g0.MAX_SOURCE_NODES:raise pi.InputCapacityError('CAPACITY_BLOCKED: source nodes')
    if type(features)is not list or len(features)>pi.MAX_FEATURES:raise pi.InputCapacityError('CAPACITY_BLOCKED: features')
    for node in nodes:
        check();g0._input_ref(node['ref'],source_kind=node['source_kind']);_strong(reader.root,node['ref'],check)
        if node['source_kind']=='osm_road_cells_csv':_strong(reader.root,g0._base_ref(node['provenance_ref']),check)
        if node['source_kind']=='osm_static_projection':old.local_path(reader.root,'scripts/build_osm_prospective_universe.py')
    for f in features:_strong(reader.root,g0._base_ref(f['code_ref']),check)
    policy=g0._base_ref(raw['policy_ref'])
    if policy['path']!=g0.POLICY_PATH:raise ValueError('Fixed G0 policy required')
    _strong(reader.root,policy,check)

def _content(execution,first,reader,check):
    refs={r['path']:r for r in execution['consumed_refs']}
    def consumed(ref):
        if refs.get(ref['path'])!=ref:raise ValueError('Projection ref absent from actual complete closure')
        return ref
    original=reader.read(consumed(execution['forecast_receipt']['manifest_ref']),small=True)
    matches=[n for n in original['source_nodes']if n['id']==original['domain_id']]
    if len(matches)!=1 or matches[0]['source_kind']!='cell_domain':raise ValueError('Exact original cell domain required')
    domain_ref=consumed(matches[0]['ref']);domain=reader.read(domain_ref,small=True)
    _fields(domain,('schema_version','crs','source_class','required_source_ids','cells'))
    if domain['schema_version']!='habu-g0-cell-domain-v1'or domain['crs']!='EPSG:32652':raise ValueError('Original physical cell domain required')
    config=reader.read(consumed(execution['candidate_config_source_receipt']['config_ref']),small=True)
    if config!=first['config']:raise ValueError('Original config changed between admissions')
    value=dict(schema_version=SUMMARY_PROJECTION_VERSION,purpose='DEVELOPMENT_EVALUATION_ONLY',summary_manifest_ref=execution['source_manifest_ref'],summary_manifest_canonical_sha256=execution['source_manifest_canonical_sha256'])
    for key in('operational_night','fit_cutoff','forecast_cutoff'):value[key]=execution[key]
    value.update(forecast_manifest_ref=execution['forecast_receipt']['manifest_ref'],canonical_joined_rows_sha256=execution['forecast_receipt']['canonical_joined_rows_sha256'],domain_ref=domain_ref,horizon=original['horizon'],candidate_ids=execution['candidate_ids'],candidate_config_source={k:execution['candidate_config_source_receipt'][k]for k in SUMMARY_CONFIG_FIELDS})
    for key in('candidate_config_sha256','feature_definition_sha256','fit_lineage','training_selection_sha256','model_bindings','full_counts','model_summaries'):value[key]=execution[key]
    _bound([execution,value,config,domain],check)
    recipes=prep._config(config,execution['candidate_config_sha256'],execution['feature_definition_sha256'],check)
    _,areas,_=_summary_projection(value,list(producer.CANDIDATES),execution['candidate_config_sha256'],execution['feature_definition_sha256'],recipes,check)
    cells=domain['cells'];counts={};previous=None
    if type(cells)is not list or len(cells)!=execution['full_counts']['cell_count']:raise ValueError('Physical domain count mismatch')
    for cell in cells:
        check()
        if(type(cell)is not list or len(cell)!=2 or any(type(v)is not int for v in cell)or not 1000<=cell[0]<=8999 or not 0<=cell[1]<=99999 or previous is not None and tuple(cell)<=previous):raise ValueError('Sorted physical cells required')
        previous=tuple(cell);area=models.area_id(*cell);counts[area]=counts.get(area,0)+1
    if sorted(counts)!=areas:raise ValueError('Area set differs from physical domain')
    for model in value['model_summaries']:
        for area in model['area_summaries']:
            check()
            if area['unit_count']!=counts[area['area_id']]*value['full_counts']['window_count']:raise ValueError('Area count differs from physical cells times windows')
    return value,config,cells,areas

class _State:
    __slots__=('root','context','reader','guard','first','execution','config','projection','projection_sha256','cells','areas','phase','_owner')
    def __init__(self,*args,**kwargs):
        raise ValueError('Transport state is built only inside the public invocation')
    def __setattr__(self,key,value):raise AttributeError('Readonly invocation-owned transport state')

def _dispatch(root,context,state):
    if type(state)is not _State:raise ValueError('Exact closed Stage1 summary state required')
    try:
        valid=(state._owner is _OWNED and state.phase=='READY_STAGE1'and state.context is context and
            state.root==Path(root).absolute()and type(state.reader)is _Reader and state.reader.context is context and
            state.reader.root==state.root and type(state.guard)is _Guard and state.guard.context is context and
            state.reader._guard is state.guard and set(vars(state.reader))=={'root','context','refs','_limits','_guard'} and type(state.reader.refs)is dict and type(state.reader._limits)is dict)
    except AttributeError:valid=False
    if not valid:raise ValueError('Incomplete or foreign transport state')
    _sealed(state.first['receipt'],'receipt_sha256',state.guard)
    _sealed(state.execution,'summary_sha256',state.guard)
    if (state.config!=state.first['config'] or
        _digest(state.config,state.guard)!=state.execution['candidate_config_sha256'] or
        any(state.first['receipt'][k]!=state.execution['candidate_config_source_receipt'][k]for k in SUMMARY_CONFIG_FIELDS)):
        raise ValueError('Invocation child/config identities differ')
    recipes=prep._config(state.config,state.execution['candidate_config_sha256'],state.execution['feature_definition_sha256'],state.guard)
    _summary_projection(state.projection,list(producer.CANDIDATES),state.execution['candidate_config_sha256'],state.execution['feature_definition_sha256'],recipes,state.guard)
    if _digest(state.projection,state.guard)!=state.projection_sha256:raise ValueError('Owned projection changed before Stage1')
    return _evaluate_sources

def _rescan(reader,first,execution,check):
    refs={}
    for ref in[*first['receipt']['consumed_refs'],*execution['consumed_refs'],*reader.refs.values()]:
        check()
        if ref['path']in refs and refs[ref['path']]!=ref:raise ValueError('Conflicting final original-size source refs')
        refs[ref['path']]=dict(ref)
    expected=set(first['receipt']['code_sha256_by_path']);old_source._membership(reader.root,expected,check)
    for ref in refs.values():check();reader.read(ref,parse=False)
    old_source._membership(reader.root,expected,check);check()
    return list(refs.values())

def evaluate_stage1_summary_sources_v2(root,summary_manifest_ref,stage1_manifest_ref,operational_night,forecast_as_of,*,expected_feature_definition_sha256,expected_candidate_config_sha256,context):
    """Actual fixed3 source diagnostic; no parent/native prediction or fit entry."""
    _fields(summary_manifest_ref,g0.REF_FIELDS);summary_manifest_ref=dict(summary_manifest_ref)
    _fields(stage1_manifest_ref,g0.REF_FIELDS);stage1_manifest_ref=dict(stage1_manifest_ref)
    _shape_ref(summary_manifest_ref);_shape_ref(stage1_manifest_ref)
    expected,definition=_sha(expected_candidate_config_sha256),_sha(expected_feature_definition_sha256)
    if not isinstance(context,pi.ProspectiveReadContext):raise ValueError('Actual existing prospective context required')
    if type(context.bytes_read)is not int or context.bytes_read<0 or type(context.max_bytes)is not int or not 0<context.max_bytes<=g0.MAX_TOTAL_READ_BYTES:raise ValueError('Invalid actual context ledger or allowance')
    B=[context.bytes_read];check=_Guard(context)
    try:
        check()
        if context.bytes_read>=context.max_bytes:raise pi.InputCapacityError('CAPACITY_BLOCKED: no remaining transport bytes')
        if not 0<context.remaining_seconds<=300:raise ValueError('Actual remaining elapsed bound must be at most300s')
        if not isinstance(forecast_as_of,datetime)or forecast_as_of.utcoffset()is None:raise ValueError('Actual aware forecast time required')
        pure._night(operational_night);root=Path(root).absolute();_strong(root,summary_manifest_ref,check);_strong(root,stage1_manifest_ref,check)
        check()
        if not local_path(root,stage1_manifest_ref['path']).is_file():raise ValueError('Supplied Stage1 manifest is missing')
        check()
        reader=_Reader(root,context,check);profile=_header(reader,summary_manifest_ref,operational_night,forecast_as_of,expected,definition,check);B.append(context.bytes_read)
        first=source2.load_research_candidate_config_v2(root,profile['candidate_config_manifest'],heldout_night=operational_night,fit_cutoff=profile['fit_cutoff'],forecast_cutoff=profile['forecast_cutoff'],expected_feature_definition_sha256=definition,context=context)
        B.append(context.bytes_read);_sealed(first['receipt'],'receipt_sha256',check)
        if first['receipt']['config_sha256']!=expected:raise ValueError('First actual config differs from expected')
        _forecast_header(reader,profile,check);B.append(context.bytes_read)
        execution=producer.score_g0_forecast_summary_v2(root,summary_manifest_ref,operational_night,forecast_as_of,expected_feature_definition_sha256=definition,expected_candidate_config_sha256=expected,context=context)
        B.append(context.bytes_read);_sealed(execution,'summary_sha256',check)
        second=execution['candidate_config_source_receipt'];_sealed(second,'receipt_sha256',check)
        if any(first['receipt'][k]!=second[k]for k in SUMMARY_CONFIG_FIELDS):raise ValueError('Two real source admissions differ')
        if execution['actual_read_bytes']!=B[4]or not B[3]<=B[4]-execution['summary_read_bytes']<=B[4]:raise ValueError('Producer ledger changed after seal')
        if first['receipt']['actual_read_bytes']!=B[2]or first['receipt']['validation_read_bytes']!=B[2]-B[1]:raise ValueError('Source2 load1 ledger mismatch')
        entry2=second['actual_read_bytes']-second['validation_read_bytes']
        if not B[3]<=entry2<=second['actual_read_bytes']<=B[4]:raise ValueError('Nested load2 ledger outside producer')
        projection=stage1=source_receipt=source_summary=None
        if execution['status']=='NEED_MORE_DATA':
            if execution['model_summaries']:raise ValueError('Partial score set forbidden')
            B.extend([B[4],B[4]])
        else:
            if execution['status']!='COMPLETE_DECLARED_SCORE_SUMMARY':raise ValueError('Complete summary or NMD required')
            projection,config,cells,areas=_content(execution,first,reader,check);B.append(context.bytes_read)
            # No exported constructor/factory/token permits ordinary callers to
            # construct an admitted state. object-level process tampering is not
            # a source-authentication or hostile-loaded-bytecode boundary.
            state=object.__new__(_State)
            owned=dict(root=root,context=context,reader=reader,guard=check,first=first,execution=execution,
                config=config,projection=projection,projection_sha256=_digest(projection,check),cells=cells,
                areas=areas,phase='READY_STAGE1',_owner=_OWNED)
            for key,value in owned.items():object.__setattr__(state,key,value)
            stage1,source_receipt,source_summary=old._evaluate(root,stage1_manifest_ref,None,None,context=context,_summary_v2=state)
            B.append(context.bytes_read)
        refs=_rescan(reader,first,execution,check);B.append(context.bytes_read);B.append(B[7])
        if source_receipt is not None:
            source_receipt.update(consumed_refs=refs,consumed_sha256={r['path']:r['sha256']for r in refs},actual_read_bytes=B[7],transport_read_bytes=B[7]-B[0])
        phases=dict(zip(PHASE_FIELDS,B));phases.update(source2_load1_validation_read_bytes=first['receipt']['validation_read_bytes'],source2_load2_entry_read_bytes=entry2,source2_load2_sealed_read_bytes=second['actual_read_bytes'],source2_load2_validation_read_bytes=second['validation_read_bytes'])
        value=dict(schema_version=VERSION,purpose='DEVELOPMENT_EVALUATION_ONLY',status=stage1['status']if stage1 is not None else'NEED_MORE_DATA',operational_night=operational_night,candidate_ids=list(producer.CANDIDATES),candidate_config_sha256=expected,feature_definition_sha256=definition,score_summary_projection=projection,score_summary_projection_sha256=_digest(projection,check)if projection is not None else None,summary_execution_receipt=execution,summary_execution_receipt_sha256=execution['summary_sha256'],stage1_result=stage1,source_receipt=source_receipt,source_summary=source_summary,source_authentication='NOT_ATTESTED',source_consistency='DECLARED_CONSISTENCY_ONLY',fit_lineage_authentication='CALLER_DEPENDENCY_REQUIRED',scientific_status='NOT_VALIDATED',authorities=dict.fromkeys(pure.SUMMARY_AUTHORITIES,False),limitations=['STANDALONE_DIAGNOSTIC_NOT_NATIVE_PREDICTION_OR_PARENT_ADMISSION','DECLARED_SCOPE_OUTCOMES_AND_MODEL_TRAIN_IDENTITIES_NOT_AUTHENTICATED','NO_TRUSTED_ISSUER_PREREVEAL_CONFIRMATION_OR_PRODUCTION_AUTHORITY'],entry_initial_read_bytes=B[0],actual_read_bytes=B[8],transport_read_bytes=B[8]-B[0],source_admission_receipt=first['receipt'],source_admission_receipt_sha256=first['receipt']['receipt_sha256'],phase_read_ledger=phases)
        result=_finish(value,check)
        check()
        if context.bytes_read!=B[8]:raise ValueError('Actual ledger changed at final output seal')
        return result
    except BaseException as error:
        if check.first is not None:raise check.first
        raise
