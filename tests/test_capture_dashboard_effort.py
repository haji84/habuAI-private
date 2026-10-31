"""Owner-confirmed non-scientific effort ledger regression tests."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_capture_dashboard import CaptureDataError, build

ROOT = Path(__file__).resolve().parents[1]


class OwnerEffortTests(unittest.TestCase):
    def make_repo(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        (root / "dashboard").mkdir()
        for filename in ("baseline_2026.json", "owner_effort_2026-10-26.json"):
            (root / "dashboard" / filename).write_bytes(
                (ROOT / "dashboard" / filename).read_bytes()
            )
        return tmp, root

    def test_confirmed_totals_and_months(self):
        result = build(ROOT)
        self.assertEqual(result["total"], 262)
        self.assertEqual(result["asof"], "2026-10-30")
        effort = result["effort"]
        self.assertEqual((effort["total_nights"], effort["positive_nights"], effort["zero_nights"]),
                         (101, 90, 11))
        self.assertAlmostEqual(effort["per_night_average"], 262 / 101, places=3)
        self.assertTrue(effort["not_model_exposure"])
        self.assertTrue(effort["not_negative_training_labels"])
        self.assertEqual([m["nights"] for m in result["effort_months"]],
                         [8, 16, 15, 15, 18, 16, 13])
        self.assertEqual([m["captures"] for m in result["effort_months"]],
                         [10, 23, 60, 35, 47, 51, 36])
        nights = {n["night"]: n for n in result["nights"]}
        self.assertEqual(nights["2026-10-22"]["count"], 2)
        self.assertEqual(nights["2026-10-24"]["count"], 4)
        self.assertEqual({day:nights[day]["count"] for day in ("2026-10-26","2026-10-28","2026-10-29","2026-10-30")},
                         {"2026-10-26":3,"2026-10-28":2,"2026-10-29":2,"2026-10-30":6})
        self.assertFalse(nights["2026-09-20"]["effort_confirmed"])
        self.assertEqual(nights["2026-09-20"]["effort_status"], "EXCLUDED_NOT_SEARCH")
        for day in ("2026-04-12", "2026-04-17"):
            self.assertTrue(nights[day]["effort_confirmed"])
            self.assertEqual(nights[day]["count"], 0)
            self.assertIn("本人確認済み", nights[day]["status"])
        self.assertNotIn("2026-08-30", nights)

    def test_equal_canonical_capture_does_not_double_count(self):
        tmp, repo = self.make_repo()
        try:
            root = repo / "data/raw/habu_logs/2026"
            root.mkdir(parents=True)
            entry = {
                "schema_version": "habu-night-log-v2", "source": "user Habu log",
                "operational_date": "2026-10-22", "events": [
                    {"event_id": "two-captures", "type": "capture",
                     "species": "ハブ", "capture_owner": "self",
                     "individual_count": 2,
                     "time_local": "2026-10-22T20:00:00+09:00"}
                ],
            }
            p = root / "2026-10-22.json"
            p.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(build(repo)["total"], 249)
            entry["events"][0]["individual_count"] = 3
            p.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(CaptureDataError):
                build(repo)
        finally:
            tmp.cleanup()

    def test_explicit_zero_night_updates_effort_not_captures(self):
        tmp, repo = self.make_repo()
        try:
            root = repo / "data/raw/habu_effort/2026"
            root.mkdir(parents=True)
            p = root / "2026-10-27.json"
            record = {"schema_version": "habu-effort-night-v1",
                      "source": "user Habu log", "operational_date": "2026-10-27",
                      "owner_confirmed": True, "search_performed": True,
                      "capture_count": 0}
            p.write_text(json.dumps(record), encoding="utf-8")
            result = build(repo)
            self.assertEqual(result["asof"], "2026-10-27")
            self.assertEqual(result["total"], 249)
            self.assertEqual(result["effort"]["total_nights"], 98)
            self.assertEqual(result["effort"]["zero_nights"], 12)
            self.assertEqual(result["effort_months"][-1]["nights"], 10)
            record["owner_confirmed"] = False
            p.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaises(CaptureDataError):
                build(repo)
        finally:
            tmp.cleanup()

    def test_new_capture_night_after_scope(self):
        tmp, repo = self.make_repo()
        try:
            root = repo / "data/raw/habu_logs/2026"
            root.mkdir(parents=True)
            (root / "2026-10-25.json").write_text(json.dumps({
                "schema_version": "habu-night-log-v2", "source": "user Habu log",
                "operational_date": "2026-10-25",
                "events": [{"event_id": "future", "type": "capture",
                            "species": "ハブ", "capture_owner": "self",
                            "individual_count": 1,
                            "time_local": "2026-10-25T20:00:00+09:00"}]
            }, ensure_ascii=False), encoding="utf-8")
            result = build(repo)
            self.assertEqual(result["total"], 250)
            self.assertEqual(result["effort"]["total_nights"], 98)
            self.assertEqual(result["effort"]["positive_nights"], 87)
        finally:
            tmp.cleanup()

    def test_malformed_pdca_receipt_is_blocked(self):
        tmp, repo = self.make_repo()
        try:
            root = repo / "data/reconstructions/habu_captures"
            root.mkdir(parents=True)
            (root / "2026-10-22-owner-chat-dashboard-intake.json").write_text(
                "{}", encoding="utf-8"
            )
            with self.assertRaises(CaptureDataError):
                build(repo)
        finally:
            tmp.cleanup()

    def test_pr92_and_pr136_sources_reconcile_once(self):
        tmp, repo = self.make_repo()
        try:
            root = repo / "data/reconstructions/habu_captures"
            root.mkdir(parents=True)
            for day in ("2026-10-22", "2026-10-24"):
                file = day + "-owner-chat-dashboard-intake.json"
                (root / file).write_bytes(
                    (ROOT / "data/reconstructions/habu_captures" / file).read_bytes()
                )
            result = build(repo)
            self.assertEqual(result["total"], 249)
            self.assertEqual(result["months"][-1]["n"], 23)
            self.assertEqual(result["owner_chat_statistics"]["reported_capture_events"], 6)
            self.assertEqual(result["owner_chat_statistics"]["formal_training_positive_from_review"], 0)
            self.assertEqual(result["owner_chat_statistics"]["formal_training_negative_from_review"], 0)
            self.assertEqual(result["nights"][-1]["count"], 4)

            # A matching independent report never increments the six again.
            receipt = root / "2026-10-24-owner-chat-dashboard-intake.json"
            item = json.loads(receipt.read_text(encoding="utf-8"))
            item["capture_events"].pop()
            receipt.write_text(json.dumps(item, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(CaptureDataError, "disagree"):
                build(repo)
        finally:
            tmp.cleanup()

    def test_invalid_owner_confirmation_is_rejected(self):
        tmp, repo = self.make_repo()
        try:
            path = repo / "dashboard/owner_effort_2026-10-26.json"
            ledger = json.loads(path.read_text(encoding="utf-8"))
            ledger["capture_nights"][1]["count"] = 5
            path.write_text(json.dumps(ledger), encoding="utf-8")
            with self.assertRaises(CaptureDataError):
                build(repo)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
