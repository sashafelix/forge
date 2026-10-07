---
name: skill-devops
description: "Apply CI/CD, pipeline, and runtime/deployment configuration changes that fall within backend story scope. Keeps deploy concerns explicit and traceable. Use when this capability is relevant to the assigned stage and target stack."
---

# Skill: skill-devops

## Purpose
Apply CI/CD, pipeline, and runtime/deployment configuration changes that fall within backend story scope. Keeps deploy concerns explicit and traceable.

## When invoked
- By `ai-pipeline-green-code` or `ai-pipeline-quality-gate` when a story requires pipeline, Helm, Dockerfile, or profile/config changes.
- Only when deployment surface is affected — not for ordinary code changes.

## Reads
- `docs/conventions/backend-conventions-general.md`
- `docs/conventions/backend-conventions-quality-ops.md`
- `docs/agent/learnings.json` (filter by `infra:*`, `deploy:*`, `ci:*`, `secrets:*`)
- Existing pipeline / Helm / Dockerfile / profile config
- Runtime requirements in `brainstorm.json` or `detailed-plan.json`

## Writes
- Pipeline, Helm, Dockerfile, profile config files in scope
- Deploy decisions in `docs/agent/runs/{story_id}/decision-log.md`

## Checklist

### 1. Environment separation
- Every config change must be profile-aware: `local`, `test`, `int`, `prod`.
- No prod-only values in shared config. Externalize via environment variables or Spring profiles.
- Profile activation must be explicit (via `spring.profiles.active`), never implicit.

### 2. Secrets
- Never hardcode credentials, tokens, API keys, DB passwords, or certificates.
- Reference secrets via env vars, Vault paths, Kubernetes Secrets, or the platform's secret manager.
- If you see a hardcoded secret during the change, flag it in decision-log and escalate — do not silently fix and deploy.

### 3. Image + dependency pinning
- Docker images pinned to a specific tag or digest. No `:latest`.
- Base image aligned with the team standard (documented or inherited from parent image).
- Resolve new dependencies through the project’s approved registries/mirrors. Revalidate any learned configuration; never use learned credential workarounds or bypass access controls.

### 4. Resource + runtime limits
- Memory/CPU requests and limits set explicitly (Kubernetes).
- JVM flags (`-Xmx`, `-XX:+UseG1GC` etc.) consistent with `quality-ops` conventions.
- No change to resource limits without load-test or quality-gate evidence.

### 5. Health + readiness
- Use the target platform’s probe contract. In the Spring Boot reference with health probes enabled, the default paths are `/actuator/health/liveness` and `/actuator/health/readiness`; `/actuator/health` is aggregate health. See [Actuator endpoints](https://docs.spring.io/spring-boot/reference/actuator/endpoints.html).
- If probes require unauthenticated access, expose only the exact probe endpoints on an appropriately restricted network; never permit all `/actuator/**` endpoints by default.
- Deploy rollout blocks on readiness probe — document expected readiness time.

### 6. Observability at deploy layer
- Logs route to the configured aggregator (Logstash / ELK) per `skill-observability`.
- Metrics endpoint exposed for Prometheus scrape.
- Correlation ID propagation preserved across services.

### 7. CI/CD changes
- Pipeline step changes are minimal and reversible.
- New required checks must not be skippable (no `continue-on-error: true` for merge gates).
- Cache keys include dependency fingerprints — no stale caches silently passing.

### 8. Rollback story
- Every deploy change has a documented rollback: previous tag, revert migration (if DB), config snapshot.
- If a change is not safely rollback-able (e.g., destructive migration), it needs explicit approval in decision-log.

## Output format

```
YYYY-MM-DDThh:mm:ssZ | agent: ... | skill: skill-devops
decision: {what was changed}
rationale: {why}
affected_envs: [local|test|int|prod]
secrets_touched: {y/n + path}
rollback_plan: {steps}
```

## Guardrails
- Environment separation required — no cross-env leakage.
- Reference secrets; never hardcode.
- No production deploy from this skill — only prepare config; the deploy trigger is a human/CI concern.
- If a change affects more than the story scope (e.g., shared pipeline), pause and escalate in decision-log.

## Library and authority

Resolve `docs/`, `agents/` and `skills/` references from the Forge library root. Resolve `{project_root}` against the selected target. Read `AGENTS.md` and `skills/README.md`; load only relevant references. Inherit the caller's stage, tool permissions and write scope; read-only reviewers report findings. Return control to the caller.
