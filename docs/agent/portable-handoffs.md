# Optional portable requirement handoffs

Forge can inspect a **manually supplied** Clarity portable handoff and create a
local plan-input snapshot after explicit operator acceptance. Clarity remains a
standalone product. Neither product calls, configures or dispatches the other.
These are operator CLI tools, not new Console screens or automatic host hooks.

## Inspect, accept, verify, then use the normal host

Export a portable view of an already sealed handoff in Clarity. Copy only that
portable ZIP to the chosen private local directory. Do not provide the full audit
ZIP; it may contain private supporting evidence and is deliberately rejected.

```sh
python scripts/pipeline.py import-handoff /private/REQ1-portable.zip --show-content

# Substitute the exact package SHA-256 printed by inspection after reviewing it.
python scripts/pipeline.py import-handoff /private/REQ1-portable.zip \
  --accept-sha256 REVIEWED_PACKAGE_SHA256 --output /private/REQ1-input

python scripts/pipeline.py verify-handoff-input /private/REQ1-input
```

Inspection is read-only. Acceptance creates a new private directory and refuses
existing paths. It retains the original ZIP, byte-identical delivery files,
metadata, `plan-input.md` and `handoff-binding.json`. No shell, model, credentials,
tracker or publication operation is invoked. Paths through symlinks, unsafe ZIP
members, duplicate metadata keys, extra files and excessive expanded sizes block.

Use `plan-input.md` as the selected immutable input in the existing governed-host
workflow. The host still owns permissions, classification, approvals and execution.
Keep the accepted directory outside the target repository and model write scope.
Reverify it before use. A later requirement revision needs a new acceptance and
new governed input, not an edit to a running plan.

The acceptance receipt is a local record of explicit CLI selection, **not** an
authenticated enterprise approval. A hash proves consistent bytes, not sender
identity, business correctness, successful tests or transferable permission.
An OS owner who can replace all local records is outside this integrity boundary.
Import validation compares scenario tag identities; it does not replace the
Gherkin parser, coverage review or independent Forge verification.

## Portable contract v1

Exactly three flat UTF-8 files are accepted:

| File | Meaning |
| --- | --- |
| `requirement.md` | Exact reviewed developer narrative |
| `acceptance.feature` | Exact approved Gherkin, including line endings |
| `handoff.json` | Version, requirement/revision, export profile, upstream digests, payload hashes and scenario IDs |

The metadata kind is `clarity-portable-handoff`, with integer `schema_version: 1`.
No source bodies, reviewer/operator identities, permissions or provider configuration
are transferred. The default Clarity two-file handoff and full audit view remain
unchanged. No model rewrites approved acceptance criteria during export/import.

## Optional delivery proposal

During planning, use `skill-delivery-planning` to propose small observable slices.
A one-slice change is valid; splitting is not a quota. For each criterion retain
the imported scenario IDs, supported observation boundary, expected behaviour,
test oracle and limitations. Keep already-passing regression checks separate from
new failing evidence. Do not break existing behaviour simply to manufacture RED.

```json
{
  "schema_version": 1,
  "handoff_sha256": "REVIEWED_PACKAGE_SHA256",
  "story_id": "STORY1",
  "criteria": [{
    "sc_id": "SC-1",
    "scenario_ids": ["C1"],
    "test_boundary": {
      "interface": "Public cancellation command",
      "expected_behavior": "Queued operation becomes cancelled",
      "oracle": "Approved scenario C1 and a controlled queued fixture",
      "limitations": "Does not establish production availability"
    }
  }],
  "slices": [{
    "id": "SLICE1",
    "outcome": "A user can cancel a queued operation",
    "criterion_ids": ["SC-1"],
    "depends_on": []
  }],
  "regressions": []
}
```

This example must be adapted to the exact imported scenario set; placeholders are
not valid approvals or hashes. The checker rejects stale handoffs, missing/unknown
scenario or criterion references, duplicate delivery owners, empty test boundaries
and cyclic dependencies.

```sh
python scripts/pipeline.py check-delivery-plan \
  --handoff /private/REQ1-portable.zip --plan /private/delivery-plan.json
```

The result is **structurally valid**, not semantically approved. Carry the reviewed
mapping and test design into the normal locked detailed plan. This optional sidecar
is not a replacement for canonical stage artifacts, nor automatically enforced by
the host. Dependency waves do not grant concurrency: write-overlap checks and host
capabilities still control that. Large work can use separate small governed runs;
this change does not introduce a nested RED/GREEN protocol.

## Two-axis review projection

```sh
python scripts/pipeline.py review-axes \
  --handoff /private/REQ1-portable.zip --plan /private/delivery-plan.json \
  --run-dir /private/run-evidence --output /private/review-axes.json
```

This displays the existing independent verifier's **reported requirement coverage**
by imported scenario, separately from its engineering findings. It validates the
canonical quality artifact and requires exact story/criterion correspondence.
Unclassified hard failures apply to both axes; keyword guessing never downgrades
findings. The original canonical verdict remains authoritative.

This read-only projection does not rerun tests, authenticate the reviewer or verify
code-revision binding. Use the normal run/governance validators and inspect the
host's revision-bound execution receipts before human handover. A projection cannot
approve a PR or make an invalid run valid.
