# Reproducible evaluation and handover

Start with the [reviewer guide](reviewer-guide.md), run the [offline checks](getting-started/quickstart.md),
then complete the [governed pilot](getting-started/governed-pilot.md). Keep the scope
small enough that a reviewer can inspect the entire patch and all tests.

## Pin the source pair

Version markers alone do not identify a tested build. From a clean Forge checkout,
record both clean source revisions before running an evaluation:

```bash
python3 scripts/forge-host.py snapshot --console /absolute/path/forge-console \
  > /absolute/path/evaluation-pair.json
```

The result contains repository URLs, exact commits, source version markers and the
shared host/configuration interface versions. Dirty checkouts are rejected. This
file pins an evaluation pair; it does not certify interoperability or publish a release.
Run each repository's documented checks and one complete pilot on this exact pair.
To reproduce it, clone the two repositories and check out the recorded commits
with `git checkout --detach COMMIT` before installation.

Forge needs Python 3.11+ and Git; governed commands additionally need Linux Docker
and a reviewed preinstalled image. For Console source installation, use Node 22.12+
and run `npm ci`, `npm run build`, then `npm run dev`. Stop an older development
process before restarting. Packaged Console users need the package built from the
recorded Console commit; pulling source does not update an installed application.

## What to hand to a reviewer

| Item | What it establishes |
| --- | --- |
| `evaluation-pair.json` | Exact source pair and declared interfaces |
| Reviewed four input files and qualification worksheet | Routes, command/write limits, story facts and independently recorded capability evidence |
| `evaluation-record.json` | Observed run status, timings, command/test summaries and evidence hashes; operator notes remain labelled |
| Reviewed patch and command logs | What changed and which assertions actually failed/passed |
| Verified portable evidence archive | Consistent canonical records and integrity hashes; no transferred approval authority |
| Known limitations and failed attempts | Where the trial did not work or needed human help |

Use `export-run-bundle.py RUN/bundle evidence.tar.gz` for a successfully closed run
and `verify-export-bundle.py evidence.tar.gz` to check it. Portable exports omit
source patches; share a reviewed patch separately when permitted. Never share the
host's private authority key or database. Source context, credentials or private
details may appear in user-supplied notes or logs; review the actual files.

## Current qualification and release status

The repository contains offline contract examples, controlled provider tests and
real Docker CI checks. These test host behaviour. A public, independently reviewed
live-model reference run is still required before claiming model-backed onboarding
has been qualified. The pilot and report commands make that evidence reproducible;
their existence is not a substitute for executing the trial.

Source markers remain Forge `2.3.0` and Console `0.9.0`; the current work is unreleased.
No licence is selected in either repository. The repository owner must choose the
licence before reuse/distribution terms can be stated. Do not add an assumed licence
or describe a source snapshot as a stable release.

For an evaluation release, record the exact source pair, passing CI links, platform
tested, live pilot record, known limitations and licence decision in release notes.
Console packaging already produces `SOURCE_REVISION` and `SHA256SUMS`. Verify those
against the pinned pair; record whether each package is signed. Unsigned development
packages and signed distribution builds must be described accurately. The owner
can then approve tags and publication. See Console's
[distribution guide](https://github.com/sashafelix/forge-console/blob/main/docs/distribution.md).
