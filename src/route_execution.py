"""Conditional remaining original-plan scenarios and sampled-point diagnostics.

Public APIs reroute_remaining_plan/diagnose_route_execution accept exact builtin
JSON only. ORIGINAL/EXECUTION/POLICY/SOURCE below are closed contracts. Selection
and GPS sources are ORIGINAL UTF8 JSON strings, not raw GPX authentication. Their
hash/readiness consistency cannot prove owner intent, sensor origin or issuance.

One native graph/unit preparation and one original solver verification are shared
with optional remaining-state solver and proximity checks under one deadline.
Original return destination and wallclock deadline are immutable. Known incoming
edge state is carried into the existing solver, including after waiting/dwell.
Past/mixed units cannot gain a new full original mean. No subset plan is resealed.

Point proximity is NOT a map match, traveled path, whole-route adherence, active
search, capture outcome or negative label. Unchosen alternatives have no observed
outcome. No switch/hysteresis, live closure assimilation, model update, benefit
estimator, Pn issuance, storage, transport or production authority is implemented.
Private graph/context is constructed internally and never a public input/output.
"""
from __future__ import annotations

from datetime import timedelta
import hashlib
import json
import math
import time

import route_planning as native
from gpx_audit import utm52n

ORIGINAL={'schema_version','graph_input','decision_input','graph_policy','route_policy','route_prediction_sha256'}
EXECUTION={'schema_version','update_as_of','selection_source','observation_source'}
SOURCE={'raw_json_utf8','sha256','size_bytes','readiness','availability_basis'}
READY={'source_received_at','derived_at','materialized_at','audited_at'}
POLICY={'schema_version','phase','frozen_at','purpose','budget_basis','association','max_position_age_seconds',
    'max_observation_gap_seconds','max_accuracy_m','max_endpoint_distance_m','proximity_distance_m','capacities'}
CAPS=dict(max_points=10000,max_distance_checks=1000000,max_source_bytes=4*1024**2,
    max_json_bytes=96*1024**2,max_json_nodes=8000000,max_seconds=30)
SELECTION={'schema_version','original_route_prediction_sha256','selected_route_label','selected_route_sha256','selected_at'}
OBSERVATION={'schema_version','origin','original_route_prediction_sha256','selected_route_sha256','points','current_state'}
POINT={'point_id','sequence','observed_at','latitude','longitude','accuracy_m'}
ARRIVED={'kind','current_point_id','previous_point_id','current_node_id','incoming_edge_id'}
UNSTARTED={'kind','current_point_id','current_node_id'}


def _policy(value,budget):
    if value is None:raise native._Missing('EXPLICIT_EXECUTION_POLICY_REQUIRED')
    native._fields(value,POLICY)
    required=dict(schema_version='habu-route-execution-policy-v2',phase='DEVELOPMENT',
        purpose='CONDITIONAL_RESELECTION_OF_UNCHANGED_ORIGINAL_PLAN',
        budget_basis='ORIGINAL_WALLCLOCK_DEADLINE',association='DECLARED_EDGE_ENDPOINTS_ONLY')
    if any(value[k]!=v for k,v in required.items()):raise native._Unsupported('EXECUTION_SCENARIO_NOT_IMPLEMENTED')
    native._time(value['frozen_at']);native._fields(value['capacities'],set(CAPS))
    for key,limit in CAPS.items():
        if key=='max_seconds':
            if not 0<native._number(value['capacities'][key],0,limit):raise native._Invalid('POSITIVE_TIME_CAP_REQUIRED')
        else:native._integer(value['capacities'][key],1,limit)
    for key in ('max_position_age_seconds','max_observation_gap_seconds'):
        native._number(value[key],0,86400)
    for key in ('max_accuracy_m','max_endpoint_distance_m','proximity_distance_m'):
        native._number(value[key],0,100000)
    budget.deadline=min(budget.deadline,budget.start+value['capacities']['max_seconds']);budget.check()
    return value


def _source(value,asof,policy,budget):
    if value is None:raise native._Missing('DECLARED_EXECUTION_SOURCE_NOT_SUPPLIED')
    native._fields(value,SOURCE);native._text(value['availability_basis']);native._fields(value['readiness'],READY)
    clocks={k:native._time(v) for k,v in value['readiness'].items()}
    if clocks['derived_at']<clocks['source_received_at'] or any(clocks[k]<clocks['derived_at'] for k in ('materialized_at','audited_at')):
        raise native._Invalid('SOURCE_READINESS_CAUSAL_ORDER')
    if max(clocks.values())>asof:raise native._Missing('SOURCE_NOT_AVAILABLE_AT_UPDATE')
    raw=value['raw_json_utf8'];limit=policy['capacities']['max_source_bytes']
    if type(raw) is not str:raise native._Invalid('RAW_UTF8_SOURCE_REQUIRED')
    if len(raw)>limit:raise native._Capacity('RAW_SOURCE_BYTE_CAPACITY')
    encoded=raw.encode('utf-8');budget.check()
    if len(encoded)>limit:raise native._Capacity('RAW_SOURCE_BYTE_CAPACITY')
    if type(value['size_bytes']) is not int or value['size_bytes']!=len(encoded) or native._sha(value['sha256'])!=hashlib.sha256(encoded).hexdigest():
        raise native._Invalid('RAW_SOURCE_HASH_OR_SIZE_MISMATCH')
    body=json.loads(encoded,object_pairs_hook=native._pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(native._Invalid('NONFINITE_SOURCE_JSON')))
    caps=policy['capacities']
    return native._graph_owned(body,budget,max_nodes=caps['max_json_nodes'],max_bytes=caps['max_json_bytes']),clocks


def _xy(latitude,longitude):
    # This native metric has a fixed UTM52N support; do not use it globally.
    lat=native._number(latitude,0,84);lon=native._number(longitude,126,132)
    x,y=utm52n(lat,lon)
    if not math.isfinite(x) or not math.isfinite(y):raise native._Capacity('UTM_NUMERICAL_CAPACITY')
    return x,y


def _inputs(original,execution,policy,budget):
    native._fields(original,ORIGINAL);native._fields(execution,EXECUTION)
    if original['schema_version']!='habu-original-route-bundle-v1' or execution['schema_version']!='habu-route-execution-input-v2':
        raise native._Invalid('EXECUTION_BUNDLE_VERSION')
    native._sha(original['route_prediction_sha256']);asof=native._time(execution['update_as_of'])
    selection,sready=_source(execution['selection_source'],asof,policy,budget)
    observation,oready=_source(execution['observation_source'],asof,policy,budget)
    native._fields(selection,SELECTION);native._fields(observation,OBSERVATION)
    if selection['schema_version']!='habu-declared-route-selection-v1' or observation['schema_version']!='habu-normalized-route-observations-v1':
        raise native._Invalid('SOURCE_SCHEMA_VERSION')
    if observation['origin']!='NORMALIZED_GPS_MEASURED_DECLARATION':raise native._Unsupported('OBSERVATION_ORIGIN_NOT_SUPPORTED')
    expected=original['route_prediction_sha256']
    if selection['original_route_prediction_sha256']!=expected or observation['original_route_prediction_sha256']!=expected:
        raise native._Invalid('ORIGINAL_PREDICTION_SOURCE_BINDING')
    if selection['selected_route_label'] not in ('A','B','C') or native._sha(selection['selected_route_sha256'])!=observation['selected_route_sha256']:
        raise native._Invalid('SELECTED_ROUTE_SOURCE_BINDING')
    selected_at=native._time(selection['selected_at']);frozen=native._time(policy['frozen_at'])
    if selected_at>asof or frozen>=selected_at or max(sready.values())<selected_at:
        raise native._Invalid('SELECTION_POLICY_OR_RECEIPT_CLOCK')
    points=observation['points']
    if type(points) is not list:raise native._Invalid('POINT_LIST_REQUIRED')
    if len(points)>policy['capacities']['max_points']:raise native._Capacity('POINT_CAPACITY')
    if not points:raise native._Missing('OBSERVED_POINTS_REQUIRED')
    ids=set();prior_time=None;prior_sequence=-1
    for point in points:
        budget.check();native._fields(point,POINT);pid=native._text(point['point_id'])
        seq=native._integer(point['sequence'],0,2**53-1);stamp=native._time(point['observed_at'])
        if pid in ids or seq<=prior_sequence or (prior_time is not None and stamp<prior_time):
            raise native._Invalid('OBSERVATION_IDENTITY_OR_ORDER')
        if stamp>asof or stamp>oready['source_received_at'] or stamp<=selected_at or stamp<=max(sready.values()):
            raise native._Invalid('OBSERVATION_FUTURE_OR_CAUSAL_CLOCK')
        _xy(point['latitude'],point['longitude'])
        if point['accuracy_m'] is not None:native._number(point['accuracy_m'],0,100000)
        ids.add(pid);prior_sequence=seq;prior_time=stamp
    return asof,selection,observation


def _position(context,observation,asof,policy):
    points=observation['points'];state=observation['current_state']
    if type(state) is not dict:raise native._Missing('CURRENT_ENTRY_HISTORY_REQUIRED')
    if state.get('kind')=='ARRIVED_VIA_EDGE':native._fields(state,ARRIVED)
    elif state.get('kind')=='UNSTARTED_STATIONARY':native._fields(state,UNSTARTED)
    else:raise native._Missing('CURRENT_ENTRY_HISTORY_UNKNOWN')
    current=points[-1]
    if state['current_point_id']!=current['point_id']:raise native._Invalid('CURRENT_POINT_NOT_LATEST')
    nodes={n['node_id']:n for n in context['graph']['nodes']};node=nodes.get(state['current_node_id'])
    if node is None or node['origin']!='OSM_NODE':raise native._Missing('CURRENT_REAL_GRAPH_NODE_REQUIRED')
    def supported(point,target):
        if point['accuracy_m'] is None or point['accuracy_m']>policy['max_accuracy_m']:
            raise native._Missing('POSITION_PRECISION_UNKNOWN_OR_UNSUPPORTED')
        a=_xy(point['latitude'],point['longitude']);b=_xy(target['latitude'],target['longitude'])
        if math.hypot(a[0]-b[0],a[1]-b[1])>policy['max_endpoint_distance_m']:
            raise native._Invalid('DECLARED_NODE_POSITION_MISMATCH')
    supported(current,node)
    if (asof-native._time(current['observed_at'])).total_seconds()>policy['max_position_age_seconds']:
        raise native._Missing('CURRENT_POSITION_TOO_OLD')
    incoming=''
    if state['kind']=='ARRIVED_VIA_EDGE':
        if len(points)<2 or points[-2]['point_id']!=state['previous_point_id']:raise native._Missing('INCOMING_EDGE_OBSERVATION_PAIR_REQUIRED')
        before=points[-2];gap=(native._time(current['observed_at'])-native._time(before['observed_at'])).total_seconds()
        if not 0<gap<=policy['max_observation_gap_seconds']:raise native._Missing('INCOMING_EDGE_TIME_SUPPORT_UNKNOWN')
        incoming=native._text(state['incoming_edge_id']);edge=context['_last_engine'].edges.get(incoming)
        if edge is None or edge['to_node']!=node['node_id']:raise native._Invalid('INCOMING_EDGE_NODE_BINDING')
        supported(before,nodes[edge['from_node']])
    else:
        if node['node_id']!=context['decision']['start_node_id']:raise native._Invalid('UNSTARTED_ORIGINAL_START_REQUIRED')
        if points[0]['sequence']!=0 or native._time(points[0]['observed_at'])!=context['depart']:
            raise native._Missing('UNSTARTED_HISTORY_FROM_DEPARTURE_REQUIRED')
        prior=None
        for point in points:
            context['budget'].check();supported(point,node);stamp=native._time(point['observed_at'])
            if prior is not None and (stamp-prior).total_seconds()>policy['max_observation_gap_seconds']:
                raise native._Missing('UNSTARTED_HISTORY_GAP_UNRESOLVED')
            prior=stamp
    end=context['end']
    if asof<context['depart'] or asof>=end:raise native._Missing('ORIGINAL_WALLCLOCK_DEADLINE_EXHAUSTED')
    return dict(node_id=node['node_id'],incoming_edge_id=incoming,depart=asof,end=end,
        remaining_budget_seconds=(end-asof).total_seconds())


def _proximity(context,selected,points,policy):
    budget=context['budget'];nodes={n['node_id']:n for n in context['graph']['nodes']}
    edges={e['edge_id']:e for e in context['graph']['edges']};segments=[]
    for eid in sorted(set(selected['edge_ids'])):
        budget.check();e=edges[eid];a=nodes[e['from_node']];b=nodes[e['to_node']]
        segments.append((_xy(a['latitude'],a['longitude']),_xy(b['latitude'],b['longitude'])))
    checks=0;within=0;outside=0;unknown=0
    for point in points:
        budget.check()
        if point['accuracy_m'] is None or point['accuracy_m']>policy['max_accuracy_m'] or not segments:
            unknown+=1;continue
        x,y=_xy(point['latitude'],point['longitude']);distance=None
        for (ax,ay),(bx,by) in segments:
            budget.check();checks+=1
            if checks>policy['capacities']['max_distance_checks']:raise native._Capacity('POINT_EDGE_DISTANCE_WORK_CAPACITY')
            dx,dy=bx-ax,by-ay;length2=dx*dx+dy*dy
            t=max(0.,min(1.,((x-ax)*dx+(y-ay)*dy)/length2)) if length2 else 0.
            d=math.hypot(x-ax-t*dx,y-ay-t*dy);distance=d if distance is None else min(distance,d)
        if distance<=policy['proximity_distance_m']:within+=1
        else:outside+=1
    return dict(kind='POINT_TO_SELECTED_PLANNED_EDGE_DISTANCE_ONLY',observed_points=len(points),
        within_declared_distance_points=within,outside_declared_distance_points=outside,unresolved_points=unknown,
        distance_checks=checks,threshold_m=policy['proximity_distance_m'],continuous_path_inferred=False)


def _empty():
    return dict(schema_version='habu-route-remaining-plan-v2',execution_status='FAIL',blockers=[],remaining_routes=[],
        expected_captures=None,proximity=None,source_authentication='NOT_ATTESTED',scientific_status='NOT_VALIDATED',
        navigation_status='NAVIGATION_BLOCKED',production_authorized=False,official_issuance_authorized=False,
        navigation_authorized=False,fit_authorized=False,source_authorized=False,owner_plan_modified=False,
        scientific_authorized=False,promotion_authorized=False,confirmation_authorized=False,
        owner_subset_intent_authenticated=False,selection_authorized=False,route_benefit='NOT_VALIDATED',
        whole_route_adherence='NOT_ESTABLISHED',capture_outcome='NOT_ASSESSED',verified_active_search_seconds=None,
        negative_labels_created=0,switch_recommendation='NOT_EVALUATED',unselected_route_outcomes=[])


def _execute(original,execution,policy,budget_seconds,reroute):
    result=_empty()
    try:
        budget=native._Budget(budget_seconds)
        original,execution,policy=native._graph_owned([original,execution,policy],budget)
        policy=_policy(policy,budget);caps=policy['capacities']
        native._graph_owned([original,execution,policy],budget,max_nodes=caps['max_json_nodes'],max_bytes=caps['max_json_bytes'])
        asof,selection,observation=_inputs(original,execution,policy,budget)
        proof=native._empty()
        context=native._prepare_route_context(original['graph_input'],original['decision_input'],
            original['graph_policy'],original['route_policy'],budget,proof)
        work=dict(expanded_states=0,shortest_path_calls=0,shortest_path_states=0,shortest_path_relaxations=0)
        native._run_prepared_route(context,proof,work=work)
        if proof.get('route_prediction_sha256')!=original['route_prediction_sha256']:
            raise native._Invalid('ORIGINAL_ROUTE_REPLAY_HASH_MISMATCH')
        selected=[r for r in proof['routes'] if r['label']==selection['selected_route_label'] and r['route_sha256']==selection['selected_route_sha256']]
        if len(selected)!=1:raise native._Invalid('OWNER_SELECTION_NOT_AN_ORIGINAL_CANDIDATE')
        if native._time(selection['selected_at'])<context['cutoff'] or any(not context['depart']<=native._time(p['observed_at'])<=context['end'] for p in observation['points']):
            raise native._Invalid('SELECTION_OR_OBSERVATION_OUTSIDE_ORIGINAL_SCOPE')
        result['proximity']=_proximity(context,selected[0],observation['points'],policy)
        alternatives={r['label']:r for r in proof['routes']}
        result.update(original_route_prediction_sha256=original['route_prediction_sha256'],
            selected_route_sha256=selection['selected_route_sha256'],selected_route_label=selection['selected_route_label'],
            original_source_cutoff=native._utc(context['cutoff']),update_as_of=native._utc(asof),
            original_return_required=context['decision']['require_return'],original_destination_node_id=context['decision']['end_node_id'],
            original_wallclock_deadline=native._utc(context['end']),native_bindings=proof['native_bindings'],
            graph_status=proof['graph_status'],graph_diagnostics=proof['graph_diagnostics'],
            native_count_status=proof['native_count_status'],unmet_requirements=proof['unmet_requirements'],
            declaration_purpose=policy['purpose'],unselected_route_outcomes=[dict(label=label,
                route_sha256=alternatives[label]['route_sha256'] if label in alternatives else None,
                candidate_status='ORIGINAL_CANDIDATE' if label in alternatives else 'NOT_PRODUCED',
                actual_outcome='NOT_OBSERVED') for label in ('A','B','C') if label!=selection['selected_route_label']],
            original_replay_status=proof['execution_status'],source_hashes={k:execution[k]['sha256'] for k in ('selection_source','observation_source')},
            policy_sha256=native._seal(policy,budget,caps['max_json_bytes']),
            original_bundle_sha256=native._seal(original,budget,caps['max_json_bytes']),
            execution_input_sha256=native._seal(execution,budget,caps['max_json_bytes']))
        if reroute:
            remaining=_position(context,observation,asof,policy);rerun=native._empty()
            native._run_prepared_route(context,rerun,remaining_state=remaining,work=work)
            result.update(execution_status=rerun['execution_status'],remaining_routes=rerun['routes'],
                expected_captures=rerun['expected_captures'],blockers=rerun['blockers'],
                remaining_state={**remaining,'depart':native._utc(remaining['depart']),'end':native._utc(remaining['end'])},
                remaining_native_result={k:v for k,v in rerun.items() if k!='runtime_elapsed_seconds'})
        else:result['execution_status']='DIAGNOSTIC_ONLY'
        result['work']=dict(work);budget.check()
        result['omitted_operational_fields']=['runtime_elapsed_seconds']
        result['execution_sha256']=native._seal(result,budget,caps['max_json_bytes'])
        result['runtime_elapsed_seconds']=time.monotonic()-budget.start
        native._graph_owned(result,budget,max_nodes=caps['max_json_nodes'],max_bytes=caps['max_json_bytes'])
    except native._Missing as exc:result.update(execution_status='DATA_BLOCKED',blockers=[str(exc)])
    except native._Unsupported as exc:result.update(execution_status='IMPLEMENTATION_BLOCKED',blockers=[str(exc)])
    except (native._Capacity,native._GraphCapacity,native.CountActivityCapacityError):
        result.update(execution_status='RUNTIME_BLOCKED',blockers=['EXECUTION_RESOURCE_OR_RUNTIME_CAPACITY'])
    except (native._Invalid,native._GraphInvalid,ValueError,TypeError,KeyError,IndexError,OverflowError,RecursionError,UnicodeError):
        result.update(execution_status='FAIL',blockers=['EXECUTION_SOURCE_OR_POLICY_INVALID'])
    if result['execution_status'] in ('FAIL','DATA_BLOCKED','IMPLEMENTATION_BLOCKED','RUNTIME_BLOCKED'):
        # No partially populated or unsealed derived claim survives a failure.
        result={**_empty(),'execution_status':result['execution_status'],'blockers':result['blockers']}
    return result


def reroute_remaining_plan(original,execution,*,policy,budget_seconds=30):
    """Offer conditional remaining routes; no owner reselection or Pn is issued."""
    return _execute(original,execution,policy,budget_seconds,True)


def diagnose_route_execution(original,execution,*,policy,budget_seconds=30):
    """Count sampled-point proximity only; never infer actual continuous search."""
    return _execute(original,execution,policy,budget_seconds,False)
