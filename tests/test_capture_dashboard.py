"""Regression tests for the frozen personal capture dashboard."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.build_capture_dashboard import CaptureDataError, build, operational_night

ROOT = Path(__file__).resolve().parents[1]


class DashboardTests(unittest.TestCase):
    def make_repo(self):
        temp = tempfile.TemporaryDirectory()
        repo = Path(temp.name)
        (repo / "dashboard").mkdir()
        (repo / "dashboard/baseline_2026.json").write_bytes(
            (ROOT / "dashboard/baseline_2026.json").read_bytes()
        )
        return temp, repo

    def add(self, repo, night, events, filename="one.json"):
        folder = repo / "data/raw/habu_logs/2026"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / filename).write_text(
            json.dumps({
                "schema_version": "habu-night-log-v2",
                "source": "user Habu log", "operational_date": night,
                "events": events
            }, ensure_ascii=False),
            encoding="utf-8"
        )

    def event(self, identifier="x", owner="self", kind="capture", n=1):
        return {"event_id": identifier, "type": kind,
                "capture_owner": owner, "individual_count": n,
                "species": "ハブ", "time_local": "2026-10-22T00:30:00+09:00",
                "place": "Private location"}

    def test_frozen_baseline(self):
        data = build(ROOT)
        self.assertEqual(data["total"], 240)
        self.assertEqual([m["n"] for m in data["months"]], [10, 23, 60, 35, 45, 50, 17])
        self.assertEqual(data["asof"], "2026-10-20")

    def test_april_reconciles_to_ten_without_false_legacy_captures(self):
        data = build(ROOT)
        april_nights = [x for x in data["nights"] if x["month"] == "2026-04"]
        self.assertEqual(sum(x["count"] for x in april_nights), 10)
        self.assertEqual(next(x["count"] for x in april_nights
                              if x["night"] == "2026-04-17"), 0)
        self.assertEqual(next(x["count"] for x in april_nights
                              if x["night"] == "2026-04-28"), 1)
        self.assertEqual(next(x["count"] for x in april_nights
                              if x["night"] == "2026-04-29"), 3)
        self.assertEqual(data["undated_count"], 0)
        self.assertEqual(data["undated_captures"], [])
        self.assertEqual(data["months"][0]["n"], 10)
        self.assertEqual(data["months"][-1]["cum"], 240)
        self.assertTrue(all(x["night"][:7] == "2026-04" for x in april_nights))
        april28 = next(x for x in april_nights if x["night"] == "2026-04-28")
        self.assertIn("原文", april28["status"])
        self.assertIn("学習", april28["note"])

    def test_april_reconciliation_keeps_gpx_and_training_unverified(self):
        path = ROOT / "data/reconstructions/habu_captures/2026-04-count-reconciliation-10.json"
        evidence = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(evidence["revised_month_count"], 10)
        self.assertEqual(evidence["revised_season_total_through_2026_10_20"], 240)
        self.assertEqual(evidence["dated_total"], 10)
        self.assertEqual(evidence["undated_count"], 0)
        self.assertFalse(evidence["inclusion_policy"]["model_training_as_verified_positive"])
        self.assertFalse(evidence["inclusion_policy"]["stage_gate_verified_positive"])
        self.assertFalse(evidence["inclusion_policy"]["negative_or_exposure_generation"])
        report = next(x for x in evidence["evidence"]
                      if x["type"] == "owner_conversation_index")
        self.assertFalse(report["verbatim_report_recovered"])
        self.assertIsNone(report["canonical_event_id"])
        self.assertIsNone(report["lat"])
        self.assertIsNone(report["lon"])
        self.assertIsNone(report["gpx"])
        receipts = next(x for x in evidence["evidence"]
                        if x["type"] == "owner_purchase_history")
        self.assertEqual(sum(x["count"] for x in receipts["purchase_dates"]), 10)
        self.assertFalse(receipts["purchase_day_is_capture_day"])

    def test_april_29_reconstructed_event_ids_no_fake_gpx(self):
        source = ROOT / "data/reconstructions/habu_captures/2026-04-29-owner-chat.json"
        evidence = json.loads(source.read_text(encoding="utf-8"))
        self.assertEqual(evidence["operational_night"], "2026-04-29")
        self.assertEqual(evidence["reported_count"], 3)
        self.assertEqual(evidence["source"]["kind"], "owner_conversation")
        self.assertEqual(evidence["evidence_grade"], "PROVISIONAL_OWNER_REPORT")
        self.assertFalse(evidence["inclusion_policy"]["model_training_positive"])
        self.assertFalse(evidence["inclusion_policy"]["stage_gate_positive"])
        self.assertFalse(evidence["inclusion_policy"]["negative_or_exposure_generation"])
        self.assertFalse(evidence["gps_reconstruction"]["gpx_source_found"])
        self.assertFalse(evidence["gps_reconstruction"]["gps_points_found"])
        self.assertFalse(evidence["gps_reconstruction"]["route_recreated"])
        self.assertFalse(evidence["gps_reconstruction"]["negative_exposure_eligible"])
        self.assertEqual(evidence["duplicate_review"]["april_total"], 11)  # historical source snapshot
        self.assertEqual(evidence["duplicate_review"]["season_total_through_20261020"], 241)  # historical
        events = evidence["events"]
        self.assertEqual(len(events), 3)
        self.assertEqual(len({x["reconstruction_id"] for x in events}), 3)
        self.assertEqual(
            [(x["reported_local_time"], x["reported_place"], x["size_reported"])
             for x in events],
            [("20:19", "伊須", "小型"), ("22:21", "勝浦", "小型"),
             ("23:10", "嘉鉄", "中型")],
        )
        for x in events:
            self.assertEqual(x["capture_owner"], "self")
            self.assertEqual(x["time_precision"], "approximately (頃)")
            self.assertIsNone(x["original_event_id"])
            self.assertIsNone(x["canonical_individual_id"])
            self.assertIsNone(x["lat"])
            self.assertIsNone(x["lon"])
            self.assertIsNone(x["gpx_point_id"])
            self.assertEqual(
                operational_night(
                    "2026-04-29T" + x["reported_local_time"] + ":00+09:00"
                ),
                "2026-04-29",
            )
        dashboard = build(ROOT)
        april_29 = next(x for x in dashboard["nights"]
                        if x["night"] == "2026-04-29")
        self.assertEqual(april_29["count"], 3)
        self.assertEqual(dashboard["total"], 240)
        # The published dashboard must not expose locality or a fabricated track.
        self.assertNotIn("伊須", json.dumps(dashboard, ensure_ascii=False))
        self.assertNotIn("勝浦", json.dumps(dashboard, ensure_ascii=False))
        self.assertNotIn("嘉鉄", json.dumps(dashboard, ensure_ascii=False))

    def test_undated_counts_cannot_hide_missing_baseline(self):
        tmp, repo = self.make_repo()
        try:
            path = repo / "dashboard/baseline_2026.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            next(x for x in payload["nights"] if x["night"] == "2026-04-29")["count"] = 2
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(CaptureDataError):
                build(repo)
        finally:
            tmp.cleanup()

    def test_invalid_reconciliation_requires_review(self):
        tmp, repo = self.make_repo()
        try:
            path = repo / "dashboard/baseline_2026.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["undated_captures"] = [{"month": "2026-04", "count": 1, "review_status": "CONFIRMED"}]
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(CaptureDataError):
                build(repo)
        finally:
            tmp.cleanup()

    def test_night_boundary(self):
        self.assertEqual(operational_night("2026-10-22T06:59:59+09:00"), "2026-10-21")
        self.assertEqual(operational_night("2026-10-22T07:00:00+09:00"), "2026-10-22")
        with self.assertRaises(CaptureDataError):
            operational_night("2026-10-22T00:30:00")

    def test_new_capture_no_sightings_or_third_party(self):
        tmp, repo = self.make_repo()
        try:
            self.add(repo, "2026-10-21", [
                self.event("a", n=2), self.event("b", owner="other"),
                self.event("c", kind="sighting")])
            out = build(repo)
            self.assertEqual(out["total"], 242)
            self.assertEqual(out["months"][-1]["n"], 19)
            self.assertEqual(out["new_confirmed_nights"], 1)
            rendered = json.dumps(out, ensure_ascii=False)
            self.assertNotIn("Private location", rendered)
            self.assertNotIn("latitude", rendered)
        finally:
            tmp.cleanup()

    def test_duplicate_event_blocks(self):
        tmp, repo = self.make_repo()
        try:
            event = self.event()
            self.add(repo, "2026-10-21", [event], filename="first.json")
            self.add(repo, "2026-10-21",
                     [event, self.event("second")], filename="second.json")
            with self.assertRaises(CaptureDataError):
                build(repo)
        finally:
            tmp.cleanup()

    def test_old_logs_do_not_change_baseline(self):
        tmp, repo = self.make_repo()
        try:
            self.add(repo, "2026-09-28", [
                {"type": "capture", "event_id": "old", "individual_count": 99,
                 "time_local": "2026-09-28T21:00:00+09:00"}])
            self.assertEqual(build(repo)["total"], 240)
        finally:
            tmp.cleanup()

    def test_conflicting_raw_and_individuals_blocks(self):
        tmp, repo = self.make_repo()
        try:
            self.add(repo, "2026-10-21", [self.event("a", n=2)])
            folder = repo / "data/processed/individuals/2026"
            folder.mkdir(parents=True)
            (folder / "2026-10-21.csv").write_text(
                "individual_id,operational_date,event_time_local,capture_owner\n"
                "a,2026-10-21,2026-10-21T23:00:00+09:00,self\n",
                encoding="utf-8"
            )
            with self.assertRaises(CaptureDataError):
                build(repo)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
