"""Read the canonical Forge library without loading runtime-specific prompt copies."""
from __future__ import annotations

import json
from pathlib import Path
import re

from pipeline_support.common import ROOT, read_bytes

IDENTITY = re.compile(r'[a-z][a-z0-9-]{0,79}')


def definition(root: Path, relative: str) -> dict:
    data = read_bytes(root, relative)
    if len(data) > 128 * 1024:
        raise ValueError('Library definition exceeds 128 KiB: ' + relative)
    text = data.decode('utf-8').replace('\r\n', '\n')
    match = re.match(r'\A---\n(.*?)\n---\n(.*)\Z', text, re.S)
    if not match:
        raise ValueError('Missing library frontmatter: ' + relative)
    fields = {}
    for line in match[1].splitlines():
        key, separator, value = line.partition(':')
        if not separator or key not in ('name', 'description', 'role') or key in fields:
            raise ValueError('Unsupported/duplicate library metadata: ' + relative)
        value = value.strip()
        if value.startswith('"'):
            value = json.loads(value)
        if not isinstance(value, str) or not value.strip():
            raise ValueError('Library metadata must be nonempty strings: ' + relative)
        fields[key] = value
    if not IDENTITY.fullmatch(fields.get('name', '')) or not fields.get('description') or not match[2].strip():
        raise ValueError('Invalid library identity/description/body: ' + relative)
    return {**fields, 'path': relative, 'body': match[2].strip(), 'bytes': len(data)}


def library(root: Path = ROOT) -> dict:
    paths = {
        'agents': sorted(p.relative_to(root).as_posix() for p in (root / 'agents').glob('*.md') if p.name != 'README.md'),
        'skills': sorted(p.relative_to(root).as_posix() for p in (root / 'skills').glob('*/SKILL.md')),
    }
    result = {}
    for kind, names in paths.items():
        if not 1 <= len(names) <= 100:
            raise ValueError('Expected 1–100 canonical ' + kind)
        entries = [definition(root, name) for name in names]
        if len({item['name'] for item in entries}) != len(entries):
            raise ValueError('Duplicate ' + kind + ' identity')
        for item in entries:
            expected = Path(item['path']).stem if kind == 'agents' else Path(item['path']).parent.name
            if item['name'] != expected:
                raise ValueError('Library name must match its canonical path: ' + item['path'])
        result[kind] = entries
    if sum(item['bytes'] for entries in result.values() for item in entries) > 2 * 1024 * 1024:
        raise ValueError('Canonical library exceeds 2 MiB')
    return result


def catalog(root: Path = ROOT) -> dict:
    return {kind: [{k: v for k, v in item.items() if k not in ('body', 'bytes')} for item in entries]
            for kind, entries in library(root).items()}


def agent_for_role(role: str, root: Path = ROOT) -> dict:
    matches = [item for item in library(root)['agents'] if item.get('role') == role]
    if len(matches) != 1:
        raise ValueError('Expected one canonical agent for role: ' + role)
    return matches[0]


def guidance_paths(root: Path = ROOT) -> set[str]:
    entries = library(root)
    return ({'AGENTS.md', 'CLAUDE.md', 'README.md', 'CONTRIBUTING.md', 'agents/README.md', 'skills/README.md',
             'docs/enforcement.md', 'docs/model-portability.md', 'packs/rgr-software-v2/pack.json'}
            | {item['path'] for values in entries.values() for item in values}
            | {p.relative_to(root).as_posix() for pattern in ('docs/conventions/*.md', 'docs/agent/*.md',
               'docs/agent/*.json', 'docs/agent/schemas/*.json') for p in root.glob(pattern)})


def claude_definitions(root: Path = ROOT) -> dict:
    preface = (f'Forge library root: {root.resolve()}. Read AGENTS.md there first. '
               'Resolve library docs/agents/skills references from that root; read only relevant skills. '
               'Use the separately supplied target repository for story files.\n\n')
    return {item['name']: {'description': item['description'], 'prompt': preface +
            f"Read the full canonical agent instructions at {root.resolve() / item['path']} before starting. "
            'Follow that role and its required outputs; do not substitute a cached prompt.'}
            for item in library(root)['agents']}


def validate(root: Path = ROOT) -> dict:
    entries = library(root)
    contracts = json.loads(read_bytes(root, 'docs/agent/role-contracts.json'))['roles']
    expected = {role['id'] for role in contracts}
    roles = [item['role'] for item in entries['agents'] if 'role' in item]
    if set(roles) != expected or len(roles) != len(expected):
        raise ValueError('Every governed role must bind exactly one canonical agent')
    for directory in ('.claude/agents', '.github/agents'):
        if list((root / directory).glob('ai-pipeline-*.md')):
            raise ValueError('Remove obsolete Forge agent copies from ' + directory)
    # Check concrete canonical references, including links in both entry catalogs.
    for path in sorted(root.rglob('*.md')):
        if any(part in ('.git', '.agent-runs', '__pycache__') for part in path.parts) or path.name == 'CHANGELOG.md':
            continue
        text = read_bytes(root, path.relative_to(root).as_posix()).decode('utf-8')
        if 'docs/skills/' in text:
            raise ValueError('Obsolete skill path in ' + str(path.relative_to(root)))
        for ref in re.findall(r'(?<![\w-])(?:agents/[a-z0-9-]+\.md|skills/[a-z0-9-]+/SKILL\.md)', text):
            read_bytes(root, ref)
    return {kind: len(items) for kind, items in entries.items()}
