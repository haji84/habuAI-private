"""Private, immutable source intake for existing Habu AI PDCA coordinator.

This tool does NOT issue predictions, certify Negatives or promote models.
No source data is written to a repository checkout or printed to stdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from xml.parsers import expat

STAMP = re.compile(r"(?m)^[^\S\n]*(20\d{2})/(\d{2})/(\d{2})\s+(\d{1,2}):(\d{2})[^\S\n]*$")
VALID_EXT = {"log": ".txt", "gpx": ".gpx"}
MAX_RAW_BYTES = 200 * 1024 * 1024
MAX_LOG_BYTES = 4 * 1024 * 1024
MAX_LOG_RECORDS = 20_000
MAX_LOG_NIGHTS = 128
MAX_XML_POINTS = 1_000_000
MAX_XML_ELEMENTS = 2_000_000
MAX_XML_DEPTH = 64
MAX_RECEIPT_BYTES = 256 * 1024
MAX_READ_BYTES = 2 * 1024 * 1024 * 1024
MAX_INTAKE_SECONDS = 300
READ_CHUNK_BYTES = 64 * 1024


class IntakeError(ValueError):
    pass


class _ReadBudget:
    """One cooperative parent clock/read ledger; a failed +1 read still counts."""
    def __init__(self, seconds, *, maximum=MAX_INTAKE_SECONDS, error_type=IntakeError):
        self.error_type = error_type
        if type(seconds) not in (int, float) or not 0 < seconds <= maximum or not math.isfinite(seconds):
            raise error_type("Invalid whole-entry timeout")
        self.deadline = time.monotonic() + seconds
        self.bytes_read = 0

    def check(self):
        if time.monotonic() >= self.deadline:
            raise self.error_type("Whole-entry deadline exceeded")
        if self.bytes_read > MAX_READ_BYTES:
            raise self.error_type("Cumulative read capacity exceeded")

    def remaining_seconds(self):
        self.check()
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise self.error_type("Whole-entry deadline exceeded")
        return remaining


def _regular_size(path: Path, limit: int, budget: _ReadBudget):
    budget.check()
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or
            getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
        raise budget.error_type("Source must be a regular non-reparse file")
    if not 0 < info.st_size <= limit:
        raise budget.error_type("Invalid source size")
    budget.check()
    return info


def _chunks(path: Path, limit: int, budget: _ReadBudget, *, expected_size=None):
    info = _regular_size(path, limit, budget)
    size = info.st_size if expected_size is None else expected_size
    if info.st_size != size:
        raise budget.error_type("Source size changed")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if (not stat.S_ISREG(opened.st_mode) or opened.st_size != size or
                (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)):
            raise budget.error_type("Source descriptor changed")
        total = 0
        while True:
            budget.check()
            allowance = min(READ_CHUNK_BYTES, size-total, limit-total,
                            MAX_READ_BYTES-budget.bytes_read)
            chunk = stream.read(max(0, allowance) + 1)
            budget.bytes_read += len(chunk)
            total += len(chunk)
            budget.check()
            if total > size or total > limit:
                raise budget.error_type("Source grew beyond original size/capacity")
            if not chunk:
                if total != size:
                    raise budget.error_type("Source shrank during read")
                break
            yield chunk


def _read_bytes(path: Path, limit: int, budget: _ReadBudget) -> bytes:
    data = bytearray()
    for chunk in _chunks(path, limit, budget):
        data.extend(chunk)
    budget.check()
    return bytes(data)


def _encoded_report(report: dict, budget: _ReadBudget) -> bytes:
    data = bytearray()
    for piece in json.JSONEncoder(ensure_ascii=False, indent=2).iterencode(report):
        budget.check()
        part = piece.encode("utf-8")
        if len(data) + len(part) + 1 > MAX_RECEIPT_BYTES:
            raise budget.error_type("Receipt capacity exceeded")
        data.extend(part)
    data.extend(b"\n")
    budget.check()
    return bytes(data)


def guard_private_path(root: Path, path: Path) -> None:
    """Cooperative no-reparse/containment check, not atomic FS confinement."""
    root, path = Path(root).absolute(), Path(path).absolute()
    try:
        parts = path.relative_to(root).parts
    except ValueError as exc:
        raise IntakeError("Private path escapes its root") from exc
    if ".." in parts:
        raise IntakeError("Private path traversal forbidden")
    current = root
    for part in (None, *parts):
        if part is not None:
            current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if (stat.S_ISLNK(info.st_mode) or
                getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise IntakeError("Private path symlink/junction/reparse forbidden")
        if current != path and not stat.S_ISDIR(info.st_mode):
            raise IntakeError("Private parent is not a directory")
    if not path.resolve().is_relative_to(root):
        raise IntakeError("Resolved private path escapes its root")


def source_receipt_id(records: list[dict]) -> str:
    """The original v1 records-only ID definition, unchanged for old receipts."""
    canonical = json.dumps(records, ensure_ascii=False, sort_keys=True).encode()
    return hashlib.sha256(canonical).hexdigest()


class _TempOwner:
    """Creation provenance; a POSIX descriptor pins the live inode generation.

    Windows cannot unlink our ordinary open files (real WinError32), so its
    existing FileID/creation-time checks do not pretend to be POSIX unlink proof.
    This token is local Python state and is never receipt/claim JSON authority.
    """
    __slots__ = ('identity', '_birth_ns', '_fd', '_closed')

    def __init__(self, stream):
        self._fd = None
        self._closed = False
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode):
            raise IntakeError('TEMP_CLEANUP_RESIDUAL: creation descriptor not regular')
        self.identity = (opened.st_dev, opened.st_ino)
        self._birth_ns = opened.st_ctime_ns
        if os.name == 'posix':
            self._fd = os.dup(stream.fileno())
            try:
                held = os.fstat(self._fd)
                if (held.st_dev, held.st_ino) != self.identity:
                    raise IntakeError('TEMP_CLEANUP_RESIDUAL: creation descriptor changed')
            except BaseException as primary:
                try:self.close()
                except BaseException:
                    BaseException.add_note(primary, 'TEMP_OWNER_CONSTRUCTION_CLOSE_RESIDUAL')
                raise

    def matches(self, current):
        if self._closed or not stat.S_ISREG(current.st_mode):
            return False
        if self._fd is not None:
            held = os.fstat(self._fd)
            return (stat.S_ISREG(held.st_mode) and
                    (held.st_dev, held.st_ino) == self.identity == (current.st_dev, current.st_ino))
        return (os.name == 'nt' and self.identity == (current.st_dev, current.st_ino)
                and self._birth_ns == current.st_ctime_ns)

    def close(self):
        if self._closed:
            return
        self._closed = True
        fd, self._fd = self._fd, None
        if fd is not None:
            os.close(fd)  # never retry a possibly released/reused descriptor

    def __del__(self):
        # Last-resort FD release only; normal callers explicitly close in finally.
        try:
            self.close()
        except BaseException:
            pass


def _temp_owner(stream):
    return _TempOwner(stream)


def cleanup_owned_temp(root: Path, temp: Path | None,
                       identity: _TempOwner | None, primary: BaseException | None, *, release=True) -> None:
    """Unlink only the creation-owned generation, then close its held descriptor."""
    failure = None
    try:
        if temp is not None:
            guard_private_path(root, temp)
            current = temp.lstat()
            if type(identity) is not _TempOwner or not identity.matches(current):
                raise IntakeError("TEMP_CLEANUP_RESIDUAL: temporary generation changed/unproven; replacement preserved")
            temp.unlink()
    except FileNotFoundError:
        pass
    except BaseException as residual:
        failure = residual
    finally:
        if release and type(identity) is _TempOwner:
            try:
                identity.close()
            except BaseException as residual:
                if failure is None:
                    failure = residual
                else:
                    BaseException.add_note(failure, 'TEMP_OWNER_DESCRIPTOR_CLOSE_RESIDUAL')
    if failure is not None:
        note = "TEMP_CLEANUP_RESIDUAL: temporary cleanup not verified; preserved for review"
        if primary is not None:
            BaseException.add_note(primary, note)
            return
        BaseException.add_note(failure, note)
        raise failure


def operational_night(stamp: datetime) -> str:
    if stamp.hour < 7:
        stamp -= timedelta(days=1)
    return stamp.strftime("%Y-%m-%d")


def summarize_log(contents: str, *, _budget=None) -> dict:
    """Literal event-count diagnostics only, NOT validated capture/effort evidence."""
    budget = _budget if _budget is not None else _ReadBudget(MAX_INTAKE_SECONDS)
    if len(contents) > MAX_LOG_BYTES or len(contents.encode("utf-8")) > MAX_LOG_BYTES:
        raise IntakeError("Log capacity exceeded")
    starts = []
    for match in STAMP.finditer(contents):
        budget.check()
        if len(starts) >= MAX_LOG_RECORDS:
            raise IntakeError("Log record capacity exceeded")
        starts.append(match)
    if not starts:
        raise IntakeError("No recognizable timestamps")
    nights: dict[str, dict] = {}
    for i, match in enumerate(starts):
        budget.check()
        try:
            timestamp = datetime(*map(int, match.groups()))
        except ValueError as exc:
            raise IntakeError("Invalid recorded timestamp") from exc
        night = operational_night(timestamp)
        if night not in nights and len(nights) >= MAX_LOG_NIGHTS:
            raise IntakeError("Log night capacity exceeded")
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
    budget.check()
    return {"nights": nights, "record_count": len(starts),
            "classification": "UNVERIFIED_SOURCE_DIAGNOSTIC"}


def _digest(path: Path, budget: _ReadBudget, limit=MAX_RAW_BYTES, *, expected_size=None) -> tuple[str, int]:
    h, n = hashlib.sha256(), 0
    for chunk in _chunks(path, limit, budget, expected_size=expected_size):
        h.update(chunk)
        n += len(chunk)
    budget.check()
    return h.hexdigest(), n


def _immutable_copy(source: Path, target: Path, expected: str, root: Path,
                    budget: _ReadBudget, size: int) -> None:
    budget.check()
    guard_private_path(root, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    guard_private_path(root, target)
    if target.exists():
        if _digest(target, budget, expected_size=size)[0] != expected:
            raise IntakeError("Existing archive conflict")
        return
    temp = None
    temp_identity = None
    try:
        with NamedTemporaryFile(dir=target.parent, prefix=".pending-", delete=False) as fout:
            temp = Path(fout.name)
            opened = os.fstat(fout.fileno())
            temp_identity = _temp_owner(fout)
            guard_private_path(root, temp)
            os.chmod(temp, 0o600)
            for chunk in _chunks(source, MAX_RAW_BYTES, budget, expected_size=size):
                fout.write(chunk)
            fout.flush()
            os.fsync(fout.fileno())
        guard_private_path(root, temp)
        if _digest(temp, budget, expected_size=size)[0] != expected:
            raise IntakeError("SHA mismatch during intake")
        try:
            guard_private_path(root, target)
            budget.check()
            os.link(temp, target)
        except FileExistsError:
            guard_private_path(root, target)
            if _digest(target, budget, expected_size=size)[0] != expected:
                raise IntakeError("Concurrent archive conflict")
        if _digest(target, budget, expected_size=size)[0] != expected:
            raise IntakeError("Published archive conflict")
    finally:
        cleanup_owned_temp(root, temp, temp_identity, sys.exception())


def _validate_gpx(stage: Path, size: int, digest: str, budget: _ReadBudget):
    parser = expat.ParserCreate(namespace_separator="}")
    depth = elements = points = 0
    def forbidden(*_):
        raise IntakeError("GPX DTD/entities forbidden")
    def start(name, attrs):
        nonlocal depth, elements, points
        budget.check()
        depth += 1
        elements += 1
        if name.rsplit("}", 1)[-1] == "trkpt":
            points += 1
        if depth > MAX_XML_DEPTH or elements > MAX_XML_ELEMENTS or points > MAX_XML_POINTS:
            raise IntakeError("GPX structure capacity exceeded")
    def end(name):
        nonlocal depth
        budget.check()
        depth -= 1
    parser.StartDoctypeDeclHandler = forbidden
    parser.EntityDeclHandler = forbidden
    parser.ExternalEntityRefHandler = forbidden
    parser.StartElementHandler = start
    parser.EndElementHandler = end
    h = hashlib.sha256()
    try:
        for chunk in _chunks(stage, MAX_RAW_BYTES, budget, expected_size=size):
            h.update(chunk)
            parser.Parse(chunk, False)
            budget.check()
        parser.Parse(b"", True)
    except expat.ExpatError as exc:
        raise IntakeError("GPX XML malformed") from exc
    budget.check()
    if h.hexdigest() != digest:
        raise IntakeError("Staged GPX changed during parse")


def intake(repo_root: Path, private_root: Path, *, log_file: Path | None = None,
           gpx_file: Path | None = None) -> dict:
    budget = _ReadBudget(MAX_INTAKE_SECONDS)
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
        limit = min(MAX_RAW_BYTES, MAX_LOG_BYTES) if kind == "log" else MAX_RAW_BYTES
        size = _regular_size(src, limit, budget).st_size  # reject declared oversize before open
        stage = identity = None
        try:
            with NamedTemporaryFile(dir=private_root, prefix=".capture-", delete=False) as out:
                stage = Path(out.name)
                info = os.fstat(out.fileno())
                identity = _temp_owner(out)
                guard_private_path(private_root, stage)
                os.chmod(stage, 0o600)
                h = hashlib.sha256()
                for chunk in _chunks(src, limit, budget, expected_size=size):
                    h.update(chunk)
                    out.write(chunk)
                out.flush()
                os.fsync(out.fileno())
            sha = h.hexdigest()
            guard_private_path(private_root, stage)
            if kind == "log":
                raw = _read_bytes(stage, limit, budget)
                if hashlib.sha256(raw).hexdigest() != sha:
                    raise IntakeError("Staged log changed during parse")
                try:
                    contents = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
                    diagnostics = summarize_log(contents, _budget=budget)
                except UnicodeError as exc:
                    raise IntakeError("Text log must be UTF-8") from exc
            else:
                _validate_gpx(stage, size, sha, budget)
            target = private_root / "raw" / kind / (sha + VALID_EXT[kind])
            _immutable_copy(stage, target, sha, private_root, budget, size)
        finally:
            cleanup_owned_temp(private_root, stage, identity, sys.exception())
        records.append({"type": kind, "sha256": sha, "size_bytes": size,
                        "private_archive": str(target)})
    receipt_id = source_receipt_id(records)
    report = {"schema": "habu-private-intake-v1", "receipt_id": receipt_id,
              "sources": records, "log_diagnostic": diagnostics,
              "pdca": "NOT_RUN", "model_validation": "NOT_RUN",
              "official_p0": "NOT_CHECKED", "negative_labels": "NOT_CERTIFIED"}
    receipt = private_root / "receipts" / (receipt_id + ".json")
    guard_private_path(private_root, receipt)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    guard_private_path(private_root, receipt)
    encoded = _encoded_report(report, budget)
    if receipt.exists():
        if _read_bytes(receipt, MAX_RECEIPT_BYTES, budget) != encoded:
            raise IntakeError("Receipt conflict")
    else:
        tmp = None
        temp_identity = None
        try:
            with NamedTemporaryFile(dir=receipt.parent, prefix=".pending-", delete=False) as stream:
                tmp = Path(stream.name)
                opened = os.fstat(stream.fileno())
                temp_identity = _temp_owner(stream)
                guard_private_path(private_root, tmp)
                os.chmod(tmp, 0o600)
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                guard_private_path(private_root, receipt)
                budget.check()
                os.link(tmp, receipt)
            except FileExistsError:
                guard_private_path(private_root, receipt)
                if _read_bytes(receipt, MAX_RECEIPT_BYTES, budget) != encoded:
                    raise IntakeError("Concurrent receipt conflict")
            if _read_bytes(receipt, MAX_RECEIPT_BYTES, budget) != encoded:
                raise IntakeError("Published receipt conflict")
        finally:
            cleanup_owned_temp(private_root, tmp, temp_identity, sys.exception())
    budget.check()
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
