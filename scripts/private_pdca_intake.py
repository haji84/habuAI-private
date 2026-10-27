"""Private, immutable source intake for existing Habu AI PDCA coordinator.

This tool does NOT issue predictions, certify Negatives or promote models.
No source data is written to a repository checkout or printed to stdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from xml.etree import ElementTree

STAMP = re.compile(r"(?m)^\s*(20\d{2})/(\d{2})/(\d{2})\s+(\d{1,2}):(\d{2})\s*$")
VALID_EXT = {"log": ".txt", "gpx": ".gpx"}


class IntakeError(ValueError):
    pass


def operational_night(stamp: datetime) -> str:
    if stamp.hour < 7:
        stamp -= timedelta(days=1)
    return stamp.strftime("%Y-%m-%d")


def summarize_log(contents: str) -> dict:
    """Literal event-count diagnostics only, NOT validated capture/effort evidence."""
    starts = list(STAMP.finditer(contents))
    if not starts:
        raise IntakeError("No recognizable timestamps")
    nights: dict[str, dict] = {}
    for i, match in enumerate(starts):
        try:
            timestamp = datetime(*map(int, match.groups()))
        except ValueError as exc:
            raise IntakeError("Invalid recorded timestamp") from exc
        night = operational_night(timestamp)
        rec = nights.setdefault(night, {"owner_habu_capture_events": 0,
                                        "habu_sighting_events": 0,
                                        "habu_roadkill_events": 0,
                                        "start_events": 0, "end_events": 0,
                                        "ambiguous_events": 0})
        block = contents[match.end():starts[i+1].start() if i+1 < len(starts) else len(contents)]
        lines = [x.strip() for x in block.splitlines() if x.strip()]
        if not lines:
            continue
        head = lines[0]
        if "エリア探索開始" in lines:
            rec["start_events"] += 1
        if "エリア探索終了" in lines:
            rec["end_events"] += 1
        if head in {"捕獲", "目撃", "轢死"}:
            species_lines = [x for x in lines[1:] if x == "ハブ" or x.startswith("ハブ捕獲")]
            is_hime = any("ヒメハブ" in x for x in lines[1:])
            if head == "捕獲" and species_lines and not is_hime:
                rec["owner_habu_capture_events"] += 1
                if any(re.fullmatch(r"\d+匹", x) for x in lines[1:]):
                    rec["ambiguous_events"] += 1
            elif head == "目撃" and "ハブ" in species_lines and not is_hime:
                rec["habu_sighting_events"] += 1
            elif head == "轢死" and "ハブ" in species_lines and not is_hime:
                rec["habu_roadkill_events"] += 1
            if head == "捕獲" and not species_lines:
                rec["ambiguous_events"] += 1
    return {"nights": nights, "record_count": len(starts),
            "classification": "UNVERIFIED_SOURCE_DIAGNOSTIC"}


def _digest(path: Path) -> tuple[str, int]:
    h, n = hashlib.sha256(), 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
            n += len(chunk)
    return h.hexdigest(), n


def _immutable_copy(source: Path, target: Path, expected: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if not target.is_file() or target.is_symlink() or _digest(target)[0] != expected:
            raise IntakeError("Existing archive conflict")
        return
    temp = None
    try:
        with NamedTemporaryFile(dir=target.parent, prefix=".pending-", delete=False) as fout:
            temp = Path(fout.name)
            os.chmod(temp, 0o600)
            with source.open("rb") as fin:
                shutil.copyfileobj(fin, fout, 1024 * 1024)
            fout.flush()
            os.fsync(fout.fileno())
        if _digest(temp)[0] != expected:
            raise IntakeError("SHA mismatch during intake")
        try:
            os.link(temp, target)
        except FileExistsError:
            if _digest(target)[0] != expected:
                raise IntakeError("Concurrent archive conflict")
    finally:
        if temp and temp.exists():
            temp.unlink()


def intake(repo_root: Path, private_root: Path, *, log_file: Path | None = None,
           gpx_file: Path | None = None) -> dict:
    repo_root = repo_root.resolve(strict=True)
    private_root = private_root.resolve()
    if private_root == repo_root or repo_root in private_root.parents or private_root in repo_root.parents:
        raise IntakeError("Private storage must not overlap repository checkout")
    if not any((log_file, gpx_file)):
        raise IntakeError("Provide a log and/or GPX")
    private_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix" and private_root.stat().st_mode & 0o077:
        raise IntakeError("Private root has group/other permissions")
    records = []
    diagnostics = {"status": "NOT_RUN", "reason": "Log absent"}
    for kind, src in (("log", log_file), ("gpx", gpx_file)):
        if src is None:
            continue
        src = Path(src)
        if src.is_symlink() or not src.is_file():
            raise IntakeError("Raw source must be a regular non-symlink file")
        sha, size = _digest(src)
        if not size or size > 200 * 1024 * 1024:
            raise IntakeError("Invalid raw source size")
        if kind == "log":
            try:
                diagnostics = summarize_log(src.read_text(encoding="utf-8-sig"))
            except UnicodeError as exc:
                raise IntakeError("Text log must be UTF-8") from exc
        else:
            try:
                for _, elem in ElementTree.iterparse(src, events=("end",)):
                    elem.clear()
            except ElementTree.ParseError as exc:
                raise IntakeError("GPX XML malformed") from exc
        target = private_root / "raw" / kind / (sha + VALID_EXT[kind])
        _immutable_copy(src, target, sha)
        records.append({"type": kind, "sha256": sha, "size_bytes": size,
                        "private_archive": str(target)})
    canonical = json.dumps(records, ensure_ascii=False, sort_keys=True).encode()
    receipt_id = hashlib.sha256(canonical).hexdigest()
    report = {"schema": "habu-private-intake-v1", "receipt_id": receipt_id,
              "sources": records, "log_diagnostic": diagnostics,
              "pdca": "NOT_RUN", "model_validation": "NOT_RUN",
              "official_p0": "NOT_CHECKED", "negative_labels": "NOT_CERTIFIED"}
    receipt = private_root / "receipts" / (receipt_id + ".json")
    receipt.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
    if receipt.exists():
        if receipt.read_bytes() != encoded:
            raise IntakeError("Receipt conflict")
    else:
        tmp = None
        try:
            with NamedTemporaryFile(dir=receipt.parent, prefix=".pending-", delete=False) as stream:
                tmp = Path(stream.name)
                os.chmod(tmp, 0o600)
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(tmp, receipt)
            except FileExistsError:
                if receipt.read_bytes() != encoded:
                    raise IntakeError("Concurrent receipt conflict")
        finally:
            if tmp and tmp.exists():
                tmp.unlink()
    return {"receipt_id": receipt_id, "raw_files_archived": len(records),
            "pdca": "NOT_RUN", "model_validation": "NOT_RUN",
            "next": "Invoke existing PDCA in isolated private worktree when authorized sources and ORIGINAL P0 are available"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--gpx", type=Path)
    args = parser.parse_args()
    print(json.dumps(intake(args.repo_root, args.private_root, log_file=args.log,
                            gpx_file=args.gpx), ensure_ascii=False))


if __name__ == "__main__":
    main()
