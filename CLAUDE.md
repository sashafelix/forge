# Forge in Claude Code

Read [AGENTS.md](AGENTS.md) first. It defines the library entry point, stage order and instruction locations. Agent definitions live only in `agents/`; reusable skills live only in `skills/`.

Launch from the Forge checkout with `python3 scripts/launch-claude.py --` followed by your Claude arguments. The launcher supplies canonical agent definitions through `--agents` and selects `ai-pipeline-rgr-orchestrator`. No `.claude/agents/` prompt copies are needed. See [the first-change walkthrough](docs/getting-started/first-change.md).

Claude Code is a prompt-based adapter; use the [governed host](docs/governed-host.md) for host-enforced Docker commands, role scopes, approvals and receipts. Model and permission choices remain operator decisions.
