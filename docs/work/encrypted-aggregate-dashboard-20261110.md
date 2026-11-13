# Public code, encrypted originals, aggregate-only dashboard

The owner approved keeping the repository public and showing aggregate capture statistics. This implementation separates those public values from raw GPX, exact capture locations, individual event times, original logs, models containing private location detail, and decryption keys.

## Implemented path

Private authenticated archive -> legacy AES-256-GCM verification -> source-hash-bound base and owner overlay -> existing `apply_overlay` -> strict `project_public_summary` -> three-file static release.

`tools/dashboard_release/habu_library_vault_tool.py` is a byte-identical copy of the already verified private vault tool, SHA-256 `d3be93d8cb642166665f3bb454988d80874c2a87a80c01055e50a0dd61c3eca3`. Its legacy create helper expects 19 files; extending real snapshots continues to use the existing private `habu_private_vault_extend.py`, not a replacement format. Never use the sample creation helper to overwrite existing source backups.

The new bridge refuses Public Actions execution, missing/incorrect hashes, wrong keys or modified ciphertext, private inputs inside Git, symlink input paths, inconsistent owner totals and conflicting output directories. It decrypts required JSONs in memory; other originals are verified and not exported. Public input validation is an allowlist, not a blacklist of coordinate field names.

## Private invocation

Run only in the authorized private runtime. No key value belongs in a command argument or log; `--key-file` is an access-controlled file path outside Git.

```sh
python tools/dashboard_release/vault_dashboard.py \
  --archive /private/current.habuenc.zip \
  --key-file /private/key-custody/owner-key.json \
  --base-entry 2026/11/APPROVED-BASE.txt \
  --overlay-entry 2026/11/APPROVED-OVERLAY.txt \
  --expected-archive-sha256 ARCHIVE_SHA256 \
  --expected-base-sha256 BASE_SHA256 \
  --expected-overlay-sha256 OVERLAY_SHA256 \
  --template dashboard/public-summary.html \
  --destination /separate/public-release
```

The placeholders are not real source bindings. The private receipt and latest Library handoff identify actual immutable entries. JSON inputs stored under `.txt` names are a packaging compatibility choice, not changed event dates or altered raw bytes. A source-provenance record distinguishes original uploads, derived ledgers, model snapshots, and the derived historical dashboard base.

## What may be served

Only `index.html`, `data/public_summary.json`, and `_headers` from the verified release directory. The public JSON contains monthly/annual totals, counts of search nights, model sample sizes and an explicit unresolved-total status. It deliberately contains no day-by-day activity calendar, raw notes, local names, coordinates, individual times, private paths, source hashes or credentials. The page does not fetch private inputs, decrypt data, use a private service worker, or contact third parties. Host-specific security headers must be configured at deployment; the HTML also carries its CSP.

Do not deploy the entire repo, private dashboard directory, source archive, or working directory. Generated aggregate values are plaintext public information; encryption of originals does not make the displayed values secret or erase older plaintext already present in repository history.

## Actual verification in this session

- Original authenticated snapshot: 19 files. Preserved unchanged.
- Appended snapshot: 15 additional source/derived files, 34 total. Existing key reused, previous ciphertext members preserved. All 15 added entries independently restored and compared with source SHA-256.
- New snapshot uploaded to private Library; downloaded copy authenticated again, 34 files verified. Generated HTML and JSON matched their uploaded copies byte-for-byte.
- Public page shows monthly capture total and historical total with the separate owner-reported total. Their discrepancy is retained, not forced into equality.
- Local 36/36 targeted tests passed: 27 export/crypto tests + 9 existing overlay tests. Synthetic keys only in CI. Local cryptography 46.0.4; CI checks 50.0.2 independently.
- Desktop/mobile rendering: no JavaScript errors, no horizontal overflow, no browser network requests or decryption. This was an in-memory browser check, not a hosted deployment test.

## Not claimed

Main merge, live site switch, unattended device upload, independent security review, offline owner key backup, historical public-plaintext removal, formal G0 learning or Champion promotion. A key and its encrypted archive remain under the same private Library account, so account compromise remains a custody risk. The new export path does not itself mitigate old repository history.
