# Attachment transport and raw intake

## Goal

Allow ChatGPT Work, GORIQ, a desktop bridge, or another authorized runtime to
save an uploaded GPX/log/database/GIS file into the Habu AI repository without
changing the original bytes.

The transport layer and the canonical intake layer are separate:

1. the runtime materializes/downloads the attachment to a local file;
2. `scripts/ingest_attachment.py` performs byte-preserving intake;
3. the repository workflow handles branch, tests, PR, and eligible continuation.

## Canonical command

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

## What the adapter guarantees

- original source file is read only;
- staged bytes are copied to `incoming/<kind>/`;
- SHA-256 is verified after the copy;
- an evidence JSON record is written under `evidence/raw_intake/`;
- optional promotion writes the same bytes to `data/raw/<kind>/`;
- promotion is verified again by SHA-256;
- repeated ingestion of the same bytes is idempotent;
- a same-name/different-bytes collision is rejected rather than overwritten;
- a supplied expected SHA-256 must match exactly.

This is the repository-side contract needed for the current Chat/Work workflow
and for future GORIQ. A runtime that can materialize an attachment to disk can
use the same adapter without changing the canonical storage rules.

## Important limitation

A transport that cannot expose the uploaded attachment bytes or a local file
path cannot claim the file is stored in `data/raw/`. It may record metadata,
but canonical save is complete only after this adapter verifies the actual
bytes.
