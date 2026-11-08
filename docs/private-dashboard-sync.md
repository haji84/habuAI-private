# Private dashboard intake: implementation and deployment boundary

## Implemented behavior

The existing intake page and `scripts/private_dashboard_chat.py` call the same authenticated API. TXT/LOG and GPX files retain their exact bytes in a content-addressed private SQLite store. The original log parser, GPX validator, owner-batch validator and capture-dashboard builder are reused. Preparation archives originals and reports date/format conflicts; it does not change capture totals. Explicit owner-confirmed night totals are committed together with the new snapshot in one SQLite transaction. A repeated request returns its previous result without adding captures again. All eligible new nights in one upload must be confirmed together; partial confirmation cannot silently discard the remaining nights.

The protected dashboard reads the committed snapshot at `/data/capture_summary.json`. Its existing intake UI gains GPX selection, private upload, per-night confirmation, held reasons, and post-write readback. Visible home pages check the revision every 30 seconds. Private summary, home HTML and API responses are network-only and not placed in the service-worker cache. Offline field-recorder assets and IndexedDB recording remain separate.

These are operational owner totals, not certified spatial observations, model fitting or prediction updates. GPX timestamps do not certify full-night coverage, active search, zero captures, or event-to-location matches. Existing/historical dates and ambiguous source dates are held for the established review/correction process. This change does not automatically import the existing private Library backlog.

## Deployment is not completed by this PR

A static website cannot execute this WSGI application or store private uploads. Required before enabling live writes:

1. A trusted Python 3.12+ runtime with Node.js available, behind the owner's verified HTTPS protection. Route the dashboard and `/api/private-intake/*` through this application at the same origin. Deploy all current dashboard assets. Do not send uploads through a public GitHub issue, workflow log, artifact, or git data file.
2. A durable private local volume outside both the code checkout and the served dashboard directory. SQLite is for one host with local storage, not ephemeral serverless or a network-shared filesystem. Restrict the service account, protect backups, and test recovery. POSIX modes are set; Windows ACLs require separate verification. Filesystem checks assume no adversarial process with access to the service account and are not OS sandboxing.
3. Configure `HABU_PRIVATE_ROOT`, `HABU_DASHBOARD_ORIGIN` (HTTPS scheme and host only, no trailing slash), and a securely generated `HABU_DASHBOARD_TOKEN` of at least 32 printable ASCII characters in the runtime's secret environment. Never place the token in source, chat messages, URLs, or browser JavaScript. Browser authentication uses username `owner` and that token; the Chat client uses Bearer authentication. Existing provider login is not automatically mapped to this application. Verify both layers and the permitted owner before deployment.
4. Serve the factory `scripts.private_dashboard_api:create_app()` using an approved production WSGI server. The HTTPS reverse proxy must supply the correct WSGI scheme and Host, limit request bodies to at most 66 MiB, enforce body/read/worker timeouts and rate limits, and not log request bodies or authorization headers. The application does not trust arbitrary forwarded-header assertions. Production server/proxy provisioning and provider charges are outside this PR.
5. Run one authorized live upload, authenticated readback, unauthorized denial, duplicate retry, stale-tab rejection, and restart/recovery test. Verify the actual phone dashboard displays the new revision. No live-production success is claimed from local tests.

The constructor freezes the existing canonical aggregate inputs as the seed on first startup. A later code deployment does not silently replace that seed. Baseline changes and historical corrections require an explicitly reviewed migration, not deletion/recreation of the database.

## Chat-side entry

A trusted active Chat runtime must materialize the user's original files and invoke:

```sh
python scripts/private_dashboard_chat.py --log /private/incoming/log.txt --gpx /private/incoming/track.gpx
```

This archives/prepares and reports a receipt. To apply, the same invocation can include one `--confirm YYYY-MM-DD=COUNT` per new operational night, but only for actual owner-confirmed personal Habu captures and confirmed search nights. Do not infer these arguments from GPX or the parser's capture-hint count. No confirmation means no aggregate write. Repeated files preserve the same receipt. Failed or ambiguous inputs return a held/error result, not success.

The CLI is an executable adapter, not a registered ChatGPT connector, attachment event subscription, or unattended Library bridge. Endpoint/credentials and invocation from the actual Chat environment must still be connected and verified. Do not report that merely posting to Chat already updates production.

## API contract

- GET `/api/private-intake/status`: committed revision, asof and service mode.
- POST `/api/private-intake/prepare`: `{files:[{kind:"log"|"gpx",content_b64:"..."}],channel:"chat"|"dashboard"}`.
- POST `/api/private-intake/apply`: `{receipt_id,batch,expected_revision}` using the existing `habu-local-intake-review-batch-v1` schema.
- GET `/data/capture_summary.json`: existing dashboard schema, generated from committed private inputs.

Limits: 12 sources/request, 12 MiB/source, 48 MiB total decoded sources, 12 MiB combined log text, 128 parsed nights, 2 GiB stored raw sources. Non-UTF-8 logs, invalid GPX, contradictory nights and ambiguous event times are held. A temporary parser outage is retryable and does not create a permanently conflicting receipt. SHA deduplication is source identity, not proof of distinct biological individuals. Same-night disagreements never become extra captures automatically.

## Verification record

Local code-only workspace: Python unittest discovery executed 34 distinct tests with 0 failures and 0 skips. Tests use synthetic sources and a synthetic seed, not private owner data. Two tests use a real loopback HTTP server and the actual urllib client; they verify upload/apply/readback and authentication denial. Other tests exercise the real SQLite transaction, existing builder and parser, including concurrent retries, rollback, cross-channel deduplication, immutable raw bytes, 07:00 boundary, path containment, GPX conflicts and multi-night confirmation.

Chromium at a 390x844 viewport exercised the rendered existing intake page with real file selection, upload, confirmation, apply, readback and duplicate disablement, with no browser JavaScript errors. Browser network navigation is blocked by the execution environment's administrator policy, so that UI test used an in-process bridge to the actual WSGI application and store. This is not a real browser-network or production-phone E2E. HTTP transport was tested separately as described above.

Self-review found and reproduced three defects before fixing them: `..` path containment, partial multi-night application, and permanent receipts caused by transient parser failures. Fresh independent security review, exact-head CI, production routing/identity/volume verification, and live owner-device verification remain separate acceptance gates. No new scheduled task, provider provisioning, production merge or production model activation is performed by this PR.
