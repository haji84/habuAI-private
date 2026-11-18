"""Owner-private NightCount/EventClock research comparison runner.

Private models are read from an owner-only directory outside this public repo.
No model or raw event/GPX data is uploaded to GitHub, and nothing is promoted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from research_nightcount_clock import VERSION, compare_eventclock, compare_nightcount
from research_feature_coverage import analyze_feature_coverage
from private_owner_research import _private_roots, _immutable_report
from private_pdca_intake import (IntakeError, _ReadBudget, _read_bytes, guard_private_path)

SOURCE_LIMIT = 2 * 1024 * 1024


def _unique(pairs):
    value = {}
    for key, row in pairs:
        if key in value:
            raise IntakeError("Duplicate model JSON property")
        value[key] = row
    return value


def _fail_constant(value):
    raise IntakeError("Nonfinite model JSON")


def _read_model(private: Path, relative: str, budget: _ReadBudget):
    if (type(relative) is not str or len(relative) > 512 or "\\" in relative or
            not relative.endswith(".json") or
            PurePosixPath(relative).is_absolute() or
            any(part in ("", ".", "..") for part in relative.split("/"))):
        raise IntakeError("Untrusted private model relative path")
    path = private / relative
    guard_private_path(private, path)
    if not path.is_file():
        raise IntakeError("Private model source unavailable")
    raw = _read_bytes(path, SOURCE_LIMIT, budget)
    sha = hashlib.sha256(raw).hexdigest()
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique,
                           parse_constant=_fail_constant)
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntakeError("Malformed private research model") from exc
    if type(value) is not dict:
        raise IntakeError("Expected private research model object")
    return value, sha


def compare_private_sources(private_root: Path, *,
                            nightcount: str | None = None,
                            eventclock: str | None = None,
                            environment: str | None = None,
                            repo_root: Path = ROOT) -> dict:
    if nightcount is None and eventclock is None:
        raise IntakeError("At least one private model source is required")
    if environment is not None and nightcount is None:
        raise IntakeError("Environment comparison requires a corresponding NightCount source")
    private = _private_roots(Path(repo_root), Path(private_root))
    budget = _ReadBudget(300)
    reports = {}
    input_hashes = {}
    if nightcount is not None:
        count_source, sha = _read_model(private, nightcount, budget)
        reports["nightcount"] = compare_nightcount(count_source)
        input_hashes["nightcount"] = sha
    if eventclock is not None:
        source, sha = _read_model(private, eventclock, budget)
        reports["eventclock"] = compare_eventclock(source)
        input_hashes["eventclock"] = sha
    if environment is not None:
        environmental_source, sha = _read_model(private, environment, budget)
        reports["environment"] = analyze_feature_coverage(
            count_source, environmental_source)
        input_hashes["environment"] = sha
    raw_identity = json.dumps(input_hashes, sort_keys=True, separators=(",", ":")).encode("ascii")
    report_id = hashlib.sha256(raw_identity).hexdigest()
    report = {
        "schema_version": VERSION, "status": "RESEARCH_COMPARISON_COMPLETED",
        "input_byte_sha256": input_hashes,
        "analyses": reports, "official_prediction_issued": False,
        "negative_labels_created": 0, "production_champion_activated": False,
        "scientific_future_validation": "NOT_PERFORMED",
    }
    path = _immutable_report(private, report_id, report, budget)
    content = path.read_bytes()
    # Check the final bytes separately from the original private source reads.
    return {
        "report_id": report_id, "status": report["status"],
        "report_sha256": hashlib.sha256(content).hexdigest(),
        "analyses": {name: {
            "component": name,
            "status": "RETROSPECTIVE_RESEARCH_ONLY",
            "sample_size": (item["heldout_chronological_folds"] if name == "nightcount"
                            else item["evaluation_events"] if name == "eventclock"
                            else item["environment_matched_nights"]),
            "candidate_decisions": ([c["decision"] for c in item["paired_comparisons"]]
                                    if name == "nightcount" else [item["decision"]]
                                    if name == "eventclock" else ["NOT_VALIDATED"]),
        } for name, item in reports.items()},
        "production_champion_activated": False,
    }


def main():
    parser = argparse.ArgumentParser(description="Owner-private model comparison; no deployment")
    parser.add_argument("--private-root", required=True, type=Path)
    parser.add_argument("--nightcount", help="Relative JSON path beneath private root")
    parser.add_argument("--eventclock", help="Relative JSON path beneath private root")
    parser.add_argument("--environment", help="Private existing JMA cooling audit JSON relative path")
    args = parser.parse_args()
    value = compare_private_sources(args.private_root, nightcount=args.nightcount,
                                    eventclock=args.eventclock, environment=args.environment)
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
