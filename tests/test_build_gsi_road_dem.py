"""Synthetic source-conversion controls; never biological or field evidence."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
if importlib.util.find_spec('build_gsi_road_dem'):
    import build_gsi_road_dem as dem
else:
    dem = None
STAMP = datetime(2026, 11, 3, 10, tzinfo=timezone.utc)


def png(rgb=(0, 39, 16), *, size=(256, 256), mode='RGB'):
    output = io.BytesIO()
    Image.new(mode, size, rgb).save(output, format='PNG')
    return output.getvalue()


def cells():
    return [dict(cell_id='utm52n_100m_5000_31000', x=500050., y=3100050.,
                 island='奄美大島', length=100., direction=90.)]


class GsiRoadDemTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(dem, 'source adapter must exist')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_target_grid_preserves_road_centres_and_half_cell_origin(self):
        plan = dem.make_plan(cells())
        self.assertEqual((plan['ncols'], plan['nrows'], plan['cellsize']), (3, 3, 50))
        self.assertEqual((plan['x0'], plan['y0']), (499975., 3099975.))
        self.assertEqual(len(plan['nodes']), 9)
        center = next(n for n in plan['nodes'] if n['row'] == 1 and n['col'] == 1)
        self.assertEqual((center['x'], center['y']), (500050., 3100050.))
        self.assertGreater(plan['nodes'][0]['y'], plan['nodes'][-1]['y'])

    def test_absolute_coordinate_control_against_external_proj(self):
        # PROJ's published UTM example: lon12/lat56 in zone32 gives these
        # metre coordinates. Translating both longitude and central meridian
        # by 120 degrees gives zone52. Published values are rounded to cm;
        # its default GRS80 vs WGS84 ellipsoid difference is below this tolerance.
        # https://proj.org/en/stable/operations/projections/utm.html
        controls = [(129., 0., 500000., 0.),
                    (132., 56., 687071.44, 6210141.33)]
        for lon, lat, x, y in controls:
            actual_lat, actual_lon = dem.inverse_utm52n(x, y)
            self.assertAlmostEqual(actual_lat, lat, places=6)
            self.assertAlmostEqual(actual_lon, lon, places=6)

    def test_global_pixel_centres_edges_and_north_south_axes(self):
        # Equator/Greenwich is the exact NW edge of slippy tile (8192,8192).
        self.assertEqual(dem.tile(0, 0, 14), (8192, 8192, 0, 0))
        self.assertLess(dem.tile(1, 0, 14)[1], dem.tile(0, 0, 14)[1])
        self.assertGreater(dem.tile(0, 1, 14)[0], dem.tile(0, 0, 14)[0])

    def test_invalid_or_duplicate_road_geometry_rejects(self):
        for rows in ([], cells() * 2, [dict(cells()[0], x=float('nan'))],
                     [dict(cells()[0], x=500025.)], [dict(cells()[0], cell_id='different')]):
            with self.assertRaises(ValueError): dem.make_plan(rows)

    def test_rgb_negative_zero_and_nodata_are_distinct(self):
        for rgb, expected in [((255, 255, 156), -1.), ((0, 0, 0), 0.), ((128, 0, 0), None)]:
            image = dem.open_dem_png(png(rgb))
            self.assertEqual(dem.decode_rgb(image.getpixel((0, 0))), expected)
        with self.assertRaises(ValueError): dem.open_dem_png(png(size=(16, 16)))
        with self.assertRaises(ValueError): dem.open_dem_png(b'not PNG')
        with self.assertRaises(ValueError): dem.open_dem_png(png((0, 0, 0, 0), mode='RGBA'))

    def test_sampling_keeps_source_nodata_and_missing_tile_unknown(self):
        plan = dem.make_plan(cells())
        tile_id = plan['nodes'][0]['tile_id']
        source = dict(raw=png((128, 0, 0)), receipt={'sha256': hashlib.sha256(png((128, 0, 0))).hexdigest()})
        values, mapping = dem.sample_plan(plan, {tile_id: source})
        self.assertTrue(all(v == dem.NODATA for v in values.values()))
        self.assertTrue(all(n['status'] == 'UNKNOWN_SOURCE_NODATA' for n in mapping))
        values, mapping = dem.sample_plan(plan, {})
        self.assertTrue(all(n['status'] == 'UNKNOWN_TILE_UNAVAILABLE' for n in mapping))

    def test_ascii_north_row_first_and_unrequested_cells_stay_nodata(self):
        plan = dem.make_plan(cells())
        raw = dem.ascii_bytes(plan, {(0, 1): 50., (1, 1): 40., (2, 1): 30.})
        path = self.root / 'dem.asc'; path.write_bytes(raw)
        from road_dem_join import read_esri_ascii
        grid = read_esri_ascii(path)
        self.assertEqual([row[1] for row in grid['data']], [50., 40., 30.])
        self.assertEqual(grid['data'][0][0], dem.NODATA)

    def test_output_path_rejects_git_ancestors_and_parent_traversal(self):
        (self.root / '.git').mkdir()
        with self.assertRaises(ValueError): dem.private_root(self.root / 'outputs')
        with self.assertRaises(ValueError): dem.private_root(self.root / '..' / 'escape')

    def test_append_preserves_existing_bytes_and_rejects_collision(self):
        path = self.root / 'file'
        dem.append_bytes(path, b'first')
        dem.append_bytes(path, b'first')
        with self.assertRaises(ValueError): dem.append_bytes(path, b'second')
        self.assertEqual(path.read_bytes(), b'first')

    def test_source_acquisition_is_hash_bound_reusable_and_time_aware(self):
        raw = png()
        fetch = lambda url: (200, url, raw)
        budget = dem.ByteBudget()
        source = dem.acquire_tile(self.root, '14-8192-8192', budget=budget,
                                  fetch=fetch, clock=lambda: STAMP, pause=lambda: None)
        self.assertEqual(source['receipt']['sha256'], hashlib.sha256(raw).hexdigest())
        with patch.object(dem, '_download', side_effect=AssertionError('no refetch')):
            reused = dem.acquire_tile(self.root, '14-8192-8192', budget=dem.ByteBudget(),
                                      clock=lambda: STAMP, pause=lambda: None)
        self.assertEqual(reused['raw'], raw)
        path = self.root / source['receipt']['raw_file']
        path.write_bytes(b'changed')
        with self.assertRaises(ValueError): dem.acquire_tile(self.root, '14-8192-8192', budget=dem.ByteBudget())

    def test_http_failure_is_bounded_preserved_and_never_zero_elevation(self):
        calls = []
        def fetch(url):
            calls.append(url)
            return 404, url, b'not found'
        source = dem.acquire_tile(self.root, '14-8192-8192', budget=dem.ByteBudget(),
                                  fetch=fetch, clock=lambda: STAMP, pause=lambda: None)
        self.assertIsNone(source)
        self.assertLessEqual(len(calls), 2)
        self.assertTrue(list((self.root / 'incoming').glob('*.source')))

    def test_receipt_time_url_hash_and_path_are_validated(self):
        raw = png()
        source = dem.acquire_tile(self.root, '14-8192-8192', budget=dem.ByteBudget(),
                                  fetch=lambda url: (200, url, raw), clock=lambda: STAMP, pause=lambda: None)
        for key, val in [('retrieved_at', '2026-11-03T10:00:00'),
                         ('source_received_at', '2026-11-03T09:00:00+00:00'),
                         ('resolved_url', 'https://example.com/tile.png'),
                         ('sha256', '0' * 64), ('raw_file', '../escape')]:
            rec = dict(source['receipt']); rec[key] = val
            with self.subTest(key=key):
                with self.assertRaises(ValueError): dem.validate_source(self.root, '14-8192-8192', rec, dem.ByteBudget())

    def test_byte_budget_and_request_body_limits_fail_closed(self):
        budget = dem.ByteBudget(limit=10)
        budget.consume(10)
        with self.assertRaises(ValueError): budget.consume(1)
        with self.assertRaises(ValueError): dem.acquire_tile(self.root, '14-8192-8192', budget=dem.ByteBudget(),
            fetch=lambda url: (200, url, b'x' * 600001), clock=lambda: STAMP, pause=lambda: None)

    def test_unapproved_tile_ids_never_reach_network(self):
        for ident in ('../secret', '15-8192-8192', '14--1-1', '14-20000-2'):
            with self.assertRaises(ValueError): dem.tile_url(ident)

    def test_complete_source_conversion_reuses_existing_join_and_actual_readiness(self):
        raw = ('cell_id,cell_center_x,cell_center_y,candidate_source,road_direction_deg,island_name\n'
               'utm52n_100m_5000_31000,500050,3100050,osm_auxiliary,90,奄美大島\n').encode('utf-8')
        with patch.object(dem, 'load_verified_road_csv', return_value=raw), \
             patch.object(dem, 'parse_road_cells', return_value=cells()), \
             patch.object(dem, 'CELLS_SHA256', hashlib.sha256(raw).hexdigest()), \
             patch.object(dem, '_download', side_effect=lambda url: (200, url, png())), \
             patch.object(dem.time, 'sleep'):
            report = dem.build(self.root)
        self.assertEqual((report['coverage_cells'], report['missing_cells']), (1, 0))
        self.assertFalse(report['formal_p0_eligible'])
        self.assertFalse(report['terrain_wind_shielding_verified'])
        for artifact in report['artifacts']:
            self.assertEqual(hashlib.sha256((self.root / artifact['path']).read_bytes()).hexdigest(), artifact['sha256'])
            stamps = [datetime.fromisoformat(artifact[k]) for k in
                      ('source_received_at', 'derived_at', 'materialized_at', 'audited_at')]
            self.assertEqual(stamps, sorted(stamps))
            self.assertEqual(datetime.fromisoformat(artifact['usable_at']), max(stamps))
        joined = json.loads((self.root / report['artifacts'][-1]['path']).read_bytes())
        self.assertEqual(joined['cells'][0]['elevation_m'], 100.)
        self.assertEqual(joined['cells'][0]['slope_deg'], 0.)
        self.assertEqual(joined['slope_difference_baseline_m'], 100)

    def test_source_pixel_tampering_rejects_before_sampling(self):
        with self.assertRaises(ValueError): dem.sample_plan(dem.make_plan(cells()),
            {'14-8192-8192': {'raw': png(), 'receipt': {'sha256': '0' * 64}}})

    def test_naive_download_clock_and_foreign_redirect_never_make_valid_receipt(self):
        with self.assertRaises(ValueError): dem.acquire_tile(self.root, '14-8192-8192', budget=dem.ByteBudget(),
            fetch=lambda url: (200, url, png()), clock=lambda: STAMP.replace(tzinfo=None), pause=lambda: None)
        source = dem.acquire_tile(self.root, '14-8192-8192', budget=dem.ByteBudget(),
            fetch=lambda url: (200, 'https://example.com/tile.png', png()), clock=lambda: STAMP, pause=lambda: None)
        self.assertIsNone(source)
        self.assertFalse((self.root / 'receipts/14-8192-8192.json').exists())

    def test_processing_cutoff_waits_for_real_clock_instead_of_backdating(self):
        later = datetime(2026, 11, 3, 10, 0, 1, tzinfo=timezone.utc)
        clock = iter([STAMP, STAMP, later])
        waits = []
        result = dem.processing_cutoff(STAMP.isoformat(), clock=lambda: next(clock), pause=lambda: waits.append(1))
        self.assertEqual(datetime.fromisoformat(result), later)
        self.assertEqual(len(waits), 2)

    def test_mutated_derived_artifacts_or_readiness_block_completion(self):
        raw = ('cell_id,cell_center_x,cell_center_y,candidate_source,road_direction_deg,island_name\n'
               'utm52n_100m_5000_31000,500050,3100050,osm_auxiliary,90,奄美大島\n').encode('utf-8')
        original = dem.join_road_dem
        for target in ('road-neighbour-dem-50m.asc', 'verified-public-roads.csv',
                       'required-node-source-map.csv', 'readiness'):
            destination = self.root / target
            def mutate_after_join(*args, **kwargs):
                result = original(*args, **kwargs)
                generation = args[1].parent
                path = (next(generation.glob('road-neighbour-dem-50m.asc.*.readiness.json'))
                        if target == 'readiness' else generation / target)
                with path.open('ab') as stream: stream.write(b'\n')
                return result
            with self.subTest(target=target), \
                 patch.object(dem, 'load_verified_road_csv', return_value=raw), \
                 patch.object(dem, 'parse_road_cells', return_value=cells()), \
                 patch.object(dem, 'CELLS_SHA256', hashlib.sha256(raw).hexdigest()), \
                 patch.object(dem, '_download', side_effect=lambda url: (200, url, png())), \
                 patch.object(dem.time, 'sleep'), \
                 patch.object(dem, 'join_road_dem', side_effect=mutate_after_join):
                with self.assertRaises(ValueError): dem.build(destination)
                self.assertFalse(list(destination.glob('conversion-*.json')))


if __name__ == '__main__':
    unittest.main()
