#!/usr/bin/env python3
"""Launch Claude Code with the canonical Forge agents supplied for this session."""
import argparse
import json
import shutil
import subprocess
import sys
from agent_library import claude_definitions, validate
from pipeline_support.common import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--claude', default='claude', help='Installed Claude Code executable')
    parser.add_argument('--print-agents', action='store_true', help='Inspect generated JSON without launching a model')
    parser.add_argument('arguments', nargs=argparse.REMAINDER, help='Arguments after -- are forwarded to Claude Code')
    args = parser.parse_args()
    validate()
    definitions = json.dumps(claude_definitions(), separators=(',', ':'))
    if args.print_agents:
        print(definitions)
        return 0
    forwarded = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
    if any(value == '--agents' or value.startswith('--agents=') or value == '--agent' or value.startswith('--agent=') for value in forwarded):
        raise ValueError('The Forge launcher supplies agents and the orchestrator; do not override them')
    executable = shutil.which(args.claude)
    if not executable:
        raise ValueError('Install/authenticate Claude Code or supply --claude /path/to/executable')
    # argv is passed directly: no shell quoting or committed adapter files.
    return subprocess.call([executable, '--agents', definitions, '--agent', 'ai-pipeline-rgr-orchestrator', *forwarded], cwd=ROOT)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
