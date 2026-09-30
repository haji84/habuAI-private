import importlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from test_evidence_audit import fixture,write,receipt,NIGHT,VERIFIED
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from master_contracts import file_hash,canonical_bytes
import evidence_audit


def build_request(root):
    rows=[{'row_id':'negative','operational_night':NIGHT,'cutoff_time':NIGHT+'T19:00:00+09:00',
           'window_start_jst':NIGHT+'T21:00:00+09:00','latitude':28.15,'longitude':129.3},
          {'row_id':'unknown','operational_night':NIGHT,'cutoff_time':NIGHT+'T19:00:00+09:00',
           'window_start_jst':NIGHT+'T21:40:00+09:00','latitude':28.16,'longitude':129.32}]
    u=write(root,'features/universe.json',{'schema_version':'1.0','source_type':'EX_ANTE_FORECAST',
            'geographic_domain':{'crs':'EPSG:32652','description':'explicit synthetic domain'},'rows':rows})
    p=write(root,'protocols/evaluation.json',{'schema_version':'1.0','frozen_at':'2026-09-01T00:00:00+09:00',
            'research_used_nights':[NIGHT],'confirmation_used_nights':[],'registered_candidates':['uniform']})
    for ref in [u,p]:ref.update(available_at='2026-09-01T00:00:00+09:00',receipt_ref=receipt(root,ref,'2026-09-01T00:00:00+09:00'))
    write(root,'features/learning_build.json',{'schema_version':'1.0','universe':u,'protocol':p,'features':[]})


class LearningSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('learning_snapshot'))
        self.b=importlib.import_module('learning_snapshot')
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def build(self):
        audit=evidence_audit.audit_evidence(self.root,NIGHT,verified_at=VERIFIED)
        return self.b.build_learning_snapshot(self.root,NIGHT,audit)
    def test_absent_universe_returns_requirements_without_fake_snapshot(self):
        fixture(self.root)
        result=self.build();self.assertEqual(result['status'],'BLOCKED')
        self.assertIn('FORECAST_UNIVERSE',str(result['input_requirements']))
        self.assertFalse((self.root/'data/processed/model_learning.json').exists())
        self.assertIsNone(result['evaluation_root'])
    def test_deterministic_rows_keep_unknown_and_outside_universe_captures(self):
        fixture(self.root,True);build_request(self.root)
        before={p:file_hash(p) for p in self.root.rglob('*') if p.is_file()}
        first=self.build();second=self.build();self.assertEqual(first,second)
        self.assertEqual(first['status'],'PASS')
        output=self.root/first['evaluation_root'];snapshot=json.loads((output/'data/processed/model_learning.json').read_text())
        by_id={r['universe_row_id']:r for r in snapshot['rows']}
        self.assertEqual(by_id['negative']['label'],0);self.assertIsNone(by_id['unknown']['label'])
        self.assertIsNone(by_id['unknown']['label_available_at'])
        self.assertEqual(snapshot['outcome_ledger']['outside_universe_event_ids'],['C'])
        self.assertEqual(snapshot['outcome_ledger']['events'][0]['capture_count'],2)
        self.assertEqual(snapshot['outcome_ledger']['denominator_coverage'],'NOT_ESTABLISHED')
        for path,sha in before.items():self.assertEqual(file_hash(path),sha)
        import model_evaluation
        consumed={};model_evaluation._validate(output,'2026-10-02',consumed,lambda:None)
    def test_existing_input_learning_is_never_overwritten(self):
        fixture(self.root,True);build_request(self.root)
        write(self.root,'data/processed/model_learning.json',{'external':'immutable'})
        result=self.build();self.assertEqual(result['status'],'NOT_APPLICABLE')
        self.assertEqual(json.loads((self.root/'data/processed/model_learning.json').read_text()),{'external':'immutable'})
    def test_universe_receipt_after_cutoff_cannot_be_backdated(self):
        fixture(self.root,True);build_request(self.root)
        p=self.root/'features/learning_build.json';d=json.loads(p.read_text())
        r=self.root/d['universe']['receipt_ref']['path'];rr=json.loads(r.read_text());rr['received_at_utc']=VERIFIED;r.write_bytes(canonical_bytes(rr))
        d['universe']['receipt_ref']['sha256']=file_hash(r);p.write_bytes(canonical_bytes(d))
        result=self.build();self.assertEqual(result['status'],'FAIL');self.assertIsNone(result['evaluation_root'])
    def test_changed_audit_source_rejects_builder(self):
        fixture(self.root,True);build_request(self.root)
        audit=evidence_audit.audit_evidence(self.root,NIGHT,verified_at=VERIFIED)
        (self.root/'data/raw/gpx/track.gpx').write_text('<gpx/>')
        result=self.b.build_learning_snapshot(self.root,NIGHT,audit)
        self.assertEqual(result['status'],'FAIL')
    def test_noneligible_track_does_not_produce_negative_training_rows(self):
        fixture(self.root);build_request(self.root);result=self.build()
        output=self.root/result['evaluation_root'];snapshot=json.loads((output/'data/processed/model_learning.json').read_text())
        self.assertTrue(all(r['label'] is None and not r['observed'] for r in snapshot['rows']))

    def test_master_generated_workspace_is_recoverable_without_input_exemption(self):
        import master_orchestrator as m
        fixture(self.root,True);build_request(self.root)
        inputs=m._inventory(self.root)
        result=m.run_master(self.root,NIGHT)
        directory=self.root/'reports/pdca'/NIGHT/'runs'/result['run_id']
        snapshot=directory/'snapshot'
        self.assertTrue(m._snapshot_matches(snapshot,inputs))
        built=snapshot/'reports/learning_evaluation'/NIGHT/'data/processed/model_learning.json'
        self.assertTrue(built.is_file())
        self.assertFalse((snapshot/'data/processed/model_learning.json').exists())
        self.assertEqual(m.run_master(self.root,NIGHT),result)
        built.write_text('{}')
        self.assertEqual(m.run_master(self.root,NIGHT)['overall_status'],'FAIL')
