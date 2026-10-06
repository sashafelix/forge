#!/usr/bin/env python3
"""Inspect synthetic Forge evidence, deterministic export and tamper rejection."""
from __future__ import annotations

import copy
import io
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def invoke(script: str, *args: Path, expected_success: bool = True) -> None:
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
                            cwd=ROOT, capture_output=True, text=True)
    if (result.returncode == 0) != expected_success:
        raise ValueError(f"Unexpected exit {result.returncode} from {script}:\n{result.stdout}{result.stderr}")
    if expected_success:
        print(result.stdout.strip())
    else:
        print("PASS: archive verifier rejected modified evidence")
        print((result.stdout + result.stderr).strip())


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="forge-evidence-"))
    run = root / "synthetic-run"
    first, second, tampered = [root / name for name in ("evidence-a.tar.gz", "evidence-b.tar.gz", "tampered.tar.gz")]
    try:
        invoke("generate-contract-fixture.py", run)
        invoke("validate-run-bundle.py", run)
        invoke("validate-run-governance.py", run)
        invoke("export-run-bundle.py", run, first)
        invoke("export-run-bundle.py", run, second)
        if first.read_bytes() != second.read_bytes():
            raise ValueError("identical synthetic evidence produced different archive bytes")
        print("PASS: both exports are byte-identical")
        invoke("verify-export-bundle.py", first)

        # Read only the archive just generated here. No files are extracted.
        changed = False
        with tarfile.open(first, "r:gz") as source, tarfile.open(tampered, "w:gz") as destination:
            for member in source.getmembers():
                if not member.isfile():
                    raise ValueError("unexpected non-file entry in generated archive")
                stream = source.extractfile(member)
                if stream is None:
                    raise ValueError(f"cannot read generated archive member {member.name}")
                data = stream.read()
                if member.name == "quality-gates.json":
                    data += b"\n "  # Still valid JSON, but no longer matches the manifest.
                    changed = True
                info = copy.copy(member)
                info.size = len(data)
                destination.addfile(info, io.BytesIO(data))
        if not changed:
            raise ValueError("generated archive did not contain quality-gates.json")
        invoke("verify-export-bundle.py", tampered, expected_success=False)
    except (OSError, ValueError, tarfile.TarError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Synthetic artifacts: {root}")
    print("No application tests or model calls were performed by this evidence example.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
