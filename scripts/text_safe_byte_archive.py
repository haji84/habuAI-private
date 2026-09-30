#!/usr/bin/env python3
"""Binary-safe, text-only attachment archive for Habu AI.

Some transports can write UTF-8 text to GitHub but cannot send arbitrary binary
files. This module provides a lossless fallback:

raw bytes -> XZ -> base64 -> deterministic text parts

Restoration verifies both the compressed payload and the original raw bytes by
SHA-256 before writing the output.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import lzma
from pathlib import Path


DEFAULT_PART_CHARS = 200_000


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def pack_file(
    source: Path,
    archive_dir: Path,
    *,
    kind: str,
    source_name: str,
    source_ref: str | None = None,
    part_chars: int = DEFAULT_PART_CHARS,
) -> dict[str, object]:
    if part_chars <= 0 or part_chars % 4:
        raise ValueError("part_chars must be a positive multiple of 4")
    if not source.is_file():
        raise FileNotFoundError(source)

    raw = source.read_bytes()
    compressed = lzma.compress(raw, format=lzma.FORMAT_XZ, preset=9 | lzma.PRESET_EXTREME)
    encoded = base64.b64encode(compressed).decode("ascii")

    archive_dir.mkdir(parents=True, exist_ok=True)
    existing = list(archive_dir.iterdir())
    if existing:
        raise FileExistsError(f"archive directory is not empty: {archive_dir}")

    parts = [encoded[i : i + part_chars] for i in range(0, len(encoded), part_chars)]
    for index, part in enumerate(parts):
        (archive_dir / f"part_{index:03d}.b64").write_text(part, encoding="ascii")

    manifest = {
        "schema_version": "habu-text-safe-byte-archive-v1",
        "original_filename": source.name,
        "kind": kind,
        "source": source_name,
        "source_ref": source_ref,
        "raw_size_bytes": len(raw),
        "raw_sha256": sha256_bytes(raw),
        "compression": "xz",
        "compressed_size_bytes": len(compressed),
        "compressed_sha256": sha256_bytes(compressed),
        "transfer_encoding": "base64",
        "encoded_chars": len(encoded),
        "part_chars": part_chars,
        "part_count": len(parts),
        "part_glob": "part_*.b64",
    }
    _write_manifest(archive_dir / "manifest.json", manifest)
    return manifest


def restore_file(archive_dir: Path, output: Path) -> dict[str, object]:
    manifest_path = archive_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    parts = sorted(archive_dir.glob("part_*.b64"))
    expected_parts = int(manifest["part_count"])
    if len(parts) != expected_parts:
        raise ValueError(
            f"part count mismatch: expected {expected_parts}, got {len(parts)}"
        )

    encoded = "".join(path.read_text(encoding="ascii") for path in parts)
    if len(encoded) != int(manifest["encoded_chars"]):
        raise ValueError("encoded length mismatch")

    try:
        compressed = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError("invalid base64 archive payload") from exc

    if len(compressed) != int(manifest["compressed_size_bytes"]):
        raise ValueError("compressed size mismatch")
    compressed_sha = sha256_bytes(compressed)
    if compressed_sha != manifest["compressed_sha256"]:
        raise ValueError(
            f"compressed SHA-256 mismatch: expected {manifest['compressed_sha256']}, "
            f"got {compressed_sha}"
        )

    if manifest["compression"] != "xz":
        raise ValueError(f"unsupported compression: {manifest['compression']}")
    try:
        raw = lzma.decompress(compressed, format=lzma.FORMAT_XZ)
    except lzma.LZMAError as exc:
        raise ValueError("invalid XZ payload") from exc

    if len(raw) != int(manifest["raw_size_bytes"]):
        raise ValueError("raw size mismatch")
    raw_sha = sha256_bytes(raw)
    if raw_sha != manifest["raw_sha256"]:
        raise ValueError(
            f"raw SHA-256 mismatch: expected {manifest['raw_sha256']}, got {raw_sha}"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    return {
        "byte_exact": True,
        "original_filename": manifest["original_filename"],
        "kind": manifest["kind"],
        "raw_size_bytes": len(raw),
        "raw_sha256": raw_sha,
        "compressed_sha256": compressed_sha,
        "part_count": len(parts),
        "output": str(output),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    pack = sub.add_parser("pack")
    pack.add_argument("--file", required=True, type=Path)
    pack.add_argument("--archive-dir", required=True, type=Path)
    pack.add_argument("--kind", required=True)
    pack.add_argument("--source", required=True)
    pack.add_argument("--source-ref")
    pack.add_argument("--part-chars", type=int, default=DEFAULT_PART_CHARS)

    restore = sub.add_parser("restore")
    restore.add_argument("--archive-dir", required=True, type=Path)
    restore.add_argument("--output", required=True, type=Path)

    args = parser.parse_args()
    if args.command == "pack":
        result = pack_file(
            args.file,
            args.archive_dir,
            kind=args.kind,
            source_name=args.source,
            source_ref=args.source_ref,
            part_chars=args.part_chars,
        )
    else:
        result = restore_file(args.archive_dir, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
