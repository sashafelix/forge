"""Semantic evidence checks shared by validation, closure and the execution host.

Legacy bundles remain inspectable; their labels/hashes are not authenticated receipts.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pipeline_support.common import STAGES, read_bytes

EMPTY_SUITE = re.compile(r"(?:\bRan\s+0\s+tests?\b|\bno tests (?:ran|collected)\b|\bcollected\s+0\s+items?\b|\b0 passed[,;]?\s+0 failed\b)", re.I)


def document(root: Path, name: str) -> dict:
    value = json.loads(read_bytes(root, name))
    if not isinstance(value, dict):
        raise ValueError(f"{name}: expected an object")
    return value


def validate_evidence(root: Path) -> list[str]:
    """Check actual referenced bytes and stage-specific outcomes, without executing them."""
    errors: list[str] = []
    checked: dict[str, bytes] = {}

    def evidence(ref: object, owner: str) -> None:
        if not isinstance(ref, str):
            errors.append(f"{owner}: evidence reference must be a relative file")
            return
        try:
            data = checked.setdefault(ref, read_bytes(root, ref))
            if not data.strip():
                errors.append(f"{owner}: empty evidence file {ref}")
            if EMPTY_SUITE.search(data.decode('utf-8', 'replace')):
                errors.append(f"{owner}: no executed tests in {ref}")
        except (ValueError, OSError) as exc:
            errors.append(f"{owner}: {exc}")

    for name in ('red-result.json', 'green-result.json', 'refactor-result.json', 'quality-gates.json'):
        try:
            value = document(root, name)
        except (ValueError, OSError) as exc:
            errors.append(str(exc))
            continue
        commands = value.get('commands', [])
        if value.get('outcome') == 'completed':
            exits = [c.get('exit_code') for c in commands if isinstance(c, dict)]
            if name != 'red-result.json' and any(code != 0 for code in exits):
                errors.append(f"{name}: completed passing stage has a nonzero command exit")
            if name == 'red-result.json' and not any(type(code) is int and code != 0 for code in exits):
                errors.append(f"{name}: RED requires an executed expected failure")
        for command in commands:
            if isinstance(command, dict):
                evidence(command.get('output_ref'), name)
        for item in value.get('criterion_evidence', []):
            if isinstance(item, dict):
                for ref in item.get('evidence_refs', []):
                    evidence(ref, name)
        # artifact_refs may include source paths; explicit evidence paths must exist.
        for ref in value.get('artifact_refs', []):
            if isinstance(ref, str) and ref.startswith('evidence/'):
                evidence(ref, name)
    return sorted(set(errors))


def validate_attempts(events: list[dict], final_attempt: int) -> list[str]:
    """Validate bounded suffix remediation, preserving the completed prefix and history."""
    errors: list[str] = []
    progress: list[str] = []
    attempt = 1
    completed_in_attempt: set[str] = set()
    terminal = False
    rejected = False
    for event in events:
        current = event.get('attempt')
        if type(current) is not int or current < 1:
            errors.append('events.jsonl: invalid attempt')
            continue
        kind, stage = event.get('event_type'), event.get('stage')
        if current != attempt:
            if terminal or not rejected or current != attempt + 1 or kind != 'attempt.started' or stage not in STAGES:
                errors.append('events.jsonl: new attempt requires contiguous attempt.started with an invalidated stage')
                continue
            index = STAGES.index(stage)
            if len(progress) < index:
                errors.append('events.jsonl: remediation cannot skip an incomplete prefix')
            progress = progress[:index]
            attempt = current
            completed_in_attempt.clear()
            rejected = False
        if kind in ('stage.failed', 'run.failed', 'convergence.remediation_requested'):
            rejected = True
        if kind == 'stage.completed':
            if terminal or stage in completed_in_attempt or len(progress) >= len(STAGES) or STAGES[len(progress)] != stage:
                errors.append(f'events.jsonl: unexpected completed stage {stage!r} in attempt {attempt}')
            else:
                progress.append(stage)
                completed_in_attempt.add(stage)
        if kind == 'run.completed':
            if progress != STAGES:
                errors.append('events.jsonl: run completed before every mandatory stage')
            terminal = True
    if progress != STAGES:
        errors.append(f'events.jsonl: completed stage order must cover {STAGES}, got {progress}')
    if attempt != final_attempt:
        errors.append('events.jsonl: final attempt differs from convergence-report.json')
    return errors
