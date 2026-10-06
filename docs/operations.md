# Operations, failure handling and recovery

Run Forge utilities from the Forge checkout. Keep its root, the target
repository, isolated story worktree and evidence directory explicit. Before a
pilot, record `git rev-parse HEAD`, Python/Git versions and the execution-host
version. Preserve operator input bytes and the exact baseline revision.

## Diagnose a failure

| Symptom | Check and next action |
| --- | --- |
| Pack/governance check fails before setup | Compare the checkout, schemas, contract paths and declared versions. Fix the contract issue outside the run; rerun preflight. |
| Adapter-copy check fails | Edit canonical `agents/` prompts, run `sync-agent-adapters.py --write`, then check again. |
| No available compatible runtime | Check the operator-selected route and host-established readiness. Install/register a compatible host or stop; setting an endpoint alone does not install an adapter. |
| Available target lacks capabilities | The resolver deliberately blocks. Correct the trusted registration/routing after review; do not bypass the required capability or silently skip that target. |
| CLI missing or unauthenticated | Check the host's installation, `claude --version` and `claude auth status` for the documented adapter; use its official authentication flow. |
| Intake remains blocked | Resolve the actual question with the operator. Five question rounds are the limit; unanswered blocking questions cannot become READY. |
| Facts conflict with repository evidence | Preserve both sources and ask the operator to resolve the conflict. A model cannot lower risk or invent authoritative project decisions. |
| Stage emits malformed JSON or fails an exit condition | Preserve the output/error, record the failure and halt. Apply only the stage contract's explicit retry policy; no hidden loops. |
| Completed-run validation fails | Read each reported artifact/criterion/stage issue. Inspect original logs and source revision. Do not change historical records just to obtain PASS. |
| High-risk specialist/checkpoint is unavailable | Stop before the controlled transition. A role label or model-written approval is not an authenticated specialist or operator decision. |
| Console export validates but nothing executes | The export is configuration/test-only. The execution host still needs a governed adapter and independent registration. |
| Export rejects a path/file/secret pattern | Inspect the reported content locally. Preserve originals and create a separately reviewed sanitised sharing copy if appropriate; do not disable integrity or secret checks. |

Contracts and prompts describe failure handling. The Python helpers do not
provide a background supervisor, automatic retry runner or authenticated
approval service. The [enforcement map](enforcement.md) identifies those host
responsibilities.

## Stop and preserve evidence

On interruption or failure, stop new stage invocations and record the last
confirmed stage, real error, worktree path and durable command-output refs.
Preserve locked input, criteria, plan, artifacts and existing events. Append
failure/decision records only where their contract permits; retain raw errors
separately when they cannot be expressed by the schema. Never claim a stage
completed because it started or because the model described an intended result.

Before any continuation, establish which commands actually finished, whether
source changed outside its scope and whether operator checkpoints remain valid.
Inspect `git status --short`, the diff against the pinned baseline and referenced
logs. Keep credentials out of errors and shared evidence.

## Current recovery limit

Profile contracts allow bounded convergence attempts: one for `small`, at most
two for `standard` and `high-risk`. However, `validate-run-bundle.py` currently
requires exactly one completed sequence of the nine stages. It does not accept
a ledger with repeated completed stages as a multi-attempt run. There is no
`forge resume` command or utility that reconstructs the state and safely
re-executes the earliest invalid stage.

For a failed run, preserve its worktree/evidence and begin a separately
identified replacement run after operator review. Record the previous run ID,
failure and reviewed correction in the new operator input/decision record.
Select the new baseline explicitly; reused code must receive fresh tests and
independent verification. Do not relabel a failed run or reset an automated
retry budget by silently creating new IDs. Linked retries remain subject to
the operator's agreed attempt limit. A new run repeats all nine stages.

Claude Code's `claude --resume SESSION_ID` restores a conversation. It is not
Forge protocol recovery, permission revalidation or evidence reconstruction.
Use it only when the host can establish the exact safe state; otherwise use the
reviewed replacement-run path. See the [official CLI reference](https://code.claude.com/docs/en/cli-reference).

## Review, export and cleanup

After a completed run passes both run validators, inspect the worktree and
rerun the relevant application checks. Export/verify the evidence only when
its contents are appropriate to share. Publication remains a separate human or
trusted-platform action.

Retain evidence and any source diff you need before removing a worktree. Check
`git -C TARGET_REPO worktree list` and the selected worktree's status, including
untracked files. Remove only a reviewed, disposable worktree with
`git -C TARGET_REPO worktree remove /absolute/path/to/worktree`. Git refuses
ordinary removal of a dirty worktree; inspect and preserve its changes instead
of adding `--force`. Remove a story branch separately only after confirming its
commits are retained where needed. Cleanup is not evidence deletion.
