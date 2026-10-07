---
name: skill-codebase-comprehension
description: "Systematically read and understand existing code before making changes. Ensures agents never write blind. Use when this capability is relevant to the assigned stage and target stack."
---

# Skill: skill-codebase-comprehension

## Purpose
Systematically read and understand existing code before making changes. Ensures agents never write blind.

## When invoked
- At the start of GREEN and REFACTOR stages, before any file writes.
- Optionally by RED stage when test targets touch complex existing code.

## Reads
- The caller’s immutable context manifest and, once available, `docs/agent/runs/{story_id}/detailed-plan.json` (to identify locked change scope)
- Applicable stack conventions; `docs/conventions/backend-conventions-general.md` only for backend work
- Files in the change scope and direct dependencies permitted by the context manifest

## Writes
- Comprehension summary appended to `docs/agent/runs/{story_id}/decision-log.md`

## Steps
1. Identify permitted scope from the context manifest and locked `detailed-plan.json`. If called before PLAN, use the permitted PREPARE/intent context; do not invent a plan.
2. Read each file and its direct dependencies (imports, called services, injected beans).
3. Trace the relevant call/data flow (for example, controller → service → repository in a backend, or component → state → API in a frontend).
4. Search the codebase for similar patterns (naming, structure, error handling, test style).
5. Identify: existing utilities to reuse, patterns to match, anti-patterns to avoid.
6. Document findings as a brief comprehension summary in the decision-log.

## Output format
```markdown
### Comprehension Summary
- **Files read**: [list]
- **Call chain**: [traced path]
- **Patterns to follow**: [list existing conventions observed]
- **Reusable utilities found**: [list or "none"]
- **Risks/conflicts with plan**: [list or "none"]
```

## Guardrails
- Do not write any production or test code during comprehension.
- Flag any conflicts between the plan and existing code structure.
- If the codebase has no prior examples for the planned pattern, note it explicitly.


## Library and authority

Resolve `docs/`, `agents/` and `skills/` references from the Forge library root. Resolve `{project_root}` against the selected target. Read `AGENTS.md` and `skills/README.md`; load only relevant references. Inherit the caller's stage, tool permissions and write scope; read-only reviewers report findings. Return control to the caller.
