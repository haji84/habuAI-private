"""Real GSI DEM tiles are verified before being promoted as source evidence."""
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("gsi_dem_probe_test",ROOT/"scripts/gsi_dem_source_probe.py")
probe=importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class DemSourceProbeTests(unittest.TestCase):
    def png(self):
        image=Image.new("RGB",(256,256),(0,39,16)) # +100.00m
        image.putpixel((0,0),(128,0,0)) # no data
        buf=io.BytesIO();image.save(buf,format="PNG");return buf.getvalue()

    def test_gsi_official_rgb_signed_dem_formula(self):
        self.assertIsNone(probe.decode_rgb((128,0,0)))
        self.assertEqual(probe.decode_rgb((0,39,16)),100.0)
        self.assertEqual(probe.decode_rgb((255,216,240)),-100.0)

    def test_capture_both_island_tiles_preserves_raw_sha(self):
        blob=self.png()
        with tempfile.TemporaryDirectory() as td:
            result=probe.acquire(Path(td),downloader=lambda u:blob)
            self.assertEqual(len(result["samples"]),2)
            self.assertFalse(result["full_road_cell_coverage"])
            self.assertFalse(result["official_original_p0_issued"])
            for record in result["samples"]:
                path=Path(td)/record["relative_path"]
                self.assertEqual(path.read_bytes(),blob)
                self.assertEqual(record["valid_pixels"],256*256-1)
                self.assertEqual(record["nodata_pixels"],1)
                self.assertEqual(record["elevation_min_m"],100.0)
                self.assertTrue(record["source"].startswith(probe.BASE+"/"))

    def test_no_data_tile_rejected(self):
        image=Image.new("RGB",(256,256),(128,0,0));buf=io.BytesIO();image.save(buf,format="PNG")
        with self.assertRaises(probe.DemProbeError):
            probe.validate_png(buf.getvalue())

    def test_invalid_tile_is_never_archived(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(probe.DemProbeError):
                probe.acquire(Path(td),downloader=lambda u:b'not_png')
            self.assertFalse((Path(td)/"evidence").exists())

    def test_slippy_mercator_mapping_valid(self):
        x,y,px,py=probe.tile(28.333,129.460,14)
        self.assertTrue(0<=x<2**14 and 0<=y<2**14)
        self.assertTrue(0<=px<256 and 0<=py<256)
        with self.assertRaises(probe.DemProbeError):
            probe.tile(100.0,129.46,14)


if __name__=="__main__":
    unittest.main()
