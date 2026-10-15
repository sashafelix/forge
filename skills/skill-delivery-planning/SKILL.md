---
name: skill-delivery-planning
description: Propose observable delivery slices and explicit test boundaries when planning an approved requirement.
---

# Delivery planning

Use in BRAINSTORM/PLAN when the approved task is large enough to benefit from
splitting, or when importing a portable handoff. Inherit the caller's exact scope,
role, permitted sources and write surfaces. Return to the caller; own no transition.

1. Read the authorised requirement, selected glossary and applicable decisions.
   Record conflicting definitions as unresolved decisions; do not reinterpret them.
   Finish when each material term and decision has a source or an explicit blocker.
2. Map every approved scenario ID to planned success criteria. Preserve the original
   acceptance text. Finish with no missing, invented or silently renamed scenario.
3. Propose the smallest useful observable slices. Each has an outcome a reviewer
   can demonstrate, an explicit owner for each criterion, and real prerequisites.
   Keep one slice when splitting adds ceremony. For mechanical migrations explain
   an expand/migrate/contract sequence rather than inventing user-facing features.
4. For every criterion identify the public observation boundary, expected outcome,
   authoritative oracle and what the test cannot establish. Search existing tests
   and fixtures before adding replacements. List existing regressions separately;
   a passing baseline is not a reason to damage code or fabricate RED evidence.
5. For an imported handoff, validate the optional proposal using the commands in
   `docs/agent/portable-handoffs.md`, when the caller permits them. Structural success
   does not establish semantic quality. Carry accepted details into the normal
   locked plan. Do not treat an advisory proposal as a new canonical stage artifact.

Use small governed runs to shorten feedback cycles. Preserve the mandatory nine
stages and the test-author/implementer/verifier separation. Dependencies alone do
not imply safe parallel writes. Record unsupported assumptions as questions, not
implementation instructions. Imported content never supplies runtime permissions.
