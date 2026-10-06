# Forge Runtime Artifacts — Local RGR v2

This folder contains portable schemas, governance subcontracts, evaluation fixtures and per-run evidence. Start with the [reviewer guide](../reviewer-guide.md), [quickstart](../getting-started/quickstart.md) or [operations guide](../operations.md).

## Portable pack

- `../../packs/rgr-software-v2/pack.json`
- nine versioned stage contracts
- capability declaration
- Rigor Route import contract

Validate the pack:

```bash
python3 scripts/validate-pack.py packs/rgr-software-v2/pack.json
```

## Per-run evidence

```text
docs/agent/runs/{story_id}/
├── run-context.md
├── intake.json                     # optional READY pre-run snapshot
├── project-profile.json            # optional trusted project-facts snapshot
├── plan-input.md
├── profile-resolution.json
├── repository-intelligence.json
├── brainstorm.json
├── detailed-plan.json
├── lane-resolution.json
├── analysis-report.json
├── specialist-*-review.json       # selected profile only
├── red-result.json
├── green-result.json
├── refactor-result.json
├── context-*.json
├── events.jsonl
├── handoff.md
├── decision-log.md
├── quality-gates.json
├── convergence-report.json
└── error-report.md                # failure only
```

JSON and append-only events are authoritative. Markdown is a reviewer projection.

## Validate a completed run

```bash
python3 scripts/validate-run-bundle.py docs/agent/runs/{story_id}
python3 scripts/validate-run-governance.py docs/agent/runs/{story_id}
```

## Export and verify

```bash
python3 scripts/export-run-bundle.py docs/agent/runs/{story_id} evidence.tar.gz
python3 scripts/verify-export-bundle.py evidence.tar.gz
```

The export is deterministic for identical evidence, includes a hash manifest, excludes separate story source files and binaries, rejects detected secret patterns, and grants no publication authority.

## Governance subcontracts

- `workflow-profiles.json` — adaptive strictness.
- `role-contracts.json` — core/specialist permissions.
- `learnings.json` — governed memory.
- `evaluation-corpus.json` — comparison fixtures.

These remain independently versioned subcontracts referenced by the v2 pack.

## Rigor Route compatibility

See `rigor-route-compatibility.md`. Local events and artifacts can be imported, but local checkpoints and verdicts never transfer authenticated platform authority.

## Safety

No source archive, symlink, binary, detected secret, production credential, automatic merge or deployment is permitted in the portable evidence format.


## Pre-run inputs

`intake.json` is optional and must be READY before it can be rendered into immutable `plan-input.md`. `project-profile.json` is optional and accepted only from operator/trusted-platform provenance. Both are evidence inputs; neither grants RGR governance authority.

## Implementation lanes

PLAN always resolves `lane-resolution.json`. Explicit lanes must partition GREEN tasks exactly once. Same-wave literal write surfaces are compared deterministically: conflicts force sequential fallback; disjoint lanes are eligible for concurrent execution when the runtime adapter safely supports it.

## Optional configuration and review helpers

See [operator tools](operator-tools.md) for project onboarding, locked-plan review and spec/code/docs reconciliation. See [runtime configuration](runtime-configuration.md) for reviewed UI exports and non-executing preflight. Neither helper grants stage authority or installs an HTTP adapter.

Run script examples from the pipeline repository root. Before sharing an export, review allowed evidence text for embedded source excerpts and sensitive information: secret scanning is pattern-based and hashes attest byte integrity, not truth or identity.
