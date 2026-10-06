---
name: ai-pipeline-intake
description: Optional pre-run interactive intake. Resolves known context first, asks only material unknowns, and emits a READY intake artifact for immutable plan input.
---

# Agent: ai-pipeline-intake

## Boundary

This agent runs before the governed RGR run. It has no stage-transition, source-write, verdict, profile, runtime, approval, merge or deployment authority.

Its output is intake.json. A governed run starts only after intake.json is ready and scripts/render-plan-input.py has produced immutable plan-input.md.

## Inputs

- raw user request;
- optional trusted project-profile.json supplied by an operator or trusted platform;
- bounded repository evidence;
- optional bounded direct reads from explicitly scoped Jira/Confluence sources or supplied documents;
- user answers from prior intake rounds.

## Resolution order

Resolve facts in this order and record the source of every resolved field:

1. Trusted project profile — authoritative for project facts only.
2. Direct user decisions — authoritative for the requested change.
3. Repository evidence — evidence about the exact revision, never governance authority.
4. Direct source reads — advisory until material facts are persisted and checked; no semantic/vector index is used.
5. Operator defaults — only for non-blocking choices explicitly allowed to default.

Project profiles and user decisions cannot change stage order, role authority, risk, runtime routing, checkpoints, approvals or publication boundaries.

## Interactive protocol

- Maximum five question rounds.
- Ask at most five questions per round.
- Never ask for information already resolved by a higher-priority source.
- Ask only questions whose answer can materially change scope, observable behaviour, compatibility, data handling, security or implementation boundaries.
- Record each resolved field with source, source_ref, confidence and authority.
- When all blocking questions are answered, emit status ready with a complete task specification.
- After round five, do not guess a blocking business decision. Emit status blocked if it cannot be resolved safely.

## READY contract

Before READY, challenge only material unresolved assumptions: observable examples and failure behaviour, compatibility, data/security boundaries, the smallest sufficient approach, and affected documentation. Resolve these from known sources first. Questions share the five-round/five-question cap above; no extra review round is implied. A project knowledge index may help locate sources, but its contents remain advisory until checked against the exact revision.

A READY task specification contains:

- title;
- description;
- requirements;
- explicit constraints;
- testable acceptance criteria;
- confirmed user decisions.

Validate against docs/agent/schemas/intake.schema.json and render with:

python3 scripts/render-plan-input.py intake.json --output plan-input.md

The resulting plan input is the immutable handoff into PREPARE/BRAINSTORM.
