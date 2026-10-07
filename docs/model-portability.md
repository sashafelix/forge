# Model and runtime portability

Forge's core is model- and provider-neutral: stage order, roles, evidence, risk and validation do not depend on a named model. The operator chooses a model through an execution host capable of the required tools and outputs. Portability does not mean every model is equally capable or that changing a provider endpoint installs a runtime.

## Separate the layers

| Layer | Source | Responsibility |
| --- | --- | --- |
| Delivery protocol | `packs/rgr-software-v2/`, `docs/agent/` | Stage/role authority, evidence and deterministic validation |
| Canonical role instructions | `agents/` | Portable Markdown prompts with name/description metadata |
| Execution adapter | Operator-reviewed coding host; `scripts/launch-claude.py` is one supplied adapter | Model calls, tool loop, permissions, actual invocation identities and outputs |
| Model/provider | Host configuration or environment references | Reasoning, code/test generation and structured outputs within the assigned role |

No model ID is embedded in the portable prompts or example routing. The existing `frontier-default` Claude Code target remains as a compatibility profile; it is not a requirement of the protocol. Current route categories are declarations, not installed SDKs. A local model server needs an execution host for filesystem tools, commands and role isolation.

## Inspect provider-neutral routing

Run from the Forge root:

```bash
python3 scripts/resolve-runtime.py examples/model-neutral/request.json \
  --routing examples/model-neutral/runtime-routing.json
```

Expected: `target_id` is `operator-primary`, `adapter` is `custom`, `model_ref` is `env:FORGE_PRIMARY_MODEL` and `fallback` is false. No model or endpoint is contacted. The example preserves the same role/capability requirements and route order while replacing provider-specific targets with operator bindings.

`FORGE_PRIMARY_MODEL`, `FORGE_PRIMARY_ENDPOINT`, `FORGE_FALLBACK_MODEL` and `FORGE_FALLBACK_ENDPOINT` are example environment references for a future/installed host. The resolver returns these references; it does not dereference them, read secrets or prove they are set. The example target capability lists are illustrative declarations. A host must independently establish them before marking a target available. The example primary is labelled local and the fallback external; review locality and policy before permitting fallback.

Only an operator/trusted platform may select the routing file and available-target list. The `--routing` command is an inspection example; target-repository content cannot supply this policy. A per-run overlay cannot manufacture a new target or widen a role. A present but incompatible target blocks rather than silently falling back.

The four provider protocols supported by Console's configuration export are described in [runtime configuration](agent/runtime-configuration.md). The optional [governed host](governed-host.md) implements their bounded tool loop, role scopes, Docker commands, exact invocation receipts and operator checkpoints. Selecting a model still requires independently reviewed registrations; a configuration export does not authorize execution by itself.

## Adapter requirements

A host integrating another model must:

1. Bind the exact portable prompt, stage/role and immutable context to each invocation.
2. Enforce filesystem, tool, command, network and credential authority outside the model prompt.
3. Establish target readiness and capabilities independently; never import a UI probe as execution authority.
4. Create a revision-pinned worktree and lock input, criteria and plan before implementation.
5. Capture real command exits/output references, append lifecycle events and validate artifacts before advancing.
6. Use a distinct VERIFY invocation and authenticate required operator checkpoints.
7. Follow resolved lane waves, or run them sequentially when safe concurrency is unavailable.
8. Stop on missing capabilities, malformed output, deterministic failure, exceeded budget or unavailable required specialists.
9. Preserve failed evidence, keep release authority external and follow the [recovery rules](operations.md).

Acceptance should demonstrate a real small-profile run plus negative tests for forbidden writes, capability mismatch, invalid JSON, missing evidence, verifier separation and interruption. High-risk support additionally needs specialist and checkpoint conformance. Provider probes and the structural tests in this repository are not that certification.

## Claude Code as one adapter

Use the native Claude executable on Windows. The launcher rejects `.cmd`/`.bat` wrappers so session JSON cannot become shell input. The governed host's Windows path remains the WSL CLI documented in its guide.

Launch from the Forge checkout using `python3 scripts/launch-claude.py --`, with explicit access to the target and operator inputs. The launcher reads `agents/`, passes small discovery entries using `--agents` that load the canonical prompt on invocation, and selects the orchestrator as the main session. Agents read applicable skills from `skills/`; no prompt copies are committed. The [first-change guide](getting-started/first-change.md) has the complete recipe. Official references: [CLI](https://code.claude.com/docs/en/cli-reference) and [subagents](https://code.claude.com/docs/en/sub-agents), checked on 2026-10-07. The CLI launch syntax was checked against those docs; no authenticated model run is bundled or claimed.
