"""Evidence matrix must not infer a capture-free night from GPS alone."""
import csv
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
        self.assertEqual(result["verified_positive_training_rows"],0)
        self.assertEqual(result["verified_negative_training_rows"],0)
        self.assertFalse(result["original_p0_issued"])
        for row in result["nights"]:
            self.assertFalse(row["training_eligible"])
            self.assertNotEqual(row["negative"],"0")
            self.assertFalse(row["sources"]["raw_owner_habu_log"]["present"])
            self.assertFalse(row["sources"]["capture_event_ledger"]["present"])
            self.assertFalse(row["sources"]["individual_ledger"]["present"])

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
