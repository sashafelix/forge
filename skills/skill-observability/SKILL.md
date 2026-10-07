---
name: skill-observability
description: "Add or validate logs/metrics/traces for key backend business flows. Use when this capability is relevant to the assigned stage and target stack."
---

# Skill: skill-observability

## Purpose
Add or validate logs/metrics/traces for key backend business flows.

## Reads
- `docs/conventions/backend-conventions-general.md`
- `docs/conventions/backend-conventions-quality-ops.md`
- `docs/conventions/backend-conventions-security.md`

## Writes
- observability code/config changes in scope
- decision notes in `docs/agent/runs/{story_id}/decision-log.md`

## Conventions

### Correlation ID
- Every request must have a correlation ID (trace ID).
- For the Spring Boot 3 reference stack, use Micrometer Tracing with a supported bridge. Sleuth belongs to older Boot integrations; follow the target project’s dependency management. See [Spring Boot tracing](https://docs.spring.io/spring-boot/3.5/reference/actuator/tracing.html).
- Include correlation ID in all log entries and error responses.
- Header: `X-Correlation-ID` or `X-Request-ID`.

### Structured Logging
Use SLF4J with structured key-value pairs:
```java
log.info("Processing order", kv("orderId", orderId), kv("userId", userId));
```

Required log fields for business events:
| Field | Description |
|-------|-------------|
| `correlationId` | Request trace ID |
| `action` | Business action name |
| `entityType` | Entity being acted on |
| `entityId` | Entity identifier |
| `outcome` | success / failure |
| `durationMs` | Processing time (for perf-critical flows) |

### Log Levels
| Level | Use for |
|-------|---------|
| ERROR | Unexpected failures requiring attention |
| WARN | Recoverable issues, degraded behavior |
| INFO | Business events, request summaries |
| DEBUG | Detailed flow for troubleshooting |
| TRACE | Very verbose, usually disabled in prod |

### Sensitive Data Redaction
Choose allowed non-sensitive log fields first. Omit or explicitly mask sensitive fields and test the rendered log output. The `LogSanitizer` example only replaces control characters to limit log injection; it is not a PII/secret redactor. Do not log raw request objects.

Never log:
- Passwords, tokens, secrets
- Full credit card numbers
- Personal identifiers (SSN, etc.)
- Raw request bodies containing PII

### Metrics
- Use Micrometer for custom metrics.
- Use the target project’s metric namespace (for example, `orders.order.created`); `ai_pipeline` is not a required namespace for applications using this pipeline.
- Tag with relevant dimensions (status, type, etc.).

### Error Events
For error logging, always include:
```java
log.error("Failed to process order", kv("orderId", orderId), kv("errorType", e.getClass().getSimpleName()), e);
```

## Guardrails
- No sensitive data in telemetry.
- Keep diagnostics actionable and low-noise.
- Test that correlation IDs propagate through async flows.
- Verify redaction in log output for sensitive fields.






## Library and authority

Resolve `docs/`, `agents/` and `skills/` references from the Forge library root. Resolve `{project_root}` against the selected target. Read `AGENTS.md` and `skills/README.md`; load only relevant references. Inherit the caller's stage, tool permissions and write scope; read-only reviewers report findings. Return control to the caller.
