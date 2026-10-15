# Focused engineering practices

These optional helpers strengthen existing Forge roles. They do not add stages,
new agent authority, automatic publication, a new memory service or a second
orchestration framework. Load a helper only when its trigger is relevant.

| Need | Helper | Concrete result |
| --- | --- | --- |
| Decompose an approved requirement | `skill-delivery-planning` | Observable slices, stable scenario mapping and explicit test boundaries |
| Diagnose a hard bug | `skill-diagnosing-bugs` | Reproduction/evidence status, falsifiable hypotheses and regression evidence |
| Improve the working environment after a run | `skill-environment-retro` | Evidence-backed proposals, prioritising executable checks for mechanical errors |
| Investigate costly architectural complexity | `skill-architecture-survey` | Scoped before/after candidates for human selection, never automatic refactoring |

PLAN/ANALYZE still decide whether a proposed design preserves intent. RED still
owns failing acceptance evidence; GREEN cannot redefine it. VERIFY remains an
independent, read-only role. Regression tests that already pass remain regressions,
not invented failing success criteria. Architecture findings are advisory unless a
real contract, requirement or existing standard is violated.

Retrospectives propose changes to the existing learning/check infrastructure. They
do not silently rewrite policy, add broad instructions to every model call or make
an AI's own past conclusion authoritative. Revalidate candidate learnings at the
actual target revision. Keep mechanical checks in executable tooling and reserve
human/model judgment for genuinely semantic questions.

The practices were inspired by Matt Pocock's composable engineering skills:
https://github.com/mattpocock/skills. These are independently written adaptations
for Forge's role boundaries; no upstream skill text or auto-updating plugin is
vendored. Review any future upstream-derived changes as normal source changes.

## Evaluate changes rather than assuming improvement

Compare representative tasks against the previous workflow using repeated trials.
Record requirement changes/lost decisions, human correction effort, duplicate
questions, unsupported additions and total calls/tokens per completed change.
Include failures and unknown usage. Unit/contract tests establish mechanical
behaviour, not reduced token costs, model quality or equal outcomes across users.
