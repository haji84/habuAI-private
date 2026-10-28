"""Private-source runner for the existing, single-entry Habu PDCA engine.

This adapter intentionally does not declare imported raw files eligible scientific data.
Run receipts and stdout logs remain within a private filesystem outside GitHub.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from private_pdca_intake import IntakeError, MAX_RAW_BYTES, cleanup_owned_temp, guard_private_path, source_receipt_id

SHA = re.compile(r"[a-f0-9]{64}\Z")
NIGHT = re.compile(r"20\d{2}-\d{2}-\d{2}\Z")


class PrivateRunError(ValueError):
    pass


def _guard_private_path(root: Path, path: Path) -> None:
    try:
        guard_private_path(root, path)
    except IntakeError as exc:
        raise PrivateRunError(str(exc)) from exc


def _cleanup_owned_temp(root, temp, identity, primary):
    try:
        cleanup_owned_temp(root, temp, identity, primary)
    except IntakeError as exc:
        raise PrivateRunError(str(exc)) from exc


def _is_under(path: Path, base: Path) -> bool:
    return path == base or base in path.parents


def _validate_roots(code_root: Path, workspace: Path, store: Path) -> tuple[Path, Path, Path]:
    code_root = code_root.resolve(strict=True)
    workspace = workspace.resolve(strict=True)
    store = store.resolve(strict=True)
    if not (code_root / "scripts" / "run_pdca.py").is_file():
        raise PrivateRunError("Canonical PDCA script unavailable")
    for private in (workspace, store):
        if _is_under(private, code_root) or _is_under(code_root, private):
            raise PrivateRunError("Refusing a private path overlapping repository code")
        if os.name == "posix" and private.stat().st_mode & 0o077:
            raise PrivateRunError("Private directory accessible by group/other")
    if workspace == store or _is_under(workspace, store) or _is_under(store, workspace):
        raise PrivateRunError("Source store and scientific workspace must be separate")
    return code_root, workspace, store


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def _receipt_sources(receipt_path: Path, store: Path) -> tuple[str, list[dict]]:
    _guard_private_path(store, receipt_path)
    receipt_path = receipt_path.resolve(strict=True)
    if not _is_under(receipt_path, store):
        raise PrivateRunError("Receipt outside private source store")
    try:
        manifest = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PrivateRunError("Invalid intake receipt JSON") from exc
    fields = {"schema", "receipt_id", "sources", "log_diagnostic", "pdca",
              "model_validation", "official_p0", "negative_labels"}
    if (not isinstance(manifest, dict) or set(manifest) != fields or
            manifest["schema"] != "habu-private-intake-v1" or
            not isinstance(manifest["log_diagnostic"], dict) or
            manifest["pdca"] != "NOT_RUN" or manifest["model_validation"] != "NOT_RUN" or
            manifest["official_p0"] != "NOT_CHECKED" or manifest["negative_labels"] != "NOT_CERTIFIED"):
        raise PrivateRunError("Invalid intake receipt schema")
    receipt_id = manifest.get("receipt_id")
    if not isinstance(receipt_id, str) or not SHA.fullmatch(receipt_id):
        raise PrivateRunError("Invalid receipt identifier")
    rows = manifest.get("sources")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 2:
        raise PrivateRunError("Missing original sources")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"type", "sha256", "size_bytes", "private_archive"}:
            raise PrivateRunError("Invalid source row schema")
        kind = row.get("type")
        digest = row.get("sha256")
        if kind not in ("log", "gpx") or not isinstance(digest, str) or not SHA.fullmatch(digest):
            raise PrivateRunError("Invalid source manifest entry")
        if kind in seen:
            raise PrivateRunError("Duplicate source kind")
        seen.add(kind)
        size, archive = row["size_bytes"], row["private_archive"]
        if type(size) is not int or not 0 < size <= MAX_RAW_BYTES:
            raise PrivateRunError("Invalid source size")
        if not isinstance(archive, str) or not archive or not Path(archive).is_absolute():
            raise PrivateRunError("Invalid source archive path")
    if source_receipt_id(rows) != receipt_id:
        raise PrivateRunError("Receipt identifier does not bind source rows")
    for row in rows:
        target = Path(row["private_archive"])
        _guard_private_path(store, target)
        if target.is_symlink():
            raise PrivateRunError("Symlink source forbidden")
        target = target.resolve(strict=True)
        if not _is_under(target, store) or not target.is_file():
            raise PrivateRunError("Source outside private store")
        if _sha(target) != row["sha256"] or target.stat().st_size != row["size_bytes"]:
            raise PrivateRunError("Source integrity mismatch")
    return receipt_id, rows


def _copy_verified(source: Path, dest: Path, digest: str, allowed_root: Path) -> None:
    _guard_private_path(allowed_root, dest)
    dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    _guard_private_path(allowed_root, dest)
    real_parent = dest.parent.resolve(strict=True)
    if not _is_under(real_parent, allowed_root):
        raise PrivateRunError("Inbox escapes private workspace")
    if dest.is_symlink():
        raise PrivateRunError("Symlink destination forbidden")
    if dest.exists():
        if _sha(dest) != digest:
            raise PrivateRunError("Scientific inbox collision")
        return
    tmp = None
    temp_identity = None
    try:
        with NamedTemporaryFile(dir=dest.parent, delete=False) as f:
            tmp = Path(f.name)
            opened = os.fstat(f.fileno())
            temp_identity = (opened.st_dev, opened.st_ino)
            _guard_private_path(allowed_root, tmp)
            os.chmod(tmp, 0o600)
            with source.open("rb") as inp:
                for part in iter(lambda: inp.read(1024 * 1024), b""):
                    f.write(part)
            f.flush()
            os.fsync(f.fileno())
        _guard_private_path(allowed_root, tmp)
        if _sha(tmp) != digest:
            raise PrivateRunError("Copy integrity mismatch")
        try:
            _guard_private_path(allowed_root, dest)
            os.link(tmp, dest)
        except FileExistsError:
            _guard_private_path(allowed_root, dest)
            if _sha(dest) != digest:
                raise PrivateRunError("Concurrent inbox collision")
    finally:
        _cleanup_owned_temp(allowed_root, tmp, temp_identity, sys.exception())


def run_private(code_root: Path, workspace: Path, store: Path,
                receipt_path: Path, night: str, timeout_seconds: int = 330) -> dict:
    if not NIGHT.fullmatch(night):
        raise PrivateRunError("Invalid operational-night identifier")
    code_root, workspace, store = _validate_roots(code_root, workspace, store)
    receipt_id, rows = _receipt_sources(receipt_path, store)
    identity = hashlib.sha256(f"{night}:{receipt_id}".encode()).hexdigest()
    outdir = store / "private_pdca_runs"
    dest = outdir / f"{identity}.json"
    _guard_private_path(store, dest)
    for row in rows:
        digest = row["sha256"]
        kind = row["type"]
        extension = ".txt" if kind == "log" else ".gpx"
        _copy_verified(Path(row["private_archive"]),
                       workspace / "incoming" / "private_pdca" / (digest + extension),
                       digest, workspace)
    command = [sys.executable, str(code_root / "scripts" / "run_pdca.py"),
               "--root", str(workspace), "--night", night]
    # The engine sees a private workspace, not the public repository checkout.
    outcome = "NOT_RUN"
    overall = "BLOCKED"
    try:
        proc = subprocess.run(command, cwd=workspace, capture_output=True,
                              timeout=timeout_seconds, check=False)
        output = json.loads(proc.stdout.decode("utf-8"))
        outcome = str(output.get("overall_status", "INVALID_OUTPUT"))
        if outcome not in {"PASS", "PARTIAL", "BLOCKED", "FAIL", "NOT_VALIDATED"}:
            outcome = "INVALID_OUTPUT"
        overall = "PARTIAL" if proc.returncode == 0 else "BLOCKED"
    except (subprocess.TimeoutExpired, UnicodeError, json.JSONDecodeError, OSError):
        outcome = "RUNNER_FAILURE"
        overall = "BLOCKED"
    # Private intake is not canonically admitted evidence and thus never itself proves KPI.
    record = {"schema": "habu-private-pdca-run-v1", "night": night,
              "source_receipt_id": receipt_id, "source_sha256": [r["sha256"] for r in rows],
              "backend_status": outcome, "overall_status": overall,
              "raw_inbox_only": True, "source_eligible_for_model": False,
              "p0_frozen_score": "NOT_CERTIFIED", "p1_scores": "NOT_CERTIFIED",
              "model_validation": "NOT_CERTIFIED", "champion_promotion": "FORBIDDEN",
              "next": "Complete canonical source-admission audit, then rerun existing engine"}
    _guard_private_path(store, dest)
    outdir.mkdir(mode=0o700, parents=True, exist_ok=True)
    _guard_private_path(store, dest)
    if dest.exists() and not dest.is_file():
        raise PrivateRunError("Result receipt is not a regular file")
    previous = json.loads(dest.read_text()) if dest.exists() else None
    if previous and previous != record:
        raise PrivateRunError("Non-identical scientific retry: retain old run, use versioned attempt")
    if not previous:
        data = (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode()
        tmp = None
        temp_identity = None
        try:
            with NamedTemporaryFile(dir=outdir, delete=False) as file:
                tmp = Path(file.name)
                opened = os.fstat(file.fileno())
                temp_identity = (opened.st_dev, opened.st_ino)
                _guard_private_path(store, tmp)
                os.chmod(tmp, 0o600)
                file.write(data)
                file.flush()
                os.fsync(file.fileno())
            try:
                _guard_private_path(store, dest)
                os.link(tmp, dest)
            except FileExistsError:
                _guard_private_path(store, dest)
                if dest.read_bytes() != data:
                    raise PrivateRunError("Concurrent result conflict")
        finally:
            _cleanup_owned_temp(store, tmp, temp_identity, sys.exception())
    return {"run_receipt": identity, "backend_status": outcome,
            "overall_status": overall, "p0": "NOT_CERTIFIED",
            "model_validation": "NOT_CERTIFIED"}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--code-root", type=Path, required=True)
    p.add_argument("--private-workspace", type=Path, required=True)
    p.add_argument("--private-store", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--night", required=True)
    a = p.parse_args()
    print(json.dumps(run_private(a.code_root, a.private_workspace, a.private_store,
                                 a.receipt, a.night), ensure_ascii=False))


if __name__ == "__main__":
    main()
