---
name: skill-integration
description: "Implement resilient adapters for external systems (message brokers, object storage, REST APIs, SFTP). Keep the adapter layer thin, the domain layer ignorant of transport, and behavior predictable under failure. Use when this capability is relevant to the assigned stage and target stack."
---

# Skill: skill-integration

## Purpose
Implement resilient adapters for external systems (message brokers, object storage, REST APIs, SFTP). Keep the adapter layer thin, the domain layer ignorant of transport, and behavior predictable under failure.

## When invoked
- By `ai-pipeline-green-code` when a story touches an external system.
- By `ai-pipeline-refactor` when an existing adapter has drift (retry pattern inconsistent, timeout missing, etc.).

## Reads
- `docs/conventions/backend-conventions-general.md`
- `docs/conventions/backend-conventions-integration.md`
- `docs/conventions/backend-conventions-security.md`
- `docs/agent/learnings.json` (filter by `integration:*`, `infra:*`)
- External contract specs (OpenAPI, Avro, WSDL, XSD)
- Direct sources: linked security standards for auth rules and explicitly scoped Confluence/repository documents for integration architecture

## Writes
- Integration adapters/clients and tests in scope
- Decision notes in `docs/agent/runs/{story_id}/decision-log.md`

## Adapter Anatomy

Every external integration has:

1. **Client interface** — domain-friendly method names, domain types in/out. Lives in domain package.
2. **Adapter implementation** — translates domain types ↔ external types, handles transport. Lives in infra package.
3. **Client config** — timeouts, retries, auth, base URL — externalized, profile-aware.
4. **Contract types** — external DTOs in their own subpackage, never leaking into domain.
5. **Mapper** — adapter ↔ domain mapping (MapStruct per `skill-entity-mapping`).
6. **Tests** — contract test + resilience test + integration test with a test double.

## Resilience Checklist

### 1. Timeouts (mandatory)
- Connect timeout + read timeout set explicitly. No infinite waits.
- Default: connect 2s, read 5s. Override per-call when story requires.
- No timeout = not production-ready. Fail the checklist.

### 2. Retries
- Only idempotent operations retry automatically (GET, PUT with idempotency key, DELETE).
- Non-idempotent (POST without idempotency) requires explicit caller decision in decision-log.
- Exponential backoff with jitter. Max retry count bounded (default 3).
- No retry on 4xx (client error) except 429 (rate limit) and 408 (timeout).

### 3. Circuit breaker / bulkhead
- For high-volume downstreams, use a circuit breaker (Resilience4j).
- Fallback behavior must be explicit: cached response, default value, or fail-fast.
- Silent fallback that masks downstream outages is a bug — surface it in logs + metrics.

### 4. Idempotency
- Outbound POST: include idempotency key in header or body where the downstream supports it.
- Inbound POST: accept idempotency key; return same response for replay within TTL.
- Log the idempotency key (sanitized) for correlation.

### 5. Authentication
- Token refresh handled by the client, not by the caller.
- Token never logged, never cached in memory beyond its TTL.
- mTLS: certificates from secure store, not file system constants.

### 6. Payload size + streaming
- Large payloads (>10MB): stream, do not buffer.
- Reject oversized inbound payloads at the edge with 413.
- Compress outbound where the downstream supports it.

## Test Strategy

### Contract test
- Verifies the adapter speaks the external contract correctly.
- Uses a recorded/stubbed response (WireMock, MockServer) or a schema validator.

### Resilience test
- Adapter behavior under: downstream 500, timeout, connection refused, slow response.
- Assert retries happen (and stop at max), circuit opens, fallback activates.

### Integration test
- End-to-end via Testcontainers or an in-process test double.
- Never hits real external systems in CI.

Example structure:

```java
@WireMockTest
class OrderClientAdapterTest {

  @Test
  void getOrder_downstreamReturns500_retriesThenFails() { ... }

  @Test
  void getOrder_downstreamSlowerThanTimeout_throwsTimeout() { ... }

  @Test
  void getOrder_circuitOpen_returnsFallback() { ... }
}
```

## Secrets + Config

- Base URL, credentials, certificates → environment variables or secret store.
- No hardcoded endpoints (including "localhost" defaults that ship to prod by accident).
- Profile-specific config: `local` points to a mock/stub; `prod` points to the real endpoint.

## Output format

```
YYYY-MM-DDThh:mm:ssZ | agent: ... | skill: skill-integration
decision: added/modified adapter for {system}
rationale: {what external interaction was needed}
retry_policy: {max retries, backoff}
timeout: {connect/read}
fallback: {behavior on downstream failure}
tests: {contract + resilience + integration test class names}
```

## Guardrails
- No hardcoded credentials, endpoints, or certificates.
- Explicit retry/backoff/idempotency behavior; no silent defaults.
- Deterministic integration test doubles — no real network in tests.
- Domain layer stays ignorant of HTTP/Kafka/S3 — only the adapter layer knows transport.
- If the external contract is unclear or unversioned, halt and escalate — do not guess the shape.

## Library and authority

Resolve `docs/`, `agents/` and `skills/` references from the Forge library root. Resolve `{project_root}` against the selected target. Read `AGENTS.md` and `skills/README.md`; load only relevant references. Inherit the caller's stage, tool permissions and write scope; read-only reviewers report findings. Return control to the caller.
