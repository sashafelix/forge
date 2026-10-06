# Portable Forge role prompts

These Markdown files are the canonical, model-neutral instructions for the Local RGR protocol. Their `name` and `description` frontmatter are metadata, not a model selection. The body can be supplied to any compatible coding-agent host. No model ID, provider subscription or vendor SDK is required to read the prompts or validate evidence.

| Prompt | Role / stage |
| --- | --- |
| [ai-pipeline-rgr-orchestrator.md](ai-pipeline-rgr-orchestrator.md) | Orchestrator; transitions, setup, PLAN and closure |
| [ai-pipeline-intake.md](ai-pipeline-intake.md) | Optional pre-run intake; no delivery authority |
| [ai-pipeline-prepare.md](ai-pipeline-prepare.md) | PREPARE / repository analyst |
| [ai-pipeline-brainstorm.md](ai-pipeline-brainstorm.md) | BRAINSTORM / specifier |
| [ai-pipeline-analyze.md](ai-pipeline-analyze.md) | ANALYZE / consistency analyst |
| [ai-pipeline-red-test.md](ai-pipeline-red-test.md) | RED / test author |
| [ai-pipeline-green-code.md](ai-pipeline-green-code.md) | GREEN / implementer |
| [ai-pipeline-refactor.md](ai-pipeline-refactor.md) | REFACTOR / refactorer |
| [ai-pipeline-quality-gate.md](ai-pipeline-quality-gate.md) | VERIFY / independent verifier |
| [ai-pipeline-converge.md](ai-pipeline-converge.md) | CONVERGE / convergence reviewer |

PLAN is performed by the orchestrator; there is no separate PLAN agent file. Selected specialist roles are declared in [role-contracts.json](../docs/agent/role-contracts.json), with output shapes in [specialist-review.schema.json](../docs/agent/schemas/specialist-review.schema.json). A host must implement their scoped invocations when a profile requires them; missing specialists block execution.

The [.claude/agents/](../.claude/agents/README.md) copies preserve the existing Claude Code names and installation layout. Edit the canonical files here, then refresh and check the adapter:

```bash
python3 scripts/sync-agent-adapters.py --write
python3 scripts/sync-agent-adapters.py
```

Run those commands from the Forge root. CI rejects missing or divergent adapter copies. Prompt availability does not prove a host can enforce the protocol: follow the [portability contract](../docs/model-portability.md) and [enforcement map](../docs/enforcement.md).
