"""Contract tests for the machine-readable Codex handoff; no workers are launched."""
from __future__ import annotations
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from check_codex_parallel_handoff import verify,ContractError,ALL_README_DOCS,MANIFEST

class ParallelHandoffContractTest(unittest.TestCase):
    def test_complete_handoff_passes_without_claiming_model_training(self):
        report=verify(ROOT)
        self.assertEqual(report["status"],"CODEX_HANDOFF_CONTRACT_PASS_NO_WORKERS_LAUNCHED")
        self.assertEqual(report["lane_count"],7)
        self.assertEqual(report["scientific_verified_negative"],0)
        self.assertEqual(report["stage1_scientific_status"],"NOT_VALIDATED")
        self.assertEqual(report["production_champion"],"BLOCKED")

    def _repo(self):
        folder=tempfile.TemporaryDirectory()
        root=Path(folder.name)
        source_set=ALL_README_DOCS | {MANIFEST,"AGENTS.md","dashboard/baseline_2026.json"}
        for relative in source_set:
            path=root/relative
            path.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/relative,path)
        return folder,root

    def test_owner_count_tamper_fails_closed(self):
        folder,root=self._repo()
        try:
            path=root/MANIFEST
            state=json.loads(path.read_text(encoding="utf-8"))
            state["latest_verified_prior_evidence"]["owner_august_2026_personal_captures"]=45
            path.write_text(json.dumps(state,ensure_ascii=False),encoding="utf-8")
            with self.assertRaisesRegex(ContractError,"Owner capture correction"):
                verify(root)
        finally:
            folder.cleanup()

    def test_fake_started_workers_fails_closed(self):
        folder,root=self._repo()
        try:
            path=root/MANIFEST
            state=json.loads(path.read_text(encoding="utf-8"))
            state["status"]="RUNNING_AUTONOMOUSLY"
            path.write_text(json.dumps(state,ensure_ascii=False),encoding="utf-8")
            with self.assertRaisesRegex(ContractError,"invent launched"):
                verify(root)
        finally:
            folder.cleanup()

    def test_unauthorized_approval_bypass_fails_closed(self):
        folder,root=self._repo()
        try:
            path=root/MANIFEST
            state=json.loads(path.read_text(encoding="utf-8"))
            state["change_protocol"]["full_head_ci_required"]=False
            path.write_text(json.dumps(state,ensure_ascii=False),encoding="utf-8")
            with self.assertRaisesRegex(ContractError,"CI gates"):
                verify(root)
        finally:
            folder.cleanup()

if __name__=="__main__":
    unittest.main()
