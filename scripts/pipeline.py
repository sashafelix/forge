#!/usr/bin/env python3
"""Optional local project setup and read-only review helpers. No execution authority."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from pipeline_support.common import json_text, save_new
from pipeline_support.onboarding import QUESTIONS, onboard
from pipeline_support.reconciliation import reconcile
from pipeline_support.review import review_plan
from pipeline_support.handoff_transfer import accept, inspect, parse_json, public_summary, read_local, verify_accepted
from pipeline_support.delivery_planning import validate_plan, review_axes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("onboard", help="Create project knowledge notes from five answers")
    setup.add_argument("--repo", type=Path, required=True)
    setup.add_argument("--answers", type=Path, help="JSON object with the five answer fields; otherwise prompt")
    setup.add_argument("--directory", default="docs/knowledge")
    for name in ("review-plan", "reconcile"):
        command = commands.add_parser(name)
        command.add_argument("run_dir", type=Path)
        command.add_argument("--output", type=Path, help="New report path; default stdout. Existing files are never replaced.")
        if name == "reconcile":
            command.add_argument("--repo", type=Path, required=True)
            command.add_argument("--base", required=True)
    transfer = commands.add_parser("import-handoff", help="Inspect a portable handoff; explicitly accept its SHA-256 to create local input")
    transfer.add_argument("archive", type=Path)
    transfer.add_argument("--show-content", action="store_true", help="Display the exact requirement and feature as escaped JSON")
    transfer.add_argument("--accept-sha256")
    transfer.add_argument("--output", type=Path, help="New private directory; required only when accepting")
    verify = commands.add_parser("verify-handoff-input", help="Recheck saved handoff and plan-input integrity")
    verify.add_argument("directory", type=Path)
    for name in ("check-delivery-plan", "review-axes"):
        command = commands.add_parser(name)
        command.add_argument("--handoff", type=Path, required=True)
        command.add_argument("--plan", type=Path, required=True)
        command.add_argument("--output", type=Path)
        if name == "review-axes":
            command.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "onboard":
            if args.answers:
                from pipeline_support.common import read_json
                answers = read_json(args.answers.parent, args.answers.name)
            else:
                answers = {key: input(question + "\n> ") for key, question in QUESTIONS}
            print(json_text({"created": onboard(args.repo, answers, args.directory)}), end="")
            return 0
        if args.command == "import-handoff":
            if bool(args.accept_sha256) != bool(args.output):
                raise ValueError("Acceptance requires both --accept-sha256 and --output")
            packet = inspect(args.archive)
            result = public_summary(packet)
            if args.show_content:
                result["content"] = {name: packet["files"][name].decode("utf-8") for name in ("requirement.md", "acceptance.feature")}
            if args.accept_sha256:
                result["accepted_input"] = accept(packet, args.accept_sha256, args.output)
            print(json_text(result), end="")
            return 0
        if args.command == "verify-handoff-input":
            print(json_text(verify_accepted(args.directory)), end="")
            return 0
        if args.command in ("check-delivery-plan", "review-axes"):
            packet = inspect(args.handoff)
            proposal = parse_json(read_local(args.plan))
            if args.command == "check-delivery-plan":
                result = validate_plan(packet, proposal)
            else:
                from pipeline_support.common import read_json
                quality = read_json(args.run_dir, "quality-gates.json", "quality-gates.schema.json")
                result = review_axes(packet, proposal, quality)
        else:
            result = review_plan(args.run_dir) if args.command == "review-plan" else reconcile(args.run_dir, args.repo, args.base)
        rendered = json_text(result)
        if args.output:
            save_new(args.output, rendered)
        else:
            print(rendered, end="")
        return 1 if result.get("status") == "blocked" or result.get("canonical_verdict") == "FAIL" else 0
    except (OSError, ValueError, UnicodeError, EOFError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
