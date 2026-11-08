"""Evidence matrix must not infer a capture-free night from GPS alone."""
import csv
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from build_gpx_outcome_source_matrix import build_source_matrix, SourceMatrixError


class MatrixTests(unittest.TestCase):
    def test_actual_thirteen_file_crosswalk(self):
        result=build_source_matrix(ROOT)
        self.assertEqual(result["raw_file_count"],13)
        self.assertEqual(result["raw_point_count"],243747)
        self.assertEqual(result["august_nights"],12)
        self.assertEqual(result["september_nights"],1)
        self.assertEqual(result["unique_nights"],13)
        self.assertEqual(len(result["nights"]),13)
        self.assertEqual(sum(row["night"]=="2026-08-31" for row in result["nights"]),1)
        self.assertEqual(result["status"],"BLOCKED_MISSING_COMPLETE_OUTCOMES_AND_EXANTE_FEATURES")
        self.assertEqual(result["category_counts"],{"OUTCOME_LEDGER_MISSING":13})
        self.assertEqual(result["verified_positive_training_rows"],0)
        self.assertEqual(result["verified_negative_training_rows"],0)
        self.assertIs(result["original_p0_issued"],False)
        derived = {
            "capture_event_ledger": ("capture_events",413,
                "137c04b5abe6713c1668633fe10afa61f601a5c0a8d5331471d71f8cbf0a972f"),
            "individual_ledger": ("individuals",378,
                "6d0c01d185722044bf976f2858461990518dffe6ee402815269ad94f5f242947"),
        }
        for row in result["nights"]:
            with self.subTest(night=row["night"]):
                self.assertIs(row["training_eligible"],False)
                self.assertIs(row["official_kpi_eligible"],False)
                self.assertEqual(row["classification"],"OUTCOME_LEDGER_MISSING")
                self.assertEqual(row["positive"],"UNKNOWN_UNTIL_INDIVIDUAL_EVENT_VALIDATION")
                self.assertEqual(row["negative"],"UNKNOWN_UNTIL_SEARCH_EFFORT_AND_COMPLETE_OUTCOME")
                expected = {"raw_owner_habu_log":{"present":False,"sha256":None}}
                for role, (_, _, digest) in derived.items():
                    present = row["night"]=="2026-08-31"
                    expected[role] = {"present":present,"sha256":digest if present else None}
                self.assertEqual(row["sources"],expected)
                for role in expected:
                    self.assertIs(row["sources"][role]["present"],expected[role]["present"])

        # These are two derived source-record selectors, not permanent animal IDs
        # or evidence of complete outcomes/search exposure for this night.
        records = {}
        for role, (folder, size, digest) in derived.items():
            raw=(ROOT/f"data/processed/{folder}/2026/2026-08-31.csv").read_bytes()
            self.assertEqual(len(raw),size)
            self.assertEqual(hashlib.sha256(raw).hexdigest(),digest)
            records[role]=list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
            self.assertEqual(len(records[role]),2)
            self.assertEqual([r["operational_date"] for r in records[role]],
                             ["2026-08-31","2026-08-31"])
        events=records["capture_event_ledger"]
        occurrences=records["individual_ledger"]
        event_ids=["AUG31SRC-L10110","AUG31SRC-L10492"]
        self.assertEqual([r["event_id"] for r in events],event_ids)
        self.assertEqual([r["event_type"] for r in events],["capture","capture"])
        self.assertEqual([r["event_count"] for r in events],["1","1"])
        self.assertEqual([r["event_id"] for r in occurrences],event_ids)
        self.assertEqual([r["individual_id"] for r in occurrences],
                         [event_id+"-OCC01" for event_id in event_ids])
        self.assertEqual([r["individual_index"] for r in occurrences],["1","1"])

    def test_gpx_qc_registry_tampering_is_rejected(self):
        # A standalone fixture deliberately has no 13 real source files:
        # the matrix must never report such a fabricated roster as complete.
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"evidence/legacy/habuAI-public/v2_actual_gpx_13night_qc.csv"
            p.parent.mkdir(parents=True)
            p.write_text("operational_night,gps_points,sha256\n2026-08-12,10,fake\n")
            with self.assertRaises(SourceMatrixError):
                build_source_matrix(root)


if __name__=="__main__":
    unittest.main()
