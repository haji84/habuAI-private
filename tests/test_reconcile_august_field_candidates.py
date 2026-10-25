"""August recovered candidate source links must remain not eligible for training."""
import copy
from contextlib import contextmanager, redirect_stdout
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import reconcile_august_field_candidates as audit


class DiagnosticOutputBoundary(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="august-output-boundary-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name).resolve()
        self.root = self.work / "dataset"
        self.root.mkdir()
        self.report = {"status": "SYNTHETIC_DIAGNOSTIC_ONLY",
                       "candidate_event_mentions_total": 0,
                       "gpx_proximity_matched_capture_mentions": 0,
                       "gpx_proximity_matched_reaction_controls": 0}

    def call(self, destination):
        with patch.object(sys, "argv", ["review", "--root", str(self.root),
                                       "--output", str(destination)]), \
                patch.object(audit, "reconcile", return_value=self.report), \
                redirect_stdout(io.StringIO()):
            return audit.main()

    def sentinel(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"immutable synthetic source sentinel")
        return path

    def rejected(self, path):
        error = None
        try:
            self.call(path)
        except ValueError as exc:
            error = exc
        self.assertEqual(path.read_bytes(), b"immutable synthetic source sentinel")
        self.assertIsNotNone(error, "unsafe output must fail closed")

    def test_cli_cannot_overwrite_dataset_raw_or_original(self):
        for relative in ("data/raw/source.txt", "predictions/original/night/P0.json",
                         "predictions/recovered_original/night/P0.json"):
            with self.subTest(relative=relative):
                self.rejected(self.sentinel(self.root / relative))

    def test_cli_cannot_overwrite_repository_source_with_separate_dataset(self):
        canonical = self.work / "repository"
        with patch.object(audit, "ROOT", canonical):
            self.rejected(self.sentinel(canonical / "data/raw/source.txt"))

    def test_cli_rejects_sources_even_if_dataset_is_nested_in_raw(self):
        canonical = self.work / "repository"
        self.root = canonical / "data/raw/nested-dataset"
        with patch.object(audit, "ROOT", canonical):
            self.rejected(self.sentinel(self.root / "reports/looks-derived.json"))

    def test_cli_rejects_unrelated_and_traversal_destinations(self):
        self.rejected(self.sentinel(self.work / "outside.json"))
        path = self.sentinel(self.root / "data/raw/source.txt")
        (self.root / "reports").mkdir()
        self.rejected(self.root / "reports/../data/raw/source.txt")
        self.assertTrue(path.is_file())

    def test_reports_and_artifacts_preserve_diagnostic_json(self):
        for folder in ("reports", "artifacts"):
            path = self.sentinel(self.root / folder / "nested/review.json")
            self.assertEqual(self.call(path), 0)
            self.assertEqual(json.loads(path.read_bytes()), self.report)
            self.assertEqual(list(path.parent.glob(".august-review-*")), [])

    def test_relative_ci_artifact_destination_is_preserved(self):
        previous = Path.cwd()
        try:
            os.chdir(self.root)
            output = Path("artifacts/reconciliation/review.json")
            self.assertEqual(self.call(output), 0)
            self.assertEqual(json.loads(output.read_bytes()), self.report)
        finally:
            os.chdir(previous)

    def test_failed_atomic_publish_preserves_existing_derived_file(self):
        path = self.sentinel(self.root / "reports/review.json")
        with patch("os.replace", side_effect=OSError("synthetic publish failure")):
            with self.assertRaises(OSError):
                self.call(path)
        self.assertEqual(path.read_bytes(), b"immutable synthetic source sentinel")
        self.assertEqual(list(path.parent.glob(".august-review-*")), [])

    def test_atomic_output_does_not_mutate_raw_hardlink(self):
        raw = self.sentinel(self.root / "data/raw/source.txt")
        output = self.root / "artifacts/review.json"
        output.parent.mkdir()
        os.link(raw, output)
        self.assertEqual(raw.stat().st_ino, output.stat().st_ino)
        self.assertEqual(self.call(output), 0)
        self.assertEqual(raw.read_bytes(), b"immutable synthetic source sentinel")
        self.assertEqual(json.loads(output.read_bytes()), self.report)
        self.assertNotEqual(raw.stat().st_ino, output.stat().st_ino)

    @unittest.skipIf(os.name == "nt", "POSIX symlink fixture; Windows junction below")
    def test_symlink_destination_and_ancestor_are_rejected(self):
        external = self.sentinel(self.work / "external/source.txt")
        reports = self.root / "reports"
        reports.mkdir()
        (reports / "file.json").symlink_to(external)
        (reports / "linked").symlink_to(external.parent, target_is_directory=True)
        for path in (reports / "file.json", reports / "linked/source.txt"):
            self.rejected(path)

    @contextmanager
    def junction(self, link, target):
        link.parent.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, AUGUST_TEST_LINK=str(link), AUGUST_TEST_TARGET=str(target))
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                        "New-Item -ItemType Junction -Path $env:AUGUST_TEST_LINK "
                        "-Target $env:AUGUST_TEST_TARGET -ErrorAction Stop | Out-Null"],
                       env=env, check=True, capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            self.assertTrue(link.is_junction())
            self.assertFalse(link.is_symlink())
            yield
        finally:
            self.assertTrue(link.absolute().is_relative_to(self.work))
            self.assertTrue(link.resolve().is_relative_to(self.work))
            os.rmdir(link)  # Remove only the link before recursive temp cleanup.

    @unittest.skipUnless(os.name == "nt", "native Windows junction fixture")
    def test_native_junction_destination_and_root_ancestor_are_rejected(self):
        external = self.sentinel(self.work / "external/source.txt")
        with self.junction(self.root / "reports/linked", external.parent):
            self.rejected(self.root / "reports/linked/source.txt")
        external_reports = self.sentinel(self.work / "external/reports/source.txt")
        with self.junction(self.work / "dataset-alias", external.parent):
            self.root = self.work / "dataset-alias"
            self.rejected(self.root / "reports/source.txt")
        self.assertEqual(external_reports.read_bytes(), b"immutable synthetic source sentinel")


class AugustCandidateActualGPS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # All four 4-6MB GPX sources are read once per test class.
        cls.real_report = audit.reconcile(ROOT)

    def test_eleven_capture_statements_match_real_gpx_but_stay_unverified(self):
        r = self.real_report
        self.assertEqual(r["candidate_event_mentions_total"], 11)
        self.assertEqual(r["gpx_proximity_matched_capture_mentions"], 11)
        self.assertEqual(set(r["gpx_nights"]), {
            "2026-08-12", "2026-08-13", "2026-08-15", "2026-08-17"})
        self.assertEqual(
            [len(r["gpx_nights"][night]["capture_candidate_statements"])
             for night in sorted(r["gpx_nights"])], [4, 2, 3, 2])
        self.assertEqual(r["formally_eligible_training_rows"], 0)
        self.assertEqual(r["exact_owner_capture_positive_individuals"], 0)
        self.assertEqual(r["observed_negative_units"], 0)
        self.assertFalse(r["independent_original_binary_verification"])
        self.assertTrue(r["unknown_passage_not_negative"])

    def test_workbook_role_conflict_and_null_quantities_not_hidden(self):
        for night in self.real_report["gpx_nights"].values():
            for row in night["capture_candidate_statements"]:
                self.assertIsNone(row["explicit_exact_individual_count"])
                self.assertEqual(row["minimum_possible_individuals"], 1)
                self.assertFalse(row["owner_capture_verified"])
                self.assertTrue(row["workbook_role_conflict"])
                self.assertFalse(row["training_positive_eligible"])
                self.assertLessEqual(row["absolute_time_delta_s"], audit.MAX_MATCH_SECONDS)
                self.assertLessEqual(row["spatial_distance_m"], audit.MAX_MATCH_DISTANCE_M)

    def test_roadkill_and_himehabu_remain_non_capture(self):
        r=self.real_report
        self.assertEqual(sum(len(n["reaction_controls"]) for n in r["gpx_nights"].values()),4)
        kinds=[x["category"] for n in r["gpx_nights"].values() for x in n["reaction_controls"]]
        self.assertEqual(kinds.count("HABU_ROADKILL_NONCAPTURE"),2)
        self.assertEqual(kinds.count("OTHER_SPECIES_SIGHTING_NONCAPTURE"),2)
        self.assertTrue(all(not x["training_positive_eligible"]
            for n in r["gpx_nights"].values() for x in n["reaction_controls"]))

    def test_missing_search_markers_do_not_prove_exposure(self):
        r=self.real_report["gpx_nights"]
        self.assertEqual(len(r["2026-08-13"]["search_markers"]), 0)
        for night in r.values():
            self.assertFalse(night["complete_search_exposure_verified"])
            self.assertFalse(night["exhaustive_owner_capture_ledger_verified"])
            self.assertEqual(night["eligible_negative_units"],0)

    def test_mutated_recovered_source_blocks_training(self):
        # Test a patched content-digest, not a fabricated original source.
        original=audit.digest_file
        def corrupted(path):
            if path.name=="august-extracted.txt": return "0"*64
            return original(path)
        with patch.object(audit,"digest_file",side_effect=corrupted):
            with self.assertRaises(audit.IntakeError):
                audit._read_review(ROOT)

    def test_source_role_or_quantity_cannot_be_promoted_by_review_changes(self):
        original=audit._read_review
        def forged(root):
            payload, source, sha = original(root)
            payload = copy.deepcopy(payload)
            payload["capture_candidates"][0]["exact_individual_count"] = 1
            return payload,source,sha
        with patch.object(audit,"_read_review",side_effect=forged):
            with self.assertRaises(audit.IntakeError):
                audit.reconcile(ROOT)

    def test_recovered_source_is_not_original_txt(self):
        self.assertEqual(
            self.real_report["representation"],
            "derived_recovered_read_content_not_original_txt_bytes")
        self.assertTrue(all(
            n["source_status"]=="RECOVERED_LOG_MATCHED_NOT_CANONICAL"
            for n in self.real_report["gpx_nights"].values()
        ))


if __name__ == "__main__":
    unittest.main()
