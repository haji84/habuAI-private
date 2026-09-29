#!/usr/bin/env python3
"""Byte-preserving attachment intake for Habu AI.

This adapter is intentionally transport-neutral. ChatGPT Work, GORIQ, a local
desktop bridge, or a human can first materialize/download an attachment to a
local path, then call this script. The script preserves the original bytes,
stages them under incoming/, records evidence, and can promote them to data/raw/.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from scripts.register_raw_file import ALLOWED_EXTENSIONS, audit_file, sha256_file

RAW_DIR_BY_KIND = {
    "gpx": "gpx",
    "habu_log": "habu_logs",
    "capture_db": "capture_db",
    "gis": "gis",
    "other": "other",
}


def _atomic_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        raise FileExistsError(dst)
    with tempfile.NamedTemporaryFile(
        dir=dst.parent, prefix=f".{dst.name}.", suffix=".part", delete=False
    ) as handle:
        tmp = Path(handle.name)
    try:
        shutil.copyfile(src, tmp)
        os.replace(tmp, dst)
    finally:
        if tmp.exists():
            tmp.unlink()


def _atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".part",
        delete=False,
    ) as handle:
        handle.write(text)
        tmp = Path(handle.name)
    try:
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _find_raw_duplicate(repo_root: Path, digest: str) -> Path | None:
    raw_root = repo_root / "data" / "raw"
    if not raw_root.exists():
        return None
    for path in raw_root.rglob("*"):
        if path.is_file() and sha256_file(path) == digest:
            return path
    return None


def ingest_attachment(
    source_file: Path,
    *,
    repo_root: Path,
    kind: str,
    source: str,
    source_ref: str | None = None,
    expected_sha256: str | None = None,
    promote: bool = False,
) -> dict[str, object]:
    source_file = source_file.resolve()
    repo_root = repo_root.resolve()

    if not source_file.is_file():
        raise FileNotFoundError(source_file)
    if kind not in RAW_DIR_BY_KIND:
        raise ValueError(f"unsupported kind: {kind}")

    # Validate extension and calculate the source digest without changing the file.
    audit = audit_file(source_file, kind)
    digest = str(audit["sha256"])
    if expected_sha256 and digest.lower() != expected_sha256.lower():
        raise ValueError(
            f"SHA-256 mismatch: expected {expected_sha256.lower()}, got {digest.lower()}"
        )

    incoming = repo_root / "incoming" / kind / f"{digest}__{source_file.name}"
    if incoming.exists():
        if sha256_file(incoming) != digest:
            raise RuntimeError(f"incoming path collision with different bytes: {incoming}")
        staged_status = "already_staged"
    else:
        _atomic_copy(source_file, incoming)
        if sha256_file(incoming) != digest:
            incoming.unlink(missing_ok=True)
            raise RuntimeError("byte-preservation check failed after staging")
        staged_status = "staged"

    raw_duplicate = _find_raw_duplicate(repo_root, digest)
    raw_path: Path | None = None
    promote_status = "not_requested"

    if promote:
        if raw_duplicate is not None:
            raw_path = raw_duplicate
            promote_status = "already_present_by_sha256"
        else:
            raw_dir = repo_root / "data" / "raw" / RAW_DIR_BY_KIND[kind]
            raw_path = raw_dir / source_file.name
            if raw_path.exists():
                existing_digest = sha256_file(raw_path)
                if existing_digest != digest:
                    raise FileExistsError(
                        f"raw filename collision: {raw_path} has SHA-256 {existing_digest}"
                    )
                promote_status = "already_present_same_path"
            else:
                _atomic_copy(incoming, raw_path)
                if sha256_file(raw_path) != digest:
                    raw_path.unlink(missing_ok=True)
                    raise RuntimeError("byte-preservation check failed after raw promotion")
                promote_status = "promoted"

    evidence = {
        "schema_version": "habu-attachment-intake-v1",
        "source": source,
        "source_ref": source_ref,
        "filename": source_file.name,
        "kind": kind,
        "bytes": source_file.stat().st_size,
        "sha256": digest,
        "received_at_utc": datetime.now(timezone.utc).isoformat(),
        "incoming_path": incoming.relative_to(repo_root).as_posix(),
        "staged_status": staged_status,
        "promote_requested": promote,
        "promote_status": promote_status,
        "raw_path": raw_path.relative_to(repo_root).as_posix() if raw_path else None,
        "raw_duplicate_path": (
            raw_duplicate.relative_to(repo_root).as_posix() if raw_duplicate else None
        ),
        "byte_preserved": True,
    }
    evidence_path = repo_root / "evidence" / "raw_intake" / f"{digest}.json"
    _atomic_json(evidence_path, evidence)
    evidence["evidence_path"] = evidence_path.relative_to(repo_root).as_posix()
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--kind", required=True, choices=sorted(RAW_DIR_BY_KIND))
    parser.add_argument("--source", required=True)
    parser.add_argument("--source-ref")
    parser.add_argument("--expected-sha256")
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()

    result = ingest_attachment(
        args.file,
        repo_root=args.repo_root,
        kind=args.kind,
        source=args.source,
        source_ref=args.source_ref,
        expected_sha256=args.expected_sha256,
        promote=args.promote,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
