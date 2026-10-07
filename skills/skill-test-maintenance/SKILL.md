---
name: skill-test-maintenance
description: "Keep backend tests stable, readable, and deterministic. Invoked during REFACTOR and whenever test code itself is the target of change. Use when this capability is relevant to the assigned stage and target stack."
---

# Skill: skill-test-maintenance

## Purpose
Keep backend tests stable, readable, and deterministic. Invoked during REFACTOR and whenever test code itself is the target of change.

## When invoked
- By `ai-pipeline-refactor` when test code needs cleanup alongside production refactors.
- By `ai-pipeline-red-test` when the existing test suite has rot that blocks writing new tests (flaky tests, copy-paste, hidden production logic).
- Never to alter what a test *asserts* — that is a behavior change, not maintenance.

## Reads
- `docs/conventions/backend-conventions-general.md`
- `docs/conventions/backend-conventions-testing-style.md`
- `docs/agent/learnings.json` (filter by `testing:*`)
- Tests in scope + the production code they cover

## Writes
- Test updates in scope
- Non-obvious strategy updates in `docs/agent/runs/{story_id}/decision-log.md`

## Determinism Checklist

### 1. No wall-clock dependence
- No `LocalDateTime.now()` in asserts. Use an injected `Clock` or a fixed test instant.
- No "ran within 5 seconds" timeouts as success criteria.

### 2. No network / external process dependence
- No real HTTP calls. Use `@MockBean`, WireMock, or Testcontainers.
- No real database except via Testcontainers (documented in the test class).
- No `Thread.sleep` — use Awaitility or synchronous test doubles.

### 3. No cross-test state
- Each test must set up its own data. No relying on state from a previous test.
- `@DirtiesContext` only as a last resort (it's slow).
- No static mutable state leaking between tests.

### 4. Deterministic ordering
- No assertions on collection order unless the collection is inherently ordered (e.g., a sorted query result).
- Use `assertThat(list).containsExactlyInAnyOrder(...)` when order is incidental.

### 5. One test, one story
- A test with 5 assertions about 3 different concerns is 3 tests pretending to be one.
- Split them. Name each after the specific condition + expected behavior.

## Readability Checklist

### 1. Naming
- `methodUnderTest_condition_expectedBehavior` per conventions.
- The test name alone should tell the reader what scenario and outcome.

### 2. Arrange / Act / Assert blocks
- Three visually distinct sections per test, separated by blank lines or comments.
- No arrange work mixed into asserts.

### 3. Test data builders
- Use builders when the same test fixture appears 3+ times. Not before.
- Builders in `test/` only; never leaking into `main/`.
- Builder defaults should be "valid" — tests override what's relevant to the scenario.

### 4. Assertion style
- Prefer AssertJ `assertThat(x).isEqualTo(y)` over JUnit `assertEquals(y, x)`.
- Use specific matchers: `.hasSize(n)`, `.contains(x)`, `.isInstanceOf(X.class)`.
- Custom assertions only when they'd be reused 3+ times.

## "Don't mock what you don't own"
- Mock boundaries you control (your services, your repositories).
- Do not mock `java.time`, `java.util`, JDBC, HTTP clients, filesystem — use fakes, test doubles, or Testcontainers.
- External integrations: use WireMock / Testcontainers, not plain `@MockBean`.

## Test Strategy Changes
If you change *how* tests verify something (e.g., swap a unit test for an integration test), log it:

```
YYYY-MM-DDThh:mm:ssZ | agent: ... | skill: skill-test-maintenance
decision: swap {old strategy} → {new strategy}
rationale: {why — flakiness, coverage gap, contract drift}
preserved_SCs: {list of SC-{n} still verified}
```

## Guardrails
- Preserve behavior intent from RED tests. If the original test asserted X, the refactored test still asserts X.
- Never delete a test to make the suite green. Fix the production code or flag `[UNCERTAIN]`.
- Never add `@Ignore` / `@Disabled` as a shortcut. If a test is disabled, there must be a linked ticket + rationale.
- Flaky tests are bugs — fix the determinism, don't add retries.

## Library and authority

Resolve `docs/`, `agents/` and `skills/` references from the Forge library root. Resolve `{project_root}` against the selected target. Read `AGENTS.md` and `skills/README.md`; load only relevant references. Inherit the caller's stage, tool permissions and write scope; read-only reviewers report findings. Return control to the caller.
