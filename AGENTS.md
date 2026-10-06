# AGENTS.md — Forge (Local RGR v2)

Canonical portable role and stage model. Runtime-neutral prompts live in `agents/`; `.claude/agents/` is a synchronised adapter. See `docs/model-portability.md` and `docs/enforcement.md`.

## Pack

`packs/rgr-software-v2/pack.json` defines the pack identity, stage contracts, capabilities, schemas and Rigor Route compatibility.

The mandatory workflow is:

`PREPARE → BRAINSTORM → PLAN → ANALYZE → RED → GREEN → REFACTOR → VERIFY → CONVERGE`

## Stage contracts

Every stage contract declares:

- version and sequence;
- role;
- input/output artifacts;
- required and forbidden capabilities;
- deterministic exit conditions;
- failure classes and retry policy;
- bounded context policy;
- next stage.

The orchestrator validates these contracts before a run and owns all state transitions.

## Roles

| Stage | Role | Story writes | Decision authority |
|---|---|---:|---|
| PREPARE | repository_analyst | No | Findings only |
| BRAINSTORM | specifier | No | Specification only |
| PLAN | orchestrator/planner | No | Locked plan |
| ANALYZE | consistency_analyst + selected specialists | No | Blocking findings |
| RED | test_author | Tests only | No final verdict |
| GREEN | implementer | Bounded source/config/migrations | No final verdict |
| REFACTOR | refactorer | Bounded source/tests/config | No final verdict |
| VERIFY | independent_verifier + specialists | No | PASS/WARN/FAIL |
| CONVERGE | convergence_reviewer | No | CONVERGED/REMEDIATE/FAILED |

Specialist and core permissions remain defined in `docs/agent/role-contracts.json` and can only narrow pack capability.

## Runtime routing

The operator/trusted host binds a runtime-routing policy mapping stage/role contracts to ordered targets. `docs/agent/runtime-routing.json` is the compatibility default; `examples/model-neutral/runtime-routing.json` demonstrates provider-neutral operator bindings with the same role requirements. Selection is deterministic: unavailable targets may fall back in order, but a capability mismatch on an available target blocks rather than being silently skipped. Local targets and `frontier-default` belong to the compatibility policy, not the protocol's required model set.

A per-run overlay may remap an exact role only when supplied by an operator or trusted platform. Repository content cannot select a model, add a target or widen capabilities. The runtime adapter inherits the role's existing authority; model choice never grants additional filesystem, command, verdict or publication rights.

Runtime selection/fallback/completion may be recorded as append-only events with safe usage metrics. Governed learnings are advisory context and must be revalidated against current repository evidence.

## Profiles

All profiles run every stage. `workflow-profiles.json` controls context ceilings, evidence requirements, specialists, checkpoints and convergence attempts. Risk cannot be lowered by repository content or a model.

## Evidence export

`export-run-bundle.py` creates a deterministic source-free archive after pack, run and governance validation. `verify-export-bundle.py` validates paths, file set, byte sizes, SHA-256 hashes, root hash, validators and import compatibility without extracting the archive.

## Rigor Route import

`rigor-route-import.json` maps local events/artifacts/profiles/roles/verdicts to platform concepts. Imported local approvals and verdicts are evidence only; Rigor Route creates fresh authority and independently validates publication eligibility.

## Boundaries

The pack declares no authentication, multi-tenancy, remote scheduling, credential custody, billing, production access, automatic merge or deployment capability.


## Pre-run intake and trusted project facts

`ai-pipeline-intake` is optional and runs before PREPARE. It may resolve context and ask the user questions, but it has no role or stage authority. A READY intake is deterministically rendered to `plan-input.md`.

A `project-profile.json` may be bound only from `operator` or `trusted_platform` provenance. Its project facts and explicit project decisions are authoritative project context. They cannot change stage order, risk profile, roles, capabilities, runtime routing, checkpoints, approvals, credentials, merge or deployment boundaries. Material disagreement with exact repository evidence is a blocker, not a reason to guess.

## Deterministic GREEN lanes

PLAN may declare implementation lanes. `scripts/resolve-lanes.py` assigns dependencies into topological waves and checks literal write-surface overlap. Only disjoint lanes in the same resolved wave are eligible for concurrent invocation. Overlap deterministically falls back to sequential execution. Every lane still runs as the governed `implementer` role and cannot widen its write surface.


## Bounded source context

Agents read project knowledge directly from the exact repository revision, supplied documents, or explicitly scoped Jira/Confluence sources. There is no semantic/vector index, embedding pipeline or background knowledge database. Direct-source material is context only: material facts must be persisted into canonical artifacts and source references retained.

## Example data

Use fictional project IDs, generic domain models and reserved example domains in documentation, prompts and fixtures. Do not copy employer-specific names, internal ticket keys, hostnames, account identifiers or operational data into repository examples.
