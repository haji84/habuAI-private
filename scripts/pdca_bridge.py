#!/usr/bin/env python3
"""Fixed Actions entrypoint; issue content is never evaluated as code."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from master_contracts import atomic_json
from pdca_bridge import GitHubAPI, GitTransport, discover_commands, execute_command, verify_handled_receipt, _sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['discover', 'execute'])
    args = parser.parse_args()
    repository = os.environ['GITHUB_REPOSITORY']
    api, transport = GitHubAPI(repository), GitTransport(ROOT)
    if args.operation == 'discover':
        trusted_source = api.default_source()
        transport.git('fetch', '--quiet', '--no-tags', transport.remote, trusted_source)
        def receipt(command):
            branch = 'pdca/command-' + command['command_id']
            head = transport.head(branch)
            if not head:
                return None
            path = f'reports/pdca/{command["night"]}/bridge/command-{command["command_id"]}.json'
            value = json.loads(transport.read(head, path))
            if not isinstance(value, dict) or value.get('schema_version') != '1.0' or value.get('command') != command:
                raise ValueError('Malformed command receipt object/schema/binding')
            source = _sha(value.get('command_source_commit', value['source_commit']))
            transport.git('fetch', '--quiet', '--no-tags', transport.remote, source)
            if transport.git('merge-base', '--is-ancestor', source, trusted_source, check=False).returncode:
                raise ValueError('Command receipt source is not trusted history')
            transport.assert_report_tree(head, source)
            return value
        diagnostics = []
        pending = discover_commands(repository, api.open_issues(), receipt, diagnostics=diagnostics,
            receipt_validator=lambda command, value: verify_handled_receipt(transport, command, value, trusted_source))
        audit = {'pending_issues': pending, 'receipt_failures': diagnostics}
        atomic_json(ROOT / 'artifacts/bridge/discovery.json', audit)
        print(json.dumps(audit, ensure_ascii=False))
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
            output.write('issue=' + (str(pending[0]) if pending else '') + '\n')
        return 0
    # Fixed filename in a unique Actions checkout. No caller-controlled path.
    destination = ROOT / 'artifacts/bridge/attempt.json'
    destination.unlink(missing_ok=True)
    try:
        result = execute_command(ROOT, repository, int(os.environ['ISSUE_NUMBER']),
                                 api, transport, os.environ['BRIDGE_ATTEMPT'])
    except Exception as exc:
        result = {'state': 'RETRYABLE', 'scientific_status': 'FAIL',
                  'reason': 'BRIDGE_EXECUTION_FAILED: ' + str(exc)}
    atomic_json(destination, result)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get('state') == 'HANDLED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
