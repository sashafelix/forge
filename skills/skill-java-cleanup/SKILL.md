---
name: skill-java-cleanup
description: "Improve Java code structure, readability, and maintainability during the REFACTOR stage, without changing behavior. Use when this capability is relevant to the assigned stage and target stack."
---

# Skill: skill-java-cleanup

## Purpose
Improve Java code structure, readability, and maintainability during the REFACTOR stage, without changing behavior.

## When invoked
- By `ai-pipeline-refactor` after GREEN passes.
- Only on files the story actually touched. Do not expand scope.

## Reads
- `docs/conventions/backend-conventions-general.md`
- `docs/conventions/backend-conventions-java-style.md`
- `docs/agent/learnings.json` (filter by `tooling:java`, `style:*`)
- Files in refactor scope + their direct callers

## Writes
- Refactor-only Java code changes in scope
- Rationale in `docs/agent/runs/{story_id}/decision-log.md` for non-trivial changes

## Cleanup Checklist

Work through these against the touched files:

### 1. Dead code
- Remove methods, fields, imports, constants that have zero callers inside the module.
- Remove commented-out code blocks. If it matters, it's in git.
- Remove stale `TODO` / `FIXME` / `XXX` comments. If the TODO is real, file a ticket; if not, delete.
- Remove unused exception declarations (`throws X` that is never thrown).

### 2. File size (>300 LOC)
- Flag every file over 300 LOC (excluding generated code and tests).
- Split when the split is natural: extract inner static classes, split by responsibility, move DTOs to their own files.
- If a split would be forced or cross-cutting, log `[UNCERTAIN]` in decision-log and leave it.

### 3. Method size and SRP
- Methods over ~30 LOC or ~3 nested levels are candidates for extraction.
- Extracted methods must have a clear single-responsibility name (not `helperMethod1`).
- Do not extract just to hit a line count — extraction must improve readability.

### 4. Rule of Three (anti-premature-abstraction)
- A shared base class, interface, or generic helper requires **3+ concrete callers** before extraction.
- If you see an abstraction with 1–2 callers, inline it back.
- Speculative abstractions ("we'll need this later") are deleted.

### 5. Naming
- Variables, fields, methods: names match what the thing *is*, not what it *does internally*.
- Prefer `orders` over `orderList`, `isValid` over `checkValidity`, `customerId` over `cid`.
- Rename local variables freely; rename public API members only with cross-module impact check.

### 6. Visibility + immutability
- Prefer `private` / `package-private` over `public` for internal helpers.
- Prefer `final` fields + constructor injection (`@RequiredArgsConstructor`).
- Prefer immutable collections / records for DTOs where conventions allow.

### 7. Exception handling hygiene
- No empty `catch` blocks. No `catch (Exception e) { log.error(e); }` that silently swallows.
- Rethrow or translate to domain-specific exceptions per `skill-exception-handling`.
- Exception messages must be actionable — include the failing inputs (sanitized).

### 8. Log hygiene
- No `System.out.println`, no `printStackTrace`, no `e.printStackTrace()`.
- Use structured logging per `skill-observability`. Include correlation IDs.
- Never log secrets, tokens, PII or full request bodies. Omit/mask sensitive fields; use `LogSanitizer` only for control characters in approved non-sensitive fields.

### 9. Stream + Optional usage
- Streams for transformation, not for side effects. No `.forEach(x -> someField += ...)`.
- `Optional` for return values, not for fields or parameters.
- Avoid `.orElse(expensiveCall())` — use `.orElseGet(() -> ...)` when the fallback is expensive.

### 10. Test hygiene touch-up
- Rename tests to `method_condition_expectedBehavior` if GREEN left inconsistent names.
- Remove assertion duplication within a test (one test = one story).
- Extract obvious test data builders only when reused 3+ times.

## Output format

Record in `decision-log.md` for non-trivial cleanups:

```
YYYY-MM-DDThh:mm:ssZ | agent: ai-pipeline-refactor | skill: skill-java-cleanup
decision: {what was changed}
rationale: {why — which checklist item}
files: {list}
behavior_preserved_by: {which tests cover this code}
```

## Guardrails
- No behavior changes. Ever. If the test suite output changes, you broke something.
- No API/DB contract drift.
- No renaming of public methods, DTO fields, or DB columns without explicit approval.
- Test structure/names may be cleaned up through `skill-test-maintenance` if assertions, scenario coverage and observable intent are preserved. Stop if making a refactor pass requires weakening or changing expected behavior.
- If unsure whether a cleanup is safe, leave the code and log `[UNCERTAIN]`.

## Library and authority

Resolve `docs/`, `agents/` and `skills/` references from the Forge library root. Resolve `{project_root}` against the selected target. Read `AGENTS.md` and `skills/README.md`; load only relevant references. Inherit the caller's stage, tool permissions and write scope; read-only reviewers report findings. Return control to the caller.
