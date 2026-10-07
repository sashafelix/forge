#!/usr/bin/env python3
"""Validate a portable local RGR pack and its compatibility contracts."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from schema_validation import validate_instance

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "docs" / "agent" / "schemas"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_doc(path: Path, schema_name: str) -> tuple[dict[str, Any], list[str]]:
    document = load_json(path)
    schema = load_json(SCHEMA_DIR / schema_name)
    if not isinstance(document, dict):
        return {}, [f"{path}: root must be an object"]
    errors = [f"{path}: {error}" for error in validate_instance(document, schema)]
    return document, errors


def canonical_manifest_hash(manifest: dict[str, Any]) -> str:
    clone = json.loads(json.dumps(manifest))
    clone["integrity"]["manifest_sha256"] = None
    clone["integrity"]["signature"] = None
    payload = json.dumps(clone, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate(pack_path: Path) -> tuple[list[str], dict[str, str]]:
    errors: list[str] = []
    hashes: dict[str, str] = {}
    manifest, manifest_errors = validate_doc(pack_path, "pack-manifest.schema.json")
    errors.extend(manifest_errors)
    if manifest_errors:
        return errors, hashes

    pack_id = manifest["pack_id"]
    pack_version = manifest["pack_version"]
    role_doc = load_json(ROOT / manifest["roles_path"])
    role_ids = {role["id"] for role in role_doc["roles"]}
    role_allowed_stages = {role["id"]: set(role["allowed_stages"]) for role in role_doc["roles"]}
    profiles_doc = load_json(ROOT / manifest["profiles_path"])
    mandatory = profiles_doc["mandatory_stage_order"]

    capabilities_path = ROOT / manifest["capabilities_path"]
    capabilities, capability_errors = validate_doc(capabilities_path, "capability-declaration.schema.json")
    errors.extend(capability_errors)
    capability_ids = [item["id"] for item in capabilities.get("capabilities", [])]
    if len(capability_ids) != len(set(capability_ids)):
        errors.append(f"{capabilities_path}: capability ids must be unique")
    if capabilities.get("pack_id") != pack_id or capabilities.get("pack_version") != pack_version:
        errors.append(f"{capabilities_path}: pack identity/version mismatch")
    required_capability_ids = set(capability_ids)
    unsupported = set(capabilities.get("unsupported_features", []))
    for boundary in ["automatic merge", "automatic deployment", "production access"]:
        if boundary not in unsupported:
            errors.append(f"{capabilities_path}: must explicitly mark {boundary!r} unsupported")

    stage_schema = load_json(SCHEMA_DIR / "stage-contract.schema.json")
    stage_entries = manifest["stage_contracts"]
    stages: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for entry in stage_entries:
        rel_path = entry["path"]
        if rel_path in seen_paths:
            errors.append(f"pack manifest: duplicate stage path {rel_path}")
        seen_paths.add(rel_path)
        path = ROOT / rel_path
        if not path.is_file():
            errors.append(f"pack manifest: missing stage contract {rel_path}")
            continue
        contract = load_json(path)
        errors.extend(f"{path}: {error}" for error in validate_instance(contract, stage_schema))
        stages.append(contract)
        digest = sha256(path)
        hashes[rel_path] = digest
        declared = entry.get("sha256")
        if declared is not None and declared != digest:
            errors.append(f"pack manifest: hash mismatch for {rel_path}")
        if entry.get("stage") != contract.get("stage"):
            errors.append(f"pack manifest: stage name mismatch for {rel_path}")

    ordered_stages = [stage.get("stage") for stage in sorted(stages, key=lambda item: item.get("sequence", 0))]
    if ordered_stages != mandatory:
        errors.append(f"stage contracts must match mandatory order {mandatory}, got {ordered_stages}")
    for index, stage in enumerate(sorted(stages, key=lambda item: item["sequence"]), 1):
        if stage["sequence"] != index:
            errors.append(f"stage {stage['stage']}: sequence must be {index}")
        if stage["pack_id"] != pack_id or stage["pack_version"] != pack_version:
            errors.append(f"stage {stage['stage']}: pack identity/version mismatch")
        if stage["role"] not in role_ids:
            errors.append(f"stage {stage['stage']}: unknown role {stage['role']}")
        unknown_capabilities = set(stage["required_capabilities"]) - required_capability_ids
        if unknown_capabilities:
            errors.append(f"stage {stage['stage']}: unknown required capabilities {sorted(unknown_capabilities)}")
        overlap = set(stage["required_capabilities"]) & set(stage["forbidden_capabilities"])
        if overlap:
            errors.append(f"stage {stage['stage']}: capability both required and forbidden {sorted(overlap)}")
        if not all(stage["context_policy"].values()):
            errors.append(f"stage {stage['stage']}: all context safety controls must be true")
        expected_next = mandatory[index] if index < len(mandatory) else None
        if stage["next_stage"] != expected_next:
            errors.append(f"stage {stage['stage']}: next_stage must be {expected_next!r}")
        if stage["retry_policy"]["max_attempts"] > 2:
            errors.append(f"stage {stage['stage']}: max attempts cannot exceed two")

    routing_path = ROOT / manifest["runtime_routing_path"]
    routing, routing_errors = validate_doc(routing_path, "runtime-routing.schema.json")
    errors.extend(routing_errors)
    if routing.get("pack_id") != pack_id or routing.get("pack_version") != pack_version:
        errors.append(f"{routing_path}: pack identity/version mismatch")
    target_ids = [target["id"] for target in routing.get("targets", [])]
    if len(target_ids) != len(set(target_ids)):
        errors.append(f"{routing_path}: target ids must be unique")
    targets_by_id = {target["id"]: target for target in routing.get("targets", [])}
    route_ids = [route["id"] for route in routing.get("routes", [])]
    if len(route_ids) != len(set(route_ids)):
        errors.append(f"{routing_path}: route ids must be unique")
    exact_routes: set[tuple[str, str]] = set()
    wildcard_roles: set[str] = set()
    for route in routing.get("routes", []):
        role = route["role"]
        stage = route["stage"]
        if role not in role_ids:
            errors.append(f"{routing_path}: route {route['id']} references unknown role {role}")
            continue
        if stage == "*":
            wildcard_roles.add(role)
        else:
            exact_routes.add((stage, role))
            if stage not in role_allowed_stages.get(role, set()):
                errors.append(f"{routing_path}: role {role} is not allowed in stage {stage}")
        unknown_targets = set(route["targets"]) - set(target_ids)
        if unknown_targets:
            errors.append(f"{routing_path}: route {route['id']} references unknown targets {sorted(unknown_targets)}")
        required_model = set(route["required_model_capabilities"])
        for target_id in route["targets"]:
            target = targets_by_id.get(target_id)
            if target is None:
                continue
            missing = required_model - set(target["capabilities"])
            if missing:
                errors.append(f"{routing_path}: route {route['id']} target {target_id} lacks capabilities {sorted(missing)}")
    for stage in stages:
        pair = (stage["stage"], stage["role"])
        if pair not in exact_routes and stage["role"] not in wildcard_roles:
            errors.append(f"{routing_path}: missing runtime route for stage owner {pair[0]}/{pair[1]}")

    for rel_path in manifest["artifact_schemas"]:
        if not (ROOT / rel_path).is_file():
            errors.append(f"pack manifest: missing artifact schema {rel_path}")
    for rel_path in [manifest["profiles_path"], manifest["roles_path"], manifest["learnings_path"]]:
        if not (ROOT / rel_path).is_file():
            errors.append(f"pack manifest: missing referenced governance file {rel_path}")

    import_path = ROOT / manifest["compatibility"]["evidence_import_contract"]
    import_doc, import_errors = validate_doc(import_path, "evidence-import.schema.json")
    errors.extend(import_errors)
    if import_doc.get("pack_id") != pack_id or import_doc.get("pack_version") != pack_version:
        errors.append(f"{import_path}: pack identity/version mismatch")
    if import_doc.get("publication_mode") != "none" or manifest["compatibility"]["publication_authority"] != "none":
        errors.append("pack/import contract must not grant publication authority")
    for key in ["event_schema", "profile_schema", "role_schema"]:
        path = ROOT / import_doc.get(key, "")
        if not path.is_file():
            errors.append(f"{import_path}: missing referenced {key} {import_doc.get(key)!r}")

    manifest_hash = canonical_manifest_hash(manifest)
    hashes[str(pack_path.relative_to(ROOT))] = manifest_hash
    declared_manifest_hash = manifest["integrity"].get("manifest_sha256")
    if declared_manifest_hash is not None and declared_manifest_hash != manifest_hash:
        errors.append("pack manifest: manifest_sha256 mismatch")
    if manifest["integrity"].get("signature") is not None:
        errors.append("pack manifest: local validator cannot verify a signature; activate signed packs in a trusted platform")

    return errors, hashes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack", nargs="?", type=Path, default=ROOT / "packs" / "rgr-software-v2" / "pack.json")
    parser.add_argument("--hash-report", type=Path)
    args = parser.parse_args()
    try:
        errors, hashes = validate(args.pack.resolve())
    except (ValueError, KeyError, TypeError) as exc:
        errors, hashes = [str(exc)], {}
    if args.hash_report:
        args.hash_report.write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {args.pack} is a valid portable local RGR v2 pack ({len(hashes) - 1} stage hashes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
