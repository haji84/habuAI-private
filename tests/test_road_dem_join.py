"""DEM road joining requires real hashes, trustworthy availability, no fabricated coverage."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from road_dem_join import (join_road_dem, digest_file, TerrainSourceError,
                           read_esri_ascii, sample_gradient)


class RoadDemJoinTests(unittest.TestCase):
    def fixtures(self, directory: Path):
        road = directory / "roads.csv"
        with road.open("w", newline="") as f:
            out = csv.DictWriter(f, fieldnames=[
                "cell_id", "cell_center_x", "cell_center_y",
                "candidate_source", "road_direction_deg", "island_name"])
            out.writeheader()
            out.writerow({"cell_id": "utm52n_100m_5002_31002",
                          "cell_center_x": 500250, "cell_center_y": 3100250,
                          "candidate_source": "osm_auxiliary",
                          "road_direction_deg": 90, "island_name": "奄美大島"})
            out.writerow({"cell_id": "utm52n_100m_5010_31002",
                          "cell_center_x": 501050, "cell_center_y": 3100250,
                          "candidate_source": "osm_auxiliary",
                          "road_direction_deg": 0, "island_name": "加計呂麻島"})
        dem = directory / "dem.asc"
        header = """ncols 5
nrows 5
xllcorner 500000
yllcorner 3100000
cellsize 100
NODATA_value -9999
"""
        # Actual terrain values are synthetic only within these isolated unit tests.
        dem.write_text(header + "\n".join(
            " ".join(str(v) for v in row) for row in
            [[40]*5, [30]*5, [20]*5, [10]*5, [0]*5]) + "\n")
        return road, dem

    def join(self, road, dem, **extra):
        opts = dict(
            road_sha256=digest_file(road), dem_sha256=digest_file(dem),
            dem_epsg=32652, road_available_at="2026-10-23T12:00:00+09:00",
            dem_available_at="2026-10-23T12:00:00+09:00",
            cutoff_time="2026-10-24T17:00:00+09:00",
            wind_from_deg=0)
        opts.update(extra)
        return join_road_dem(road, dem, **opts)

    def test_gradient_bearing_and_coverage_are_source_bound(self):
        with tempfile.TemporaryDirectory() as t:
            road, dem = self.fixtures(Path(t))
            result = self.join(road, dem)
            self.assertEqual(result["status"], "SOURCE_JOIN_PARTIAL")
            self.assertEqual(result["coverage_cells"], 1)
            self.assertEqual(result["missing_cells"], 1)
            self.assertFalse(result["formal_p0_eligible"])
            cell = result["cells"][0]
            self.assertAlmostEqual(cell["elevation_m"], 20.0)
            self.assertGreater(cell["slope_deg"], 0)
            self.assertAlmostEqual(cell["aspect_downslope_deg"], 180.0)
            self.assertAlmostEqual(cell["tpi_3x3_m"], 0.0)
            self.assertAlmostEqual(cell["wind_cross_road_geometry_proxy"], 1.0)
            self.assertFalse(cell["terrain_wind_shielding_verified"])
            self.assertEqual(result["cells"][1]["status"], "UNKNOWN_DEM_COVERAGE")

    def test_late_availability_blocks_forward_prediction(self):
        with tempfile.TemporaryDirectory() as t:
            road, dem = self.fixtures(Path(t))
            with self.assertRaises(TerrainSourceError):
                self.join(road, dem, dem_available_at="2026-10-24T18:00:00+09:00")

    def test_hash_mismatch_blocks_source(self):
        with tempfile.TemporaryDirectory() as t:
            road, dem = self.fixtures(Path(t))
            with self.assertRaises(TerrainSourceError):
                self.join(road, dem, dem_sha256="f"*64)

    def test_unknown_projection_must_not_be_assumed(self):
        with tempfile.TemporaryDirectory() as t:
            road, dem = self.fixtures(Path(t))
            with self.assertRaises(TerrainSourceError):
                self.join(road, dem, dem_epsg=4326)

    def test_missing_dem_cannot_be_filled_in(self):
        with tempfile.TemporaryDirectory() as t:
            road, dem = self.fixtures(Path(t))
            content = dem.read_text().replace("20 20 20 20 20", "20 20 -9999 20 20")
            dem.write_text(content)
            result = self.join(road, dem)
            self.assertEqual(result["missing_cells"], 2)

    def test_source_grid_alignment_must_match_ids(self):
        with tempfile.TemporaryDirectory() as t:
            road, dem = self.fixtures(Path(t))
            content = road.read_text().replace("utm52n_100m_5002_31002",
                                               "utm52n_100m_5003_31002")
            road.write_text(content)
            with self.assertRaises(TerrainSourceError):
                self.join(road, dem)

    def test_dem_reader_rejects_invalid_dimensions(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "invalid.asc"
            path.write_text("ncols 1\nnrows 1\nxllcorner 1\nyllcorner 1\ncellsize 100\nNODATA_value -9999\n1")
            with self.assertRaises(TerrainSourceError):
                read_esri_ascii(path)


if __name__ == "__main__":
    unittest.main()
