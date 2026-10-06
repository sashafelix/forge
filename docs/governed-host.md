# Governed Forge host

`scripts/forge-host.py` is an opt-in execution host for Forge's nine stages. It owns model tool calls, transitions, command receipts, checkpoints and recovery. It supports OpenAI Chat Completions, OpenAI Responses, Anthropic Messages and Gemini. Model IDs, parameters and ordered fallbacks come from the operator's configuration. No named model is required.

Use it for a bounded pilot. Claude Code remains another adapter with its own enforcement boundary. A Console probe or imported bundle never grants execution authority.

## Prerequisites and independent inputs

Install Python 3.11+, Git and a reachable Linux Docker engine. On Windows, use the CLI inside WSL; Console's native bridge currently requires a directly selectable Linux/macOS host. Preinstall an immutable container image containing the target's test dependencies. The host never pulls images, installs dependencies or falls back to a host shell.

Prepare these files outside the target repository:

| File | Purpose |
| --- | --- |
| `runtime-configuration.json` | Reviewed endpoints, credential references, models and all role routes; Console can export this. |
| `execution-policy.json` | Literal, disjoint source/test roots, fixed command IDs/argv, immutable image and limits. |
| `runtime-inventory.json` | Independently reviewed capability registrations tied to exact provider/model binding hashes. |
| `facts.json` | Explicit story ID and risk facts for the existing profile resolver. |
| `plan-input.md` | The task, observable requirements and constraints. |

The selected Forge code, Python, Docker daemon/image, operator inputs and local account form the trust boundary. Repository files cannot choose commands, endpoints, approvals or weaker risk. Project-profile exports remain separate context: validate them and incorporate reviewed facts into your operator task. Their command descriptions do not register execution commands.

The [policy example](../examples/governed-host/execution-policy.json) matches the disposable first-change repository. Its zero digest is a placeholder. Copy the file outside the target and replace it with your reviewed image's SHA-256 ID. For the fixture, explicitly provision `python:3.12-slim` and record `docker image inspect python:3.12-slim --format '{{.Id}}'`. Execution uses that immutable ID, never the tag.

`validate-runtime-configuration.py` reports binding hashes. Each [inventory registration](agent/runtime-configuration.md) supplies `model_id`, `protocol`, `binding_sha256`, `ready` and independently established `capabilities`. Diagnostics can inform this review; they cannot register themselves. An available model missing a required capability blocks. Unavailable or stale registrations may use only explicit fallbacks. Changing an endpoint/model/parameter/credential reference invalidates its registration. Live quality still needs qualification.

## Prepare and approve

Run `python3 examples/first-change/create_demo.py` for a disposable baseline. Inspect the printed task/facts paths. Replace the absolute placeholders below. The target must be a clean Git checkout, including untracked files. Preparation snapshots tracked HEAD bytes without history; symlinks/submodules are refused. The original branch stays unchanged.

```bash
python3 scripts/forge-host.py doctor \
  --configuration /operator/runtime-configuration.json \
  --policy /operator/execution-policy.json \
  --inventory /operator/runtime-inventory.json --facts /operator/facts.json

python3 scripts/forge-host.py prepare \
  --repo /pilot/target --run-dir /pilot/new-run \
  --task-file /operator/plan-input.md --facts /operator/facts.json \
  --configuration /operator/runtime-configuration.json \
  --policy /operator/execution-policy.json \
  --inventory /operator/runtime-inventory.json

python3 scripts/forge-host.py status /pilot/new-run
```

Doctor checks policy, core/specialist routes, risk and Docker readiness without contacting models. Preparation creates private state and a start checkpoint; no model runs yet. Supply keys separately through the named environment variables. Review the exact base, endpoints, scopes, command argv, image and limits. Use the status response's `approval.id` and `approval.binding_sha256`:

```bash
python3 scripts/forge-host.py approve /pilot/new-run \
  --approval-id APPROVAL_ID --binding BINDING_SHA256
python3 scripts/forge-host.py advance /pilot/new-run
```

Each `advance` executes one stage or final closure. Repeat while `ready`; required checkpoints return `awaiting_approval`. Bindings cover run/stage/attempt/base/policy/configuration and current workspace/artifacts, expire after 24 hours and reject changed bytes. Expired approvals can be cancelled and replaced by a newly prepared run; automatic renewal is not supplied. High-risk runs require specialists at ANALYZE/VERIFY and approvals before GREEN/close.

Every actor gets a fresh invocation/session. GREEN lanes execute **sequentially** in deterministic dependency waves with separate scopes/receipts. Disjoint eligibility does not currently launch concurrent workers.

## Tools, evidence and trust

Models request bounded listing, direct reads, literal searches, scoped UTF-8 writes, registered commands or one JSON submission. Writes require both an approved root and an exact locked-plan output. RED writes tests; GREEN writes source; REFACTOR preserves frozen RED tests. Reviewers cannot write source. Common credential-file reads are denied and known provider values are redacted from reads/logs. This cannot detect every secret embedded in arbitrary source.

Commands run as non-root in Docker with no network, a read-only container root, dropped capabilities, resource/time/output limits and only the disposable workspace mounted. Provider requests occur in the host and may contain source. Locality is operator-declared and cannot establish a gateway's forwarding behavior. Review registered commands and images: they execute target code. Containers do not imply immunity from kernel vulnerabilities or a workspace disk quota.

Receipts capture actual argv, exit, output hash, unique case IDs/counts and duration. Use verbose unittest/pytest or JUnit with a separate `report_path`. Empty, all-skipped, malformed or inconsistent reporting is rejected. Test commands cannot mutate story files. RED must fail mapped regression assertions without collection/runtime errors. GREEN/REFACTOR/VERIFY must pass mapped cases without skips. Test semantics and sufficiency still need independent review.

Invalid test reports retain the bounded raw command log and an error receipt; mandatory stage tests still block advancement. Stopped commands retain partial output. Executed filesystem violations retain evidence and stop the stage immediately. Cache folders may be omitted from story fingerprints, but links anywhere in the workspace are rejected before checkpoint copying.

VERIFY uses a fresh base plus only the locked patch and frozen tests. Closure reconciles the current workspace with independently executed receipts, all mandatory artifacts, scope and evidence hashes. Unvalidated proposals survive rejection separately and grant no authority.

```bash
python3 scripts/forge-host.py events /pilot/new-run --after 0 --limit 200
python3 scripts/forge-host.py verify /pilot/new-run
python3 scripts/forge-host.py inspect /pilot/new-run/bundle
python3 scripts/close-run.py /pilot/new-run/bundle
```

`verify` checks receipts against the separately selected private SQLite ledger/HMAC key. `inspect`, `close-run` and existing validators perform advisory file/schema/history checks. Exported signatures and actor labels never authenticate a host. Protect the local account and state directory: someone owning both key and ledger is inside this trust boundary. This is not remote attestation.

## Recovery

SQLite transactions and a single-worker lease own state/events; private snapshots provide stage checkpoints. There is no automatic retry or process resurrection.

```bash
python3 scripts/forge-host.py resume /pilot/new-run
python3 scripts/forge-host.py retry /pilot/new-run --stage quality_gate
python3 scripts/forge-host.py cancel /pilot/new-run
```

Resume accepts interrupted work or an abandoned worker, restores its checkpoint and requests fresh approval/invocations. Deterministic rejection requires retry at the failed stage or an earlier invalid stage. Retry preserves receipts and archives the invalidated suffix; it consumes a convergence attempt. Small allows one total attempt; standard/high-risk allow two. The preserved prefix remains bound to its original invocations. Cancellation is terminal and retains evidence/partial source. SIGINT/SIGTERM cancel CLI execution and stop labelled containers.

Failed preparation or missing checkpoints need a new reviewed run. Never edit the ledger to relabel failure. Event reads remain available while a worker runs; this is a single-machine lease, not a distributed scheduler.

## Handoff, export and evaluation

Completed runs include `changes.patch` and `handoff.md`. Patches support bounded UTF-8 content; binary, rename identity and file-mode patches are not supported. Review/apply manually at the recorded base, then rerun application checks. The host does not commit, push, merge or deploy.

```bash
git -C /pilot/target apply --check /pilot/new-run/bundle/changes.patch
python3 scripts/export-run-bundle.py /pilot/new-run/bundle /pilot/evidence.tar.gz
python3 scripts/verify-export-bundle.py /pilot/evidence.tar.gz
python3 scripts/forge-host.py grade /pilot/new-run
```

Portable export omits `changes.patch`, workspace, ledger and key. Review embedded excerpts before sharing. Grade reruns the patched result and an unpatched-base negative control with frozen RED tests, appending fresh receipts without repeating model review.

Use `forge-host.py evaluate /operator/evaluation.json` with this shape:

```json
{"schema_version":"1.0","runs":[
  {"label":"baseline","run_dir":"/runs/base-1","repeat":1},
  {"label":"candidate","run_dir":"/runs/candidate-1","repeat":1}
]}
```

Each row must name a distinct run. Labels must cover identical tasks/baselines/policies/repeats with one immutable configuration per label. Use multiple pinned tasks and at least three independent repeats. Failures remain in the denominator; output includes Wilson 95% intervals and estimated tokens. Billing cost and a model-quality winner are not inferred.

## Qualification

Python tests exercise real test commands in a controlled local fixture adapter, all stages, specialists/checkpoints, recovery, tampering and four protocol fixtures. CI additionally executes the complete fixture through real Docker and checks container boundaries. The controlled model does not establish live provider quality. Qualify your endpoints, parameters, tools, key environment and tests on the intended host. External tracing/workflow frameworks and concurrent lane workers remain future integrations.
