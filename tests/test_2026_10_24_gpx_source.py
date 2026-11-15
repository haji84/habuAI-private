"""Verify 2026-10-24 original GPX is perfectly recoverable, not a fabricated joined track."""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from scripts.verify_2026_10_24_source_gpx import (
    ROOT, MANIFEST, OriginalGpxError, verify,
)

class October24RawGpxSourceTests(unittest.TestCase):
    def test_source_sha_and_track_preservation(self):
        report=verify(ROOT)
        self.assertEqual(report["status"],"ORIGINAL_BYTES_VERIFIED")
        self.assertEqual(report["original_point_counts"],{"0":202,"1":20689})
        self.assertEqual(report["verified_original_gpx_bytes"],5522059)
        self.assertAlmostEqual(report["verified_unmeasured_gap_seconds"],4054,places=1)
        self.assertFalse(report["interpolation_performed"])
        self.assertEqual(report["eligible_negative_labels"],0)
        self.assertEqual(report["formal_pdca_prediction_score"],"BLOCKED_NO_ORIGINAL_P0")
        self.assertEqual(report["source_sha256"],[
            "ab20c54e4fb7083156933629aec8259899b7c4bac5ba30a3112502da7686f314",
            "e7a93f4046ec114f3e191ee0bbe49fd238129913f29620147243cac993fce7f1"])

    def test_reassembled_original_is_byte_exact_and_not_interpolated(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/"recovered_source_segment_B.gpx"
            verify(ROOT,output=target)
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(),
                "e7a93f4046ec114f3e191ee0bbe49fd238129913f29620147243cac993fce7f1")
            self.assertEqual(target.stat().st_size,5468818)

    def test_missing_part_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            manifest=json.loads((ROOT/MANIFEST).read_text(encoding="utf-8"))
            entries=[manifest["original_files"][0]["path"]]
            entries += [p["path"] for p in manifest["original_files"][1]["parts"]]
            for rel in entries:
                src=ROOT/rel
                dest=root/rel
                dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(src,dest)
            path=root/MANIFEST
            path.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/MANIFEST,path)
            broken=root/entries[5]
            broken.unlink()
            with self.assertRaises(OriginalGpxError):
                verify(root)
            shutil.copyfile(ROOT/entries[5],broken)
            with broken.open("ab") as file:
                file.write(b"fabricated")
            with self.assertRaises(OriginalGpxError):
                verify(root)

    def test_metadata_keeps_owner_field_note_anchors_distinct_from_gpx(self):
        manifest=json.loads((ROOT/MANIFEST).read_text(encoding="utf-8"))
        self.assertEqual(manifest["gps_gap"]["observed_original_segments"],2)
        self.assertFalse(manifest["gps_gap"]["interpolate_or_insert_gpx_points"])
        self.assertFalse(manifest["gps_gap"]["fill_missing_gpx_from_sightings"])
        self.assertEqual(manifest["training"]["formal_negative_labels"],0)
        self.assertEqual(manifest["training"]["formal_positive_labels"],0)
        self.assertFalse(manifest["training"]["actual_prediction_p0_available"])
        self.assertEqual(len(manifest["original_files"][1]["parts"]),21)

if __name__=="__main__":
    unittest.main()
