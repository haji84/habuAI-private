"""Capture a complete fixed-profile local candidate run; never merges or issues forecasts."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / 'premerge-integration-20261021'
OUT = Path(__file__).resolve().parent

def hashes():
    return {str(p.relative_to(CANDIDATE)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(CANDIDATE.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}

before = hashes()
(OUT / 'hashes-before.json').write_text(json.dumps(before, indent=2) + '\n')
cmd = [str(ROOT / 'habu-ci-venv/bin/python'), '-m', 'unittest', 'discover', '-s', 'tests', '-v']
started = time.monotonic()
with (OUT / 'full-suite.log').open('wb') as stream:
    completed = subprocess.run(cmd, cwd=CANDIDATE, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
elapsed = time.monotonic() - started
after = hashes()
(OUT / 'hashes-after.json').write_text(json.dumps(after, indent=2) + '\n')
raw = (OUT / 'full-suite.log').read_bytes()
log = raw.decode('utf-8')
summaries = re.findall(r'Ran (\d+) tests in ([\d.]+)s', log)
result = {'task_id': 'HABU-WORK-20261021-PREMERGE-INTEGRATION', 'command': cmd,
          'cwd': str(CANDIDATE), 'exit_code': completed.returncode, 'elapsed_seconds': elapsed,
          'summary': summaries[-1] if summaries else None, 'expected_tests': 327,
          'final_ok': log.rstrip().endswith('OK'), 'hashes_unchanged': before == after,
          'changed_paths': sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k)),
          'file_count_before': len(before), 'file_count_after': len(after),
          'log_sha256': hashlib.sha256(raw).hexdigest(),
          'qualification': 'LOCAL_PREMERGE_COMPOSITION_ONLY_NOT_HOSTED_CI_OR_MAIN_E2E'}
result['verified_pass'] = completed.returncode == 0 and result['final_ok'] and before == after and result['summary'][0] == '327'
(OUT / 'suite-exit.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
raise SystemExit(0 if result['verified_pass'] else 1)
