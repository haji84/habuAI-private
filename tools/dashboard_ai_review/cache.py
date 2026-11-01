"""Privacy-minimal, fail-closed cache for verified zero-finding review segments.

This cache is only an optimization within PR #136. It cannot authorize approval.
No patches, model responses, file paths, location data or secrets are persisted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.request

VERSION = 1
MAX_CACHE_BYTES = 512 * 1024
MAX_CACHE_ENTRIES = 4096
HEX_64 = re.compile(r"^[0-9a-f]{64}$")
HEX_16 = re.compile(r"^[0-9a-f]{16}$")
LOCAL_TAGS_URL = "http://127.0.0.1:11434/api/tags"


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def model_digest(model: str) -> str:
    """Pin the local model's actual Ollama digest, not its mutable tag alone."""
    with urllib.request.urlopen(LOCAL_TAGS_URL, timeout=15) as response:
        data = json.load(response)
    models = data.get("models")
    if not isinstance(models, list):
        raise ValueError("Local Ollama model listing unavailable")
    for item in models:
        if not isinstance(item, dict):
            continue
        if item.get("name") == model or item.get("model") == model:
            digest = item.get("digest")
            if not isinstance(digest, str) or not HEX_64.fullmatch(digest):
                raise ValueError("Local Ollama model digest invalid")
            return digest
    raise ValueError("Requested Ollama model digest not found")


def reviewer_revision(*paths: Path) -> str:
    """Invalidate when any reviewer/cache implementation bytes change."""
    result = hashlib.sha256()
    for path in paths:
        result.update(path.name.encode("utf-8") + b"\0")
        result.update(path.read_bytes())
        result.update(b"\0")
    return result.hexdigest()


def fingerprint(*, path: str, number: int, total: int, owned: str,
                prompt: str, segment_id: str, model: str,
                digest: str, revision: str) -> str:
    """Bind cache reuse to the complete owned bytes and actual review prompt.

    Prompt includes adjacent context, so a changed neighbor invalidates reuse.
    """
    if (not path or not model or number < 1 or total < number or
            not HEX_16.fullmatch(segment_id) or
            not HEX_64.fullmatch(digest) or not HEX_64.fullmatch(revision)):
        raise ValueError("Invalid reviewer cache identity")
    identity = {
        "schema": VERSION,
        "path": path,
        "part": number,
        "total": total,
        "owned_sha256": sha256_bytes(owned.encode("utf-8")),
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "segment_id": segment_id,
        "model": model,
        "model_digest": digest,
        "reviewer_revision": revision,
    }
    canonical = json.dumps(identity, sort_keys=True, ensure_ascii=True,
                           separators=(",", ":")).encode("utf-8")
    return sha256_bytes(canonical)


def _read_index(path: Path) -> dict[str, str]:
    """Never use partial, malformed, overlarge or forged-shaped cache data."""
    if not path.is_file() or path.is_symlink():
        raise ValueError("Missing or unsafe cache index")
    size = path.stat().st_size
    if size < 2 or size > MAX_CACHE_BYTES:
        raise ValueError("Unexpected cache index size")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"version", "entries"}:
        raise ValueError("Unexpected cache index schema")
    if data["version"] != VERSION or isinstance(data["version"], bool):
        raise ValueError("Unsupported cache index version")
    entries = data["entries"]
    if not isinstance(entries, dict) or len(entries) > MAX_CACHE_ENTRIES:
        raise ValueError("Invalid cache index entries")
    if any(not isinstance(k, str) or not HEX_64.fullmatch(k) or
           not isinstance(v, str) or not HEX_16.fullmatch(v)
           for k, v in entries.items()):
        raise ValueError("Invalid cache index receipts")
    return entries


class VerifiedZeroCache:
    """Trust boundary: cache hit is advisory reuse, never independent approval."""

    def __init__(self, directory: str | None):
        self.path = Path(directory) / "index.json" if directory else None
        self.entries: dict[str, str] = {}
        if self.path is not None:
            try:
                self.entries = _read_index(self.path)
                print(f"SHA_CACHE_LOADED: {len(self.entries)} verified-zero receipts", flush=True)
            except (ValueError, OSError, UnicodeError, json.JSONDecodeError):
                print("SHA_CACHE_MISS: empty, corrupt or unavailable index", flush=True)

    def has(self, key: str, segment_id: str) -> bool:
        return (bool(HEX_64.fullmatch(key)) and bool(HEX_16.fullmatch(segment_id))
                and self.entries.get(key) == segment_id)

    def remember(self, key: str, segment_id: str) -> None:
        if self.path is None:
            return
        if not HEX_64.fullmatch(key) or not HEX_16.fullmatch(segment_id):
            raise ValueError("Refusing malformed review receipt")
        if self.path.exists() and self.path.is_symlink():
            raise ValueError("Refusing symlinked review cache")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.parent.is_symlink():
            raise ValueError("Refusing symlinked review cache directory")
        self.entries[key] = segment_id
        while len(self.entries) > MAX_CACHE_ENTRIES:
            self.entries.pop(next(iter(self.entries)))
        content = json.dumps({"version": VERSION, "entries": self.entries},
                             sort_keys=True, separators=(",", ":")) + "\n"
        if len(content.encode("utf-8")) > MAX_CACHE_BYTES:
            raise ValueError("Review cache index budget exceeded")
        fd, name = tempfile.mkstemp(prefix=".cache-index-", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate hash-only review cache")
    parser.add_argument("--validate-index", required=True)
    args = parser.parse_args()
    try:
        entries = _read_index(Path(args.validate_index))
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError):
        print("SHA_CACHE_SAVE_BLOCKED: absent or unsafe index", flush=True)
        return 2
    print(f"SHA_CACHE_SAFE: {len(entries)} hash-only receipts", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
