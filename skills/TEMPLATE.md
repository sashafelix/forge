# Skill template

Create `skills/<name>/SKILL.md` with this frontmatter, followed by the instructions below:

```yaml
---
name: skill-example
description: "Describe the capability and concrete situations when it applies."
---
```

Use this as a scaffold for new skills. Skills are reusable capabilities invoked by stage agents; they do not own stage transitions. State up-front whether the skill is stack-neutral or stack-specific.

## Purpose
One-line capability summary.

## Applicability
- Stack-neutral **or** stack-specific (`stack:backend-*`, `stack:frontend-*`, …). State explicitly.
- Invoked by: list the stage agents that call this skill.

## Reads
- Convention and context files required.
- `run-context.md` to pick up `project_root`, `stack`, `scope_tags`.

## Writes
- Files this skill may update (use `{project_root}` — never hardcoded paths).
- Optional `decision-log.md` entries with rationale.

## Authority
- Inherit the caller’s stage/role and immutable context; never widen permissions.
- Writes below are conditional on the caller’s authority. VERIFY helpers only inspect and report.
- Use canonical JSON artifacts for decisions; Markdown is a projection. Apply only conventions relevant to the target stack.

## Guardrails
- No stage ownership — return control to the caller.
- No out-of-scope changes.
- No hardcoded secrets, URLs, or env-specific values.




