import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote

from scripts.fetch_osm_road import (
    acquire_tiles,
    acquire_tiles_with_subdivision,
    build_overpass_query,
    process_tiles,
    recover_unreferenced_raw_rows,
    write_optional_parquet,
)


class FetchOsmRoadTests(unittest.TestCase):
    def test_query_requests_highways_and_referenced_nodes(self):
        query = build_overpass_query((28.0, 129.0, 28.1, 129.1))
        self.assertEqual(
            query,
            '[out:json][timeout:120];way["highway"](28.0000000,129.0000000,28.1000000,129.1000000);out body;>;out skel qt;',
        )

    def test_acquisition_saves_success_and_manifests_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory)
            tiles = [
                {"tile_id": "r00_c00", "bbox_south_west_north_east": (28.0, 129.0, 28.1, 129.1)},
                {"tile_id": "r00_c01", "bbox_south_west_north_east": (28.0, 129.1, 28.1, 129.2)},
            ]
            payload = json.dumps({"osm3s": {"timestamp_osm_base": "2026-09-24T00:00:00Z"}, "elements": []}).encode()

            def fetcher(url, timeout):
                if "(28.0000000,129.0000000,28.1000000,129.1000000)" in unquote(url):
                    return 200, payload, "https://overpass.test/final"
                return 500, b"server error", "https://overpass.test/final"

            rows = acquire_tiles(tiles, raw, fetcher=fetcher, endpoint="https://overpass.test/api", retry_attempts=1, sleep_seconds=0)
            self.assertEqual([row["status"] for row in rows], ["downloaded", "http_error"])
            saved = raw / "r00_c00.json"
            self.assertEqual(saved.read_bytes(), payload)
            self.assertEqual(rows[0]["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(rows[0]["osm_base_timestamp"], "2026-09-24T00:00:00Z")
            self.assertFalse((raw / "r00_c01.json").exists())

    def test_cached_tile_is_reused_without_network_call(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory)
            payload = json.dumps({"elements": []}).encode()
            (raw / "r00_c00.json").write_bytes(payload)
            tiles = [{"tile_id": "r00_c00", "bbox_south_west_north_east": (28.0, 129.0, 28.1, 129.1)}]

            def forbidden_fetcher(url, timeout):
                raise AssertionError("network called for cached tile")

            rows = acquire_tiles(tiles, raw, fetcher=forbidden_fetcher, endpoint="https://overpass.test/api", retry_attempts=1, sleep_seconds=0)
            self.assertEqual(rows[0]["status"], "cached")

    def test_unreferenced_raw_is_recovered_with_bbox_and_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory)
            payload = json.dumps({"elements": []}).encode()
            path = raw / "r00_c00_s00.json"
            path.write_bytes(payload)
            roots = [{"tile_id": "r00_c00", "bbox_south_west_north_east": (0.0, 0.0, 1.0, 1.0)}]
            rows = recover_unreferenced_raw_rows(raw, [], roots, "https://overpass.test/api")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["status"], "retained_superseded_raw")
            self.assertEqual(json.loads(rows[0]["bbox_south_west_north_east"]), [0.0, 0.0, 0.5, 0.5])
            self.assertEqual(rows[0]["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(rows[0]["retrieval_time_status"], "filesystem_mtime_recovered")

    def test_timed_out_tile_is_subdivided_and_children_cover_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory)
            tile = {"tile_id": "r00_c00", "bbox_south_west_north_east": (28.0, 129.0, 28.2, 129.2)}
            payload = json.dumps({"elements": []}).encode()

            def fetcher(url, timeout):
                decoded = unquote(url)
                if "(28.0000000,129.0000000,28.2000000,129.2000000)" in decoded:
                    return 504, b"timeout", "https://overpass.test/final"
                return 200, payload, "https://overpass.test/final"

            rows = acquire_tiles_with_subdivision(
                [tile], raw, fetcher=fetcher, endpoint="https://overpass.test/api",
                retry_attempts=1, sleep_seconds=0, max_subdivide_depth=1,
                request_timeout_seconds=45,
            )
            self.assertEqual(rows[0]["status"], "subdivided_after_http_error")
            children = rows[1:]
            self.assertEqual(len(children), 4)
            self.assertTrue(all(row["status"] == "downloaded" for row in children))
            self.assertTrue(all(row["parent_tile_id"] == "r00_c00" for row in children))
            self.assertTrue(all(row["request_timeout_seconds"] == 45 for row in children))

    def test_subdivision_does_not_query_children_outside_target_polygon(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory)
            tile = {"tile_id": "root", "bbox_south_west_north_east": (0.0, 0.0, 1.0, 1.0)}
            polygons = [[[[0.1, 0.1], [0.4, 0.1], [0.4, 0.4], [0.1, 0.4], [0.1, 0.1]]]]
            payload = json.dumps({"elements": []}).encode()
            calls = []

            def fetcher(url, timeout):
                calls.append(unquote(url))
                if len(calls) == 1:
                    return 504, b"timeout", "https://overpass.test/final"
                return 200, payload, "https://overpass.test/final"

            rows = acquire_tiles_with_subdivision(
                [tile], raw, fetcher=fetcher, endpoint="https://overpass.test/api",
                retry_attempts=1, sleep_seconds=0, max_subdivide_depth=1,
                target_polygons=polygons,
            )
            self.assertEqual(len(calls), 2)
            self.assertEqual(sum(row["status"] == "downloaded" for row in rows), 1)
            self.assertEqual(sum(row["status"] == "outside_target_polygon" for row in rows), 3)

    def test_processing_writes_centerlines_and_only_normal_route_cells(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw"
            processed = root / "processed"
            evidence = root / "evidence"
            raw.mkdir()
            tile = {
                "elements": [
                    {"type": "way", "id": 1, "nodes": [10, 11], "tags": {"highway": "track"}},
                    {"type": "way", "id": 2, "nodes": [12, 13], "tags": {"highway": "track", "access": "private"}},
                    {"type": "node", "id": 10, "lat": 28.0000, "lon": 128.9890},
                    {"type": "node", "id": 11, "lat": 28.0000, "lon": 129.0010},
                    {"type": "node", "id": 12, "lat": 28.0010, "lon": 129.0000},
                    {"type": "node", "id": 13, "lat": 28.0010, "lon": 129.0010},
                ]
            }
            (raw / "r00_c00.json").write_text(json.dumps(tile), encoding="utf-8")
            (raw / "retained_old.json").write_text(json.dumps({"elements": []}), encoding="utf-8")
            acquisition_manifest = root / "osm_acquisition_manifest.csv"
            acquisition_manifest.write_text("tile_id,status\nr00_c00,downloaded\n", encoding="utf-8")
            boundary = root / "boundary.geojson"
            boundary.write_text(json.dumps({
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "properties": {"osm_id": 4098976},
                    "geometry": {"type": "Polygon", "coordinates": [[
                        [128.99, 27.99], [129.02, 27.99], [129.02, 28.02], [128.99, 28.02], [128.99, 27.99]
                    ]]},
                }],
            }), encoding="utf-8")
            manifest_rows = [{"tile_id": "r00_c00", "status": "downloaded", "saved_path": str(raw / "r00_c00.json")}]
            summary = process_tiles(raw, boundary, processed, evidence, manifest_rows, target_relation_ids={4098976}, parquet_writer=None)
            lines = [json.loads(line) for line in (processed / "osm_road_centerlines.geojsonl").read_text().splitlines()]
            self.assertEqual({line["properties"]["osm_way_id"] for line in lines}, {1, 2})
            with (processed / "osm_road_candidate_cells.csv").open(encoding="utf-8-sig", newline="") as handle:
                cells = list(csv.DictReader(handle))
            self.assertTrue(cells)
            self.assertTrue(all("2" not in row["osm_way_ids"] for row in cells))
            self.assertTrue(all(row["island_osm_relation_id"] == "4098976" for row in cells))
            self.assertTrue(all(row["island_name"] == "奄美大島" for row in cells))
            self.assertEqual(summary["ways_inside_target"], 2)
            self.assertEqual(summary["normal_route_ways_inside_target"], 1)
            self.assertEqual(summary["normal_route_ways_by_highway"], {"track": 1})
            self.assertEqual(summary["restricted_or_nonvehicle_ways_by_status"], {"restricted": 1})
            self.assertEqual(summary["parquet_status"], "unavailable_no_writer")
            self.assertEqual(summary["candidate_cells_by_island"], {"奄美大島": len(cells)})
            self.assertTrue((evidence / "osm_road_evidence_manifest.csv").exists())
            evidence_text = (evidence / "osm_road_evidence_manifest.csv").read_text(encoding="utf-8-sig")
            self.assertIn("osm_acquisition_manifest.csv", evidence_text)
            self.assertIn("retained_old.json", evidence_text)

    def test_optional_parquet_does_not_create_fake_file_without_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cells.parquet"
            status = write_optional_parquet([{"cell_id": "x"}], path, writer=None)
            self.assertEqual(status, "unavailable_no_writer")
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
