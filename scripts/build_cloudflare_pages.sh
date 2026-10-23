#!/usr/bin/env bash
# Cloudflare Pages Git Integration fallback when GitHub-hosted Actions cannot allocate runners.
# IMPORTANT: DO NOT enable this build/deploy until Access protects both production and preview URLs.
set -euo pipefail
if [[ "${HUB_NATURAL_ACCESS_VERIFIED:-}" != "true" ]]; then
  echo "BLOCKED: Explicit Cloudflare Access approval is not set."
  exit 1
fi
# The Access policy and disabled preview deployments MUST be independently
# verified in the Cloudflare account before setting these variables.
if [[ "${HUB_NATURAL_PREVIEWS_DISABLED:-}" != "true" ]]; then
  echo "BLOCKED: Preview deployments must be disabled on Cloudflare Pages."
  exit 1
fi
if [[ "${HUB_NATURAL_BOOTSTRAP_DEPLOYMENT:-}" == "true" ]]; then
  # A production pages.dev hostname is not live before the very first deploy.
  # This flag is ONLY for the first deploy after the Access policy is verified.
  echo "BOOTSTRAP: policy pre-verified; first deployment URL not yet live"
else
  if [[ -z "${HUB_NATURAL_PRODUCTION_URL:-}" ]]; then
    echo "BLOCKED: Production URL is required after initial deployment."
    exit 1
  fi
  python scripts/verify_pages_access.py --production "$HUB_NATURAL_PRODUCTION_URL"
fi
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
