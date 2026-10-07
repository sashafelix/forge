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

PLAN is performed by the orchestrator. Each governed agent declares its `role` in frontmatter; the host resolves that binding against `docs/agent/role-contracts.json`.

| Specialist | Definition |
| --- | --- |
| risk_reviewer | [agent](ai-pipeline-risk-reviewer.md) |
| threat_modeler | [agent](ai-pipeline-threat-modeler.md) |
| migration_reviewer | [agent](ai-pipeline-migration-reviewer.md) |
| infrastructure_reviewer | [agent](ai-pipeline-infrastructure-reviewer.md) |
| contract_reviewer | [agent](ai-pipeline-contract-reviewer.md) |
| accessibility_reviewer | [agent](ai-pipeline-accessibility-reviewer.md) |

Profiles choose the required specialists. Their scoped invocations and typed reviews remain mandatory when selected. Missing roles block execution.

Read [AGENTS.md](../AGENTS.md), then the assigned definition and only applicable [skills](../skills/README.md). The governed host loads these files directly. Claude Code receives definitions at launch:

```bash
python3 scripts/validate-agent-library.py
python3 scripts/launch-claude.py -- --add-dir /path/to/target /path/to/operator-inputs
```

`--print-agents` prints generated Claude discovery JSON without contacting a model. Each session entry points to its canonical prompt, which is read when the agent starts; no committed copies or symlinks are required. Console supports the same canonical layout for ordinary standalone libraries, including temporary Copilot discovery files restored after each run. Forge's governed stage agents use Console's separate host bridge, not its standalone CLI controllers. See [model portability](../docs/model-portability.md).
