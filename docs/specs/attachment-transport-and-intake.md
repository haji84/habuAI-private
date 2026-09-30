# Attachment transport and raw intake

## Goal

Allow ChatGPT, ChatGPT Work, GORIQ, a desktop bridge, or another authorized
runtime to save an uploaded GPX/log/database/GIS file into the Habu AI
repository without changing the original bytes.

The transport layer and the canonical intake layer are separate.

### Preferred path: runtime can materialize the attachment

1. the runtime materializes/downloads the attachment to a local file;
2. `scripts/ingest_attachment.py` performs byte-preserving intake;
3. the repository workflow handles branch, tests, PR, and eligible continuation.

### Text-only fallback: runtime can read bytes but GitHub transport accepts text only

Use `scripts/text_safe_byte_archive.py`.

The fallback converts the raw attachment into:

`raw bytes -> XZ -> base64 -> deterministic UTF-8 text parts`

The repository stores a manifest plus `part_*.b64` files. Restoration verifies
the compressed SHA-256 and the original raw SHA-256 before the output is
accepted. The original filename, byte count, source, source reference, and kind
remain in the manifest.

This is the supported fallback for Chat-style transports that can inspect the
attachment but cannot send an arbitrary binary Git blob directly. It avoids
claiming success from metadata alone while still preserving the exact original
bytes in a reconstructable form.

## Canonical direct-intake command

```bash
python scripts/ingest_attachment.py \
  --file "/path/to/2026-09-28-探索.gpx" \
  --repo-root . \
  --kind gpx \
  --source chat \
  --source-ref "conversation-file-id" \
  --expected-sha256 "<known sha256>" \
  --promote
```

Windows:

```powershell
.\scripts\ingest-attachment.ps1 \
  -File "C:\path\2026-09-28-探索.gpx" \
  -Kind gpx \
  -Source chat \
  -SourceRef "conversation-file-id" \
  -ExpectedSha256 "<known sha256>" \
  -Promote
```

## Text-safe archive commands

Create an archive:

```bash
python scripts/text_safe_byte_archive.py pack \
  --file "/path/to/2026-09-28-探索.gpx" \
  --archive-dir "data/raw/attachment_archives/gpx/<sha256>" \
  --kind gpx \
  --source chat \
  --source-ref "conversation-file-id"
```

Restore and verify it:

```bash
python scripts/text_safe_byte_archive.py restore \
  --archive-dir "data/raw/attachment_archives/gpx/<sha256>" \
  --output "/tmp/2026-09-28-探索.gpx"
```

A successful restore is authoritative only when the restored raw byte length and
SHA-256 match the manifest.

## What direct intake guarantees

- original source file is read only;
- staged bytes are copied to `incoming/<kind>/`;
- SHA-256 is verified after the copy;
- an evidence JSON record is written under `evidence/raw_intake/`;
- optional promotion writes the same bytes to `data/raw/<kind>/`;
- promotion is verified again by SHA-256;
- repeated ingestion of the same bytes is idempotent;
- a same-name/different-bytes collision is rejected rather than overwritten;
- a supplied expected SHA-256 must match exactly.

## What the text-safe fallback guarantees

- original bytes are never normalized as text;
- XZ compression is lossless;
- base64 parts contain only transport-safe ASCII;
- missing or altered parts are rejected;
- compressed SHA-256 is checked before decompression;
- raw byte length and raw SHA-256 are checked after decompression;
- arbitrary binary content, CRLF, BOMs, embedded NULs, and non-text bytes survive
  round-trip unchanged.

The 2026-09-28 GPX already demonstrates the same principle through the earlier
line-preserving GPX archive. The generic byte archive supersedes that
GPX-specific transport for future attachments; the existing line archive remains
valid evidence and is not rewritten or deleted.

## Completion rule

A transport must not claim canonical save based on metadata alone.

Save is complete when either:

1. direct intake verifies the actual bytes in the canonical raw path; or
2. a repository-stored text-safe archive restores byte-for-byte to the expected
   raw size and SHA-256 under automated verification.

