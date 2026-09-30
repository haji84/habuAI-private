import csv
import hashlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.migrate_legacy_public_gpx import (
    git_blob_sha1,
    migrate_bundle_bytes,
    sha256_bytes,
)


def make_bundle(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def write_expected(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["operational_night", "filename", "sha256"],
        )
        writer.writeheader()
        writer.writerows(rows)


class LegacyPublicGpxMigrationTests(unittest.TestCase):
    def test_verify_only_matches_by_sha_not_filename(self):
        raw = b"<?xml version='1.0'?><gpx><trk><name>x</name></trk></gpx>"
        digest = sha256_bytes(raw)
        bundle = make_bundle({"odd/location/not-the-manifest-name.gpx": raw})

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = root / "expected.csv"
            write_expected(
                expected,
                [
                    {
                        "operational_night": "2026-08-12",
                        "filename": "legacy-name.gpx",
                        "sha256": digest,
                    }
                ],
            )

            result = migrate_bundle_bytes(
                bundle,
                repo_root=root / "repo",
                expected_csv=expected,
                source_url="https://example.invalid/bundle.zip",
                source_repo="owner/repo",
                source_commit="abc",
                expected_source_blob_sha=git_blob_sha1(bundle),
                expected_source_size=len(bundle),
                verify_only=True,
            )

            self.assertTrue(result["all_expected_sha256_matched"])
            self.assertEqual(result["verified_actual_gpx_nights"], 1)
            self.assertEqual(
                result["files"][0]["legacy_member_path"],
                "odd/location/not-the-manifest-name.gpx",
            )

    def test_migration_stages_and_promotes_exact_bytes(self):
        raw = b"\xef\xbb\xbf<gpx>\r\nmeasured\x00payload\r\n</gpx>\r\n"
        digest = sha256_bytes(raw)
        bundle = make_bundle({"nested/8:15探索.gpx": raw})

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            expected = root / "expected.csv"
            write_expected(
                expected,
                [
                    {
                        "operational_night": "2026-08-15",
                        "filename": "8:15探索.gpx",
                        "sha256": digest,
                    }
                ],
            )

            result = migrate_bundle_bytes(
                bundle,
                repo_root=repo,
                expected_csv=expected,
                source_url="https://example.invalid/bundle.zip",
                source_repo="owner/repo",
                source_commit="abc",
                expected_source_blob_sha=git_blob_sha1(bundle),
                expected_source_size=len(bundle),
                verify_only=False,
            )

            record = result["files"][0]
            incoming = repo / record["incoming_path"]
            raw_path = repo / record["raw_path"]
            self.assertEqual(incoming.read_bytes(), raw)
            self.assertEqual(raw_path.read_bytes(), raw)
            self.assertEqual(hashlib.sha256(raw_path.read_bytes()).hexdigest(), digest)
            self.assertEqual(raw_path.name, "2026-08-15__legacy.gpx")
            self.assertTrue(record["byte_preserved"])

    def test_wrong_source_blob_is_rejected(self):
        raw = b"<gpx/>"
        digest = sha256_bytes(raw)
        bundle = make_bundle({"night.gpx": raw})

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = root / "expected.csv"
            write_expected(
                expected,
                [
                    {
                        "operational_night": "2026-08-12",
                        "filename": "night.gpx",
                        "sha256": digest,
                    }
                ],
            )
            with self.assertRaises(ValueError):
                migrate_bundle_bytes(
                    bundle,
                    repo_root=root / "repo",
                    expected_csv=expected,
                    source_url="https://example.invalid/bundle.zip",
                    source_repo="owner/repo",
                    source_commit="abc",
                    expected_source_blob_sha="0" * 40,
                    expected_source_size=len(bundle),
                    verify_only=True,
                )

    def test_missing_expected_gpx_is_rejected(self):
        raw = b"<gpx/>"
        bundle = make_bundle({"night.gpx": raw})

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = root / "expected.csv"
            write_expected(
                expected,
                [
                    {
                        "operational_night": "2026-08-12",
                        "filename": "other.gpx",
                        "sha256": "f" * 64,
                    }
                ],
            )
            with self.assertRaises(ValueError):
                migrate_bundle_bytes(
                    bundle,
                    repo_root=root / "repo",
                    expected_csv=expected,
                    source_url="https://example.invalid/bundle.zip",
                    source_repo="owner/repo",
                    source_commit="abc",
                    expected_source_blob_sha=git_blob_sha1(bundle),
                    expected_source_size=len(bundle),
                    verify_only=True,
                )


if __name__ == "__main__":
    unittest.main()
