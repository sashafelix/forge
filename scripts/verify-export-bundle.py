#!/usr/bin/env python3
"""Verify a deterministic local RGR evidence archive without extracting it."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

from schema_validation import validate_instance

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK = ROOT / "packs" / "rgr-software-v2" / "pack.json"
EXPORT_SCHEMA = ROOT / "docs" / "agent" / "schemas" / "export-manifest.schema.json"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc


def safe_member_name(name: str) -> str:
    path = PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ValueError(f"unsafe archive member path: {name!r}")
    normalized = path.as_posix()
    if normalized != name or normalized.startswith("/"):
        raise ValueError(f"non-canonical archive member path: {name!r}")
    return normalized


def root_hash(entries: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for entry in sorted(entries, key=lambda item: item["path"]):
        digest.update(f"{entry['path']}\0{entry['sha256']}\0{entry['bytes']}\n".encode("utf-8"))
    return digest.hexdigest()


def read_archive(path: Path) -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            for member in archive.getmembers():
                name = safe_member_name(member.name)
                if name in members:
                    raise ValueError(f"duplicate archive member: {name}")
                if not member.isfile():
                    raise ValueError(f"archive member must be a regular file: {name}")
                if member.issym() or member.islnk():
                    raise ValueError(f"links are forbidden in evidence archives: {name}")
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise ValueError(f"unable to read archive member: {name}")
                data = extracted.read()
                if len(data) != member.size:
                    raise ValueError(f"archive size mismatch for {name}")
                members[name] = data
    except (OSError, tarfile.TarError) as exc:
        raise ValueError(f"{path}: invalid tar.gz archive: {exc}") from exc
    return members


def verify(bundle_path: Path, pack_path: Path) -> list[str]:
    errors: list[str] = []
    members = read_archive(bundle_path)
    manifest_bytes = members.get("export-manifest.json")
    if manifest_bytes is None:
        return ["archive missing export-manifest.json"]
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"export-manifest.json is invalid UTF-8 JSON: {exc}"]

    export_schema = load_json(EXPORT_SCHEMA)
    errors.extend(f"export-manifest.json: {error}" for error in validate_instance(manifest, export_schema))
    if not isinstance(manifest, dict):
        return errors or ["export-manifest.json root must be an object"]

    listed = manifest.get("files", [])
    listed_paths = [entry.get("path") for entry in listed if isinstance(entry, dict)]
    if len(listed_paths) != len(set(listed_paths)):
        errors.append("export-manifest.json: file paths must be unique")
    actual_evidence_paths = set(members) - {"export-manifest.json"}
    expected_evidence_paths = {path for path in listed_paths if isinstance(path, str)}
    missing = sorted(expected_evidence_paths - actual_evidence_paths)
    extra = sorted(actual_evidence_paths - expected_evidence_paths)
    if missing:
        errors.append(f"archive missing manifest-listed files: {missing}")
    if extra:
        errors.append(f"archive contains unlisted files: {extra}")

    for entry in listed:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            continue
        path = entry["path"]
        try:
            safe_member_name(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        data = members.get(path)
        if data is None:
            continue
        digest = hashlib.sha256(data).hexdigest()
        if entry.get("sha256") != digest:
            errors.append(f"{path}: SHA-256 mismatch")
        if entry.get("bytes") != len(data):
            errors.append(f"{path}: byte-size mismatch")
        if b"\x00" in data:
            errors.append(f"{path}: binary/NUL content is forbidden")

    if manifest.get("root_hash") != root_hash([entry for entry in listed if isinstance(entry, dict)]):
        errors.append("export-manifest.json: root_hash mismatch")
    if manifest.get("contains_source_code") is not False:
        errors.append("export-manifest.json: contains_source_code must be false")
    if manifest.get("contains_secrets") is not False:
        errors.append("export-manifest.json: contains_secrets must be false")

    pack = load_json(pack_path)
    import_path = ROOT / pack["compatibility"]["evidence_import_contract"]
    import_contract = load_json(import_path)
    if manifest.get("pack_id") != pack.get("pack_id") or manifest.get("pack_version") != pack.get("pack_version"):
        errors.append("export manifest pack identity/version does not match selected pack")
    if manifest.get("protocol_version") != pack.get("protocol_version"):
        errors.append("export manifest protocol_version does not match selected pack")
    expected_format = import_contract.get("accepted_bundle_format", "").split("/", 1)[-1]
    if manifest.get("bundle_format_version") != expected_format:
        errors.append("export manifest bundle format is incompatible with evidence import contract")
    required = set(import_contract.get("required_artifacts", [])) - {"export-manifest.json"}
    required_missing = sorted(required - actual_evidence_paths)
    if required_missing:
        errors.append(f"Import-required artifacts missing: {required_missing}")
    required_flags = {
        entry.get("path")
        for entry in listed
        if isinstance(entry, dict) and entry.get("required") is True
    }
    if not required.issubset(required_flags):
        errors.append(f"manifest does not mark all import-required artifacts required: {sorted(required - required_flags)}")
    if import_contract.get("publication_mode") != "none":
        errors.append("evidence import contract unexpectedly grants publication authority")

    validator_names = {
        item.get("name")
        for item in manifest.get("validators", [])
        if isinstance(item, dict) and item.get("outcome") == "PASS"
    }
    expected_validators = {"validate-pack.py", "validate-run-bundle.py", "validate-run-governance.py"}
    if not expected_validators.issubset(validator_names):
        errors.append(f"export manifest missing PASS validators: {sorted(expected_validators - validator_names)}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK)
    args = parser.parse_args()
    try:
        errors = verify(args.bundle.resolve(), args.pack.resolve())
    except (ValueError, KeyError, TypeError, OSError) as exc:
        errors = [str(exc)]
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {args.bundle} is a verified local-rgr-evidence-bundle/1.0 archive")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
