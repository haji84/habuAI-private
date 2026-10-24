"""Regression tests for the Codex parallel development handoff, not model accuracy."""
from __future__ import annotations
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from scripts.check_codex_handoff import (
    ROOT, DOCS, FIRST_READ, STATE, HandoffContractError, check_handoff
)

class CodexHandoffContractTests(unittest.TestCase):
    def test_real_repository_handoff_is_complete_but_not_an_active_worker(self):
        r=check_handoff(ROOT)
        self.assertEqual(r["status"],"PASS_HANDOFF_DOCUMENTS_ONLY")
        self.assertEqual(r["lanes"],["E","F","M1","M2","M3","V","I"])
        self.assertEqual(r["coordinator_tasks"],7)
        self.assertFalse(r["codex_workers_started"])
        self.assertFalse(r["scientific_kpi_measured_by_this_script"])

    def copy_fixture(self):
        temp=tempfile.TemporaryDirectory()
        root=Path(temp.name)
        for path in (*DOCS,*FIRST_READ,STATE):
            target=root/path
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/path,target)
        return temp,root

    def test_false_execution_and_fake_scientific_success_rejected(self):
        temp,root=self.copy_fixture()
        try:
            path=root/STATE
            value=json.loads(path.read_text(encoding="utf-8"))
            value["status"]="RUNNING_WITHOUT_REAL_CODEX_RUN"
            path.write_text(json.dumps(value,ensure_ascii=False),encoding="utf-8")
            with self.assertRaisesRegex(HandoffContractError,"impersonate an active"):
                check_handoff(root)
            value["status"]="HANDOFF_DOCUMENTED_NOT_EXECUTING"
            value["official_performance"]["current_scientific_status"]="PASS"
            path.write_text(json.dumps(value,ensure_ascii=False),encoding="utf-8")
            with self.assertRaisesRegex(HandoffContractError,"Unproven Stage1"):
                check_handoff(root)
        finally:
            temp.cleanup()

    def test_missing_file_and_unbalanced_markdown_fail_closed(self):
        temp,root=self.copy_fixture()
        try:
            missing=root/DOCS[2]
            missing.unlink()
            with self.assertRaisesRegex(HandoffContractError,"source missing"):
                check_handoff(root)
            shutil.copyfile(ROOT/DOCS[2],missing)
            with missing.open("a",encoding="utf-8") as fp:
                fp.write(chr(96)*3+"python\n")
            with self.assertRaisesRegex(HandoffContractError,"Unbalanced fenced"):
                check_handoff(root)
        finally:
            temp.cleanup()

    def test_incomplete_lane_roster_and_unknown_label_guard_fail_closed(self):
        temp,root=self.copy_fixture()
        try:
            state_path=root/STATE
            state=json.loads(state_path.read_text(encoding="utf-8"))
            state["lanes"]=state["lanes"][:-1]
            state_path.write_text(json.dumps(state,ensure_ascii=False),encoding="utf-8")
            with self.assertRaisesRegex(HandoffContractError,"lane roster"):
                check_handoff(root)
            shutil.copyfile(ROOT/STATE,state_path)
            agents=root/"AGENTS.md"
            contents=agents.read_text(encoding="utf-8")
            agents.write_text(contents.replace("Unknown is not Negative","Unknown could be Negative"),encoding="utf-8")
            with self.assertRaisesRegex(HandoffContractError,"scientific noncapture"):
                check_handoff(root)
        finally:
            temp.cleanup()

if __name__=="__main__":
    unittest.main()
