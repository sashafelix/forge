---
name: skill-compliance
description: "Capture traceable evidence for security, quality, and release controls. Every compliance claim must link to a specific file, test, commit, or contract. Use when this capability is relevant to the assigned stage and target stack."
---

# Skill: skill-compliance

## Purpose
Capture traceable evidence for security, quality, and release controls. Every compliance claim must link to a specific file, test, commit, or contract.

## When invoked
- By `ai-pipeline-quality-gate` during VERIFY, before CONVERGE.
- By `ai-pipeline-green-code` when a story touches a regulated concern (auth, PII, audit logging, cryptography, financial data).

## Reads
- `docs/conventions/backend-conventions-general.md`
- `docs/conventions/backend-conventions-quality-ops.md`
- `docs/conventions/backend-conventions-security.md`
- `docs/agent/learnings.json` (filter by `compliance:*`, `security:*`, `audit:*`)
- Run folder: canonical `quality-gates.json`, `brainstorm.json`, stage results and append-only handoff/decision records
- Direct sources: linked security/IAM/AI standards, supplied documents, or repository Markdown; retain the exact file/page/URL reference

## Writes
- Compliance notes in `docs/agent/runs/{story_id}/decision-log.md`
- Evidence references recorded in canonical gate/stage artifacts; the calling agent projects the summary into `quality-gates.md`. During VERIFY, do not edit story code.

## Evidence Checklist

Every entry below must have a concrete link (file path, test name, commit, migration ID, direct-source reference). No hand-wavy "we follow the standard" claims.

### 1. Security controls
- [ ] Authentication required on new endpoints? Proof: configured authentication entry point and an unauthenticated-request test; `@PreAuthorize` concerns method authorization and requires method security to be enabled.
- [ ] Authorization correct per role? Proof: positive + negative test per role.
- [ ] Input validation? Proof: `@Valid` annotation + negative test for invalid payload.
- [ ] Output sanitization for sensitive data? Proof: explicit omission/masking policy and assertions on actual output. Newline sanitization alone does not redact secrets or PII.
- [ ] Secrets handling? Proof: env-var reference, no literal in config.

### 2. Audit + traceability
- [ ] Audit log entry for regulated operations? Proof: logger call + test asserting log output.
- [ ] Correlation ID propagated? Proof: `skill-observability` configuration + integration test.
- [ ] Created/updated columns on new entities per `backend-conventions-entity-mapping`? Proof: migration DDL.

### 3. Data handling
- [ ] PII/PHI fields identified? Proof: list in decision-log.
- [ ] PII not logged? Proof: allowed log fields or explicit masking plus negative tests for sensitive values.
- [ ] PII not returned in public-facing DTOs? Proof: DTO shape review + contract test.
- [ ] Data retention rule considered? Proof: cleanup job, TTL, or explicit decision-log entry "not applicable because ...".

### 4. Contract compatibility
- [ ] OpenAPI diff checked? Proof: `skill-contract-guard` output in handoff.
- [ ] DB migration backward-compatible? Proof: migration type in `skill-database` safety matrix.
- [ ] Event schema (Kafka) backward-compatible? Proof: schema registry diff.

### 5. Test evidence (mandatory matrix)
- [ ] Unit tests cover changed business logic.
- [ ] Integration test if external systems involved.
- [ ] Security test if authz touched.
- [ ] Coverage ≥ the recorded project threshold on touched modules (no regression).

### 6. Release-readiness
- [ ] Feature flag required? Documented + test asserts both states.
- [ ] Rollback plan? Documented in `skill-devops` evidence or decision-log.
- [ ] Dependencies on other services/stories? Documented with story IDs.

## Evidence Summary Block

The calling agent inserts this into `quality-gates.md`:

```markdown
## Compliance Evidence

| Control | Status | Evidence |
| --- | --- | --- |
| AuthN on endpoint | ✓ | `OrderControllerTest#create_unauthenticated_returns401` |
| AuthZ per role | ✓ | `OrderControllerTest#create_asClerk_returns403` |
| Input validation | ✓ | `OrderControllerTest#create_invalidPayload_returns400` |
| Audit log | ✓ | `OrderServiceTest#create_logsAuditEntry` |
| PII sanitization | ✓ | `OrderLoggingTest#omitsCustomerIdentifiers` |
| OpenAPI compatible | ✓ | `skill-contract-guard` output → `handoff.md` |
| Coverage ≥ the recorded project threshold | ✓ | JaCoCo report → `target/site/jacoco/` |
```

Every failed control needs a blocking finding and evidence. Only non-correctness preferences may be WARN with rationale; an approval note cannot waive a required security or correctness gate.

## Guardrails
- Evidence must be traceable to a file, test, or commit. "We followed the standard" is not evidence.
- No PASS claim without specific proof.
- No skipping an item; if inapplicable, explicitly state "N/A because {reason}" in decision-log.
- If a control conflicts with the story scope (e.g., PII rule blocks a feature), halt and escalate — do not silently downgrade.

## Library and authority

Resolve `docs/`, `agents/` and `skills/` references from the Forge library root. Resolve `{project_root}` against the selected target. Read `AGENTS.md` and `skills/README.md`; load only relevant references. Inherit the caller's stage, tool permissions and write scope; read-only reviewers report findings. Return control to the caller.
