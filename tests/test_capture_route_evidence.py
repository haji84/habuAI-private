"""Synthetic-only tests: no owner locations, identities or logs."""
from copy import deepcopy
import importlib.util
import json
import unittest
from unittest.mock import patch


SHA = "a" * 64
GPS_SHA = "b" * 64


def event(**changes):
    result = dict(event_id="synthetic-event", individual_ids=["synthetic-animal"],
                  source_sha256=SHA, recorded_at="2026-01-02T03:00:00+00:00",
                  time_semantics="OBSERVED_AT", uncertainty_seconds=0,
                  latitude=35.0, longitude=129.0, owner_role="OWNER", species="HABU",
                  event_type="CAPTURE", count=1)
    result.update(changes)
    return result


def point(**changes):
    result = dict(time_utc="2026-01-02T03:00:00+00:00", latitude=35.0,
                  longitude=129.0, sequence=0, source_sha256=GPS_SHA,
                  point_id=GPS_SHA + ":0", origin="GPS_MEASURED", exclude_point=False,
                  track_index=0, segment_index=0, qc_reasons=[])
    result.update(changes)
    return result


class CaptureRouteEvidenceTests(unittest.TestCase):
    def match(self, events, points):
        self.assertIsNotNone(importlib.util.find_spec("src.capture_route_evidence"),
                             "capture sidecar implementation missing")
        from src.capture_route_evidence import match_captures
        return match_captures(events, points, source_sha256=SHA)

    def test_time_only_capture_preserves_positive_two_individuals(self):
        result = self.match([event(latitude=None, longitude=None,
                                  individual_ids=["one", "two"], count=2)], [point()])
        row = result["sidecars"][0]
        self.assertTrue(row["capture_positive_evidence"])
        self.assertEqual(row["match_status"], "TIME_ONLY_POSITIVE_EVIDENCE")
        self.assertEqual(row["event"]["individual_ids"], ["one", "two"])
        self.assertEqual(result["summary"]["capture_positive_individuals"], 2)
        self.assertEqual(row["candidates"], [])

    def test_match_requires_time_and_distance_independently(self):
        for fix, status in [(point(), "SINGLE_SAMPLE_CANDIDATE"),
                            (point(time_utc="2026-01-02T03:10:00Z"), "SINGLE_SAMPLE_CANDIDATE"),
                            (point(time_utc="2026-01-02T03:10:00.001Z"), "NO_SAMPLE_CANDIDATE"),
                            (point(latitude=35.002), "NO_SAMPLE_CANDIDATE")]:
            with self.subTest(status=status, fix=fix):
                row = self.match([event()], [fix])["sidecars"][0]
                self.assertEqual(row["match_status"], status)
        near = self.match([event()], [point(latitude=35.0008)])["sidecars"][0]
        self.assertAlmostEqual(near["candidates"][0]["distance_m"], 88.72, delta=0.15)
        self.assertEqual(near["candidates"][0]["delta_seconds"], 0)

    def test_repeated_visits_remain_ambiguous_without_duplicating_event(self):
        points = [point(), point(sequence=1, point_id=GPS_SHA + ":1",
                                 time_utc="2026-01-02T03:05:00Z")]
        result = self.match([event()], points)
        self.assertEqual(len(result["sidecars"]), 1)
        self.assertEqual(result["sidecars"][0]["match_status"], "MULTIPLE_SAMPLE_CANDIDATES")
        self.assertEqual(len(result["sidecars"][0]["candidates"]), 2)
        self.assertEqual(result["summary"]["capture_positive_individuals"], 1)

    def test_recording_delay_and_uncertainty_do_not_become_exact_event_time(self):
        for changes in ({"time_semantics": "CAPTURE_COMPLETED_AT"},
                        {"time_semantics": "RECORDED_AT"},
                        {"time_semantics": "UNKNOWN"}, {"uncertainty_seconds": 90}):
            with self.subTest(changes=changes):
                row = self.match([event(**changes)], [point()])["sidecars"][0]
                self.assertEqual(row["match_status"], "TIMING_AMBIGUOUS")
                self.assertEqual(len(row["candidates"]), 1)
                self.assertEqual(row["event"]["recorded_at"], "2026-01-02T03:00:00+00:00")

    def test_other_species_roles_and_reaction_types_stay_separate(self):
        cases = [(dict(species="HIMEHABU"), False), (dict(event_type="ROADKILL"), False),
                 (dict(event_type="SIGHTING"), False), (dict(event_type="ESCAPED"), False),
                 (dict(event_type="CAPTURED_THEN_ESCAPED"), True),
                 (dict(owner_role="OTHER"), True)]
        for changes, positive in cases:
            with self.subTest(changes=changes):
                result = self.match([event(**changes)], [point()])
                row = result["sidecars"][0]
                self.assertEqual(row["capture_positive_evidence"], positive)
                for key, value in changes.items():
                    self.assertEqual(row["event"][key], value)
                expected_owner = int(positive and changes.get("owner_role") != "OTHER")
                self.assertEqual(result["summary"]["owner_capture_individuals"], expected_owner)

    def test_duplicate_events_and_reused_individuals_fail_closed(self):
        for other in (event(), event(count=2, individual_ids=["x", "y"]),
                      event(event_id="second")):
            with self.subTest(other=other):
                with self.assertRaisesRegex(ValueError, "CAPTURE_IDENTITY_CONFLICT"):
                    self.match([event(), other], [])

    def test_excluded_bad_point_is_skipped_before_coordinate_time_validation(self):
        row = self.match([event()], [point(exclude_point=True, latitude=None,
                                          longitude=None, time_utc=None)])["sidecars"][0]
        self.assertEqual(row["match_status"], "NO_SAMPLE_CANDIDATE")

    def test_interpolated_or_untyped_point_cannot_impersonate_measurement(self):
        for fix in (point(origin="GPS_INTERPOLATED"), point(origin=None)):
            with self.subTest(fix=fix), self.assertRaises(ValueError):
                self.match([event()], [fix])

    def test_no_mutation_no_qualification_no_model_or_canonical_updates(self):
        events, points = [event()], [point()]
        before = deepcopy((events, points))
        result = self.match(events, points)
        result["sidecars"][0]["event"]["individual_ids"].append("external-mutation")
        self.assertEqual((events, points), before)
        self.assertEqual(result["summary"]["canonical_updates"], 0)
        self.assertEqual(result["summary"]["model_updates"], 0)
        for row in result["sidecars"]:
            self.assertFalse(row["formal_positive"])
            self.assertFalse(row["formal_negative"])
            self.assertFalse(row["predictive_success"])
            self.assertEqual(row["usage"], "POST_SEARCH_RESEARCH_ONLY")
        json.dumps(result, allow_nan=False)

    def test_strict_event_schema_and_hash_source_binding(self):
        bads = [event(source_sha256="c" * 64), event(recorded_at="2026-01-02T03:00:00"),
                event(uncertainty_seconds=float("nan")), event(uncertainty_seconds=-1),
                event(count=True), event(count=0), event(latitude=35, longitude=None),
                event(latitude=float("inf")), event(species="assume_habu"),
                event(individual_ids=["one", "one"], count=2), event(private_extra="sentinel")]
        for bad in bads:
            with self.subTest(keys=list(bad)):
                with self.assertRaises(ValueError) as cm:
                    self.match([bad], [])
                self.assertNotIn("sentinel", str(cm.exception))

    def test_unknown_quantity_or_missing_individual_ids_preserves_capture_event(self):
        for count, ids in [(None, []), (2, []), (2, ["known-one"])]:
            with self.subTest(count=count, ids=ids):
                result = self.match([event(count=count, individual_ids=ids)], [])
                row = result["sidecars"][0]
                self.assertTrue(row["capture_positive_evidence"])
                self.assertEqual(row["recorded_count"], count)
                self.assertEqual(row["known_individual_count"], len(ids))
                self.assertEqual(row["event"]["individual_ids"], ids)
                self.assertEqual(result["summary"]["capture_positive_events"], 1)

    def test_declared_complete_individual_list_must_match_count(self):
        with self.assertRaises(ValueError):
            self.match([event(count=2, individual_ids_complete=True)], [])
        with self.assertRaises(ValueError):
            self.match([event(count=1, individual_ids=["a", "b"])], [])

    def test_invalid_route_identity_or_timestamp_fail_closed(self):
        for fix in (point(sequence=True), point(source_sha256="invalid"),
                    point(point_id="wrong"), point(exclude_point="false"),
                    point(time_utc="2026-01-02T03:00:00"), point(latitude=95)):
            with self.subTest(fix=fix), self.assertRaises(ValueError):
                self.match([event()], [fix])
        with self.assertRaises(ValueError):
            self.match([event()], [point(), point()])

    def test_timezone_equivalent_and_order_independent_point_matching(self):
        events = [event(recorded_at="2026-01-02T12:00:00+09:00")]
        points = [point(sequence=2, point_id=GPS_SHA + ":2", time_utc="2026-01-02T03:05:00Z"), point()]
        row = self.match(events, points)["sidecars"][0]
        self.assertEqual([p["delta_seconds"] for p in row["candidates"]], [0, 300])

    def test_numeric_overflow_is_sanitized_and_projected_region_enforced(self):
        for change in ({"latitude": 10 ** 1000}, {"longitude": -10},
                       {"uncertainty_seconds": 10 ** 1000}):
            with self.subTest(field=list(change)), self.assertRaises(ValueError):
                self.match([event(**change)], [])

    def test_datetime_endpoints_keep_inclusive_time_boundary(self):
        for instant in ("0001-01-01T00:00:00Z", "9999-12-31T23:59:59.999999Z"):
            with self.subTest(instant=instant):
                row = self.match([event(recorded_at=instant)],
                                 [point(time_utc=instant)])["sidecars"][0]
                self.assertEqual(row["match_status"], "SINGLE_SAMPLE_CANDIDATE")

    def test_candidate_and_comparison_budgets_fail_without_partial_output(self):
        points = [point(), point(sequence=1, point_id=GPS_SHA + ":1")]
        for limit in ("MAX_CANDIDATES", "MAX_COMPARISONS"):
            with self.subTest(limit=limit), patch("src.capture_route_evidence." + limit, 1):
                with self.assertRaisesRegex(ValueError, "CAPTURE_BUDGET_EXCEEDED"):
                    self.match([event()], points)

    def test_unknown_species_does_not_create_habu_capture_positive(self):
        row = self.match([event(species="UNKNOWN", count=None, individual_ids=[])],
                         [point()])["sidecars"][0]
        self.assertFalse(row["capture_positive_evidence"])
        self.assertIsNone(row["recorded_count"])

    def test_sample_uncertainty_is_retained_without_certifying_actual_distance(self):
        row = self.match([event()], [point(accuracy_m=80, hdop=3)])["sidecars"][0]
        candidate = row["candidates"][0]
        self.assertEqual(candidate["accuracy_m"], 80)
        self.assertEqual(candidate["hdop"], 3)
        self.assertEqual(candidate["distance_semantics"], "RECORDED_COORDINATE_CENTERS")
        self.assertFalse(row["formal_positive"])

    def test_nonfinite_sample_accuracy_cannot_escape_as_json(self):
        with self.assertRaises(ValueError):
            self.match([event()], [point(accuracy_m=float("nan"))])


if __name__ == "__main__":
    unittest.main()
