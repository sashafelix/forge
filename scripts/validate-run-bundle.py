#!/usr/bin/env python3
"""Validate local RGR v2.3 run-bundle schemas and cross-artifact invariants."""
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
SCHEMA_DIR = ROOT / "docs" / "agent" / "schemas"
STAGES = ["prepare", "brainstorm", "plan", "analyze", "red_test", "green_code", "refactor", "quality_gate", "converge"]
REQUIRED_FILES = [
    "run-context.md", "plan-input.md", "repository-intelligence.json",
    "brainstorm.md", "brainstorm.json", "detailed-plan.md", "detailed-plan.json",
    "lane-resolution.json", "analysis-report.json", "red-result.json", "green-result.json",
    "refactor-result.json", "handoff.md", "quality-gates.md", "quality-gates.json",
    "convergence-report.json", "decision-log.md", "events.jsonl",
]
ARTIFACT_SCHEMAS = {
    "repository-intelligence.json": "repository-intelligence.schema.json",
    "brainstorm.json": "brainstorm.schema.json",
    "detailed-plan.json": "detailed-plan.schema.json",
    "lane-resolution.json": "lane-resolution.schema.json",
    "analysis-report.json": "analysis-report.schema.json",
    "red-result.json": "stage-result.schema.json",
    "green-result.json": "stage-result.schema.json",
    "refactor-result.json": "stage-result.schema.json",
    "quality-gates.json": "quality-gates.schema.json",
    "convergence-report.json": "convergence-report.schema.json",
}
OPTIONAL_ARTIFACT_SCHEMAS = {
    "intake.json": "intake.schema.json",
    "project-profile.json": "project-profile.schema.json",
}
STAGE_RESULTS = {
    "red-result.json": ("red_test", "test_author", "red_confirmed"),
    "green-result.json": ("green_code", "implementer", "pass"),
    "refactor-result.json": ("refactor", "refactorer", "pass"),
}


def load_json(path: Path) -> Any:
    try:
        return json.loads(read_bytes(path.parent, path.name))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc


def schema(name: str) -> dict[str, Any]:
    loaded = load_json(SCHEMA_DIR / name)
    if not isinstance(loaded, dict):
        raise ValueError(f"{SCHEMA_DIR / name}: schema root must be an object")
    return loaded


def validate_artifact(path: Path, schema_name: str) -> tuple[list[str], Any]:
    instance = load_json(path)
    errors = [f"{path}: {error}" for error in validate_instance(instance, schema(schema_name))]
    return errors, instance


def validate_events(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    events: list[dict[str, Any]] = []
    previous = 0
    event_schema = schema("run-event.schema.json")
    for line_no, raw in enumerate(read_bytes(path.parent, path.name).decode('utf-8').splitlines(), 1):
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{line_no}: invalid JSON: {exc}")
            continue
        errors.extend(f"{path}:{line_no}: {error}" for error in validate_instance(event, event_schema))
        if not isinstance(event, dict):
            continue
        sequence = event.get("sequence")
        if not isinstance(sequence, int) or sequence != previous + 1:
            errors.append(f"{path}:{line_no}: sequence must be contiguous; expected {previous + 1}, got {sequence!r}")
        if isinstance(sequence, int):
            previous = sequence
        events.append(event)
    if not events:
        errors.append(f"{path}: must contain at least one event")
    return errors, events


def validate_task_graph(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    tasks = {task.get("id"): task for task in plan.get("tasks", []) if isinstance(task, dict)}
    if None in tasks:
        errors.append("detailed-plan.json: every task must have an id")
        tasks.pop(None, None)
    for task_id, task in tasks.items():
        for dependency in task.get("depends_on", []):
            if dependency not in tasks:
                errors.append(f"detailed-plan.json: {task_id} depends on unknown task {dependency}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str, chain: list[str]) -> None:
        if task_id in visiting:
            errors.append(f"detailed-plan.json: dependency cycle {' -> '.join(chain + [task_id])}")
            return
        if task_id in visited or task_id not in tasks:
            return
        visiting.add(task_id)
        for dependency in tasks[task_id].get("depends_on", []):
            visit(dependency, chain + [task_id])
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in sorted(tasks):
        visit(task_id, [])
    return errors


def ids(items: Any, key: str) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {item.get(key) for item in items if isinstance(item, dict) and isinstance(item.get(key), str)}


def validate_lane_contract(plan: dict[str, Any], resolution: dict[str, Any], green_result: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    tasks = {item.get("id"): item for item in plan.get("tasks", []) if isinstance(item, dict)}
    green_ids = {task_id for task_id, task in tasks.items() if task and task.get("stage") == "green_code"}
    declared = plan.get("implementation_lanes", [])
    declared_ids = {lane.get("id") for lane in declared if isinstance(lane, dict)}
    resolved_ids = {lane.get("id") for lane in resolution.get("lanes", []) if isinstance(lane, dict)}

    if resolution.get("story_id") != plan.get("story_id"):
        errors.append("lane-resolution.json: story_id must match detailed-plan.json")

    if declared:
        assigned = []
        for lane in declared:
            if isinstance(lane, dict):
                assigned.extend(lane.get("task_ids", []))
        assigned_set = set(assigned)
        if len(assigned) != len(assigned_set):
            errors.append("detailed-plan.json: a GREEN task is assigned to more than one implementation lane")
        if assigned_set != green_ids:
            errors.append(
                f"detailed-plan.json: explicit lanes must assign exactly GREEN tasks {sorted(green_ids)}, got {sorted(assigned_set)}"
            )
        if declared_ids != resolved_ids:
            errors.append(
                f"lane-resolution.json: lane ids must match declared lanes {sorted(declared_ids)}, got {sorted(resolved_ids)}"
            )
        lane_results = green_result.get("lane_results", [])
        result_ids = {item.get("lane_id") for item in lane_results if isinstance(item, dict)}
        if result_ids != declared_ids:
            errors.append(
                f"green-result.json: lane_results must exactly cover declared lanes {sorted(declared_ids)}, got {sorted(result_ids)}"
            )
        if any(item.get("outcome") != "completed" for item in lane_results if isinstance(item, dict)):
            errors.append("green-result.json: every explicit lane must have outcome=completed")

    wave_ids = [
        lane_id
        for wave in resolution.get("waves", [])
        if isinstance(wave, dict)
        for lane_id in wave.get("lane_ids", [])
    ]
    if len(wave_ids) != len(set(wave_ids)):
        errors.append("lane-resolution.json: every resolved lane must occur in exactly one wave")
    if resolved_ids and set(wave_ids) != resolved_ids:
        errors.append("lane-resolution.json: waves must cover every resolved lane exactly once")
    if resolution.get("mode") == "parallel":
        if not any(len(wave.get("lane_ids", [])) > 1 for wave in resolution.get("waves", []) if isinstance(wave, dict)):
            errors.append("lane-resolution.json: parallel mode requires at least one multi-lane wave")
        if any(check.get("conflict") is True for check in resolution.get("overlap_checks", []) if isinstance(check, dict)):
            errors.append("lane-resolution.json: parallel mode cannot contain write-surface conflicts")
    return errors


def validate(run_dir: Path) -> list[str]:
    errors: list[str] = []
    for name in REQUIRED_FILES:
        if not (run_dir / name).is_file():
            errors.append(f"missing required artifact: {name}")
    for stage in STAGES:
        if not (run_dir / f"context-{stage}.json").is_file():
            errors.append(f"missing required context manifest: context-{stage}.json")
    if errors:
        return errors

    artifacts: dict[str, dict[str, Any]] = {}
    for filename, schema_name in ARTIFACT_SCHEMAS.items():
        artifact_errors, instance = validate_artifact(run_dir / filename, schema_name)
        errors.extend(artifact_errors)
        if isinstance(instance, dict):
            artifacts[filename] = instance

    optional_artifacts: dict[str, dict[str, Any]] = {}
    for filename, schema_name in OPTIONAL_ARTIFACT_SCHEMAS.items():
        path = run_dir / filename
        if not path.is_file():
            continue
        artifact_errors, instance = validate_artifact(path, schema_name)
        errors.extend(artifact_errors)
        if isinstance(instance, dict):
            optional_artifacts[filename] = instance

    intake = optional_artifacts.get("intake.json")
    if intake is not None:
        if intake.get("status") != "ready":
            errors.append("intake.json: run snapshot must have status=ready")
        blockers = [
            q.get("id") for q in intake.get("questions", [])
            if isinstance(q, dict) and q.get("blocking") is True and q.get("answered") is not True
        ]
        if blockers:
            errors.append(f"intake.json: unresolved blocking questions {blockers}")

    project_profile = optional_artifacts.get("project-profile.json")
    if project_profile is not None and project_profile.get("provenance", {}).get("source") not in {"operator", "trusted_platform"}:
        errors.append("project-profile.json: trusted provenance must be operator or trusted_platform")

    contexts: dict[str, dict[str, Any]] = {}
    for path in sorted(run_dir.glob("context-*.json")):
        context_errors, instance = validate_artifact(path, "context-manifest.schema.json")
        errors.extend(context_errors)
        if isinstance(instance, dict):
            contexts[path.name] = instance

    if errors:
        return errors

    brainstorm = artifacts.get("brainstorm.json", {})
    plan = artifacts.get("detailed-plan.json", {})
    lanes = artifacts.get("lane-resolution.json", {})
    analysis = artifacts.get("analysis-report.json", {})
    gates = artifacts.get("quality-gates.json", {})
    convergence = artifacts.get("convergence-report.json", {})
    repository = artifacts.get("repository-intelligence.json", {})

    story_ids = {
        value.get("story_id")
        for value in [*artifacts.values(), *contexts.values()]
        if isinstance(value.get("story_id"), str)
    }
    if len(story_ids) != 1:
        errors.append(f"artifacts must contain exactly one story_id, got {sorted(story_ids)}")
    story_id = next(iter(story_ids), None)

    sc_ids = ids(brainstorm.get("success_criteria"), "id")
    if not sc_ids:
        errors.append("brainstorm.json: success_criteria must contain non-empty ids")
    for trace in brainstorm.get("input_trace", []):
        if isinstance(trace, dict):
            unknown = set(trace.get("covered_by", [])) - sc_ids
            if unknown:
                errors.append(f"brainstorm.json: input trace references unknown criteria {sorted(unknown)}")
    if any(item.get("status") == "blocking" for item in brainstorm.get("uncertainties", []) if isinstance(item, dict)):
        errors.append("brainstorm.json: blocking uncertainty cannot advance to completed bundle")

    planned_ids = ids(plan.get("criterion_test_map"), "sc_id")
    evidence_ids = ids(gates.get("criterion_evidence"), "sc_id")
    for label, artifact_ids in (
        ("detailed-plan.json criterion_test_map", planned_ids),
        ("quality-gates.json criterion_evidence", evidence_ids),
    ):
        missing = sc_ids - artifact_ids
        unknown = artifact_ids - sc_ids
        if missing:
            errors.append(f"{label}: missing success criteria {sorted(missing)}")
        if unknown:
            errors.append(f"{label}: references unknown success criteria {sorted(unknown)}")
    errors.extend(validate_task_graph(plan))

    if analysis.get("hard_findings"):
        errors.append("analysis-report.json: hard_findings must be empty before RED")
    if analysis.get("unresolved_uncertainties"):
        errors.append("analysis-report.json: unresolved_uncertainties must be empty before RED")

    for filename, (expected_stage, expected_role, expected_status) in STAGE_RESULTS.items():
        result = artifacts.get(filename, {})
        if result.get("stage") != expected_stage:
            errors.append(f"{filename}: stage must be {expected_stage}")
        if result.get("actor_role") != expected_role:
            errors.append(f"{filename}: actor_role must be {expected_role}")
        if result.get("outcome") != "completed":
            errors.append(f"{filename}: completed bundle requires outcome=completed")
        if result.get("self_check", {}).get("complete") is not True:
            errors.append(f"{filename}: self_check.complete must be true")
        result_ids = ids(result.get("criterion_evidence"), "sc_id")
        if result_ids != sc_ids:
            errors.append(f"{filename}: criterion evidence must exactly match {sorted(sc_ids)}")
        for item in result.get("criterion_evidence", []):
            if isinstance(item, dict) and item.get("status") != expected_status:
                errors.append(f"{filename}: {item.get('sc_id')} must have status {expected_status}")

    errors.extend(validate_lane_contract(plan, lanes, artifacts.get("green-result.json", {})))

    if project_profile is not None:
        for stage in STAGES:
            context = contexts.get(f"context-{stage}.json", {})
            sources = [
                item.get("path")
                for key in ("required_sources", "optional_sources")
                for item in context.get(key, [])
                if isinstance(item, dict)
            ]
            if "project-profile.json" not in sources:
                errors.append(f"context-{stage}.json: bound project-profile.json must be present in stage context")

    if gates.get("reviewer_role") != "independent_verifier":
        errors.append("quality-gates.json: reviewer_role must be independent_verifier")
    if gates.get("reviewer_identity") == "ai-pipeline-green-code":
        errors.append("quality-gates.json: implementer cannot be reviewer_identity")
    if gates.get("verdict") == "PASS":
        if gates.get("hard_failures"):
            errors.append("quality-gates.json: PASS cannot contain hard_failures")
        for item in gates.get("criterion_evidence", []):
            if isinstance(item, dict) and item.get("status") != "PASS":
                errors.append(f"quality-gates.json: PASS requires PASS evidence for {item.get('sc_id')}")

    outcome = convergence.get("outcome")
    gaps = convergence.get("blocking_gaps", [])
    earliest = convergence.get("earliest_invalid_stage")
    if outcome == "CONVERGED" and (gaps or earliest is not None):
        errors.append("convergence-report.json: CONVERGED requires no blocking_gaps and no earliest_invalid_stage")
    if outcome == "REMEDIATE" and (not gaps or earliest is None):
        errors.append("convergence-report.json: REMEDIATE requires blocking_gaps and earliest_invalid_stage")
    if gates.get("verdict") == "PASS" and outcome != "CONVERGED":
        errors.append("convergence-report.json: PASS bundle must finish CONVERGED")

    for stage in STAGES:
        context = contexts.get(f"context-{stage}.json", {})
        if context.get("stage") != stage:
            errors.append(f"context-{stage}.json: stage must be {stage}")

    event_errors, events = validate_events(run_dir / "events.jsonl")
    errors.extend(event_errors)
    event_story_ids = {event.get("story_id") for event in events if isinstance(event.get("story_id"), str)}
    if story_id is not None and event_story_ids != {story_id}:
        errors.append(f"events.jsonl: story ids {sorted(event_story_ids)} do not match artifacts {story_id}")
    errors.extend(validate_attempts(events, convergence.get('attempt', 1)))
    errors.extend(validate_evidence(run_dir))
    if not any(event.get("event_type") == "lane_plan.resolved" and "lane-resolution.json" in event.get("artifact_refs", []) for event in events):
        errors.append("events.jsonl: missing lane_plan.resolved event referencing lane-resolution.json")
    if intake is not None and not any(event.get("event_type") == "intake.bound" and "intake.json" in event.get("artifact_refs", []) for event in events):
        errors.append("events.jsonl: intake snapshot requires intake.bound event")
    if project_profile is not None and not any(event.get("event_type") == "project_profile.bound" and "project-profile.json" in event.get("artifact_refs", []) for event in events):
        errors.append("events.jsonl: project profile snapshot requires project_profile.bound event")

    revision = repository.get("revision")
    if not isinstance(revision, str) or not revision:
        errors.append("repository-intelligence.json: revision must be non-empty")
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
    print(f"PASS: {args.run_dir} satisfies local RGR v2.3 schemas and invariants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
