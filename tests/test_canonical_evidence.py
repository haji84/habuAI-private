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

class CanonicalEvidenceTests(unittest.TestCase):
    def test_canonical_capture_event_count_expands_individuals(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"data"/"processed"/"capture_events"/"2026"/"2026-09-28.csv"
            p.parent.mkdir(parents=True)
            with p.open("w",encoding="utf-8",newline="") as fh:
                w=csv.DictWriter(fh,fieldnames=["event_id","operational_date","event_time_local","event_type","event_count","latitude","longitude"])
                w.writeheader()
                w.writerow({"event_id":"CAP-X","operational_date":"2026-09-28","event_time_local":"2026-09-29T00:00:00+09:00",
                            "event_type":"capture","event_count":"2","latitude":"28.1675","longitude":"129.2997"})
            rows=pdca_pipeline.load_captures(root)
            self.assertEqual(len(rows),2)
            self.assertEqual({r["event_id"] for r in rows},{"CAP-X#1","CAP-X#2"})
            self.assertTrue(all(r["night_date"]=="2026-09-28" for r in rows))

    def test_line_archive_is_sha_verified_and_read_as_gpx(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            archive=root/"data"/"raw"/"gpx_archives"/"night.gpx.lines"
            archive.mkdir(parents=True)
            lines=[
                '<?xml version="1.0"?>',
                '<gpx version="1.1"><trk><trkseg>',
                '<trkpt lat="28.15" lon="129.30"><time>2026-09-28T12:00:00Z</time></trkpt>',
                '</trkseg></trk></gpx>'
            ]
            raw="\n".join(lines).encode("utf-8")
            (archive/"part_000.txt").write_text("\n".join(lines[:2]),encoding="utf-8")
            (archive/"part_001.txt").write_text("\n".join(lines[2:]),encoding="utf-8")
            manifest={
                "part_glob":"part_*.txt","part_count":2,"encoding":"utf-8",
                "raw_size_bytes":len(raw),"raw_sha256":hashlib.sha256(raw).hexdigest()
            }
            (archive/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
            pts=pdca_pipeline.load_gpx_points(root)
            self.assertEqual(len(pts),1)
            self.assertEqual(pts[0]["night_date"],"2026-09-28")
            self.assertEqual(pts[0]["gpx_sha256"],manifest["raw_sha256"])

if __name__=="__main__":
    unittest.main()
