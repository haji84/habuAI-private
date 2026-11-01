"""Frozen synthetic reviewer holdout v1: 20 independently witnessed bug/clean pairs.

Only requirements and code are given to an evaluated model. Labels and witness
results are retained solely in the trusted scorer. This is a synthetic quality
benchmark, NOT general proof of software correctness or production model quality.
Never update v1 to improve a score; create v2 for future additions.
"""
from __future__ import annotations

import hashlib
import json

from quality import new_file_patch

# All arguments, code, requirements and labels are synthetic.
# IMPORTANT: Do not include 'kind', 'expected' or alternative code in prompts.
PAIRS = json.loads(r'''[{"key":"capture_kind","lang":"python","req":"Only events whose kind is exactly capture contribute to a capture total.","args":["sighting"],"expected":0,"bad":"def check(kind):\n    return int(kind != 'roadkill')","good":"def check(kind):\n    return int(kind == 'capture')"},{"key":"species_filter","lang":"python","req":"Only the exact species ハブ counts as a target capture; ヒメハブ must not be counted.","args":["ヒメハブ"],"expected":0,"bad":"def check(species):\n    return int(species in ('ハブ', 'ヒメハブ'))","good":"def check(species):\n    return int(species == 'ハブ')"},{"key":"seven_hour","lang":"python","req":"A local hour before 07:00 belongs to the previous exploration night.","args":[6],"expected":true,"bad":"def check(hour):\n    return hour < 6","good":"def check(hour):\n    return hour < 7"},{"key":"latitude_range","lang":"python","req":"Latitude outside -90 through 90 degrees is invalid.","args":[100],"expected":false,"bad":"def check(lat):\n    return -180 <= lat <= 180","good":"def check(lat):\n    return -90 <= lat <= 90"},{"key":"longitude_range","lang":"python","req":"Longitude outside -180 through 180 degrees is invalid.","args":[200],"expected":false,"bad":"def check(lon):\n    return -360 <= lon <= 360","good":"def check(lon):\n    return -180 <= lon <= 180"},{"key":"event_id_dedup","lang":"python","req":"A previously stored event ID must never be accepted again.","args":[["evt-1"],"evt-1"],"expected":false,"bad":"def check(seen, event_id):\n    return event_id not in seen or event_id == seen[-1]","good":"def check(seen, event_id):\n    return event_id not in seen"},{"key":"boolean_not_count","lang":"python","req":"A boolean is not a valid integer capture count even though bool subclasses int in Python.","args":[true],"expected":false,"bad":"def check(value):\n    return isinstance(value, int)","good":"def check(value):\n    return type(value) is int"},{"key":"confirmed_zero","lang":"python","req":"A zero-capture night must be explicitly confirmed by its owner.","args":[false,0],"expected":false,"bad":"def check(confirmed, count):\n    return count == 0","good":"def check(confirmed, count):\n    return confirmed is True and count == 0"},{"key":"exposure_not_inferred","lang":"python","req":"Missing capture records count as a non-capture observation only when actual search exposure was verified.","args":[false,[]],"expected":false,"bad":"def check(searched, captures):\n    return len(captures) == 0","good":"def check(searched, captures):\n    return searched is True and len(captures) == 0"},{"key":"path_traversal","lang":"python","req":"A relative import path containing a '..' segment is unsafe and must be rejected.","args":["../data"],"expected":false,"bad":"def check(path):\n    return not path.startswith('/')","good":"def check(path):\n    return not path.startswith('/') and '..' not in path.split('/')"},{"key":"capture_limit","lang":"python","req":"An individual daily capture count must be an integer from 0 through 100.","args":[101],"expected":false,"bad":"def check(n):\n    return 0 <= n <= 999","good":"def check(n):\n    return type(n) is int and 0 <= n <= 100"},{"key":"digest_equality","lang":"python","req":"A source receipt is trusted only when its expected digest equals the computed digest exactly.","args":["aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"],"expected":false,"bad":"def check(expected, computed):\n    return len(expected) == len(computed)","good":"def check(expected, computed):\n    return expected == computed"},{"key":"gap_inclusive","lang":"js","req":"An observed GPS gap of at least 300 seconds starts a new track segment.","args":[300],"expected":true,"bad":"function check(seconds) { return seconds > 300; }","good":"function check(seconds) { return seconds >= 300; }"},{"key":"save_ack","lang":"js","req":"The UI may display saved only after the durable save operation succeeds.","args":[false],"expected":false,"bad":"function check(writeSucceeded) { return true; }","good":"function check(writeSucceeded) { return writeSucceeded === true; }"},{"key":"free_route_export","lang":"js","req":"The FREE plan may record GPS but may not export a GPS route.","args":["FREE"],"expected":false,"bad":"function check(plan) { return ['FREE','TRACK','AI','PREMIUM'].includes(plan); }","good":"function check(plan) { return ['TRACK','AI','PREMIUM'].includes(plan); }"},{"key":"owner_confirmation_boolean","lang":"js","req":"Owner confirmation is valid only for the actual boolean true, never a string.","args":["false"],"expected":false,"bad":"function check(value) { return Boolean(value); }","good":"function check(value) { return value === true; }"},{"key":"digest_hex","lang":"js","req":"A 64-character SHA-256 digest must contain hexadecimal characters only.","args":["gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg"],"expected":false,"bad":"function check(value) { return value.length === 64; }","good":"function check(value) { return /^[0-9a-f]{64}$/.test(value); }"},{"key":"distinct_same_time","lang":"js","req":"Events occurring at the same time but having distinct event IDs are not duplicates.","args":[{"time":"T","id":"e1"},{"time":"T","id":"e2"}],"expected":false,"bad":"function check(a, b) { return a.time === b.time; }","good":"function check(a, b) { return a.id === b.id; }"},{"key":"monthly_sum","lang":"js","req":"Total captures across all months equal the sum, not the maximum, of month counts.","args":[[2,3]],"expected":5,"bad":"function check(monthCounts) { return Math.max(...monthCounts); }","good":"function check(monthCounts) { return monthCounts.reduce((a,b)=>a+b,0); }"},{"key":"privacy_export","lang":"js","req":"An aggregate-only public record containing a lat or lon key must not be exported.","args":[{"lat":0}],"expected":false,"bad":"function check(record) { return true; }","good":"function check(record) { return !('lat' in record || 'lon' in record); }"}]''')


def instances() -> list[dict]:
    """Generate 20 positives and 20 negatives with opaque path names."""
    result: list[dict] = []
    for spec in PAIRS:
        for variant, label in (("bad", "positive"), ("good", "negative")):
            suffix = ".py" if spec["lang"] == "python" else ".js"
            filename = hashlib.sha256(
                (spec["key"] + "\x00" + variant).encode("utf-8")
            ).hexdigest()[:16]
            path = "fixture/holdout_" + filename + suffix
            comment = "# " if spec["lang"] == "python" else "// "
            source = comment + "Requirement: " + spec["req"] + "\n" + spec[variant] + "\n"
            result.append({
                "id": filename, "family": spec["key"],
                "language": spec["lang"],
                "path": path, "source": source,
                "patch": new_file_patch(path, tuple(source.rstrip("\n").split("\n"))),
                "label": label, "args": spec["args"],
                "expected_good": spec["expected"],
            })
    if len(result) != 40 or len({x["path"] for x in result}) != 40:
        raise ValueError("Frozen synthetic holdout inventory failed")
    return result


def public_prompt_instance(item: dict) -> dict:
    """Make accidental answer-label exposure to a model difficult."""
    return {"path": item["path"], "patch": item["patch"]}
