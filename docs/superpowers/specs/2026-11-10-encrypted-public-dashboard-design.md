# Encrypted originals and aggregate-only public dashboard

## Approved intent
Keep application/prediction/dashboard code in the existing Public repository. Preserve raw GPX, exact capture positions and individual logs in authenticated encrypted storage. Supply the browser only deliberate aggregate fields. Reuse PR #160 and the existing AES-256-GCM vault and owner-overlay builder; do not start another model, repository, automation or hosting provider.

## Boundary
An authorized private worker verifies/decrypts the existing vault in memory, applies the existing owner-night overlay, and builds an allowlisted monthly/season summary. A separate public static release contains only `index.html`, `data/public_summary.json`, and security headers. It contains no key, decryption code, individual timestamps, positions, private source filenames, raw notes, GPX or per-event rows. This is public aggregation, not anonymous-data or privacy-math guarantees.

## Approach
Use the current private Python runtime and AES format rather than browser decryption (would expose keys to clients) or privileged Public Actions (not allowed for real originals). Publishing a new web host, changing secrets/permissions, main merge and production Champion promotion remain outside this slice. The public page is an independent safe export of the existing dashboard, not a second capture database.

## Rules
The source tally and separately reported owner total retain their discrepancy. Survey/non-search days are excluded from effort and zero-night counts. Research model sample sizes are distinct from personal capture totals and formal model authorization. Arbitrary private strings never cross the export boundary. Unsafe paths, modified ciphertext/keys, unrecognized fields in the public format, and inconsistent totals fail closed.

## Verification
Run existing overlay tests and new synthetic cryptography/export tests. Then exercise the same private pipeline with the real encrypted archive, adding newly received originals via the existing append-only extension. Read back and decrypt the new snapshot, verify all source hashes, scan the release, render its page, and keep the evidence outside Git. No tests alone imply official scientific model qualification or hosted deployment.
