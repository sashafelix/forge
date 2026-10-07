# Contributing to Forge

Open a focused issue or pull request with the concrete behaviour being changed
and evidence for the result. Read [AGENTS.md](AGENTS.md), the
[enforcement map](docs/enforcement.md) and [SECURITY.md](SECURITY.md) before
changing delivery contracts or authority boundaries.

Edit role instructions in `agents/` and reusable skills in `skills/<name>/SKILL.md`.
`AGENTS.md` and the catalogs point to those definitions. Runtime adapters load them
at launch; do not commit runtime prompt mirrors. Preserve machine identifiers and
schema IDs unless a versioned compatibility change is intentional.

Run from the repository root:

```bash
python3 scripts/validate-agent-library.py
python3 scripts/validate-pack.py packs/rgr-software-v2/pack.json
python3 scripts/validate-governance.py
python3 scripts/evaluate-corpus.py
python3 -m unittest discover -s tests -v
python3 examples/inspect-evidence.py
python3 examples/first-change/create_demo.py
```

Also run checks specific to the affected utility or application. Explain what
was actually executed and what remains untested; synthetic fixtures are not
model-backed coding evidence. Keep documentation links and command recipes
accurate. Use fictional identifiers and reserved example domains; do not commit
credentials, private project data or generated real-run evidence.

Record current changes under `Unreleased` in [CHANGELOG.md](CHANGELOG.md).
`VERSION` is a source version marker, not proof of a tagged release. License
selection and releases are repository-owner decisions; contributors should not
invent a license or claim an unreleased revision is a published release.
