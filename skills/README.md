# Canonical skill catalog

Skills are reusable capabilities called by stage agents. Each definition lives once at `skills/<name>/SKILL.md`, with name/description metadata for discovery. Read [AGENTS.md](../AGENTS.md) and load only relevant skill bodies. Resolve library paths from the Forge checkout; target paths come from `{project_root}`. Skills do not own stage transitions.

The pipeline is **stack-agnostic**. Skills fall into two groups:
1. **Shared principles**: apply when relevant, using the target stack’s mechanisms. Many helper examples are Java/Spring-specific.
2. **Stack-specific**: apply only when the target `stack` matches (e.g., Java/Spring backend). The calling agent decides based on `run-context.md > stack` and `scope_tags`.

## Shared helpers (examples may be stack-specific)
- [skill-codebase-comprehension](skill-codebase-comprehension/SKILL.md) — systematic read-and-understand before any write
- [skill-project-scaffold](skill-project-scaffold/SKILL.md) — bootstrap module/project structure (stack-agnostic with mapping table)
- [skill-api-service](skill-api-service/SKILL.md) — HTTP/RPC surface patterns
- [skill-security](skill-security/SKILL.md) — auth/authz + security tests
- [skill-integration](skill-integration/SKILL.md) — resilient external adapters
- [skill-validation](skill-validation/SKILL.md) — input validation at boundaries
- [skill-exception-handling](skill-exception-handling/SKILL.md) — centralized error handling
- [skill-test-maintenance](skill-test-maintenance/SKILL.md) — deterministic, readable tests
- [skill-contract-guard](skill-contract-guard/SKILL.md) — API/DTO/DB compatibility checks
- [skill-observability](skill-observability/SKILL.md) — logs/metrics/tracing quality
- [skill-devops](skill-devops/SKILL.md) — CI/CD + runtime config changes
- [skill-compliance](skill-compliance/SKILL.md) — traceable evidence for release controls
- [skill-decision-index](skill-decision-index/SKILL.md) — compact update of `decision-index.md`

Direct context lookup uses exact repository Markdown/docs, supplied files, or explicitly scoped Jira/Confluence reads. No semantic/vector index or embedding store is part of the pipeline.

## Stack-specific skills (invoke only when the stack matches)
- [skill-database](skill-database/SKILL.md) — SQL migrations + safety matrix *(stacks with a relational persistence layer; Flyway examples, generalizes to Liquibase/Drizzle/Prisma/Alembic)*
- [skill-entity-mapping](skill-entity-mapping/SKILL.md) — entity / repository / DTO / mapper boundaries *(ORM-backed backends)*
- [skill-transaction-policy](skill-transaction-policy/SKILL.md) — transactional boundaries *(backends with DB writes)*
- [skill-java-cleanup](skill-java-cleanup/SKILL.md) — dead code, file size, Rule of Three, naming *(Java-style cleanup; the principles generalize; agent may apply analogous cleanup tools for other stacks if no equivalent skill exists)*

## Conditional helpers and future additions
- [skill-scheduling](skill-scheduling/SKILL.md) — when scheduled tasks / cron jobs are in scope (backend-cron, CI schedules, client polling)
- `skill-caching` *(future)*
- `skill-xml-jaxb` *(future — XML import/export)*
- Frontend-specific skills (`skill-component-patterns`, `skill-state-management`, `skill-a11y`) *(future, as needed)*

## Shared rules
- Follow `AGENTS.md`. Apply `docs/conventions/backend-conventions-general.md` only when the stack is backend.
- Write only within the scope requested by the calling agent.
- Record non-trivial decisions to `docs/agent/runs/{story_id}/decision-log.md` with rationale and related learning IDs.
- Read `docs/agent/learnings.json` at start, **filtered by `scope_tags`** matching the task (especially `stack:*`); append reusable candidate learnings with evidence.
- Use `{project_root}` from run-context for all file paths.
- No skill may unilaterally change stage; return control to the calling agent.

## Shared authority and applicability

Every helper inherits its caller’s stage, role, immutable context and permitted write surfaces. A listed Writes section applies only when that caller has the corresponding authority; helpers used by VERIFY or another read-only role may report findings but must not edit story code. No helper grants deployment or publication rights.

Canonical JSON artifacts and stage/profile contracts take precedence over Markdown projections and illustrative snippets. Java/Spring examples are reference patterns for applicable projects, not dependencies or universal rules of the pipeline. Follow the target project’s approved stack and versions; placeholder classes and omitted setup make examples fragments, not complete applications.
