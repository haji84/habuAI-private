import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"))

import pdca_pipeline
import freeze_prediction

class PDCAE2ETests(unittest.TestCase):
    def _write_prediction(self, root, night, version, cutoff):
        d=root/"predictions"/"original"/night/version
        d.mkdir(parents=True)
        payload={
            "prediction_id":f"{night}-{version}",
            "operational_night":night,
            "prediction_version":version,
            "prediction_class":"ORIGINAL",
            "cutoff_time":cutoff,
            "timezone":"Asia/Tokyo",
            "targets_100m_10min":[{
                "target_id":"T1",
                "latitude":28.15,
                "longitude":129.30,
                "predicted_time_jst":"2026-09-30T21:00:00+09:00",
                "radius_m":100,
                "time_tolerance_min":10
            }]
        }
        payload["payload_sha256"]=pdca_pipeline.canonical_prediction_hash(payload)
        (d/"prediction.json").write_text(json.dumps(payload),encoding="utf-8")

    def test_single_entry_pipeline_reports_unvalidated_synthetic_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); night="2026-09-30"
            self._write_prediction(root,night,"P0","2026-09-30T20:00:00+09:00")
            self._write_prediction(root,night,"P1","2026-09-30T21:00:00+09:00")

            gpx=root/"data"/"raw"/"gpx"/"night.gpx"
            gpx.parent.mkdir(parents=True)
            gpx.write_text("""<?xml version="1.0"?>
<gpx version="1.1"><trk><trkseg>
<trkpt lat="28.15" lon="129.30"><time>2026-09-30T12:03:00Z</time></trkpt>
</trkseg></trk></gpx>""",encoding="utf-8")

            cap=root/"data"/"raw"/"capture_db"/"captures.csv"
            cap.parent.mkdir(parents=True)
            with cap.open("w",encoding="utf-8",newline="") as fh:
                w=csv.DictWriter(fh,fieldnames=["event","datetime_jst","latitude","longitude","event_id","event_count"])
                w.writeheader()
                w.writerow({"event":"capture","datetime_jst":"2026-09-30T21:03:00+09:00",
                            "latitude":"28.15","longitude":"129.30","event_id":"C1","event_count":"1"})

            result=pdca_pipeline.run_pipeline(root,night)
            self.assertEqual(result["overall_status"],"PARTIAL")
            stages = {s["name"]: s["status"] for s in result["stages"]}
            self.assertEqual(stages["candidate_validation"], "NOT_VALIDATED")
            self.assertEqual(stages["model_evaluation"], "NOT_VALIDATED")
            self.assertFalse(result["p0_score"]["strict_official_score_eligible"])
            self.assertEqual(result["p0_score"]["provenance_status"], "NOT_VALIDATED")
            self.assertEqual(result["walk_forward"], [])
            self.assertEqual(result["p0_score"]["matched_targets"],1)
            self.assertEqual(result["realtime_scores"][0]["matched_targets"],0)
            self.assertEqual(result["exposure"][0]["observation"],"UNKNOWN")
            self.assertIsNone(result["exposure"][0]["label"])
            self.assertEqual(result["feature_analysis"]["time_of_night"][0]["observed_units"],0)
            self.assertTrue((root/"reports"/"pdca"/night/"pdca_report.md").exists())

    def test_freeze_is_append_only(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); inp=root/"input.json"
            inp.write_text(json.dumps({"prediction_id":"x","cutoff_time":"2026-09-30T20:00:00+09:00",
                                       "targets_100m_10min":[]}),encoding="utf-8")
            out=freeze_prediction.freeze(root,inp,"2026-09-30","P0", now=pdca_pipeline.parse_dt("2026-09-30T20:00:00+09:00"))
            self.assertTrue(out.exists())
            payload=json.loads(out.read_text(encoding="utf-8"))
            status,_=pdca_pipeline.verify_predictions([payload])
            self.assertEqual(status,"PASS")
            with self.assertRaises(FileExistsError):
                freeze_prediction.freeze(root,inp,"2026-09-30","P0", now=pdca_pipeline.parse_dt("2026-09-30T20:00:00+09:00"))

if __name__=="__main__":
    unittest.main()
