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

    def test_21_parts_and_no_synthetic_gap_points(self):
        fragments=sorted((SRC/CASES[1][0]).glob("part_???.gpxfrag"))
        self.assertEqual(len(fragments),21)
        self.assertEqual([int(f.stem.split("_")[-1]) for f in fragments],list(range(21)))
        self.assertFalse(any((SRC/CASES[1][0]/x).exists() for x in ("predicted.gpx","filled-gap.gpx")))
        self.assertEqual(CASES[0][1]+CASES[1][1],5522059)

if __name__=="__main__":
    unittest.main()
