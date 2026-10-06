# Inspect synthetic evidence without a model

From the Forge root, run:

```bash
python3 examples/inspect-evidence.py
```

This standard-library script creates a fresh temporary directory and leaves it
available for inspection. It generates a complete small-profile fixture,
validates its evidence and governance, exports it twice, compares the bytes and
verifies the archive. It then changes `quality-gates.json` inside a copied
archive without updating the manifest. The verifier must reject that archive;
the example treats that rejection as the expected successful check.

Expected output includes `PASS: both exports are byte-identical`,
`PASS: archive verifier rejected modified evidence` and the artifact directory.
The unmodified archive remains available as `evidence-a.tar.gz`.

## Read the generated run

Within the printed directory, inspect `synthetic-run/`:

| File | What to look for |
| --- | --- |
| `plan-input.md`, `brainstorm.json` | Requested behaviour and the `SC-1` success criterion |
| `detailed-plan.json`, `lane-resolution.json` | Test mapping, locked tasks, resolved implementation waves |
| `red-result.json`, `green-result.json`, `refactor-result.json` | Declared stage outcomes and criterion evidence references |
| `quality-gates.json`, `convergence-report.json` | Independent-review fields and final consistency result |
| `context-*.json`, `profile-resolution.json` | Bounded source context and small-profile requirements |
| `events.jsonl` | One completed nine-stage sequence, with contiguous event numbers |
| `evidence/` | Synthetic log text referenced by the fixture |

The generator uses a fixed fictional revision, timestamps and test claims.
`fixture-check` is a fabricated command label, not an executable you need to
install. The fixture has no application checkout and does not execute its
claimed red/green tests. Its backend/frontend lanes demonstrate the schema;
they are unrelated to the greeting application in the first-change recipe.

## Interpret the result

These checks demonstrate structural consistency, deterministic export and
byte-integrity verification. They do not prove that an agent wrote working
code, obeyed permissions or ran the logged tests. For real evidence, inspect
the exact application worktree, command outputs and authenticated runtime
records, and independently rerun the relevant checks. See the
[enforcement map](../enforcement.md) and [supervised coding recipe](first-change.md).

To inspect an existing completed run instead, replace the paths below:

```bash
python3 scripts/validate-run-bundle.py /absolute/path/to/run
python3 scripts/validate-run-governance.py /absolute/path/to/run
python3 scripts/export-run-bundle.py /absolute/path/to/run /absolute/path/to/evidence.tar.gz
python3 scripts/verify-export-bundle.py /absolute/path/to/evidence.tar.gz
```

Export does not overwrite the source evidence. Review its contents before
sharing: allowed text can contain excerpts or sensitive information not caught
by pattern-based secret scanning. An export grants no publication authority.
