---
name: skill-decision-index
description: "Maintain `docs/agent/decision-index.md` \u2014 a compact, global pointer to every story's decision log. The index is a table of contents, not a re-statement. Use when this capability is relevant to the assigned stage and target stack."
---

# Skill: skill-decision-index

## Purpose
Maintain `docs/agent/decision-index.md` — a compact, global pointer to every story's decision log. The index is a table of contents, not a re-statement.

## When invoked
- By `ai-pipeline-rgr-orchestrator` after CONVERGE closes a run or on explicit terminal abort/failure.
- VERIFY supplies the canonical gate verdict; it does not itself close the run. Use FAIL for terminal failure even if an earlier gate passed.

## Reads
- `docs/agent/runs/{story_id}/decision-log.md` — to extract a one-line summary
- `docs/agent/runs/{story_id}/quality-gates.json` and `convergence-report.json` — to establish the gate verdict and closure outcome
- `docs/agent/decision-index.md` (if exists) — to append without duplicating

## Writes
- `docs/agent/decision-index.md`

## Index Format

One row per story, pointing to its latest closed run. This is mutable navigation metadata; prior run/attempt evidence remains immutable. Columns:

| Story ID | Date | Verdict | Summary | Tags | Link |
| --- | --- | --- | --- | --- | --- |
| `<story-id>` | `<YYYY-MM-DD>` | PASS \| FAIL \| WARN | one-line what-changed / why-failed | `tag`, `tag` | [log](runs/`<story-id>`/decision-log.md) |

`story_id` is whatever identifier the input gave you: a Jira key (e.g., `ACME-123`), a feature slug (`user-profile-avatar-upload`), a request slug (`source-2026-04-cleanup`), or a direct-source task id. Use what `run-context.md > story_id` says; never invent.

## Summary construction

The `Summary` column must:
- Be one sentence, ≤120 characters.
- State what changed (PASS), the terminal failure (FAIL), or the non-correctness caveat (WARN). A local PASS does not mean the change was published.
- Contain no jargon a future operator wouldn't understand.

Pull the summary from:
1. The current canonical gate/convergence findings (a Markdown summary may help locate them).
2. Otherwise synthesize from the first/last entries in `decision-log.md`.

## Tags

Use tags that match the `scope_tags` vocabulary in `docs/agent/learnings.json`:
- Stack: `stack:backend-java`, `stack:frontend-react`, `stack:mobile-flutter`, `stack:infra-terraform`, …
- Area: `layer:api`, `layer:db`, `domain:auth`, `layer:integration`, `domain:scheduling`, `domain:observability`, `domain:security`, `layer:ui`, `domain:state`, `domain:routing`, `domain:forms`
- Risk: `domain:audit`, `domain:pii`, `domain:migration`, `domain:breaking-contract` *(if applicable)*
- Infra: `infra:nexus`, `infra:k8s`, `infra:kafka`, `infra:s3`, `infra:postgres`, `infra:redis`, …

Tags enable future agents to find precedent: *"show me all stories that touched migrations"*.

## Link

Relative link from `docs/agent/` root:
- `[log](runs/{story_id}/decision-log.md)`

If the run also produced a `quality-gates.md` with a verdict worth re-reading, add a second link:
- `[gate](runs/{story_id}/quality-gates.md)`

## Idempotency

- If a story ID already has a row, update it in place (do not duplicate).
- If a previous run for the same story failed and a re-run succeeds, replace only the index row with the new verdict/date and current evidence link. Preserve all prior run/attempt evidence.

## Output example

```markdown
# Decision Index

| Story ID | Date | Verdict | Summary | Tags | Link |
| --- | --- | --- | --- | --- | --- |
| ACME-1421 | 2026-05-02 | PASS | Inventory adjustment endpoint with audit log | `stack:backend-java`, `layer:api`, `domain:audit`, `infra:postgres` | [log](runs/ACME-1421/decision-log.md) |
| user-profile-avatar-upload | 2026-05-03 | PASS | Drag-and-drop avatar upload with client-side crop preview | `stack:frontend-react`, `layer:ui`, `domain:forms` | [log](runs/user-profile-avatar-upload/decision-log.md) |
| source-2026-04-cleanup | 2026-05-04 | FAIL | Halted at dependency resolve (registry auth 401) | `layer:infra`, `infra:nexus` | [log](runs/source-2026-04-cleanup/decision-log.md) |
```

## Guardrails
- One row per story. Update in place; do not append duplicates.
- Summary ≤120 chars. No paragraphs.
- Link must resolve — verify the target file exists before committing the row.
- Do not duplicate rationale from the decision log; the index points, it does not re-state.
- Keep the file sortable by date (most recent last, or most recent first — pick one and stay consistent).

## Library and authority

Resolve `docs/`, `agents/` and `skills/` references from the Forge library root. Resolve `{project_root}` against the selected target. Read `AGENTS.md` and `skills/README.md`; load only relevant references. Inherit the caller's stage, tool permissions and write scope; read-only reviewers report findings. Return control to the caller.
