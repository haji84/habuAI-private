#!/usr/bin/env python3
"""Fail-closed checks for the owner-approved Codex parallel handoff manifest.

Checks documented cross-lane constraints and source-grounded baseline statuses.
This does not launch Codex, train models, certify science or authorize deployment.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MANIFEST="docs/work/CODEX_STATE_20261025.json"
ALL_LANES={"E","F","M1","M2","M3","V","I"}
ALL_README_DOCS={
    "docs/work/CODEX_PARALLEL_MASTER_20261025.md",
    "docs/work/CODEX_LANES_20261025.md",
    "docs/work/CODEX_MODELS_20261025.md",
    "docs/work/CODEX_ACCEPTANCE_20261025.md",
    "docs/work/CODEX_COPY_PASTE_20261025.md",
}
class ContractError(ValueError):
    pass

def _require(value,reason):
    if not value:
        raise ContractError(reason)

def verify(root:Path=ROOT)->dict:
    root=Path(root)
    state=json.loads((root/MANIFEST).read_text(encoding="utf-8"))
    _require(state["schema_version"]=="habu-codex-parallel-handoff-v1","Unexpected handoff schema")
    _require(state["repo"]=="haji84/habuAI-private","Repo identity mismatch")
    _require(state["target_branch"]=="main","Handoff target branch drift")
    _require(state["authoritative_master_issue"]=="https://github.com/haji84/AI-/issues/1642","Master goal drift")
    _require(state["status"]=="HANDOFF_DOCUMENTED_NOT_EXECUTING","Do not invent launched workers")
    docs=set(state["versioned_documents"])
    _require(docs==ALL_README_DOCS,"Missing or untracked Codex document")
    _require(all((root/p).is_file() for p in docs),"Missing handoff file on checked out branch")
    _require((root/"AGENTS.md").is_file(),"Missing repository AGENTS")
    ag=(root/"AGENTS.md").read_text(encoding="utf-8")
    _require("CODEX_PARALLEL_MASTER_20261025.md" in ag,"Agents not linked to handoff")
    _require("independently corroborated active Habu search" in ag,"AGENTS missing actual-search scientific gate")
    _require("source-bound complete owner capture-outcome" in ag,"AGENTS missing full outcome ledger scientific gate")
    _require(state["latest_verified_prior_evidence"]["owner_august_2026_personal_captures"]==47,"Owner capture correction lost")
    _require(state["latest_verified_prior_evidence"]["through_2026_10_20_personal_capture_cumulative"]==243,"Dated owner cumulative anchor drift")
    _require(state["latest_verified_prior_evidence"]["gps_only_noncapture_review_candidates"]==3491,"Original review candidate count drift")
    _require(state["latest_verified_prior_evidence"]["source_fauna_priority_review_packets"]==75,"Source-first review priority changed")
    _require(state["latest_verified_prior_evidence"]["science_training_negative_rows"]==0,"Fake negative science certification")
    _require(state["latest_verified_prior_evidence"]["science_training_positive_rows"]==0,"Fake positive science certification")
    _require(state["official_performance"]["stage1_name"]=="1km Top10 Recall","Stage1 target changed")
    _require(state["official_performance"]["stage1_recall_minimum"]==0.9 if "stage1_recall_minimum" in state["official_performance"] else state["official_performance"]["threshold"]==0.9,"Stage1 threshold changed")
    _require(state["official_performance"]["current_scientific_status"]=="NOT_VALIDATED","Do not pretend Stage1 passed")
    _require(state["official_performance"]["ultimate_name"]=="100m ±10min","100m formal time precision drift")
    _require(state["official_performance"]["current_scientific_status"]=="NOT_VALIDATED","Do not pretend time precision passed")
    _require(state["latest_verified_main_code"]["champion_state"]=="SANDBOX_ONLY_PRODUCTION_AUTHORITY_BLOCKED","Do not grant production Champion authority")
    _require(state["change_protocol"]["source_data_immutable"] and state["change_protocol"]["original_prediction_immutable"],"Source/ORIGINAL immutability cannot be weakened")
    _require(state["change_protocol"]["full_head_ci_required"] and state["change_protocol"]["post_merge_fresh_main_verification_required"],"CI gates cannot be waived")
    lanes=state["lanes"]
    actual={w["id"] for w in lanes}
    _require(actual==ALL_LANES and len(lanes)==len(ALL_LANES),"Seven distinct worker lanes required")
    _require(all(w["status"]=="NOT_STARTED" for w in lanes),"Handoff does not actually run Codex agents")
    _require(state["gate_G0"]["status"]=="NOT_STARTED","Handoff cannot claim schema freeze done")
    for w in lanes:
        _require(w["first_slice"] and w["paths"],"Lane missing actionable first slice/owned paths: "+w["id"])
        _require(set(w["depends_on"]).issubset(ALL_LANES|{"G0"}),"Unknown lane dependency")
    _require([w["id"] for w in lanes]==["E","F","M1","M2","M3","V","I"],"Unexpected work ownership order")
    _require(len(state["coordinator_queue"])>=5,"No deterministic restartable coordinator tasks")
    for s in state["no_false_claims"]:
        _require(isinstance(s,str) and bool(s),"No-false-claim statement missing")
    ref=(root/"dashboard/baseline_2026.json")
    if ref.exists():
        baseline=json.loads(ref.read_text(encoding="utf-8"))
        august=next((m for m in baseline["months"] if m["key"]=="2026-08"),None)
        _require(august and august["n"]==47,"Current baseline August owner count is not confirmed 47")
    doc=(root/"docs/work/CODEX_MODELS_20261025.md").read_text(encoding="utf-8")
    for required in ("HB-A1","HB-A2","HB-B1","HB-B2","HB-C1","HB-ENS","out-of-universe","Positive-only"):
        _require(required.lower() in doc.lower(),"Model research/evaluation condition missing: "+required)
    prompt=(root/"docs/work/CODEX_COPY_PASTE_20261025.md").read_text(encoding="utf-8")
    for required in ("【ハブAI","E:","F:","M1:","M2:","M3:","V:","I:","Human Gate","GOAL"):
        _require(required.lower() in prompt.lower(),"Incomplete executable Codex prompt: "+required)
    return {
        "status":"CODEX_HANDOFF_CONTRACT_PASS_NO_WORKERS_LAUNCHED",
        "master_issue":state["authoritative_master_issue"],
        "handoff_documents":sorted(docs),
        "lane_count":len(lanes),
        "scientific_verified_negative":0,
        "stage1_scientific_status":"NOT_VALIDATED",
        "production_champion":"BLOCKED",
    }

if __name__=="__main__":
    print(json.dumps(verify(),ensure_ascii=False,indent=2))
