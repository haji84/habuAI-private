import csv
import itertools
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
import pdca_pipeline as p
import freeze_prediction as f

NIGHT = '2026-09-30'
NOW = p.parse_dt('2026-09-30T20:00:00+09:00')


def target(ident='T', minute='21:00', lat=28.15, lon=129.30, **extra):
    return dict(target_id=ident, latitude=lat, longitude=lon,
                predicted_time_jst=f'{NIGHT}T{minute}:00+09:00', **extra)


def prediction(targets=None, **extra):
    return dict(prediction_version='P0', prediction_class='ORIGINAL', operational_night=NIGHT,
                cutoff_time=NOW.isoformat(), targets=targets or [], **extra)


def capture(ident='C', minute='21:00', lat=28.15, lon=129.30):
    return dict(event_id=ident, datetime_jst=p.parse_dt(f'{NIGHT}T{minute}:00+09:00'),
                latitude=lat, longitude=lon, night_date=NIGHT)


class ScoringIntegrityTests(unittest.TestCase):
    def test_gpx_samples_alone_have_nullable_labels_and_no_precision_denominator(self):
        exposure=p.build_exposure([capture()],[],NIGHT)
        self.assertIsNone(exposure[0]['label'])
        self.assertEqual(exposure[0]['observation'],'UNKNOWN')
        summary=p.exposure_feature_summary(exposure)
        self.assertEqual(summary['time_of_night'][0]['observed_units'],0)
        self.assertEqual(summary['time_of_night'][0]['sampled_units'],1)
        self.assertIsNone(p.score_prediction(prediction([target()]),[],NIGHT,exposure=exposure)['precision'])

    def test_hash_failure_cannot_be_downgraded_by_missing_hash(self):
        bad = prediction(payload_sha256='tampered')
        for rows in ([bad, prediction()], [prediction(), bad]):
            self.assertEqual(p.verify_predictions(rows)[0], 'FAIL')

    def test_unobserved_target_is_unknown_not_false_positive(self):
        score = p.score_prediction(prediction([target()]), [], NIGHT)
        self.assertIsNone(score['precision'])
        self.assertEqual(score['unknown_targets'], 1)

    def test_only_matching_observed_negative_units_enter_precision(self):
        targets = [target('hit'), target('negative', '21:10'), target('unknown', '21:20')]
        exposure = p.build_exposure([capture(minute='21:10')], [], NIGHT)
        # Scorer boundary fixture: an explicitly audited negative, not inferred from its track.
        exposure[0].update(label=0, observation='observed_negative',
                           source_refs=[{'path':'synthetic/session-policy.json','sha256':'1'*64}])
        score = p.score_prediction(prediction(targets), [capture()], NIGHT, exposure=exposure)
        self.assertEqual(score['precision'], .5)
        self.assertEqual(score['observed_negative_targets'], 1)
        self.assertEqual(score['unknown_targets'], 1)

    def test_formal_kpi_ignores_payload_radius_and_time_overrides(self):
        cases = [(target(radius_m=10000), capture(lon=129.305)),
                 (target(time_tolerance_min=60), capture(minute='21:11')),
                 (target(radius_m=0, time_tolerance_min=0), capture(minute='21:10'))]
        for t, c, expected in [(cases[0][0], cases[0][1], 0), (cases[1][0], cases[1][1], 0), (cases[2][0], cases[2][1], 1)]:
            with self.subTest(target=t):
                self.assertEqual(p.score_prediction(prediction([t]), [c], NIGHT)['matched_targets'], expected)

    def test_targets_at_or_before_cutoff_are_not_prospective(self):
        score = p.score_prediction(prediction([target('earlier', '19:59'), target('exact', '20:00')]),
                                   [capture(minute='20:01')], NIGHT)
        self.assertEqual(score['target_count'], 0)
        self.assertEqual(score['formal_100m_10min_status'], 'NOT_PRODUCED')
        self.assertEqual(score['excluded_nonprospective_targets'], 2)

    def test_maximum_matching_is_permutation_invariant(self):
        # Flexible target can hit both; constrained target can hit only C1.
        targets = [target('flexible', '21:00'), target('constrained', '20:50')]
        caps = [capture('C1', '20:59'), capture('C2', '21:09')]
        results = []
        for ts in itertools.permutations(targets):
            for cs in itertools.permutations(caps):
                score = p.score_prediction(prediction(list(ts)), list(cs), NIGHT)
                self.assertEqual(score['matched_targets'], 2)
                results.append(score['matches'])
        self.assertTrue(all(result == results[0] for result in results))

    def test_grid_positivity_is_not_radius_from_first_sample(self):
        # Coordinates straddle 100m cell boundary but are less than 100m apart.
        points = [capture(lat=28.15, lon=129.3000)]
        caps = [capture(lat=28.15, lon=129.3008)]
        self.assertIsNone(p.build_exposure(points, caps, NIGHT)[0]['label'])

    def test_capture_parser_rejects_invalid_or_ambiguous_rows(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); path = root / 'data/raw/capture_db/events.csv'
            path.parent.mkdir(parents=True)
            base = dict(event='capture', datetime_jst=f'{NIGHT}T21:00:00+09:00', latitude=28.15,
                        longitude=129.30, count='1', operational_date=NIGHT)
            variants = [dict(event=''), dict(event='non_capture'), dict(event='capture_attempt'),
                        dict(count='0'), dict(count='-2'), dict(count='1.5'), dict(count='nan'),
                        dict(latitude='nan'), dict(longitude='181'), dict(latitude='91'),
                        dict(operational_date='2026-09-29')]
            with path.open('w', newline='') as fh:
                w = csv.DictWriter(fh, fieldnames=list(base)); w.writeheader()
                w.writerows([{**base, **v} for v in variants] + [base])
            self.assertEqual(len(p.load_captures(root)), 1)

    def test_count_accuracy_is_unvalidated_without_complete_observation(self):
        score = p.score_prediction(prediction(expected_capture_count=0, expected_capture_range=[0, 1]), [], NIGHT)
        self.assertEqual(score['capture_count_status'], 'NOT_VALIDATED')
        self.assertIsNone(score['capture_count_absolute_error'])
        self.assertIsNone(score['actual_within_expected_range'])
        self.assertEqual(score['diagnostic_capture_count_absolute_error'], 0)

    def test_historical_future_nights_and_missing_hashes_are_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for night, hashed in [('2026-09-29', True), (NIGHT, True), ('2026-09-28', False)]:
                path = root / f'predictions/original/{night}/P0/prediction.json'
                path.parent.mkdir(parents=True)
                payload = prediction(); payload['operational_night'] = night
                if hashed:
                    payload['payload_sha256'] = p.canonical_prediction_hash(payload)
                path.write_text(json.dumps(payload))
            rows = p.historical_p0(root, [], before_night=NIGHT)
            self.assertEqual([r['night'] for r in rows], ['2026-09-29'])
            self.assertEqual(rows[0]['evaluation_class'], 'HISTORICAL_DIAGNOSTIC')
            self.assertFalse(rows[0]['strict_official_score_eligible'])

    def test_invalid_target_coordinates_do_not_crash_or_enter_metrics(self):
        for lat, lon in [(float('nan'), 129.3), (28.15, float('inf')), (91, 129.3), (28.15, 181)]:
            with self.subTest(lat=lat, lon=lon):
                score = p.score_prediction(prediction([target(lat=lat, lon=lon)]), [], NIGHT)
                self.assertEqual(score['target_count'], 0)

    def test_missing_hash_pipeline_is_never_official_eligible(self):
        from test_pdca_e2e import PDCAE2ETests
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            PDCAE2ETests()._write_prediction(root, NIGHT, 'P0', NOW.isoformat())
            path = root / f'predictions/original/{NIGHT}/P0/prediction.json'
            payload = json.loads(path.read_text()); payload.pop('payload_sha256')
            path.write_text(json.dumps(payload))
            gpx = root / 'data/raw/gpx/night.gpx'; gpx.parent.mkdir(parents=True)
            gpx.write_text('<gpx><trk><trkseg><trkpt lat="28.15" lon="129.3"><time>2026-09-30T12:00:00Z</time></trkpt></trkseg></trk></gpx>')
            result = p.run_pipeline(root, NIGHT)
            self.assertEqual(result['integrity'][0]['status'], 'PARTIAL')
            self.assertEqual(result['overall_status'], 'PARTIAL')
            self.assertFalse(result['p0_score']['strict_official_score_eligible'])
            self.assertEqual(result['p0_score']['provenance_status'], 'NOT_VALIDATED')

    def test_historical_tamper_is_not_scored(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); path = root / f'predictions/original/{NIGHT}/P0/prediction.json'
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(prediction([target()], payload_sha256='tamper')))
            self.assertEqual(p.historical_p0(root, [capture()]), [])

    def test_missing_or_nonstring_version_returns_structured_integrity_failure(self):
        for version in [None, 0, [], "P00"]:
            with self.subTest(version=version), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                directory = 'P00' if version == 'P00' else 'P0'
                path = root / f'predictions/original/{NIGHT}/{directory}/prediction.json'
                path.parent.mkdir(parents=True)
                payload = prediction()
                if version is None:
                    payload.pop('prediction_version')
                else:
                    payload['prediction_version'] = version
                payload['payload_sha256'] = p.canonical_prediction_hash(payload)
                path.write_text(json.dumps(payload))
                original = path.read_bytes()
                result = p.run_pipeline(root, NIGHT)
                self.assertEqual(result['overall_status'], 'FAIL')
                self.assertEqual(result['integrity'][0]['status'], 'FAIL')
                self.assertIn('version', result['integrity'][0]['reason'])
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(json.loads((root / f'reports/pdca/{NIGHT}/pdca_result.json').read_text())['overall_status'], 'FAIL')

    def test_pipeline_rejects_class_and_night_mismatches(self):
        for field, value in [('prediction_class', 'REPLAY'), ('operational_night', '2026-09-29'), ('prediction_version', 'P4')]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as td:
                root = Path(td); path = root / f'predictions/original/{NIGHT}/P0/prediction.json'
                path.parent.mkdir(parents=True)
                payload = prediction(); payload[field] = value
                payload['payload_sha256'] = p.canonical_prediction_hash(payload)
                path.write_text(json.dumps(payload))
                result = p.run_pipeline(root, NIGHT)
                self.assertEqual(result['overall_status'], 'FAIL')


class FreezeIntegrityTests(unittest.TestCase):
    def test_freeze_rejects_replay_relabel(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); inp=root/'input.json'
            inp.write_text(json.dumps({'prediction_class':'REPLAY'}))
            with self.assertRaises(ValueError):
                f.freeze(root, inp, NIGHT)

    def test_freeze_rejects_bad_night_paths_and_skipped_versions(self):
        for night, version in [('../escape', 'P0'), ('2026-02-30', 'P0'), (NIGHT, 'P2')]:
            with self.subTest(night=night, version=version), tempfile.TemporaryDirectory() as td:
                root=Path(td); inp=root/'input.json'; inp.write_text('{}')
                with self.assertRaises(ValueError):
                    f.freeze(root, inp, night, version)

    def test_freeze_rejects_retrospective_cutoff_against_actual_issuance(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); inp=root/'input.json'
            inp.write_text(json.dumps({'cutoff_time':'2000-01-01T20:00:00+09:00'}))
            with self.assertRaises(ValueError):
                f.freeze(root, inp, '2000-01-01')

    def test_new_freeze_preserves_input_and_marks_missing_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); inp=root/'input.json'; inp.write_text('{}')
            out=f.freeze(root, inp, NIGHT, now=NOW)
            payload=json.loads(out.read_text())
            self.assertEqual(payload['cutoff_time'], NOW.isoformat())
            self.assertEqual(payload['provenance_status'], 'NOT_VALIDATED')
            self.assertFalse(payload['strict_official_score_eligible'])
            self.assertEqual(inp.read_text(), '{}')

    def test_freeze_rejects_metadata_conflicts_and_retroactive_targets(self):
        variants = [{'operational_night':'2026-09-29'}, {'prediction_version':'P1'},
                    {'created_at':'2026-09-29T20:00:00+09:00'},
                    {'cutoff_time':'2026-09-30T20:00:01+09:00'},
                    {'freeze_status':'retrospective_recovery_after_label_reveal'},
                    {'targets':[target(minute='20:00')]}]
        for payload in variants:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as td:
                root=Path(td); inp=root/'input.json'; inp.write_text(json.dumps(payload))
                with self.assertRaises(ValueError):
                    f.freeze(root, inp, NIGHT, now=NOW)
                self.assertFalse((root/'predictions/original').exists())

    def test_freeze_rejects_existing_version_gaps(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); inp=root/'input.json'; inp.write_text('{}')
            for version in ['P0', 'P2']:
                (root/f'predictions/original/{NIGHT}/{version}').mkdir(parents=True)
            with self.assertRaises(ValueError):
                f.freeze(root, inp, NIGHT, now=NOW)

    def test_freeze_rejects_invalid_targets_instead_of_silently_issuing_them(self):
        for bad in [target(lat=float('nan')), {'target_id':'broken'}]:
            with self.subTest(target=bad), tempfile.TemporaryDirectory() as td:
                root=Path(td); inp=root/'input.json'; inp.write_text(json.dumps({'targets':[bad]}))
                with self.assertRaises(ValueError):
                    f.freeze(root, inp, NIGHT, now=NOW)

    def test_freeze_preserves_earlier_information_cutoff_without_lag_window(self):
        # Both calculation latency and earlier model information cutoffs are legitimate.
        for cutoff in ['2026-09-30T19:59:59+09:00', '2026-09-29T07:00:00+09:00']:
            with self.subTest(cutoff=cutoff), tempfile.TemporaryDirectory() as td:
                root=Path(td); inp=root/'input.json'
                inp.write_text(json.dumps({'cutoff_time':cutoff, 'targets':[target()]}))
                path=f.freeze(root, inp, NIGHT, now=NOW)
                payload=json.loads(path.read_text())
                self.assertEqual(payload['cutoff_time'], cutoff)
                self.assertEqual(payload['frozen_at'], NOW.isoformat())
                self.assertEqual(payload['created_at'], NOW.isoformat())
                self.assertFalse(payload['strict_official_score_eligible'])
                self.assertEqual(payload['provenance_status'], 'NOT_VALIDATED')
                self.assertEqual(p.verify_predictions([payload])[0], 'PASS')

    def test_earlier_cutoff_cannot_make_already_elapsed_target_prospective(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); inp=root/'input.json'
            inp.write_text(json.dumps({'cutoff_time':'2026-09-30T19:00:00+09:00',
                                       'targets':[target(minute='19:30')]}))
            with self.assertRaises(ValueError):
                f.freeze(root, inp, NIGHT, now=NOW)
            self.assertFalse((root/'predictions/original').exists())
