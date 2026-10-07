---
name: skill-project-scaffold
description: "Bootstrap or align project structure when a task requires new modules, new packages, or build/config skeletons. Keeps scaffolding minimal and task-scoped. Use when this capability is relevant to the assigned stage and target stack."
---

# Skill: skill-project-scaffold

## Purpose
Bootstrap or align project structure when a task requires new modules, new packages, or build/config skeletons. Keeps scaffolding minimal and task-scoped.

**Stack-agnostic.** The checklist below is expressed in neutral terms (entry point, config, test skeleton, migration location). Translate to the idiomatic layout of the stack declared in `run-context.md > stack`. A non-exhaustive mapping:

| Neutral term | Java/Spring | Node/TS | Python | Go | React/Next |
| --- | --- | --- | --- | --- | --- |
| manifest | `pom.xml` / `build.gradle` | `package.json` | `pyproject.toml` | `go.mod` | `package.json` |
| source root | `src/main/java/` | `src/` | `src/<pkg>/` or `<pkg>/` | `pkg/`, `internal/` | `src/` or `app/` |
| test root | `src/test/java/` | `src/**/*.test.ts` or `tests/` | `tests/` | `*_test.go` co-located | `src/**/*.test.tsx` |
| config | `src/main/resources/` | `config/` or env files | `settings.py` / `.env` | embed or `config/` | `.env`, `next.config.js` |
| migration | `src/main/resources/db/migration/` | `drizzle/` / `prisma/migrations/` | `alembic/versions/` | `migrations/` | n/a |

## When invoked
- By `ai-pipeline-green-code` when a task introduces a new module, new top-level package, or requires build config changes.
- Never for ordinary tasks inside an existing module — those use the existing structure.

## Reads
- `docs/conventions/backend-conventions-general.md` (when stack is backend)
- Any stack-specific style / testing conventions under `docs/conventions/`
- `docs/agent/learnings.json` (filter by `stack:*`, `build:*`, `tooling:*`, `scaffolding:*`)
- Existing modules / projects — to match the chosen parent pattern

## Writes
- Manifest / build file for the stack (see mapping table above)
- Package skeletons under `{project_root}` using the stack's canonical source and test layouts
- `docs/agent/runs/{story_id}/decision-log.md` for setup choices

## Scaffolding Checklist

### 1. Inherit before inventing
- If a parent module / workspace / BOM / monorepo root exists, inherit from it. Do not duplicate dependency versions.
- For multi-module builds: the new module's manifest references the parent; versions come from the parent's dependency-management block (Maven `<dependencyManagement>`, npm workspace root, pnpm workspace, Gradle version catalog, `go.work`, Cargo workspace).

### 2. Package / folder naming
- Follow the existing root package / import path used by the project.
- Use the stack's idiomatic sub-structure — e.g., for a backend service: `api/controller`, `api/dto`, `domain/service`, `domain/model`, `infra/repository`, `infra/client`, `infra/config`, `infra/security`, `common/exception`, `common/util`. For a frontend: `components/`, `hooks/`, `routes/` or `app/`, `lib/`, `styles/`.
- Do not create sub-packages speculatively; add them when the first real file needs them.

### 3. Minimum viable skeleton
Only create what the task actually needs. Defer the rest.

- Manifest file (see mapping table)
- One entry point if the module is executable (e.g., `*Application.java` with `@SpringBootApplication`, `src/index.ts`, `main.go`, `manage.py`)
- One canonical config file with `local`/`development` defaults; environment overrides come later
- Empty test root; no fixture files until a test needs them
- `.gitignore` additions only if module-specific (build outputs, lockfiles are usually covered at repo root)

### 4. Build + profile config
- Define the stack's equivalents of `local`, `test`, `int`, `prod` profiles via the canonical mechanism (Spring profiles, `NODE_ENV` + dotenv, `APP_ENV`, Go build tags, `cargo --profile`).
- Wire a coverage tool with the project's target threshold (JaCoCo / c8 / Istanbul / coverage.py / `go test -cover`). Record the threshold in decision-log if the project has no prior target.
- No disabled tests, no skipped coverage checks.

### 5. Integration points
- Migration folder only if the module owns a schema (see mapping table).
- API contract file (OpenAPI / GraphQL schema / proto) location aligned with existing modules.
- Observability config (logging, tracing) inherited from parent where possible.

### 6. Testing scaffold
- Add one smoke test per module type. Examples:
  - Spring Boot application module → `@SpringBootTest` context-loads
  - Spring API module → `@WebMvcTest` hits one endpoint
  - Node service → one Vitest/Jest test that imports the entry point and asserts boot
  - Next.js app → one Playwright/Vitest smoke test rendering the root route
  - Go service → `TestMain` that wires the server and pings `/health`
- Do not generate placeholder tests that assert nothing — smoke tests must actually verify something minimal.

## Anti-patterns

- **Do not** generate empty interfaces/classes/components "for future use."
- **Do not** copy a neighbor module wholesale — copy only the pieces the task requires.
- **Do not** add optional starters / plugins / packages "just in case". Add when a test requires them.
- **Do not** create a new parent/BOM/workspace root without explicit architect approval; flag `[UNCERTAIN]` instead.

## Output format

```
YYYY-MM-DDThh:mm:ssZ | agent: ai-pipeline-green-code | skill: skill-project-scaffold
decision: created module {name} with {packages/files}
rationale: {task requires ... / inherited from {parent}}
parent_manifest: {path}
deferred: {list of things explicitly NOT created, for future tasks}
```

## Guardrails
- Keep bootstrap minimal and task-scoped.
- No stage updates from this skill.
- No cross-module refactors; if the task needs them, halt and escalate.
- If a standard convention is missing in `docs/conventions/` for the target stack, flag `[UNCERTAIN]` — do not invent a new one.

## Library and authority

Resolve `docs/`, `agents/` and `skills/` references from the Forge library root. Resolve `{project_root}` against the selected target. Read `AGENTS.md` and `skills/README.md`; load only relevant references. Inherit the caller's stage, tool permissions and write scope; read-only reviewers report findings. Return control to the caller.
