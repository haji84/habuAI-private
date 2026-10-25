"""Actual 400,000-cell/32-feature boundary, entirely synthetic."""
import hashlib
import json
import resource
import sys
import tempfile
import time
from pathlib import Path

FIX=Path('/workspace/scratch/ded5451af149/pr32-fix')
ORIGINAL=Path('/workspace/scratch/ded5451af149/pr32-independent')
sys.path[:0]=[str(FIX/'src'),str(ORIGINAL/'tests')]
import prospective_inputs as pi
from master_contracts import digest
from test_prospective_inputs import fixtures,write,run

with tempfile.TemporaryDirectory() as temp:
    root=Path(temp)
    u,f,s,ur,fr,sr=fixtures(root)
    template=u['rows'][0]
    u['rows']=[dict(template,row_id=f'r{i}',utm_x_m=100050+(i%1000)*100,
                    utm_y_m=3000050+(i//1000)*100) for i in range(12500)]
    s['universe']=write(root,ur['path'],u)
    s['features']=[]
    names=[]
    for i in range(32):
        name=f'independent_synthetic_{i}'
        names.append(name)
        feature=dict(f,feature_name=name,values={row['row_id']:1.0 for row in u['rows']})
        s['features'].append(write(root,f'features/f{i}.json',feature))
    s['feature_schema_sha256']=digest(sorted(names))
    sr=write(root,sr['path'],s)
    referenced={sr['path'],s['universe']['path'],*(r['path'] for r in s['features'])}
    raw_bytes=sum((root/p).stat().st_size for p in referenced)
    before=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    start=time.perf_counter()
    result=run(root,sr,model_feature_names=tuple(names))
    elapsed=time.perf_counter()-start
    peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps(dict(module=str(Path(pi.__file__).resolve()),
        src_sha256=hashlib.sha256(Path(pi.__file__).read_bytes()).hexdigest(),
        rows=len(result['rows']),features=len(names),cells=len(result['rows'])*len(names),
        referenced_raw_bytes=raw_bytes,elapsed_seconds=round(elapsed,3),
        peak_rss_kib=peak,rss_growth_bytes=(peak-before)*1024,
        official_issuance_authorized=result['official_issuance_authorized']),indent=2))
