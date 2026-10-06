#!/usr/bin/env python3
"""Create a separate baseline repository and operator inputs; do not run a model."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

EXAMPLE = Path(__file__).resolve().parent
FORGE = EXAMPLE.parents[1]


def create_demo(output: Path | None = None) -> dict[str, str]:
    if output is None:
        root = Path(tempfile.mkdtemp(prefix="forge-first-change-")).resolve()
    else:
        root = output.resolve()
        root.mkdir(parents=True, exist_ok=False)
    target, inputs = root / "target", root / "inputs"
    target.mkdir()
    inputs.mkdir()
    for name in ("greeting.py", "test_greeting.py"):
        shutil.copyfile(EXAMPLE / name, target / name)
    (target / ".gitignore").write_text("__pycache__/\n*.pyc\n.agent-runs/\n", encoding="utf-8")

    def git(*args: str) -> str:
        return subprocess.run(["git", "-C", str(target), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    git("init", "-q")
    git("add", "greeting.py", "test_greeting.py", ".gitignore")
    git("-c", "user.name=Forge Demo", "-c", "user.email=demo@example.invalid",
        "-c", "commit.gpgsign=false", "commit", "-qm", "Passing greeting baseline")
    subprocess.run([sys.executable, "-m", "unittest", "-v"], cwd=target, check=True,
                   stdout=sys.stderr, stderr=sys.stderr)

    story = "DEMO-" + uuid.uuid4().hex[:8].upper()
    plan = (EXAMPLE / "plan-input.md").read_text(encoding="utf-8")
    (inputs / "plan-input.md").write_text(plan.replace("DEMO-STORY-ID", story), encoding="utf-8")
    facts = json.loads((EXAMPLE / "facts.json").read_text(encoding="utf-8"))
    facts["story_id"] = story
    (inputs / "facts.json").write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")
    descriptor = {
        "forge_root": str(FORGE), "demo_root": str(root), "target_repo": str(target),
        "input_dir": str(inputs), "plan_input": str(inputs / "plan-input.md"),
        "facts_file": str(inputs / "facts.json"), "base_revision": git("rev-parse", "HEAD"),
        "story_id": story, "run_dir": str(FORGE / "docs/agent/runs" / story),
    }
    (root / "demo.json").write_text(json.dumps(descriptor, indent=2) + "\n", encoding="utf-8")
    return descriptor


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New directory; existing paths are never overwritten")
    args = parser.parse_args()
    try:
        result = create_demo(args.output)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
