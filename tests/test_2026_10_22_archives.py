"""October 22 historical Habu evidence integrity tests (not a P0 acceptance test)."""
from pathlib import Path
import csv
import hashlib
import json
import tempfile
import unittest
from xml.etree import ElementTree

from scripts.text_safe_byte_archive import restore_file


class October22Archives(unittest.TestCase):
    def test_original_gpx_and_generated_report_zip_restore(self):
        repo = Path(__file__).resolve().parents[1]
        paths = (
            ("gpx", "7ee4f005cc27fb3d680bd05b7de19d5e9d33241b906c545bbb356c885a2849aa", "7ee4f005cc27fb3d680bd05b7de19d5e9d33241b906c545bbb356c885a2849aa", 4675850),
            ("pdca_artifact", "3cb92409ee699bdfc6923f680398cc7297688b3ac9", "3cb92409ee699bdfc6923f680398cc7297688b3ac9f298a1c613e42693d2bfa1", 20796),
        )
        for kind, directory_name, digest, nbytes in paths:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as td:
                directory = repo / "data" / "raw" / "attachment_archives" / kind / directory_name
                self.assertTrue(directory.is_dir(), str(directory))
                raw_file = Path(td) / ("source.gpx" if kind == "gpx" else "report.zip")
                result = restore_file(directory, raw_file)
                self.assertEqual(result["raw_sha256"], digest)
                self.assertEqual(result["raw_size_bytes"], nbytes)
                self.assertEqual(hashlib.sha256(raw_file.read_bytes()).hexdigest(), digest)
                if kind == "gpx":
                    root = ElementTree.parse(raw_file).getroot()
                    count = len(root.findall(".//{http://www.topografix.com/GPX/1/1}trkpt"))
                    self.assertEqual(count, 17731)
                else:
                    import zipfile
                    with zipfile.ZipFile(raw_file) as z:
                        payload = json.loads(z.read("pdca_result.json"))
                    self.assertEqual(payload["owner_captures"], 2)
                    self.assertEqual(payload["habu_roadkills"], 1)
                    self.assertEqual(payload["capture_count_prediction_reference"]["original_p0_status"], "BLOCKED_NO_FROZEN_FORECAST")

if __name__ == "__main__":
    unittest.main()
