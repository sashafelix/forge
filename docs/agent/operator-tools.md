# Project setup and review tools

These optional tools improve preparation and inspection around Forge’s Local RGR 2.3 protocol. They do not introduce a stage, execute configured commands, change locked intent or issue an approval. Existing run artifacts and pack contracts remain compatible.

## Guided project notes

From the pipeline checkout:

```bash
python3 scripts/pipeline.py onboard --repo /path/to/project
```

Answer five questions about purpose, stack, tests, build and constraints. For noninteractive use, `--answers answers.json` accepts exactly the string fields `purpose`, `stack`, `test_command`, `build_command`, `constraints`.

This creates `docs/knowledge/INDEX.md`, focused product/architecture/delivery/decision notes and a provenance record. `--directory` selects another literal repository-relative directory. The selected project must be a Git repository with a commit. Existing knowledge files are never overwritten. Review notes before committing; recorded commands are unexecuted and facts are advisory. Read the index and relevant topics within the current context budget, not the entire directory by default.

Project onboarding is separate from story intake. It does not reset intake's five-round, five-question budget or convert repository notes into a trusted project profile.

## Challenge a locked plan

```bash
python3 scripts/pipeline.py review-plan /path/to/run --output /tmp/plan-review.json
```

The helper checks schema validity, matching story IDs, duplicate IDs, task/criterion/test-map coverage, task dependency cycles, literal output paths and blocking uncertainties. Potentially subjective criterion wording generates advisory questions, capped at five. This is a heuristic prompt for review, not a semantic verdict. The analyst must still check failure behaviour, examples, compatibility, assumptions, alternatives and sufficiency of the planned tests against exact sources.

ANALYZE records confirmed structural or semantic defects in the canonical `analysis-report.json`. The helper does not alter it. Material questions use the existing intake/remediation protocol and remaining budget; reaching the limit leaves unresolved blockers blocked.

## Reconcile implementation and documentation

After an independent VERIFY artifact exists:

```bash
python3 scripts/pipeline.py reconcile /path/to/run \
  --repo /path/to/story-worktree \
  --base FULL_BASE_COMMIT_SHA \
  --output /tmp/reconciliation.json
```

Select the exact worktree and full base SHA recorded in `repository-intelligence.json`. The comparison includes committed changes since that base, staged/unstaged changes, deletions and nonignored untracked files. Only the selected run-evidence directory, if inside the repository, is excluded. Gitignored files are not inspected. Task outputs must enumerate literal files for this helper; directory/glob scope must be refined into files through the normal planning process before relying on reconciliation.

The report compares changed paths with locked task outputs and VERIFY's changed-file list, checks criterion/test continuity, fingerprints referenced evidence and checks planned documentation files exist. Documentation impact still requires semantic review: if there is no documentation task, record which user/API/operations references need changes, or why none do. A filename or an unchanged document alone cannot prove documentation is correct.

Findings go through normal remediation from the earliest invalid stage. Never repair drift by rewriting locked criteria to describe whatever the implementation happens to do. Reports include input, evidence and changed-file hashes; deleted files have a null hash. They are point-in-time inspections, not atomic snapshots, execution evidence or release approvals. Oversized files and symlinks are rejected rather than silently inspected outside the selected roots. Keep output reports outside the source worktree, or in its selected run-evidence directory.

Both review commands use exit `0` for clear/advisory-only results, `1` for blocking findings and `2` for invalid input/inspection errors. `status: clear` means only the performed checks found no issue. Reports default to stdout; `--output` creates a new file and refuses overwrite. Standard run/governance validators and independent verification remain required. These optional reports are not automatically included in portable evidence exports.

## Configuration-only desktop companion

[Forge Console](https://github.com/sashafelix/forge-console) can prepare a `project-profile.json` using the existing profile schema `1.0`. Review its project facts and explicitly supply it as operator input:

```bash
python3 scripts/validate-project-profile.py /path/to/project-profile.json
```

The UI and pipeline remain separate repositories. The UI export carries no stage, runtime, risk, capability, checkpoint or publication authority. Provenance text alone does not establish trust: bind the file only when independently supplied by an operator/trusted platform. Repository-discovered profiles remain untrusted. Commands are project facts, not permission to execute them.

Execution continues through the existing pipeline orchestrator and runtime. A future desktop execution adapter requires a separately reviewed, opt-in integration and end-to-end conformance tests for all nine stages, risk escalation, independent verification, checkpoints, evidence integrity, failure/remediation and interrupted-run recovery.

The companion also prepares reviewed provider/model profiles and role-routing exports. Follow [runtime configuration](runtime-configuration.md) to validate and explicitly preflight those files. Preflight is separate from the project-facts handoff, does not read credentials or contact providers, returns `execution_authority: false`, and does not modify live routing.
