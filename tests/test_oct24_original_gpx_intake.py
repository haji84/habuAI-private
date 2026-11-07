"""Oct24 real GPX source bytes are preserved, exactly reassembled and non-interpolated."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from verify_oct24_source_intake import verify,CASES,SRC

class OriginalGPXByteIntegrity(unittest.TestCase):
    def test_byte_identical_source_archive_and_exact_original_gps_points(self):
        confirmed=verify()
        self.assertEqual(len(confirmed),2)
        self.assertEqual([count for _path,_sha,count in confirmed],[202,20689])
        self.assertEqual(sum(count for _path,_sha,count in confirmed),20891)
        self.assertEqual([sha for _path,sha,_count in confirmed],[x[2] for x in CASES])

    def test_derived_event_review_csv_sha_and_source_role_separation(self):
        import csv,hashlib
        path=ROOT/"evidence/recovered_sources/2026-10-24-capture-and-fauna-source-review.csv"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                         "d5b07cec456bd4aeaf1bfce3037919eba88949181126462e7d61595d9e8eb95f")
        with path.open(encoding="utf-8-sig",newline="") as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),39)
        captures=[x for x in rows if x["kind"]=="捕獲"]
        sightings=[x for x in rows if x["kind"]=="目撃"]
        roadkills=[x for x in rows if x["kind"]=="轢死"]
        self.assertEqual((len(captures),len(sightings),len(roadkills)),(4,32,3))
        self.assertEqual(sum(int(x["quantity"]) for x in captures),4)
        self.assertEqual(sum(int(x["quantity"]) for x in sightings),34)
        self.assertEqual(sum(x["species_or_description"]=="ハブ" for x in roadkills),1)
        self.assertEqual(captures[0]["gpx_observation_quality"],"TIME_GAP_UNOBSERVED")
        self.assertTrue(all(c["gpx_observation_quality"]=="SUPPORTED_EVENT_TIME_SPACE" for c in captures[1:]))
        self.assertTrue(all(not x["training_label"] for x in rows))

    def test_21_parts_and_no_synthetic_gap_points(self):
        fragments=sorted((SRC/CASES[1][0]).glob("part_???.gpxfrag"))
        self.assertEqual(len(fragments),21)
        self.assertEqual([int(f.stem.split("_")[-1]) for f in fragments],list(range(21)))
        self.assertFalse(any((SRC/CASES[1][0]/x).exists() for x in ("predicted.gpx","filled-gap.gpx")))
        self.assertEqual(CASES[0][1]+CASES[1][1],5522059)

if __name__=="__main__":
    unittest.main()
