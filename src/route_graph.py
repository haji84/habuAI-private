"""Pure source-bound OSM research topology, never navigation authorization.

Public API accepts exact builtin JSON only. GraphInput has exactly schema_version,
sources, domain, context, coverage, closures, policy_sha256. Source records contain
raw_json_utf8/sha256/size_bytes/available_at/availability_basis. Domain is
{crs,polygons,sha256}, with polygons[outer_ring,hole,...] in longitude/latitude.
Its SHA covers crs/polygons, not an original boundary file. Context is
{operational_night,cutoff_time,forecast_start,forecast_end,mode}. Coverage has
turn_restrictions/current_access/closures, each scoped as documented in _coverage.
Policy fields are closed below; all capacities and access tokens are explicit.

Only node-via no/only relations are implemented. Unsupported grammar/geometry is
reported, never promoted to permissive navigation. No speeds, snapping, rewards,
model writes, filesystem reads, callbacks or transport are accepted. Availability
is checked for consistency, not authenticated. One deadline is cooperative; the
bounded builtin JSON parser cannot be preempted within a single parse operation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import time

from gpx_audit import utm52n


class _Invalid(ValueError):
    pass


class _Capacity(ValueError):
    pass


class _Blocked(ValueError):
    pass


class _Geometry(ValueError):
    pass


CEILINGS = dict(max_sources=128,max_source_bytes=4*1024**2,max_total_source_bytes=64*1024**2,
    max_elements=1000000,max_nodes=800000,max_ways=200000,max_references=2000000,
    max_edges=2000000,max_transitions=1000000,max_polygon_vertices=50000,
    max_geometry_candidates=10000000,max_geometry_index_entries=4000000,
    max_json_nodes=8000000,max_json_bytes=96*1024**2,max_seconds=300)
POLICY = {'schema_version','mode','access_precedence','allow_values','deny_values',
          'barrier_pass_values','unknown_access_policy','unsupported_semantics',
          'geometry_tolerance_degrees','capacities'}


def _raw(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


def _hash(value):
    return hashlib.sha256(_raw(value)).hexdigest()


def _fields(value,keys):
    if type(value) is not dict or set(value)!=set(keys): raise _Invalid('EXACT_FIELDS_REQUIRED')


def _int(value,minimum=1,maximum=2**63-1):
    if type(value) is not int or not minimum<=value<=maximum: raise _Invalid('INTEGER_RANGE')
    return value


def _number(value,low,high):
    kind=type(value)
    if (kind is not int and kind is not float) or not low<=value<=high: raise _Invalid('FINITE_NUMBER_RANGE')
    return float(value)


def _sha(value):
    if type(value) is not str or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
        raise _Invalid('SHA256_REQUIRED')
    return value


def _time(value):
    if type(value) is not str or len(value)>64 or 'T' not in value: raise _Invalid('AWARE_TIME_REQUIRED')
    try: result=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError: raise _Invalid('INVALID_TIME') from None
    if result.utcoffset() is None: raise _Invalid('AWARE_TIME_REQUIRED')
    return result


class _Budget:
    def __init__(self,seconds):
        seconds=_number(seconds,0,300)
        if seconds<=0: raise _Invalid('POSITIVE_BUDGET_REQUIRED')
        self.start=time.monotonic(); self.deadline=self.start+seconds
        self.geometry_count=0; self.geometry_limit=CEILINGS['max_geometry_candidates']

    def check(self):
        if time.monotonic()>=self.deadline: raise _Capacity('DEADLINE_EXCEEDED')

    def geometry(self):
        self.check(); self.geometry_count+=1
        if self.geometry_count>self.geometry_limit: raise _Capacity('GEOMETRY_CANDIDATE_CAPACITY')


def _owned(value,budget,*,max_nodes=8000000,max_bytes=96*1024**2,return_bytes=False):
    active=set(); nodes=0; size=0
    def visit(item,depth):
        nonlocal nodes,size
        budget.check(); nodes+=1; size+=8
        if nodes>max_nodes: raise _Capacity('JSON_NODE_CAPACITY')
        if depth>32: raise _Capacity('JSON_DEPTH_CAPACITY')
        if size>max_bytes: raise _Capacity('JSON_ESTIMATED_BYTE_CAPACITY')
        kind=type(item)
        if kind is dict or kind is list:
            if id(item) in active: raise _Invalid('CYCLIC_JSON')
            if len(item)>max_nodes: raise _Capacity('JSON_NODE_CAPACITY')
            active.add(id(item))
            if kind is dict:
                for k,v in item.items():
                    if type(k) is not str or len(k)>512: raise _Invalid('JSON_KEY')
                    visit(k,depth+1); visit(v,depth+1)
            else:
                for v in item: visit(v,depth+1)
            active.remove(id(item))
        elif kind is str:
            if len(item)>max_bytes: raise _Capacity('STRING_CAPACITY')
            try: size+=len(item.encode('utf-8'))
            except UnicodeEncodeError: raise _Invalid('INVALID_UNICODE') from None
        elif kind is int:
            if not -(2**63)<=item<2**63: raise _Invalid('INTEGER_RANGE')
        elif kind is float:
            if not math.isfinite(item): raise _Invalid('NONFINITE_JSON')
        elif kind is not bool and kind is not type(None): raise _Invalid('BUILTIN_JSON_REQUIRED')
    visit(value,0)
    if size>max_bytes: raise _Capacity('JSON_ESTIMATED_BYTE_CAPACITY')
    raw=_raw(value); budget.check()
    if len(raw)>max_bytes: raise _Capacity('JSON_BYTE_CAPACITY')
    return raw if return_bytes else json.loads(raw)


def _policy(value):
    _fields(value,POLICY)
    if value['schema_version']!='habu-route-graph-policy-v1': raise _Invalid('POLICY_VERSION')
    if value['mode'] not in ('motor_vehicle','motorcar'): raise _Blocked('MODE_SEMANTICS_UNIMPLEMENTED')
    if value['unknown_access_policy']!='PRESERVE_UNKNOWN' or value['unsupported_semantics']!='QUARANTINE':
        raise _Invalid('POLICY_SEMANTICS')
    for name in ('access_precedence','allow_values','deny_values','barrier_pass_values'):
        xs=value[name]
        if type(xs) is not list or not 0<len(xs)<=16: raise _Invalid('TOKEN_LIST')
        if any(type(x) is not str or not 0<len(x)<=64 for x in xs) or len(xs)!=len(set(xs)):
            raise _Invalid('TOKEN_LIST')
    if value['access_precedence'][0]!=value['mode'] or value['access_precedence'][-1]!='access':
        raise _Invalid('MODE_PRECEDENCE')
    if set(value['allow_values']) & set(value['deny_values']): raise _Invalid('ACCESS_CONTRADICTION')
    if not {'no','private'}<=set(value['deny_values']): raise _Invalid('DENY_POLICY_REQUIRED')
    _number(value['geometry_tolerance_degrees'],1e-13,1e-8)
    _fields(value['capacities'],CEILINGS)
    for key,ceiling in CEILINGS.items(): _int(value['capacities'][key],1,ceiling)
    return value


def _context(value,policy):
    _fields(value,{'operational_night','cutoff_time','forecast_start','forecast_end','mode'})
    if value['mode']!=policy['mode']: raise _Invalid('MODE_MISMATCH')
    night=value['operational_night']
    if type(night) is not str or len(night)!=10: raise _Invalid('NIGHT_REQUIRED')
    try: start=datetime.fromisoformat(night+'T07:00:00+09:00')
    except ValueError: raise _Invalid('INVALID_NIGHT') from None
    if start.date().isoformat()!=night: raise _Invalid('INVALID_NIGHT')
    if night=='9999-12-31': raise _Invalid('NIGHT_BOUNDARY_UNREPRESENTABLE')
    cutoff=_time(value['cutoff_time']); a=_time(value['forecast_start']); b=_time(value['forecast_end'])
    if not start<=cutoff<=a<b<=start+timedelta(days=1): raise _Invalid('FORECAST_SCOPE')
    return cutoff,a,b


def _pairs(pairs):
    result={}
    for k,v in pairs:
        if k in result: raise _Invalid('DUPLICATE_JSON_KEY')
        result[k]=v
    return result


def _constant(_):
    raise _Invalid('NONFINITE_JSON')


def _json_integer(token):
    if len(token)>20: raise _Invalid('RAW_INTEGER_CAPACITY')
    return _int(int(token),-(2**63),2**63-1)


def _parse(text,budget):
    depth=0; quoted=False; escaped=False
    for i,c in enumerate(text):
        if i%4096==0: budget.check()
        if quoted:
            if escaped: escaped=False
            elif c=='\\': escaped=True
            elif c=='"': quoted=False
        elif c=='"': quoted=True
        elif c in '[{':
            depth+=1
            if depth>32: raise _Capacity('RAW_JSON_DEPTH')
        elif c in ']}': depth-=1
    try: return json.loads(text,object_pairs_hook=_pairs,parse_constant=_constant,parse_int=_json_integer)
    except (json.JSONDecodeError,RecursionError): raise _Invalid('MALFORMED_SOURCE_JSON') from None


def _sources(sources,caps,cutoff,budget):
    if type(sources) is not list or not sources: raise _Blocked('SOURCE_MISSING')
    if len(sources)>caps['max_sources']: raise _Capacity('SOURCE_COUNT')
    refs=[]; all_elements=[]; total=0; hashes=set()
    for source in sources:
        budget.check()
        _fields(source,{'raw_json_utf8','sha256','size_bytes','available_at','availability_basis'})
        text=source['raw_json_utf8']
        if type(text) is not str: raise _Invalid('RAW_UTF8_REQUIRED')
        if len(text)>caps['max_source_bytes']: raise _Capacity('SOURCE_BYTES')
        raw=text.encode('utf-8'); total+=len(raw)
        if len(raw)>caps['max_source_bytes'] or total>caps['max_total_source_bytes']: raise _Capacity('SOURCE_BYTES')
        _int(source['size_bytes']); _sha(source['sha256'])
        if len(raw)!=source['size_bytes'] or hashlib.sha256(raw).hexdigest()!=source['sha256']:
            raise _Invalid('SOURCE_HASH_OR_SIZE_MISMATCH')
        if source['sha256'] in hashes: raise _Invalid('DUPLICATE_SOURCE')
        hashes.add(source['sha256'])
        if source['availability_basis'] not in ('ACTUAL_LOCAL_MATERIALIZATION','SOURCE_BOUND_RECEIPT'):
            raise _Blocked('AVAILABILITY_BASIS_UNSUPPORTED')
        if source['available_at'] is None or _time(source['available_at'])>=cutoff: raise _Blocked('SOURCE_NOT_BEFORE_CUTOFF')
        body=_parse(text,budget)
        body=_owned(body,budget,max_nodes=caps['max_json_nodes'],max_bytes=caps['max_json_bytes'])
        if type(body) is not dict or type(body.get('elements')) is not list: raise _Invalid('ELEMENTS_REQUIRED')
        if len(all_elements)+len(body['elements'])>caps['max_elements']: raise _Capacity('ELEMENT_COUNT')
        for element in body['elements']: all_elements.append((element,source['sha256']))
        refs.append({k:v for k,v in source.items() if k!='raw_json_utf8'})
    return all_elements,sorted(refs,key=lambda x:x['sha256']),hashes


def _coverage(value,hashes,domain,context,cutoff,a,b):
    _fields(value,{'turn_restrictions','current_access','closures'})
    for claim in value.values():
        _fields(claim,{'status','source_sha256s','domain_sha256','mode','valid_start','valid_end','available_at'})
        if claim['status'] not in ('UNKNOWN','DECLARED_COMPLETE'): raise _Invalid('COVERAGE_STATUS')
        refs=claim['source_sha256s']
        if type(refs) is not list or any(_sha(x) not in hashes for x in refs) or len(refs)!=len(set(refs)):
            raise _Invalid('COVERAGE_SOURCE')
        if claim['domain_sha256']!=domain['sha256'] or claim['mode']!=context['mode']:
            raise _Invalid('COVERAGE_SCOPE')
        if _time(claim['valid_start'])>a or _time(claim['valid_end'])<b: raise _Invalid('COVERAGE_TIME_SCOPE')
        if claim['available_at'] is not None and _time(claim['available_at'])>=cutoff:
            raise _Blocked('COVERAGE_NOT_BEFORE_CUTOFF')
        if claim['status']=='DECLARED_COMPLETE' and (not refs or claim['available_at'] is None):
            raise _Blocked('COVERAGE_PROOF_MISSING')


def _cross(a,b): return a[0]*b[1]-a[1]*b[0]
def _sub(a,b): return (a[0]-b[0],a[1]-b[1])


def _intersections(a,b,c,d,eps):
    """Segment parameter hits; None denotes overlapping/ambiguous collinearity."""
    r=_sub(b,a); s=_sub(d,c); q=_sub(c,a)
    lr=math.hypot(*r); ls=math.hypot(*s)
    if min(lr,ls)<=eps: raise _Geometry('DEGENERATE_SEGMENT')
    den=_cross(r,s)
    if abs(den)<=eps*max(lr,ls):
        if abs(_cross(q,r))<=eps*lr:
            t0=(q[0]*r[0]+q[1]*r[1])/(lr*lr)
            t1=t0+(s[0]*r[0]+s[1]*r[1])/(lr*lr)
            if max(min(t0,t1),0)<=min(max(t0,t1),1)+eps/lr: return None
        return []
    t=_cross(q,s)/den; u=_cross(q,r)/den
    if -eps/lr<=t<=1+eps/lr and -eps/ls<=u<=1+eps/ls: return [min(1.,max(0.,t))]
    return []


def _in_ring(point,ring,eps,segments=None,budget=None):
    x,y=point; inside=False
    for a,b in (zip(ring,ring[1:]) if segments is None else segments):
        if budget is not None: budget.geometry()
        dx=b[0]-a[0]; dy=b[1]-a[1]; length=math.hypot(dx,dy)
        if length<=eps: raise _Geometry('DEGENERATE_RING_EDGE')
        if abs(_cross(_sub(point,a),(dx,dy)))<=eps*length and min(a[0],b[0])-eps<=x<=max(a[0],b[0])+eps and min(a[1],b[1])-eps<=y<=max(a[1],b[1])+eps:
            return None
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]: inside=not inside
    return inside


class _GeometryIndex:
    """Lossless bbox candidate index. Cell width affects work, never geometry."""
    def __init__(self,polygons,rings,eps,caps,budget):
        self.polygons=polygons; self.rings=rings; self.eps=eps; self.budget=budget
        self.segments=[(a,b,r,i) for r,ring in enumerate(rings) for i,(a,b) in enumerate(zip(ring,ring[1:]))]
        xs=[p[0] for ring in rings for p in ring]; ys=[p[1] for ring in rings for p in ring]
        self.left=min(xs); self.bottom=min(ys)
        self.width=max(max(xs)-self.left,max(ys)-self.bottom)/max(1,math.ceil(math.sqrt(len(self.segments))*16))
        if self.width<=eps: raise _Geometry('DOMAIN_EXTENT_UNRESOLVED')
        self.grid={}; self.rows={}; entries=0
        self.ring_ids={id(ring):i for i,ring in enumerate(rings)}
        for i,(a,b,r,j) in enumerate(self.segments):
            budget.check(); x0,x1,y0,y1=self.range(a,b)
            entries+=(x1-x0+1)*(y1-y0+1)+(y1-y0+1)
            if entries>caps['max_geometry_index_entries']: raise _Capacity('GEOMETRY_INDEX_CAPACITY')
            for y in range(y0,y1+1):
                budget.check(); self.rows.setdefault((r,y),[]).append(i)
                for x in range(x0,x1+1): self.grid.setdefault((x,y),[]).append(i)
        self.entry_limit=caps['max_geometry_index_entries']

    def range(self,a,b):
        eps=self.eps; width=self.width
        return (math.floor((min(a[0],b[0])-eps-self.left)/width),math.floor((max(a[0],b[0])+eps-self.left)/width),
                math.floor((min(a[1],b[1])-eps-self.bottom)/width),math.floor((max(a[1],b[1])+eps-self.bottom)/width))

    def query(self,a,b):
        x0,x1,y0,y1=self.range(a,b)
        if (x1-x0+1)*(y1-y0+1)>self.entry_limit: raise _Capacity('GEOMETRY_QUERY_CAPACITY')
        seen=set()
        for y in range(y0,y1+1):
            self.budget.check()
            for x in range(x0,x1+1):
                for i in self.grid.get((x,y),()):
                    if i not in seen:
                        seen.add(i);self.budget.geometry();yield i

    def in_ring(self,point,ring):
        row=math.floor((point[1]-self.bottom)/self.width); rid=self.ring_ids[id(ring)]
        ids=self.rows.get((rid,row),())
        return _in_ring(point,ring,self.eps,((self.segments[i][0],self.segments[i][1]) for i in ids),self.budget)


def _domain(value,caps,eps,budget):
    _fields(value,{'crs','polygons','sha256'})
    if value['crs']!='EPSG:4326' or _sha(value['sha256'])!=_hash({k:value[k] for k in ('crs','polygons')}):
        raise _Invalid('DOMAIN_HASH_OR_CRS')
    polygons=value['polygons']; total=0; rings=[]
    if type(polygons) is not list or not polygons: raise _Invalid('DOMAIN_POLYGONS')
    for polygon in polygons:
        if type(polygon) is not list or not polygon: raise _Invalid('DOMAIN_RINGS')
        for ring in polygon:
            if type(ring) is not list or len(ring)<4: raise _Invalid('DOMAIN_RING')
            total+=len(ring)
            if total>caps['max_polygon_vertices']: raise _Capacity('POLYGON_CAPACITY')
            for point in ring:
                if type(point) is not list or len(point)!=2: raise _Invalid('DOMAIN_POINT')
                _number(point[0],126,132); _number(point[1],0,84)
            if ring[0]!=ring[-1]: raise _Invalid('RING_NOT_CLOSED')
            origin=ring[0]
            twice_area=sum(_cross(_sub(a,origin),_sub(b,origin)) for a,b in zip(ring,ring[1:]))
            perimeter=sum(math.dist(a,b) for a,b in zip(ring,ring[1:]))
            if abs(twice_area)<=eps*perimeter: raise _Geometry('ZERO_OR_UNRESOLVED_RING_AREA')
            for a,b in zip(ring,ring[1:]):
                if math.dist(a,b)<=eps: raise _Geometry('DEGENERATE_RING_EDGE')
            rings.append(ring)
    index=_GeometryIndex(polygons,rings,eps,caps,budget)
    # Preserve every exact intersection test, limiting candidates by bbox only.
    for i,(a,b,r,j) in enumerate(index.segments):
        for k in index.query(a,b):
            if k<=i: continue
            c,d,s,t=index.segments[k]
            if r==s and (abs(j-t)==1 or {j,t}=={0,len(rings[r])-2}): continue
            hit=_intersections(a,b,c,d,eps)
            if hit is None or hit: raise _Geometry('SELF_INTERSECTING_RING' if r==s else 'INTERSECTING_DOMAIN_RINGS')
    for polygon in polygons:
        for hole in polygon[1:]:
            if index.in_ring(hole[0],polygon[0]) is not True: raise _Geometry('HOLE_OUTSIDE_OUTER')
        for i,hole in enumerate(polygon[1:]):
            for other in polygon[i+2:]:
                budget.check()
                if index.in_ring(hole[0],other) or index.in_ring(other[0],hole): raise _Geometry('NESTED_HOLES')
    for i,poly in enumerate(polygons):
        for other in polygons[i+1:]:
            budget.check()
            if _inside(poly[0][0],index,eps,[other]) or _inside(other[0][0],index,eps,[poly]): raise _Geometry('OVERLAPPING_POLYGONS')
    return index


def _inside(point,index,eps,polygons=None):
    for polygon in index.polygons if polygons is None else polygons:
        outer=index.in_ring(point,polygon[0])
        if outer is None: raise _Geometry('BOUNDARY_AMBIGUOUS')
        if outer:
            for hole in polygon[1:]:
                inside=index.in_ring(point,hole)
                if inside is None: raise _Geometry('BOUNDARY_AMBIGUOUS')
                if inside: break
            else: return True
    return False


def _clip(a,b,polygons,eps,budget):
    length=math.dist(a,b)
    if length<=eps: raise _Geometry('DEGENERATE_WAY_SEGMENT')
    hits=[0.,1.]
    for i in polygons.query(a,b):
        c,d,_,_=polygons.segments[i]; result=_intersections(a,b,c,d,eps)
        if result is None: raise _Geometry('COLLINEAR_DOMAIN_BOUNDARY')
        hits.extend(result)
    hits.sort(); unique=[]
    for t in hits:
        if not unique or (t-unique[-1])*length>eps: unique.append(t)
    intervals=[]
    for lo,hi in zip(unique,unique[1:]):
        mid=(lo+hi)/2
        if _inside((a[0]+(b[0]-a[0])*mid,a[1]+(b[1]-a[1])*mid),polygons,eps): intervals.append((lo,hi))
    return intervals


def _elements(items,caps,budget,diagnostics):
    groups={}; references=0
    for element,source in items:
        budget.check()
        if type(element) is not dict or element.get('type') not in ('node','way','relation'): raise _Invalid('ELEMENT_TYPE')
        kind=element['type']; ident=_int(element.get('id'))
        version=element.get('version')
        if version is not None: _int(version)
        if 'version' in element and version is None: raise _Invalid('NULL_VERSION')
        tags=element.get('tags',{})
        if type(tags) is not dict or any(type(k) is not str or type(v) is not str for k,v in tags.items()): raise _Invalid('OSM_TAGS')
        if kind=='node':
            _number(element.get('lon'),-180,180); _number(element.get('lat'),-90,90)
        elif kind=='way':
            ids=element.get('nodes')
            if type(ids) is not list or len(ids)<2: raise _Invalid('WAY_NODES')
            for value in ids: _int(value)
            references+=len(ids)
        else:
            members=element.get('members')
            if type(members) is not list: raise _Invalid('RELATION_MEMBERS')
            references+=len(members)
            for member in members:
                _fields(member,{'type','ref','role'}); _int(member['ref'])
                if member['type'] not in ('node','way','relation') or type(member['role']) is not str: raise _Invalid('RELATION_MEMBER')
        if references>caps['max_references']: raise _Capacity('REFERENCE_CAPACITY')
        groups.setdefault((kind,ident),[]).append((element,source))
    selected={}
    for key,records in sorted(groups.items()):
        budget.check(); versions={e.get('version') for e,s in records}
        if None in versions and len(versions)>1:
            diagnostics.append(dict(reason='UNKNOWN_VERSION_CONFLICT',element_type=key[0],element_id=key[1])); continue
        by_version={}
        for e,s in records:
            v=e.get('version'); body=_raw(e)
            if v in by_version and by_version[v][0]!=body: raise _Invalid('EQUAL_VERSION_CONFLICT')
            by_version[v]=(body,e)
        version=None if versions=={None} else max(versions)
        element=by_version[version][1]
        selected[key]=(element,sorted({s for e,s in records if e.get('version')==version}))
        if version is None: diagnostics.append(dict(reason='VERSION_UNKNOWN',element_type=key[0],element_id=key[1]))
    for kind,cap in [('node','max_nodes'),('way','max_ways')]:
        if sum(k[0]==kind for k in selected)>caps[cap]: raise _Capacity(kind.upper()+'_CAPACITY')
    return selected


def _access(tags,policy):
    for key in policy['access_precedence']:
        if key in tags:
            value=tags[key].strip().lower()
            if value in policy['deny_values']: return 'DENIED'
            if value in policy['allow_values']: return 'DECLARED_ALLOWED_NOT_VERIFIED'
            return 'UNKNOWN'
    return 'UNKNOWN'


def _closures(values,hashes,context,cutoff,a,b):
    if type(values) is not list: raise _Invalid('CLOSURES_LIST')
    closed=set()
    for value in values:
        _fields(value,{'source_sha256','target_type','target_id','valid_start','valid_end','available_at','mode','status'})
        if _sha(value['source_sha256']) not in hashes: raise _Invalid('CLOSURE_SOURCE')
        if value['target_type'] not in ('node','way') or value['mode']!=context['mode'] or value['status']!='CLOSED': raise _Invalid('CLOSURE_SCOPE')
        _int(value['target_id']); start=_time(value['valid_start']); end=_time(value['valid_end'])
        if start>=end: raise _Invalid('CLOSURE_TIME')
        if value['available_at'] is None or _time(value['available_at'])>=cutoff: raise _Blocked('CLOSURE_NOT_BEFORE_CUTOFF')
        if start<b and end>a: closed.add((value['target_type'],value['target_id']))
    return closed


def _graph(selected,polygons,policy,closed,budget,diagnostics):
    nodes={}; edges=[]; ways={}; eps=policy['geometry_tolerance_degrees']; caps=policy['capacities']
    incidents={}
    for (kind,way_id),(way,sources) in sorted(selected.items()):
        if kind!='way': continue
        budget.check(); tags=way.get('tags',{}); access=_access(tags,policy)
        reason=None
        if not tags.get('highway'): reason='NON_HIGHWAY_WAY'
        elif ('way',way_id) in closed: reason='SOURCE_BOUND_CLOSURE'
        elif access=='DENIED': reason='ACCESS_DENIED'
        elif tags.get('route')=='ferry': reason='FERRY_UNSUPPORTED'
        elif any('conditional' in k for k in tags): reason='CONDITIONAL_UNSUPPORTED'
        elif any(k.startswith('oneway:') or k.endswith((':forward',':backward',':lanes')) for k in tags): reason='DIRECTIONAL_TAG_UNSUPPORTED'
        oneway=tags.get('oneway','yes' if tags.get('junction')=='roundabout' else 'no').strip().lower()
        if oneway not in ('yes','1','true','no','0','false','-1'): reason='ONEWAY_UNSUPPORTED'
        if reason:
            diagnostics.append(dict(reason=reason,way_id=way_id)); continue
        if access=='UNKNOWN': diagnostics.append(dict(reason='ACCESS_UNKNOWN',way_id=way_id))
        directions=(-1,) if oneway=='-1' else (1,) if oneway in ('yes','1','true') else (1,-1)
        for index,(first,second) in enumerate(zip(way['nodes'],way['nodes'][1:])):
            budget.check(); pair=[]; invalid=False
            for ident in (first,second):
                record=selected.get(('node',ident))
                if record is None:
                    diagnostics.append(dict(reason='MISSING_NODE',way_id=way_id,node_id=ident)); invalid=True; break
                n,refs=record; ntags=n.get('tags',{})
                if any('conditional' in key for key in ntags):
                    diagnostics.append(dict(reason='NODE_CONDITIONAL_UNSUPPORTED',way_id=way_id,node_id=ident)); invalid=True; break
                if ('node',ident) in closed or _access(ntags,policy)=='DENIED' or ('barrier' in ntags and ntags['barrier']!='no' and not any(ntags.get(k) in policy['barrier_pass_values'] for k in policy['access_precedence'])):
                    diagnostics.append(dict(reason='NODE_BARRIER_OR_CLOSURE',way_id=way_id,node_id=ident)); invalid=True; break
                pair.append((n,refs))
            if invalid: continue
            a=(pair[0][0]['lon'],pair[0][0]['lat']); b=(pair[1][0]['lon'],pair[1][0]['lat'])
            try: intervals=_clip(a,b,polygons,eps,budget)
            except _Geometry as e:
                diagnostics.append(dict(reason=str(e),way_id=way_id,segment_index=index)); continue
            for part,(lo,hi) in enumerate(intervals):
                endpoints=[]
                for side,t in enumerate((lo,hi)):
                    original=0 if t==0 else 1 if t==1 else None
                    lon=a[0]+(b[0]-a[0])*t; lat=a[1]+(b[1]-a[1])*t
                    if original is not None:
                        n,refs=pair[original]; ident='osm:'+str(n['id'])
                        node=dict(node_id=ident,longitude=lon,latitude=lat,version=n.get('version'),source_sha256s=refs,origin='OSM_NODE')
                    else:
                        ident=f'boundary:{way_id}:{way.get("version")}:{index}:{part}:{side}'
                        node=dict(node_id=ident,longitude=lon,latitude=lat,version=None,source_sha256s=sources,origin='EDGE_LOCAL_DOMAIN_INTERSECTION')
                    nodes[ident]=node; endpoints.append(ident)
                x1,y1=utm52n(nodes[endpoints[0]]['latitude'],nodes[endpoints[0]]['longitude'])
                x2,y2=utm52n(nodes[endpoints[1]]['latitude'],nodes[endpoints[1]]['longitude'])
                length=math.hypot(x2-x1,y2-y1)
                if not 0<length<1e7: raise _Invalid('GEOMETRIC_LENGTH_INVALID')
                for direction in directions:
                    if len(edges)>=caps['max_edges']: raise _Capacity('EDGE_CAPACITY')
                    start,end=endpoints if direction==1 else endpoints[::-1]
                    way_ref=f'way:{way_id}:{way.get("version")}'
                    ways[way_ref]=dict(way_ref=way_ref,way_id=way_id,way_version=way.get('version'),source_sha256s=sources,tags=tags)
                    edges.append(dict(edge_id=f'{way_ref}:{index}:{part}:{direction}',way_ref=way_ref,
                        segment_index=index,from_node=start,to_node=end,length_m=length,
                        access_status=access,direction=direction))
                for ident in endpoints:
                    incidents.setdefault(ident,set()).add(tuple(tags.get(k,'') for k in ('layer','bridge','tunnel')))
    for ident,structures in sorted(incidents.items()):
        if len(structures)>1: diagnostics.append(dict(reason='STRUCTURAL_TRANSITION_UNVERIFIED',node_id=ident))
    return sorted(nodes.values(),key=lambda n:n['node_id']),sorted(edges,key=lambda e:e['edge_id']),sorted(ways.values(),key=lambda w:w['way_ref'])


def _restrictions(selected,edges,ways,caps,budget,diagnostics):
    incoming={}; outgoing={}; constraints=[]; work=0
    by_id={e['edge_id']:e for e in edges}
    by_way={w['way_ref']:w['way_id'] for w in ways}
    for e in edges:
        incoming.setdefault((by_way[e['way_ref']],e['to_node']),[]).append(e['edge_id'])
        outgoing.setdefault((by_way[e['way_ref']],e['from_node']),[]).append(e['edge_id'])
    for (kind,ident),(relation,sources) in sorted(selected.items()):
        if kind!='relation' or relation.get('tags',{}).get('type')!='restriction': continue
        budget.check(); tags=relation['tags']; members=relation['members']; name=tags.get('restriction','')
        supported={'no_left_turn','no_right_turn','no_straight_on','no_u_turn','only_left_turn','only_right_turn','only_straight_on'}
        roles={}
        for m in members: roles.setdefault(m['role'],[]).append(m)
        valid=(set(tags)<={'type','restriction'} and name in supported and set(roles)=={'from','via','to'}
               and all(len(v)==1 for v in roles.values()))
        if valid:
            valid=(roles['from'][0]['type']=='way' and roles['to'][0]['type']=='way' and roles['via'][0]['type']=='node')
        if not valid:
            diagnostics.append(dict(reason='UNSUPPORTED_RESTRICTION',relation_id=ident)); continue
        via='osm:'+str(roles['via'][0]['ref']); before=incoming.get((roles['from'][0]['ref'],via),[]); after=outgoing.get((roles['to'][0]['ref'],via),[])
        if not before or not after:
            diagnostics.append(dict(reason='UNRESOLVED_RESTRICTION',relation_id=ident)); continue
        work+=len(before)*len(after)
        if work>caps['max_transitions']: raise _Capacity('TRANSITION_CAPACITY')
        if name=='no_u_turn':
            pairs=[([pre],[post]) for pre in before for post in after if by_id[pre]['from_node']==by_id[post]['to_node']]
            if not pairs:
                diagnostics.append(dict(reason='UNRESOLVED_U_TURN',relation_id=ident)); continue
        elif len(before)!=1 or len(after)!=1:
            diagnostics.append(dict(reason='AMBIGUOUS_RESTRICTION_EDGES',relation_id=ident)); continue
        else: pairs=[(before,after)]
        for pre,post in pairs:
            constraints.append(dict(relation_id=ident,relation_version=relation.get('version'),rule='NO' if name.startswith('no_') else 'ONLY',
                restriction=name,via_node=via,from_edges=sorted(pre),to_edges=sorted(post),source_sha256s=sources))
    return constraints


def _result(status,**values):
    return dict(schema_version='habu-route-graph-result-v1',status=status,navigation_status='NAVIGATION_BLOCKED',
        source_authenticity='NOT_ATTESTED',scientific_status='NOT_VALIDATED',production_authorized=False,
        official_issuance_authorized=False,fit_authorized=False,selection_authorized=False,**values)


def build_route_graph(graph_input,*,policy,budget_seconds=30):
    """Return bounded research topology or a sanitized structured failure.

    Only owned internal validation exceptions are caught. Unexpected implementation
    defects propagate; input contents are never interpolated into error messages.
    """
    try:
        budget=_Budget(budget_seconds)
        owned=_owned([graph_input,policy],budget); data,policy=owned
        _fields(data,{'schema_version','sources','domain','context','coverage','closures','policy_sha256'})
        if data['schema_version']!='habu-route-graph-input-v1': raise _Invalid('INPUT_VERSION')
        policy=_policy(policy); caps=policy['capacities']
        budget.geometry_limit=caps['max_geometry_candidates']
        budget.deadline=min(budget.deadline,budget.start+caps['max_seconds']); budget.check()
        _owned(owned,budget,max_nodes=caps['max_json_nodes'],max_bytes=caps['max_json_bytes'])
        if _sha(data['policy_sha256'])!=_hash(policy): raise _Invalid('POLICY_HASH_MISMATCH')
        cutoff,a,b=_context(data['context'],policy)
        items,refs,hashes=_sources(data['sources'],caps,cutoff,budget)
        diagnostics=[]
        selected=_elements(items,caps,budget,diagnostics)
        try: polygons=_domain(data['domain'],caps,policy['geometry_tolerance_degrees'],budget)
        except _Geometry as e:
            polygons=None; diagnostics.append(dict(reason=str(e)))
        _coverage(data['coverage'],hashes,data['domain'],data['context'],cutoff,a,b)
        closed=_closures(data['closures'],hashes,data['context'],cutoff,a,b)
        nodes,edges,ways=_graph(selected,polygons,policy,closed,budget,diagnostics) if polygons is not None else ([],[],[])
        constraints=_restrictions(selected,edges,ways,caps,budget,diagnostics)
        body=dict(source_refs=refs,domain_sha256=data['domain']['sha256'],policy_sha256=data['policy_sha256'],
            context=data['context'],coverage=data['coverage'],closures=data['closures'],nodes=nodes,edges=edges,ways=ways,
            transition_constraints=constraints,diagnostics=sorted(diagnostics,key=lambda x:_raw(x)),
            missing_requirements=['AUTHENTICATED_SOURCE_AVAILABILITY','VALIDATED_CURRENT_ACCESS','VALIDATED_RESTRICTION_AND_CLOSURE_COVERAGE'],
            summary=dict(source_count=len(refs),selected_elements=len(selected),node_count=len(nodes),way_count=len(ways),directed_edge_count=len(edges),restriction_count=len(constraints)))
        canonical_body=_owned(body,budget,max_nodes=caps['max_json_nodes'],max_bytes=caps['max_json_bytes'],return_bytes=True)
        graph_sha=hashlib.sha256(canonical_body).hexdigest(); budget.check()
        return _result('PARTIAL' if diagnostics else 'GRAPH_BUILT_RESEARCH_ONLY',graph_sha256=graph_sha,**body)
    except _Invalid as e: return _result('FAIL',reason=str(e),graph_sha256=None)
    except _Capacity as e: return _result('CAPACITY_EXCEEDED',reason=str(e),graph_sha256=None)
    except _Blocked as e: return _result('DATA_BLOCKED',reason=str(e),graph_sha256=None)
