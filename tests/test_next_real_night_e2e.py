"""Read-only future-night acceptance never promotes synthetic or unauthenticated evidence."""
import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

import pdca_pipeline
from master_contracts import canonical_bytes

spec = importlib.util.spec_from_file_location(
    "next_night_e2e", ROOT / "scripts" / "audit_next_real_night_e2e.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
JST = ZoneInfo("Asia/Tokyo")
NIGHT = "2026-11-02"
START = datetime(2026, 11, 2, 19, 0, tzinfo=JST)
NOW = datetime(2026, 11, 2, 17, 0, tzinfo=JST)
WINDOWS_WITHOUT_FCNTL = sys.platform == "win32" and importlib.util.find_spec("fcntl") is None


class RealNightE2EAcceptanceTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)

    def check(self, phase="after", start=START, now=NOW):
        return gate.inspect(self.root, NIGHT, actual_start=start, phase=phase, now=now)

    def codes(self, result):
        return {v["code"] for v in result["blockers"]}

    def write_report(self, *, stages=None, padding_size=0, bind_manifest=False):
        report = {
            "operational_night": NIGHT, "overall_status": "PASS",
            "completed": True, "run_id": "f" * 64,
            "stages": ([{"name": n, "status": "PASS"} for n in gate.STAGE_NAMES]
                       if stages is None else stages),
            "operational_result": {"p0_score": {"strict_official_score_eligible": True}},
        }
        if padding_size:
            report["synthetic_padding"] = "x" * padding_size
        raw = json.dumps(report).encode("utf-8")
        path = self.root / f"reports/pdca/{NIGHT}/pdca_result.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        if bind_manifest:
            manifest = path.parent / "runs" / report["run_id"] / "run_manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_bytes(raw)
        return path

    def assert_capacity_blocked(self, result):
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["official_e2e_complete"])
        self.assertTrue(any("CAPACITY_BLOCKED" in b["detail"]
                            for b in result["blockers"]), result["blockers"])

    def test_mixed_stage_members_are_structured_invalid(self):
        stages = [{"name": n, "status": "PASS"} for n in gate.STAGE_NAMES] + [None]
        self.write_report(stages=stages)
        try:
            result = self.check()
        except AttributeError as exc:
            self.fail(f"Malformed stage member escaped the structured blocker: {exc}")
        self.assertIn("PDCA_REPORT_INVALID", self.codes(result))
        self.assertFalse(result["official_e2e_complete"])

    def test_physical_oversize_report_is_capacity_blocked(self):
        path = self.write_report(padding_size=16 * 1024**2)
        self.assertGreater(path.stat().st_size, 16 * 1024**2)
        self.assert_capacity_blocked(self.check())

    def test_physical_prediction_reads_share_cumulative_byte_budget(self):
        raw_total = 0
        padding = "x" * (13 * 1024**2)
        for version in range(1, 6):
            path = self.root / f"predictions/original/{NIGHT}/P{version}/prediction.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"prediction_version": f"P{version}",
                                       "synthetic_padding": padding}), encoding="utf-8")
            self.assertLess(path.stat().st_size, 16 * 1024**2)
            raw_total += path.stat().st_size
        self.assertGreater(raw_total, 64 * 1024**2)
        self.assert_capacity_blocked(self.check())

    def test_physical_oversize_original_is_capacity_blocked(self):
        path = self.write_p0()
        with path.open("ab") as stream:
            stream.write(b" " * (16 * 1024**2))
        result = self.check()
        self.assertIn("P0_READ_INVALID", self.codes(result))
        self.assert_capacity_blocked(result)

    def test_exact_json_byte_boundary_and_bound_manifest_are_admitted(self):
        path = self.write_report(bind_manifest=True)
        raw = path.read_bytes()
        raw += b" " * (16 * 1024**2 - len(raw))
        path.write_bytes(raw)
        manifest = path.parent / "runs" / ("f" * 64) / "run_manifest.json"
        manifest.write_bytes(raw)
        result = self.check()
        self.assertNotIn("PDCA_REPORT_INVALID", self.codes(result))
        self.assertNotIn("PDCA_MANIFEST_NOT_BOUND", self.codes(result))
        self.assertNotIn("PDCA_SCIENTIFIC_GATES_OPEN", self.codes(result))
        self.assertFalse(result["official_e2e_complete"])

    def test_unrelated_directory_entries_count_towards_scan_limit(self):
        directory = self.root / f"predictions/original/{NIGHT}"
        directory.mkdir(parents=True)
        for index in range(256):
            (directory / f"unrelated-{index}").touch()
        self.assertNotIn("P0_READ_INVALID", self.codes(self.check()))
        (directory / "one-more").touch()
        self.assert_capacity_blocked(self.check())

    def test_p_directory_boundary_is_counted_before_materialization(self):
        directory = self.root / f"predictions/original/{NIGHT}"
        for index in range(64):
            (directory / f"P{index}").mkdir(parents=True)
        self.assertNotIn("P0_READ_INVALID", self.codes(self.check()))
        (directory / "P64").mkdir()
        self.assert_capacity_blocked(self.check())

    def test_physical_deep_report_is_structured_capacity_blocker(self):
        path = self.write_report()
        path.write_bytes(b'{"operational_night":"2026-11-02","deep":' +
                         b"[" * 32 + b"0" + b"]" * 32 + b"}")
        self.assert_capacity_blocked(self.check())

    def test_json_depth_boundary_and_escaped_structural_text(self):
        raw = b"[" * 32 + b"0" + b"]" * 32
        gate._json(raw, gate._Budget())
        with self.assertRaisesRegex(ValueError, "CAPACITY_BLOCKED.*depth"):
            gate._json(b"[" + raw + b"]", gate._Budget())
        value = {"synthetic_text": '\\"' + "[{]}" * 100 + "\\end"}
        self.assertEqual(gate._json(json.dumps(value).encode(), gate._Budget()), value)

    def test_json_node_limit_counts_overwritten_duplicate_tokens(self):
        raw = b"{" + b'"same":0,' * 100_000 + b'"last":0}'
        with self.assertRaisesRegex(ValueError, "CAPACITY_BLOCKED.*node"):
            gate._json(raw, gate._Budget())

    def test_json_nodes_share_one_cumulative_ledger(self):
        raw = b"[" + b"0," * 129_999 + b"0]"
        budget = gate._Budget()
        for _ in range(3):
            self.assertEqual(len(gate._json(raw, budget)), 130_000)
        with self.assertRaisesRegex(ValueError, "CAPACITY_BLOCKED.*node"):
            gate._json(raw, budget)
        self.assertEqual(budget.nodes, 500_001)

    def test_capture_and_rejection_bytes_and_reopens_are_charged(self):
        path = self.root / "synthetic.bin"
        path.write_bytes(b"abc")
        budget = gate._Budget()
        with self.assertRaisesRegex(ValueError, "CAPACITY_BLOCKED"):
            budget.read(self.root, "synthetic.bin", 2)
        self.assertEqual((budget.bytes, budget.reads), (3, 1))
        budget = gate._Budget()
        for _ in range(128):
            self.assertEqual(budget.read(self.root, "synthetic.bin"), b"abc")
        with self.assertRaisesRegex(ValueError, "CAPACITY_BLOCKED.*count"):
            budget.read(self.root, "synthetic.bin")
        self.assertEqual(budget.bytes, 384)
        budget = gate._Budget()
        budget.bytes = 64 * 1024**2 - 2
        with self.assertRaisesRegex(ValueError, "CAPACITY_BLOCKED"):
            budget.read(self.root, "synthetic.bin")
        self.assertEqual(budget.bytes, 64 * 1024**2 + 1)

    def test_expired_private_budget_rejects_before_read_parse_or_hash(self):
        budget = gate._Budget()
        budget.deadline = 0
        with self.assertRaisesRegex(ValueError, "RUNTIME_BLOCKED"):
            budget.read(self.root, "absent.json")
        with self.assertRaisesRegex(ValueError, "RUNTIME_BLOCKED"):
            gate._json(b"{}", budget)
        with self.assertRaisesRegex(ValueError, "RUNTIME_BLOCKED"):
            gate._verify_captured_p0({}, self.root, NIGHT, budget)
        self.assertEqual((budget.bytes, budget.reads), (0, 0))

    def test_malformed_stage_shapes_do_not_escape_blockers(self):
        valid = [{"name": n, "status": "PASS"} for n in gate.STAGE_NAMES]
        for stages in ("not-a-list", [None], valid + [True], valid + ["bad"]):
            with self.subTest(stages_type=type(stages).__name__):
                self.write_report(stages=stages)
                self.assertIn("PDCA_REPORT_INVALID", self.codes(self.check()))

    def test_missing_duplicate_and_failed_stage_diagnostics_stay_distinct(self):
        valid = [{"name": n, "status": "PASS"} for n in gate.STAGE_NAMES]
        for stages in (valid[:-1], valid[:-1] + [valid[0]]):
            self.write_report(stages=stages)
            self.assertIn("PDCA_STAGES_INCOMPLETE", self.codes(self.check()))
        valid[0]["status"] = "PARTIAL"
        self.write_report(stages=valid)
        self.assertIn("PDCA_SCIENTIFIC_GATES_OPEN", self.codes(self.check()))

    def test_admitted_verifier_disk_semantics_equal_existing_native_verifier(self):
        cases = ("valid", "missing-sidecar", "oversize-sidecar", "bad-sidecar",
                 "pretty-record", "crlf-sidecar", "missing-hash", "bad-hash",
                 "wrong-class", "wrong-night", "wrong-version", "nan")
        previous_root = self.root
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as folder:
                self.root = Path(folder)
                path = self.write_p0()
                sidecar = path.with_name("sha256.txt")
                payload = json.loads(path.read_text(encoding="utf-8"))
                if case == "missing-sidecar":
                    sidecar.unlink()
                elif case == "oversize-sidecar":
                    sidecar.write_bytes(b"x" * 131)
                elif case == "bad-sidecar":
                    sidecar.write_bytes(b"bad\n")
                elif case == "crlf-sidecar":
                    sidecar.write_bytes(sidecar.read_bytes().replace(b"\n", b"\r\n"))
                elif case == "pretty-record":
                    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                elif case in ("missing-hash", "bad-hash"):
                    if case == "missing-hash":
                        payload.pop("payload_sha256")
                    else:
                        payload["payload_sha256"] = "0" * 64
                    path.write_bytes(canonical_bytes(payload) + b"\n")
                elif case.startswith("wrong-") or case == "nan":
                    if case == "wrong-class":
                        payload["prediction_class"] = "REPLAY"
                    elif case == "wrong-night":
                        payload["operational_night"] = "2026-11-03"
                    elif case == "wrong-version":
                        payload["prediction_version"] = "P1"
                    else:
                        payload["synthetic_number"] = float("nan")
                    payload["payload_sha256"] = pdca_pipeline.canonical_prediction_hash(payload)
                    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode() + b"\n"
                    path.write_bytes(raw)
                    sidecar.write_bytes((payload["payload_sha256"] + "  prediction.json\n").encode())
                # The unchanged facade is exercised only on these small synthetic files.
                old = pdca_pipeline.load_predictions(self.root, NIGHT)
                expected = pdca_pipeline.verify_predictions(old, root=self.root, night=NIGHT)
                budget = gate._Budget()
                captured = gate._load_originals(self.root, NIGHT, budget)
                actual = gate._verify_captured_p0(captured[0], self.root, NIGHT, budget)
                self.assertEqual(actual, expected)
        self.root = previous_root

    def test_bounded_record_reopen_detects_changed_bytes(self):
        path = self.write_p0()
        budget = gate._Budget()
        captured = gate._load_originals(self.root, NIGHT, budget)
        path.write_text(json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2),
                        encoding="utf-8")
        status, rows = gate._verify_captured_p0(captured[0], self.root, NIGHT, budget)
        self.assertEqual(status, "FAIL")
        self.assertEqual(rows[0]["sidecar_status"], "NONCANONICAL_BYTES")
        self.assertEqual(budget.reads, 3)  # Initial capture, sidecar and actual reopen.

    def test_report_manifest_comparison_preserves_exact_bytes_without_writes(self):
        path = self.write_report(bind_manifest=True)
        before = {p.relative_to(self.root): p.read_bytes()
                  for p in self.root.rglob("*") if p.is_file()}
        self.assertNotIn("PDCA_MANIFEST_NOT_BOUND", self.codes(self.check()))
        after = {p.relative_to(self.root): p.read_bytes()
                 for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(after, before)
        manifest = path.parent / "runs" / ("f" * 64) / "run_manifest.json"
        manifest.write_bytes(manifest.read_bytes() + b"\n")
        self.assertIn("PDCA_MANIFEST_NOT_BOUND", self.codes(self.check()))

    def test_recovered_scope_and_spoofed_path_do_not_redirect_reads(self):
        path = self.write_p0()
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["_path"] = "../../external/prediction.json"
        path.write_bytes(canonical_bytes(payload) + b"\n")
        budget = gate._Budget()
        captured = gate._load_originals(self.root, NIGHT, budget)
        self.assertEqual(Path(captured[0]["_path"]).as_posix(),
                         f"predictions/original/{NIGHT}/P0/prediction.json")
        _, rows = gate._verify_captured_p0(captured[0], self.root, NIGHT, budget)
        self.assertEqual(rows[0]["sidecar_status"], "NONCANONICAL_BYTES")

    def write_p0(self, *, created="2026-11-02T18:00:00+09:00",
                 frozen="2026-11-02T18:01:00+09:00", corrupt=False):
        payload = {
            "prediction_class": "ORIGINAL",
            "operational_night": NIGHT,
            "prediction_version": "P0",
            "created_at": created,
            "cutoff_time": "2026-11-02T17:59:00+09:00",
            "frozen_at": frozen,
            "targets_100m_10min": [{
                "target_id": "mock-only",
                "latitude": 28.15,
                "longitude": 129.3,
                "predicted_time_jst": "2026-11-02T20:00:00+09:00",
            }],
        }
        payload["payload_sha256"] = pdca_pipeline.canonical_prediction_hash(payload)
        path = self.root / f"predictions/original/{NIGHT}/P0/prediction.json"
        path.parent.mkdir(parents=True)
        path.write_bytes(canonical_bytes(payload) + b"\n")
        sidecar = path.with_name("sha256.txt")
        sidecar.write_bytes(((("0" * 64) if corrupt else payload["payload_sha256"])
                             + "  prediction.json\n").encode("ascii"))
        return path

    def test_missing_original_remains_blocked_without_writes(self):
        before = sorted(self.root.rglob("*"))
        result = self.check()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("P0_MISSING_OR_DUPLICATE", self.codes(result))
        self.assertIn("PDCA_REPORT_MISSING", self.codes(result))
        self.assertEqual(sorted(self.root.rglob("*")), before)

    @unittest.skipIf(WINDOWS_WITHOUT_FCNTL, "Canonical POSIX preflight requires fcntl; missing capability tested separately")
    def test_before_reuses_existing_strict_preflight(self):
        result = self.check("before")
        self.assertFalse(result["official_e2e_complete"])
        self.assertTrue(result["read_only"])
        self.assertIn("PRODUCTION_ISSUANCE_AUTHORITY_BLOCKED", self.codes(result))
        self.assertFalse((self.root / "predictions").exists())

    @unittest.skipUnless(WINDOWS_WITHOUT_FCNTL, "Actual Windows missing-fcntl capability regression")
    def test_before_missing_fcntl_is_structured_without_fabricated_preflight(self):
        try:
            result = self.check("before")
        except ModuleNotFoundError as exc:
            self.fail(f"Known unsupported capability escaped the observer: {exc.name}")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(result["read_only"])
        self.assertFalse(result["official_e2e_complete"])
        self.assertIn("P0_PREFLIGHT_RUNTIME_BLOCKED", self.codes(result))
        self.assertNotIn("PRODUCTION_ISSUANCE_AUTHORITY_BLOCKED", self.codes(result))
        self.assertNotIn("existing_preflight_status", result["evidence"])
        self.assertFalse((self.root / "predictions").exists())

    def test_valid_synthetic_freeze_is_not_production_authority(self):
        original = self.write_p0()
        before = original.read_bytes()
        result = self.check()
        self.assertEqual(result["evidence"]["p0_freeze_integrity"], "PASS")
        self.assertEqual(result["evidence"]["p0_sidecar"], "MATCH")
        self.assertIn("TRUSTED_REAL_E2E_UNATTESTED", self.codes(result))
        self.assertNotIn("P0_NOT_PROSPECTIVE", self.codes(result))
        self.assertFalse(result["official_e2e_complete"])
        self.assertEqual(original.read_bytes(), before)

    def test_late_freeze_is_rejected(self):
        self.write_p0(frozen="2026-11-02T19:00:00+09:00")
        self.assertIn("P0_NOT_PROSPECTIVE", self.codes(self.check()))

    def test_bad_sidecar_never_counts_as_p0(self):
        self.write_p0(corrupt=True)
        result = self.check()
        self.assertIn("P0_FREEZE_INVALID", self.codes(result))
        self.assertEqual(result["evidence"]["p0_sidecar"], "MISMATCH")

    def test_malformed_original_json_container_blocks_without_crashing(self):
        path = self.root / f"predictions/original/{NIGHT}/P0/prediction.json"
        path.parent.mkdir(parents=True)
        path.write_text('["not-an-original-record"]', encoding="utf-8")
        result = self.check()
        self.assertIn("P0_READ_INVALID", self.codes(result))
        self.assertFalse(result["official_e2e_complete"])

    def test_malformed_original_payload_digest_blocks_without_crashing(self):
        path = self.write_p0()
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["targets_100m_10min"] = {"not": "an array"}
        path.write_text(json.dumps(payload), encoding="utf-8")
        result = self.check()
        self.assertIn("P0_FREEZE_INVALID", self.codes(result))

    def test_recovered_prediction_does_not_replace_original(self):
        path = self.root / f"predictions/recovered_original/{NIGHT}/P0/prediction.json"
        path.parent.mkdir(parents=True)
        path.write_text('{"prediction_version":"P0"}', encoding="utf-8")
        self.assertIn("P0_MISSING_OR_DUPLICATE", self.codes(self.check()))

    def test_fake_all_pass_pdca_report_does_not_certify_real_e2e(self):
        self.write_p0()
        path = self.root / f"reports/pdca/{NIGHT}/pdca_result.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({
            "operational_night": NIGHT, "overall_status": "PASS",
            "completed": True,
            "run_id": "f" * 64,
            "stages": [{"name": n, "status": "PASS"} for n in gate.STAGE_NAMES],
            "operational_result": {"p0_score": {"strict_official_score_eligible": True}},
        }), encoding="utf-8")
        result = self.check()
        self.assertIn("PDCA_MANIFEST_NOT_BOUND", self.codes(result))
        self.assertIn("TRUSTED_REAL_E2E_UNATTESTED", self.codes(result))
        self.assertFalse(result["official_e2e_complete"])

    def test_0700_boundary_and_wrong_night(self):
        at = datetime(2026, 11, 3, 6, 59, tzinfo=JST)
        self.assertEqual(gate.night_for(at), NIGHT)
        self.assertEqual(gate.night_for(datetime(2026, 11, 3, 7, 0, tzinfo=JST)),
                         "2026-11-03")
        self.assertIn("START_NIGHT_MISMATCH", self.codes(self.check(start=datetime(
            2026, 11, 3, 7, 0, tzinfo=JST))))

    def test_naive_time_and_invalid_phase_rejected(self):
        with self.assertRaises(ValueError):
            gate.aware("2026-11-02T18:00:00")
        with self.assertRaises(ValueError):
            self.check(start=datetime(2026, 11, 2, 19, 0))
        with self.assertRaises(ValueError):
            self.check(phase="issue")

    def test_symlink_to_external_original_never_accepted(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "original"
            target.mkdir()
            p = self.root / "predictions"
            p.mkdir()
            try:
                (p / "original").symlink_to(target, target_is_directory=True)
            except OSError as exc:
                if getattr(exc, "winerror", None) == 1314:
                    self.skipTest("Windows symlink privilege unavailable (WinError 1314)")
                raise
            result = self.check()
            self.assertIn("P0_READ_INVALID", self.codes(result))


if __name__ == "__main__":
    unittest.main()
