#!/usr/bin/env python3
"""Offline-only migration of location-bearing Git originals into an encrypted vault.

No network, no Git pushes, no tracking rewrites, no plaintext staging copies.
Run only on a trusted local machine with the full source repository cloned.
Public CI may run synthetic tests; it MUST NOT archive real owner's files.
Uses the existing SourceCipher (AES-256-GCM), PBKDF2-HMAC-SHA256 passphrase
derivation, authenticated source digests and byte-exact independent readback.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import getpass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import subprocess
import sys

REPO_CODE = Path(__file__).resolve().parents[1]
if str(REPO_CODE) not in sys.path:
    sys.path.insert(0, str(REPO_CODE))
from scripts.private_dashboard_crypto import SourceCipher, CryptoError

VERSION = "habu-private-git-vault-v1"
PBKDF2_ROUNDS = 600_000
CHUNK = 8 * 1024 * 1024   # smaller than the existing SourceCipher per-blob limit
MAX_SOURCE_SIZE = 512 * 1024 * 1024
MAX_TOTAL = 2 * 1024 * 1024 * 1024
MAX_SOURCES = 10_000
MAX_MANIFEST = 12 * 1024 * 1024
SCOPES = (
    "data/raw/habu_logs/", "data/raw/gpx/", "data/raw/gpx_archives/",
    "data/raw/attachment_archives/", "data/raw/capture_db/",
    "data/raw/other/", "data/processed/individuals/",
    "data/processed/capture_events/", "data/reconstructions/habu_captures/",
)
LOCATION_EXTENSIONS = {".gpx", ".jsonl", ".kml", ".geojson", ".sqlite", ".sqlite3", ".db"}
PRIVATE_NAME = ("owner-raw", "private-raw", "original-gpx", "owner-gps", "capture-location")
SENSITIVE_CSV = re.compile(
    rb"(?<![0-9])(?:2[6-9]|3[01])\.[0-9]{6,}[\s,;\t]{1,90}"
    rb"(?:12[4-9]|13[0-1])\.[0-9]{6,}(?![0-9])"
)
SENSITIVE_KEYS = re.compile(
    rb'(?i)(?:"|\\?")?(?:latitude|longitude|gps_lat|gps_lon|capture_lat|capture_lon)'
    rb'(?:"|\\?")?\s*[:=]\s*-?\d{1,3}\.\d{6,}'
)
HASH = re.compile(r"[0-9a-f]{64}\Z")
NAME = re.compile(r"[a-f0-9]{32}\.enc\Z")
GIT_OID = re.compile(r"[0-9a-f]{40,64}\Z")


class VaultError(RuntimeError):
    """Fixed generic errors only; never print owner path or raw coordinates."""


@dataclass(frozen=True)
class Source:
    path: str
    oid: str
    size: int
    mode: str


def safe_path(path: str) -> str:
    if not isinstance(path, str) or not path or any(x in path for x in ("\\", "\0", ":")):
        raise VaultError("UNSAFE_SOURCE_PATH")
    p = PurePosixPath(path)
    if p.is_absolute() or any(s in (".", "..", "") for s in path.split("/")):
        raise VaultError("UNSAFE_SOURCE_PATH")
    return path


def run_git(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    p = subprocess.run(["git", "-C", str(repo), *args], input=input_bytes,
                       capture_output=True, check=False)
    if p.returncode:
        raise VaultError("GIT_SOURCE_UNAVAILABLE")
    return p.stdout


def repo_root(repo: Path) -> Path:
    path = repo.resolve(strict=True)
    root = Path(run_git(path, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if root != path:
        raise VaultError("EXPECTED_REPOSITORY_ROOT")
    return root


def head_sources(repo: Path) -> tuple[str, list[Source]]:
    head = run_git(repo, "rev-parse", "HEAD").decode().strip()
    if not GIT_OID.fullmatch(head):
        raise VaultError("UNPINNED_SOURCE_HEAD")
    entries = run_git(repo, "ls-tree", "-r", "--full-tree", "-l", "-z", head).split(b"\0")
    all_files = []
    for item in entries:
        if not item:
            continue
        try:
            metadata, raw_path = item.split(b"\t", 1)
            mode, kind, oid, length = metadata.decode("ascii").split()
            filename = safe_path(raw_path.decode("utf-8"))
            if kind != "blob" or not GIT_OID.fullmatch(oid):
                raise VaultError("SOURCE_TYPE_UNEXPECTED")
            if filename.startswith(("data/", "raw/", "Raw/", "library/", "Library/",
                                    "evidence/", "reports/", "docs/")):
                all_files.append(Source(filename, oid, int(length), mode))
        except (ValueError, UnicodeError):
            raise VaultError("INVALID_GIT_SOURCE_INVENTORY") from None
    if len(all_files) > MAX_SOURCES:
        raise VaultError("SOURCE_INVENTORY_LIMIT")
    return head, all_files


def role_sensitive(name: str) -> bool:
    lower = name.lower()
    if any(lower.startswith(s) for s in SCOPES):
        return True
    if lower.startswith(("data/", "raw/", "library/", "evidence/", "reports/", "docs/")):
        if any(lower.endswith(x) for x in LOCATION_EXTENSIONS):
            return True
        if any(t in lower for t in PRIVATE_NAME):
            return True
    return False


def content_sensitive(data: bytes) -> bool:
    return bool(SENSITIVE_CSV.search(data) or SENSITIVE_KEYS.search(data) or
                b"<trkpt " in data or b"<wpt " in data)


def source_bytes(repo: Path, source: Source) -> bytes:
    if source.mode not in ("100644", "100755") or source.size > MAX_SOURCE_SIZE:
        raise VaultError("UNSUPPORTED_OR_OVERSIZE_SOURCE")
    data = run_git(repo, "cat-file", "blob", source.oid)
    if len(data) != source.size:
        raise VaultError("GIT_BLOB_LENGTH_MISMATCH")
    header = ("blob " + str(len(data)) + "\0").encode()
    hash_alg = hashlib.sha256 if len(source.oid) == 64 else hashlib.sha1
    if hash_alg(header + data).hexdigest() != source.oid:
        raise VaultError("GIT_BLOB_DIGEST_MISMATCH")
    return data


def inventory(repo: Path) -> tuple[str, list[Source]]:
    commit, files = head_sources(repo)
    selected = []
    total = 0
    for src in files:
        if role_sensitive(src.path):
            chosen = True
        elif src.path.lower().endswith((".txt", ".csv", ".tsv", ".json", ".log", ".md")):
            # Inspect original committed bytes, not a mutable checkout.
            chosen = src.size > 4 * 1024 * 1024 or content_sensitive(source_bytes(repo, src))
        else:
            chosen = False
        if chosen:
            selected.append(src)
            total += src.size
        if total > MAX_TOTAL:
            raise VaultError("TOTAL_SOURCE_SIZE_LIMIT")
    return commit, selected


def password_key(passphrase: str, salt: bytes) -> bytes:
    if not isinstance(passphrase, str) or len(passphrase) < 16 or len(passphrase) > 1024:
        raise VaultError("PASSPHRASE_TOO_SHORT")
    if len(salt) != 16:
        raise VaultError("KDF_SALT_INVALID")
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt,
                               PBKDF2_ROUNDS, dklen=32)


def private_destination(dest: Path, *, forbidden: tuple[Path, ...]) -> Path:
    if not dest.is_absolute():
        raise VaultError("PRIVATE_DESTINATION_MUST_BE_ABSOLUTE")
    path = dest.expanduser().absolute()
    if path.exists() or path.is_symlink():
        raise VaultError("DESTINATION_ALREADY_EXISTS")
    for root in (path, *path.parents):
        if root.is_symlink() or (root / ".git").exists():
            raise VaultError("DESTINATION_OVERLAPS_GIT_OR_LINK")
    resolved_parent = path.parent.resolve(strict=True)
    for root in forbidden:
        other = root.resolve(strict=True)
        if resolved_parent == other or resolved_parent.is_relative_to(other):
            raise VaultError("DESTINATION_OVERLAPS_SOURCES")
    return path


def _write_new(path: Path, raw: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _read_existing(path: Path, bound: int) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > bound:
        raise VaultError("INVALID_ENCRYPTED_VAULT_CONTENTS")
    return path.read_bytes()


def _manifest(vault: Path, passphrase: str) -> tuple[dict, SourceCipher]:
    header = json.loads(_read_existing(vault / "package.json", 8192))
    if not isinstance(header, dict) or set(header) != {
            "schema_version", "salt_b64", "manifest_sha256", "source_commit",
            "sources", "parts"} or header["schema_version"] != VERSION:
        raise VaultError("INVALID_PACKAGE_HEADER")
    try:
        salt = base64.b64decode(header["salt_b64"], validate=True)
    except Exception:
        raise VaultError("INVALID_PACKAGE_HEADER") from None
    if len(salt) != 16 or not isinstance(header["sources"], int) or not 0 < header["sources"] <= MAX_SOURCES:
        raise VaultError("INVALID_PACKAGE_HEADER")
    if not GIT_OID.fullmatch(header["source_commit"]) or not HASH.fullmatch(header["manifest_sha256"]):
        raise VaultError("INVALID_PACKAGE_HEADER")
    cipher = SourceCipher(password_key(passphrase, salt))
    try:
        original = cipher.open(_read_existing(vault / "manifest.enc", MAX_MANIFEST + 256),
                               header["manifest_sha256"])
    except (CryptoError, OSError):
        raise VaultError("AUTHENTICATION_OR_INTEGRITY_FAILED") from None
    if hashlib.sha256(original).hexdigest() != header["manifest_sha256"]:
        raise VaultError("MANIFEST_INTEGRITY_FAILED")
    try:
        manifest = json.loads(original)
    except (UnicodeError, ValueError):
        raise VaultError("INVALID_PRIVATE_MANIFEST") from None
    if not isinstance(manifest, dict) or set(manifest) != {
            "schema_version", "source_commit", "files"} or manifest["schema_version"] != VERSION:
        raise VaultError("INVALID_PRIVATE_MANIFEST")
    if manifest["source_commit"] != header["source_commit"] or len(manifest["files"]) != header["sources"]:
        raise VaultError("PACKAGE_SOURCE_MISMATCH")
    return manifest, cipher


def _each_verified(vault: Path, manifest: dict, cipher: SourceCipher):
    seen_paths, seen_files = set(), {"manifest.enc", "package.json"}
    for row in manifest["files"]:
        if not isinstance(row, dict) or set(row) != {"path", "sha256", "size", "parts"}:
            raise VaultError("INVALID_PRIVATE_MANIFEST")
        relative = safe_path(row["path"])
        if relative in seen_paths or not HASH.fullmatch(row["sha256"]):
            raise VaultError("DUPLICATE_OR_INVALID_ORIGINAL")
        seen_paths.add(relative)
        if not isinstance(row["size"], int) or not 0 <= row["size"] <= MAX_SOURCE_SIZE:
            raise VaultError("INVALID_SOURCE_SIZE")
        digest = hashlib.sha256()
        total = 0
        for item in row["parts"]:
            if not isinstance(item, dict) or set(item) != {"name", "sha256", "size"}:
                raise VaultError("INVALID_PART_MANIFEST")
            name = item["name"]
            if not isinstance(name, str) or not NAME.fullmatch(name) or name in seen_files:
                raise VaultError("DUPLICATE_OR_UNSAFE_PART")
            seen_files.add(name)
            if not HASH.fullmatch(item["sha256"]) or not isinstance(item["size"], int) or not 0 < item["size"] <= CHUNK:
                raise VaultError("INVALID_PART_MANIFEST")
            try:
                clear = cipher.open(_read_existing(vault / name, CHUNK + 256),
                                    item["sha256"])
            except (OSError, CryptoError):
                raise VaultError("AUTHENTICATION_OR_INTEGRITY_FAILED") from None
            if len(clear) != item["size"] or hashlib.sha256(clear).hexdigest() != item["sha256"]:
                raise VaultError("PART_INTEGRITY_FAILED")
            total += len(clear)
            digest.update(clear)
            yield relative, clear
        if total != row["size"] or digest.hexdigest() != row["sha256"]:
            raise VaultError("SOURCE_INTEGRITY_FAILED")
    real_names = {p.name for p in vault.iterdir()}
    if real_names != seen_files:
        raise VaultError("UNKNOWN_OR_MISSING_ENCRYPTED_FILES")
    if sum(len(x["parts"]) for x in manifest["files"]) > 200_000:
        raise VaultError("PART_COUNT_LIMIT")


def verify(vault: Path, passphrase: str) -> dict:
    vault = vault.resolve(strict=True)
    manifest, cipher = _manifest(vault, passphrase)
    count = 0
    digest = hashlib.sha256()
    for _, part in _each_verified(vault, manifest, cipher):
        count += len(part)
        digest.update(part)
    return {"status": "VERIFIED_ENCRYPTED_ONLY", "sources": len(manifest["files"]),
            "bytes": count, "source_commit": manifest["source_commit"],
            "archive_digest_check": digest.hexdigest()[:16]}


def archive(repo: Path, out: Path, passphrase: str) -> dict:
    repo = repo_root(repo)
    out = private_destination(out, forbidden=(repo,))
    head, files = inventory(repo)
    if not files:
        raise VaultError("NO_PROTECTED_INPUTS")
    salt = secrets.token_bytes(16)
    cipher = SourceCipher(password_key(passphrase, salt))
    stage = out.parent / (".habu-private-stage-" + secrets.token_hex(12))
    stage.mkdir(mode=0o700)
    try:
        rows = []
        part_count = 0
        for source in files:
            original = source_bytes(repo, source)
            dig = hashlib.sha256(original).hexdigest()
            parts = []
            for at in range(0, len(original), CHUNK):
                chunk = original[at:at + CHUNK]
                name = secrets.token_hex(16) + ".enc"
                part_sha = hashlib.sha256(chunk).hexdigest()
                _write_new(stage / name, cipher.seal(chunk, part_sha))
                parts.append({"name": name, "sha256": part_sha, "size": len(chunk)})
                part_count += 1
            rows.append({"path": source.path, "sha256": dig,
                         "size": len(original), "parts": parts})
        manifest = {"schema_version": VERSION, "source_commit": head, "files": rows}
        manifest_bytes = json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")
        if len(manifest_bytes) > MAX_MANIFEST:
            raise VaultError("MANIFEST_SIZE_LIMIT")
        manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
        _write_new(stage / "manifest.enc", cipher.seal(manifest_bytes, manifest_sha))
        header = {"schema_version": VERSION, "source_commit": head,
                  "salt_b64": base64.b64encode(salt).decode("ascii"),
                  "manifest_sha256": manifest_sha,
                  "sources": len(rows), "parts": part_count}
        _write_new(stage / "package.json",
                   (json.dumps(header, sort_keys=True) + "\n").encode("utf-8"))
        receipt = verify(stage, passphrase)
        if receipt["sources"] != len(rows):
            raise VaultError("INDEPENDENT_READBACK_FAILED")
        os.rename(stage, out)  # Only after authenticating every encrypted item.
        return receipt
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise



def archive_history_bundle(repo: Path, out: Path, passphrase: str) -> dict:
    """Encrypt a byte-exact Git bundle of ALL LOCAL fetched refs, without
    writing a plaintext bundle anywhere. Cannot include unfetched PR refs or
    remote forks. An independent restore and git bundle verify is required.
    """
    repo = repo_root(repo)
    out = private_destination(out, forbidden=(repo,))
    head = run_git(repo, "rev-parse", "HEAD").decode().strip()
    refs = run_git(repo, "for-each-ref", "--format=%(refname)").splitlines()
    if not refs:
        raise VaultError("NO_LOCAL_HISTORY_REFS")
    salt = secrets.token_bytes(16)
    cipher = SourceCipher(password_key(passphrase, salt))
    stage = out.parent / (".habu-git-history-stage-" + secrets.token_hex(12))
    stage.mkdir(mode=0o700)
    process = None
    try:
        process = subprocess.Popen(
            ["git", "-C", str(repo), "bundle", "create", "-", "--all"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        original = hashlib.sha256()
        total, chunks, parts = 0, 0, []
        while True:
            part = process.stdout.read(CHUNK)
            if not part:
                break
            total += len(part)
            if total > MAX_SOURCE_SIZE:
                raise VaultError("HISTORY_BUNDLE_SIZE_LIMIT")
            original.update(part)
            name = secrets.token_hex(16) + ".enc"
            sha = hashlib.sha256(part).hexdigest()
            _write_new(stage / name, cipher.seal(part, sha))
            parts.append({"name": name, "sha256": sha, "size": len(part)})
            chunks += 1
        if process.wait(timeout=120) != 0 or total == 0:
            raise VaultError("GIT_BUNDLE_CREATION_FAILED")
        manifest = {
            "schema_version": VERSION, "source_commit": head,
            "files": [{"path": "internal/all-fetched-refs.bundle",
                       "sha256": original.hexdigest(), "size": total,
                       "parts": parts}]
        }
        sealed = json.dumps(manifest, ensure_ascii=False, separators=(",", ":"),
                            sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(sealed).hexdigest()
        _write_new(stage / "manifest.enc", cipher.seal(sealed, digest))
        header = {"schema_version": VERSION, "source_commit": head,
                  "salt_b64": base64.b64encode(salt).decode("ascii"),
                  "manifest_sha256": digest, "sources": 1, "parts": chunks}
        _write_new(stage / "package.json",
                   (json.dumps(header, sort_keys=True) + "\n").encode("utf-8"))
        proof = verify(stage, passphrase)
        if proof["bytes"] != total:
            raise VaultError("HISTORY_INDEPENDENT_READBACK_FAILED")
        os.rename(stage, out)
        return proof | {"status": "LOCAL_REFS_BUNDLE_ENCRYPTED_VERIFIED",
                        "local_refs": len(refs),
                        "remote_forks_or_unfetched_PR_refs_proven": False}
    except BaseException:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        shutil.rmtree(stage, ignore_errors=True)
        raise



def restore(vault: Path, out: Path, passphrase: str) -> dict:
    vault = vault.resolve(strict=True)
    out = private_destination(out, forbidden=(vault,))
    original = verify(vault, passphrase)  # prove complete before any write
    manifest, cipher = _manifest(vault, passphrase)
    stage = out.parent / (".habu-restore-stage-" + secrets.token_hex(12))
    stage.mkdir(mode=0o700)
    try:
        # Incrementally reconstruct only in private mode-0700 staging; never
        # touch or overwrite a file in the user's existing repository.
        for item in manifest["files"]:
            safe_path(item["path"])
            dest = stage / item["path"]
            if not dest.resolve().is_relative_to(stage):
                raise VaultError("UNSAFE_RESTORE_PATH")
            dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if dest.exists() or dest.is_symlink():
                raise VaultError("DUPLICATE_RESTORE_PATH")
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(dest, flags, 0o600)
            try:
                with os.fdopen(fd, "wb") as f:
                    for part in item["parts"]:
                        data = cipher.open(_read_existing(vault / part["name"], CHUNK + 256),
                                           part["sha256"])
                        f.write(data)
                    f.flush()
                    os.fsync(f.fileno())
            except BaseException:
                dest.unlink(missing_ok=True)
                raise
            if dest.stat().st_size != item["size"]:
                raise VaultError("RESTORED_LENGTH_MISMATCH")
            if hashlib.sha256(dest.read_bytes()).hexdigest() != item["sha256"]:
                raise VaultError("RESTORED_SOURCE_SHA_MISMATCH")
        os.rename(stage, out)
        return original | {"status": "RESTORED_TO_PRIVATE_LOCATION"}
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise



def local_history_paths(repo: Path) -> tuple[set[str], int]:
    """Return path-based candidates from fetched local refs, not remote proof."""
    root = repo_root(repo)
    refs = run_git(root, "for-each-ref", "--format=%(refname)").splitlines()
    history = run_git(root, "log", "--all", "--pretty=format:",
                      "--name-only", "--no-renames", "-z")
    paths = set()
    for segment in history.split(b"\0"):
        if not segment:
            continue
        try:
            path = segment.decode("utf-8").strip("\n")
            if path and role_sensitive(safe_path(path)):
                paths.add(path)
        except (UnicodeError, VaultError):
            raise VaultError("UNSUPPORTED_HISTORICAL_PATH") from None
    return paths, len(refs)


def history_candidates(repo: Path) -> dict:
    """Only a PATH audit; cannot clear cached PRs, forks or unknown old blobs."""
    root = repo_root(repo)
    current_head, now = inventory(root)
    paths, ref_count = local_history_paths(root)
    current_paths = {x.path for x in now}
    return {"status": "HISTORICAL_REFS_NEED_PRIVATE_REWRITE_AND_GITHUB_SUPPORT",
            "local_refs": ref_count, "current_sensitive_sources": len(current_paths),
            "historical_sensitive_path_candidates": len(paths),
            "historical_paths_absent_from_current": len(paths - current_paths),
            "all_remote_forks_clones_and_PR_refs_audited": False,
            "source_commit": current_head}


def write_history_removal_plan(repo: Path, destination: Path) -> dict:
    """Emit only to a new private 0600 file, NEVER to GitHub Actions logs.

    This is a REVIEW CANDIDATE for git-filter-repo --paths-from-file,
    not a verified exhaustive purge list and NEVER a rewrite command.
    """
    root = repo_root(repo)
    out = private_destination(destination, forbidden=(root,))
    paths, ref_count = local_history_paths(root)
    if not paths or any("\n" in path or "\r" in path for path in paths):
        raise VaultError("HISTORICAL_PATHS_REQUIRE_REVIEW")
    lines = "".join("literal:" + path + "\n" for path in sorted(paths))
    _write_new(out, lines.encode("utf-8"))
    return {"status": "PRIVATE_HISTORY_REWRITE_REVIEW_ONLY",
            "candidate_paths": len(paths), "local_refs": ref_count,
            "history_rewritten": False, "GitHub_support_completed": False}



def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline private GPS source archive. NEVER run on public CI with real data.")
    sub = parser.add_subparsers(dest="action", required=True)
    scan = sub.add_parser("scan", help="Count tracked candidate sources without printing paths")
    scan.add_argument("--repo", type=Path, required=True)
    history = sub.add_parser("history-scan", help="Count location-bearing paths across locally fetched refs")
    history.add_argument("--repo", type=Path, required=True)
    hp = sub.add_parser("history-pathlist", help="Export private candidate path list for human review")
    hp.add_argument("--repo", type=Path, required=True)
    hp.add_argument("--out", type=Path, required=True)
    bundle = sub.add_parser("history-archive", help="Encrypt all fetched local Git refs without plaintext bundle")
    bundle.add_argument("--repo", type=Path, required=True)
    bundle.add_argument("--out", type=Path, required=True)
    enc = sub.add_parser("archive", help="Encrypt and prove byte-exact recovery before publishing")
    enc.add_argument("--repo", type=Path, required=True)
    enc.add_argument("--out", type=Path, required=True)
    chk = sub.add_parser("verify", help="Read-back and authenticate every encrypted part")
    chk.add_argument("--vault", type=Path, required=True)
    rest = sub.add_parser("restore", help="Explicitly reconstruct into a new private directory")
    rest.add_argument("--vault", type=Path, required=True)
    rest.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == "scan":
            head, files = inventory(repo_root(args.repo))
            print(json.dumps({"status": "AUDIT_ONLY_NO_FILES_MOVED",
                              "count": len(files), "bytes": sum(x.size for x in files),
                              "head_verified": bool(head)}))
            return
        if args.action == "history-scan":
            print(json.dumps(history_candidates(args.repo), sort_keys=True))
            return
        if args.action == "history-pathlist":
            print(json.dumps(write_history_removal_plan(args.repo, args.out), sort_keys=True))
            return
        phrase = getpass.getpass("Private vault passphrase (not stored; at least 16 characters): ")
        if args.action == "archive":
            result = archive(args.repo, args.out, phrase)
        elif args.action == "history-archive":
            result = archive_history_bundle(args.repo, args.out, phrase)
        elif args.action == "verify":
            result = verify(args.vault, phrase)
        else:
            result = restore(args.vault, args.out, phrase)
        # Never print original names, coordinates, password or secret keys.
        print(json.dumps(result, sort_keys=True))
    except (OSError, ValueError, VaultError, CryptoError, subprocess.SubprocessError):
        print("PRIVATE_GPS_VAULT_HOLD: incomplete or unsafe operation; no original removed",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
