"""Regression tests for owner-confirmed, idempotent capture/effort updates."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_capture_dashboard import CaptureDataError, build

ROOT = Path(__file__).resolve().parents[1]


class DashboardAutomationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        dashboard = self.repo / "dashboard"
        dashboard.mkdir()
        for name in ("baseline_2026.json", "owner_effort_2026-10-26.json"):
            (dashboard / name).write_bytes((ROOT / "dashboard" / name).read_bytes())

    def owner_night(self, date, count, revision=1, **extra):
        file = self.repo / "data/raw/habu_owner_nights/2026" / (date + ".json")
        file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "habu-owner-night-v1",
            "source": "user Habu log",
            "operational_date": date,
            "owner_confirmed": True,
            "search_performed": True,
            "capture_count": count,
            "revision": revision,
        }
        payload.update(extra)
        file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return file

    def amendment(self, date, before_count, after_count, searched_before=True,
                  searched_after=True, revision=1, **extra):
        file = self.repo / "data/raw/habu_owner_amendments/2026" / (date + ".json")
        file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "habu-owner-amendment-v1",
            "source": "user Habu log", "operational_date": date,
            "revision": revision, "owner_confirmed": True,
            "original_captures": before_count,
            "original_search_performed": searched_before,
            "capture_count": after_count, "search_performed": searched_after,
            "reason": "本人確認による数量訂正",
        }
        payload.update(extra)
        file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return file

    def test_future_capture_and_zero_nights_recalculate_every_metric(self):
        self.owner_night("2026-10-27", 3)
        self.owner_night("2026-10-28", 0)
        data = build(self.repo)
        self.assertEqual((data["total"], data["asof"]), (252, "2026-10-28"))
        self.assertEqual((data["effort"]["total_nights"], data["effort"]["positive_nights"],
                          data["effort"]["zero_nights"]), (99, 87, 12))
        self.assertAlmostEqual(data["effort"]["per_night_average"], 252 / 99, places=3)
        self.assertEqual((data["effort_months"][-1]["captures"],
                          data["effort_months"][-1]["nights"]), (26, 11))
        self.assertEqual(data["months"][-1]["cum"], 252)
        # Rebuilding from the same immutable source does not add counts again.
        self.assertEqual(build(self.repo)["total"], 252)
        self.assertEqual((data["effort"]["not_model_exposure"],
                          data["effort"]["not_negative_training_labels"]), (True, True))

    def test_updating_same_future_night_replaces_not_adds(self):
        path = self.owner_night("2026-10-27", 3)
        self.assertEqual(build(self.repo)["total"], 252)
        obj = json.loads(path.read_text(encoding="utf-8"))
        obj["capture_count"] = 4
        obj["revision"] = 2
        path.write_text(json.dumps(obj), encoding="utf-8")
        result = build(self.repo)
        self.assertEqual(result["total"], 253)
        self.assertEqual(result["effort"]["total_nights"], 98)
        self.assertEqual(result["effort"]["positive_nights"], 87)

    def test_canonical_matches_once_and_conflict_fails_closed(self):
        self.owner_night("2026-10-27", 3)
        root = self.repo / "data/raw/habu_logs/2026"
        root.mkdir(parents=True)
        path = root / "2026-10-27.json"
        event = {
            "schema_version": "habu-night-log-v2", "source": "user Habu log",
            "operational_date": "2026-10-27",
            "events": [{"type": "capture", "species": "ハブ",
                        "capture_owner": "self", "event_id": "confirmed-e1",
                        "individual_count": 3,
                        "time_local": "2026-10-27T20:00:00+09:00"}],
        }
        path.write_text(json.dumps(event, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(build(self.repo)["total"], 252)
        event["events"][0]["individual_count"] = 4
        path.write_text(json.dumps(event, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(CaptureDataError, "conflict"):
            build(self.repo)

    def test_historical_correction_recalculates_without_changing_original(self):
        baseline = (self.repo / "dashboard/baseline_2026.json").read_bytes()
        self.amendment("2026-10-24", 4, 3)
        data = build(self.repo)
        self.assertEqual(data["total"], 248)
        self.assertEqual((data["effort"]["total_nights"], data["effort"]["positive_nights"],
                          data["effort"]["zero_nights"]), (97, 86, 11))
        self.assertEqual((data["effort_months"][-1]["captures"],
                          data["effort_months"][-1]["nights"]), (22, 9))
        self.assertEqual(data["owner_amendments"][0]["corrected_count"], 3)
        self.assertEqual((self.repo / "dashboard/baseline_2026.json").read_bytes(), baseline)

    def test_zero_night_corrected_to_capture_and_excluded_to_search(self):
        self.amendment("2026-04-12", 0, 1)
        self.amendment("2026-09-20", 0, 0,
                       searched_before=False, searched_after=True)
        data = build(self.repo)
        self.assertEqual(data["total"], 250)
        self.assertEqual((data["effort"]["total_nights"], data["effort"]["positive_nights"],
                          data["effort"]["zero_nights"]), (98, 87, 11))
        by_date = {n["night"]: n for n in data["nights"]}
        self.assertEqual(by_date["2026-04-12"]["effort_status"], "OWNER_AMENDED_CAPTURE")
        self.assertEqual(by_date["2026-09-20"]["effort_status"], "OWNER_AMENDED_ZERO")

    def test_unconfirmed_unknown_and_invalid_amendments_are_rejected(self):
        path = self.amendment("2026-10-24", 7, 3)
        with self.assertRaisesRegex(CaptureDataError, "conflicts"):
            build(self.repo)
        path = self.amendment("2026-10-29", 0, 1)
        with self.assertRaisesRegex(CaptureDataError, "conflicts"):
            build(self.repo)
        path.unlink()
        path = self.amendment("2026-10-24", 4, 3, owner_confirmed=False)
        with self.assertRaisesRegex(CaptureDataError, "Unconfirmed"):
            build(self.repo)

    def test_unconfirmed_privacy_fields_and_history_overlap_are_rejected(self):
        self.owner_night("2026-10-27", 3, owner_confirmed=False)
        with self.assertRaisesRegex(CaptureDataError, "Unconfirmed"):
            build(self.repo)
        self.owner_night("2026-10-27", 3, latitude=28.0)
        with self.assertRaisesRegex(CaptureDataError, "fields"):
            build(self.repo)
        path = self.owner_night("2026-10-22", 2)
        with self.assertRaisesRegex(CaptureDataError, "protected history"):
            build(self.repo)
        path.unlink()

    def test_duplicate_legacy_zero_night_sources_fail(self):
        self.owner_night("2026-10-27", 0)
        folder = self.repo / "data/raw/habu_effort/2026"
        folder.mkdir(parents=True)
        (folder / "2026-10-27.json").write_text(json.dumps({
            "schema_version": "habu-effort-night-v1",
            "source": "user Habu log", "operational_date": "2026-10-27",
            "owner_confirmed": True, "search_performed": True, "capture_count": 0,
        }), encoding="utf-8")
        with self.assertRaisesRegex(CaptureDataError, "Duplicate future zero"):
            build(self.repo)


if __name__ == "__main__":
    unittest.main()
