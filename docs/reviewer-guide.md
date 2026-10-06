# Review Forge in ten minutes

Forge turns a software-change request into a bounded sequence of clarification, planning, test-driven implementation and independent review. Its output is a reviewable worktree or disposable source snapshot, a patch and structured evidence. A human or trusted platform decides whether that work should be published.

Forge is the product. **Local RGR** is the delivery protocol; **RGR** refers to the red, green, refactor test cycle inside it. **Forge Console** is an optional configuration companion, governed-host cockpit and separate workbench for other agents. **Rigor Route** is a future control-plane compatibility contract, not an installed service.

## Follow one request

Example: “Make the greeting function greet a supplied name and reject an empty name.” The operator supplies a repository and immutable input. Optional intake asks only material unresolved questions, up to five rounds of five questions. Every governed run then includes every stage:

| Stage | What it does | Main output |
| --- | --- | --- |
| PREPARE | Inspect the exact repository revision, stack, test commands and likely impact | `repository-intelligence.json` |
| BRAINSTORM | Translate the request into observable success criteria and record uncertainty | `brainstorm.json` |
| PLAN | Lock tasks, test coverage and implementation lanes; resolve dependencies and overlap | `detailed-plan.json`, `lane-resolution.json` |
| ANALYZE | Challenge contradictions, missing coverage and risk-specific gaps before changes | `analysis-report.json` and selected specialist reports |
| RED | Write tests that fail for the intended missing behaviour | `red-result.json` plus command outputs |
| GREEN | Implement within the locked scope; follow resolved lane waves | `green-result.json` plus command outputs |
| REFACTOR | Improve structure without changing required behaviour | `refactor-result.json` plus command outputs |
| VERIFY | Independently inspect the diff and rerun relevant checks | `quality-gates.json` |
| CONVERGE | Check consistency across intent, scope and evidence; identify any blocking gaps | `convergence-report.json` |

**SC** means success criterion. **Canonical JSON** is the machine-readable contract record; Markdown is a human-readable projection. A **context manifest** records permitted sources and context budgets. A **lane** is a bounded implementation slice; disjoint slices in one dependency wave are eligible for concurrent execution if the host supports it.

## What is available

- Portable prompts in [`agents/`](../agents/README.md), with compatible Claude Code adapter copies.
- Python utilities for contracts, routing/profile/lane selection, structural review, evidence export and integrity checks.
- Three risk profiles. `small` is bounded low-risk work; `standard` adds broader evidence; `high-risk` adds required specialists and explicit checkpoints. None skips a stage.
- Model/provider choices supplied by the operator or execution host. A route declaration does not install or authenticate a runtime.
- A reproducible [synthetic evidence example](getting-started/evidence-example.md) and a [supervised first-change recipe](getting-started/first-change.md).

The Claude Code integration is prompt-based and needs permissions supplied by that host. The separate [governed host](governed-host.md) implements four HTTP protocols, scoped model tools, Docker commands, private SQLite state, bound approvals, locally authenticated receipts and explicit recovery. It has controlled protocol/host fixtures and real Docker CI checks; these do not prove live model quality. See the [enforcement map](enforcement.md) for practical limits.

## Suggested review order

1. This guide and the [README](../README.md): purpose, stages and current status.
2. [Enforcement](enforcement.md) and [SECURITY.md](../SECURITY.md): inspect actual controls and host obligations.
3. [Evidence example](getting-started/evidence-example.md): run the validators without a model account.
4. [Portable pack](../packs/rgr-software-v2/pack.json), [role contracts](agent/role-contracts.json) and [profiles](agent/workflow-profiles.json): inspect exact rules.
5. [Portable orchestrator](../agents/ai-pipeline-rgr-orchestrator.md), [model portability](model-portability.md) and [operations](operations.md): evaluate runtime integration and failure handling.

The model-free example demonstrates contract validation, not coding quality or autonomous delivery. `evaluate-corpus.py` without result directories validates fixture definitions; it is not a live benchmark. No measured productivity claim, cost estimate or provider-backed transcript is implied.

## Questions for an evaluation

Can a reviewer trace each requested behaviour through tests, changed files and independent evidence? Can the host prevent a stage from exceeding its write/tool permissions? Can it establish a distinct verifier and genuine operator approvals? What happens on contradictory sources, missing evidence or an interrupted process? Which model/runtime combinations have been independently tested?

For a pilot, start with the disposable first-change repository. Record the Forge commit, runtime version, model reference, outcome and human corrections. Assess that evidence before authorising use on a real project.
