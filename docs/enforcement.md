# What Forge enforces, and what the host must enforce

Forge publishes a delivery protocol, portable instructions, file validators and an opt-in [governed execution host](governed-host.md). A valid document is not proof that a process obeyed it. The first table describes portable file checks and obligations for other adapters; the second describes the governed host.

| Concern | Current repository checks | Execution-host / reviewer obligation |
| --- | --- | --- |
| Pack and stage contracts | `validate-pack.py` checks schema shapes, ordered contracts, role/capability references, declared hashes and routing compatibility | Invoke only the authorised next stage; prevent model-authored policy changes |
| Risk profile | `resolve-profile.py` deterministically classifies supplied facts and can raise the operator minimum; run-governance checks profile requirements | Establish accurate facts from trusted operator context; prevent a runtime from choosing weaker facts |
| Runtime routing | `resolve-runtime.py` selects declared available targets and rejects an available target's capability mismatch | Establish availability, authenticate the provider and register real capabilities; declarations are not readiness probes |
| Intake | Schema caps rounds at five; rendering and completed-bundle checks reject unresolved blocking intake | Ask only material questions and obtain real user answers |
| Lane safety | `resolve-lanes.py` detects dependency cycles and literal prefix overlap; run-bundle checks plan/lane correspondence | Enforce each lane's actual write scope, join results and run combined checks; literal path checks are not an OS sandbox |
| Run evidence | `validate-run-bundle.py` checks files/schemas, actual referenced logs, exits, empty-suite markers, criterion sets and bounded suffix-remediation history | Capture real commands and preserve prior bytes; file checks do not replay commands or authenticate a log's origin |
| Independent verification | Role/status fields and the reserved implementer identity are checked | Establish a distinct invocation/identity and independent checks; no identity authentication or full actor provenance service is shipped |
| Context and permissions | Run-governance checks declared context budgets and required context manifests | Limit actual filesystem reads/writes, commands, network and credentials; prompts alone cannot enforce those permissions |
| Operator checkpoints | Run-governance requires matching `checkpoint.accepted` events attributed to `operator` | Authenticate and bind the real approval to the exact request; writing an actor label is not authentication |
| Event history | Event schema and contiguous sequence are checked | Enforce append-only storage. Rewriting a complete ledger can still produce structurally valid JSON; no signed immutable ledger is provided |
| Evidence export | Export scans allowed file types/secret patterns and rejects symlinks/unsafe paths; archive verification checks bytes/hashes/file set | Review embedded excerpts and sensitive text; hashes establish byte consistency, not authorship or factual correctness |
| Publication | Contracts declare no automatic merge, deployment or production access | Keep release credentials and publication authority outside the agent runtime |

The schema utility implements the repository's documented JSON Schema subset; it is not a general-purpose implementation of every draft keyword. See [`schema_validation.py`](../scripts/schema_validation.py).

## Current execution maturity

The [portable prompts](../agents/README.md) are usable by compatible hosts, and the Claude Code layout is one supplied adapter. The files currently carry no role-specific `tools` or `permissionMode` frontmatter. Permissions are inherited from the configured host; the role descriptions are instructions. For stronger guarantees, install reviewed host policy, permission hooks or isolation that maps each role to the allowed tools and paths.

The opt-in host supplies the following enforcement. It requires independently selected operator files and a reviewed Docker image/daemon. It does not turn an imported file or UI probe into authority.

| Boundary | Governed host behavior | Practical limit |
| --- | --- | --- |
| Model tools | Broker enforces role, fixed command IDs, exact planned outputs and frozen tests | Registered commands execute target code; semantic sufficiency needs review |
| Commands | Non-root Docker, no network/history/credentials, read-only root, dropped capabilities, bounded resources/time/output | Local Docker/image/kernel are trusted; workspace disk quota is not supplied |
| Stage truth | Distinct invocations, captured outputs/case IDs, mandatory real RED/GREEN/REFACTOR/VERIFY commands, fresh verification workspace | Protocol fixtures do not establish live model quality or complete test coverage |
| Input and approval | Pinned initial artifacts; checkpoint binds run/stage/attempt/base/policy/configuration/workspace/artifacts and expires | Approval is a local operator action, not an authenticated hosted identity service |
| Evidence | Immutable invocation snapshots, private SQLite receipts and HMAC verification against the separately selected host | Key and ledger must stay private; an exported signature cannot authenticate itself |
| Recovery | Single-worker lease, restored stage snapshots, fresh approvals/invocations, explicit bounded suffix retry | No background supervisor, remote scheduler or automatic process resurrection |
| Lanes | Separate scopes and receipts in deterministic waves | Actual execution is sequential |
| Publication | Text patch and handoff for manual review | No commit/push/merge/deployment authority |

## What a successful check means

A `PASS` reports the checks that tool performed. It does not certify the model, establish that all claimed tests ran, prove source safety or approve release. The [synthetic fixture](getting-started/evidence-example.md) intentionally contains generated claims that pass structural validation; it is an example of the artifact format, not proof of executed development.

A Git worktree separates ordinary branch changes. Processes still have the operating-system authority granted to their user account. Read [SECURITY.md](../SECURITY.md) before using real repositories, credentials or integrations.
