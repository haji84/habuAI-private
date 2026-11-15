"""Oct24 original two-GPX source conservation and no invented missing route."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from verify_oct24_gpx_intake import verify,restore_second_gpx,Oct24GPXSourceError,SOURCE_ROOT

class Oct24SourcePreservationTests(unittest.TestCase):
    def test_original_two_gpx_sources_and_67min34sec_gap(self):
        evidence=verify(ROOT)
        self.assertEqual(evidence["status"],"EXACT_ORIGINAL_TWO_GPXS_PRESERVED_IN_INCOMING")
        self.assertEqual(evidence["first"]["raw_points"],202)
        self.assertEqual(evidence["second"]["raw_points"],20689)
        self.assertEqual(evidence["total_original_gpx_points"],20891)
        self.assertEqual(evidence["gpx_gap_seconds_rounded"],4054)
        self.assertEqual(evidence["first"]["source_size_bytes"],53241)
        self.assertEqual(evidence["second"]["source_size_bytes"],5468818)
        self.assertEqual(evidence["first"]["source_sha256"],
                         "ab20c54e4fb7083156933629aec8259899b7c4bac5ba30a3112502da7686f314")
        self.assertEqual(evidence["second"]["source_sha256"],
                         "e7a93f4046ec114f3e191ee0bbe49fd238129913f29620147243cac993fce7f1")
        self.assertFalse(evidence["original_p0_verified"])
        self.assertFalse(evidence["nightly_search_effort_certified"])
        self.assertEqual(evidence["new_scientific_negative_labels"],0)

    def test_byte_reconstitution_and_per_part_sha(self):
        manifest=json.loads((ROOT/SOURCE_ROOT/"source_manifest.json").read_text(encoding="utf-8"))
        split=manifest["source_gpx_files"][1]
        self.assertEqual(len(split["parts"]),21)
        self.assertEqual(sum(e["size_bytes"] for e in split["parts"]),5468818)
        original=restore_second_gpx(ROOT,split)
        self.assertEqual(len(original),5468818)
        self.assertEqual(sum(original.count(x) for x in (b"\n",)),20702)
        self.assertTrue(original.endswith(b"</gpx>"))

    def test_missing_chunk_or_tampered_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            fake=Path(folder)
            target=fake/SOURCE_ROOT
            target.mkdir(parents=True)
            shutil.copyfile(ROOT/SOURCE_ROOT/"source_manifest.json",target/"source_manifest.json")
            incoming=fake/SOURCE_ROOT/"2026-10-24-0834_original.gpx.parts"
            incoming.mkdir(parents=True)
            original=json.loads((target/"source_manifest.json").read_text())["source_gpx_files"][1]
            with self.assertRaisesRegex(Oct24GPXSourceError,"Missing original GPX fragment"):
                restore_second_gpx(fake,original)
            src=ROOT/SOURCE_ROOT/"2026-10-24-0834_original.gpx.parts/part_000.txt"
            dest=incoming/"part_000.txt"
            dest.write_bytes(src.read_bytes()+b"\n")
            with self.assertRaisesRegex(Oct24GPXSourceError,"fragment digest/length mismatch"):
                restore_second_gpx(fake,original)

    def test_science_source_remains_incoming_not_promoted(self):
        manifest=json.loads((ROOT/SOURCE_ROOT/"source_manifest.json").read_text())
        self.assertEqual(manifest["raw_status"],"INCOMING_ONLY_NOT_CANONICAL_OR_SCIENTIFIC_EXPOSURE")
        self.assertTrue(manifest["gap"]["no_interpolation"])
        self.assertEqual(manifest["registration"]["science_negative_eligible"],0)
        self.assertEqual(manifest["registration"]["science_positive_eligible"],0)
        self.assertTrue(manifest["registration"]["original_p0_missing"])
        self.assertFalse(manifest["registration"]["source_upload_location"].startswith("data/raw"))
        self.assertNotIn("negative",manifest["source_gpx_files"][1]["storage_mode"].lower())

if __name__=="__main__":
    unittest.main()
