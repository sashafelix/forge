#!/usr/bin/env python3
"""Validate one run against the v1.3 governance subcontracts used by the current Local RGR pack."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from schema_validation import validate_instance
from evidence_validation import validate_attempts, validate_evidence
from pipeline_support.common import read_bytes

ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / "docs" / "agent"
SCHEMA_DIR = AGENT_DIR / "schemas"
STAGES = ["prepare", "brainstorm", "plan", "analyze", "red_test", "green_code", "refactor", "quality_gate", "converge"]


def load_json(path: Path) -> Any:
    try:
        return json.loads(read_bytes(path.parent, path.name))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc


def expected_specialists(profile: dict[str, Any], facts: dict[str, Any]) -> set[str]:
    tags = set(facts.get("risk_tags", []))
    if facts.get("security_sensitive"):
        tags.add("security")
    if facts.get("data_migration"):
        tags.add("migration")
    if facts.get("infrastructure_change"):
        tags.add("infra")
    if facts.get("contract_change"):
        tags.add("breaking-contract")
    roles = set(profile.get("specialist_roles", []))
    for tag in tags:
        role = profile.get("conditional_specialists", {}).get(tag)
        if isinstance(role, str):
            roles.add(role)
    return roles


def read_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_no, raw in enumerate(read_bytes(path.parent, path.name).decode('utf-8').splitlines(), 1):
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(event, dict):
            raise ValueError(f"{path}:{line_no}: event must be an object")
        events.append(event)
    return events


def validate(run_dir: Path) -> list[str]:
    errors: list[str] = []
    resolution_path = run_dir / "profile-resolution.json"
    if not resolution_path.is_file():
        return ["missing required artifact: profile-resolution.json"]

    resolution = load_json(resolution_path)
    resolution_schema = load_json(SCHEMA_DIR / "profile-resolution.schema.json")
    errors.extend(f"{resolution_path}: {error}" for error in validate_instance(resolution, resolution_schema))
    if errors:return errors
    profiles_doc = load_json(AGENT_DIR / "workflow-profiles.json")
    profiles = {profile["id"]: profile for profile in profiles_doc["profiles"]}
    roles_doc = load_json(AGENT_DIR / "role-contracts.json")
    roles = {role["id"]: role for role in roles_doc["roles"]}
    role_ids = set(roles)

    selected = resolution.get("selected_profile")
    profile = profiles.get(selected)
    if profile is None:
        errors.append(f"profile-resolution.json: unknown selected_profile {selected!r}")
        return errors

    actual_specialists = set(resolution.get("specialist_roles", []))
    expected = expected_specialists(profile, resolution.get("facts", {}))
    if actual_specialists != expected:
        errors.append(f"profile-resolution.json: specialist_roles must be {sorted(expected)}, got {sorted(actual_specialists)}")
    if actual_specialists - role_ids:
        errors.append(f"profile-resolution.json: unknown specialist roles {sorted(actual_specialists - role_ids)}")
    if resolution.get("manual_checkpoints") != profile["manual_checkpoints"]:
        errors.append("profile-resolution.json: manual_checkpoints must match selected profile")
    if resolution.get("overridden") and not resolution.get("override_reason"):
        errors.append("profile-resolution.json: overridden resolution requires override_reason")
    if not resolution.get("overridden") and resolution.get("override_reason") is not None:
        errors.append("profile-resolution.json: non-overridden resolution cannot have override_reason")

    specialist_schema = load_json(SCHEMA_DIR / "specialist-review.schema.json")
    for specialist in sorted(actual_specialists & role_ids):
        outputs = roles[specialist].get("canonical_outputs", [])
        for output in outputs:
            if not output.startswith("specialist-"):
                continue
            path = run_dir / output
            if not path.is_file():
                errors.append(f"missing required specialist artifact for {specialist}: {output}")
                continue
            review = load_json(path)
            errors.extend(f"{path}: {error}" for error in validate_instance(review, specialist_schema))
            if errors:continue
            if review.get("role") != specialist:
                errors.append(f"{path}: role must be {specialist}")
            if review.get("status") == "FAIL":
                errors.append(f"{path}: specialist FAIL blocks run closure")
            if any(item.get("severity") == "blocking" for item in review.get("findings", []) if isinstance(item, dict)):
                errors.append(f"{path}: blocking specialist finding prevents closure")

    budget = profile["budgets"]
    context_schema = load_json(SCHEMA_DIR / "context-manifest.schema.json")
    for stage in STAGES:
        path = run_dir / f"context-{stage}.json"
        if not path.is_file():
            errors.append(f"missing required context manifest: {path.name}")
            continue
        context = load_json(path)
        errors.extend(f"{path}: {error}" for error in validate_instance(context, context_schema))
        if errors:continue
        limits = context.get("budget", {})
        if limits.get("max_files", 0) > budget["max_context_files"]:
            errors.append(f"{path}: max_files exceeds {selected} profile")
        if limits.get("max_bytes", 0) > budget["max_context_bytes"]:
            errors.append(f"{path}: max_bytes exceeds {selected} profile")
        max_tokens = limits.get("max_tokens")
        if isinstance(max_tokens, int) and max_tokens > budget["max_tokens"]:
            errors.append(f"{path}: max_tokens exceeds {selected} profile")

    convergence_path = run_dir / "convergence-report.json"
    if convergence_path.is_file():
        convergence = load_json(convergence_path)
        if convergence.get("attempt", 0) > budget["max_convergence_attempts"]:
            errors.append("convergence-report.json: attempt exceeds selected profile budget")

    events_path = run_dir / "events.jsonl"
    events: list[dict[str, Any]] = []
    if events_path.is_file():
        events = read_events(events_path)
        for line_no, event in enumerate(events, 1):
            if type(event.get('attempt')) is not int or event['attempt'] > budget['max_convergence_attempts']:
                errors.append(f'events.jsonl:{line_no}: attempt exceeds selected profile budget')
            actor_role = event.get("actor_role")
            if actor_role not in role_ids and actor_role not in {"planner", "operator"}:
                errors.append(f"events.jsonl:{line_no}: unknown actor_role {actor_role!r}")
        if not any(event.get("event_type") == "profile.resolved" and "profile-resolution.json" in event.get("artifact_refs", []) for event in events):
            errors.append("events.jsonl: missing profile.resolved event referencing profile-resolution.json")

    accepted_checkpoints = {
        event.get("safe_summary")
        for event in events
        if event.get("event_type") == "checkpoint.accepted" and event.get("actor_role") == "operator"
    }
    for checkpoint in profile["manual_checkpoints"]:
        if checkpoint not in accepted_checkpoints:
            errors.append(f"events.jsonl: missing accepted operator checkpoint {checkpoint!r}")

    errors.extend(validate_evidence(run_dir))
    if events and convergence_path.is_file():
        errors.extend(validate_attempts(events, convergence.get('attempt', 1)))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    try:
        errors = validate(args.run_dir)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, RecursionError) as exc:
        errors = [str(exc)]
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {args.run_dir} satisfies the v1.3 governance subcontracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
