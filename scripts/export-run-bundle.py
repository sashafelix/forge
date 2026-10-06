#!/usr/bin/env python3
"""Validate and export a deterministic, source-free local RGR evidence bundle."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import mimetypes
import re
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any

from schema_validation import validate_instance

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK = ROOT / "packs" / "rgr-software-v2" / "pack.json"
SCHEMA = ROOT / "docs" / "agent" / "schemas" / "export-manifest.schema.json"
ALLOWED_SUFFIXES = {".json", ".jsonl", ".md", ".txt", ".log", ".xml", ".html", ".csv", ".yaml", ".yml"}
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"(?i)\b(?:password|passwd|secret|access[_-]?token)\s*[:=]\s*[^<\s][^\s]{5,}"),
]


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_validator(script: str, *args: str) -> None:
    command = [sys.executable, str(ROOT / "scripts" / script), *args]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise ValueError(f"validator failed: {' '.join(command)}\n{detail}")


def safe_files(run_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlink not allowed in evidence bundle: {path}")
        if not path.is_file():
            continue
        rel = path.relative_to(run_dir)
        if rel.as_posix() == 'changes.patch':
            # The local host diff is reviewable source material, deliberately excluded from source-free exports.
            continue
        if any(part in {".git", ".."} for part in rel.parts):
            raise ValueError(f"unsafe evidence path: {rel}")
        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            raise ValueError(f"unsupported/binary evidence type: {rel}")
        data = path.read_bytes()
        if b"\x00" in data:
            raise ValueError(f"binary evidence is not allowed: {rel}")
        text = data.decode("utf-8")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                raise ValueError(f"possible secret detected in {rel}: pattern {pattern.pattern}")
        files.append(path)
    return files


def event_timestamp(run_dir: Path) -> str:
    events = []
    for raw in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines():
        if raw.strip():
            events.append(json.loads(raw))
    if not events or not isinstance(events[-1].get("timestamp"), str):
        raise ValueError("events.jsonl must end with a timestamped event")
    return events[-1]["timestamp"]


def root_hash(entries: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for entry in sorted(entries, key=lambda item: item["path"]):
        digest.update(f"{entry['path']}\0{entry['sha256']}\0{entry['bytes']}\n".encode("utf-8"))
    return digest.hexdigest()


def tar_bytes(files: list[tuple[str, bytes]]) -> bytes:
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name, data in sorted(files, key=lambda item: item[0]):
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            info.mode = 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            archive.addfile(info, io.BytesIO(data))
    compressed = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=compressed, compresslevel=9, mtime=0) as stream:
        stream.write(raw.getvalue())
    return compressed.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--manifest-out", type=Path)
    args = parser.parse_args()

    try:
        run_dir = args.run_dir.resolve()
        pack_path = args.pack.resolve()
        run_validator("validate-pack.py", str(pack_path))
        run_validator("validate-run-bundle.py", str(run_dir))
        run_validator("validate-run-governance.py", str(run_dir))

        pack = load_json(pack_path)
        import_contract = load_json(ROOT / pack["compatibility"]["rigor_route_import_contract"])
        required = set(import_contract["required_artifacts"]) - {"export-manifest.json"}
        run_files = safe_files(run_dir)
        rel_names = {path.relative_to(run_dir).as_posix() for path in run_files}
        missing = required - rel_names
        if missing:
            raise ValueError(f"run bundle missing import-required artifacts: {sorted(missing)}")

        file_entries: list[dict[str, Any]] = []
        archive_files: list[tuple[str, bytes]] = []
        for path in run_files:
            rel = path.relative_to(run_dir).as_posix()
            data = path.read_bytes()
            media_type = mimetypes.guess_type(rel)[0] or "text/plain"
            entry = {
                "path": rel,
                "sha256": sha256_bytes(data),
                "bytes": len(data),
                "media_type": media_type,
                "required": rel in required,
            }
            file_entries.append(entry)
            archive_files.append((rel, data))

        profile = load_json(run_dir / "profile-resolution.json")
        repository = load_json(run_dir / "repository-intelligence.json")
        manifest = {
            "schema_version": "1.0",
            "bundle_format_version": "1.0",
            "pack_id": pack["pack_id"],
            "pack_version": pack["pack_version"],
            "protocol_version": pack["protocol_version"],
            "story_id": profile["story_id"],
            "created_at": event_timestamp(run_dir),
            "source_revision": repository["revision"],
            "profile": profile["selected_profile"],
            "files": sorted(file_entries, key=lambda item: item["path"]),
            "validators": [
                {"name": "validate-pack.py", "version": "2.0.0", "outcome": "PASS"},
                {"name": "validate-run-bundle.py", "version": "2.0.0", "outcome": "PASS"},
                {"name": "validate-run-governance.py", "version": "2.0.0", "outcome": "PASS"}
            ],
            "root_hash": root_hash(file_entries),
            "contains_source_code": False,
            "contains_secrets": False,
        }
        errors = validate_instance(manifest, load_json(SCHEMA))
        if errors:
            raise ValueError("export manifest invalid: " + "; ".join(errors))
        manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
        archive_files.append(("export-manifest.json", manifest_bytes))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(tar_bytes(archive_files))
        if args.manifest_out:
            args.manifest_out.write_bytes(manifest_bytes)
        print(f"PASS: exported {len(file_entries)} evidence files to {args.output} ({args.output.stat().st_size} bytes)")
        return 0
    except (ValueError, KeyError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
