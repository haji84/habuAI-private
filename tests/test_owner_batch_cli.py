"""Exercise the documented direct CLI without an inherited import path."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class OwnerBatchDirectCLITests(unittest.TestCase):
    def invoke(self,*args,cwd):
        env=dict(os.environ);env.pop('PYTHONPATH',None)
        return subprocess.run([sys.executable,'-B','-X','utf8',
            str(ROOT/'scripts/import_owner_batch.py'),*map(str,args)],
            cwd=cwd,env=env,capture_output=True,text=True,encoding='utf-8')

    def test_documented_help_runs_from_repository_and_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            for cwd in (ROOT,Path(folder)):
                with self.subTest(cwd_kind='repo' if cwd==ROOT else 'external'):
                    result=self.invoke('--help',cwd=cwd)
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertIn('--batch',result.stdout)

    def test_real_dry_run_validates_batch_and_preserves_original_files(self):
        from test_log_intake_ui import LogIntakeTests
        fixture=LogIntakeTests();self.addCleanup(fixture.doCleanups)
        repo=fixture.make_repo()
        before={p.relative_to(repo).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in repo.rglob('*') if p.is_file()}
        with tempfile.TemporaryDirectory() as folder:
            batch=Path(folder)/'batch.json'
            batch.write_text(json.dumps(fixture.batch()),encoding='utf-8')
            result=self.invoke('--batch',batch,'--repo-root',repo,cwd=Path(folder))
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Validated new nights: 1',result.stdout)
        self.assertIn('DRY_RUN_ONLY',result.stdout)
        after={p.relative_to(repo).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in repo.rglob('*') if p.is_file()}
        self.assertEqual(after,before)


if __name__=='__main__':unittest.main()
