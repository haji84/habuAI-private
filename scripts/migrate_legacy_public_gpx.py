#!/usr/bin/env python3
"""Migrate legacy ACTUAL_GPX originals into the private canonical repository.

The legacy public repository contains a ZIP bundle rather than individually
committed GPX files. This migration:

1. downloads that exact Git blob over HTTPS;
2. verifies its Git blob SHA-1 and expected byte size;
3. finds GPX members by raw SHA-256, never by filename;
4. stages each verified original through the canonical attachment intake;
5. promotes the byte-identical GPX into data/raw/gpx/;
6. writes migration evidence.

No trajectory content is normalized or regenerated.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from scripts.ingest_attachment import ingest_attachment


DEFAULT_SOURCE_URL = (
    "https://raw.githubusercontent.com/haji84/habuAI/main/"
    "data/raw/habuAI_initial_raw_bundle.zip"
)
DEFAULT_SOURCE_REPO = "haji84/habuAI"
DEFAULT_SOURCE_COMMIT = "8fc8cdb81e9b8da566ba1e57ed1d52e7d0627475"
DEFAULT_SOURCE_BLOB_SHA = "01e612df1ed56e198116ec3e882786da34e4e232"
DEFAULT_SOURCE_SIZE = 4_897_166
DEFAULT_EXPECTED_CSV = (
    Path("evidence/legacy/habuAI-public/v2_actual_gpx_13night_qc.csv")
)
DEFAULT_RESULT = (
    Path("evidence/legacy/habuAI-public/legacy_13_gpx_migration_result.json")
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def load_expected_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"operational_night", "filename", "sha256"}
    if not rows:
        raise ValueError(f"empty expected GPX manifest: {path}")
    missing_columns = required - set(rows[0])
    if missing_columns:
        raise ValueError(
            f"expected manifest missing columns: {sorted(missing_columns)}"
        )

    result: dict[str, dict[str, str]] = {}
    for row in rows:
        digest = row["sha256"].strip().lower()
        if len(digest) != 64:
            raise ValueError(f"invalid SHA-256 in expected manifest: {digest}")
        if digest in result:
            raise ValueError(f"duplicate expected SHA-256: {digest}")
        result[digest] = row
    return result


def download_bytes(url: str) -> bytes:
    if not url.startswith("https://"):
        raise ValueError("legacy source URL must use HTTPS")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "habuAI-private-legacy-gpx-migration/1"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def inspect_bundle(
    bundle: bytes,
    expected: dict[str, dict[str, str]],
) -> dict[str, dict[str, object]]:
    matches: dict[str, dict[str, object]] = {}
    seen_matching_digest: set[str] = set()

    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise ValueError(f"ZIP CRC check failed: {bad_member}")

        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".gpx"):
                continue
            raw = archive.read(info)
            digest = sha256_bytes(raw)
            if digest not in expected:
                continue
            if digest in seen_matching_digest:
                raise ValueError(
                    f"expected GPX appears more than once in bundle: {digest}"
                )
            seen_matching_digest.add(digest)
            matches[digest] = {
                "member_path": info.filename,
                "member_size_bytes": len(raw),
                "bytes": raw,
            }

    missing = sorted(set(expected) - set(matches))
    if missing:
        missing_nights = [expected[d]["operational_night"] for d in missing]
        raise ValueError(
            "legacy bundle is missing expected ACTUAL_GPX originals: "
            + ", ".join(missing_nights)
        )
    return matches


def migrate_bundle_bytes(
    bundle: bytes,
    *,
    repo_root: Path,
    expected_csv: Path,
    source_url: str,
    source_repo: str,
    source_commit: str,
    expected_source_blob_sha: str,
    expected_source_size: int,
    verify_only: bool,
) -> dict[str, object]:
    if len(bundle) != expected_source_size:
        raise ValueError(
            f"legacy source bundle size mismatch: expected {expected_source_size}, "
            f"got {len(bundle)}"
        )
    blob_sha = git_blob_sha1(bundle)
    if blob_sha != expected_source_blob_sha:
        raise ValueError(
            f"legacy source Git blob SHA mismatch: expected "
            f"{expected_source_blob_sha}, got {blob_sha}"
        )

    expected = load_expected_rows(expected_csv)
    matches = inspect_bundle(bundle, expected)

    migrated: list[dict[str, object]] = []
    for digest, row in sorted(
        expected.items(), key=lambda item: item[1]["operational_night"]
    ):
        match = matches[digest]
        record: dict[str, object] = {
            "operational_night": row["operational_night"],
            "legacy_filename": row["filename"],
            "legacy_member_path": match["member_path"],
            "raw_size_bytes": match["member_size_bytes"],
            "raw_sha256": digest,
        }

        if not verify_only:
            safe_name = f"{row['operational_night']}__legacy.gpx"
            with tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / safe_name
                source.write_bytes(match["bytes"])  # type: ignore[arg-type]
                intake = ingest_attachment(
                    source,
                    repo_root=repo_root,
                    kind="gpx",
                    source="legacy-github",
                    source_ref=(
                        f"{source_repo}@{source_commit}:"
                        f"{match['member_path']}"
                    ),
                    expected_sha256=digest,
                    promote=True,
                )
            record["incoming_path"] = intake["incoming_path"]
            record["raw_path"] = intake["raw_path"]
            record["promote_status"] = intake["promote_status"]
            record["byte_preserved"] = intake["byte_preserved"]

        migrated.append(record)

    return {
        "schema_version": "habu-legacy-gpx-migration-v1",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "repository": source_repo,
            "commit": source_commit,
            "url": source_url,
            "bundle_size_bytes": len(bundle),
            "bundle_git_blob_sha1": blob_sha,
            "bundle_sha256": sha256_bytes(bundle),
        },
        "expected_actual_gpx_nights": len(expected),
        "verified_actual_gpx_nights": len(matches),
        "verify_only": verify_only,
        "all_expected_sha256_matched": set(matches) == set(expected),
        "files": migrated,
    }


def write_result(path: Path, result: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--source-repo", default=DEFAULT_SOURCE_REPO)
    parser.add_argument("--source-commit", default=DEFAULT_SOURCE_COMMIT)
    parser.add_argument(
        "--source-blob-sha", default=DEFAULT_SOURCE_BLOB_SHA
    )
    parser.add_argument("--source-size", type=int, default=DEFAULT_SOURCE_SIZE)
    parser.add_argument("--expected-csv", type=Path, default=DEFAULT_EXPECTED_CSV)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    expected_csv = (
        args.expected_csv
        if args.expected_csv.is_absolute()
        else repo_root / args.expected_csv
    )
    result_path = (
        args.result if args.result.is_absolute() else repo_root / args.result
    )

    bundle = download_bytes(args.source_url)
    result = migrate_bundle_bytes(
        bundle,
        repo_root=repo_root,
        expected_csv=expected_csv,
        source_url=args.source_url,
        source_repo=args.source_repo,
        source_commit=args.source_commit,
        expected_source_blob_sha=args.source_blob_sha,
        expected_source_size=args.source_size,
        verify_only=args.verify_only,
    )
    write_result(result_path, result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
