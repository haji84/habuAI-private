import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"))

import pdca_pipeline
import run_pdca

class PDCATests(unittest.TestCase):
    def test_operational_night_before_0700_is_previous_day(self):
        self.assertEqual(run_pdca.operational_night(datetime(2026,9,30,6,59,tzinfo=ZoneInfo("Asia/Tokyo"))),"2026-09-29")

    def test_operational_night_at_0700_is_current_day(self):
        self.assertEqual(run_pdca.operational_night(datetime(2026,9,30,7,0,tzinfo=ZoneInfo("Asia/Tokyo"))),"2026-09-30")

    def test_missing_predictions_blocks_pipeline(self):
        with tempfile.TemporaryDirectory() as td:
            result=pdca_pipeline.run_pipeline(Path(td),"2026-09-30")
            self.assertEqual(result["overall_status"],"BLOCKED")
            self.assertEqual(result["stages"][0]["name"],"load_frozen_predictions")

    def test_prediction_hash_roundtrip(self):
        payload={"prediction_id":"x","prediction_version":"P0","cutoff_time":"2026-09-30T20:00:00+09:00","targets_100m_10min":[]}
        h=pdca_pipeline.canonical_prediction_hash(payload)
        payload["payload_sha256"]=h
        status,rows=pdca_pipeline.verify_predictions([payload])
        self.assertEqual(status,"PASS")
        self.assertEqual(rows[0]["actual_sha256"],h)

    def test_load_predictions_numeric_order(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); base=root/"predictions"/"original"/"2026-09-30"
            for name in ("P10","P2","P0","P1"):
                d=base/name; d.mkdir(parents=True)
                p={"prediction_id":name,"prediction_version":name,"cutoff_time":"2026-09-30T20:00:00+09:00","targets_100m_10min":[]}
                p["payload_sha256"]=pdca_pipeline.canonical_prediction_hash(p)
                (d/"prediction.json").write_text(json.dumps(p),encoding="utf-8")
            got=pdca_pipeline.load_predictions(root,"2026-09-30")
            self.assertEqual([p["prediction_version"] for p in got],["P0","P1","P2","P10"])

    def test_exposure_marks_only_observed_units_negative(self):
        points=[{"datetime_jst":pdca_pipeline.parse_dt("2026-09-30T20:05:00+09:00"),"latitude":28.15,"longitude":129.30,"night_date":"2026-09-30","source":"x"}]
        exposure=pdca_pipeline.build_exposure(points,[],"2026-09-30")
        self.assertEqual(len(exposure),1)
        self.assertEqual(exposure[0]["observation"],"observed_negative")

    def test_score_respects_cutoff(self):
        pred={"prediction_version":"P0","cutoff_time":"2026-09-30T20:00:00+09:00",
              "targets_100m_10min":[{"latitude":28.15,"longitude":129.30,"predicted_time_jst":"2026-09-30T21:00:00+09:00"}]}
        captures=[
            {"datetime_jst":pdca_pipeline.parse_dt("2026-09-30T19:59:00+09:00"),"latitude":28.15,"longitude":129.30,"night_date":"2026-09-30","event_id":"before"},
            {"datetime_jst":pdca_pipeline.parse_dt("2026-09-30T21:03:00+09:00"),"latitude":28.15,"longitude":129.30,"night_date":"2026-09-30","event_id":"after"},
        ]
        score=pdca_pipeline.score_prediction(pred,captures,"2026-09-30")
        self.assertEqual(score["captures_after_cutoff"],1)
        self.assertEqual(score["matched_targets"],1)
        self.assertEqual(score["matches"][0]["event_id"],"after")

if __name__=="__main__":
    unittest.main()
