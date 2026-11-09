"""Fail-closed integration of generated Habu PDCA reports after trusted PR CI.

This workflow runs from the default branch on workflow_run completion. It never
checks out or executes untrusted PR code, and cannot merge raw/code/model changes.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

BRANCH = re.compile(r"^pdca/run-([a-f0-9]{64})$")
TITLE = re.compile(r"^PDCA evidence: (\d{4}-\d{2}-\d{2})$")
PATH = re.compile(r"^reports/pdca/(\d{4}-\d{2}-\d{2})/(runs|bridge)/[A-Za-z0-9_./-]+$")


def eligible(event, pr, changes, repository):
    run = event.get('workflow_run') or {}
    if (event.get('action') != 'completed'
            or run.get('name') != 'data-intake-tests'
            or run.get('event') != 'pull_request'
            or run.get('conclusion') != 'success'):
        return False, 'NO_TRUSTED_SUCCESSFUL_CI'
    if ((event.get('repository') or {}).get('full_name') != repository
            or (run.get('head_repository') or {}).get('full_name') != repository):
        return False, 'UNTRUSTED_REPOSITORY'
    number = pr.get('number')
    if not isinstance(number, int) or number not in [x.get('number') for x in run.get('pull_requests') or []]:
        return False, 'NO_VERIFIED_CI_PR_BINDING'
    if pr.get('state') != 'open' or pr.get('draft') is not False:
        return False, 'UNREADY_PR'
    if ((pr.get('base') or {}).get('ref') != 'main'
            or ((pr.get('base') or {}).get('repo') or {}).get('full_name') != repository):
        return False, 'UNEXPECTED_BASE'
    head = pr.get('head') or {}
    if ((head.get('repo') or {}).get('full_name') != repository or head.get('sha') != run.get('head_sha')):
        return False, 'STALE_OR_FORK_HEAD'
    match = BRANCH.fullmatch(head.get('ref') or '')
    title = TITLE.fullmatch(pr.get('title') or '')
    if not match or not title:
        return False, 'NOT_GENERATED_PDCA_REPORT'
    run_id = match.group(1)
    night = title.group(1)
    if pr.get('requested_reviewers') or pr.get('requested_teams'):
        return False, 'REVIEW_PENDING'
    labels = {item.get('name', '').lower() for item in pr.get('labels') or []}
    if labels.intersection({'human-gate', 'do-not-merge', 'security-review', 'hold'}):
        return False, 'HUMAN_GATE'
    if not changes or len(changes) > 2000:
        return False, 'EMPTY_OR_UNBOUNDED_DIFF'
    changed = set()
    for item in changes:
        path = item.get('filename') or ''
        m = PATH.fullmatch(path)
        if not m or m.group(1) != night or item.get('status') not in ('added', 'modified'):
            return False, 'UNSAFE_PATH_OR_CHANGE'
        if path in changed:
            return False, 'DUPLICATE_PATH'
        changed.add(path)
    must_have = {
        f'reports/pdca/{night}/runs/{run_id}/run_manifest.json',
        f'reports/pdca/{night}/runs/{run_id}/evidence_manifest.json',
        f'reports/pdca/{night}/bridge/recovery-{run_id}.json',
    }
    if not must_have.issubset(changed):
        return False, 'MISSING_REPRODUCIBILITY_EVIDENCE'
    return True, 'ALLOW_REPRODUCIBLE_REPORT_ONLY'


def gh_api(repo, token, path, method='GET', payload=None):
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', repo) or not path.startswith('/'):
        raise ValueError('Invalid repository or endpoint')
    data = None if payload is None else json.dumps(payload).encode('utf-8')
    headers = {'Accept': 'application/vnd.github+json',
               'Authorization': 'Bearer ' + token,
               'X-GitHub-Api-Version': '2022-11-28',
               'User-Agent': 'habu-pdca-report-automerge'}
    req = urllib.request.Request(f'https://api.github.com/repos/{repo}{path}',
                                 data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read())


def main() -> int:
    repo = os.environ['GITHUB_REPOSITORY']
    token = os.environ['GH_TOKEN']
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text('utf-8'))
    run = event.get('workflow_run') or {}
    if run.get('conclusion') != 'success' or run.get('event') != 'pull_request':
        print('SKIP: CI is not successful')
        return 0
    associated = run.get('pull_requests') or []
    if len(associated) > 10:
        print('SKIP: unbounded PR association')
        return 0
    for related in associated:
        number = related.get('number')
        if not isinstance(number, int) or number <= 0:
            continue
        pr = gh_api(repo, token, f'/pulls/{number}')
        files = []
        for page in range(1, 22):
            current = gh_api(repo, token, f'/pulls/{number}/files?per_page=100&page={page}')
            files.extend(current)
            if len(current) < 100:
                break
        else:
            print(f'SKIP #{number}: too many files')
            continue
        good, why = eligible(event, pr, files, repo)
        print(f'#{number}: {why}')
        if not good:
            continue
        try:
            result = gh_api(repo, token, f'/pulls/{number}/merge', method='PUT',
                            payload={'sha': pr['head']['sha'], 'merge_method': 'squash',
                                     'commit_title': 'Archive independently verified Habu PDCA report'})
            print(f'#{number}: ' + ('MERGED' if result.get('merged') else 'MERGE_DENIED'))
        except urllib.error.HTTPError as exc:
            print(f'#{number}: MERGE_BLOCKED_HTTP_{exc.code}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
