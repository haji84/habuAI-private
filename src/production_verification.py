"""Bounded consistency checks for supplied, normalized Task8 GitHub facts.

This module performs no transport, file access, scientific reproduction or state
transition. An entirely invented coherent document can pass *consistency*. It
cannot authenticate the source of a fact, authorize production, or replace the
fixed controller's direct authenticated observations and reproduction.

``verify_exact_facts`` assesses merged-intent admission only. Absent/unavailable
facts (including an open PR) are BLOCKED; malformed or contradictory supplied
facts FAIL. Input mappings/lists must be exact builtins, not executable objects.
Page envelopes describe only the collections actually used, not all Actions
history. Job steps are complete embedded lists; numbers need not be contiguous.
``code_sha256`` uses the existing codex-cycle convention: digest(path -> SHA).
Artifact hashes and checkout evidence hashes bind assertions, not authentication.
"""
from __future__ import annotations

from datetime import datetime
import json
import math
import re
import time

from master_contracts import canonical_bytes, digest

MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_NODES = 50_000
MAX_DEPTH = 24
MAX_ITEMS = 4096
MAX_STRING_BYTES = 16_384
_HEX40 = re.compile(r'[a-f0-9]{40}')
_HEX64 = re.compile(r'[a-f0-9]{64}')
_BINDINGS = {'code_sha256', 'policy_sha256', 'model_sha256',
             'evidence_sha256', 'protocol_sha256'}


class _Rejected(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code


def _fail(code):
    raise _Rejected('FAIL', code)


def _blocked(code):
    raise _Rejected('BLOCKED', code)


def _fields(value, expected):
    if value is None:
        _blocked('MISSING_FACT')
    if type(value) is not dict:
        _fail('OBJECT_REQUIRED')
    if set(value) - set(expected):
        _fail('UNEXPECTED_FIELDS')
    if set(expected) - set(value):
        _blocked('MISSING_FIELDS')


def _items(value, *, nonempty=False):
    if value is None:
        _blocked('MISSING_FACT')
    if type(value) is not list:
        _fail('LIST_REQUIRED')
    if len(value) > MAX_ITEMS:
        _blocked('ITEM_LIMIT')
    if nonempty and not value:
        _blocked('EMPTY_REQUIRED_COLLECTION')
    return value


def _integer(value, minimum=1, maximum=2**63 - 1):
    if value is None:
        _blocked('MISSING_FACT')
    if type(value) is not int:
        _fail('INTEGER_REQUIRED')
    if not minimum <= value <= maximum:
        _fail('INTEGER_RANGE')
    return value


def _text(value):
    if value is None:
        _blocked('MISSING_FACT')
    if type(value) is not str or not value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        _fail('TEXT_REQUIRED')
    return value


def _hash(value, *, git=False):
    if value is None:
        _blocked('MISSING_HASH')
    if type(value) is not str or not (_HEX40 if git else _HEX64).fullmatch(value):
        _fail('INVALID_HASH')
    return value


def _path(value, *, prefix=False):
    _text(value)
    path = value[:-1] if prefix and value.endswith('/') else value
    if ('\\' in path or ':' in path or path.startswith('/') or
            any(p in ('', '.', '..') for p in path.split('/'))):
        _fail('NONCANONICAL_PATH')
    return value


def _stamp(value):
    _text(value)
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        _fail('INVALID_TIME')
    if 'T' not in value or result.tzinfo is None or result.utcoffset() is None:
        _fail('AWARE_TIME_REQUIRED')
    return result


def _repository(value, *, current=False):
    _fields(value, {'id', 'full_name', 'default_branch'} | ({'default_head_sha'} if current else set()))
    _integer(value['id'])
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', _text(value['full_name'])):
        _fail('REPOSITORY_NAME')
    _path(value['default_branch'])
    if current:
        _hash(value['default_head_sha'], git=True)
    return {key: value[key] for key in ('id', 'full_name', 'default_branch')}


def _manifest(value):
    result = {}
    for row in _items(value, nonempty=True):
        _fields(row, {'path', 'sha256'})
        name, sha = _path(row['path']), _hash(row['sha256'])
        if name in result:
            _fail('DUPLICATE_PATH')
        result[name] = sha
    return result


def _bindings(value):
    _fields(value, _BINDINGS)
    for sha in value.values():
        _hash(sha)
    return value


def _page(value, check, **scope):
    _fields(value, {'total_count', 'per_page', 'pages'} | set(scope))
    for key, expected in scope.items():
        _integer(value[key])
        if value[key] != expected:
            _fail('COLLECTION_SCOPE')
    total = _integer(value['total_count'], 0, MAX_ITEMS)
    per_page = _integer(value['per_page'], 1, 100)
    pages = _items(value['pages'], nonempty=True)
    result = []
    for index, page in enumerate(pages, 1):
        check()
        _fields(page, {'page', 'has_next', 'items'})
        _integer(page['page'])
        if page['page'] != index:
            _blocked('INCOMPLETE_PAGINATION')
        if type(page['has_next']) is not bool:
            if page['has_next'] is None:
                _blocked('MISSING_FACT')
            _fail('BOOLEAN_REQUIRED')
        rows = _items(page['items'])
        if len(rows) > per_page:
            _fail('PAGE_SIZE')
        if page['has_next'] != (index < len(pages)):
            _blocked('INCOMPLETE_PAGINATION')
        if index < len(pages) and len(rows) != per_page:
            _blocked('INCOMPLETE_PAGINATION')
        result.extend(rows)
    if len(result) < total:
        _blocked('INCOMPLETE_PAGINATION')
    if len(result) > total:
        _fail('COLLECTION_COUNT')
    return result


def _json_snapshot(values, check):
    """Reject executable subclasses/cycles and bound before canonical encoding."""
    pending = [(values, 0, False)]
    active, nodes, approximate_bytes = set(), 0, 0
    while pending:
        check()
        item, depth, leaving = pending.pop()
        if leaving:
            active.remove(id(item))
            continue
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            _blocked('STRUCTURE_LIMIT')
        kind = type(item)
        if kind is dict or kind is list:
            if len(item) > MAX_ITEMS:
                _blocked('ITEM_LIMIT')
            if id(item) in active:
                _fail('CYCLIC_INPUT')
            active.add(id(item))
            pending.append((item, depth, True))
            if kind is dict:
                for key, value in item.items():
                    if type(key) is not str:
                        _fail('JSON_KEY_TYPE')
                    pending.extend(((key, depth + 1, False), (value, depth + 1, False)))
            else:
                pending.extend((value, depth + 1, False) for value in item)
        elif kind is str:
            if len(item) > MAX_STRING_BYTES:
                _blocked('STRING_LIMIT')
            length = len(item.encode('utf-8'))
            if length > MAX_STRING_BYTES:
                _blocked('STRING_LIMIT')
            approximate_bytes += length
        elif kind is int:
            if not -(2**63) <= item < 2**63:
                _fail('INTEGER_RANGE')
            approximate_bytes += 24
        elif kind is float:
            if not math.isfinite(item):
                _fail('NONFINITE_NUMBER')
            approximate_bytes += 24
        elif kind is not bool and kind is not type(None):
            _fail('JSON_BUILTIN_TYPES_REQUIRED')
        if approximate_bytes > MAX_INPUT_BYTES:
            _blocked('BYTE_LIMIT')
    raw = canonical_bytes(values)
    check()
    if len(raw) > MAX_INPUT_BYTES:
        _blocked('BYTE_LIMIT')
    return json.loads(raw)


def _status(row):
    status, conclusion = row['status'], row['conclusion']
    _text(status)
    if status not in ('queued', 'in_progress', 'completed'):
        _fail('CI_STATUS')
    if conclusion not in (None, 'success', 'failure', 'cancelled', 'skipped',
                          'neutral', 'timed_out', 'action_required', 'stale', 'startup_failure'):
        _fail('CI_CONCLUSION')
    if status != 'completed':
        if conclusion is not None:
            _fail('CI_STATUS_CONTRADICTION')
        _blocked('CI_NOT_COMPLETED')
    if conclusion is None:
        _blocked('CI_CONCLUSION_MISSING')


def _success(row):
    _status(row)
    if row['conclusion'] != 'success':
        _fail('REQUIRED_CI_NOT_SUCCESS')


def _verify(facts, intent, policy, check, computed):
    _fields(policy, {'schema_version', 'repository', 'task_id', 'allowed_operations',
        'allowed_merge_methods', 'allowed_paths', 'required_workflows',
        'allowed_reviewer_ids', 'min_approvals', 'max_fact_age_seconds'})
    _fields(intent, {'schema_version', 'repository', 'task_id', 'operation', 'pr_number',
        'base_sha', 'head_sha', 'head_tree_sha', 'merge_tree_sha', 'code_manifest',
        'artifact_bindings', 'ci_runs', 'assessed_at'})
    _fields(facts, {'schema_version', 'observed_at', 'repository', 'pr', 'commits',
        'changed_files', 'ci', 'reviews', 'closures', 'workflow_definitions', 'merge'})
    if (policy['schema_version'] != 'habu-exact-fact-policy-v1' or
            intent['schema_version'] != 'habu-exact-fact-intent-v1' or
            facts['schema_version'] != 'habu-exact-facts-v1'):
        _fail('SCHEMA_VERSION')
    repository = _repository(policy['repository'])
    if _repository(intent['repository']) != repository or _repository(facts['repository'], current=True) != repository:
        _fail('REPOSITORY_IDENTITY')
    if _text(intent['task_id']) != _text(policy['task_id']):
        _fail('TASK_IDENTITY')
    operations = _items(policy['allowed_operations'], nonempty=True)
    methods = _items(policy['allowed_merge_methods'], nonempty=True)
    if (len(set(operations)) != len(operations) or any(x not in ('PROMOTE', 'ROLLBACK') for x in operations)
            or len(set(methods)) != len(methods) or any(x not in ('MERGE', 'SQUASH', 'REBASE') for x in methods)):
        _fail('POLICY_OPERATIONS')
    if _text(intent['operation']) not in operations:
        _fail('OPERATION_SCOPE')
    paths = [_path(x, prefix=True) for x in _items(policy['allowed_paths'], nonempty=True)]
    if len(set(paths)) != len(paths):
        _fail('DUPLICATE_PATH')
    def allowed(path):
        return any(path.startswith(x) if x.endswith('/') else path == x for x in paths)
    assessed, observed = _stamp(intent['assessed_at']), _stamp(facts['observed_at'])
    max_age = _integer(policy['max_fact_age_seconds'], 1, 31_536_000)
    if observed > assessed:
        _fail('FUTURE_FACTS')
    if (assessed - observed).total_seconds() > max_age:
        _blocked('STALE_FACTS')
    code = _manifest(intent['code_manifest'])
    bindings = _bindings(intent['artifact_bindings'])
    if bindings['code_sha256'] != digest(code) or bindings['policy_sha256'] != digest(policy):
        _fail('INTENT_BINDING')
    number = _integer(intent['pr_number'])
    for key in ('base_sha', 'head_sha', 'head_tree_sha'):
        _hash(intent[key], git=True)
    pr = facts['pr']
    _fields(pr, {'number', 'base_repository_id', 'head_repository_id', 'base_branch',
        'head_branch', 'base_sha', 'head_sha', 'author_id', 'state', 'draft', 'merged', 'merge_commit_sha'})
    for key in ('number', 'base_repository_id', 'head_repository_id', 'author_id'):
        _integer(pr[key])
    if (pr['number'] != number or pr['base_repository_id'] != repository['id'] or
            pr['head_repository_id'] != repository['id']):
        _fail('PR_IDENTITY_OR_FORK')
    _path(pr['head_branch'])
    if pr['base_branch'] != repository['default_branch']:
        _fail('PR_BASE_BRANCH')
    if _hash(pr['base_sha'], git=True) != intent['base_sha'] or _hash(pr['head_sha'], git=True) != intent['head_sha']:
        _fail('PR_REVISION_MOVED')
    if type(pr['draft']) is not bool or type(pr['merged']) is not bool:
        if pr['draft'] is None or pr['merged'] is None:
            _blocked('MISSING_FACT')
        _fail('BOOLEAN_REQUIRED')
    if pr['draft']:
        _blocked('PR_DRAFT')
    if _text(pr['state']) not in ('open', 'closed') or pr['merged'] and pr['state'] != 'closed':
        _fail('PR_STATE_CONTRADICTION')
    if not pr['merged']:
        _blocked('PR_NOT_MERGED')
    merged = _hash(pr['merge_commit_sha'], git=True)
    merge_tree = _hash(intent['merge_tree_sha'], git=True)
    merge = facts['merge']
    _fields(merge, {'method', 'prior_default_sha', 'commit_sha'})
    if _text(merge['method']) not in methods:
        _fail('MERGE_METHOD')
    if _hash(merge['commit_sha'], git=True) != merged or _hash(merge['prior_default_sha'], git=True) != intent['base_sha']:
        _fail('MERGE_MAPPING')
    commits = {}
    for row in _items(facts['commits'], nonempty=True):
        check(); _fields(row, {'sha', 'tree_sha', 'parents'})
        sha = _hash(row['sha'], git=True); _hash(row['tree_sha'], git=True)
        parents = [_hash(x, git=True) for x in _items(row['parents'])]
        if sha in commits or len(set(parents)) != len(parents):
            _fail('DUPLICATE_COMMIT_OR_PARENT')
        if sha in parents:
            _fail('COMMIT_CYCLE')
        commits[sha] = row
    def commit(sha):
        if sha not in commits:
            _blocked('COMMIT_FACT_MISSING')
        return commits[sha]
    # Check cycles only in supplied graph; a bounded ancestry proof need not
    # include every ancestor back to repository genesis.
    done, active = set(), set()
    for sha in commits:
        pending = [(sha, False)]
        while pending:
            check(); item, leave = pending.pop()
            if leave:
                active.remove(item); done.add(item); continue
            if item in done or item not in commits:
                continue
            if item in active:
                _fail('COMMIT_CYCLE')
            active.add(item); pending.append((item, True))
            pending.extend((parent, False) for parent in commits[item]['parents'])
    def ancestor(descendant, expected):
        pending, seen, missing = [descendant], set(), False
        while pending:
            check(); sha = pending.pop()
            if sha == expected:
                return
            if sha in seen:
                continue
            seen.add(sha)
            if sha not in commits:
                missing = True
            else:
                pending.extend(commits[sha]['parents'])
        if missing:
            _blocked('ANCESTRY_FACTS_INCOMPLETE')
        _fail('NOT_ANCESTOR')
    commit(intent['base_sha'])
    if commit(intent['head_sha'])['tree_sha'] != intent['head_tree_sha'] or commit(merged)['tree_sha'] != merge_tree:
        _fail('COMMIT_TREE_MAPPING')
    if merge['method'] == 'MERGE':
        if commit(merged)['parents'] != [intent['base_sha'], intent['head_sha']]:
            _fail('MERGE_PARENTS')
    elif merge['method'] == 'SQUASH':
        if commit(merged)['parents'] != [intent['base_sha']]:
            _fail('SQUASH_PARENT')
    else:
        # Rebase replaces the source commits with a linear sequence. Merely
        # finding the base somewhere under an arbitrary merge is insufficient.
        current = merged
        if current == intent['base_sha']:
            _fail('REBASE_PARENT_CHAIN')
        while current != intent['base_sha']:
            check(); parents = commit(current)['parents']
            if len(parents) != 1:
                _fail('REBASE_PARENT_CHAIN')
            current = parents[0]
    ancestor(facts['repository']['default_head_sha'], merged)
    changed = _page(facts['changed_files'], check, repository_id=repository['id'], pr_number=number)
    seen_paths = set()
    for row in changed:
        check(); _fields(row, {'path', 'status', 'previous_path'})
        name = _path(row['path'])
        if name in seen_paths:
            _fail('DUPLICATE_PATH')
        seen_paths.add(name)
        if row['status'] not in ('added', 'modified', 'removed', 'renamed', 'copied'):
            _fail('FILE_STATUS')
        previous = row['previous_path']
        if row['status'] in ('renamed', 'copied'):
            previous = _path(previous)
        elif previous is not None:
            _fail('FILE_STATUS_CONTRADICTION')
        if not allowed(name) or previous is not None and not allowed(previous):
            _fail('CHANGED_PATH_SCOPE')
    if not changed and commit(intent['base_sha'])['tree_sha'] != intent['head_tree_sha']:
        _fail('EMPTY_CHANGED_FILES')
    _verify_ci(facts, intent, policy, commits, commit, check, merged, merge_tree, computed)
    needed = {intent['head_sha'], merged} | {x['tested_sha'] for x in intent['ci_runs']}
    closures = {}
    for row in _items(facts['closures']):
        check(); _fields(row, {'commit_sha', 'files', 'artifact_bindings'})
        sha = _hash(row['commit_sha'], git=True)
        if sha in closures:
            _fail('DUPLICATE_CLOSURE')
        commit(sha)
        if _manifest(row['files']) != code or _bindings(row['artifact_bindings']) != bindings:
            _fail('CLOSURE_BINDING')
        closures[sha] = row
    if needed - set(closures):
        _blocked('CLOSURE_FACT_MISSING')
    _verify_reviews(facts, intent, policy, observed, check, computed)
    computed.update(code_sha256=digest(code), changed_path_count=len(changed),
                    merged_commit_sha=merged, default_branch_head_sha=facts['repository']['default_head_sha'])


def _verify_ci(facts, intent, policy, commits, commit, check, merged, merge_tree, computed):
    definitions = {}
    for row in _items(facts['workflow_definitions']):
        check(); _fields(row, {'commit_sha', 'tree_sha', 'path', 'sha256'})
        sha = _hash(row['commit_sha'], git=True)
        tree = _hash(row['tree_sha'], git=True)
        path, value = _path(row['path']), _hash(row['sha256'])
        if commit(sha)['tree_sha'] != tree:
            _fail('WORKFLOW_DEFINITION_TREE')
        if (sha, path) in definitions:
            _fail('DUPLICATE_WORKFLOW_DEFINITION')
        definitions[sha, path] = value
    requirements = {}
    for row in _items(policy['required_workflows'], nonempty=True):
        _fields(row, {'workflow_id', 'path', 'definition_sha256', 'event', 'checkout_mode', 'required_jobs'})
        key = _integer(row['workflow_id']); _path(row['path']); _hash(row['definition_sha256'])
        if not re.fullmatch(r'\.github/workflows/[^/]+\.ya?ml', row['path']):
            _fail('WORKFLOW_PATH')
        if key in requirements:
            _fail('DUPLICATE_WORKFLOW')
        if row['event'] not in ('pull_request', 'push') or row['checkout_mode'] not in ('HEAD', 'PR_MERGE', 'MERGED'):
            _fail('WORKFLOW_POLICY')
        if row['checkout_mode'] == 'MERGED' and row['event'] != 'push' or row['checkout_mode'] == 'PR_MERGE' and row['event'] != 'pull_request':
            _fail('WORKFLOW_POLICY')
        names = set()
        for job in _items(row['required_jobs'], nonempty=True):
            _fields(job, {'name', 'steps'}); name = _text(job['name'])
            if name in names:
                _fail('DUPLICATE_REQUIRED_JOB')
            names.add(name)
            steps = [_text(x) for x in _items(job['steps'], nonempty=True)]
            if len(set(steps)) != len(steps):
                _fail('DUPLICATE_REQUIRED_STEP')
        requirements[key] = row
    expected = {}
    run_ids = set()
    for row in _items(intent['ci_runs']):
        _fields(row, {'workflow_id', 'run_id', 'attempt', 'tested_sha', 'tested_tree_sha', 'definition_commit_sha'})
        key = _integer(row['workflow_id']); run_id = _integer(row['run_id']); _integer(row['attempt'])
        for name in ('tested_sha', 'tested_tree_sha', 'definition_commit_sha'):
            _hash(row[name], git=True)
        if key in expected or run_id in run_ids:
            _fail('DUPLICATE_RUN')
        expected[key] = row; run_ids.add(run_id)
    if set(expected) - set(requirements):
        _fail('WORKFLOW_IDENTITY')
    if set(requirements) - set(expected):
        _blocked('REQUIRED_CI_MISSING')
    actual = {}
    for row in _items(facts['ci']):
        _fields(row, {'workflow_id', 'workflow_path', 'definition_sha256', 'definition_commit_sha',
            'repository_id', 'run_id', 'attempt', 'latest_attempt', 'event', 'head_branch',
            'pr_number', 'run_head_sha', 'status', 'conclusion', 'jobs'})
        key = _integer(row['workflow_id'])
        if key in actual:
            _fail('DUPLICATE_RUN')
        if key not in requirements:
            _fail('WORKFLOW_IDENTITY')
        actual[key] = row
    if set(requirements) - set(actual):
        _blocked('REQUIRED_CI_MISSING')
    all_job_ids = set()
    for key, rule in requirements.items():
        check(); row, wanted = actual[key], expected[key]
        for name in ('repository_id', 'run_id', 'attempt', 'latest_attempt'):
            _integer(row[name])
        _path(row['workflow_path']); _hash(row['definition_sha256']); _hash(row['definition_commit_sha'], git=True)
        if (row['workflow_path'] != rule['path'] or row['definition_sha256'] != rule['definition_sha256']
                or row['definition_commit_sha'] != wanted['definition_commit_sha']):
            _fail('WORKFLOW_IDENTITY')
        commit(wanted['definition_commit_sha'])
        if wanted['definition_commit_sha'] not in {intent['base_sha'], intent['head_sha'], wanted['tested_sha'], merged}:
            _fail('WORKFLOW_DEFINITION_REVISION')
        definition_key = wanted['definition_commit_sha'], rule['path']
        if definition_key not in definitions:
            _blocked('WORKFLOW_DEFINITION_MISSING')
        if definitions[definition_key] != rule['definition_sha256']:
            _fail('WORKFLOW_DEFINITION_HASH')
        if row['repository_id'] != intent['repository']['id'] or row['run_id'] != wanted['run_id']:
            _fail('RUN_IDENTITY')
        if row['latest_attempt'] < row['attempt']:
            _fail('CI_ATTEMPT_CONTRADICTION')
        if row['latest_attempt'] > row['attempt']:
            _blocked('STALE_CI_ATTEMPT')
        if row['attempt'] != wanted['attempt']:
            _fail('CI_ATTEMPT_MISMATCH')
        if row['event'] != rule['event']:
            _fail('CI_EVENT')
        mode = rule['checkout_mode']
        expected_head = merged if mode == 'MERGED' else intent['head_sha']
        if _hash(row['run_head_sha'], git=True) != expected_head:
            _fail('RUN_HEAD_SHA')
        branch = intent['repository']['default_branch'] if mode == 'MERGED' else facts['pr']['head_branch']
        if row['head_branch'] != branch:
            _fail('RUN_BRANCH')
        if rule['event'] == 'pull_request':
            if _integer(row['pr_number']) != intent['pr_number']:
                _fail('RUN_PR_IDENTITY')
        elif row['pr_number'] is not None:
            _fail('RUN_EVENT_SCOPE')
        tested = commit(wanted['tested_sha'])
        if tested['tree_sha'] != wanted['tested_tree_sha']:
            _fail('TESTED_TREE')
        if mode == 'HEAD' and (wanted['tested_sha'] != intent['head_sha'] or wanted['tested_tree_sha'] != intent['head_tree_sha']):
            _fail('TESTED_HEAD')
        if mode == 'MERGED' and (wanted['tested_sha'] != merged or wanted['tested_tree_sha'] != merge_tree):
            _fail('TESTED_MERGED_COMMIT')
        if mode == 'PR_MERGE' and (tested['parents'] != [intent['base_sha'], intent['head_sha']] or
                wanted['tested_sha'] in (intent['base_sha'], intent['head_sha']) or wanted['tested_tree_sha'] != merge_tree):
            _fail('SYNTHETIC_MERGE_MAPPING')
        _success(row)
        jobs = _page(row['jobs'], check, run_id=row['run_id'], attempt=row['attempt'])
        seen, grouped = set(), {}
        for job in jobs:
            check(); _fields(job, {'id', 'name', 'run_id', 'attempt', 'status', 'conclusion',
                'steps_complete', 'steps', 'checkout'})
            job_id = _integer(job['id']); name = _text(job['name'])
            if job_id in seen or job_id in all_job_ids:
                _fail('DUPLICATE_JOB')
            seen.add(job_id); all_job_ids.add(job_id)
            if _integer(job['run_id']) != row['run_id'] or _integer(job['attempt']) != row['attempt']:
                _fail('JOB_ATTEMPT_SCOPE')
            grouped.setdefault(name, []).append(job)
        for requirement in rule['required_jobs']:
            if requirement['name'] not in grouped:
                _blocked('REQUIRED_JOB_MISSING')
            for job in grouped[requirement['name']]:
                _success(job)
                if type(job['steps_complete']) is not bool:
                    if job['steps_complete'] is None:
                        _blocked('MISSING_FACT')
                    _fail('BOOLEAN_REQUIRED')
                if not job['steps_complete']:
                    _blocked('STEPS_INCOMPLETE')
                checkout = job['checkout']
                _fields(checkout, {'sha', 'tree_sha', 'evidence_sha256'})
                _hash(checkout['evidence_sha256'])
                if _hash(checkout['sha'], git=True) != wanted['tested_sha'] or _hash(checkout['tree_sha'], git=True) != wanted['tested_tree_sha']:
                    _fail('ACTUAL_CHECKOUT_MISMATCH')
                steps, numbers = {}, set()
                for step in _items(job['steps']):
                    _fields(step, {'number', 'name', 'status', 'conclusion'})
                    number = _integer(step['number']); name = _text(step['name'])
                    if number in numbers:
                        _fail('DUPLICATE_STEP')
                    numbers.add(number); steps.setdefault(name, []).append(step)
                for name in requirement['steps']:
                    if name not in steps:
                        _blocked('REQUIRED_STEP_MISSING')
                    for step in steps[name]:
                        _success(step)
    computed['workflow_runs'] = [{key: row[key] for key in ('workflow_id', 'run_id', 'attempt', 'tested_sha', 'tested_tree_sha')}
                                 for row in expected.values()]


def _verify_reviews(facts, intent, policy, observed, check, computed):
    minimum = _integer(policy['min_approvals'], 1, 100)
    allowed = [_integer(x) for x in _items(policy['allowed_reviewer_ids'], nonempty=True)]
    if len(set(allowed)) != len(allowed):
        _fail('DUPLICATE_REVIEWER')
    rows = _page(facts['reviews'], check, repository_id=intent['repository']['id'], pr_number=intent['pr_number'])
    seen, decisions = set(), {}
    for row in rows:
        check(); _fields(row, {'id', 'actor_id', 'state', 'commit_sha', 'submitted_at'})
        review_id = _integer(row['id']); actor = _integer(row['actor_id'])
        if review_id in seen:
            _fail('DUPLICATE_REVIEW')
        seen.add(review_id)
        if row['state'] not in ('APPROVED', 'CHANGES_REQUESTED', 'COMMENTED', 'DISMISSED', 'PENDING'):
            _fail('REVIEW_STATE')
        if row['state'] == 'PENDING':
            if row['submitted_at'] is not None:
                _fail('PENDING_REVIEW_SUBMITTED')
            if row['commit_sha'] is not None:
                _hash(row['commit_sha'], git=True)
            continue
        stamp = _stamp(row['submitted_at']); _hash(row['commit_sha'], git=True)
        if stamp > observed:
            _fail('FUTURE_REVIEW')
        if row['state'] != 'COMMENTED':
            decisions.setdefault(actor, []).append((stamp, row))
    approvals = 0
    for actor, history in decisions.items():
        check(); newest = max(x[0] for x in history)
        latest = [row for stamp, row in history if stamp == newest]
        if len({(row['state'], row['commit_sha']) for row in latest}) != 1:
            _blocked('AMBIGUOUS_EFFECTIVE_REVIEW')
        row = latest[0]
        if row['state'] == 'CHANGES_REQUESTED':
            _blocked('UNRESOLVED_CHANGES_REQUESTED')
        if (row['state'] == 'APPROVED' and row['commit_sha'] == intent['head_sha'] and
                actor in allowed and actor != facts['pr']['author_id']):
            approvals += 1
    if approvals < minimum:
        _blocked('INDEPENDENT_APPROVALS_MISSING')
    computed['effective_independent_approvals'] = approvals


def verify_exact_facts(facts: dict, *, intent: dict, policy: dict, max_seconds: float = 1.0) -> dict:
    """Compute supplied-fact consistency; never authenticate or grant authority.

    Inputs are snapshotted canonically and not modified. Repository facts need
    direct authentication by the existing controller before privileged use;
    science/confirmation/activation remain separate, unimplemented operations.
    A caller-provided assessment time checks internal freshness only.
    """
    result = dict(schema_version='habu-pure-production-fact-consistency-v1',
        fact_consistency='FAIL', reason_codes=[], computed={},
        source_authentication='NOT_ATTESTED_BY_PURE_VALIDATOR',
        scientific_reproduction='NOT_REPRODUCED', production_authorized=False,
        official_issuance_authorized=False)
    try:
        budget_type = type(max_seconds)
        if (budget_type is not int and budget_type is not float) or not 0 < max_seconds <= 5:
            _fail('INVALID_BUDGET')
        deadline = time.monotonic() + max_seconds
        def check():
            if time.monotonic() >= deadline:
                _blocked('DEADLINE')
        facts, intent, policy = _json_snapshot([facts, intent, policy], check)
        result['computed'] = dict(facts_sha256=digest(facts), intent_sha256=digest(intent), policy_sha256=digest(policy))
        _verify(facts, intent, policy, check, result['computed'])
        check()
        result['fact_consistency'] = 'CONSISTENT_NOT_AUTHENTICATED'
    except _Rejected as exc:
        result['fact_consistency'] = exc.status
        result['reason_codes'] = [exc.code]
    except (TypeError, ValueError, OverflowError, RecursionError, RuntimeError):
        # Do not echo source strings, identifiers, paths or exception messages.
        result['reason_codes'] = ['MALFORMED_INPUT']
    return result
