"""Synthetic source-only route reconstruction; no private locations or labels."""
import copy
import hashlib
import importlib
import json
import math
import unittest
from unittest.mock import patch

from src.terrain_road_features import inverse_utm52n


SHA = 'a' * 64


def fix(x, y, stamp, **extra):
    lat, lon = inverse_utm52n(x, y)
    return dict(time=stamp, lat=lat, lon=lon, accuracy=5, **extra)


def gpx(segments):
    groups = []
    for rows in segments:
        items = []
        for row in rows:
            time = '<time>' + row['time'] + '</time>' if row.get('time') else ''
            quality = '<hdop>' + str(row['hdop']) + '</hdop>' if 'hdop' in row else ''
            items.append('<trkpt lat="' + str(row['lat']) + '" lon="' + str(row['lon']) + '">'
                         + time + quality + '</trkpt>')
        groups.append('<trkseg>' + ''.join(items) + '</trkseg>')
    return ('<gpx xmlns="http://www.topografix.com/GPX/1/1"><trk>'
            + ''.join(groups) + '</trk></gpx>').encode()


class RouteRecoveryTests(unittest.TestCase):
    def setUp(self):
        try:
            self.api = importlib.import_module('src.route_recovery')
        except ModuleNotFoundError as exc:
            if exc.name != 'src.route_recovery':
                raise
            self.fail('Source-preserving route recovery API is not implemented')

    def parse(self, raw, format='gpx'):
        return self.api.parse_route(raw, format=format,
                                    source_sha256=hashlib.sha256(raw).hexdigest())

    def route(self, rows, **kwargs):
        return self.api.recover_route(self.parse(gpx([rows])), **kwargs)

    def test_source_segments_never_become_a_connecting_route(self):
        raw = gpx([[fix(500050, 1005, '2026-11-03T13:00:00Z')],
                   [fix(500060, 1005, '2026-11-03T13:00:10Z')]])
        parsed = self.parse(raw)
        result = self.api.recover_route(parsed)
        self.assertEqual([p['segment_index'] for p in result['points']], [0, 1])
        self.assertEqual(result['summary']['interpolated_seconds'], 0)
        self.assertEqual(result['summary']['accepted_points'], 2)
        self.assertIn('SOURCE_SEGMENT_BOUNDARY', [g['reason'] for g in result['gaps']])

    def test_source_hash_mismatch_rejects_before_parsing(self):
        with self.assertRaisesRegex(ValueError, 'SHA'):
            self.api.parse_route(b'<not-xml', source_sha256=SHA)

    def test_naive_time_and_local_bad_point_are_quarantined_not_invented(self):
        rows = [fix(500050, 1005, '2026-11-03T13:00:00Z'),
                dict(time='2026-11-03T13:00:05', lat=999, lon=129),
                fix(500060, 1005, '2026-11-03T13:00:10Z'),
                fix(500070, 1005, '2026-11-03T13:00:20Z')]
        result = self.route(rows)
        self.assertEqual(result['summary']['source_points'], 4)
        self.assertEqual(result['summary']['accepted_points'], 3)
        self.assertTrue(result['points'][1]['exclude_point'])
        self.assertEqual(result['points'][1]['time_raw'], '2026-11-03T13:00:05')
        self.assertAlmostEqual(result['summary']['interpolated_seconds'], 10)
        self.assertFalse(result['points'][2]['exclude_point'])

    def test_duplicate_and_reversed_times_split_instead_of_sorting_source(self):
        stamps = ['2026-11-03T13:00:00Z', '2026-11-03T13:00:00Z',
                  '2026-11-03T12:59:59Z', '2026-11-03T13:00:10Z']
        result = self.route([fix(500050 + i, 1005, t) for i, t in enumerate(stamps)])
        self.assertEqual([p['time_raw'] for p in result['points']], stamps)
        self.assertEqual(result['summary']['source_points'], 4)
        self.assertGreaterEqual(len(result['gaps']), 2)
        self.assertTrue(any('NON_MONOTONIC_TIME' in p['qc_reasons'] for p in result['points']))

    def test_long_gap_keeps_both_measured_sides_and_no_fabricated_fixes(self):
        rows = [fix(500050, 1005, '2026-11-03T13:00:00Z'),
                fix(500060, 1005, '2026-11-03T13:00:10Z'),
                fix(500080, 1005, '2026-11-03T14:00:00Z'),
                fix(500090, 1005, '2026-11-03T14:00:10Z')]
        result = self.route(rows)
        self.assertEqual(len(result['points']), 4)
        self.assertEqual(result['summary']['accepted_points'], 4)
        self.assertAlmostEqual(result['summary']['interpolated_seconds'], 20)
        gap = next(g for g in result['gaps'] if g['reason'] == 'TIME_GAP')
        self.assertEqual(gap['duration_seconds'], 3590)
        self.assertFalse(gap['route_hypothesis_produced'])

    def test_cell_and_ten_minute_crossings_partition_time_without_double_count(self):
        result = self.route([fix(500050, 1005, '2026-11-03T13:09:50Z'),
                             fix(500150, 1005, '2026-11-03T13:10:10Z')])
        windows = sorted(result['windows'], key=lambda w: w['window_start_jst'])
        self.assertEqual(len(windows), 2)
        self.assertEqual([(w['cell_x'], w['cell_y']) for w in windows], [(5000, 10), (5001, 10)])
        self.assertEqual([w['window_start_jst'] for w in windows],
                         ['2026-11-03T22:00:00+09:00', '2026-11-03T22:10:00+09:00'])
        for window in windows:
            self.assertAlmostEqual(window['interpolated_seconds'], 10, places=2)
            self.assertEqual(window['measured_continuous_search_seconds'], None)

    def test_stationary_capture_stop_is_not_automatically_a_pause(self):
        result = self.route([fix(500050, 1005, '2026-11-03T13:00:00Z'),
                             fix(500050, 1005, '2026-11-03T13:00:20Z')])
        self.assertAlmostEqual(result['summary']['interpolated_seconds'], 20)
        self.assertEqual(result['summary']['intentional_pause_seconds'], 0)
        self.assertEqual(result['windows'][0]['activity_class'], 'UNRESOLVED_ACTIVITY')

    def test_repeated_visits_preserve_exposures_and_require_context_for_inference(self):
        rows = [fix(500050, 1005, '2026-11-03T13:00:00Z'),
                fix(500150, 1005, '2026-11-03T13:00:20Z'),
                fix(500050, 1005, '2026-11-03T13:00:40Z')]
        result = self.route(rows)
        first = next(w for w in result['windows'] if w['cell_x'] == 5000)
        self.assertEqual(first['visit_count'], 2)
        self.assertAlmostEqual(first['interpolated_seconds'], 20, places=2)
        self.assertEqual(first['activity_class'], 'UNRESOLVED_ACTIVITY')
        inferred = self.route(rows, activity={'owner_search_context': True, 'source_sha256': SHA})
        first = next(w for w in inferred['windows'] if w['cell_x'] == 5000)
        self.assertEqual(first['activity_class'], 'SEARCH_INFERRED')
        self.assertFalse(first['formal_negative_eligible'])

    def test_union_pause_removes_only_overlap_and_preserves_measured_points(self):
        pauses = [dict(start='2026-11-03T22:00:05+09:00', end='2026-11-03T22:00:15+09:00',
                       owner_confirmed=True, classification='INTENTIONAL_PAUSE', source_sha256=SHA),
                  dict(start='2026-11-03T22:00:10+09:00', end='2026-11-03T22:00:18+09:00',
                       owner_confirmed=True, classification='INTENTIONAL_PAUSE', source_sha256=SHA)]
        result = self.route([fix(500050, 1005, '2026-11-03T13:00:00Z'),
                             fix(500060, 1005, '2026-11-03T13:00:20Z')], pauses=pauses)
        self.assertEqual(result['summary']['intentional_pause_seconds'], 13)
        self.assertAlmostEqual(result['windows'][0]['pause_overlap_seconds'], 13)
        self.assertAlmostEqual(result['windows'][0]['movement_effort_proxy_seconds'], 7)
        self.assertEqual(len(result['points']), 2)

    def test_exact_november_pause_is_1752_seconds_not_a_hardware_failure(self):
        pause = dict(start='2026-11-03T22:14:53+09:00', end='2026-11-03T22:44:05+09:00',
                     owner_confirmed=True, classification='INTENTIONAL_PAUSE', source_sha256=SHA)
        result = self.route([fix(500050, 1005, '2026-11-03T09:17:00Z'),
                             fix(500060, 1005, '2026-11-03T14:33:00Z')], pauses=[pause])
        self.assertEqual(result['summary']['session_elapsed_seconds'], 18960)
        self.assertEqual(result['summary']['intentional_pause_seconds'], 1752)
        self.assertEqual(result['summary']['elapsed_minus_pause_proxy_seconds'], 17208)
        self.assertEqual(result['summary']['interpolated_seconds'], 0)
        self.assertTrue(result['gaps'][0]['intentional_pause_overlap_seconds'] == 1752)
        self.assertEqual(result['gaps'][0]['gps_hardware_failure'], 'NOT_ESTABLISHED')

    def test_unconfirmed_pause_is_rejected_instead_of_subtracted(self):
        with self.assertRaises(ValueError):
            self.route([fix(500050, 1005, '2026-11-03T13:00:00Z')], pauses=[
                dict(start='2026-11-03T22:00:00+09:00', end='2026-11-03T22:01:00+09:00',
                     owner_confirmed=False, classification='INTENTIONAL_PAUSE', source_sha256=SHA)])

    def test_operational_night_partitions_at_seven_am(self):
        result = self.route([fix(500050, 1005, '2026-11-03T21:59:50Z'),
                             fix(500060, 1005, '2026-11-03T22:00:10Z')])
        self.assertEqual([p['operational_night'] for p in result['points']], ['2026-11-03', '2026-11-04'])
        self.assertEqual({w['operational_night'] for w in result['windows']}, {'2026-11-03', '2026-11-04'})

    def test_field_session_and_jsonl_keep_native_point_shape_and_explicit_gap(self):
        rows = [fix(500050, 1005, '2026-11-03T13:00:00Z'),
                fix(500060, 1005, '2026-11-03T13:00:10Z')]
        session = dict(schema_version='habu-field-session-v1', id='synthetic-session-00001',
                       startedAt=rows[0]['time'], endedAt=rows[1]['time'], status='stopped',
                       points=rows, events=[], gaps=[dict(time='2026-11-03T13:00:05Z', reason='manual')], revision=1)
        result = self.api.recover_route(self.parse(json.dumps(session).encode(), 'field-session'))
        self.assertEqual(result['summary']['interpolated_seconds'], 0)
        self.assertIn('RECORDER_GAP', [g['reason'] for g in result['gaps']])
        raw = b'\n'.join(json.dumps(dict(row, segment=i)).encode() for i, row in enumerate(rows))
        parsed = self.parse(raw, 'jsonl')
        self.assertEqual([p['segment_index'] for p in parsed['points']], [0, 1])

    def test_parser_rejects_entities_duplicate_json_and_unbounded_or_unknown_structure(self):
        cases = [(b'<!DOCTYPE gpx [<!ENTITY x "x">]><gpx/>', 'gpx'),
                 (b'<other/>', 'gpx'), (b'{"schema_version":"a","schema_version":"b"}', 'field-session'),
                 (b'{"time":"2026-11-03T13:00:00Z","lat":NaN,"lon":129}', 'jsonl')]
        for raw, fmt in cases:
            with self.subTest(format=fmt), self.assertRaises(ValueError):
                self.parse(raw, fmt)
        with self.assertRaises(ValueError):
            self.api.parse_route(b' ' * (20_000_000 + 1), source_sha256=SHA)

    def test_input_values_are_unchanged_and_interpolated_points_never_become_measured(self):
        parsed = self.parse(gpx([[fix(500050, 1005, '2026-11-03T13:00:00Z'),
                                  fix(500150, 1005, '2026-11-03T13:00:20Z')]]))
        original = copy.deepcopy(parsed)
        result = self.api.recover_route(parsed)
        self.assertEqual(parsed, original)
        self.assertEqual(len(result['points']), 2)
        self.assertTrue(all(p['origin'] == 'GPS_MEASURED' for p in result['points']))
        self.assertFalse(result['summary']['official_prediction_authorized'])
        self.assertEqual(result['summary']['formal_negative_count'], 0)
        self.assertEqual(result['summary']['training_eligibility'], 'NOT_ASSESSED')

    def test_point_refs_and_origins_remain_explicit_without_a_road_source(self):
        result = self.route([fix(500050, 1005, '2026-11-03T13:00:00Z'),
                             fix(500060, 1005, '2026-11-03T13:00:10Z')])
        row = result['windows'][0]
        self.assertEqual(row.get('point_ids'), [p['point_id'] for p in result['points']])
        self.assertEqual(row.get('origins'), ['GPS_MEASURED', 'GPS_INTERPOLATED'])
        self.assertEqual(result['summary'].get('road_matching_status'), 'NOT_PRODUCED_NO_ROAD_SOURCE')

    def test_reversal_cannot_reset_the_native_segment_clock(self):
        seconds = [0, 10, 5, 7, 20]
        result = self.route([fix(500050+i, 1005, '2026-11-03T13:00:' + str(s).zfill(2)+'Z')
                             for i, s in enumerate(seconds)])
        self.assertEqual(result['summary']['accepted_points'], 3)
        self.assertAlmostEqual(result['summary']['interpolated_seconds'], 10)

    def test_forged_parsed_origin_or_parent_digest_is_rejected(self):
        parsed = self.parse(gpx([[fix(500050, 1005, '2026-11-03T13:00:00Z')]]))
        for change in [dict(origin='GPS_INTERPOLATED'), dict(source_sha256='b'*64)]:
            bad = copy.deepcopy(parsed)
            bad['points'][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.api.recover_route(bad)

    def test_speed_alone_is_not_search_and_impossible_interval_is_not_filled(self):
        result = self.route([fix(500050, 1005, '2026-11-03T13:00:00Z'),
                             fix(500250, 1005, '2026-11-03T13:00:01Z')],
                            activity={'owner_search_context': True, 'source_sha256': SHA})
        self.assertEqual(result['summary']['interpolated_seconds'], 0)
        self.assertEqual(result['gaps'][0]['reason'], 'IMPLAUSIBLE_SPEED')
        self.assertTrue(all(w['activity_class'] == 'UNRESOLVED_ACTIVITY' for w in result['windows']))

    def test_explicit_search_context_and_turn_back_are_only_research_inference(self):
        result = self.route([fix(500020, 1005, '2026-11-03T13:00:00Z'),
                             fix(500070, 1005, '2026-11-03T13:00:10Z'),
                             fix(500030, 1005, '2026-11-03T13:00:20Z')],
                            activity={'owner_search_context': True, 'source_sha256': SHA})
        self.assertEqual(result['windows'][0]['activity_class'], 'SEARCH_INFERRED')
        self.assertIn('TURN_BACK_PATTERN', result['windows'][0]['activity_reasons'])
        self.assertFalse(result['windows'][0]['formal_negative_eligible'])

    def test_road_ambiguity_keeps_candidates_but_rejects_precise_path(self):
        def road(id, y):
            a, b = fix(500000, y, ''), fix(500300, y, '')
            return dict(road_id=id, source_sha256=SHA,
                        geometry=dict(type='LineString', coordinates=[[a['lon'], a['lat']], [b['lon'], b['lat']]]))
        rows = [fix(500050, 1005, '2026-11-03T13:00:00Z'),
                fix(500150, 1005, '2026-11-03T13:00:20Z')]
        result = self.route(rows, roads=[road('left', 1000), road('right', 1010)])
        self.assertEqual(len(result['points'][0]['road_match']['candidates']), 2)
        self.assertEqual(result['summary']['interpolated_seconds'], 0)
        self.assertEqual(result['gaps'][0]['reason'], 'ROAD_MATCH_AMBIGUITY')
        clear = self.route(rows, roads=[road('single', 1000)])
        self.assertEqual(clear['points'][0]['road_match']['status'], 'MATCHED')
        self.assertAlmostEqual(clear['points'][0]['road_match']['candidates'][0]['distance_m'], 5, places=2)
        self.assertFalse(clear['points'][0]['road_match']['official_access_verified'])

    def test_quality_rejection_is_local_and_unknown_accuracy_is_not_zero(self):
        rows = [fix(500050, 1005, '2026-11-03T13:00:00Z', hdop=2),
                fix(500060, 1005, '2026-11-03T13:00:10Z', hdop=50),
                fix(500070, 1005, '2026-11-03T13:00:20Z', hdop=2),
                fix(500080, 1005, '2026-11-03T13:00:30Z', hdop=2)]
        result = self.route(rows)
        self.assertEqual(result['summary']['accepted_points'], 3)
        self.assertAlmostEqual(result['summary']['interpolated_seconds'], 10)
        self.assertIsNone(result['points'][0]['accuracy_m'])  # GPX supplies HDOP, not accuracy.

    def test_capacity_and_policy_rejections_have_bounded_fixed_diagnostics(self):
        parsed = self.parse(gpx([[fix(500050, 1005, '2026-11-03T13:00:00Z')]]))
        for policy in [dict(max_interval_seconds=60), dict(road_match_radius_m=1e100), dict(max_speed_mps=math.nan)]:
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                self.api.recover_route(parsed, policy=policy)

    def test_pause_and_activity_source_refs_survive_reconstruction(self):
        pause = dict(start='2026-11-03T22:00:02+09:00', end='2026-11-03T22:00:03+09:00',
                     owner_confirmed=True, classification='INTENTIONAL_PAUSE', source_sha256=SHA)
        result = self.route([fix(500050, 1005, '2026-11-03T13:00:00Z'),
                             fix(500060, 1005, '2026-11-03T13:00:10Z')], pauses=[pause],
                            activity=dict(owner_search_context=True, source_sha256=SHA))
        self.assertEqual(result.get('activity_source_sha256'), SHA)
        self.assertEqual(result.get('pause_evidence'), [pause])

    def test_nonmonotonic_gap_does_not_fabricate_elapsed_duration(self):
        result = self.route([fix(500050, 1005, '2026-11-03T13:00:10Z'),
                             fix(500060, 1005, '2026-11-03T13:00:05Z')])
        self.assertIsNone(result['gaps'][0]['duration_seconds'])
        self.assertEqual(result['gaps'][0].get('signed_source_elapsed_seconds'), -5)

    def test_far_roads_are_not_scanned_for_each_measured_point(self):
        roads = []
        for i in range(200):
            a, b = fix(600000, 1005 + 100*i, ''), fix(600020, 1005 + 100*i, '')
            roads.append(dict(road_id=str(i), source_sha256=SHA, geometry=dict(
                type='LineString', coordinates=[[a['lon'], a['lat']], [b['lon'], b['lat']]])))
        result = self.route([fix(500050, 1005, '2026-11-03T13:00:00Z')], roads=roads)
        self.assertEqual(result['points'][0]['road_match']['status'], 'UNMATCHED')
        self.assertEqual(result['summary'].get('road_distance_checks'), 0)

    def test_existing_rapid_jump_break_is_preserved_even_at_vehicle_speed(self):
        result = self.route([fix(500050, 1005, '2026-11-03T13:00:00Z'),
                             fix(500650, 1005, '2026-11-03T13:00:20Z')])
        self.assertEqual(result['summary']['interpolated_seconds'], 0)
        self.assertEqual(result['gaps'][0]['reason'], 'RAPID_JUMP')

    def test_partial_activity_scope_does_not_certify_a_whole_window(self):
        rows = [fix(500050, 1005, '2026-11-03T13:00:00Z'),
                fix(500150, 1005, '2026-11-03T13:00:20Z'),
                fix(500050, 1005, '2026-11-03T13:00:40Z')]
        activity = dict(owner_search_context=True, source_sha256=SHA,
                        scope_start='2026-11-03T22:00:00+09:00', scope_end='2026-11-03T22:00:25+09:00')
        result = self.route(rows, activity=activity)
        row = next(w for w in result['windows'] if w['cell_x'] == 5000)
        self.assertEqual(row['activity_class'], 'UNRESOLVED_ACTIVITY')
        self.assertAlmostEqual(row.get('search_inferred_proxy_seconds', -1), 10, places=2)
        self.assertFalse(row['formal_negative_eligible'])

    def test_activity_scope_is_paired_aware_and_half_open(self):
        rows = [fix(500050, 1005, '2026-11-03T13:00:00Z')]
        for change in [dict(scope_start='2026-11-03T13:00:00Z'),
                       dict(scope_start='2026-11-03T13:00:00', scope_end='2026-11-03T13:00:01Z'),
                       dict(scope_start='2026-11-03T13:00:01Z', scope_end='2026-11-03T13:00:00Z')]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.route(rows, activity=dict(owner_search_context=True, source_sha256=SHA, **change))
        result = self.route(rows, activity=dict(owner_search_context=True, source_sha256=SHA))
        self.assertEqual(result['summary'].get('activity_context_scope'), 'EXPLICIT_WHOLE_SOURCE_CONTEXT')

    def test_utf16_dtd_and_entity_declarations_are_rejected_before_expansion(self):
        xml = ('<?xml version="1.0" encoding="UTF-16"?>'
               '<!DOCTYPE gpx [<!ENTITY stamp "2026-11-03T13:00:00Z">]>'
               '<gpx><trk><trkseg><trkpt lat="0" lon="129"><time>&stamp;</time>'
               '</trkpt></trkseg></trk></gpx>')
        for encoding, bom in [('utf-16-le', b'\xff\xfe'), ('utf-16-be', b'\xfe\xff')]:
            with self.subTest(encoding=encoding), self.assertRaisesRegex(ValueError, 'ENTITY'):
                self.parse(bom + xml.encode(encoding))

    def test_valid_utf16_measurements_are_preserved_without_forbidding_the_encoding(self):
        xml = ('<?xml version="1.0" encoding="UTF-16"?><gpx><trk><trkseg>'
               '<trkpt lat="0" lon="129"><time>2026-11-03T13:00:00Z</time>'
               '</trkpt></trkseg></trk></gpx>')
        for encoding, bom in [('utf-16-le', b'\xff\xfe'), ('utf-16-be', b'\xfe\xff')]:
            with self.subTest(encoding=encoding):
                parsed = self.parse(bom + xml.encode(encoding))
                self.assertEqual(len(parsed['points']), 1)
                self.assertEqual(parsed['points'][0]['time_utc'], '2026-11-03T13:00:00+00:00')

    def test_isolated_future_timestamp_is_quarantined_without_poisoning_the_tail(self):
        stamps = ['2026-11-03T01:00:00Z', '2026-11-03T11:00:00Z',
                  '2026-11-03T01:00:02Z', '2026-11-03T01:00:03Z']
        result = self.route([fix(500050+i, 1005, t) for i, t in enumerate(stamps)])
        self.assertEqual([p['time_raw'] for p in result['points']], stamps)
        self.assertEqual(result['summary']['accepted_points'], 3)
        self.assertTrue(result['points'][1]['exclude_point'])
        self.assertIn('ISOLATED_TIMESTAMP_EXCURSION', result['points'][1]['qc_reasons'])
        self.assertFalse(result['points'][2]['exclude_point'])
        self.assertAlmostEqual(result['summary']['interpolated_seconds'], 1)
        self.assertEqual(result['segments'][0].get('temporal_support'), 'SOURCE_TIMES_WITH_LOCAL_CLOCK_CONFLICT')

    def test_mapmatched_candidates_have_distinct_origin_and_uncalibrated_confidence(self):
        a, b = fix(500000, 1000, ''), fix(500300, 1000, '')
        road = dict(road_id='synthetic-road', source_sha256=SHA, geometry=dict(
            type='LineString', coordinates=[[a['lon'], a['lat']], [b['lon'], b['lat']]]))
        result = self.route([fix(500050, 1005, '2026-11-03T13:00:00Z'),
                             fix(500060, 1005, '2026-11-03T13:00:10Z')], roads=[road])
        point = result['points'][0]
        self.assertEqual(point['origin'], 'GPS_MEASURED')
        self.assertEqual(point['road_match'].get('origin'), 'GPS_MAP_MATCHED')
        self.assertEqual(point['road_match'].get('confidence'), 'GNSS_ACCURACY_UNKNOWN')
        self.assertEqual(point['road_match']['candidates'][0].get('origin'), 'GPS_MAP_MATCHED')
        self.assertFalse(point['road_match'].get('confidence_calibrated', True))
        row = result['windows'][0]
        self.assertIn('GPS_MAP_MATCHED', row['origins'])
        self.assertEqual(row.get('mapmatched_point_count'), 2)
        self.assertEqual(row.get('road_match_status_counts'), {'MATCHED': 2})

    def test_reported_gnss_accuracy_still_does_not_claim_road_confidence_calibration(self):
        a, b = fix(500000, 1000, ''), fix(500300, 1000, '')
        road = dict(road_id='synthetic-road', source_sha256=SHA, geometry=dict(
            type='LineString', coordinates=[[a['lon'], a['lat']], [b['lon'], b['lat']]]))
        raw = json.dumps(fix(500050, 1005, '2026-11-03T13:00:00Z')).encode()
        result = self.api.recover_route(self.parse(raw, 'jsonl'), roads=[road])
        match = result['points'][0]['road_match']
        self.assertEqual(match.get('confidence'), 'UNVALIDATED_SPATIAL_CANDIDATE')
        self.assertFalse(match.get('confidence_calibrated', True))
        self.assertFalse(match['official_access_verified'])

    def test_duplicate_segment_time_is_not_double_counted_as_effort(self):
        rows = [fix(500050, 1005, '2026-11-03T13:00:00Z'),
                fix(500060, 1005, '2026-11-03T13:00:20Z')]
        parsed = self.parse(gpx([rows, rows]))
        result = self.api.recover_route(parsed)
        self.assertEqual(len(result['points']), 4)
        self.assertEqual([p['time_raw'] for p in result['points']], [r['time'] for r in rows]*2)
        self.assertEqual(result['summary']['interpolated_seconds'], 0)
        self.assertEqual(sum(w['movement_effort_proxy_seconds'] for w in result['windows']), 0)
        self.assertEqual(result['summary']['overlapping_source_intervals'], 2)

    def test_conflicting_simultaneous_locations_hold_both_edges_and_keep_tail(self):
        groups = [[fix(500050, 1005, '2026-11-03T13:00:00Z'),
                   fix(500060, 1005, '2026-11-03T13:00:20Z')],
                  [fix(501050, 1005, '2026-11-03T13:00:10Z'),
                   fix(501060, 1005, '2026-11-03T13:00:30Z')],
                  [fix(502050, 1005, '2026-11-03T13:00:40Z'),
                   fix(502060, 1005, '2026-11-03T13:00:50Z')]]
        result = self.api.recover_route(self.parse(gpx(groups)))
        self.assertEqual(result['summary']['accepted_points'], 6)
        self.assertEqual(result['summary']['interpolated_seconds'], 10)
        self.assertEqual(len(result['segments']), 1)
        self.assertEqual(result['segments'][0]['from_point_id'], result['points'][4]['point_id'])
        self.assertEqual(sum(g['reason']=='OVERLAPPING_SOURCE_TIME' for g in result['gaps']), 2)

    def test_touching_time_boundaries_are_not_overlapping_intervals(self):
        groups = [[fix(500050, 1005, '2026-11-03T13:00:00Z'),
                   fix(500060, 1005, '2026-11-03T13:00:10Z')],
                  [fix(500060, 1005, '2026-11-03T13:00:10Z'),
                   fix(500070, 1005, '2026-11-03T13:00:20Z')]]
        result = self.api.recover_route(self.parse(gpx(groups)))
        self.assertEqual(result['summary']['interpolated_seconds'], 20)
        self.assertEqual(result['summary']['overlapping_source_intervals'], 0)

    def test_huge_local_numeric_value_is_quarantined_without_losing_normal_tail(self):
        for field in ('lat', 'accuracy'):
            rows = [fix(500050+i, 1005, f'2026-11-03T13:00:{second:02d}Z')
                    for i, second in enumerate((0, 5, 10, 20))]
            rows[1][field] = 10**400
            raw = b'\n'.join(json.dumps(row).encode() for row in rows)
            with self.subTest(field=field):
                result = self.api.recover_route(self.parse(raw, 'jsonl'))
                self.assertEqual(len(result['points']), 4)
                self.assertEqual(result['summary']['accepted_points'], 3)
                self.assertTrue(result['points'][1]['exclude_point'])
                self.assertEqual(result['points'][1]['raw_fields'][field], 10**400)
                self.assertEqual(result['summary']['interpolated_seconds'], 10)

    def test_long_diagonal_indexes_original_edge_without_filling_its_rectangle(self):
        road = dict(road_id='synthetic-long-diagonal', source_sha256=SHA,
                    geometry=dict(type='LineString', coordinates=[[129, 28], [131, 30]]))
        rows = [dict(lat=28, lon=129, time='2026-11-03T13:00:00Z'),
                dict(lat=28.00001, lon=129.00001, time='2026-11-03T13:00:20Z')]
        result = self.route(rows, roads=[road])
        self.assertEqual(len(result['points']), 2)
        self.assertEqual(result['points'][0]['road_match']['status'], 'MATCHED')
        self.assertEqual(result['points'][0]['road_match']['candidates'][0]['road_id'], road['road_id'])
        self.assertEqual(result['summary']['interpolated_seconds'], 20)

    def test_optional_road_index_capacity_does_not_erase_measured_route(self):
        rows = [fix(500050, 1005, '2026-11-03T13:00:00Z'),
                fix(500060, 1005, '2026-11-03T13:00:20Z')]
        road = dict(road_id='synthetic-index-budget', source_sha256=SHA, geometry=dict(
            type='LineString', coordinates=[[r['lon'], r['lat']] for r in rows]))
        with patch.object(self.api, 'MAX_OPERATIONS', 2):
            result = self.route(rows, roads=[road])
        self.assertEqual(result['summary']['interpolated_seconds'], 20)
        self.assertEqual(len(result['points']), 2)
        self.assertEqual(result['summary']['road_matching_status'], 'NOT_PRODUCED_ROAD_INDEX_CAPACITY')
        self.assertTrue(all(p['road_match']['status']=='NOT_PRODUCED_CAPACITY' for p in result['points']))

    def test_optional_road_match_capacity_is_partial_and_keeps_original_fixes(self):
        rows = [fix(500050, 1005, '2026-11-03T13:00:00Z'),
                fix(500060, 1005, '2026-11-03T13:00:20Z')]
        roads = [dict(road_id='synthetic-match-budget-'+str(i), source_sha256=SHA, geometry=dict(
            type='LineString', coordinates=[[r['lon'], r['lat']] for r in rows])) for i in range(2)]
        with patch.object(self.api, 'MAX_OPERATIONS', 2):
            result = self.route(rows, roads=roads, policy=dict(road_match_radius_m=0.000001))
        self.assertEqual(len(result['points']), 2)
        self.assertEqual(result['summary']['road_matching_status'], 'PARTIAL_ROAD_MATCH_CAPACITY')
        self.assertEqual(result['points'][0]['road_match']['status'], 'AMBIGUOUS')
        self.assertEqual(result['points'][1]['road_match']['status'], 'NOT_PRODUCED_CAPACITY')

    def test_foreign_distance_error_is_not_laundered_into_road_capacity(self):
        rows = [fix(500050, 1005, '2026-11-03T13:00:00Z')]
        road = dict(road_id='synthetic-error-origin', source_sha256=SHA, geometry=dict(
            type='LineString', coordinates=[[129, 0], [129, 0.01]]))
        error = ValueError('ROAD_MATCH_CAPACITY')
        with patch.object(self.api, 'point_segment_distance_and_bearing', side_effect=error):
            with self.assertRaises(ValueError) as caught:
                self.route(rows, roads=[road])
        self.assertIs(caught.exception, error)

    def test_invalid_road_geometry_is_not_reclassified_as_a_capacity_failure(self):
        road = dict(road_id='synthetic-invalid-geometry', source_sha256=SHA,
                    geometry=dict(type='LineString', coordinates=None))
        with self.assertRaisesRegex(ValueError, 'ROAD_VERTEX_CAPACITY'):
            self.route([fix(500050, 1005, '2026-11-03T13:00:00Z')], roads=[road])

    def test_buffered_line_index_preserves_direct_distance_candidates(self):
        a, b = fix(500095, 1005, ''), fix(500305, 1205, '')
        road = dict(road_id='synthetic-buffer-crossings', source_sha256=SHA, geometry=dict(
            type='LineString', coordinates=[[a['lon'], a['lat']], [b['lon'], b['lat']]]))
        index = self.api._road_index([road], self.api.DEFAULT_POLICY)
        xy = [self.api.utm52n(r['lat'], r['lon']) for r in (a, b)]
        for x in range(500050, 500351, 25):
            for y in range(950, 1251, 25):
                expected, _ = self.api.point_segment_distance_and_bearing(x, y, *xy[0], *xy[1])
                match = self.api._match_road(dict(utm_x=x, utm_y=y, accuracy_m=None), index,
                                            self.api.DEFAULT_POLICY, [0])
                with self.subTest(x=x, y=y):
                    self.assertEqual(bool(match['candidates']), expected <= self.api.DEFAULT_POLICY['road_match_radius_m'])


if __name__ == '__main__':
    unittest.main()
