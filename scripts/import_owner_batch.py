#!/usr/bin/env python3
"""Review and import a local HUB NATURAL confirmed-night batch into a feature branch.

This accepts aggregate-only owner confirmations, never uploads/infers raw
capture events. The browser download is NOT an authoritative GitHub write.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from scripts.build_capture_dashboard import build, CaptureDataError

ROOT_FIELDS = {
    "schema_version", "baseline_asof", "source_sha256",
    "requires_server_reconciliation", "counts_are_owner_confirmed_not_scientific_labels", "files",
}
NIGHT_FIELDS = {
    "schema_version", "source", "operational_date", "owner_confirmed",
    "search_performed", "capture_count", "revision",
}
PATH_PATTERN = re.compile(r"data/raw/habu_owner_nights/(20\d\d)/(20\d\d-\d\d-\d\d)\.json")


def validate_batch(payload: object) -> tuple[str, dict[str, dict]]:
    if not isinstance(payload, dict) or set(payload) != ROOT_FIELDS:
        raise CaptureDataError("Unknown batch fields")
    if (payload["schema_version"] != "habu-local-intake-review-batch-v1"
            or payload["requires_server_reconciliation"] is not True
            or payload["counts_are_owner_confirmed_not_scientific_labels"] is not True):
        raise CaptureDataError("Untrusted batch metadata")
    asof = payload["baseline_asof"]
    if type(asof) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", asof):
        raise CaptureDataError("Invalid baseline date")
    try:
        date.fromisoformat(asof)
    except ValueError as ex:
        raise CaptureDataError("Invalid calendar date") from ex
    hashes = payload["source_sha256"]
    if (not isinstance(hashes, list) or not hashes
            or len(hashes) != len(set(hashes))
            or any(type(x) is not str or not re.fullmatch("[0-9a-f]{64}", x) for x in hashes)):
        raise CaptureDataError("Source hash evidence missing/invalid")
    inputs = payload["files"]
    if not isinstance(inputs, list) or not (1 <= len(inputs) <= 180):
        raise CaptureDataError("Invalid confirmed-night list")
    output: dict[str, dict] = {}
    for item in inputs:
        if not isinstance(item, dict) or set(item) != {"path", "content"}:
            raise CaptureDataError("Invalid file entry")
        path = item["path"]
        if not isinstance(path, str):
            raise CaptureDataError("Invalid filename")
        match = PATH_PATTERN.fullmatch(path)
        if not match:
            raise CaptureDataError("Only dated aggregate owner night files are permitted")
        record = item["content"]
        if not isinstance(record, dict) or set(record) != NIGHT_FIELDS:
            raise CaptureDataError("Unexpected owner night fields")
        operational_date = record["operational_date"]
        try:
            date.fromisoformat(operational_date)
        except (TypeError, ValueError) as exc:
            raise CaptureDataError("Invalid night calendar date") from exc
        if (match.group(1) != operational_date[:4] or match.group(2) != operational_date
                or operational_date <= asof or path in output):
            raise CaptureDataError("Overlapping/duplicate confirmed night")
        if (record["schema_version"] != "habu-owner-night-v1"
                or record["source"] != "user Habu log"
                or record["owner_confirmed"] is not True
                or record["search_performed"] is not True
                or type(record["capture_count"]) is not int
                or not 0 <= record["capture_count"] <= 100
                or record["revision"] != 1 or type(record["revision"]) is not int):
            raise CaptureDataError("Unconfirmed or invalid tally")
        output[path] = record
    return asof, output


def plan(repo: Path, payload: object) -> tuple[list[tuple[Path, dict]], list[str]]:
    asof, entries = validate_batch(payload)
    current = build(repo)
    pending = []
    skipped = []
    for relative, record in entries.items():
        target = repo / relative
        if target.exists():
            try:
                if json.loads(target.read_text(encoding="utf-8")) == record:
                    skipped.append(relative)
                    continue
            except (ValueError, UnicodeError) as exc:
                raise CaptureDataError("Existing destination is not valid JSON") from exc
            raise CaptureDataError("Conflicting already registered date: " + record["operational_date"])
        if asof != current["asof"]:
            raise CaptureDataError("Dashboard baseline changed: refresh comparison first")
        if record["operational_date"] <= current["asof"]:
            raise CaptureDataError("Night overlaps current dashboard")
        pending.append((target, record))
    if pending:
        # Verify all tentative writes in an isolated copy BEFORE touching the working branch.
        with tempfile.TemporaryDirectory() as d:
            sandbox = Path(d)
            for rel in ("dashboard/baseline_2026.json", "dashboard/owner_effort_2026-10-26.json"):
                source = repo / rel
                if source.is_file():
                    dest = sandbox / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, dest)
            for rel in ("data/raw/habu_logs", "data/raw/habu_effort",
                        "data/raw/habu_owner_nights", "data/raw/habu_owner_amendments",
                        "data/reconstructions/habu_captures", "data/processed/individuals"):
                src = repo / rel
                if src.is_dir():
                    shutil.copytree(src, sandbox / rel, dirs_exist_ok=True)
            for target, record in pending:
                dest = sandbox / target.relative_to(repo)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            build(sandbox)
    return pending, skipped


def feature_branch(repo: Path) -> bool:
    result = subprocess.run(["git", "branch", "--show-current"], cwd=repo,
                            capture_output=True, text=True, check=False)
    return result.returncode == 0 and result.stdout.strip() not in ("", "main", "master")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=Path, required=True)
    ap.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--apply", action="store_true", help="Create aggregate JSONs ONLY in a feature branch")
    a = ap.parse_args()
    repo = a.repo_root.resolve()
    payload = json.loads(a.batch.read_text(encoding="utf-8"))
    writes, skipped = plan(repo, payload)
    print(f"Validated new nights: {len(writes)}; already-identical: {len(skipped)}")
    if not a.apply:
        print("DRY_RUN_ONLY: use --apply on an authorized feature branch")
        return
    if not feature_branch(repo):
        raise SystemExit("REFUSED: approval workflow requires a feature branch; main is never updated")
    for path, record in writes:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print("FILES_CREATED_ON_FEATURE_BRANCH: review and PR required; not deployed")


if __name__ == "__main__":
    main()
