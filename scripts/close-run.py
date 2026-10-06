#!/usr/bin/env python3
"""Canonical read-only closure: structural/governance/evidence checks and optional exact-revision reconciliation."""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import sys
from pipeline_support.reconciliation import reconcile


def validate(root: Path, repo: Path | None = None, base: str | None = None) -> dict:
    errors: list[str] = []
    for script in ('validate-run-bundle.py', 'validate-run-governance.py'):
        spec = importlib.util.spec_from_file_location(script[:-3], Path(__file__).parent / script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        try:
            errors.extend(module.validate(root))
        except (OSError, ValueError, KeyError, TypeError, UnicodeError) as exc:
            errors.append(str(exc))
    reconciliation = None
    if bool(repo) != bool(base):
        errors.append('Exact reconciliation requires both --repo and --base')
    if repo and base:
        try:
            reconciliation = reconcile(root, repo, base)
            errors.extend(item['message'] for item in reconciliation['findings'] if item['severity'] == 'blocking')
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(str(exc))
    return {'schema_version': '1.0', 'status': 'blocked' if errors else 'consistent',
            'authority': 'advisory', 'evidence_level': 'reconciled' if reconciliation and not errors else 'structural',
            'authenticated_execution': False, 'errors': sorted(set(errors)), 'reconciliation': reconciliation,
            'limits': ['Consistent files and actor labels do not authenticate execution. Use independently bound host receipts.']}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run_dir', type=Path)
    p.add_argument('--repo', type=Path)
    p.add_argument('--base')
    a = p.parse_args()
    result = validate(a.run_dir, a.repo, a.base)
    print(json.dumps(result, indent=2))
    return int(result['status'] == 'blocked')


if __name__ == '__main__':
    raise SystemExit(main())
