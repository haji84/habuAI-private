#!/usr/bin/env bash
# Fail closed before a protected Pages build or a public-source merge.
# GitHub repo visibility is PUBLIC as of audit; Cloudflare Access does NOT
# protect GitHub's source tree or Git history.
set -euo pipefail
python - <<'PY'
import pathlib
import re
import subprocess
import sys

root = pathlib.Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True).strip()).resolve()
if pathlib.Path.cwd().resolve() != root:
    print("PUBLIC_SOURCE_AUDIT_HOLD: run from repository root")
    sys.exit(1)

tracked = subprocess.check_output(
    ["git", "ls-files", "-z", "--", "data/", "library/", "Library/", "raw/", "Raw/"]
).split(b"\x00")
# Deliberately detect by file *role* as well as by content. No original
# coordinates, source filenames, hashes, or small location excerpts go to CI logs.
high_precision_pair = re.compile(
    rb"(?<![0-9])(?:2[6-9]|3[01])\.[0-9]{6,}[\s,;\t]{1,70}"
    rb"(?:12[4-9]|13[0-1])\.[0-9]{6,}(?![0-9])"
)
latitude_value = re.compile(
    rb'["\x27](?:lat|latitude)["\x27]\s*:\s*(?:2[6-9]|3[01])\.[0-9]{6,}'
)
longitude_value = re.compile(
    rb'["\x27](?:lon|longitude)["\x27]\s*:\s*(?:12[4-9]|13[0-1])\.[0-9]{6,}'
)
blocked = 0
for item in tracked:
    if not item:
        continue
    try:
        name = item.decode("utf-8")
    except UnicodeDecodeError:
        blocked += 1
        continue
    path = root / name
    try:
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            blocked += 1
            continue
        # Exact originals and route formats do not belong in a public repo,
        # even if their GPS contents happen not to match an island bounding box.
        suffix = path.suffix.lower()
        lower = path.name.lower()
        if suffix in (".gpx", ".jsonl", ".kml", ".geojson", ".sqlite", ".sqlite3", ".db") or (
            any(token in lower for token in ("owner-raw", "private-raw", "original-gpx", "owner-gps"))
            and suffix in (".txt", ".log", ".csv", ".json", ".tsv")
        ):
            blocked += 1
            continue
        if suffix not in (".json", ".csv", ".tsv", ".txt", ".log"):
            continue
        if path.stat().st_size > 4 * 1024 * 1024:
            blocked += 1
            continue
        body = path.read_bytes()
        if high_precision_pair.search(body) or (
            latitude_value.search(body) and longitude_value.search(body)
        ):
            blocked += 1
    except (OSError, ValueError):
        blocked += 1

if blocked:
    # Do not disclose matching filenames or GPS values into a public CI log.
    print("PUBLIC_SOURCE_AUDIT_HOLD: precise/original source present in tracked data",
          "(matching files:", blocked, "). Do not merge or deploy from public git.")
    print("Remediation requires private-source migration, history review, and")
    print("fresh independent proof that personal GPS is no longer public.")
    sys.exit(1)
print("PUBLIC_SOURCE_AUDIT_PASS: no prohibited tracked originals in audited data paths")
PY
