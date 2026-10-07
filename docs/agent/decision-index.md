# Decision Index

Compact navigation index of the latest closed run for each story. Updated by the orchestrator through `skill-decision-index` after CONVERGE or explicit terminal failure. One row per story; updating this index never changes append-only run evidence.

`Story ID` is whatever identifier the input supplied (Jira key, feature slug, request slug, direct-source task id) — use exactly what was in `run-context.md > story_id`.

| Story ID | Date | Verdict | Summary | Tags | Link |
| --- | --- | --- | --- | --- | --- |

See `skills/skill-decision-index/SKILL.md` for the row contract, tag vocabulary, and idempotency rules.
