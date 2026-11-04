# Field offline preparation on canonical static routes

This repair stays in PR155. Reuse the existing local three-path candidate7a455e3 and independently review it before integration; follow-up fixes preserve that candidate and its HOLD receipt. No Cloudflare deployment, Access/configuration change, new service, permission, GPS action or captured-record write is authorized by this plan.

Owned production paths: `dashboard/sw.js`, `dashboard/field-app.js`, `tests/test_field_offline.py`. The separate root-owned field.html change only removes a stale fixed249/97 display reference; it does not change any tally or approval rule. Existing field-recording tests cover that copy change.

## Observed failures and constraints

[Cloudflare Pages serving documentation](https://developers.cloudflare.com/pages/configuration/serving-pages/) states that HTML URLs redirect to extensionless routes. The current physical shell fetch rejects redirected HTML, and canonical `/field` and `/intake` were absent from field-shell routing. [ServiceWorkerContainer.ready](https://developer.mozilla.org/en-US/docs/Web/API/ServiceWorkerContainer/ready) can wait indefinitely; the old status-message timeout starts only after it resolves. These are software defects, not evidence of successful real-device offline operation.

Preserve physical shell asset names and the existing builder's content-dependent cache identity. Use only a closed mapping of known same-origin canonical/static aliases. Fetch canonical HTML directly; a fallback to the exact legacy static name is allowed only for an explicit404 and must itself be unredirected and valid. Authentication failures, redirects, opaque responses, wrong MIME and unexpected origins are rejected. Known page-role checks reject dashboard/login HTML substituted for field or intake; these are consistency checks, not portable authentication or full-content signatures.

Cache only the static application shell. No raw GPX, logs, tokens, private payload or operational records enter these caches. Canonical and physical field/intake aliases must serve their respective shell offline. Preserve dashboard summary freshness behavior: a require_fresh request cannot silently return old cached data. Keep existing old-good cache preservation when a new install fails.

## Bounded readiness and repair verification

Bound registration, worker readiness and status messaging by one total preparation deadline. Close timers and MessagePorts on success, timeout and synchronous post failure. Give overlapping preparations explicit attempt identity so an older completion cannot overwrite a newer successful state. A preparation failure remains visible as unready; it must not leave the initial checking message forever or imply offline success.

TDD the actual canonical/legacy routing failure, never-settling readiness, stale attempts, timer/port cleanup, unexpected HTML/URL/MIME/Access responses, failed-new-install/old-cache behavior and fresh-summary semantics. Preserve the original candidate's independent counterexamples and use the existing Node/VM harness, Node syntax checks and affected recording/builder regressions. A separate reviewer checks exact committed bytes. New exact-head CI and later approved-main/device verification remain required; no authenticated page visit, fixture or cache test is a real exploration/P0-to-PDCA result.
