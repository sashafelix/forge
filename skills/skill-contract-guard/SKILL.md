---
name: skill-contract-guard
description: "Detect and classify API/DTO/DB contract changes as breaking or non-breaking. Use when this capability is relevant to the assigned stage and target stack."
---

# Skill: skill-contract-guard

## Purpose
Detect and classify API/DTO/DB contract changes as breaking or non-breaking.

## Reads
- `docs/conventions/backend-conventions-general.md`
- `docs/conventions/backend-conventions-api-service.md`
- `docs/conventions/backend-conventions-database.md`
- OpenAPI spec (current + baseline)
- DTO classes (request/response)
- Flyway migrations (current + baseline)

## Writes
- compatibility decision to `docs/agent/runs/{story_id}/decision-log.md`
- gate evidence block via calling agent

## Compatibility Checklist

### OpenAPI Contract
| Check | Breaking if... | Verdict |
|-------|----------------|---------|
| Endpoint removed | Yes | FAIL |
| Endpoint path changed | Yes | FAIL |
| Required field added to request | Yes | FAIL |
| Required field removed from response | Yes | FAIL |
| Field type changed | Yes | FAIL |
| Optional field added to response | No | PASS |
| Optional field added to request | No | PASS |
| New endpoint added | No | PASS |

### DTO Contract
| Check | Breaking if... | Verdict |
|-------|----------------|---------|
| Field renamed | Yes | FAIL |
| Field type changed | Yes | FAIL |
| Field removed from response | Yes | FAIL |
| Validation constraint tightened | Yes (may reject previously valid input) | FAIL |
| New optional field | No | PASS |

### Database Contract
| Check | Breaking if... | Verdict |
|-------|----------------|---------|
| Column removed | Yes | FAIL |
| Column renamed | Yes | FAIL |
| Column type changed (narrowing) | Yes | FAIL |
| NOT NULL added without default | Yes | FAIL |
| Table removed | Yes | FAIL |
| New column with default | No | PASS |
| New table | No | PASS |
| Index added/removed | No (but document) | PASS |

## Evidence Template
```markdown
## Contract Compatibility Check
- Story: {story_id}
- Date: {date}

### OpenAPI
- [ ] No endpoints removed
- [ ] No breaking request changes
- [ ] No breaking response changes
- Verdict: PASS / FAIL

### DTO
- [ ] No field removals/renames
- [ ] No type changes
- Verdict: PASS / FAIL

### Database
- [ ] No destructive DDL
- [ ] No narrowing type changes
- Verdict: PASS / FAIL

### Overall: PASS / FAIL
### Notes: ...
```

## Guardrails
- Mark breakage explicitly with FAIL verdict.
- Include impact and mitigation notes for any WARN or FAIL.
- Breaking changes require explicit approval in decision log before proceeding.






## Library and authority

Resolve `docs/`, `agents/` and `skills/` references from the Forge library root. Resolve `{project_root}` against the selected target. Read `AGENTS.md` and `skills/README.md`; load only relevant references. Inherit the caller's stage, tool permissions and write scope; read-only reviewers report findings. Return control to the caller.
