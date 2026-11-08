# Private dashboard intake: implementation and deployment boundary

## Implemented behavior

The existing intake page and `scripts/private_dashboard_chat.py` call the same authenticated API. TXT/LOG and GPX files retain their exact bytes in a content-addressed private SQLite store. The original log parser, GPX validator, owner-batch validator and capture-dashboard builder are reused. Preparation archives originals and reports date/format conflicts; it does not change capture totals. Explicit owner-confirmed night totals are committed together with the new snapshot in one SQLite transaction. A repeated request returns its previous result without adding captures again. All eligible new nights in one upload must be confirmed together; partial confirmation cannot silently discard the remaining nights.

The protected dashboard reads the committed snapshot at `/data/capture_summary.json`. Its existing intake UI gains GPX selection, private upload, per-night confirmation, held reasons, and post-write readback. Visible home pages check the revision every 30 seconds. Private summary, home HTML and API responses are network-only and not placed in the service-worker cache. Offline field-recorder assets and IndexedDB recording remain separate.

These are operational owner totals, not certified spatial observations, model fitting or prediction updates. GPX timestamps do not certify full-night coverage, active search, zero captures, or event-to-location matches. Existing/historical dates and ambiguous source dates are held for the established review/correction process. This change does not automatically import the existing private Library backlog.

## FIELD rapid recording and guarded deferred sync (2026-11-08)

**Problem:** The previous mobile field page required a long series of selects/inputs to record one sighting or Habu capture. That is unsuitable for field use.

The existing `dashboard/field.html` now offers large, one-touch actions for *本人ハブ捕獲*, Habu sighting, roadkill, missed Habu and *他者捕獲*, plus a small wildlife grid. Fine-grained inputs remain available under a collapsed details section. The action calls the same `field-app.js` event-save handler and its tested serialized IndexedDB writer, rather than a competing GPS or event store. Current timestamp and the latest **actually measured GPS** point (only if not older than 90 seconds) are retained. No invented coordinate, person ownership, capture or Negative is created; operation while driving is not advised.

The established native iPhone app additionally offers one-tap capture/sighting/roadkill/missed Habu buttons through the existing native recorder's `addObservation` method, preserving the previously verified locked-screen GPS code. Its prior 30-minute-plus real-phone proof is not invalidated or repeated solely because the input UI changed.

**Private auto-upload:** The field page adds a separate opt-in `field-sync.js` adapter. Consent and per-session receipts are stored in IndexedDB, not localStorage. Only **completed**, locally validated sessions are eligible. On a visible page or network return, the adapter first checks that the same-origin protected API is not anonymously readable, then verifies the expected `habu-private-dashboard-status-v1` / `PRIVATE_DURABLE_STORE` response. Only after those gates does it transmit field-log and measured GPX bytes to the existing `/api/private-intake/prepare` endpoint. Duplicate receipts/previously applied sessions are skipped and recoverable failures keep local originals. A separate explicit *post-exploration confirmation* is required before calling the existing atomic `apply` endpoint for personally caught Habu night totals, which are read back; no date/capture count is inferred from GPS. A received original is **not** yet an approved dashboard aggregate or official training label.

**Critical operating limitation:** The current production `hub-natural-private.pages.dev` is static Pages and has **no authenticated persistent private write backend attached**. Thus enabling the UI checkbox on that site must show `同期未接続` and send no raw bytes. There is no general-purpose free GitHub-hosted server here. To complete production auto-sync, an authorized, persistent private backend plus trusted identity and storage still needs deployment/verification without Vercel, ZBook or new paid services. Do not claim this is already operational, and do not publish source GPS/TXT to public GitHub.

An optional `ハブログ＋GPXをまとめて共有` button invokes the platform's *user-controlled* share sheet as a no-server fallback, not an automatic ChatGPT upload. The browser/app may support or reject multi-file sharing, and reception needs owner confirmation. Browser PWA locked-screen GPS remains unguaranteed; existing native-phone recording remains the correct continuity source.

## Deployment is not completed by this PR

A static website cannot execute this WSGI application or store private uploads. Required before enabling live writes:

1. A trusted Python 3.12+ runtime with Node.js available, behind the owner's verified HTTPS protection. Route the dashboard and `/api/private-intake/*` through this application at the same origin. Deploy all current dashboard assets. Do not send uploads through a public GitHub issue, workflow log, artifact, or git data file.
2. A durable private local volume outside both the code checkout and the served dashboard directory. SQLite is for one host with local storage, not ephemeral serverless or a network-shared filesystem. Restrict the service account, protect backups, and test recovery. POSIX modes are set; Windows ACLs require separate verification. Filesystem checks assume no adversarial process with access to the service account and are not OS sandboxing.
3. Configure `HABU_PRIVATE_ROOT`, `HABU_DASHBOARD_ORIGIN` (HTTPS scheme and host only, no trailing slash), and a securely generated `HABU_DASHBOARD_TOKEN` of at least 32 printable ASCII characters in the runtime's secret environment. Never place the token in source, chat messages, URLs, or browser JavaScript. Browser authentication uses username `owner` and that token; the Chat client uses Bearer authentication. Existing provider login is not automatically mapped to this application. Verify both layers and the permitted owner before deployment.
4. Serve the factory `scripts.private_dashboard_api:create_app()` using an approved production WSGI server. The HTTPS reverse proxy must supply the correct WSGI scheme and Host, limit request bodies to at most 66 MiB, enforce body/read/worker timeouts and rate limits, and not log request bodies or authorization headers. The application does not trust arbitrary forwarded-header assertions. Production server/proxy provisioning and provider charges are outside this PR.
5. Run one authorized live upload, authenticated readback, unauthorized denial, duplicate retry, stale-tab rejection, and restart/recovery test. Verify the actual phone dashboard displays the new revision. No live-production success is claimed from local tests.

The constructor freezes the existing canonical aggregate inputs as the seed on first startup. A later code deployment does not silently replace that seed. Baseline changes and historical corrections require an explicitly reviewed migration, not deletion/recreation of the database.

## Native iPhone Habu-log + GPX handoff (2026-11-08)

The previously implemented iOS recorder's screen-off GPS path remains unchanged and the owner's completed long-duration real-device evidence is retained. This PR adds a **derived Japanese `ハブログ` TXT** export from the *same saved JSONL session* used for the existing GPX. `HabuLogExporter.txt` emits the literal JST observation times, start/end events, capture/sighting/roadkill, count, species, optional note and explicitly recorded actor. An older observation with no actor stays **未確認**, never inferred as a personally caught Habu. Multi-line note contents cannot inject a fake event. GPS gaps remain a separate diagnostics event, not proof of search or a scientific negative. No GPS coordinate is inferred for an observation, and exporting TXT does not change the JSONL original or GPX.

The iPhone field UI offers **ハブログTXT**, existing **GPXを作成**, and **ハブログとGPXをまとめて作成** (two-file owner-directed Share Sheet). Both files can be voluntarily delivered into the user's private Chat conversation as a current manual handoff, or selected in the dashboard's existing log/GPX intake screen when its protected write backend is actually connected. The PR #92 private intake service supports `log` and `gpx` bytes and owner confirmation. Sharing is not unattended Chat ingestion, permanent Library archival, completed model training or canonical/dashboard synchronization.

**No new Vercel service, ZBook resident service, paid cloud store, or raw GPS write to public GitHub is permitted.** In the present static-only Pages production, the private WSGI/SQLite ingest/commit runtime is not deployed, so the native app should show that *local export ≠ synced dashboard*. The next deployment gate remains a real access-controlled durable private endpoint, authenticated Chat bridge, and a readback-verified live aggregate without modifying the existing original/raw data. Changing only the TXT exporter must not force another 30-minute owner GPS trial.

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
