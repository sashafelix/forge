"""Create a disposable pilot and record observed runs without granting authority."""
from __future__ import annotations

from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from pipeline_support.common import ROOT, contained, read_bytes
from runtime_configuration import inspect_configuration, load
from .policy import validate as validate_policy


def revision(root: Path | None = None) -> dict:
    root = root or ROOT
    def git(*args):
        try:
            return subprocess.check_output(['git', '-C', str(root), *args], text=True, stderr=subprocess.PIPE).strip()
        except subprocess.SubprocessError as exc:
            raise ValueError(f'Cannot read the Git source revision in {root}') from exc
    return {'commit': git('rev-parse', 'HEAD'),
            'dirty': bool(git('status', '--porcelain', '--untracked-files=normal'))}


def evaluation_snapshot(console: Path) -> dict:
    console = console.expanduser().resolve()
    package = json.loads(read_bytes(console, 'package.json'))
    if package.get('name') != 'agent-pipeline-ui':
        raise ValueError('Select the Forge Console source checkout')
    pair = {'forge': {'repository': 'https://github.com/sashafelix/forge',
                      'version_marker': (ROOT / 'VERSION').read_text().strip(), **revision()},
            'console': {'repository': 'https://github.com/sashafelix/forge-console',
                        'version_marker': package['version'], **revision(console)}}
    if any(item['dirty'] for item in pair.values()):
        raise ValueError('Both source checkouts must be clean before pinning an evaluation pair')
    return {'schema_version': '1.0', 'kind': 'forge-evaluation-snapshot', 'sources': pair,
            'host_interface': '1.0', 'runtime_configuration_schema': '1.0',
            'release_status': 'source_snapshot', 'qualification': 'not_established_by_snapshot',
            'requirements': {'python': '3.11+', 'console_node': '22.12+', 'sandbox': 'Linux Docker'},
            'limits': ['Version markers do not establish a tagged release.',
                       'Run both repositories\' checks and a live pilot on these exact revisions.']}


def create_pilot(output: Path, configuration_path: Path, image: str) -> dict:
    """Create-only, offline scaffolding. Every registration starts unavailable."""
    configuration = load(configuration_path)
    inspection = inspect_configuration(configuration)
    policy = load(ROOT / 'examples/governed-host/execution-policy.json')
    policy['image'] = image
    validate_policy(policy)
    if image.endswith('sha256:' + '0' * 64):
        raise ValueError('Supply the actual immutable image ID; the example placeholder cannot run')
    output = output.expanduser().absolute()
    if any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError('Pilot destination cannot contain symlinks')
    if output.resolve().is_relative_to(ROOT):
        raise ValueError('Create the pilot outside the Forge checkout')
    source = revision()
    spec = importlib.util.spec_from_file_location('first_change', ROOT / 'examples/first-change/create_demo.py')
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    try:
        descriptor = demo.create_demo(output)
    except subprocess.SubprocessError as exc:
        raise ValueError('Pilot baseline creation failed; inspect the new directory before retrying with a new path') from exc
    output.chmod(0o700)
    inputs = output / 'inputs'
    inputs.chmod(0o700)

    def write(name, value):
        with (inputs / name).open('x', encoding='utf-8') as stream:
            (inputs / name).chmod(0o600)
            json.dump(value, stream, indent=2)
            stream.write('\n')

    write('runtime-configuration.json', configuration)
    write('execution-policy.json', policy)
    write('runtime-inventory.json', {'schema_version': '1.0', 'registrations': [
        {key: binding[key] for key in ('model_id', 'protocol', 'binding_sha256')} |
        {'ready': False, 'capabilities': []} for binding in inspection['bindings']]})
    routes = load(ROOT / 'docs/agent/runtime-routing.json')['routes']
    requirements = {route['role']: route['required_model_capabilities'] for route in routes}
    write('registration-review.json', {'schema_version': '1.0', 'purpose': 'Review worksheet; not host authority',
        'models': [{key: binding[key] for key in ('model_id', 'protocol', 'binding_sha256')} | {
            'requirements_by_role': {r['role']: requirements[r['role']] for r in configuration['profile']['routes']
                                     if binding['model_id'] in r['models']},
            'evidence': [], 'reviewed_by': None, 'reviewed_at': None} for binding in inspection['bindings']]})
    write('evaluation-notes.json', {'schema_version': '1.0', 'execution_kind': 'not_run',
        'forge_revision': source, 'console_revision': None,
        'runtime_versions': {'python': sys.version.split()[0], 'docker': 'record before running'},
        'interventions': [], 'observations': ''})
    paths = {key: str(inputs / name) for key, name in (
        ('configuration', 'runtime-configuration.json'), ('policy', 'execution-policy.json'),
        ('inventory', 'runtime-inventory.json'), ('facts', 'facts.json'))}
    result = {'schema_version': '1.0', 'kind': 'forge-pilot', 'ready': False,
              'execution_authority': False, 'root': str(output), 'target_repo': descriptor['target_repo'],
              'run_dir': str(output / 'run'), 'task_file': descriptor['plan_input'], 'inputs': paths,
              'base_revision': descriptor['base_revision'], 'forge_revision': source,
              'review_file': str(inputs / 'registration-review.json'),
              'notes_file': str(inputs / 'evaluation-notes.json'),
              'next_step': 'Review SETUP.md and independently qualify the runtime bindings before registering them.'}
    (output / 'demo.json').unlink()  # One descriptor for this pilot, with host storage outside both repositories.
    (output / 'pilot.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    (output / 'SETUP.md').write_text('''# Your disposable Forge pilot

The baseline test passed. No model was called, image pulled, capability registered or run approved.

1. Read `inputs/plan-input.md` and `inputs/facts.json`. The target is the `target` directory.
2. Review `inputs/runtime-configuration.json` and `inputs/execution-policy.json`.
   The policy permits only `greeting.py` and `test_greeting.py`, with one unittest command.
   Confirm the pinned image is installed and contains Python 3.12. No dependencies are downloaded by the host.
3. Complete `inputs/registration-review.json` with independently observed evidence for the exact
   endpoint, protocol, model and parameters. Role requirements are suggestions for qualification,
   not proven capabilities. A model listing or a successful connection probe is insufficient.
4. In `inputs/runtime-inventory.json`, register only established capabilities and mark only
   qualified bindings `ready: true`. Leave unqualified fallbacks unavailable. Recompute binding
   hashes with `validate-runtime-configuration.py` if any configuration value changes.
5. Record actual tool versions in `inputs/evaluation-notes.json`. After attempting the run,
   set execution_kind to `live_model` or `controlled_fixture` and record every human correction.
6. In Console, select the four files named in `pilot.json`, check readiness, select `target`,
   and paste the task from `inputs/plan-input.md`. Review and approve the visible start checkpoint.
   Run one stage at a time. Inspect the diff, tests, logs and independent verdict before publication.

For the complete CLI recipe, qualification checklist, expected result and failure recovery,
read `docs/getting-started/governed-pilot.md` in your Forge checkout. Keep failed attempts as evidence.
Generation does not establish model quality. These local files need review before sharing.
''', encoding='utf-8')
    return result


def record_run(engine, notes_path: Path) -> dict:
    """Summarize real host receipts; keep operator claims distinct from observations."""
    notes = load(notes_path)
    fields = {'schema_version', 'execution_kind', 'forge_revision', 'console_revision',
              'runtime_versions', 'interventions', 'observations'}
    if (not isinstance(notes, dict) or set(notes) != fields or notes['schema_version'] != '1.0'
            or notes['execution_kind'] not in ('live_model', 'controlled_fixture')
            or not isinstance(notes['runtime_versions'], dict) or not notes['runtime_versions']
            or not all(isinstance(v, str) and v.strip() and len(v) <= 500 for v in notes['runtime_versions'].values())
            or not isinstance(notes['interventions'], list) or len(notes['interventions']) > 100
            or not all(isinstance(v, str) and 0 < len(v) <= 2000 for v in notes['interventions'])
            or not isinstance(notes['observations'], str) or len(notes['observations']) > 10000):
        raise ValueError('Complete evaluation-notes.json with execution kind, actual versions and human interventions')
    with engine.store.worker():
        state = engine.store.state()
        if state['status'] not in ('completed', 'failed', 'cancelled'):
            raise ValueError('Record a completed, failed or cancelled attempt; do not summarize active work')
        receipts = engine.store.receipts()
        proof = engine.verify_receipts() if state['status'] == 'completed' else {
            'locally_authenticated': False, 'errors': ['Incomplete run; no successful closure asserted']}
        commands = [{key: r[key] for key in ('id', 'stage', 'role', 'attempt', 'command_id', 'exit_code',
                    'output_ref', 'output_sha256', 'wall_time_ms', 'tests', 'purpose') if key in r}
                    for r in receipts if r['kind'] == 'command']
        def fingerprint(name):
            if not contained(engine.bundle, name).exists():
                return None
            data = read_bytes(engine.bundle, name)
            return {'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        configuration = state['configuration']
        providers = {p['id']: p for p in configuration['providers']}
        elapsed = (datetime.fromisoformat(state['updated_at'].replace('Z', '+00:00')) -
                   datetime.fromisoformat(state['created_at'].replace('Z', '+00:00'))).total_seconds()
        return {'schema_version': '1.0', 'kind': 'forge-evaluation-record',
                'run_id': state['id'], 'story_id': state['story_id'], 'status': state['status'],
                'base_revision': state['base_revision'], 'profile': state['profile'], 'attempt': state['attempt'],
                'created_at': state['created_at'], 'last_host_update': state['updated_at'],
                'elapsed_seconds_to_last_host_update': round(elapsed, 3),
                'host_version': state['host_version'], 'sandbox': state['sandbox'],
                'image': state['policy']['image'], 'configuration_sha256': state['configuration_sha256'],
                'policy_sha256': state['policy_sha256'], 'completed_stages': state['completed_stages'],
                'configured_models': [{'id': m['id'], 'model': m['model'],
                                       'protocol': providers[m['providerId']]['protocol']}
                                      for m in configuration['profile']['models']],
                'commands': commands, 'receipt_verification': proof,
                'evidence': [value for name in ('events.jsonl', 'changes.patch', 'quality-gates.json',
                                               'convergence-report.json') if (value := fingerprint(name))],
                'operator_declared': notes,
                'limits': ['Operator notes and model origin are not independently attested.',
                           'Local receipt verification is not remote attestation or a model-quality benchmark.',
                           'Elapsed time includes operator waits and may include regrading; tokens are not billing data.']}
