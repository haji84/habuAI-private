#!/usr/bin/env bash
# Cloudflare Pages Git Integration fallback when GitHub-hosted Actions cannot allocate runners.
# IMPORTANT: DO NOT enable this build/deploy until Access protects both production and preview URLs.
set -euo pipefail
python --version
python -m pip install --disable-pip-version-check 'Pillow==11.3.0'
python -m unittest discover -s tests -p test_capture_dashboard.py -v
python -m unittest discover -s tests -p test_verify_pages_access.py -v
python scripts/build_capture_dashboard.py
python - <<'PY'
import json
from pathlib import Path
data=json.loads(Path('dashboard/dist/data/capture_summary.json').read_text(encoding='utf-8'))
assert data['privacy']=='AGGREGATE_ONLY_NO_COORDINATES'
assert data['total']==sum(m['n'] for m in data['months'])
assert data['total']==sum(n['count'] for n in data['nights'])
assert (Path('dashboard/dist')/'_headers').is_file()
assert (Path('dashboard/dist')/'manifest.webmanifest').is_file()
assert 'rel="manifest"' in Path('dashboard/dist/index.html').read_text(encoding='utf-8')
print('CLOUDFLARE_PAGES_BUILD_OK',data['total'],data['asof'])
PY
