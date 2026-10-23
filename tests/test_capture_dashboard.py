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
        self.assertEqual(data["total"], 241)
        self.assertEqual([m["n"] for m in data["months"]], [11, 23, 60, 35, 45, 50, 17])
        self.assertEqual(data["asof"], "2026-10-20")

    def test_april_29_restores_three_dated_captures_without_double_count(self):
        data = build(ROOT)
        april_nights = [x for x in data["nights"] if x["month"] == "2026-04"]
        self.assertEqual(sum(x["count"] for x in april_nights), 11)
        self.assertEqual(next(x["count"] for x in april_nights if x["night"] == "2026-04-29"), 3)
        self.assertEqual(data["undated_count"], 0)
        self.assertEqual(data["undated_captures"], [])
        self.assertEqual(data["months"][0]["n"], 11)
        self.assertEqual(data["months"][-1]["cum"], 241)
        self.assertTrue(all(x["night"][:7] == "2026-04" for x in april_nights))

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
            self.assertEqual(out["total"], 243)
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
            self.assertEqual(build(repo)["total"], 241)
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
