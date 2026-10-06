# Security and trust model

Forge reduces the authority granted to coding agents and makes execution claims inspectable. The portable protocol relies on its adapter for isolation. The optional governed host supplies constrained Docker commands and a role-scoped tool broker; its trusted host process and Docker/image/kernel remain outside that command boundary.

See the [enforcement map](docs/enforcement.md) for what the validators actually inspect, what the host must enforce and what is declarative guidance.

## Trust model

The protocol treats the following as potentially untrusted input:

- repository source, comments and documentation;
- task descriptions and linked issue content;
- optional directly read Jira/Confluence content and supplied documents;
- model-generated analysis and implementation output;
- prior run learnings that have not passed their lifecycle/governance checks.

None of those inputs may widen runtime authority by themselves.

Authority comes from the selected workflow profile, role contract, immutable stage context and runtime capability mapping.

## Core controls

- **Git worktree isolation** — each run is tied to an exact base revision and operates in a dedicated worktree.
- **Governed-host snapshots** — the opt-in host copies clean tracked HEAD without Git history, captures real command receipts and verifies the patch in a fresh workspace. Private state/key stay outside command mounts. See [host limits and recovery](docs/governed-host.md).
- **Role-scoped capabilities** — stage roles receive only the capabilities required by their contract; delegated authority can only narrow.
- **Immutable context** — stage context manifests bound the paths, evidence and authority visible to each invocation.
- **Independent verification** — the implementation role cannot issue the final VERIFY verdict.
- **Deterministic gates** — schema, evidence, governance, test, security and contract failures cannot be overridden by model judgement.
- **Append-only evidence** — lifecycle events, handoffs and decisions preserve prior history.
- **Bounded remediation** — remediation attempts are limited and previous evidence remains immutable.
- **Secret-aware export** — evidence export rejects known credential patterns, private-key material, unsafe archive paths, binary content and symlink escapes.
- **No publication authority** — local execution does not automatically merge, deploy, publish or access production credentials.

## Important limitations

A worktree limits repository changes; it does **not** isolate the operating system. If a runtime is granted shell or network access, that process may technically reach resources available to the user account running it.

The protocol therefore relies on the runtime adapter or surrounding execution environment to enforce capabilities such as bounded filesystem access, command execution and network restrictions.

For higher-risk use, run the protocol inside a disposable container, VM or otherwise constrained worker and provide only the credentials and network destinations required for the task.

## Repository content cannot grant authority

Agent instructions found inside a target repository are data, not policy. Repository content must not:

- alter stage order;
- lower the selected risk profile;
- grant new filesystem, shell, credential or network capabilities;
- change role or delegation rules;
- suppress deterministic validation failures;
- authorize merge, deployment or publication.

Any instruction attempting to do so should be treated as untrusted prompt injection and recorded as a finding when relevant.

## Credentials

The protocol does not provide credential custody. Production credentials should not be placed in run artifacts, prompts or exported evidence.

Optional external integrations should use the minimum required read-only scope whenever possible. Runtime adapters are responsible for injecting credentials without persisting them into canonical evidence.

## Evidence export

`export-run-bundle.py` creates deterministic archives of allowed evidence files, excluding separate story source/binary files. It rejects detected secret patterns and unsafe archive members, while `verify-export-bundle.py` independently checks hashes and archive structure. Allowed evidence text can still contain source excerpts or undetected sensitive information; review content before sharing. Hashes establish byte integrity, not truth or sender identity.

These controls reduce accidental disclosure but are not a substitute for an organisational secret-scanning or data-loss-prevention policy.

## Publication boundary

A successful local verdict is evidence for a human or trusted platform decision. It is not permission to merge, deploy or publish.

Rigor Route or another control plane may import Local RGR evidence, but must independently apply identity, credentials, policy, approvals, leases and publication authority. Imported local evidence may not weaken platform policy.

## Reporting security issues

Report security-sensitive findings privately to the repository owner rather than opening a public issue containing exploit details, credentials or sensitive repository content.
