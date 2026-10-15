---
name: skill-environment-retro
description: Propose evidence-backed environment improvements after a run or a repeated agent failure.
---

# Environment retrospective

Use after a completed/interrupted run when the operator asks for improvement, or
when the assigned role permits candidate learnings. This helper proposes changes;
it does not modify policies, scripts, credentials or global model instructions.

1. Read only the selected run evidence and relevant authorised project configuration.
   Distinguish observed failure from a speculative explanation. Every candidate must
   reference a concrete event, command, file or human correction.
2. Check whether the missing protection already exists. A disabled or unwired check
   should be repaired before a second implementation is proposed.
3. Prefer executable checks for mechanical mistakes: syntax, prohibited imports,
   contract shape, stale generated files or missing CI invocation. Reserve semantic
   questions for independent review and labelled evaluation cases, not keyword bans.
4. Identify narrow navigation pointers and missing information access separately from
   quality failures. Remove duplicated advice rather than enlarging every prompt.
   Access proposals never grant permissions; the operator reviews their scope.
5. Return a short severity-ordered proposal: observation, evidence, proposed change,
   expected benefit, verification method and downside. Reuse the existing candidate
   learning lifecycle and revalidate against the exact repository revision.

Do not guess cost savings or declare that a prompt change improved model quality.
Do not promote a learning to policy or auto-commit a linter rule. Approval and a
separate reviewable implementation are required before any proposal takes effect.
