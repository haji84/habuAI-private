#!/usr/bin/env python3
"""Check the Codex handoff is complete, internally consistent, discoverable.

This validates DOCUMENTATION and restart state only. It does not start Codex,
run models, certify training data, or claim production activation.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DOCS=(
    "docs/work/CODEX_PARALLEL_MASTER_20261025.md",
    "docs/work/CODEX_LANES_20261025.md",
    "docs/work/CODEX_MODELS_20261025.md",
    "docs/work/CODEX_ACCEPTANCE_20261025.md",
    "docs/work/CODEX_COPY_PASTE_20261025.md",
)
STATE="docs/work/CODEX_STATE_20261025.json"
FIRST_READ=("AGENTS.md","docs/specs/master-goal-1642-source.md","docs/specs/master-goal-1642.md")

class HandoffContractError(ValueError):
    pass

def require(condition:bool,message:str)->None:
    if not condition:
        raise HandoffContractError(message)

def check_handoff(root:Path=ROOT)->dict:
    root=Path(root)
    require((root/STATE).is_file(),"Missing persisted Codex state")
    state=json.loads((root/STATE).read_text(encoding="utf-8"))
    require(state.get("schema_version")=="habu-codex-parallel-handoff-v1","Unexpected state schema")
    require(state.get("status")=="HANDOFF_DOCUMENTED_NOT_EXECUTING","Handoff cannot impersonate an active Codex run")
    require(state.get("repo")=="haji84/habuAI-private","Wrong canonical repo")
    require(state.get("target_branch")=="main","Invalid integration base")
    require(state.get("authoritative_master_issue")=="https://github.com/haji84/AI-/issues/1642","Missing Master Goal authority")
    require(tuple(state.get("versioned_documents",()))==DOCS,"Codex document manifest drift")
    require(tuple(state.get("first_read",()))==FIRST_READ,"Codex first-read source order drift")
    docs={}
    for name in (*FIRST_READ,*DOCS):
        file=root/name
        require(file.is_file(),"Required source missing: "+name)
        data=file.read_text(encoding="utf-8")
        require(len(data)>100,"Handoff source suspiciously empty: "+name)
        docs[name]=data
        if name in DOCS:
            require(not any(chr(92)+chr(96) in line for line in data.splitlines()),"Escaped code markers break executable Markdown: "+name)
            require(data.count(chr(96)*3)%2==0,"Unbalanced fenced Markdown code blocks: "+name)
    require("CODEX_PARALLEL_MASTER_20261025.md" in docs["AGENTS.md"],"Codex will not find instructions from AGENTS.md")
    require("Unknown is not Negative" in docs["AGENTS.md"],"Missing scientific noncapture guard")
    require("capture-outcome" in docs["AGENTS.md"],"Missing complete capture-outcome requirement")
    entry=docs[DOCS[-1]]
    for token in ("#1642","#32/#33/#46","E:","F:","M1:","M2:","M3:","V:","I:","100m±10分","Human Gate"):
        require(token in entry,"Codex startup prompt missing required token: "+token)
    baseline=state.get("latest_verified_prior_evidence") or {}
    expected={"owner_august_2026_personal_captures":47,
              "through_2026_10_20_personal_capture_cumulative":243,
              "gps_only_noncapture_review_candidates":3491,
              "grouped_review_packets":774,
              "source_fauna_priority_review_packets":75,
              "science_certified_actual_search_units":0,
              "science_training_positive_rows":0,
              "science_training_negative_rows":0}
    for key,value in expected.items():
        require(baseline.get(key)==value,"Historical source safety invariant changed: "+key)
    score=state.get("official_performance") or {}
    require(score.get("threshold")==0.9,"1km Stage1 Top10 Recall minimum silently changed")
    require(score.get("current_scientific_status")=="NOT_VALIDATED","Unproven Stage1 falsely declared complete")
    require(score.get("ultimate_name")=="100m ±10min","Formal final KPI must remain 100m±10min")
    lane_ids=[x["id"] for x in state.get("lanes",[])]
    require(lane_ids==["E","F","M1","M2","M3","V","I"],"Parallel lane roster changed without reviewed contract")
    require(len(lane_ids)==len(set(lane_ids)),"Duplicate worker lane")
    for lane in state["lanes"]:
        require(lane["status"]=="NOT_STARTED","Handoff must not impersonate a running worker")
        require(lane.get("paths") and lane.get("first_slice"),"Missing bounded worker ownership")
    require(len(state.get("coordinator_queue",[]))>=6,"No resumable coordinator task queue")
    require(all(x["status"]=="NOT_STARTED" for x in state["coordinator_queue"]),"Initial coordinator work misrepresented as completed")
    require(set([32,33,46]).issubset(set(state.get("open_prs_to_audit_not_auto_merge",[]))),"Existing prospect PR reuse omitted")
    require(state.get("change_protocol",{}).get("full_head_ci_required") is True,"Exact-head CI gate missing")
    require(state.get("change_protocol",{}).get("source_data_immutable") is True,"Raw evidence immutability missing")
    require(state.get("no_false_claims"),"Missing no-background-work disclaimer")
    return {"status":"PASS_HANDOFF_DOCUMENTS_ONLY","repo":state["repo"],
            "master_issue":state["authoritative_master_issue"],
            "files_checked":len(FIRST_READ)+len(DOCS)+1,
            "lanes":lane_ids,"coordinator_tasks":len(state["coordinator_queue"]),
            "source_evidence_verified_by_this_script":False,
            "codex_workers_started":False,
            "scientific_kpi_measured_by_this_script":False}

def main()->int:
    parser=argparse.ArgumentParser(description="Validate Codex handoff files only")
    parser.add_argument("--root",type=Path,default=ROOT)
    args=parser.parse_args()
    result=check_handoff(args.root)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
