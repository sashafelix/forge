"""Deterministic structural checks for optional delivery proposals, not a scheduler."""
from __future__ import annotations

import re
from .handoff_transfer import IDENTIFIER, require

SC = re.compile(r"SC-[1-9][0-9]*\Z")


def _fields(value, keys, label):
    require(isinstance(value, dict) and set(value) == set(keys), "Invalid fields: " + label)


def _text(value, label, maximum=4000):
    require(isinstance(value, str) and bool(value.strip()) and len(value) <= maximum
            and not any(ord(c) < 32 and c not in "\n\r\t" for c in value), "Invalid " + label)


def _ids(value, allowed, label, nonempty=True):
    require(isinstance(value, list) and len(value) <= 200, "Invalid " + label)
    require(all(isinstance(v, str) for v in value), "Invalid " + label)
    require(len(set(value)) == len(value) and set(value) <= allowed, "Unknown or duplicate " + label)
    require(bool(value) or not nonempty, "Empty " + label)
    return set(value)


def validate_plan(inspected: dict, plan: dict) -> dict:
    """Reject stale packages, missing coverage, invalid references and cyclic edges.

    A structurally valid proposal still requires the normal semantic PLAN/ANALYZE
    review and a locked detailed-plan. It cannot alter that plan or stage protocol.
    """
    _fields(plan, {"schema_version", "handoff_sha256", "story_id", "criteria", "slices", "regressions"}, "delivery proposal")
    require(type(plan["schema_version"]) is int and plan["schema_version"] == 1, "Unsupported proposal version")
    require(plan["handoff_sha256"] == inspected["package_sha256"], "Delivery proposal targets a different handoff")
    require(isinstance(plan["story_id"], str) and IDENTIFIER.fullmatch(plan["story_id"]), "Invalid story ID")
    scenarios = set(inspected["metadata"]["scenario_ids"])
    criteria = plan["criteria"]
    require(isinstance(criteria, list) and 1 <= len(criteria) <= 200, "Provide 1 to 200 criteria")
    mapped, criterion_ids = set(), set()
    for criterion in criteria:
        _fields(criterion, {"sc_id", "scenario_ids", "test_boundary"}, "criterion")
        cid = criterion["sc_id"]
        require(isinstance(cid, str) and SC.fullmatch(cid) and cid not in criterion_ids, "Invalid or duplicate criterion ID")
        criterion_ids.add(cid)
        mapped |= _ids(criterion["scenario_ids"], scenarios, "scenario references")
        boundary = criterion["test_boundary"]
        _fields(boundary, {"interface", "expected_behavior", "oracle", "limitations"}, "test boundary")
        for name, value in boundary.items():
            _text(value, "test boundary " + name)
    require(mapped == scenarios, "Every approved scenario must map to a criterion")
    slices = plan["slices"]
    require(isinstance(slices, list) and 1 <= len(slices) <= 100, "Provide 1 to 100 delivery slices")
    seen, assigned = {}, set()
    for item in slices:
        _fields(item, {"id", "outcome", "criterion_ids", "depends_on"}, "slice")
        sid = item["id"]
        require(isinstance(sid, str) and IDENTIFIER.fullmatch(sid) and sid not in seen, "Invalid or duplicate slice ID")
        _text(item["outcome"], "observable slice outcome")
        owned = _ids(item["criterion_ids"], criterion_ids, "slice criteria")
        require(not assigned.intersection(owned), "Each criterion has exactly one delivery owner")
        assigned |= owned
        seen[sid] = item
    require(assigned == criterion_ids, "Unassigned criteria remain")
    for sid, item in seen.items():
        deps = _ids(item["depends_on"], set(seen), "slice dependencies", nonempty=False)
        require(sid not in deps, "A slice cannot depend on itself")
    remaining, done, waves = set(seen), set(), []
    while remaining:
        ready = sorted(sid for sid in remaining if set(seen[sid]["depends_on"]) <= done)
        require(bool(ready), "Delivery dependencies contain a cycle")
        waves.append(ready)
        remaining.difference_update(ready)
        done.update(ready)
    regressions = plan["regressions"]
    require(isinstance(regressions, list) and len(regressions) <= 200, "Invalid regressions")
    test_ids = set()
    for item in regressions:
        _fields(item, {"test_id", "behavior", "boundary"}, "regression")
        for name, value in item.items():
            _text(value, "regression " + name)
        require(item["test_id"] not in test_ids, "Duplicate regression test")
        test_ids.add(item["test_id"])
    return {"schema_version": 1, "kind": "delivery-proposal-check", "story_id": plan["story_id"],
            "handoff_sha256": inspected["package_sha256"], "status": "structurally-valid",
            "criterion_count": len(criteria), "scenario_count": len(scenarios), "dependency_waves": waves,
            "semantic_review_required": True, "execution_authority": False,
            "parallel_execution_permitted": False}


def review_axes(inspected: dict, plan: dict, quality: dict) -> dict:
    """Read-only projection of an existing verifier's reported evidence.

    Caller validates quality-gates.schema.json first. Unclassified hard failures
    block both axes: this helper never uses keyword guessing to waive findings.
    This projection does not rerun tests or prove that the reviewer was independent.
    """
    validate_plan(inspected, plan)
    require(quality.get("story_id") == plan["story_id"], "Review belongs to another story")
    require(quality.get("reviewer_role") == "independent_verifier" and bool(quality.get("reviewer_identity")), "Independent verifier identity is required")
    require(quality.get("verdict") in ("PASS", "WARN", "FAIL"), "Invalid canonical verdict")
    evidence = quality.get("criterion_evidence")
    require(isinstance(evidence, list) and bool(evidence), "Criterion evidence is required")
    by_id = {}
    for item in evidence:
        require(isinstance(item, dict) and item.get("status") in ("PASS", "WARN", "FAIL"), "Invalid criterion verdict")
        cid = item.get("sc_id")
        require(isinstance(cid, str) and cid not in by_id, "Duplicate criterion evidence")
        require(isinstance(item.get("tests"), list) and bool(item["tests"])
                and isinstance(item.get("evidence_refs"), list) and bool(item["evidence_refs"]), "Evidence references are required")
        by_id[cid] = item
    require(set(by_id) == {c["sc_id"] for c in plan["criteria"]}, "Review must cover the exact mapped criteria")
    hard = quality.get("hard_failures")
    require(isinstance(hard, list), "Hard failures must be explicit")
    results = {s: [] for s in inspected["metadata"]["scenario_ids"]}
    for item in plan["criteria"]:
        for scenario in item["scenario_ids"]:
            results[scenario].append(by_id[item["sc_id"]])
    status = lambda values: "FAIL" if "FAIL" in values else "WARN" if "WARN" in values else "PASS"
    scenario_results = {sid: {"reported_status": status([e["status"] for e in entries]), "criteria": entries}
                        for sid, entries in sorted(results.items())}
    fidelity = status([e["reported_status"] for e in scenario_results.values()])
    if hard or quality["verdict"] == "FAIL":
        fidelity = "FAIL"
    if quality["verdict"] != "FAIL":
        require(not hard and fidelity != "FAIL", "Canonical verdict contradicts blocking evidence")
    if quality["verdict"] == "PASS":
        require(fidelity == "PASS" and not hard, "Canonical PASS contradicts its evidence")
    return {"schema_version": 1, "kind": "review-axes-projection", "authority": "advisory",
            "story_id": plan["story_id"], "handoff_sha256": inspected["package_sha256"],
            "requirement_revision": inspected["metadata"]["revision"],
            "requirement_fidelity": {"reported_status": fidelity, "scenarios": scenario_results},
            "engineering_quality": {"reported_status": quality["verdict"], "hard_failures": hard,
                                    "artifact_refs": quality.get("artifact_refs", [])},
            "unclassified_hard_failures_apply_to_both_axes": True,
            "canonical_verdict": quality["verdict"], "tests_rerun": False,
            "code_revision_binding_verified": False, "execution_authority": False,
            "publication_authority": False}
