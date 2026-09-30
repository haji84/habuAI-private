import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import pdca_pipeline

class RecoveredPredictionTests(unittest.TestCase):
    def test_recovered_p0_is_partial_and_count_forecast_is_scored_without_fake_100m_targets(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); night="2026-09-28"
            pred_dir=root/"predictions"/"recovered_original"/night/"P0"
            pred_dir.mkdir(parents=True)
            payload={
                "prediction_id":"legacy",
                "operational_night":night,
                "prediction_version":"P0",
                "prediction_class":"RECOVERED_ORIGINAL",
                "cutoff_time":"2026-09-28T18:26:08+09:00",
                "freeze_status":"retrospective_recovery_after_label_reveal",
                "strict_official_score_eligible":False,
                "expected_capture_count":4,
                "expected_capture_range":[2,6],
                "targets_100m_10min":[]
            }
            payload["payload_sha256"]=pdca_pipeline.canonical_prediction_hash(payload)
            (pred_dir/"prediction.json").write_text(json.dumps(payload),encoding="utf-8")

            gpx=root/"data"/"raw"/"gpx"/"night.gpx"
            gpx.parent.mkdir(parents=True)
            gpx.write_text("""<?xml version="1.0"?>
<gpx version="1.1"><trk><trkseg>
<trkpt lat="28.15" lon="129.30"><time>2026-09-28T12:00:00Z</time></trkpt>
</trkseg></trk></gpx>""",encoding="utf-8")

            cap=root/"data"/"processed"/"capture_events"/"2026"/"2026-09-28.csv"
            cap.parent.mkdir(parents=True)
            with cap.open("w",encoding="utf-8",newline="") as fh:
                w=csv.DictWriter(fh,fieldnames=["event_id","operational_date","event_time_local","event_type","event_count","latitude","longitude"])
                w.writeheader()
                w.writerow({"event_id":"C","operational_date":night,"event_time_local":"2026-09-28T21:00:00+09:00",
                            "event_type":"capture","event_count":"6","latitude":"28.15","longitude":"129.30"})

            result=pdca_pipeline.run_pipeline(root,night)
            self.assertEqual(result["prediction_scope"],"RECOVERED_ORIGINAL")
            self.assertEqual(result["overall_status"],"PARTIAL")
            self.assertEqual(result["p0_score"]["formal_100m_10min_status"],"NOT_PRODUCED")
            self.assertEqual(result["p0_score"]["expected_capture_count"],4.0)
            self.assertEqual(result["p0_score"]["captures_after_cutoff"],6)
            self.assertEqual(result["p0_score"]["capture_count_absolute_error"],2.0)
            self.assertTrue(result["p0_score"]["actual_within_expected_range"])

if __name__=="__main__":
    unittest.main()
