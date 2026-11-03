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
        self.assertEqual(data["total"], 249)
        self.assertEqual([m["n"] for m in data["months"]], [10, 23, 60, 35, 47, 51, 23])
        self.assertEqual(data["asof"], "2026-10-24")
        self.assertEqual(
            data["owner_confirmed_monthly_counts"]["2026-04"]["status"],
            "OWNER_CONFIRMED",
        )
        self.assertEqual(
            data["owner_confirmed_monthly_counts"]["2026-04"]["count"], 10
        )
        self.assertFalse(
            data["owner_confirmed_monthly_counts"]["2026-04"][
                "independent_event_time_location_gpx_verification"
            ]
        )

    def test_owner_confirmed_august_47_and_aug31_two_captures(self):
        data=build(ROOT)
        august=[n for n in data["nights"] if n["month"]=="2026-08"]
        self.assertEqual(sum(n["count"] for n in august),47)
        self.assertEqual(len(august),17)
        self.assertEqual(next(n["count"] for n in august if n["night"]=="2026-08-31"),2)
        self.assertEqual(data["months"][4]["cum"],175)
        self.assertEqual(data["months"][5]["cum"],226)
        self.assertEqual(data["total"],249)
        confirmation=data["owner_confirmed_monthly_counts"]["2026-08"]
        self.assertEqual(confirmation["status"],"OWNER_CONFIRMED")
        self.assertEqual(confirmation["count"],47)
        self.assertFalse(confirmation["independent_event_time_location_gpx_verification"])
        evidence=json.loads((ROOT/confirmation["correction_evidence"]).read_text(encoding="utf-8"))
        self.assertEqual(evidence["owner_confirmation"]["confirmed_count"],47)
        self.assertEqual(evidence["reconciliation"]["newly_allocated_august31_day_count"],2)
        self.assertTrue(evidence["evidence_interpretation"]["log_byte_exact_native_original_verified"] is False)
        self.assertEqual(evidence["evidence_interpretation"]["formal_negative_training_rows_added"],0)

    def test_undated_owner_august_count_tamper_rejected(self):
        temp,repo=self.make_repo()
        try:
            p=repo/"dashboard/baseline_2026.json"
            b=json.loads(p.read_text(encoding="utf-8"))
            b["owner_confirmed_monthly_counts"]["2026-08"]["count"]=45
            p.write_text(json.dumps(b,ensure_ascii=False),encoding="utf-8")
            with self.assertRaises(CaptureDataError):
                build(repo)
        finally:
            temp.cleanup()

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
        self.assertEqual(data["months"][-1]["cum"], 249)
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
        self.assertEqual(evidence["status"], "OWNER_CONFIRMED_MONTHLY_TOTAL")
        self.assertEqual(
            evidence["owner_monthly_confirmation"]["confirmation_scope"],
            "monthly_capture_count_only",
        )
        self.assertTrue(
            evidence["inclusion_policy"]["monthly_capture_count_owner_confirmed"]
        )
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
        self.assertEqual(dashboard["total"], 249)
        # The published dashboard must not expose locality or a fabricated track.
        self.assertNotIn("伊須", json.dumps(dashboard, ensure_ascii=False))
        self.assertNotIn("勝浦", json.dumps(dashboard, ensure_ascii=False))
        self.assertNotIn("嘉鉄", json.dumps(dashboard, ensure_ascii=False))

    def test_september_28_five_events_are_six_individual_captures(self):
        data = build(ROOT)
        night = next(x for x in data["nights"] if x["night"] == "2026-09-28")
        self.assertEqual(night["count"], 6)
        self.assertEqual(data["months"][5]["n"], 51)
        self.assertEqual(data["months"][-1]["cum"], 249)
        self.assertIn("5捕獲イベント", night["status"])
        self.assertEqual(data["owner_confirmed_monthly_counts"]["2026-04"]["count"], 10)

    def test_october_22_and_24_owner_report_source_and_reaction_metrics(self):
        data=build(ROOT)
        self.assertEqual(data["total"],249)
        self.assertEqual(data["asof"],"2026-10-24")
        self.assertEqual(data["months"][-1]["n"],23)
        day={x["night"]:x for x in data["nights"]}
        self.assertEqual(day["2026-10-22"]["count"],2)
        self.assertEqual(day["2026-10-24"]["count"],4)
        self.assertEqual(day["2026-10-24"]["sighting"],32)
        self.assertEqual(day["2026-10-24"]["roadkill"],3)
        self.assertEqual(day["2026-10-24"]["pdca_status"],"BLOCKED")
        self.assertEqual(day["2026-10-22"]["pdca_status"],"BLOCKED")
        self.assertEqual(data["new_confirmed_nights"],0)  # review source is not canonical individual proof
        self.assertEqual(data["new_owner_report_nights"],2)
        summary=data["owner_chat_statistics"]
        self.assertEqual(summary["reported_capture_events"],6)
        self.assertEqual(summary["fauna_sighting_events"],53)
        self.assertEqual(summary["fauna_sighting_quantity"],59)
        self.assertEqual(summary["roadkill_events"],4)
        self.assertEqual(summary["habu_roadkill_events"],2)
        self.assertEqual(summary["owner_capture_size_distribution"]["小型"],4)
        self.assertEqual(summary["owner_capture_size_distribution"]["かなり大型"],1)
        self.assertEqual(summary["owner_capture_size_distribution"]["超大型"],1)
        self.assertEqual(summary["capture_road_surface_distribution"],{"ウエット":3,"ドライ":3})
        self.assertEqual(summary["gps_gap_nights"],[{"night":"2026-10-24","gap_seconds":4054}])
        self.assertEqual(summary["temperature_reports_unlocated_c"],[{"night":"2026-10-24","values":[29,26,28]}])
        self.assertEqual(summary["formal_training_negative_from_review"],0)
        self.assertEqual(summary["formal_training_positive_from_review"],0)
        serialized=json.dumps(data,ensure_ascii=False)
        for sensitive in ("28.24570181906794","129.3335101852521","古仁屋瀬久井西"):
            self.assertNotIn(sensitive,serialized)

    def test_duplicate_or_fake_owner_report_does_not_raise_capture_count(self):
        temp,repo=self.make_repo()
        try:
            folder=repo/"data/reconstructions/habu_captures"
            folder.mkdir(parents=True)
            report=json.loads((ROOT/"data/reconstructions/habu_captures/2026-10-24-owner-chat-dashboard-intake.json").read_text(encoding="utf-8"))
            path=folder/"2026-10-24-owner-chat-dashboard-intake.json"
            path.write_text(json.dumps(report,ensure_ascii=False),encoding="utf-8")
            self.assertEqual(build(repo)["total"],247)
            report["capture_events"][1]["event_id"]=report["capture_events"][0]["event_id"]
            path.write_text(json.dumps(report,ensure_ascii=False),encoding="utf-8")
            with self.assertRaisesRegex(CaptureDataError,"Duplicate"):
                build(repo)
            report["capture_events"][1]["event_id"]="owner-chat-20261024-0023"
            report["scientific_restrictions"]["eligible_learning_negative_count"]=999
            path.write_text(json.dumps(report,ensure_ascii=False),encoding="utf-8")
            with self.assertRaisesRegex(CaptureDataError,"cannot promote"):
                build(repo)
        finally:
            temp.cleanup()

    def test_raw_conflict_with_owner_source_is_not_double_counted(self):
        temp,repo=self.make_repo()
        try:
            folder=repo/"data/reconstructions/habu_captures"
            folder.mkdir(parents=True)
            p=ROOT/"data/reconstructions/habu_captures/2026-10-22-owner-chat-dashboard-intake.json"
            (folder/p.name).write_bytes(p.read_bytes())
            one=self.event("same",n=1);one["time_local"]="2026-10-23T00:10:00+09:00"
            two=self.event("extra",n=1);two["time_local"]="2026-10-23T00:48:00+09:00"
            self.add(repo,"2026-10-22",[one],filename="canonical.json")
            with self.assertRaisesRegex(CaptureDataError,"conflict"):
                build(repo)
            self.add(repo,"2026-10-22",[one,two],filename="canonical.json")
            self.assertEqual(build(repo)["total"],245)
        finally:
            temp.cleanup()

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

    def test_owner_confirmation_does_not_allow_mismatched_month_count(self):
        tmp, repo = self.make_repo()
        try:
            path = repo / "dashboard/baseline_2026.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["owner_confirmed_monthly_counts"]["2026-04"]["count"] = 11
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
            self.assertEqual(out["total"], 245)
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
            self.assertEqual(build(repo)["total"], 243)
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
