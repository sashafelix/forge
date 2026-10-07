"""Controlled provider and subprocess adapter for host conformance tests only.

The production CLI has no subprocess fallback. These fixed local commands execute
only the small test repository created below; they are not an isolation benchmark.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from forge_host.engine import Engine, OUTPUTS, ROLES
from forge_host.sandbox import test_summary
from runtime_configuration import binding_hash


def fixture_documents(root):
    spec = importlib.util.spec_from_file_location('generator', ROOT / 'scripts/generate-contract-fixture.py')
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    generator.generate(root)
    documents = {stage: json.loads((root / name).read_text()) for stage, name in OUTPUTS.items()}
    documents['plan']['tasks'][2]['outputs'] = ['frontend/fixture.py']
    documents['plan']['criterion_test_map'][0]['test_ids'] = ['test_fixture.FixtureTests.test_value']
    return documents


def target_repository(root):
    root.mkdir()
    for folder in ('backend', 'frontend'):
        (root / folder).mkdir()
        (root / folder / 'fixture.py').write_text('def fixture_value():\n    return 0\n')
    (root / 'test_fixture.py').write_text('# RED will add the required regression test.\n')
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(root), '-c', 'user.name=Fixture',
                    '-c', 'user.email=fixture@example.test', 'commit', '-qm', 'baseline'], check=True,
                   env={**os.environ, 'GIT_AUTHOR_DATE': '2000-01-01T00:00:00Z', 'GIT_COMMITTER_DATE': '2000-01-01T00:00:00Z'})


def inputs():
    configuration = json.loads((ROOT / 'tests/fixtures/runtime-configuration.json').read_text())
    # Both fixture providers are local, unauthenticated and registered by this test host.
    for provider in configuration['providers']:
        provider.update(locality='local', baseUrl='http://localhost:11434/v1',
                        auth={'mode': 'none', 'header': 'Authorization', 'credentialRef': None})
    policy = {'schema_version': '1.0', 'source_paths': ['backend', 'frontend'], 'test_paths': ['test_fixture.py'],
              'commands': {'tests': ['python3', '-B', '-m', 'unittest', '-v', 'test_fixture']},
              'test_command': 'tests', 'test_format': 'unittest', 'image': 'sha256:' + 'a' * 64,
              'max_turns': 10, 'max_output_bytes': 200000, 'command_timeout': 30}
    inventory = {'schema_version': '1.0', 'registrations': []}
    for model in configuration['profile']['models']:
        provider = next(p for p in configuration['providers'] if p['id'] == model['providerId'])
        inventory['registrations'].append({'model_id': model['id'], 'protocol': provider['protocol'],
                                           'binding_sha256': binding_hash(provider, model), 'ready': True,
                                           'capabilities': sorted({c for route in json.loads((ROOT / 'docs/agent/runtime-routing.json').read_text())['routes'] for c in route['required_model_capabilities']})})
    facts = {'story_id': 'HOST-FIXTURE-001', 'facts': {
        'risk_tags': [], 'blast_radius': 'low', 'uncertainty': 'low', 'changed_module_count': 1,
        'cross_service': False, 'contract_change': False, 'data_migration': False,
        'security_sensitive': False, 'infrastructure_change': False}}
    return configuration, policy, inventory, facts


class ControlledSandbox:
    executions = []
    fail_once = False
    def __init__(self, policy, run_id): self.policy = policy
    @staticmethod
    def readiness(image): return {'ready': True, 'backend': 'controlled-test-adapter'}
    def permissions(self, workspace): pass
    def stop(self): pass
    def execute(self, workspace, command, cancelled):
        if type(self).fail_once:
            type(self).fail_once = False
            raise InterruptedError('Controlled command interruption')
        if cancelled(): raise InterruptedError('Cancelled')
        type(self).executions.append(str(workspace))
        result = subprocess.run([sys.executable, '-B', '-m', 'unittest', '-v', 'test_fixture'],
                                cwd=workspace, capture_output=True, text=True, timeout=10)
        output = result.stdout + result.stderr
        return {'argv': self.policy['commands'][command], 'exit_code': result.returncode, 'output': output,
                'tests': test_summary(output, 'unittest'), 'wall_time_ms': 1}


class ControlledProvider:
    def __init__(self, documents):
        self.documents = documents
        self.reject_verifier = False
        self.sessions = []
    def __call__(self, provider, model, system, prompt):
        request = json.loads(prompt)
        self.sessions.append((request['stage'], request['role'], model['id']))
        parent = self
        class Session:
            def estimated_input_tokens(self): return 10
            def reply(self, results): pass
            def next(self):
                stage, role = request['stage'], request['role']
                document = copy.deepcopy(parent.documents[stage])
                if role != ROLES[stage]:
                    document = {'schema_version': '1.0', 'story_id': request['story_id'], 'role': role,
                                'reviewer_identity': 'proposed-label', 'status': 'PASS', 'findings': [], 'evidence_refs': ['detailed-plan.json']}
                if stage == 'quality_gate' and parent.reject_verifier:
                    document['verdict'] = 'FAIL'
                actions = []
                if stage == 'red_test':
                    actions.append({'kind': 'write', 'path': 'test_fixture.py', 'text':
                        'import unittest\nfrom backend.fixture import fixture_value as backend\n'
                        'from frontend.fixture import fixture_value as frontend\n'
                        'class FixtureTests(unittest.TestCase):\n'
                        '    def test_value(self):\n        self.assertEqual(backend() + frontend(), 42)\n'})
                if stage == 'green_code':
                    for name in request['allowed_write_files']:
                        actions.append({'kind': 'write', 'path': name, 'text': 'def fixture_value():\n    return 21\n'})
                actions.append({'kind': 'submit', 'document': document})
                return [{'id': str(i), 'name': 'forge_action', 'arguments': action} for i, action in enumerate(actions)]
        return Session()


def create_engine(root, minimum=None):
    repo = root / 'target'
    target_repository(repo)
    provider = ControlledProvider(fixture_documents(root / 'documents'))
    configuration, policy, inventory, facts = inputs()
    if minimum: policy['minimum_profile'] = minimum
    engine = Engine.prepare(repo, root / 'run', 'Implement the fixture value with a regression test.',
                            facts, configuration, policy, inventory,
                            session_factory=provider, sandbox_factory=ControlledSandbox)
    return engine, provider


def approve(engine):
    approval = engine.view()['approval']
    engine.approve(approval['id'], approval['binding_sha256'])


def finish(engine):
    for _ in range(15):
        view = engine.view()
        if view['status'] == 'awaiting_approval': approve(engine)
        elif view['status'] == 'ready': engine.advance()
        else: return view
    raise AssertionError('Run failed to terminate')
