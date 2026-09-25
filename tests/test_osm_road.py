import unittest

from src.osm_road import (
    aggregate_road_cells,
    build_bbox_tiles,
    classify_vehicle_route,
    deduplicate_elements,
    load_target_polygons,
    parse_overpass_elements,
    partition_tiles_by_target_bbox,
    partition_tiles_by_target_polygon,
    point_in_multipolygon,
    prepare_polygons,
    reconstruct_way_parts,
    segment_grid_contributions_xy,
)


class OsmRoadTests(unittest.TestCase):
    def test_bbox_tiles_cover_extent_without_gaps(self):
        rows = build_bbox_tiles((129.0, 28.0, 129.2, 28.2), columns=2, rows=2)
        self.assertEqual(
            [(row["tile_id"], row["bbox_south_west_north_east"]) for row in rows],
            [
                ("r00_c00", (28.0, 129.0, 28.1, 129.1)),
                ("r00_c01", (28.0, 129.1, 28.1, 129.2)),
                ("r01_c00", (28.1, 129.0, 28.2, 129.1)),
                ("r01_c01", (28.1, 129.1, 28.2, 129.2)),
            ],
        )

    def test_tiles_outside_target_polygon_bbox_are_skipped_conservatively(self):
        tiles = [
            {"tile_id": "inside", "bbox_south_west_north_east": (0.0, 0.0, 1.0, 1.0)},
            {"tile_id": "outside", "bbox_south_west_north_east": (2.0, 2.0, 3.0, 3.0)},
        ]
        polygons = [[[[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8], [0.2, 0.2]]]]
        selected, skipped = partition_tiles_by_target_bbox(tiles, polygons)
        self.assertEqual([row["tile_id"] for row in selected], ["inside"])
        self.assertEqual(skipped, [{
            "tile_id": "outside",
            "bbox_south_west_north_east": (2.0, 2.0, 3.0, 3.0),
            "status": "outside_target_polygon_bbox",
        }])

    def test_exact_tile_polygon_intersection_excludes_bbox_only_overlap(self):
        tiles = [
            {"tile_id": "triangle", "bbox_south_west_north_east": (0.1, 0.1, 0.2, 0.2)},
            {"tile_id": "bbox_only", "bbox_south_west_north_east": (0.8, 0.8, 0.9, 0.9)},
            {"tile_id": "crossed_by_edge", "bbox_south_west_north_east": (0.0, 0.0, 1.0, 1.0)},
        ]
        triangle = [[[0, 0], [1, 0], [0, 1], [0, 0]]]
        vertical_strip = [[[0.4, -1], [0.6, -1], [0.6, 2], [0.4, 2], [0.4, -1]]]
        polygons = [[[(float(x), float(y)) for x, y in triangle[0]]], [[(float(x), float(y)) for x, y in vertical_strip[0]]]]
        selected, skipped = partition_tiles_by_target_polygon(tiles, polygons)
        self.assertEqual([row["tile_id"] for row in selected], ["triangle", "crossed_by_edge"])
        self.assertEqual([row["tile_id"] for row in skipped], ["bbox_only"])

    def test_parse_and_deduplicate_prefers_greater_version(self):
        first = {
            "elements": [
                {"type": "node", "id": 1, "lat": 28.0, "lon": 129.0, "version": 1},
                {"type": "way", "id": 8, "nodes": [1], "version": 1, "tags": {"highway": "track"}},
            ]
        }
        second = {
            "elements": [
                {"type": "way", "id": 8, "nodes": [1], "version": 2, "tags": {"highway": "service"}},
            ]
        }
        merged = deduplicate_elements(parse_overpass_elements(first) + parse_overpass_elements(second))
        self.assertEqual(merged[("way", 8)]["version"], 2)
        self.assertEqual(merged[("way", 8)]["tags"]["highway"], "service")

    def test_equal_version_conflict_is_rejected(self):
        elements = [
            {"type": "way", "id": 8, "version": 2, "nodes": [1], "tags": {"highway": "track"}},
            {"type": "way", "id": 8, "version": 2, "nodes": [2], "tags": {"highway": "track"}},
        ]
        with self.assertRaisesRegex(ValueError, "contradictory equal-version"):
            deduplicate_elements(elements)

    def test_missing_node_breaks_geometry_without_joining_gap(self):
        nodes = {
            1: {"lat": 28.0, "lon": 129.0},
            2: {"lat": 28.0, "lon": 129.001},
            4: {"lat": 28.0, "lon": 129.003},
            5: {"lat": 28.0, "lon": 129.004},
        }
        way = {"id": 9, "nodes": [1, 2, 3, 4, 5], "tags": {"highway": "track"}}
        result = reconstruct_way_parts(nodes, way)
        self.assertEqual(result["parts"], [[(129.0, 28.0), (129.001, 28.0)], [(129.003, 28.0), (129.004, 28.0)]])
        self.assertEqual(result["missing_node_ids"], [3])

    def test_vehicle_route_classification_keeps_rural_roads_and_obeys_prohibition(self):
        cases = [
            ({"highway": "track"}, True, "track"),
            ({"highway": "service"}, True, "service"),
            ({"highway": "footway", "motor_vehicle": "yes"}, True, "explicit_vehicle"),
            ({"highway": "track", "motor_vehicle": "no"}, False, "prohibited"),
            ({"highway": "residential", "access": "private"}, False, "restricted"),
            ({"highway": "footway"}, False, "non_vehicle"),
        ]
        for tags, expected, status in cases:
            with self.subTest(tags=tags):
                got = classify_vehicle_route(tags)
                self.assertEqual(got["normal_route"], expected)
                self.assertEqual(got["vehicle_status"], status)

    def test_polygon_membership_handles_hole_and_boundary(self):
        geojson = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"osm_id": 1},
                "geometry": {"type": "Polygon", "coordinates": [
                    [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
                    [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]],
                ]},
            }],
        }
        polygons = load_target_polygons(geojson, {1})
        self.assertTrue(point_in_multipolygon(2, 2, polygons))
        self.assertFalse(point_in_multipolygon(5, 5, polygons))
        self.assertTrue(point_in_multipolygon(0, 5, polygons))

    def test_prepared_polygon_index_preserves_membership_results(self):
        polygons = [[
            [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)],
            [(4, 4), (6, 4), (6, 6), (4, 6), (4, 4)],
        ]]
        prepared = prepare_polygons(polygons, bin_size_degrees=1.0)
        for point in [(2, 2), (5, 5), (0, 5), (12, 5), (4, 5), (9, 9)]:
            with self.subTest(point=point):
                self.assertEqual(
                    point_in_multipolygon(point[0], point[1], polygons),
                    point_in_multipolygon(point[0], point[1], prepared),
                )

    def test_segment_grid_contributions_cover_boundary_cells(self):
        rows = segment_grid_contributions_xy(0.0, 50.0, 250.0, 50.0)
        self.assertEqual([(r["cell_x_index"], round(r["length_m"], 6)) for r in rows], [(0, 100.0), (1, 100.0), (2, 50.0)])
        boundary = segment_grid_contributions_xy(100.0, 0.0, 100.0, 250.0)
        self.assertEqual([(r["cell_x_index"], r["cell_y_index"]) for r in boundary], [(1, 0), (1, 1), (1, 2)])

    def test_aggregation_excludes_non_target_island_and_prohibited_road(self):
        geojson = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"osm_id": 11},
                "geometry": {"type": "Polygon", "coordinates": [[
                    [128.99, 27.99], [129.02, 27.99], [129.02, 28.02], [128.99, 28.02], [128.99, 27.99]
                ]]},
            }],
        }
        polygons = load_target_polygons(geojson, {11})
        ways = [
            {"osm_way_id": 1, "parts": [[(129.0, 28.0), (129.001, 28.0)]], "tags": {"highway": "track"}, "island_osm_relation_id": 11, "island_name": "target"},
            {"osm_way_id": 2, "parts": [[(129.0, 28.001), (129.001, 28.001)]], "tags": {"highway": "track", "access": "private"}},
            {"osm_way_id": 3, "parts": [[(130.0, 28.0), (130.001, 28.0)]], "tags": {"highway": "service"}},
        ]
        cells = aggregate_road_cells(ways, polygons)
        self.assertTrue(cells)
        self.assertEqual({way_id for row in cells for way_id in row["osm_way_ids"]}, {1})
        self.assertTrue(all(row["normal_route"] for row in cells))
        self.assertTrue(all(row["island_osm_relation_id"] == 11 for row in cells))
        self.assertTrue(all(row["island_name"] == "target" for row in cells))


if __name__ == "__main__":
    unittest.main()
