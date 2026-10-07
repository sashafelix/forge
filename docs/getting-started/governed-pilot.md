# Your first governed Forge run

Use a disposable greeting-function repository to learn the complete workflow:
configure → qualify → prepare → approve → advance → inspect. The helper below creates
the target, task and all four host inputs. It makes no model calls or capability grants.

Use macOS or Linux with Python 3.11+, Git and Linux Docker. On Windows, run this
recipe inside WSL; native Console can inspect the resulting evidence. Model access
must support one of the host's four HTTP protocols. Copilot and Claude Code
subscriptions are separate CLI runtimes; they do not supply governed HTTP access.

## 1. Choose a model and test image

In [Console](https://github.com/sashafelix/forge-console), open **Pipeline configuration
→ Models & providers**. Add your approved provider and model, create a profile,
assign every role, review fallback order and export `runtime-configuration.json`.
Model IDs are yours to choose. A model may serve several roles, but VERIFY always
receives a fresh, separate invocation. See [runtime configuration](../agent/runtime-configuration.md)
for the file contract and a CLI-only configuration example.

Review the endpoint, protocol, parameters and credential reference. The file contains
environment-variable names, never API keys. An external provider may receive source
context. Establish gateway locality independently. A successful connection probe
is useful diagnostics, not proof that a model can perform a role.

Provision an approved Python 3.12 Linux image using your normal process. The host
does not pull images or install dependencies. For this tiny example, a reviewed
`python:3.12-slim` image contains everything the tests need. After provisioning:

```bash
docker image inspect python:3.12-slim --format '{{.Id}}'
```

Keep the actual `sha256:…` result. A tag or all-zero example digest is not accepted
by the pilot generator. Other projects need their own reviewed image and policy.

## 2. Generate the pilot

From the Forge checkout, replace the configuration path, image ID and new destination:

```bash
python3 scripts/forge-host.py pilot \
  --configuration /absolute/path/runtime-configuration.json \
  --image sha256:YOUR_ACTUAL_64_CHARACTER_IMAGE_ID \
  --output /absolute/path/forge-pilot
```

Expected: a passing baseline test and JSON with `kind: forge-pilot`, `ready: false`.
The destination must be new and outside Forge. The generated `SETUP.md` gives the
next steps; `pilot.json` records the exact paths and source revision.

| File or directory | Purpose |
| --- | --- |
| `target/` | Separate clean Git repository; the greeting function is the change target |
| `inputs/plan-input.md` | Request and observable acceptance criteria |
| `inputs/runtime-configuration.json` | Copy of your reviewed provider/model routes |
| `inputs/execution-policy.json` | Only `greeting.py`, `test_greeting.py` and one unittest command are permitted |
| `inputs/runtime-inventory.json` | Exact binding hashes, initially `ready: false` with no capabilities |
| `inputs/facts.json` | Risk facts for this small example, not a general project profile |
| `inputs/registration-review.json` | Role requirements and a place to record qualification evidence |
| `inputs/evaluation-notes.json` | Versions, human interventions and observations for the run report |

Console offers the same helper in **Forge cockpit → New governed run → First run?
Create a disposable pilot**, after selecting Forge and Python. It asks for your
exported configuration and a new directory. Generated files are drafts and are
not automatically selected or approved.

## 3. Review and qualify the inputs

Read the task, risk facts and execution policy. Independently establish that each
binding you intend to use supports its assigned roles. Use the worksheet to record:

- The exact endpoint/protocol/model/parameters and binding hash tested.
- Observed structured output and host tool use with bounded example tasks.
- Evidence for each role capability: for example, a real regression-test task for
  `test_generation`, or an independent diff-and-test review for `verification`.
- Failures, limitations, evidence locations, reviewer and review date.

Provider listings, model self-descriptions and a single successful probe are not
sufficient. Do not copy the worksheet's required-capability lists into registrations
without evidence. Register only established capabilities in `runtime-inventory.json`
and mark those exact bindings `ready: true`. Leave unqualified fallbacks unavailable.
If you have no independently qualified runtime, stop here and conduct a supervised
runtime qualification with your platform operator.

Changing any provider or model configuration value invalidates its binding hash.
Re-inspect with `validate-runtime-configuration.py` and re-review the changed binding.
Never solve a readiness error by weakening the canonical role requirements.

## 4. Check readiness and prepare

Set `PILOT_DIR` to the generated absolute path. These commands use a POSIX shell
(macOS/Linux/WSL), from the Forge checkout:

```bash
PILOT_DIR=/absolute/path/forge-pilot
python3 scripts/forge-host.py doctor \
  --configuration "$PILOT_DIR/inputs/runtime-configuration.json" \
  --policy "$PILOT_DIR/inputs/execution-policy.json" \
  --inventory "$PILOT_DIR/inputs/runtime-inventory.json" \
  --facts "$PILOT_DIR/inputs/facts.json"
```

Continue only if JSON says `ready: true`. Doctor can exit successfully while
reporting an unavailable Docker backend; inspect `ready` and the reported reason.
Unqualified/mismatched registrations block route resolution. Readiness validates
local prerequisites and registrations; it does not make a paid model call or
verify provider credentials. Supply referenced credentials through your approved
environment or Console's matching encrypted provider binding.

```bash
python3 scripts/forge-host.py prepare \
  --repo "$PILOT_DIR/target" --run-dir "$PILOT_DIR/run" \
  --task-file "$PILOT_DIR/inputs/plan-input.md" \
  --configuration "$PILOT_DIR/inputs/runtime-configuration.json" \
  --policy "$PILOT_DIR/inputs/execution-policy.json" \
  --inventory "$PILOT_DIR/inputs/runtime-inventory.json" \
  --facts "$PILOT_DIR/inputs/facts.json"
```

Expected: `status: awaiting_approval`. Review the base revision, source/test scopes,
command, image, providers and start checkpoint. Use the exact current approval ID
and binding from `status`; do not reuse a previous run's values:

```bash
python3 scripts/forge-host.py status "$PILOT_DIR/run"
python3 scripts/forge-host.py approve "$PILOT_DIR/run" \
  --approval-id CURRENT_APPROVAL_ID --binding CURRENT_BINDING_SHA256
python3 scripts/forge-host.py advance "$PILOT_DIR/run"
```

Each `advance` executes one stage or closure. Read the result and repeat only while
the host offers `advance`. Review any new checkpoint before approving. Model calls
may consume provider allowance. On failure, inspect evidence and follow
[recovery](../operations.md); never edit receipts or failing evidence into a pass.

In Console, select the four operator files, check readiness, choose `target`, paste
`plan-input.md` and prepare. Use its checkpoint and stage controls. Console stores
the host run under its managed data directory; use the actual run path shown in
run details for the commands below, rather than `$PILOT_DIR/run`.

## 5. Inspect and record the result

A successful run should preserve `greet()` → `Hello!`, support a supplied
name with surrounding whitespace trimmed, and reject a blank name. Check the
actual task for the exact criteria. Inspect `bundle/changes.patch`, the failing RED
assertions, passing GREEN/REFACTOR tests, fresh VERIFY evidence and CONVERGE verdict.
Completion does not apply or commit the patch to your target repository.

For a completed run, verify receipts and independently regrade the patch:

```bash
python3 scripts/forge-host.py verify "$PILOT_DIR/run"
python3 scripts/forge-host.py grade "$PILOT_DIR/run"
```

Grading reruns the patched tests and checks that the frozen regression assertions
fail on the original implementation. It does not repeat model review. Record actual
Docker/runtime versions and any Console revision in `inputs/evaluation-notes.json`.
Set `execution_kind` accurately, record every human correction or retry, and retain
failed attempts. Generate a report for a completed, failed or cancelled run:

```bash
python3 scripts/forge-host.py report "$PILOT_DIR/run" \
  --notes "$PILOT_DIR/inputs/evaluation-notes.json" > "$PILOT_DIR/evaluation-record.json"
```

The report includes actual command exits/test summaries/log hashes, artifact hashes,
configured model IDs, image, timing and local receipt verification. Operator notes
are labelled as claims. Review logs, notes and diffs before sharing; do not share
`authority.key` or the private host database. See [evaluation handover](../evaluation.md)
for version pinning, evidence sharing and release status.
