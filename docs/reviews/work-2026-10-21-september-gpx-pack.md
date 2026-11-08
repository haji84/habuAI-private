# Independent review — September GPX source evidence pack

Review date: 2026-10-21 UTC. Local candidate: `data-audit-gpx-pack/`; intended Draft PR #43 baseline head `1a95d5c29607cf95ab14cc06730c2010126ebc42`. Scope is the received ZIP, its source receipt and its standard-library restoration tests.

**Verdict: PASS for incoming source-evidence staging. No blocking issue was established in the reviewed three files.** This is byte/source identity and observation consistency evidence only. It does not approve canonical ingestion, additional observations, complete search coverage, Negative/Gold eligibility, historical prediction access, a model change, main merge or successful GitHub CI.

## Independently verified

- Archive: **7,945,041 bytes**, SHA-256 `162b01718cd2916e2b3bdfa61f506e54a63ee4d54e03bd73672cb9804e324ecb`, Git blob SHA-1 `d904bd93b6a5495c7040a22f583234b80a1002f0`.
- Exactly **15 unique GPX members**, totalling **69,910,267 original bytes**. Every member matches its independently downloaded original byte-for-byte and matches the receipt's SHA-256, Git blob SHA-1, CRC32, byte size and compressed size. Full ZIP CRC validation passes. Member paths contain no traversal/absolute/backslash paths; no encryption or symlink member was found.
- For all 15 members, the stored Library listing agrees on Library ID, source file ID, original filename/path, byte size, original Library creation/receipt timestamp and `model_generated=false`. No GPX content was generated or rewritten by this review. Current recovery does not prove September forecast-time availability.
- Parsed all **264,406 timed trackpoints** from the actual XML. For each file, independently recomputed timed/untimed counts, stored first/last timestamps, min/max UTC and JST times and every point's operational night using **07:00 Asia/Tokyo**. All receipt fields agree. Each file's actual point-night set agrees with its attributed capture-log night. Filenames were not used as night evidence. A recorded span remains a point span, without an assertion that it covers an entire exploration session.
- Read the exact September source log from the previously verified corrected validation ZIP (`ee8034…0aee`), rechecked its **96,493 bytes** and SHA-256 `f27a9e06cf89b06a68520365d29630d695d59a96810c95081cfbdb88652bd733`.
- For all **50 existing September capture encounters**, independently extracted the indicated raw-log block, normalized line endings/outer block whitespace, verified the recorded block hash and literal capture timestamp, checked the corrected source identity/class/quantity, and recomputed the linked actual-point distance/time comparison. All nearest-point timestamps and metrics agree with the receipt. The 50 encounters correspond to **51 individuals** in the corrected log; the midnight two-individual encounter remains one encounter check. No new capture observation is created.

## MAIN duplicates

Fetched current MAIN's GPX tree and all six archive manifests independently through GitHub. Compared this pack against **13 direct raw GPX entries plus six archive raw identities** at inspected MAIN `27f4832a23f0a3826ce96b87afb4f2f1c58aa936`.

The only matches are:

| Operational night | Original raw SHA-256 | Handling |
| --- | --- | --- |
| 2026-09-02 | `a31e9ccdbc8f82b19681774546f3ae9a2c2aa8459334f231884e48008cfba307` | Intentional evidence copy; no additive capture intake |
| 2026-09-28 | `2e9fde7aa459fc100abf8014d95635e697a638679cc9df731f4e0f6a80fb62f3` | Intentional evidence copy; preserve existing event/individual identities |

The receipt's other 13 source statuses are explicitly limited to absence from the inspected canonical GPX tree. They do not assert global uniqueness or that observations are new. Other future capture/source overlaps still require canonical identity linking.

## Scientific and restore-test boundaries

Verified receipt-wide `quality_status=BYTE_SOURCE_IDENTITY_VERIFIED_ONLY`, `added_observation_count=0`, and false values for complete search coverage, assigned search role, Negative eligibility, Gold status and canonical promotion. Every member repeats unknown/unassigned role/Negative/Gold status. The receipt explicitly describes the 50 event-to-GPX matches as existing-observation consistency, without claiming forecast accuracy or additional observations.

Reviewed the restoration utility in `tests/test_habu_september_gpx_source_archive.py`. It verifies archive identity, exact member membership/uniqueness, CRC and all member hashes/lengths/Git blobs before writing any restored payload. Tests restore into a new temporary directory with exclusive output creation. Corruption and missing-member fixtures deliberately refresh only the outer ZIP transport hash to exercise the independent inner guards, and confirm no restore directory is created on rejection. This helper remains a test utility, not a production canonical intake executor.

Fresh execution:

`env PYTHONDONTWRITEBYTECODE=1 timeout 60s python -m unittest discover -s tests -p 'test_habu_september_gpx_source_archive.py' -v`

Result: **3/3 tests pass** in 2.716 seconds. The independent full source/point/log audit also passes. No existing raw, capture/individual table, model, Champion or P0/ORIGINAL file was modified. No GitHub write or branch update was performed.

## Evidence

- `data-audit-evidence/independent_september_gpx_pack_review.py`
- `data-audit-evidence/independent-september-gpx-pack-evidence.json` — per-member point/source results and final three-file byte manifest
- `data-audit-evidence/independent-main-gpx-manifests.json`
- `data-audit-evidence/independent-main-gpx-identity-inventory.json`

Exact pushed-head diff/CI and any later canonical promotion remain separate gates. Source identity does not fill observation-effort coverage, train/test timing or forecast-label integrity gaps.
