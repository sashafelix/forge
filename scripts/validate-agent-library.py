#!/usr/bin/env python3
"""Validate canonical agents, skills, role bindings and source references."""
import sys
from agent_library import validate

if __name__ == '__main__':
    try:
        counts = validate()
        print(f"PASS: {counts['agents']} canonical agents and {counts['skills']} skills; no Forge adapter copies")
    except (ValueError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
