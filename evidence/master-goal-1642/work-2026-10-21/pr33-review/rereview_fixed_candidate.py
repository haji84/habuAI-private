"""Independent checks against the local PR33 fix candidate; source is not modified."""
import importlib.util
import hashlib
import json
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

base = Path(__file__).parent
fixed = base.parent / 'pr33-fix'
spec = importlib.util.spec_from_file_location('fixed_pr33', fixed / 'scripts/build_osm_prospective_universe.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
one = [{'cell_id':'utm52n_100m_4000_30000','x':400050.0,'y':3000050.0,'island':'奄美大島','length':10.0,'direction':15.0}]
def args(seconds=0.1):
    cutoff = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    f = (cutoff + timedelta(minutes=10)).astimezone(m.JST)
    first = f.replace(minute=(f.minute // 10) * 10, second=0, microsecond=0)
    return m.operational_night(cutoff), cutoff.isoformat(), first.isoformat(), 1
def fixture():
    return patch.multiple(m,load_verified_road_csv=lambda _:b'synthetic',parse_road_cells=lambda _:one)
result = {'source_script_sha256':hashlib.sha256((fixed/'scripts/build_osm_prospective_universe.py').read_bytes()).hexdigest()}
with tempfile.TemporaryDirectory() as td:
    root=Path(td);repo=root/'canonical';repo.mkdir();out=root/'out'
    original=m.canonical;delayed=[False]
    def serialize(obj):
        if not delayed[0]:
            delayed[0]=True;time.sleep(0.25)
        return original(obj)
    with fixture(),patch.object(m,'canonical',serialize):
        try:m.materialize(repo,out,*args())
        except ValueError as error:
            assert 'cutoff' in str(error);result['original_clock_reproduction']='PASS: rejected'
        else:raise AssertionError('accepted build completed after cutoff')
    assert not list(out.rglob('*.json'))
    assert not list(out.rglob('.forecast-pending-*'))
    result['failed_build_no_shard']=True
with tempfile.TemporaryDirectory() as td:
    root=Path(td);repo=root/'canonical';raw=repo/'data/raw';raw.mkdir(parents=True)
    sentinel=raw/'original.bin';sentinel.write_bytes(b'original')
    out=root/'outside';out.mkdir();(out/'features').symlink_to(raw,target_is_directory=True)
    with fixture():
        try:m.materialize(repo,out,*args(10))
        except ValueError as error:
            assert 'Symlink' in str(error);result['original_symlink_reproduction']='PASS: rejected'
        else:raise AssertionError('accepted symlink output')
    assert sorted(str(x.relative_to(repo)) for x in repo.rglob('*') if x.is_file())==['data/raw/original.bin']
    assert sentinel.read_bytes()==b'original'
    result['canonical_tree_unchanged_after_rejection']=True
with tempfile.TemporaryDirectory() as td:
    root=Path(td);repo=root/'canonical';repo.mkdir();out=root/'output'
    with fixture():old=m.materialize(repo,out,*args(30))
    before={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*.json')}
    original_flock=m.fcntl.flock
    def wait_for_lock(*a):
        original_flock(*a);time.sleep(0.25)
    with fixture(),patch.object(m.fcntl,'flock',wait_for_lock):
        try:m.materialize(repo,out,*args())
        except ValueError as error:
            assert 'cutoff' in str(error);result['lock_wait_cutoff_rejected']=True
        else:raise AssertionError('accepted expired lock waiter')
    after={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*.json')}
    assert before==after;result['older_successful_shard_preserved_after_failure']=True
# Actual archive is read from its independently verified original-head directory.
cutoff=datetime.now(timezone.utc)+timedelta(minutes=5)
f=(cutoff+timedelta(minutes=10)).astimezone(m.JST)
first=f.replace(minute=(f.minute//10)*10,second=0,microsecond=0)
out=base.parent/'pr33-fixed-actual-output'
assert not out.exists(),'Use clean output directory'
started=time.monotonic()
emitted=m.materialize(base,out,m.operational_night(cutoff),cutoff.isoformat(),first.isoformat(),6)
snapshot=json.loads((out/emitted['snapshot']).read_bytes())
completed=m.aware(emitted['completed_at'])
assert completed<cutoff
for ref in [snapshot['universe'],*snapshot['features']]:
    target=out/ref['path'];assert hashlib.sha256(target.read_bytes()).hexdigest()==ref['sha256']
    assert datetime.fromtimestamp(target.stat().st_mtime,timezone.utc)<=m.aware(ref['available_at'])<=completed
    assert m.aware(ref['available_at'])<cutoff
assert emitted['rows']==101940 and emitted['official_prediction_eligible'] is False
result['actual_max_six_windows']={'rows':emitted['rows'],'elapsed_seconds':time.monotonic()-started,'completed_at':emitted['completed_at'],'cutoff':cutoff.isoformat(),'source_file_mtimes_precede_claimed_ref_availability':True,'snapshot_sha256':emitted['snapshot_sha256']}
assert hashlib.sha256((out/emitted['snapshot']).read_bytes()).hexdigest()==emitted['snapshot_sha256']
(base/'fixed-candidate-rereview-evidence.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
