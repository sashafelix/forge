# Forge Software Delivery Pack — Local RGR v2.3.0

Forge’s portable Local RGR software-delivery pack. Its model-neutral role prompts are indexed in [`agents/README.md`](../../agents/README.md); model/provider selection is an execution-host concern.

## Contents

- `pack.json` — pack identity, stage references, schemas and compatibility.
- `capabilities.json` — required/optional runtime capabilities and unsupported features.
- `evidence-import.json` — evidence import and translation contract.
- `stages/*.json` — nine ordered stage contracts.
- optional structured pre-run intake (up to five clarification rounds) and trusted project-profile schemas.
- bounded direct source reads from repository Markdown/docs, supplied files, Jira or Confluence; no vector index or embedding store.
- deterministic `lane-resolution.json` for GREEN dependency waves and concurrency safety.

## Validation

Run from the repository root. Pack validation checks contracts; it does not run a model.

```bash
python3 scripts/validate-pack.py packs/rgr-software-v2/pack.json
```

The validator checks manifest/schema validity, stage order, role and capability references, artifact paths, retry limits and evidence-import compatibility.

## Integrity

The repository pack may remain unsigned for local use. `validate-pack.py` computes deterministic SHA-256 values. Pass `--hash-report /path/to/pack-hashes.json` to write the per-stage and manifest values; default stdout reports the validation result and stage count. A receiving platform may require a signed and activated manifest before executing the pack.

## Publication

This pack has no merge, deployment or publication authority. It produces local reviewable evidence only.
