#!/usr/bin/env python3
"""Generate synthetic small-profile evidence for current contract/CI testing."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

STORY_ID = "CONTRACT-FIXTURE-001"
REVISION = "0123456789abcdef0123456789abcdef01234567"
TIMESTAMP = "2026-01-01T00:00:00Z"
STAGES = ["prepare", "brainstorm", "plan", "analyze", "red_test", "green_code", "refactor", "quality_gate", "converge"]
ROLES = {
    "prepare": "repository_analyst",
    "brainstorm": "specifier",
    "plan": "planner",
    "analyze": "consistency_analyst",
    "red_test": "test_author",
    "green_code": "implementer",
    "refactor": "refactorer",
    "quality_gate": "independent_verifier",
    "converge": "convergence_reviewer",
}


def write_json(root: Path, name: str, value: Any) -> None:
    (root / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def context(stage: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "story_id": STORY_ID,
        "attempt": 1,
        "stage": stage,
        "required_sources": [
            {
                "path": "plan-input.md" if stage == "prepare" else "brainstorm.json",
                "kind": "task" if stage == "prepare" else "artifact",
                "reason": f"Required deterministic input for {stage}",
                "sha256": None,
            }
        ],
        "optional_sources": [],
        "exclusions": [{"pattern": ".git/**", "reason": "Git internals are outside story context"}],
        "budget": {"max_files": 20, "max_bytes": 200000, "max_tokens": 40000},
    }


def stage_result(stage: str, role: str, status: str, output_ref: str, exit_code: int) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "story_id": STORY_ID,
        "attempt": 1,
        "stage": stage,
        "actor_role": role,
        "outcome": "completed",
        "commands": [
            {
                "command": f"fixture-check --stage {stage}",
                "exit_code": exit_code,
                "output_ref": output_ref,
            }
        ],
        "artifact_refs": [output_ref],
        "criterion_evidence": [
            {"sc_id": "SC-1", "status": status, "evidence_refs": [output_ref]}
        ],
        "self_check": {"complete": True, "items": [f"{stage} fixture self-check complete"]},
    }


def event(sequence: int, stage: str, event_type: str, role: str, artifact_refs: list[str], outcome: str | None = None, safe_summary: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "sequence": sequence,
        "timestamp": TIMESTAMP,
        "story_id": STORY_ID,
        "attempt": 1,
        "stage": stage,
        "event_type": event_type,
        "actor_role": role,
        "outcome": outcome,
        "causation_sequence": None if sequence == 1 else sequence - 1,
        "correlation_id": STORY_ID,
        "artifact_refs": artifact_refs,
        "safe_summary": safe_summary,
    }


def generate(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    write_text(root, "run-context.md", f"# Run Context\n\nstory_id: {STORY_ID}\nprofile: small\ncurrent_stage: done")
    write_text(root, "plan-input.md", "# Plan Input\n\nAdd one deterministic fixture behaviour with a regression test.")
    write_text(root, "brainstorm.md", "# Brainstorm Projection\n\nSC-1: GIVEN fixture input WHEN evaluated THEN fixture output is returned.")
    write_text(root, "detailed-plan.md", "# Detailed Plan Projection\n\nTASK-1 RED, TASK-2 GREEN, TASK-3 REFACTOR.")
    write_text(root, "analysis-report.md", "# Analysis Projection\n\nNo hard findings.")
    write_text(root, "handoff.md", "# Handoff Projection\n\nAll stages completed with canonical evidence.")
    write_text(root, "quality-gates.md", "# Quality Gates Projection\n\nVerdict: PASS")
    write_text(root, "convergence-report.md", "# Convergence Projection\n\nOutcome: CONVERGED")
    write_text(root, "decision-log.md", "# Decision Log\n\nFixture uses a deterministic small-profile path.")
    write_text(root, "evidence/red-test.log", "TEST-1 failed for the intended missing fixture behaviour.")
    write_text(root, "evidence/green-test.log", "TEST-1 passed; 1 test passed, 0 failed.")
    write_text(root, "evidence/refactor-test.log", "TEST-1 passed after no-op refactor; 1 test passed, 0 failed.")
    write_text(root, "evidence/verify-test.log", "Independent fixture verification passed.")

    write_json(root, "profile-resolution.json", {
        "schema_version": "1.0",
        "story_id": STORY_ID,
        "selected_profile": "small",
        "facts": {
            "risk_tags": [],
            "blast_radius": "low",
            "uncertainty": "low",
            "changed_module_count": 1,
            "cross_service": False,
            "contract_change": False,
            "data_migration": False,
            "security_sensitive": False,
            "infrastructure_change": False,
        },
        "rule_ids": ["DEFAULT-BOUNDED"],
        "reasons": ["bounded low-risk single-module change"],
        "specialist_roles": [],
        "manual_checkpoints": [],
        "overridden": False,
        "override_reason": None,
    })
    write_json(root, "repository-intelligence.json", {
        "schema_version": "1.0",
        "story_id": STORY_ID,
        "revision": REVISION,
        "project_root": ".",
        "stack": ["python"],
        "frameworks": [],
        "commands": {"build": ["python -m py_compile fixture.py"], "test": ["python -m unittest"], "lint": []},
        "modules": [{"path": "fixture.py", "reason": "Target fixture module", "confidence": "high"}],
        "symbols": [{"name": "fixture_value", "path": "fixture.py", "reason": "Target behaviour", "confidence": "high"}],
        "impact": {
            "files": [{"path": "fixture.py", "reason": "Implements SC-1", "confidence": "high"}],
            "symbols": [{"name": "fixture_value", "path": "fixture.py", "reason": "Implements SC-1", "confidence": "high"}],
            "tests": [{"path": "test_fixture.py", "reason": "Verifies SC-1", "confidence": "high"}],
        },
        "warnings": [],
        "inspection": {"paths_inspected": ["fixture.py", "test_fixture.py"], "paths_omitted": [], "file_budget": 20, "byte_budget": 200000},
    })
    write_json(root, "brainstorm.json", {
        "schema_version": "1.0",
        "story_id": STORY_ID,
        "success_criteria": [{"id": "SC-1", "statement": "GIVEN fixture input WHEN evaluated THEN fixture output is returned", "verified_by": "unit", "source": "fixture intent"}],
        "input_trace": [{"input_item": "Return fixture output", "covered_by": ["SC-1"]}],
        "uncertainties": [],
    })
    write_json(root, "detailed-plan.json", {
        "schema_version": "1.0",
        "story_id": STORY_ID,
        "status": "locked",
        "tasks": [
            {"id": "TASK-1", "stage": "red_test", "description": "Add TEST-1 for SC-1", "depends_on": [], "outputs": ["test_fixture.py"], "criteria": ["SC-1"]},
            {"id": "TASK-2", "stage": "green_code", "description": "Implement backend half of SC-1", "depends_on": ["TASK-1"], "outputs": ["backend/fixture.py"], "criteria": ["SC-1"]},
            {"id": "TASK-3", "stage": "green_code", "description": "Implement frontend half of SC-1", "depends_on": ["TASK-1"], "outputs": ["frontend/fixture.ts"], "criteria": ["SC-1"]},
            {"id": "TASK-4", "stage": "refactor", "description": "Confirm no safe refactor is required", "depends_on": ["TASK-2", "TASK-3"], "outputs": ["refactor-result.json"], "criteria": ["SC-1"]},
        ],
        "criterion_test_map": [{"sc_id": "SC-1", "test_ids": ["TEST-1"]}],
        "implementation_lanes": [
            {"id": "LANE-backend", "kind": "backend", "description": "Backend fixture implementation", "task_ids": ["TASK-2"], "write_surfaces": ["backend"], "depends_on_lanes": []},
            {"id": "LANE-frontend", "kind": "frontend", "description": "Frontend fixture implementation", "task_ids": ["TASK-3"], "write_surfaces": ["frontend"], "depends_on_lanes": []},
        ],
    })
    write_json(root, "lane-resolution.json", {
        "schema_version": "1.0",
        "story_id": STORY_ID,
        "mode": "parallel",
        "reason": "fixture lanes are dependency-independent with disjoint write surfaces",
        "lanes": [
            {"id": "LANE-backend", "kind": "backend", "task_ids": ["TASK-2"], "write_surfaces": ["backend"], "depends_on_lanes": []},
            {"id": "LANE-frontend", "kind": "frontend", "task_ids": ["TASK-3"], "write_surfaces": ["frontend"], "depends_on_lanes": []},
        ],
        "waves": [{"wave": 1, "lane_ids": ["LANE-backend", "LANE-frontend"]}],
        "overlap_checks": [{"left_lane": "LANE-backend", "right_lane": "LANE-frontend", "conflict": False, "overlap_surfaces": []}],
    })
    write_json(root, "analysis-report.json", {
        "schema_version": "1.0",
        "story_id": STORY_ID,
        "hard_findings": [],
        "warnings": [],
        "unresolved_uncertainties": [],
        "artifact_refs": ["repository-intelligence.json", "brainstorm.json", "detailed-plan.json"],
    })
    write_json(root, "red-result.json", stage_result("red_test", "test_author", "red_confirmed", "evidence/red-test.log", 1))
    green_result = stage_result("green_code", "implementer", "pass", "evidence/green-test.log", 0)
    green_result["lane_results"] = [
        {"lane_id": "LANE-backend", "wave": 1, "outcome": "completed", "artifact_refs": ["backend/fixture.py", "evidence/green-test.log"]},
        {"lane_id": "LANE-frontend", "wave": 1, "outcome": "completed", "artifact_refs": ["frontend/fixture.ts", "evidence/green-test.log"]},
    ]
    write_json(root, "green-result.json", green_result)
    write_json(root, "refactor-result.json", stage_result("refactor", "refactorer", "pass", "evidence/refactor-test.log", 0))
    write_json(root, "quality-gates.json", {
        "schema_version": "1.0",
        "story_id": STORY_ID,
        "verdict": "PASS",
        "reviewer_role": "independent_verifier",
        "reviewer_identity": "fixture-independent-verifier",
        "criterion_evidence": [{"sc_id": "SC-1", "status": "PASS", "tests": ["TEST-1"], "evidence_refs": ["evidence/verify-test.log"]}],
        "hard_failures": [],
        "changed_files": ["backend/fixture.py", "frontend/fixture.ts", "test_fixture.py"],
        "artifact_refs": ["red-result.json", "green-result.json", "refactor-result.json", "evidence/verify-test.log"],
    })
    write_json(root, "convergence-report.json", {
        "schema_version": "1.0",
        "story_id": STORY_ID,
        "attempt": 1,
        "outcome": "CONVERGED",
        "blocking_gaps": [],
        "artifact_refs": ["brainstorm.json", "detailed-plan.json", "quality-gates.json"],
        "earliest_invalid_stage": None,
    })
    for stage in STAGES:
        write_json(root, f"context-{stage}.json", context(stage))

    events: list[dict[str, Any]] = []
    sequence = 1
    events.append(event(sequence, "setup", "run.created", "orchestrator", ["plan-input.md"]))
    sequence += 1
    events.append(event(sequence, "setup", "profile.resolved", "orchestrator", ["profile-resolution.json"], safe_summary="small profile selected"))
    sequence += 1
    stage_artifacts = {
        "prepare": "repository-intelligence.json",
        "brainstorm": "brainstorm.json",
        "plan": "detailed-plan.json",
        "analyze": "analysis-report.json",
        "red_test": "red-result.json",
        "green_code": "green-result.json",
        "refactor": "refactor-result.json",
        "quality_gate": "quality-gates.json",
        "converge": "convergence-report.json",
    }
    for stage in STAGES:
        events.append(event(sequence, stage, "stage.started", ROLES[stage], [f"context-{stage}.json"]))
        sequence += 1
        outcome = "PASS" if stage == "quality_gate" else "CONVERGED" if stage == "converge" else None
        events.append(event(sequence, stage, "stage.completed", ROLES[stage], [stage_artifacts[stage]], outcome=outcome))
        sequence += 1
        if stage == "plan":
            events.append(event(sequence, "plan", "lane_plan.resolved", "orchestrator", ["lane-resolution.json"], safe_summary="parallel fixture lanes resolved"))
            sequence += 1
    events.append(event(sequence, "close", "run.completed", "orchestrator", ["quality-gates.json", "convergence-report.json"], outcome="PASS"))
    write_text(root, "events.jsonl", "\n".join(json.dumps(item, sort_keys=True, separators=(",", ":")) for item in events))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    generate(args.output_dir.resolve())
    print(f"PASS: generated local RGR v2 contract fixture at {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
