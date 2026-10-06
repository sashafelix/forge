# Operator model configuration

Forge Console can edit multiple model providers and named profiles, discover model IDs, test synthetic capabilities and export a secret-free `runtime-configuration.json`. This is an optional configuration handoff. It preserves the pipeline's nine stages, role authority, risk rules, independent verification, checkpoints and publication boundaries.

## Validate an export

From this repository:

```bash
python3 scripts/validate-runtime-configuration.py /path/to/runtime-configuration.json
```

Use `--output /path/to/new-inspection.json` to create a report without overwriting an existing file. Validation is local, bounded to 2 MiB per input, and makes no network calls or credential reads.

The version `1.0` [schema](schemas/runtime-configuration.schema.json) covers four API protocols: `openai-responses`, `openai-chat`, `anthropic-messages` and `gemini`. Providers have explicit endpoints, locality, authentication modes and environment-variable credential references. Profiles contain named model bindings, optional provider-specific parameters and a primary plus ordered fallback list for every governed role. IDs may be discovered or manually entered; the contract does not hardcode model names.

Validation rejects unknown fields, raw credential values in credential-reference fields, credentials embedded in URLs, unknown references, duplicate IDs, incomplete role routing and external bindings in a local-only profile. Model and provider metadata must contain no secrets. Locality is operator-declared; the validator cannot establish whether a gateway forwards requests externally.

The shared fixture `tests/fixtures/runtime-configuration.json` is also exercised by the UI's TypeScript validator. Its example model IDs are placeholders, not recommendations or installed adapters.

## Read-only route preflight

A valid configuration does not establish that an execution adapter is installed. The inspection report supplies `binding_sha256` values and labels each binding `requires_trusted_registration`.

A trusted host may independently register adapters it actually implements and has checked. An inventory has this shape:

```json
{
  "schema_version": "1.0",
  "registrations": [
    {
      "model_id": "local-coder",
      "protocol": "openai-chat",
      "binding_sha256": "<64-character digest from the reviewed binding>",
      "ready": true,
      "capabilities": ["<capabilities independently established by the runtime host>"]
    }
  ]
}
```

The digest binds the complete provider and model objects, including endpoint, protocol, locality, credential reference and parameters. It is an integrity check, not a signature or an attestation. Editing a binding invalidates its registration until the host reviews and registers the new binding. Changing the actual credential must also trigger the host's own readiness check; actual secrets are deliberately absent from the hash.

For example, a request file containing `{"stage":"green_code","role":"implementer"}` can be checked with:

```bash
python3 scripts/validate-runtime-configuration.py /operator/runtime-configuration.json \
  --request /operator/request.json \
  --inventory /trusted-host/runtime-inventory.json \
  --configuration-source operator \
  --inventory-source trusted_platform
```

Source flags must describe provenance already established by the caller. They do not authenticate the files. Never derive these flags or the inventory from repository-controlled content or an untrusted model. The configuration cannot register itself, and UI probe results are not imported as trusted capability claims.

The preflight resolves only valid canonical stage/role pairs. It visits the configured model bindings in order, skipping absent, unready or stale registrations. A ready registration lacking a required canonical model capability blocks resolution rather than silently falling back, matching the existing routing policy. Local-only validation applies to the whole profile, including fallbacks. Resolution always reports `execution_authority: false`.

## Opt-in execution host

This helper remains read-only and does not modify `resolve-runtime.py`, canonical routing or an active run. The separate [governed host](../governed-host.md) consumes the reviewed configuration with explicit execution policy, risk facts and independently registered inventory. It implements all four HTTP tool loops, constrained Docker commands, distinct stage/verifier invocations, bound checkpoints, evidence reconciliation and explicit recovery. Console's separate cockpit can control runs registered with this host; imported evidence stays read-only. The Claude Code adapter remains available independently.

Project facts continue to use the separate `project-profile.json` contract. A project profile cannot grant runtime-routing authority. A runtime configuration likewise cannot change governance, add capabilities, execute commands, approve a run or authorize publication.
