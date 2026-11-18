"""Private environment evidence only; no real route or on-road GPS leaves private storage."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
sys.path.insert(0, str(ROOT/"scripts"))

from private_count_clock_comparison import compare_private_sources
from private_pdca_intake import IntakeError


class PrivateEnvironmentReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        p=Path(self.temp.name)
        self.repo=p/"public-code"
        self.repo.mkdir()
        self.private=p/"owner-only"
        self.private.mkdir(mode=0o700)
        (self.private/"models").mkdir()
        counts=[1,0,2,3,2,1,7]
        self.count={
            "schema_version":"habu-research-nightcount-poisson-v1.2",
            "nights":7,"owner_captures":sum(counts),
            "elapsed_session_hours_proxy":35.0,
            "training_nights":[
                {"night":f"2026-10-{i+1:02d}","count":n,"effort_hours_proxy":5.0}
                for i,n in enumerate(counts)],
        }
        self.env={"schema_version":"habu-cooling-retrospective-audit-v1",
                  "records":[
                      {"night":"2026-10-03","owner_captures":2,
                       "session_elapsed_proxy_h":5.0,
                       "captured_not_no_capture_negative":True,
                       "temp_source":"JMA_KONIYA_CALENDAR_DAY_MIN_NOT_HUNT_TIME",
                       "station_day_min_c":21.4},
                      {"night":"2026-10-07","owner_captures":7,
                       "session_elapsed_proxy_h":5.0,
                       "captured_not_no_capture_negative":True,
                       "temp_source":"JMA_KONIYA_HOURLY",
                       "station_15_c":25.4,"station_20_c":22.0,
                       "station_15_to_20_delta_c":-3.4},
                  ]}
        (self.private/"models"/"count.json").write_text(json.dumps(self.count),encoding="utf-8")
        (self.private/"models"/"environment.json").write_text(json.dumps(self.env),encoding="utf-8")

    def run_analysis(self):
        return compare_private_sources(self.private, repo_root=self.repo,
                  nightcount="models/count.json",environment="models/environment.json")

    def test_real_feature_diagnostics_are_privately_sealed_without_model_promotion(self):
        result=self.run_analysis()
        self.assertEqual(result,self.run_analysis())
        self.assertEqual(result["analyses"]["environment"]["sample_size"],2)
        self.assertEqual(result["analyses"]["environment"]["candidate_decisions"],["NOT_VALIDATED"])
        output=self.private/"research"/(result["report_id"]+".json")
        self.assertTrue(output.is_file())
        data=json.loads(output.read_text(encoding="utf-8"))
        feature=data["analyses"]["environment"]
        self.assertIn("2026-10-02",feature["extreme_nights_without_environment"])
        self.assertFalse(feature["predictive_improvement_proven"])
        self.assertFalse(feature["champion_promotion_allowed"])
        self.assertFalse(data["production_champion_activated"])
        self.assertFalse((self.repo/"research").exists())

    def test_environment_requires_count_and_same_captures(self):
        with self.assertRaises(IntakeError):
            compare_private_sources(self.private, repo_root=self.repo,
                                    environment="models/environment.json")
        env=self.env.copy()
        env["records"]=[dict(x) for x in self.env["records"]]
        env["records"][0]["owner_captures"]+=1
        (self.private/"models"/"environment.json").write_text(json.dumps(env),encoding="utf-8")
        with self.assertRaises(ValueError):
            self.run_analysis()
        self.assertFalse((self.private/"research").exists())


if __name__=="__main__":
    unittest.main()
