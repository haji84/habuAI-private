"""Locked, synthetic quality calibration for the CPU source reviewer.

No real GPS, capture points, network calls, or production records are in fixtures.
This smoke suite catches obvious false positives/misses; it cannot prove
production precision, recall, or formal GitHub approval.
"""
from __future__ import annotations

import json

from grounding import added_source_lines, ground_candidates


def new_file_patch(path: str, lines: tuple[str, ...]) -> str:
    return (f"diff --git a/{path} b/{path}\n"
            f"new file mode 100644\n--- /dev/null\n+++ b/{path}\n"
            f"@@ -0,0 +1,{len(lines)} @@\n"
            + "".join("+" + line + "\n" for line in lines))


def case(name: str, kind: str, path: str, lines: tuple[str, ...],
         topic_words: tuple[str, ...] = ()) -> dict:
    return {
        "name": name, "kind": kind, "path": path,
        "patch": new_file_patch(path, lines),
        "source": "\n".join(lines) + "\n", "topic_words": topic_words,
    }


CASES = (
    case("stale_prestart_defect", "positive", "fixture/stale_fix.py", (
        "def should_record(sample_time_ns, tracking_start_ns):",
        "    # Requirement: never accept fixes measured before tracking began.",
        "    grace_period_ns = 5_000_000_000",
        "    return sample_time_ns >= tracking_start_ns - grace_period_ns",
        "",
    ), ("before", "prior", "pre-start", "earlier", "stale", "old", "開始前", "古い")),
    case("unknown_owner_defaults_to_self", "positive", "fixture/owner.js", (
        "function normalizeOwner(item) {",
        "  return item.owner === 'other' ? 'other' : 'self';",
        "}",
    ), ("owner", "self", "missing", "default", "unknown", "本人", "他者")),
    case("correct_prestart_guard", "negative", "fixture/correct_fix.py", (
        "def should_record(sample_time_ns, tracking_start_ns):",
        "    return sample_time_ns >= tracking_start_ns",
    )),
    case("correct_owner_validation", "negative", "fixture/correct_owner.js", (
        "function normalizeOwner(item) {",
        "  if (item.owner !== 'self' && item.owner !== 'other') throw Error('Invalid owner');",
        "  return item.owner;",
        "}",
    )),
    case("defined_callback_not_missing", "negative", "fixture/handlers.js", (
        "function onFix(position) { return position; }",
        "function gpsStart(api) { return api.watchPosition(onFix); }",
    )),
    case("complete_labeled_html", "negative", "fixture/html.html", (
        "<header><h1>Dashboard</h1></header>",
        '<button type="button" aria-label="Save">Save</button>',
    )),
)


def evaluate(model_call, parse_findings, original_reply: str | None = None) -> dict:
    """Require quoted real source for bugs, and raw-zero for correct code."""
    detected = clean = false_alarms = ungrounded = 0
    positives = negatives = 0
    for fixture in CASES:
        if original_reply is not None and fixture["name"] == "stale_prestart_defect":
            raw = original_reply
        else:
            raw = model_call(fixture["path"], fixture["patch"])
        response = json.loads(raw)
        if not isinstance(response, dict) or not isinstance(response.get("findings"), list):
            raise ValueError("Invalid quality calibration response")
        count = len(response["findings"])
        parsed = parse_findings(raw, fixture["path"])
        grounded, _ = ground_candidates(
            parsed, fixture["source"], added_source_lines(fixture["patch"])
        )
        if fixture["kind"] == "positive":
            positives += 1
            narrative = " ".join(
                str(f.get("problem", "")) + " " + str(f.get("impact", ""))
                for f in grounded
            ).lower()
            if count and grounded and any(word in narrative for word in fixture["topic_words"]):
                detected += 1
            else:
                ungrounded += 1
        else:
            negatives += 1
            if count == 0:
                clean += 1
            else:
                false_alarms += count
    passed = (detected == positives and clean == negatives
              and positives >= 2 and negatives >= 3)
    return {
        "cases": len(CASES),
        "positives": positives, "positives_grounded": detected,
        "negatives": negatives, "clean_correct": clean,
        "false_alarms": false_alarms,
        "positive_miss_or_ungrounded": ungrounded,
        "passed": passed,
        "not_production_accuracy": True,
    }
