"""Bounded conditional candidates of one unchanged original future search plan.

API: plan_route_candidates(graph_input,decision_input,*,graph_policy,policy,
budget_seconds=30). Closed fields are DECISION/POLICY/CAPS below; fixtures give
fully explicit example values, never real policy defaults. Native topology and
Gamma-Poisson unit prediction execute again; computed graph/means are not inputs.

links_source/travel_profile_source each contain exact raw_json_utf8, sha256,
size_bytes, available_at, availability_basis. Strict JSON bodies use LINK/PROFILE
fields below. Allocation links bind native graph/domain/context/model/protocol/
physical-plan hashes, exact allocation ID/hash, real incident OSM node and way.
Native UTM52N geometry must put that node in the original 100m allocation cell.
No snapping, XY bridge, edge projection, moved time or subset owner plan exists.

Only explicit stationary-node full original allocation dwell and waiting until
its unchanged start are implemented. A touched unit must be completed in full
before a final candidate can receive its native mean. Transit/revisits add no
reward. One common Gamma rate has cross-unit covariance; no marginal intervals
are summed. No route-side a/b inference or per-way biological rate is invented.

The supported uncertainty mode is TRAVEL_ONLY_NOT_AVAILABLE: lambda_u=0 and C
uses travel time only. Actual uncertainty is None/NOT_AVAILABLE. A declared speed
scenario is neither measured confidence nor risk. Other uncertainty semantics
are IMPLEMENTATION_BLOCKED rather than converted by an invented formula.

Edge-state Dijkstra preserves the preceding directed edge across legs/dwell.
Beam search has globally counted work and a cooperative deadline, deterministic
ties and feasible incumbents, never an optimality proof. Source/availability,
complete road restrictions/access, actual intent/benefit and safe navigation are
not authenticated by JSON. All scientific/production/navigation gates stay shut.
No filesystem/source/model writes, callbacks, dynamic dispatch or transport.
"""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
import hashlib
import heapq
import json
import math
import re
import time

from count_activity import predict_gamma_poisson_units,CountActivityCapacityError
from gpx_audit import utm52n
from master_contracts import digest
from route_graph import build_route_graph,_owned as _graph_owned,_Invalid as _GraphInvalid,_Capacity as _GraphCapacity

DECISION={'schema_version','graph_sha256','graph_policy_sha256','graph_domain_sha256','context',
    'model','count_protocol','planned_effort_inputs','links_source','travel_profile_source',
    'start_node_id','end_node_id','require_return','depart_at','time_budget_seconds'}
POLICY={'schema_version','phase','frozen_at','mode','association','search_timing','wait_policy',
    'partial_unit_policy','shortest_path_objective','access_policy','known_speed_limit_policy',
    'uncertainty_mode','speed_bounds_m_per_second','utility','alternatives',
    'minimum_completed_allocations','minimum_completed_units','capacities'}
CAPS=dict(max_reward_waypoints=50,beam_width=64,max_depth=20,max_expanded_states=10000,
    max_shortest_path_calls=10000,max_shortest_path_states=100000,max_shortest_path_relaxations=500000,
    max_graph_nodes=100000,max_graph_edges=200000,max_json_nodes=8000000,max_json_bytes=96*1024**2,
    max_source_bytes=4*1024**2,max_seconds=30)
LINK={'schema_version','graph_sha256','graph_policy_sha256','graph_domain_sha256','context',
      'model_sha256','count_protocol_sha256','planned_source_sha256','records'}
PROFILE={'schema_version','profile_id','context','identity','speed_m_per_second','turn_seconds','speed_basis'}
SOURCE={'raw_json_utf8','sha256','size_bytes','available_at','availability_basis'}


class _Invalid(ValueError):pass
class _Missing(ValueError):pass
class _Unsupported(ValueError):pass
class _Capacity(ValueError):pass
class _SearchEnd(ValueError):pass


class _Budget:
    def __init__(self,seconds):
        kind=type(seconds)
        if (kind is not int and kind is not float) or not 0<seconds<=30:
            raise _Invalid('BOUNDED_NONBOOLEAN_BUDGET_REQUIRED')
        self.start=time.monotonic();self.deadline=self.start+seconds
    def check(self):
        if time.monotonic()>=self.deadline:raise _Capacity('ELAPSED_CAPACITY_EXCEEDED')
    def remaining(self):
        self.check();return max(1e-12,self.deadline-time.monotonic())


def _fields(value,fields):
    if type(value) is not dict or set(value)!=fields:raise _Invalid('EXACT_FIELDS_REQUIRED')


def _text(value):
    if type(value) is not str or not value or len(value)>256 or not value.isprintable():
        raise _Invalid('BOUNDED_TEXT_REQUIRED')
    return value


def _time(value):
    if type(value) is not str or len(value)>64:raise _Invalid('AWARE_TIME_REQUIRED')
    try:stamp=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:raise _Invalid('AWARE_TIME_REQUIRED') from None
    if stamp.utcoffset() is None:raise _Invalid('AWARE_TIME_REQUIRED')
    return stamp.astimezone(timezone.utc)


def _utc(value):return value.astimezone(timezone.utc).isoformat().replace('+00:00','Z')


def _number(value,low=0,high=1e100):
    kind=type(value)
    if (kind is not int and kind is not float) or not low<=value<=high:
        raise _Invalid('FINITE_NONBOOLEAN_NUMBER_REQUIRED')
    return float(value)


def _integer(value,minimum,maximum):
    if type(value) is not int or not minimum<=value<=maximum:raise _Invalid('BOUNDED_INTEGER_REQUIRED')
    return value


def _sha(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}',value):raise _Invalid('SHA256_REQUIRED')
    return value


def _seal(value,budget,limit):
    sha=hashlib.sha256();size=0
    encoder=json.JSONEncoder(sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    for part in encoder.iterencode(value):
        budget.check();raw=part.encode('utf-8');size+=len(raw)
        if size>limit:raise _Capacity('JSON_OUTPUT_BYTE_CAPACITY_EXCEEDED')
        sha.update(raw)
    budget.check();return sha.hexdigest()


def _policy(value,budget):
    if value is None:raise _Missing('EXPLICIT_ROUTE_POLICY_NOT_SUPPLIED')
    _fields(value,POLICY)
    if value['schema_version']!='habu-conditional-route-policy-v1' or value['phase']!='DEVELOPMENT':
        raise _Invalid('DEVELOPMENT_ROUTE_POLICY_REQUIRED')
    _time(value['frozen_at']);_text(value['mode']);_fields(value['capacities'],set(CAPS))
    for name,ceiling in CAPS.items():
        if name=='max_seconds':
            if not 0<_number(value['capacities'][name],0,ceiling):raise _Invalid('POSITIVE_ELAPSED_LIMIT_REQUIRED')
        else:_integer(value['capacities'][name],1,ceiling)
    budget.deadline=min(budget.deadline,budget.start+value['capacities']['max_seconds']);budget.check()
    supported=dict(association='REAL_OSM_NODE_IN_ORIGINAL_100M_CELL',search_timing='FULL_ORIGINAL_ALLOCATION_STATIONARY_NODE',
        wait_policy='WAIT_AT_LINKED_NODE_UNTIL_ORIGINAL_START',partial_unit_policy='EXCLUDE_CANDIDATES_WITH_TOUCHED_INCOMPLETE_UNITS',
        shortest_path_objective='TRAVEL_TIME_ONLY',access_policy='ALLOW_DECLARED_NOT_VERIFIED_ONLY',
        known_speed_limit_policy='ENFORCE_PLAIN_KMH_OTHER_TAGS_BLOCK')
    if any(value[k]!=v for k,v in supported.items()):raise _Unsupported('ROUTE_SCENARIO_SEMANTICS_NOT_IMPLEMENTED')
    _fields(value['speed_bounds_m_per_second'],{'minimum','maximum'})
    lo,hi=(value['speed_bounds_m_per_second'][k] for k in ('minimum','maximum'))
    if not 0<_number(lo)<=_number(hi):raise _Invalid('POSITIVE_SPEED_RANGE_REQUIRED')
    _fields(value['utility'],{'expected_capture_weight','elapsed_seconds_weight','uncertainty_weight'})
    for x in value['utility'].values():_number(x)
    alt=value['alternatives'];_fields(alt,{'labels','b_max_overlap','c_max_overlap','c_min_expected_reward','c_objective','overlap_metric'})
    if alt['labels']!=['A','B','C'] or alt['overlap_metric']!='SHARED_UNIQUE_DIRECTED_LENGTH_OVER_MIN_UNIQUE_LENGTH':
        raise _Invalid('EXPLICIT_ABC_AND_OVERLAP_CONTRACT_REQUIRED')
    for key in ('b_max_overlap','c_max_overlap'):
        if not 0<=_number(alt[key])<1:raise _Invalid('DIVERGENCE_BOUND_REQUIRED')
    _number(alt['c_min_expected_reward'])
    if value['uncertainty_mode']!='TRAVEL_ONLY_NOT_AVAILABLE' or value['utility']['uncertainty_weight']!=0 or alt['c_objective']!='TRAVEL_TIME_ONLY':
        raise _Unsupported('ACTUAL_UNCERTAINTY_METADATA_NOT_AVAILABLE')
    _integer(value['minimum_completed_allocations'],1,value['capacities']['max_reward_waypoints'])
    _integer(value['minimum_completed_units'],0,120000)
    return value


def _pairs(pairs):
    result={}
    for key,item in pairs:
        if key in result:raise _Invalid('DUPLICATE_SOURCE_JSON_KEY')
        result[key]=item
    return result


def _source(value,cutoff,policy,budget):
    if value is None:raise _Missing('SOURCE_BOUND_LINKS_AND_TRAVEL_PROFILE_REQUIRED')
    _fields(value,SOURCE);_text(value['availability_basis'])
    if value['available_at'] is None:raise _Missing('SOURCE_AVAILABILITY_NOT_SUPPLIED')
    if _time(value['available_at'])>=cutoff:raise _Missing('SOURCE_NOT_AVAILABLE_BEFORE_OWN_CUTOFF')
    text=value['raw_json_utf8']
    if type(text) is not str:raise _Invalid('ORIGINAL_SOURCE_UTF8_REQUIRED')
    if len(text)>policy['capacities']['max_source_bytes']:raise _Capacity('SOURCE_BYTE_CAPACITY_EXCEEDED')
    raw=text.encode('utf-8');budget.check()
    if len(raw)>policy['capacities']['max_source_bytes']:raise _Capacity('SOURCE_BYTE_CAPACITY_EXCEEDED')
    if type(value['size_bytes']) is not int or value['size_bytes']!=len(raw) or _sha(value['sha256'])!=hashlib.sha256(raw).hexdigest():
        raise _Invalid('ORIGINAL_SOURCE_BYTE_BINDING_MISMATCH')
    body=json.loads(raw,object_pairs_hook=_pairs)
    return _graph_owned(body,budget,max_nodes=policy['capacities']['max_json_nodes'],max_bytes=policy['capacities']['max_json_bytes'])


def _context(decision,graph,count,policy):
    context=decision['context']
    if context!=graph['context'] or context['mode']!=policy['mode']:raise _Invalid('GRAPH_DECISION_CONTEXT_MISMATCH')
    aggregate=count['aggregate_prediction'];cutoff=_time(context['cutoff_time'])
    if not _time(policy['frozen_at'])<cutoff:raise _Invalid('POLICY_NOT_FROZEN_BEFORE_CUTOFF')
    if (aggregate['operational_night']!=context['operational_night'] or _time(aggregate['cutoff_time'])!=cutoff or
        _time(aggregate['forecast_window']['start'])!=_time(context['forecast_start']) or
        _time(aggregate['forecast_window']['end'])!=_time(context['forecast_end'])):
        raise _Invalid('NATIVE_COUNT_GRAPH_SCOPE_MISMATCH')
    depart=_time(decision['depart_at']);seconds=_number(decision['time_budget_seconds'],0,86400)
    if not seconds>0 or not cutoff<=_time(context['forecast_start'])<=depart<_time(context['forecast_end']):
        raise _Invalid('DEPARTURE_BUDGET_SCOPE_MISMATCH')
    if type(decision['require_return']) is not bool:raise _Invalid('EXPLICIT_RETURN_BOOLEAN_REQUIRED')
    if decision['require_return'] and decision['start_node_id']!=decision['end_node_id']:raise _Invalid('RETURN_NODE_MISMATCH')
    return cutoff,depart,min(depart+timedelta(seconds=seconds),_time(context['forecast_end']))


def _associations(decision,graph,count,policy,cutoff,budget):
    links=_source(decision['links_source'],cutoff,policy,budget);_fields(links,LINK)
    if links['schema_version']!='habu-route-allocation-links-v1':raise _Invalid('LINK_SOURCE_VERSION_REQUIRED')
    for name in ('graph_sha256','graph_policy_sha256','graph_domain_sha256','context'):
        if links[name]!=decision[name]:raise _Invalid('LINK_GRAPH_SCOPE_MISMATCH')
    expected=dict(model_sha256=count['lineage']['model_sha256'],count_protocol_sha256=count['lineage']['protocol_sha256'],planned_source_sha256=count['lineage']['planned_source_sha256'])
    if any(links[k]!=v for k,v in expected.items()):raise _Invalid('LINK_NATIVE_COUNT_BINDING_MISMATCH')
    profile=_source(decision['travel_profile_source'],cutoff,policy,budget);_fields(profile,PROFILE)
    if profile['schema_version']!='habu-route-travel-profile-v1' or profile['context']!=decision['context']:
        raise _Invalid('TRAVEL_PROFILE_SCOPE_MISMATCH')
    _text(profile['profile_id'])
    if profile['identity']!=decision['planned_effort_inputs']['expected_identity']:raise _Invalid('TRAVEL_PROFILE_SEARCH_IDENTITY_MISMATCH')
    if profile['speed_basis']!='DECLARED_PLANNING_ASSUMPTION':raise _Unsupported('TRAVEL_SPEED_BASIS_NOT_IMPLEMENTED')
    bounds=policy['speed_bounds_m_per_second'];speed=_number(profile['speed_m_per_second'],bounds['minimum'],bounds['maximum'])
    if speed<=0:raise _Invalid('POSITIVE_TRAVEL_SPEED_REQUIRED')
    turn=_number(profile['turn_seconds'],0,86400)
    nodes={n['node_id']:n for n in graph['nodes']};ways={w['way_ref'] for w in graph['ways']}
    incident={(e['from_node'],e['way_ref']) for e in graph['edges']}|{(e['to_node'],e['way_ref']) for e in graph['edges']}
    for key in ('start_node_id','end_node_id'):
        ident=_text(decision[key])
        if ident not in nodes:raise _Missing('START_OR_END_REAL_NODE_NOT_AVAILABLE')
        if nodes[ident]['origin']!='OSM_NODE':raise _Unsupported('START_OR_END_EDGE_PROJECTION_NOT_IMPLEMENTED')
    originals={r['allocation']['allocation_id']:r for r in count['original_allocations']}
    if len(originals)>policy['capacities']['max_reward_waypoints']:raise _Capacity('COMPLETE_ORIGINAL_ALLOCATION_WAYPOINT_CAPACITY_EXCEEDED')
    if type(links['records']) is not list:raise _Invalid('LINK_RECORD_LIST_REQUIRED')
    found={}
    for link in links['records']:
        budget.check();_fields(link,{'allocation_id','allocation_sha256','association_type','node_id','way_ref'})
        aid=_text(link['allocation_id'])
        if aid in found or aid not in originals:raise _Invalid('DUPLICATE_OR_FOREIGN_ALLOCATION_LINK')
        if link['association_type']!='OSM_NODE':raise _Unsupported('EDGE_PROJECTION_ASSOCIATION_NOT_IMPLEMENTED')
        if link['allocation_sha256']!=originals[aid]['allocation_sha256']:raise _Invalid('ORIGINAL_ALLOCATION_HASH_MISMATCH')
        node_id=_text(link['node_id']);ref=_text(link['way_ref'])
        if node_id not in nodes:raise _Missing('LINKED_REAL_NODE_NOT_AVAILABLE')
        if nodes[node_id]['origin']!='OSM_NODE':raise _Unsupported('BOUNDARY_NODE_ASSOCIATION_NOT_IMPLEMENTED')
        if ref not in ways or (node_id,ref) not in incident:raise _Invalid('LINKED_WAY_NOT_INCIDENT_TO_REAL_NODE')
        x,y=utm52n(nodes[node_id]['latitude'],nodes[node_id]['longitude']);allocation=originals[aid]['allocation']
        if (math.floor(x/100),math.floor(y/100))!=(allocation['cell_x'],allocation['cell_y']):
            raise _Invalid('ALLOCATION_REAL_NODE_CELL_MISMATCH')
        found[aid]=dict(allocation=allocation,node_id=node_id)
    if set(found)!=set(originals):raise _Missing('COMPLETE_ORIGINAL_ALLOCATION_LINKS_NOT_SUPPLIED')
    return found,speed,turn


class _Engine:
    def __init__(self,graph,decision,policy,tasks,units,speed,turn,depart,end,budget,*,initial_previous="",work=None):
        self.graph=graph;self.decision=decision;self.policy=policy;self.tasks=tasks;self.units=units
        self.speed=speed;self.turn=turn;self.depart=depart;self.end=end;self.budget=budget
        self.caps=policy['capacities'];self.reasons=set();self.exhausted=False;self.blockers=[]
        self.initial_previous=initial_previous
        self.work=work if work is not None else dict(expanded_states=0,shortest_path_calls=0,shortest_path_states=0,shortest_path_relaxations=0)
        ways={w['way_ref']:w for w in graph['ways']};self.edges={};self.adj={};self.no={};self.only={}
        self.uncertain_nodes={r['node_id'] for r in graph['diagnostics'] if r['reason']=='STRUCTURAL_TRANSITION_UNVERIFIED'}
        for edge in graph['edges']:
            budget.check()
            if edge['access_status']!='DECLARED_ALLOWED_NOT_VERIFIED':self.reasons.add('ACCESS_UNKNOWN_EDGE_EXCLUDED');continue
            tags=ways[edge['way_ref']]['tags']
            # The plain-kmh-only policy cannot resolve scoped/advisory/unit
            # grammar. Never let a generic limit mask an unsupported override.
            if any(key.startswith('maxspeed:') for key in tags):
                self.reasons.add('UNSUPPORTED_SCOPED_SPEED_LIMIT_EDGE_EXCLUDED');continue
            tag=tags.get('maxspeed')
            if tag is not None:
                if not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?',tag.strip()):self.reasons.add('UNSUPPORTED_SPEED_LIMIT_EDGE_EXCLUDED');continue
                limit=float(tag)/3.6
                if not math.isfinite(limit):self.reasons.add('UNSUPPORTED_SPEED_LIMIT_EDGE_EXCLUDED');continue
                if speed>limit:self.reasons.add('KNOWN_SPEED_LIMIT_EDGE_EXCLUDED');continue
            self.edges[edge['edge_id']]=edge;self.adj.setdefault(edge['from_node'],[]).append(edge['edge_id'])
        for outgoing in self.adj.values():outgoing.sort()
        for rule in graph['transition_constraints']:
            for before in rule['from_edges']:
                key=rule['via_node'],before
                if rule['rule']=='NO':self.no.setdefault(key,set()).update(rule['to_edges'])
                else:self.only.setdefault(key,[]).append(set(rule['to_edges']))
        self.requirements={r['row_id']:{part['allocation_id'] for part in r['allocation_intersections']} for r in units if r['allocation_intersections']}
        self.means={r['row_id']:r['mean'] for r in units}

    def _charge(self,name,cap):
        self.budget.check()
        if self.work[name]>=self.caps[cap]:raise _SearchEnd('SHORTEST_PATH_GLOBAL_CAPACITY_EXCEEDED')
        self.work[name]+=1

    def path(self,node,previous,target):
        self._charge('shortest_path_calls','max_shortest_path_calls')
        if node==target:return dict(edge_ids=[],seconds=0.,distance_m=0.,previous=previous)
        start=node,previous;heap=[(0.,node,previous)];best={start:0.};parents={}
        while heap:
            self._charge('shortest_path_states','max_shortest_path_states')
            cost,current,pre=heapq.heappop(heap);key=current,pre
            if cost!=best[key]:continue
            if current==target:
                ids=[];cursor=key
                while cursor!=start:
                    self.budget.check();parent,eid=parents[cursor];ids.append(eid);cursor=parent
                ids.reverse();return dict(edge_ids=ids,seconds=cost,distance_m=math.fsum(self.edges[e]['length_m'] for e in ids),previous=pre)
            for eid in self.adj.get(current,[]):
                self._charge('shortest_path_relaxations','max_shortest_path_relaxations');edge=self.edges[eid]
                if eid in self.no.get((current,pre),()):continue
                if any(eid not in allowed for allowed in self.only.get((current,pre),())):continue
                if current in self.uncertain_nodes and pre and self.edges[pre]['way_ref']!=edge['way_ref']:
                    self.reasons.add('STRUCTURAL_TRANSITION_UNVERIFIED_EXCLUDED');continue
                nxt=edge['to_node'],eid;candidate=cost+edge['length_m']/self.speed+(self.turn if pre else 0)
                if not math.isfinite(candidate):raise _Capacity('TRAVEL_NUMERICAL_CAPACITY_EXCEEDED')
                if nxt not in best or candidate<best[nxt]:
                    best[nxt]=candidate;parents[nxt]=(key,eid);heapq.heappush(heap,(candidate,*nxt))
        return None

    def credit(self,done):
        ids=[];touched_incomplete=False
        for key,required in self.requirements.items():
            self.budget.check()
            if required<=done:ids.append(key)
            elif required&done:touched_incomplete=True
        ids.sort()
        return ids,math.fsum(self.means[i] for i in ids),touched_incomplete

    def remaining_at(self,clock):
        return min((self.end-clock).total_seconds(),
            self.decision['time_budget_seconds']-(clock-self.depart).total_seconds())

    def candidate(self,state,return_path):
        if return_path is None:self.reasons.add('RETURN_UNREACHABLE');return None
        if return_path['seconds']>self.remaining_at(state['clock']):
            self.reasons.add('RETURN_EXCEEDS_BUDGET_OR_HORIZON');return None
        arrived=state['clock']+timedelta(seconds=return_path['seconds'])
        credited,mean,incomplete=self.credit(state['done'])
        if incomplete:self.reasons.add('TOUCHED_UNIT_INCOMPLETE_NO_PARTIAL_CREDIT');return None
        if len(state['done'])<self.policy['minimum_completed_allocations'] or len(credited)<self.policy['minimum_completed_units']:return None
        elapsed=(state['clock']-self.depart).total_seconds()+return_path['seconds'];weights=self.policy['utility']
        utility=weights['expected_capture_weight']*mean-weights['elapsed_seconds_weight']*elapsed
        if not math.isfinite(utility):raise _Capacity('UTILITY_NUMERICAL_CAPACITY_EXCEEDED')
        edge_ids=state['edge_ids']+return_path['edge_ids']
        result=dict(edge_ids=edge_ids,completed_allocation_ids=sorted(state['done']),credited_unit_ids=credited,
            expected_captures=mean,reward_semantics='SUM_NATIVE_MEANS_OF_FULL_ORIGINAL_UNITS_ONLY',utility=utility,
            travel_seconds=state['travel']+return_path['seconds'],wait_seconds=state['wait'],search_seconds=state['search'],
            elapsed_seconds=elapsed,distance_m=state['distance']+return_path['distance_m'],
            arrival_node_id=self.decision['end_node_id'],arrived_at=_utc(arrived),depart_at=_utc(self.depart),
            uncertainty=None,uncertainty_status='NOT_AVAILABLE',search_actions=state['actions'])
        result['route_sha256']=digest(result);return result

    def search(self):
        initial=dict(node=self.decision['start_node_id'],previous=self.initial_previous,clock=self.depart,done=set(),edge_ids=[],
            travel=0.,distance=0.,wait=0.,search=0,actions=[])
        states=[initial];pool={};ordered=sorted(self.tasks.items(),key=lambda v:(_time(v[1]['allocation']['start']),v[0]))
        try:
            for depth in range(self.caps['max_depth']):
                children=[]
                for state in states:
                    self.budget.check()
                    for aid,task in ordered:
                        if aid in state['done']:continue
                        allocation=task['allocation'];start=_time(allocation['start']);end=_time(allocation['end'])
                        if state['clock']>start:self.reasons.add('ORIGINAL_ALLOCATION_START_ALREADY_PASSED');continue
                        if self.work['expanded_states']>=self.caps['max_expanded_states']:raise _SearchEnd('BEAM_STATE_CAPACITY_EXCEEDED')
                        self.work['expanded_states']+=1
                        path=self.path(state['node'],state['previous'],task['node_id'])
                        if path is None:self.reasons.add('ALLOCATION_UNREACHABLE');continue
                        gap=(start-state['clock']).total_seconds()
                        if path['seconds']>gap:self.reasons.add('LATE_FOR_FULL_ORIGINAL_ALLOCATION');continue
                        arrival=state['clock']+timedelta(seconds=path['seconds'])
                        if end>self.end or (end-self.depart).total_seconds()>self.decision['time_budget_seconds']:
                            self.reasons.add('ALLOCATION_EXCEEDS_BUDGET_OR_HORIZON');continue
                        wait=gap-path['seconds']
                        child=dict(node=task['node_id'],previous=path['previous'],clock=end,done=state['done']|{aid},
                            edge_ids=state['edge_ids']+path['edge_ids'],travel=state['travel']+path['seconds'],
                            distance=state['distance']+path['distance_m'],wait=state['wait']+wait,
                            search=state['search']+allocation['planned_active_search_seconds'],
                            actions=state['actions']+[dict(allocation_id=aid,node_id=task['node_id'],
                                start=allocation['start'],end=allocation['end'],planned_active_search_seconds=allocation['planned_active_search_seconds'],
                                arrived_at=_utc(arrival),wait_seconds=wait)])
                        back=self.path(child['node'],child['previous'],self.decision['end_node_id'])
                        if back is None:self.reasons.add('RETURN_UNREACHABLE');continue
                        if back['seconds']>self.remaining_at(end):self.reasons.add('RETURN_EXCEEDS_BUDGET_OR_HORIZON');continue
                        route=self.candidate(child,back)
                        if route is not None:pool.setdefault(route['route_sha256'],route)
                        children.append(child)
                if not children:break
                def rank(state):
                    _,reward,_=self.credit(state['done']);return (-reward,state['clock'],tuple(state['edge_ids']),tuple(sorted(state['done'])))
                children.sort(key=rank)
                if len(children)>self.caps['beam_width']:self.exhausted=True;self.blockers.append('BEAM_WIDTH_PRUNED')
                states=children[:self.caps['beam_width']]
            else:
                if any(len(s['done'])<len(self.tasks) for s in states):self.exhausted=True;self.blockers.append('BEAM_DEPTH_LIMIT_REACHED')
        except _SearchEnd as exc:self.exhausted=True;self.blockers.append(str(exc))
        return list(pool.values())

    def overlap(self,a,b):
        first,second=set(a['edge_ids']),set(b['edge_ids'])
        denominator=min(math.fsum(self.edges[e]['length_m'] for e in first),math.fsum(self.edges[e]['length_m'] for e in second))
        return math.fsum(self.edges[e]['length_m'] for e in first&second)/denominator if denominator>0 else 1.

    def choose(self,pool):
        selected=[];missing=[];alternatives=self.policy['alternatives']
        rank=lambda r:(-r['utility'],-r['expected_captures'],r['elapsed_seconds'],tuple(r['edge_ids']),tuple(r['completed_allocation_ids']))
        if not pool:return [],['NO_FEASIBLE_A','NO_FEASIBLE_DIVERSE_B','NO_FEASIBLE_DIVERSE_C']
        a=min(pool,key=rank);selected.append(dict(a,label='A'))
        for label in ('B','C'):
            eligible=[r for r in pool if all(r['edge_ids']!=s['edge_ids'] and self.overlap(r,s)<=alternatives['b_max_overlap' if label=='B' else 'c_max_overlap'] for s in selected)]
            if label=='C':eligible=[r for r in eligible if r['expected_captures']>=alternatives['c_min_expected_reward']]
            if not eligible:missing.append('NO_FEASIBLE_DIVERSE_'+label);continue
            key=rank if label=='B' else lambda r:(r['travel_seconds'],-r['expected_captures'],tuple(r['edge_ids']),tuple(r['completed_allocation_ids']))
            selected.append(dict(min(eligible,key=key),label=label))
        return selected,missing


def _empty():
    return dict(schema_version='habu-conditional-route-result-v1',execution_status='FAIL',routes=[],blockers=[],
        expected_captures=None,navigation_status='NAVIGATION_BLOCKED',source_authentication='NOT_ATTESTED',
        scientific_status='NOT_VALIDATED',scientific_authorized=False,production_authorized=False,
        source_authorized=False,fit_authorized=False,selection_authorized=False,promotion_authorized=False,
        confirmation_authorized=False,navigation_authorized=False,route_benefit_validated=False,
        official_issuance_authorized=False,owner_plan_modified=False,owner_subset_intent_authenticated=False,
        uncertainty=None,uncertainty_status='NOT_AVAILABLE',global_optimum_proven=False,search_exhausted=False)


def _prepare_route_context(graph_input,decision_input,graph_policy,policy,budget,result):
    """Fixed internal preparation; never accept a caller-supplied computed context."""
    gi,decision,gp,policy=_graph_owned([graph_input,decision_input,graph_policy,policy],budget)
    policy=_policy(policy,budget);caps=policy['capacities']
    _graph_owned([gi,decision,gp,policy],budget,max_nodes=caps['max_json_nodes'],max_bytes=caps['max_json_bytes'])
    if decision is None:raise _Missing('SOURCE_BOUND_ROUTE_DECISION_NOT_SUPPLIED')
    _fields(decision,DECISION)
    if decision['schema_version']!='habu-conditional-route-decision-v1':raise _Invalid('DECISION_VERSION_REQUIRED')
    if _sha(decision['graph_policy_sha256'])!=digest(gp):raise _Invalid('GRAPH_POLICY_HASH_MISMATCH')
    if gi is None:raise _Missing('NATIVE_GRAPH_INPUT_NOT_SUPPLIED')
    graph=build_route_graph(gi,policy=gp,budget_seconds=budget.remaining());budget.check()
    if graph.get('graph_sha256') is None:
        if graph['status']=='FAIL':raise _Invalid('NATIVE_GRAPH_CONTRACT_INVALID')
        if graph['status']=='CAPACITY_EXCEEDED':raise _Capacity('NATIVE_GRAPH_CAPACITY_EXCEEDED')
        raise _Missing('NATIVE_GRAPH_NOT_PRODUCED')
    if decision['graph_sha256']!=graph['graph_sha256'] or decision['graph_domain_sha256']!=graph['domain_sha256']:
        raise _Invalid('NATIVE_GRAPH_BINDING_MISMATCH')
    if len(graph['nodes'])>caps['max_graph_nodes'] or len(graph['edges'])>caps['max_graph_edges']:
        raise _Capacity('ROUTE_GRAPH_CAPACITY_EXCEEDED')
    if any('RESTRICTION' in d['reason'] or 'U_TURN' in d['reason'] for d in graph['diagnostics']):
        raise _Unsupported('UNRESOLVED_NATIVE_RESTRICTION_SEMANTICS')
    if decision['count_protocol'] is None:raise _Missing('EXPLICIT_COUNT_PROTOCOL_NOT_SUPPLIED')
    count=predict_gamma_poisson_units(decision['model'],decision['planned_effort_inputs'],
        protocol=decision['count_protocol'],budget_seconds=budget.remaining());budget.check()
    result['native_count_status']=count['status']
    result['native_count_missing_requirements']=[x if type(x) is str and re.fullmatch('[A-Z][A-Z0-9_]{0,127}',x) else 'NATIVE_COUNT_CONTRACT_UNAVAILABLE'
        for x in count['missing_requirements']]
    if count['status']=='RUNTIME_BINDING_ERROR':raise _Capacity('NATIVE_COUNT_RUNTIME_BINDING_ERROR')
    if count['unit_predictions'] is None:raise _Missing('NATIVE_COUNT_UNIT_PREDICTION_NOT_PRODUCED')
    if any(row['mean'] is None for row in count['unit_predictions']):raise _Capacity('NATIVE_COUNT_UNIT_MOMENTS_UNAVAILABLE')
    cutoff,depart,end=_context(decision,graph,count,policy)
    tasks,speed,turn=_associations(decision,graph,count,policy,cutoff,budget)
    return dict(gi=gi,decision=decision,gp=gp,policy=policy,graph=graph,count=count,
        cutoff=cutoff,depart=depart,end=end,tasks=tasks,speed=speed,turn=turn,budget=budget)


def _run_prepared_route(context,result,*,remaining_state=None,work=None):
    """Internal v1 solver or explicit v2 entry state; inputs are already owned."""
    gi,decision,gp,policy,graph,count,depart,end,tasks,speed,turn,budget=(context[k] for k in
        ('gi','decision','gp','policy','graph','count','depart','end','tasks','speed','turn','budget'))
    caps=policy['capacities'];previous=''
    if remaining_state is not None:
        result.update(schema_version='habu-conditional-route-remaining-result-v2',
            original_decision_input_sha256=_seal(decision,budget,caps['max_json_bytes']),
            remaining_entry_state={**remaining_state,'depart':_utc(remaining_state['depart']),
                'end':_utc(remaining_state['end'])})
        decision=dict(decision,start_node_id=remaining_state['node_id'],
            depart_at=_utc(remaining_state['depart']),time_budget_seconds=remaining_state['remaining_budget_seconds'])
        depart=remaining_state['depart'];end=remaining_state['end'];previous=remaining_state['incoming_edge_id']
    engine=_Engine(graph,decision,policy,tasks,count['unit_predictions'],speed,turn,depart,end,budget,
        initial_previous=previous,work=work)
    context['_last_engine']=engine
    pool=engine.search();routes,missing=engine.choose(pool)
    result.update(execution_status='PARTIAL_RESEARCH_ONLY' if engine.exhausted and routes else 'COMPUTED_RESEARCH_ONLY' if routes else 'NO_FEASIBLE_CANDIDATE',
        routes=routes,expected_captures=routes[0]['expected_captures'] if routes else None,
        blockers=sorted(set(engine.blockers)),search_exhausted=engine.exhausted,work=dict(engine.work),
        feasibility_reasons=sorted(engine.reasons),missing_alternatives=missing,found_candidate_count=len(pool),
        graph_status=graph['status'],graph_diagnostics=graph['diagnostics'],native_count_status=count['status'],
        native_bindings=dict(graph_sha256=graph['graph_sha256'],graph_policy_sha256=digest(gp),
            unit_prediction_sha256=count['unit_prediction_sha256'],aggregate_prediction_sha256=count['aggregate_prediction']['prediction_sha256'],
            model_sha256=count['lineage']['model_sha256'],count_protocol_sha256=count['lineage']['protocol_sha256'],
            planned_source_sha256=count['lineage']['planned_source_sha256'],
            links_source_sha256=decision['links_source']['sha256'],travel_profile_source_sha256=decision['travel_profile_source']['sha256'],
            route_policy_sha256=digest(policy),decision_input_sha256=_seal(decision,budget,caps['max_json_bytes'])),
        unmet_requirements=sorted(set(graph['missing_requirements']+['ACTUAL_UNCERTAINTY_METADATA_NOT_AVAILABLE','AUTHENTICATED_OWNER_INTENT','REAL_ROUTE_BENEFIT_NOT_VALIDATED'])),
        scenario_sensitivity=dict(status='NOT_COMPUTED',reason='ADDITIONAL_REGISTERED_SPEED_SCENARIOS_NOT_SUPPLIED'),
        assumptions=['DECLARED_SPEED_AND_STATIONARY_NODE_SEARCH_SCENARIO_NOT_MEASURED',
            'CONDITIONAL_SUBSET_OF_COMPLETE_UNCHANGED_ORIGINAL_PLAN_NOT_NEW_OWNER_INTENT',
            'KNOWN_NATIVE_RESTRICTIONS_ONLY_NOT_AUTHENTICATED_COMPLETE_NAVIGATION',
            'SHARED_GAMMA_RATE_NO_SPATIAL_DIFFERENTIATION_OR_SUMMED_MARGINAL_INTERVALS',
            'BOUNDED_HEURISTIC_NOT_GLOBAL_OPTIMUM'],omitted_operational_fields=['runtime_elapsed_seconds'])
    result['route_prediction_sha256']=_seal(result,budget,caps['max_json_bytes'])
    result['runtime_elapsed_seconds']=time.monotonic()-budget.start
    _graph_owned(result,budget,max_nodes=caps['max_json_nodes'],max_bytes=caps['max_json_bytes']);budget.check()
    return result


def plan_route_candidates(graph_input,decision_input,*,graph_policy,policy,budget_seconds=30):
    result=_empty()
    try:
        budget=_Budget(budget_seconds)
        context=_prepare_route_context(graph_input,decision_input,graph_policy,policy,budget,result)
        _run_prepared_route(context,result)
    except _Missing as exc:result.update(execution_status='DATA_BLOCKED',blockers=[str(exc)])
    except _Unsupported as exc:result.update(execution_status='IMPLEMENTATION_BLOCKED',blockers=[str(exc)])
    except (_Capacity,_GraphCapacity,CountActivityCapacityError) as exc:
        code=str(exc)
        result.update(execution_status='RUNTIME_BLOCKED',blockers=[code if re.fullmatch('[A-Z][A-Z0-9_]{0,127}',code) else 'RUNTIME_OR_RESOURCE_CAPACITY_EXCEEDED'])
    except (_Invalid,_GraphInvalid):result.update(execution_status='FAIL',blockers=['SOURCE_OR_POLICY_CONTRACT_INVALID'])
    except (ValueError,TypeError,KeyError,IndexError,OverflowError,RecursionError,UnicodeError):
        result.update(execution_status='FAIL',blockers=['SOURCE_OR_POLICY_CONTRACT_INVALID'])
    if result['execution_status'] in ('FAIL','DATA_BLOCKED','IMPLEMENTATION_BLOCKED','RUNTIME_BLOCKED'):
        result.update(routes=[],expected_captures=None);result.pop('route_prediction_sha256',None)
    return result
