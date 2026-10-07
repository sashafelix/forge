# Agent & Skill Evaluation: Integrating Superpowers + Karpathy Principles

**Date:** 2026-04-20
**Scope:** Full review of the agent/skill architecture against [obra/superpowers](https://github.com/obra/superpowers) and [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) principles.
**Status:** Historical design review. The original gap analysis and recommendations below describe the April 2026 review, not current runtime requirements. The live stage contracts, canonical JSON schemas and selected workflow profile are authoritative. The current implementation map below replaces the older Markdown-only checklist mapping.

---

## 1. Executive Summary

The agent architecture is **well-structured** with clear stage ownership, deterministic TDD flow, and explicit handoffs. The original review found that several high-impact principles from both source repos were missing. The pipeline has since evolved to nine stages with canonical JSON evidence. Comprehension and incremental checks remain; style heuristics are contextual review guidance, not universal release gates.

### Current implementation map

| Review theme | Current source |
| --- | --- |
| Comprehension and search before edits | RED/GREEN/REFACTOR agent definitions; `skill-codebase-comprehension.md` |
| Incremental verification and self-check evidence | Canonical `stage-result.schema.json` for RED/GREEN/REFACTOR, their stage contracts and instructions |
| Simplicity and pattern reuse | Applicable Java-style conventions and cleanup helper |
| Independent verification and hard failures | VERIFY contract, `quality-gates.schema.json`, selected profile and projection template |
| Blocking uncertainty | BRAINSTORM/ANALYZE contracts and decision-log template |
| Stage order and helper authority | `AGENTS.md`, `skills/README.md` and role contracts |

Extensions added beyond the original review:
- **Brainstorm stage**: declarative SCs now gate planning and RED.
- **Worktree isolation**: every run lives in `.agent-runs/{story_id}` on `story/{story_id}`.
- **Learnings register with `scope_tags` + lifecycle**: candidate → active → deprecated/conflicted.
- **Stack-agnostic framing**: pipeline accepts Jira stories, feature descriptions, free-form requests, or direct-source/supplied-document tasks; target may be backend/frontend/mobile/infra/polyglot.

---

## 2. Principle Mapping & Gap Analysis

### 2.1 Superpowers Principles (obra/superpowers)

| Principle | Status at original review | Gap | Priority |
|-----------|---------------|-----|----------|
| **Read before write** — always read existing code before modifying | Partially implied in conventions | Not enforced in agent instructions | 🔴 HIGH |
| **Verify after every change** — run tests/checks after each edit | Quality gate at end only; no per-edit verification | Missing incremental verification in GREEN/REFACTOR | 🔴 HIGH |
| **Understand before changing** — trace full call chain before edits | Not mentioned in any agent/skill | Missing comprehension step in GREEN agent | 🔴 HIGH |
| **Plan before executing** — break work into steps, state them, then execute | Covered well via detailed-plan.md | ✅ Strong | ✅ OK |
| **Check your work** — self-review before declaring done | Quality gate exists but stage agents don't self-check | Missing self-verification in RED/GREEN/REFACTOR | 🟡 MED |
| **Be explicit about uncertainty** — flag assumptions clearly | Decision-log exists for this | Partially covered; could be stronger | 🟡 MED |
| **Minimal changes** — smallest possible diff | GREEN agent says "minimum" but no explicit diff-size guardrail | Could add explicit single-responsibility-per-commit rule | 🟢 LOW |
| **Don't guess — search** — use tools to find facts, don't assume | bounded repository/source reads available but not mandatory | Should mandate codebase search before writing new code | 🔴 HIGH |
| **One thing at a time** — don't mix concerns in a single change | Covered by story-first + scope boundaries | ✅ Strong | ✅ OK |
| **Preserve existing patterns** — match the style of surrounding code | Conventions exist but no explicit "match neighbors" rule | Add pattern-matching mandate to GREEN/REFACTOR | 🟡 MED |

### 2.2 Karpathy Principles (andrej-karpathy-skills)

| Principle | Status at original review | Gap | Priority |
|-----------|---------------|-----|----------|
| **Write simple, boring code** — avoid cleverness, prefer readability | Java style conventions mention readability | Not explicit enough as a core mandate | 🟡 MED |
| **Avoid premature abstraction** — don't DRY until 3+ duplications | GREEN says "no speculative abstractions" | Good. Could strengthen with Rule of Three | 🟢 LOW |
| **Flat > nested** — reduce nesting, early returns | Java style mentions "return early" | ✅ Covered | ✅ OK |
| **Functions should do one thing** — SRP at function level | Mentioned but not enforced/checked | Add to quality-gate checklist | 🟡 MED |
| **Explicit > implicit** — no magic, clear data flow | GREEN says "prefer explicit code over magic" | ✅ Covered | ✅ OK |
| **Delete dead code aggressively** — no commented-out code | Not mentioned anywhere | Add to REFACTOR and java-cleanup skill | 🟡 MED |
| **Keep files small** — split when files grow too large | Not mentioned | Add file-size awareness to REFACTOR | 🟢 LOW |
| **Name things well** — names should explain intent | Java style says "naming explicit and domain-driven" | ✅ Covered | ✅ OK |
| **Write tests that test behavior, not implementation** — black-box tests | Testing style says "describe observable behavior" | ✅ Covered | ✅ OK |
| **Don't mock what you don't own** — use integration tests for boundaries | Not mentioned | Add to testing conventions | 🟡 MED |
| **Prefer composition over inheritance** — favor interfaces/delegation | Not mentioned | Add to java-style conventions | 🟡 MED |
| **Error handling is a feature** — explicit error paths | exception-handling skill exists | ✅ Covered | ✅ OK |
| **Log thoughtfully** — structured, actionable logs only | Observability skill exists, log sanitization required | ✅ Covered | ✅ OK |

---

## 3. Recommended Changes

### 3.1 Add "Comprehension Protocol" to all stage agents (HIGH)

Add to `agents/ai-pipeline-green-code.md`, `agents/ai-pipeline-refactor.md`, and `agents/ai-pipeline-red-test.md`:

```markdown
## Comprehension Protocol (before writing any code)
1. **Read** all files you intend to modify — never write blind.
2. **Trace** the call chain: controller → service → repository → entity for the feature area.
3. **Search** the codebase (`rg` or direct bounded repository reads) for existing patterns that solve similar problems.
4. **Match** the style and patterns of neighboring code — don't introduce new conventions.
5. **State** your understanding in the decision-log before writing code.
```

### 3.2 Add "Incremental Verification" to GREEN and REFACTOR agents (HIGH)

Add to `agents/ai-pipeline-green-code.md` and `agents/ai-pipeline-refactor.md`:

```markdown
## Incremental Verification
- After each logical unit of change (e.g., one class, one method group), compile and run affected tests.
- Do not batch all changes and test only at the end.
- If a test fails unexpectedly, stop and diagnose before continuing.
- Record each verification checkpoint in handoff evidence.
```

### 3.3 Add "Don't Guess — Search" mandate (HIGH)

Add to `CLAUDE.md` under Non-Negotiables:

```markdown
- **Search before creating**: Before writing new code, search the codebase for existing implementations, utilities, or patterns that already solve the problem. Reuse over reinvent.
```

### 3.4 Add "Self-Check" step to each stage agent (MED)

Add to each stage agent's Responsibilities (before exit):

```markdown
- **Self-check**: Before declaring stage complete, re-read your own changes and verify they meet the detailed-plan tasks, follow conventions, and introduce no unintended side effects.
```

### 3.5 Strengthen java-style and java-cleanup with Karpathy principles (MED)

Add to `backend-conventions-java-style.md`:

```markdown
## Code Simplicity Rules
- Write simple, boring code. Clever code is a liability.
- Rule of Three: don't abstract until a pattern appears 3+ times.
- Prefer composition over inheritance; use interfaces and delegation.
- Delete dead code — no commented-out blocks, no unused imports, no orphaned methods.
- Keep files focused; split when a class exceeds ~300 lines or has >2 responsibilities.
- Don't mock what you don't own — for external boundaries, use integration tests or test containers.
```

### 3.6 Add to quality-gate mandatory checklist (MED)

Add to `agents/ai-pipeline-quality-gate.md` Mandatory Test Evidence Matrix:

```markdown
## Code Quality Checks
- [ ] No dead code or commented-out blocks in changed files
- [ ] Functions do one thing (SRP at method level)
- [ ] No premature abstractions introduced
- [ ] Existing codebase patterns followed (no novel conventions without decision-log justification)
- [ ] File sizes reasonable (<300 lines per class, excluding tests)
```

### 3.7 Add uncertainty flagging to decision-log convention (MED)

Add to `backend-conventions-rgr.md`:

```markdown
## Uncertainty Protocol
- If you are unsure about a design choice, business rule, or edge case:
  1. Flag it explicitly in `decision-log.md` with `[UNCERTAIN]` tag.
  2. State what you assumed and why.
  3. Mark it for review in quality gate.
- Never silently guess — wrong assumptions compound across stages.
```

---

## 4. New Skill Recommendation

### `skill-codebase-comprehension` (NEW)

```markdown
# Skill: skill-codebase-comprehension

## Purpose
Systematically read and understand existing code before making changes.

## When invoked
- At the start of GREEN and REFACTOR stages, before any file writes.

## Steps
1. Identify all files in the change scope from detailed-plan.
2. Read each file and its direct dependencies (imports, called services).
3. Search for similar patterns in the codebase (naming, structure, error handling).
4. Document findings: existing patterns to follow, utilities to reuse, anti-patterns to avoid.
5. Output a brief "comprehension summary" to decision-log.

## Guardrails
- Do not write any production code during comprehension.
- Flag any conflicts between plan and existing code.
```

---

## 5. Summary of Changes by File

| File | Change |
|------|--------|
| `CLAUDE.md` | Add "Search before creating" non-negotiable |
| `agents/ai-pipeline-red-test.md` | Add Comprehension Protocol + Self-Check |
| `agents/ai-pipeline-green-code.md` | Add Comprehension Protocol + Incremental Verification + Self-Check |
| `agents/ai-pipeline-refactor.md` | Add Comprehension Protocol + Incremental Verification + Self-Check |
| `agents/ai-pipeline-quality-gate.md` | Add Code Quality Checks to mandatory checklist |
| `docs/conventions/backend-conventions-java-style.md` | Add Code Simplicity Rules section |
| `docs/conventions/backend-conventions-rgr.md` | Add Uncertainty Protocol section |
| `docs/conventions/backend-conventions-testing-style.md` | Add "Don't mock what you don't own" rule |
| `AGENTS.md` | Add `skill-codebase-comprehension` to skill catalog, add Design Principle #7 |
| NEW: `skills/skill-codebase-comprehension/SKILL.md` | New skill definition |

---

## 6. Decision

**Historical decision:** Adopt comprehension, explicit uncertainty and incremental verification. Use the current implementation map above for live contracts; the proposed section names and file edits in the historical tables are not current instructions.
