# Quickstart

Start with a model-free review, then use the [guided governed pilot](governed-pilot.md)
to generate a disposable target and the four operator files for your first HTTP-model
run. Forge Console is optional. Use the [execution-path table](../../README.md#choose-your-execution-path)
to check platform and runtime requirements before installing anything.

## Prerequisites

Contract utilities need Python 3.11+, Git 2.30+ and a terminal. They use the Python standard library; there is no pip installation, API key or model download for this path.

Commands below use Bash syntax and `python3`. On native Windows, use the installed Python 3 command (`py -3` or `python`) instead. The [evidence example](evidence-example.md) uses a portable Python script rather than shell-specific temporary-directory commands.

```bash
git clone https://github.com/sashafelix/forge.git
cd forge
git rev-parse HEAD
python3 --version
git --version
python3 scripts/validate-agent-library.py
python3 scripts/validate-pack.py packs/rgr-software-v2/pack.json
python3 scripts/validate-governance.py
python3 scripts/evaluate-corpus.py
```

Expected: four `PASS` messages after the version/revision checks. The corpus contains 12 valid fixture definitions. These checks inspect contracts and fixture structure; they do not execute a model, test a target application or authenticate a runtime.

## Inspect a complete evidence bundle

Follow the [synthetic evidence example](evidence-example.md). It generates a nine-stage fixture, validates it, exports it twice, compares the bytes, checks archive integrity and confirms that tampered evidence is rejected. All generated files go into a fresh temporary directory.

## Try a supervised coding change with Claude Code

Follow the [first change walkthrough](first-change.md). It creates a separate Git repository with a passing baseline test, operator input and risk facts. You then explicitly launch the orchestrator in a compatible execution host. The repository is disposable; it is not Forge's source checkout.

The currently documented command uses Claude Code as one adapter. Install/authenticate it through the [official setup guide](https://code.claude.com/docs/en/quickstart) or your organisation's approved distribution. Record `claude --version`. No particular model ID is prescribed.

For a different provider or host, read [model portability](../model-portability.md). Portable prompts and routing examples are available without Claude Code, but a provider API alone is not a coding runtime.

## Optional configuration companion

[Forge Console](https://github.com/sashafelix/forge-console) can prepare project facts
and provider/model profiles, create disposable pilot inputs through a registered
host, and control governed runs from its cockpit. Reviewed exports and capability
registrations are checked by Forge. See [runtime configuration](../agent/runtime-configuration.md).

If any command fails, use [operations and troubleshooting](../operations.md); do not edit evidence until a validator turns green.
