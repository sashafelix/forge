#!/usr/bin/env python3
"""Check or refresh Claude Code copies of Forge's portable role prompts."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Refresh existing adapter paths from canonical prompts')
    args = parser.parse_args()
    source = ROOT / 'agents'
    adapter = ROOT / '.claude' / 'agents'
    prompts = sorted(source.glob('ai-pipeline-*.md'))
    if not prompts:
        print('ERROR: no portable role prompts found', file=sys.stderr)
        return 1
    expected = {path.name for path in prompts}
    extra = {path.name for path in adapter.glob('ai-pipeline-*.md')} - expected
    errors = [f'unmapped adapter prompt: {name}' for name in sorted(extra)]
    for path in prompts:
        content = path.read_bytes()
        if f'name: {path.stem}\n'.encode() not in content:
            errors.append(f'{path.name}: frontmatter name does not match file identity')
        destination = adapter / path.name
        if args.write:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        elif not destination.is_file() or destination.read_bytes() != content:
            errors.append(f'{path.name}: adapter differs; run python3 scripts/sync-agent-adapters.py --write')
    if errors:
        for error in errors:
            print(f'ERROR: {error}', file=sys.stderr)
        return 1
    print(f'PASS: {len(prompts)} portable role prompts match the Claude Code adapter')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
