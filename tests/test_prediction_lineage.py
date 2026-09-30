import importlib
import importlib.util
import json
import os
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'), str(ROOT/'scripts')]
from master_contracts import canonical_bytes, digest, file_hash
from test_champion_registry import evidence_fixture, write
import freeze_prediction as freeze
import champion_registry as registry

NIGHT='2026-09-30'
NOW=datetime.fromisoformat(NIGHT+'T20:00:00+09:00')


def forecast_fixture(root):
    universe={'schema_version':'1.0', 'source_type':'EX_ANTE_FORECAST',
              'geographic_domain':{'crs':'EPSG:32652','description':'sandbox'},
              'rows':[{'row_id':'u1','operational_night':NIGHT,'cutoff_time':NIGHT+'T19:00:00+09:00',
                       'window_start_jst':NIGHT+'T21:00:00+09:00','utm_x_m':400050,'utm_y_m':3000050}]}
    uref=write(root,'features/universe.json',universe)
    uref['available_at']='2026-09-29T00:00:00+09:00'
    snapshot={'schema_version':'1.0','operational_night':NIGHT,'cutoff_time':NIGHT+'T19:00:00+09:00',
              'universe':uref,'feature_schema_sha256':digest([]),'source_manifest':[], 'features':{}}
    ref=write(root,'features/issuance.json',snapshot)
    return root/ref['path'], ref['sha256']


class AtomicFreezeTests(unittest.TestCase):
    def test_concurrent_freezes_allocate_contiguous_complete_versions(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); inp=root/'input.json'; inp.write_text('{}')
            with ThreadPoolExecutor(4) as pool:
                paths=list(pool.map(lambda _:freeze.freeze(root,inp,NIGHT,now=NOW),range(4)))
            self.assertEqual({p.parent.name for p in paths},{'P0','P1','P2','P3'})
            for path in paths:
                self.assertTrue((path.parent/'sha256.txt').is_file())
                self.assertEqual(json.loads(path.read_text())['prediction_version'],path.parent.name)

    def test_failure_before_publication_does_not_reserve_empty_version(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); inp=root/'input.json'; inp.write_text('{}')
            # Actual filesystem rename fails after complete staging is written.
            with patch.object(freeze.os,'rename',side_effect=OSError('publication failed')):
                with self.assertRaises(OSError): freeze.freeze(root,inp,NIGHT,now=NOW)
            self.assertFalse((root/f'predictions/original/{NIGHT}/P0').exists())
            self.assertEqual(freeze.freeze(root,inp,NIGHT,now=NOW).parent.name,'P0')

    def test_staging_directory_is_synced_before_rename_and_parent_after(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); inp=root/'input.json'; inp.write_text('{}')
            events=[]; synced_paths=[]; sync=freeze.os.fsync; rename=freeze.os.rename
            def observe_sync(fd):
                path=Path(os.readlink(f'/proc/self/fd/{fd}'))
                synced_paths.append(path)
                events.append('staging_sync' if path.name.startswith('.pending-') else
                              'parent_sync' if path.name==NIGHT else
                              'parent_link_sync' if path.is_dir() else 'file_sync')
                return sync(fd)
            def observe_rename(source,destination):
                events.append('rename')
                return rename(source,destination)
            with patch.object(freeze.os,'fsync',side_effect=observe_sync), patch.object(freeze.os,'rename',side_effect=observe_rename):
                out=freeze.freeze(root,inp,NIGHT,now=NOW)
            self.assertTrue(out.is_file())
            self.assertEqual([e for e in events if e!='parent_link_sync'],
                             ['file_sync','file_sync','staging_sync','rename','parent_sync'])
            self.assertTrue({root, root/'predictions', root/'predictions/original'} <= set(synced_paths))
            self.assertLess(max(i for i,e in enumerate(events) if e=='parent_link_sync'),events.index('rename'))

    def test_failed_staging_directory_sync_cleans_up_without_reserving_version(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); inp=root/'input.json'; inp.write_text('{}')
            sync=freeze.os.fsync
            def fail_directory(fd):
                if Path(os.readlink(f'/proc/self/fd/{fd}')).name.startswith('.pending-'):
                    raise OSError('staging directory durability failure')
                return sync(fd)
            with patch.object(freeze.os,'fsync',side_effect=fail_directory):
                with self.assertRaises(OSError): freeze.freeze(root,inp,NIGHT,now=NOW)
            base=root/f'predictions/original/{NIGHT}'
            self.assertFalse((base/'P0').exists())
            self.assertEqual(list(base.glob('.pending-*')),[])
            self.assertEqual(freeze.freeze(root,inp,NIGHT,now=NOW).parent.name,'P0')

    def test_nested_new_root_requires_existing_parent_before_any_creation(self):
        with tempfile.TemporaryDirectory() as td:
            existing=Path(td); root=existing/'new-parent'/'new-root'
            inp=existing/'input.json'; inp.write_text('{}')
            with self.assertRaisesRegex(ValueError,'root parent must already exist'):
                freeze.freeze(root,inp,NIGHT,now=NOW)
            self.assertFalse((existing/'new-parent').exists())
            # A new root immediately beneath the existing filesystem boundary is supported.
            out=freeze.freeze(existing/'new-root',inp,NIGHT,now=NOW)
            self.assertTrue(out.is_file())

    def test_existing_ancestor_sync_failure_is_retried_before_publication(self):
        with tempfile.TemporaryDirectory() as td:
            existing=Path(td); root=existing/'new-root'; inp=existing/'input.json'; inp.write_text('{}')
            sync=freeze.os.fsync; attempts=[]
            def fail_boundary(fd):
                path=Path(os.readlink(f'/proc/self/fd/{fd}'))
                if path==existing:
                    attempts.append(path)
                    raise OSError('existing ancestor sync failed')
                return sync(fd)
            with patch.object(freeze.os,'fsync',side_effect=fail_boundary):
                with self.assertRaises(OSError): freeze.freeze(root,inp,NIGHT,now=NOW)
            self.assertFalse((root/f'predictions/original/{NIGHT}/P0').exists())
            def observe_retry(fd):
                path=Path(os.readlink(f'/proc/self/fd/{fd}'))
                if path==existing: attempts.append(path)
                return sync(fd)
            with patch.object(freeze.os,'fsync',side_effect=observe_retry):
                self.assertEqual(freeze.freeze(root,inp,NIGHT,now=NOW).parent.name,'P0')
            self.assertEqual(attempts,[existing,existing])

    def test_invalid_json_numbers_and_naive_clock_never_publish(self):
        for payload, now in [({'expected_capture_count':float('nan')}, NOW),
                             ({'expected_capture_count':float('inf')}, NOW),
                             ({}, NOW.replace(tzinfo=None))]:
            with self.subTest(payload=payload, now=now), tempfile.TemporaryDirectory() as td:
                root=Path(td); inp=root/'input.json'; inp.write_text(json.dumps(payload))
                with self.assertRaises(ValueError): freeze.freeze(root,inp,NIGHT,now=now)
                self.assertFalse((root/f'predictions/original/{NIGHT}/P0').exists())

    def test_generic_payload_cannot_claim_executed_champion_lineage(self):
        for field in ['champion_id','registry_event_id','inference_sha256','issued_at']:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as td:
                root=Path(td); inp=root/'input.json'; inp.write_text(json.dumps({field:'forged'}))
                with self.assertRaises(ValueError): freeze.freeze(root,inp,NIGHT,now=NOW)
                self.assertFalse((root/f'predictions/original/{NIGHT}/P0').exists())


class PredictionLineageTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('issue_prediction'),'registered inference issuer missing')
        self.issue=importlib.import_module('issue_prediction')

    def promote(self,ctx,probability,previous=None):
        model,path=evidence_fixture(ctx.root,probability)
        with patch.object(registry,'_now',return_value=NIGHT+'T18:00:00+09:00'):
            event=registry.promote(ctx,model['model_id'],path,previous)
        return model,event

    def test_actual_champion_inference_changes_output_and_keeps_old_prediction(self):
        with registry.sandbox_registry() as ctx:
            a,ea=self.promote(ctx,.2)
            path,sha=forecast_fixture(ctx.root)
            first=self.issue.issue_prediction(ctx,path,sha,NIGHT,clock=lambda:NOW)
            raw=first.read_bytes(); payload=json.loads(raw)
            self.assertEqual(payload['grid_predictions'][0]['probability'],.2)
            self.assertEqual(payload['champion_id'],a['model_id'])
            self.assertEqual(payload['registry_event_id'],ea['event_sha256'])
            self.assertEqual(payload['inference_sha256'],digest(payload['grid_predictions']))
            self.assertEqual(payload['formal_100m_10min_status'],'NOT_PRODUCED')
            self.assertFalse(payload['strict_official_score_eligible'])
            self.assertEqual(payload['qualification'],'SANDBOX_MECHANICS')
            self.assertEqual(payload['prediction_class'],'SANDBOX')
            b,eb=self.promote(ctx,.8,ea['event_sha256'])
            second=self.issue.issue_prediction(ctx,path,sha,NIGHT,clock=lambda:NOW)
            self.assertEqual(json.loads(second.read_text())['grid_predictions'][0]['probability'],.8)
            self.assertEqual(first.read_bytes(),raw)
            self.assertEqual(second.parent.name,'P1')
            self.assertFalse((ctx.root/'predictions/original').exists())

    def test_production_issuance_cannot_read_forged_registry(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); path,sha=forecast_fixture(root)
            write(root,'models/champion_registry/current.json',{'validated':True,'scope':'PRODUCTION'})
            with self.assertRaisesRegex(ValueError,'authority'):
                self.issue.issue_prediction(root,path,sha,NIGHT,clock=lambda:NOW)
            self.assertIsNone(registry.champion_at(root,NOW.isoformat()))
            self.assertFalse((root/'predictions/original').exists())

    def test_issuance_rejects_changed_inputs_future_availability_and_training(self):
        for case in ['hash','availability','training','window','schema']:
            with self.subTest(case=case), registry.sandbox_registry() as ctx:
                self.promote(ctx,.2); path,sha=forecast_fixture(ctx.root)
                value=json.loads(path.read_text())
                if case=='hash': path.write_text('{}')
                elif case=='availability': value['universe']['available_at']=NIGHT+'T19:00:00+09:00'
                elif case=='training': value['cutoff_time']='2026-08-31T19:00:00+09:00'
                elif case=='schema': value['feature_schema_sha256']='0'*64
                else:
                    up=ctx.root/value['universe']['path']; u=json.loads(up.read_text())
                    u['rows'][0]['window_start_jst']=NIGHT+'T19:30:00+09:00'
                    up.write_bytes(canonical_bytes(u)); value['universe']['sha256']=file_hash(up)
                if case!='hash': path.write_bytes(canonical_bytes(value)); sha=file_hash(path)
                with self.assertRaises(ValueError): self.issue.issue_prediction(ctx,path,sha,NIGHT,clock=lambda:NOW)
                self.assertFalse((ctx.root/f'sandbox/predictions/{NIGHT}/P0').exists())

    def test_window_alignment_is_checked_in_jst_for_equivalent_timezones(self):
        # +05:45 local :00 is JST :15 (invalid); local :45 is JST :00 (valid).
        for window, accepted in [('2026-09-30T18:00:00+05:45',False),
                                 ('2026-09-30T17:45:00+05:45',True),
                                 ('2026-09-30T12:00:00Z',True)]:
            with self.subTest(window=window), registry.sandbox_registry() as ctx:
                self.promote(ctx,.2); path,_=forecast_fixture(ctx.root)
                snapshot=json.loads(path.read_text())
                up=ctx.root/snapshot['universe']['path']; universe=json.loads(up.read_text())
                universe['rows'][0]['window_start_jst']=window
                up.write_bytes(canonical_bytes(universe)); snapshot['universe']['sha256']=file_hash(up)
                path.write_bytes(canonical_bytes(snapshot)); sha=file_hash(path)
                if accepted:
                    out=self.issue.issue_prediction(ctx,path,sha,NIGHT,clock=lambda:NOW)
                    self.assertEqual(json.loads(out.read_text())['grid_predictions'][0]['probability'],.2)
                else:
                    with self.assertRaises(ValueError):
                        self.issue.issue_prediction(ctx,path,sha,NIGHT,clock=lambda:NOW)
                    self.assertFalse((ctx.root/f'sandbox/predictions/{NIGHT}/P0').exists())

    def test_source_mutation_during_inference_prevents_publication(self):
        with registry.sandbox_registry() as ctx:
            self.promote(ctx,.2); path,sha=forecast_fixture(ctx.root)
            original=self.issue.predict_model
            def changed(*args):
                output=original(*args); path.write_text('{}'); return output
            with patch.object(self.issue,'predict_model',side_effect=changed):
                with self.assertRaises(ValueError): self.issue.issue_prediction(ctx,path,sha,NIGHT,clock=lambda:NOW)
            self.assertFalse((ctx.root/f'sandbox/predictions/{NIGHT}/P0').exists())

    def test_expired_window_during_inference_is_rejected_without_backdating(self):
        with registry.sandbox_registry() as ctx:
            self.promote(ctx,.2); path,sha=forecast_fixture(ctx.root)
            clock=iter([NOW,datetime.fromisoformat(NIGHT+'T21:00:00+09:00')])
            with self.assertRaises(ValueError): self.issue.issue_prediction(ctx,path,sha,NIGHT,clock=lambda:next(clock))
            self.assertFalse((ctx.root/f'sandbox/predictions/{NIGHT}/P0').exists())

    def test_promotion_waits_for_inference_and_publication(self):
        with registry.sandbox_registry() as ctx:
            a,ea=self.promote(ctx,.2); b,bp=evidence_fixture(ctx.root,.8); path,sha=forecast_fixture(ctx.root)
            started=threading.Event(); release=threading.Event(); promotion_started=threading.Event()
            original=self.issue.predict_model
            def slow(*args):
                started.set()
                if not release.wait(5): raise AssertionError('test synchronization timeout')
                return original(*args)
            def promote():
                promotion_started.set()
                return registry.promote(ctx,b['model_id'],bp,ea['event_sha256'])
            with patch.object(self.issue,'predict_model',side_effect=slow), ThreadPoolExecutor(2) as pool:
                issuing=pool.submit(self.issue.issue_prediction,ctx,path,sha,NIGHT,clock=lambda:NOW)
                self.assertTrue(started.wait(5))
                promoting=pool.submit(promote); self.assertTrue(promotion_started.wait(5))
                self.assertFalse(promoting.done())
                release.set(); issued=issuing.result(); promoting.result()
            self.assertEqual(json.loads(issued.read_text())['champion_id'],a['model_id'])
