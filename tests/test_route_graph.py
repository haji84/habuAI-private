"""Synthetic source-bound topology controls; no actual GPS or capture inputs."""
import copy
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def node(i, x, y, **extra):
    return dict(type='node', id=i, version=1, lon=129+x/1000, lat=28+y/1000, **extra)


def way(i, ids, **tags):
    return dict(type='way', id=i, version=1, nodes=ids,
                tags={'highway':'residential', 'motor_vehicle':'yes', **tags})


def fixture(elements=None):
    policy = dict(schema_version='habu-route-graph-policy-v1', mode='motor_vehicle',
        access_precedence=['motor_vehicle','vehicle','access'], allow_values=['yes','permissive'],
        deny_values=['no','private'], barrier_pass_values=['yes'],
        unknown_access_policy='PRESERVE_UNKNOWN', unsupported_semantics='QUARANTINE',
        geometry_tolerance_degrees=1e-11,
        capacities=dict(max_sources=30,max_source_bytes=2000000,max_total_source_bytes=16000000,
            max_elements=100000,max_nodes=80000,max_ways=20000,max_references=200000,
            max_edges=200000,max_transitions=200000,max_polygon_vertices=1000,
            max_geometry_candidates=1000000,max_geometry_index_entries=2000000,
            max_json_nodes=2000000,max_json_bytes=24000000,max_seconds=30))
    polygon=[[[128.99,27.99],[129.01,27.99],[129.01,28.01],[128.99,28.01],[128.99,27.99]]]
    domain=dict(crs='EPSG:4326',polygons=[polygon])
    domain['sha256']=digest(domain)
    context=dict(operational_night='2026-11-04',cutoff_time='2026-11-04T18:00:00+09:00',
                 forecast_start='2026-11-04T18:00:00+09:00',forecast_end='2026-11-05T01:00:00+09:00',mode='motor_vehicle')
    data=dict(schema_version='habu-route-graph-input-v1', sources=[],domain=domain,context=context,
              coverage={},closures=[],policy_sha256=digest(policy))
    for key in ('turn_restrictions','current_access','closures'):
        data['coverage'][key]=dict(status='UNKNOWN',source_sha256s=[],domain_sha256=domain['sha256'],
            mode='motor_vehicle',valid_start=context['forecast_start'],valid_end=context['forecast_end'],available_at=None)
    put_source(data,elements or [node(1,-1,0),node(2,1,0),way(10,[1,2])])
    return data, policy


def put_source(data, elements, *, text=None):
    raw=text if text is not None else json.dumps({'version':0.6,'elements':elements},ensure_ascii=False)
    data['sources']=[dict(raw_json_utf8=raw,sha256=hashlib.sha256(raw.encode()).hexdigest(),
        size_bytes=len(raw.encode()),available_at='2026-11-04T16:00:00+09:00',availability_basis='ACTUAL_LOCAL_MATERIALIZATION')]


def change_domain(data, polygons):
    data['domain']={'crs':'EPSG:4326','polygons':polygons}
    data['domain']['sha256']=digest(data['domain'])
    for claim in data['coverage'].values(): claim['domain_sha256']=data['domain']['sha256']


class RouteGraphTests(unittest.TestCase):
    def build(self, data, policy, **kwargs):
        try: module=importlib.import_module('route_graph')
        except ModuleNotFoundError: self.fail('route_graph implementation is absent')
        return module.build_route_graph(data,policy=policy,**kwargs)

    def test_basic_graph_is_source_bound_without_authority(self):
        data,p=fixture(); original=copy.deepcopy((data,p)); r=self.build(data,p)
        self.assertEqual(r['status'],'GRAPH_BUILT_RESEARCH_ONLY')
        self.assertEqual(len(r['edges']),2); self.assertEqual(len(r['nodes']),2)
        self.assertEqual(r['navigation_status'],'NAVIGATION_BLOCKED')
        self.assertFalse(r['production_authorized']); self.assertFalse(r['official_issuance_authorized'])
        self.assertEqual(r['source_authenticity'],'NOT_ATTESTED')
        self.assertEqual(r['source_refs'][0]['sha256'],data['sources'][0]['sha256'])
        self.assertEqual((data,p),original)

    def test_crossings_and_same_coordinates_never_join_distinct_nodes(self):
        data,p=fixture([node(1,-1,0),node(2,1,0),node(3,0,-1),node(4,0,1),
                        way(10,[1,2],bridge='yes',layer='1'),way(11,[3,4],tunnel='yes',layer='-1')])
        r=self.build(data,p); self.assertEqual(len(r['nodes']),4)
        self.assertEqual({e['from_node'] for e in r['edges']},{'osm:1','osm:2','osm:3','osm:4'})
        self.assertFalse(r['transition_constraints'])

    def test_real_shared_node_ramp_keeps_topology_but_marks_uncertain_transition(self):
        data,p=fixture([node(1,-1,0),node(2,0,0),node(3,1,0),way(10,[1,2],layer='0'),way(11,[2,3],layer='1',bridge='yes')])
        r=self.build(data,p); self.assertEqual(len(r['nodes']),3)
        self.assertTrue(any(x['reason']=='STRUCTURAL_TRANSITION_UNVERIFIED' for x in r['diagnostics']))

    def test_missing_middle_node_never_bridges(self):
        data,p=fixture([node(1,-1,0),node(3,1,0),way(10,[1,2,3])]); r=self.build(data,p)
        self.assertEqual(r['edges'],[]); self.assertEqual(r['status'],'PARTIAL')
        self.assertTrue(any(x['reason']=='MISSING_NODE' for x in r['diagnostics']))

    def test_versions_select_highest_and_reject_equal_conflict(self):
        elems=[node(1,-1,0),node(2,1,0),way(10,[1,2])]
        newer=copy.deepcopy(elems[0]); newer['version']=2; newer['lon']+=.001
        data,p=fixture(elems+[newer]); r=self.build(data,p)
        self.assertEqual(next(n for n in r['nodes'] if n['node_id']=='osm:1')['version'],2)
        newer['version']=1; put_source(data,elems+[newer])
        self.assertIn(self.build(data,p)['status'], ('FAIL','CAPACITY_EXCEEDED'))

    def test_missing_version_is_unknown_and_mixed_version_quarantines(self):
        elems=[node(1,-1,0),node(2,1,0),way(10,[1,2])]; del elems[0]['version']
        data,p=fixture(elems); r=self.build(data,p)
        self.assertIsNone(next(n for n in r['nodes'] if n['node_id']=='osm:1')['version'])
        self.assertEqual(r['status'],'PARTIAL')
        elems.append(node(1,-1,0)); put_source(data,elems); r=self.build(data,p)
        self.assertEqual(r['edges'],[])

    def test_boolean_id_and_coercible_version_rejected(self):
        for key,value in [('id',True),('version','1'),('version',False)]:
            with self.subTest(key=key,value=value):
                elems=[node(1,-1,0),node(2,1,0),way(10,[1,2])]; elems[0][key]=value
                data,p=fixture(elems)
                self.assertIn(self.build(data,p)['status'], ('FAIL','CAPACITY_EXCEEDED'))

    def test_reverse_oneway_roundabout_and_parallel_identity(self):
        data,p=fixture([node(1,-1,0),node(2,1,0),way(10,[1,2],oneway='-1'),way(11,[1,2],junction='roundabout')])
        r=self.build(data,p); self.assertEqual(len(r['edges']),2)
        ways={w['way_ref']:w for w in r['ways']}
        edges={ways[e['way_ref']]['way_id']:e for e in r['edges']}
        self.assertEqual(edges[10]['from_node'],'osm:2'); self.assertEqual(edges[11]['from_node'],'osm:1')

    def test_access_denied_unknown_and_barrier(self):
        for tags in ({'motor_vehicle':'no'},{'motor_vehicle':'private'}):
            data,p=fixture([node(1,-1,0),node(2,1,0),way(10,[1,2],**tags)])
            self.assertEqual(self.build(data,p)['edges'],[])
        data,p=fixture(); elems=json.loads(data['sources'][0]['raw_json_utf8'])['elements']; elems[-1]['tags']={'highway':'residential'}
        put_source(data,elems); r=self.build(data,p)
        self.assertTrue(all(e['access_status']=='UNKNOWN' for e in r['edges']))
        elems[0]['tags']={'barrier':'gate'}; put_source(data,elems)
        self.assertEqual(self.build(data,p)['edges'],[])

    def test_unsupported_conditional_direction_and_ferry_quarantine(self):
        for tags in ({'access:conditional':'no @ (wet)'},{'oneway':'reversible'},{'route':'ferry'}):
            data,p=fixture([node(1,-1,0),node(2,1,0),way(10,[1,2],**tags)])
            r=self.build(data,p); self.assertEqual(r['edges'],[]); self.assertEqual(r['status'],'PARTIAL')

    def restriction(self, kind='no_left_turn', **tags):
        return dict(type='relation',id=20,version=1,tags={'type':'restriction','restriction':kind,**tags},members=[
            {'type':'way','ref':10,'role':'from'},{'type':'node','ref':2,'role':'via'},{'type':'way','ref':11,'role':'to'}])

    def test_no_and_only_turn_constraints_bind_directed_edges(self):
        for kind,rule in [('no_left_turn','NO'),('only_right_turn','ONLY')]:
            data,p=fixture([node(1,-1,0),node(2,0,0),node(3,0,1),way(10,[1,2]),way(11,[2,3]),self.restriction(kind)])
            r=self.build(data,p); c=r['transition_constraints'][0]
            self.assertEqual(c['rule'],rule); self.assertEqual(c['via_node'],'osm:2')
            self.assertEqual(len(c['from_edges']),1); self.assertEqual(len(c['to_edges']),1)

    def test_restriction_except_or_via_way_is_blocked_not_ignored(self):
        for rel in [self.restriction(**{'except':'motorcar'}),self.restriction()]:
            if 'except' not in rel['tags']: rel['members'][1]['type']='way'
            data,p=fixture([node(1,-1,0),node(2,0,0),node(3,0,1),way(10,[1,2]),way(11,[2,3]),rel])
            r=self.build(data,p); self.assertEqual(r['status'],'PARTIAL')
            self.assertTrue(any(x['reason']=='UNSUPPORTED_RESTRICTION' for x in r['diagnostics']))

    def test_clipping_outside_endpoints_creates_edge_local_boundaries(self):
        data,p=fixture([node(1,-20,0),node(2,20,0),way(10,[1,2]),way(11,[1,2])])
        r=self.build(data,p); self.assertEqual(len(r['edges']),4); self.assertEqual(len(r['nodes']),4)
        self.assertTrue(all(n['node_id'].startswith('boundary:') for n in r['nodes']))
        self.assertTrue(all(128.99<=n['longitude']<=129.01 for n in r['nodes']))
        self.assertTrue(all(e['length_m']>0 for e in r['edges']))

    def test_polygon_hole_splits_without_gap_bridge(self):
        data,p=fixture([node(1,-20,0),node(2,20,0),way(10,[1,2])])
        poly=data['domain']['polygons'][0]
        poly.append([[128.999,27.999],[129.001,27.999],[129.001,28.001],[128.999,28.001],[128.999,27.999]])
        change_domain(data,[poly]); r=self.build(data,p)
        self.assertEqual(len(r['edges']),4); self.assertEqual(len(r['nodes']),4)
        self.assertTrue(all(e['length_m']<1100 for e in r['edges']))

    def test_self_intersection_and_overlapping_polygons_are_unsupported(self):
        data,p=fixture()
        change_domain(data,[[[[128.99,27.99],[129.01,28.01],[129.01,27.99],[128.99,28.01],[128.99,27.99]]]])
        r=self.build(data,p); self.assertEqual(r['status'],'PARTIAL'); self.assertEqual(r['edges'],[])

    def test_closure_bindings_and_cutoff(self):
        data,p=fixture()
        closure=dict(source_sha256=data['sources'][0]['sha256'],target_type='way',target_id=10,
            valid_start=data['context']['forecast_start'],valid_end=data['context']['forecast_end'],
            available_at='2026-11-04T17:00:00+09:00',mode='motor_vehicle',status='CLOSED')
        data['closures']=[closure]; self.assertEqual(self.build(data,p)['edges'],[])
        closure['available_at']=data['context']['cutoff_time']
        self.assertEqual(self.build(data,p)['status'],'DATA_BLOCKED')

    def test_source_hash_size_missing_readiness_and_cutoff(self):
        for field,value in [('sha256','0'*64),('size_bytes',1)]:
            data,p=fixture(); data['sources'][0][field]=value
            self.assertIn(self.build(data,p)['status'], ('FAIL','CAPACITY_EXCEEDED'))
        for value in [None,'2026-11-04T18:00:00+09:00']:
            data,p=fixture(); data['sources'][0]['available_at']=value
            self.assertEqual(self.build(data,p)['status'],'DATA_BLOCKED')

    def test_duplicate_raw_keys_nonfinite_and_scope_hash(self):
        for raw in ['{"elements":[],"elements":[]}','{"elements":[],"x":NaN}']:
            data,p=fixture(); put_source(data,[],text=raw)
            self.assertIn(self.build(data,p)['status'], ('FAIL','CAPACITY_EXCEEDED'))
        for field in ['policy_sha256','domain']:
            data,p=fixture()
            if field=='domain': data['domain']['sha256']='0'*64
            else: data[field]='0'*64
            self.assertIn(self.build(data,p)['status'], ('FAIL','CAPACITY_EXCEEDED'))

    def test_coverage_self_claim_never_promotes_navigation(self):
        data,p=fixture()
        for c in data['coverage'].values():
            c.update(status='DECLARED_COMPLETE',source_sha256s=[data['sources'][0]['sha256']],available_at='2026-11-04T17:00:00+09:00')
        r=self.build(data,p); self.assertEqual(r['navigation_status'],'NAVIGATION_BLOCKED')
        self.assertFalse(r['production_authorized'])

    def test_capacity_huge_budget_nonfinite_and_no_custom_callbacks(self):
        data,p=fixture()
        for b in [True,10**10000,float('nan'),float('inf'),0,-1]:
            with self.subTest(kind=type(b).__name__):
                self.assertIn(self.build(data,p,budget_seconds=b)['status'], ('FAIL','CAPACITY_EXCEEDED'))
        p['capacities']['max_nodes']=1; data['policy_sha256']=digest(p)
        self.assertIn(self.build(data,p)['status'], ('FAIL','CAPACITY_EXCEEDED'))
        calls=[]
        class M(type):
            def __eq__(self,other): calls.append('eq'); return False
            def __hash__(self): calls.append('hash'); return 1
        class Bad(metaclass=M): pass
        data,p=fixture(); data['sources']=Bad()
        self.assertIn(self.build(data,p)['status'], ('FAIL','CAPACITY_EXCEEDED'))
        self.assertEqual(calls,[])

    def test_canonical_hash_order_and_deadline(self):
        data,p=fixture(); second=copy.deepcopy(data['sources'][0]); second['raw_json_utf8']=' '+second['raw_json_utf8']
        second['sha256']=hashlib.sha256(second['raw_json_utf8'].encode()).hexdigest(); second['size_bytes']+=1
        data['sources'].append(second); first=self.build(data,p)
        data['sources'].reverse(); self.assertEqual(self.build(data,p)['graph_sha256'],first['graph_sha256'])
        self.assertEqual(self.build(data,p,budget_seconds=1e-12)['status'],'CAPACITY_EXCEEDED')

    def test_malformed_closed_nested_values_do_not_escape_type_errors(self):
        mutations=[lambda d,p:d['coverage']['closures'].update(source_sha256s=[{}]),
            lambda d,p:d['context'].update(mode=[]),
            lambda d,p:d['domain'].update(polygons=[None]),
            lambda d,p:d['closures'].append({'source_sha256':[]}),
            lambda d,p:p.update(access_precedence=[[]]),
            lambda d,p:d['sources'][0].update(availability_basis=[])]
        for mutate in mutations:
            data,p=fixture(); mutate(data,p); data['policy_sha256']=digest(p)
            with self.subTest(index=mutations.index(mutate)):
                r=self.build(data,p); self.assertIn(r['status'],('FAIL','DATA_BLOCKED'))

    def test_huge_raw_integer_and_deep_raw_input_return_sanitized_status(self):
        for raw in ['{"elements":[],"value":'+('9'*5000)+'}',
                    '{"elements":[],"value":'+('['*40)+'0'+(']'*40)+'}']:
            data,p=fixture(); put_source(data,[],text=raw)
            r=self.build(data,p); self.assertIn(r['status'],('FAIL','CAPACITY_EXCEEDED'))
            self.assertLess(len(json.dumps(r)),1000)

    def test_node_conditional_access_cannot_be_silently_permissive(self):
        data,p=fixture([node(1,-1,0,tags={'access:conditional':'no @ (wet)'}),node(2,1,0),way(10,[1,2])])
        r=self.build(data,p); self.assertEqual(r['edges'],[])
        self.assertTrue(any(x['reason']=='NODE_CONDITIONAL_UNSUPPORTED' for x in r['diagnostics']))

    def test_duplicate_source_and_unbound_coverage_fail_closed(self):
        data,p=fixture(); data['sources'].append(copy.deepcopy(data['sources'][0]))
        self.assertEqual(self.build(data,p)['status'],'FAIL')
        data,p=fixture(); data['coverage']['closures']['source_sha256s']=['a'*64]
        self.assertEqual(self.build(data,p)['status'],'FAIL')

    def test_collinear_boundary_is_quarantined_and_zero_area_domain_partial(self):
        data,p=fixture([node(1,-20,-10),node(2,20,-10),way(10,[1,2])])
        r=self.build(data,p); self.assertEqual(r['status'],'PARTIAL'); self.assertEqual(r['edges'],[])
        change_domain(data,[[[[129,28],[129.001,28],[129.002,28],[129,28]]]])
        r=self.build(data,p); self.assertEqual(r['status'],'PARTIAL'); self.assertEqual(r['edges'],[])

    def test_layer_difference_does_not_remove_node_and_high_degree_restrictions_bounded(self):
        data,p=fixture([node(1,-1,0),node(2,0,0),node(3,1,0),way(10,[1,2,1,2]),way(11,[2,3,2,3]),self.restriction()])
        p['capacities']['max_transitions']=1; data['policy_sha256']=digest(p)
        self.assertEqual(self.build(data,p)['status'],'CAPACITY_EXCEEDED')

    def test_cycles_nonfinite_coordinates_and_naive_time_fail_closed(self):
        data,p=fixture(); data['closures'].append(data)
        self.assertEqual(self.build(data,p)['status'],'FAIL')
        data,p=fixture(); data['domain']['polygons'][0][0][0][0]=float('nan')
        self.assertEqual(self.build(data,p)['status'],'FAIL')
        data,p=fixture(); data['sources'][0]['available_at']='2026-11-04T12:00:00'
        self.assertEqual(self.build(data,p)['status'],'FAIL')

    def test_empty_source_elements_are_not_fabricated(self):
        data,p=fixture(); put_source(data,[])
        r=self.build(data,p); self.assertEqual(r['edges'],[]); self.assertEqual(r['nodes'],[])
        self.assertEqual(r['summary']['selected_elements'],0)

    def test_u_turn_constraint_does_not_prohibit_straight_continuation(self):
        rel=self.restriction('no_u_turn'); rel['members'][2]['ref']=10
        data,p=fixture([node(1,-1,0),node(2,0,0),node(3,1,0),way(10,[1,2,3]),rel])
        r=self.build(data,p); edges={e['edge_id']:e for e in r['edges']}
        self.assertEqual(len(r['transition_constraints']),2)
        for c in r['transition_constraints']:
            self.assertEqual(len(c['from_edges']),1); self.assertEqual(len(c['to_edges']),1)
            before=edges[c['from_edges'][0]]; after=edges[c['to_edges'][0]]
            self.assertEqual(before['from_node'],after['to_node'])

    def test_non_highway_and_unsupported_mode_do_not_acquire_road_semantics(self):
        data,p=fixture(); elements=json.loads(data['sources'][0]['raw_json_utf8'])['elements']
        elements[-1]['tags']={'building':'yes','motor_vehicle':'yes'}; put_source(data,elements)
        self.assertEqual(self.build(data,p)['edges'],[])
        data,p=fixture(); p['mode']='foot'; p['access_precedence']=['foot','access']; data['context']['mode']='foot'
        data['policy_sha256']=digest(p)
        self.assertEqual(self.build(data,p)['status'],'DATA_BLOCKED')

    def test_scoped_directional_exceptions_not_silently_discarded(self):
        for tags in [{'oneway:motor_vehicle':'no','oneway':'yes'}, {'motor_vehicle:forward':'no'}]:
            data,p=fixture([node(1,-1,0),node(2,1,0),way(10,[1,2],**tags)])
            r=self.build(data,p); self.assertEqual(r['edges'],[]); self.assertEqual(r['status'],'PARTIAL')

    def test_large_exact_ring_is_indexed_without_simplification(self):
        data,p=fixture(); count=10000
        ring=[[129+.005*math.cos(i*2*math.pi/count),28+.005*math.sin(i*2*math.pi/count)] for i in range(count)]
        ring.append(ring[0]); change_domain(data,[[ring]])
        p['capacities']['max_polygon_vertices']=11000; data['policy_sha256']=digest(p)
        r=self.build(data,p,budget_seconds=5)
        self.assertEqual(r['status'],'GRAPH_BUILT_RESEARCH_ONLY'); self.assertEqual(len(r['edges']),2)
        self.assertEqual(r['domain_sha256'],data['domain']['sha256'])

    def test_geometry_candidate_capacity_is_explicit(self):
        data,p=fixture(); p['capacities']['max_geometry_candidates']=1;data['policy_sha256']=digest(p)
        self.assertEqual(self.build(data,p)['status'],'CAPACITY_EXCEEDED')

    def test_unrepresentable_night_boundary_is_structured_failure(self):
        data,p=fixture(); data['context'].update(operational_night='9999-12-31',
            cutoff_time='9999-12-31T18:00:00+09:00',forecast_start='9999-12-31T18:00:00+09:00',forecast_end='9999-12-31T23:00:00+09:00')
        self.assertEqual(self.build(data,p)['status'],'FAIL')

    def test_json_capacity_reason_identifies_the_actual_bound(self):
        data,p=fixture();p['capacities']['max_json_nodes']=1;data['policy_sha256']=digest(p)
        r=self.build(data,p);self.assertEqual(r['status'],'CAPACITY_EXCEEDED')
        self.assertEqual(r['reason'],'JSON_NODE_CAPACITY')

    def test_holes_nested_and_disjoint_polygon_islands_remain_explicit(self):
        data,p=fixture([node(1,-20,0),node(2,20,0),way(10,[1,2])])
        left=[[[128.99,27.99],[128.999,27.99],[128.999,28.01],[128.99,28.01],[128.99,27.99]]]
        right=[[[129.001,27.99],[129.01,27.99],[129.01,28.01],[129.001,28.01],[129.001,27.99]]]
        change_domain(data,[left,right]);r=self.build(data,p)
        self.assertEqual(len(r['edges']),4)
        self.assertEqual(len(r['nodes']),4)
        poly=fixture()[0]['domain']['polygons'][0]
        poly.extend([[[128.999,27.999],[129.001,27.999],[129.001,28.001],[128.999,28.001],[128.999,27.999]],
                     [[128.9995,27.9995],[129.0005,27.9995],[129.0005,28.0005],[128.9995,28.0005],[128.9995,27.9995]]])
        change_domain(data,[poly]);r=self.build(data,p)
        self.assertEqual(r['status'],'PARTIAL');self.assertEqual(r['edges'],[])

    def test_way_metadata_is_losslessly_stored_once_not_per_edge(self):
        elements=[node(i,i/100,0) for i in range(1,101)]
        tags={'name':'SYNTHETIC_'*100,'surface':'asphalt','bridge':'yes','layer':'1'}
        elements.append(way(900,list(range(1,101)),**tags))
        data,p=fixture(elements);r=self.build(data,p)
        self.assertEqual(len(r.get('ways',[])),1)
        saved=r['ways'][0]
        self.assertEqual(saved['tags'],elements[-1]['tags'])
        self.assertEqual(saved['source_sha256s'],[data['sources'][0]['sha256']])
        self.assertEqual(len(r['edges']),198)
        self.assertTrue(all(e['way_ref']==saved['way_ref'] and 'tags' not in e and 'source_sha256s' not in e for e in r['edges']))
        self.assertEqual(json.dumps(r).count('SYNTHETIC_'),100)


if __name__=='__main__': unittest.main()
