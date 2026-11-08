"""Exercise only disposable copies; never write the candidate's received originals."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib.util,hashlib,json,shutil,os,multiprocessing

base=Path('/workspace/scratch/ded5451af149')
candidate=base/'data-audit-repair'
script=candidate/'scripts/build_september51_07h_view.py'
spec=importlib.util.spec_from_file_location('candidate_builder',script)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
receipt_rel=Path('evidence/raw_intake/2026-10-21-september-corrected-source-receipt.json')
receipt=json.loads((candidate/receipt_rel).read_text())
target_rel=Path('data/processed/reconciliation_candidates/2026-10-21/historical_capture_display_september51_07h.csv')
expected='979ba7f96259c9202d084e302d08cd8f72f04017b80d4d23cc465242ca26ad07'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare(root):
    for rel in [receipt_rel,*[Path(x['repository_path']) for x in receipt['sources']]]:
        dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(candidate/rel,dest)
def originals(root):
    return {x['repository_path']:sha(root/x['repository_path']) for x in receipt['sources']}
def rejected(root):
    try:m.build(root)
    except (ValueError,OSError) as error:return type(error).__name__+': '+str(error)
    raise AssertionError('unsafe candidate accepted')
results={}
with TemporaryDirectory() as temp:
    root=Path(temp);prepare(root);before=originals(root)
    result=m.build(root);target=root/target_rel
    assert result['output_sha256']==expected==sha(target)
    stat=target.stat();m.build(root);again=target.stat()
    assert (stat.st_ino,stat.st_mtime_ns,stat.st_size)==(again.st_ino,again.st_mtime_ns,again.st_size)
    assert before==originals(root);results['identical_output_idempotent_no_rewrite']='PASS'
    target.write_bytes(b'previous candidate bytes must be preserved')
    saved=target.read_bytes();results['different_existing_output_rejected']=rejected(root)
    assert target.read_bytes()==saved and before==originals(root)
with TemporaryDirectory() as temp:
    top=Path(temp);root=top/'root';prepare(root);protected=top/'protected-original.bin';protected.write_bytes(b'immutable original')
    target=root/target_rel;target.parent.mkdir(parents=True);target.symlink_to(protected)
    results['target_symlink_rejected']=rejected(root)
    assert protected.read_bytes()==b'immutable original' and target.is_symlink()
for relative in ['data','data/processed','data/processed/reconciliation_candidates','data/processed/reconciliation_candidates/2026-10-21']:
    with TemporaryDirectory() as temp:
        top=Path(temp);root=top/'root';prepare(root);protected=top/'raw';protected.mkdir();(protected/'original').write_bytes(b'immutable')
        link=root/relative;link.parent.mkdir(parents=True,exist_ok=True);link.symlink_to(protected,target_is_directory=True)
        results['output_ancestor_symlink_'+relative]=rejected(root)
        assert sorted(p.name for p in protected.iterdir())==['original']
        assert (protected/'original').read_bytes()==b'immutable'
for relative in [str(receipt_rel),'evidence','incoming','incoming/2026-10-21',*[x['repository_path'] for x in receipt['sources']]]:
    with TemporaryDirectory() as temp:
        top=Path(temp);root=top/'root';prepare(root);p=root/relative;external=top/'external'
        if p.is_dir():shutil.move(str(p),external)
        else:shutil.copy2(p,external);p.unlink()
        p.symlink_to(external,target_is_directory=external.is_dir())
        results['receipt_or_input_ancestor_symlink_'+relative]=rejected(root)
        assert not (root/target_rel).exists()
for variant in ['absolute','traversal','raw_prefix']:
    with TemporaryDirectory() as temp:
        root=Path(temp);prepare(root);r=json.loads((root/receipt_rel).read_text());entry=r['sources'][0];old=root/entry['repository_path']
        if variant=='absolute':entry['repository_path']=str(old.resolve())
        elif variant=='traversal':entry['repository_path']='incoming/2026-10-21/../2026-10-21/'+old.name
        else:
            p=root/'data/raw/received.xlsx';p.parent.mkdir(parents=True);shutil.copy2(old,p);entry['repository_path']=str(p.relative_to(root))
        (root/receipt_rel).write_text(json.dumps(r,ensure_ascii=False))
        results['receipt_source_path_'+variant]=rejected(root)
        assert not (root/target_rel).exists()
with TemporaryDirectory() as temp:
    top=Path(temp);actual=top/'actual';prepare(actual);alias=top/'alias';alias.symlink_to(actual,target_is_directory=True)
    results['root_symlink_rejected']=rejected(alias)
    assert not (actual/target_rel).exists()
for kind in ['source','existing_target']:
    with TemporaryDirectory() as temp:
        root=Path(temp);prepare(root)
        if kind=='source':
            fifo=root/receipt['sources'][0]['repository_path'];fifo.unlink()
        else:
            fifo=root/target_rel;fifo.parent.mkdir(parents=True)
        os.mkfifo(fifo)
        queue=multiprocessing.Queue()
        def bounded_run():
            try:queue.put(rejected(root))
            except BaseException as error:queue.put('FAIL: '+repr(error))
        worker=multiprocessing.Process(target=bounded_run);worker.start();worker.join(1)
        if worker.is_alive():
            worker.terminate();worker.join();raise AssertionError('FIFO '+kind+' blocked before regular-file rejection')
        message=queue.get(timeout=1);assert 'regular file' in message,message
        results['fifo_'+kind+'_rejected_without_blocking']=message
result={'script_sha256':sha(script),'expected_output_sha256':expected,'cases':results,'all_received_originals_untouched':True,'scope':'all mutations confined to disposable copies'}
(base/'data-audit-evidence/independent-builder-safety-evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
