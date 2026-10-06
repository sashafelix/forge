#!/usr/bin/env python3
"""Real Docker conformance; CI supplies a freshly built immutable fixture image."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from host_fixtures import target_repository, fixture_documents, ControlledProvider, inputs, finish
from forge_host.engine import Engine
from forge_host.sandbox import DockerSandbox
from forge_host.store import atomic


@unittest.skipUnless(os.environ.get('FORGE_DOCKER_IMAGE'), 'Explicit Docker conformance image is required')
class DockerTests(unittest.TestCase):
    def test_real_nine_stage_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / 'target'
            target_repository(repo)
            configuration, policy, inventory, facts = inputs()
            policy['image'] = os.environ['FORGE_DOCKER_IMAGE']
            provider = ControlledProvider(fixture_documents(root / 'documents'))
            engine = Engine.prepare(repo, root / 'run', 'Implement fixture value.', facts, configuration,
                                    policy, inventory, session_factory=provider)
            self.assertEqual(finish(engine)['status'], 'completed')
            self.assertTrue(engine.verify_receipts()['locally_authenticated'])

    def test_no_network_host_credentials_daemon_or_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy = inputs()[1]
            policy['image'] = os.environ['FORGE_DOCKER_IMAGE']
            code = """import os,socket,pathlib
assert os.getuid()!=0
assert os.getenv('FORGE_SANDBOX_SECRET') is None
assert not pathlib.Path('/var/run/docker.sock').exists()
assert not pathlib.Path('/workspace/.git').exists()
assert 'CapEff:\\t0000000000000000' in pathlib.Path('/proc/self/status').read_text()
try: pathlib.Path('/forbidden').write_text('bad')
except OSError: pass
else: raise AssertionError('Writable root')
try: socket.create_connection(('1.1.1.1',443),timeout=1)
except OSError: pass
else: raise AssertionError('Network available')
print('sandbox boundaries checked')
"""
            policy['commands']['probe'] = ['python3', '-B', 'probe.py']
            sandbox = DockerSandbox(policy, 'conformance')
            atomic(root / 'source.txt', b'fixture')
            atomic(root / 'probe.py', code.encode())
            sandbox.permissions(root)
            os.environ['FORGE_SANDBOX_SECRET'] = 'private-test-sentinel'
            try:
                result = sandbox.execute(root, 'probe')
                self.assertEqual(result['exit_code'], 0)
                self.assertIn('boundaries checked', result['output'])
            finally: os.environ.pop('FORGE_SANDBOX_SECRET', None)


if __name__ == '__main__': unittest.main()
