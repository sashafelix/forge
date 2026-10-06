#!/usr/bin/env python3
"""Real Docker conformance; CI supplies a freshly built immutable fixture image."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from host_fixtures import target_repository, fixture_documents, ControlledProvider, inputs, finish, approve
from forge_host.engine import Engine
from forge_host.sandbox import DockerSandbox
from forge_host.store import atomic
from forge_host.tools import PolicyViolation


def prepare_with_test_prelude(root, prelude, timeout=30):
    repo=root / 'target';target_repository(repo)
    configuration, policy, inventory, facts=inputs()
    policy.update(image=os.environ['FORGE_DOCKER_IMAGE'], command_timeout=timeout)
    provider=ControlledProvider(fixture_documents(root / 'documents'))
    def factory(*args):
        session=provider(*args)
        next_action=session.next
        def next_with_prelude():
            calls=next_action()
            for call in calls:
                action=call['arguments']
                if action.get('kind')=='write' and action.get('path')=='test_fixture.py':
                    action['text']=prelude+action['text']
            return calls
        session.next=next_with_prelude
        return session
    engine=Engine.prepare(repo, root / 'run', 'Implement fixture value.', facts, configuration,
                          policy, inventory, session_factory=factory)
    approve(engine)
    for _ in range(4):engine.advance()
    return engine


@unittest.skipUnless(os.environ.get('FORGE_DOCKER_IMAGE'), 'Explicit Docker conformance image is required')
class DockerTests(unittest.TestCase):
    def test_cache_symlink_cannot_reach_checkpoint_copying(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            private=root / 'private.txt';private.write_text('host-only-sentinel')
            prelude=("from pathlib import Path\nPath('__pycache__').mkdir(exist_ok=True)\n"
                     f"Path('__pycache__/escape').symlink_to({str(private)!r})\n")
            engine=prepare_with_test_prelude(root, prelude)
            with self.assertRaisesRegex(PolicyViolation, 'Symlink'):engine.advance()
            self.assertEqual(engine.view()['status'], 'failed')
            self.assertFalse((engine.store.root / 'checkpoints/green_code').exists())
            receipt=next(r for r in engine.store.receipts() if r['kind']=='command')
            self.assertIn('Symlink', receipt['policy_error'])
            self.assertIn('AssertionError', (engine.bundle / receipt['output_ref']).read_text())

    def test_invalid_collection_and_timeout_retain_output(self):
        for label, prelude, error in (
            ('invalid', "print('before invalid collection', flush=True)\nraise RuntimeError('collection fixture')\n", ValueError),
            ('timeout', "import time\nprint('before timeout', flush=True)\ntime.sleep(10)\n", InterruptedError)):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                engine=prepare_with_test_prelude(Path(temporary), prelude, timeout=1)
                with self.assertRaises(error):engine.advance()
                self.assertEqual(engine.view()['status'], 'failed')
                self.assertEqual(engine.view()['recoverable'], label=='timeout')
                receipt=next(r for r in engine.store.receipts() if r['kind']=='command')
                self.assertIn('before '+('invalid collection' if label=='invalid' else 'timeout'),
                              (engine.bundle / receipt['output_ref']).read_text())
                self.assertIn('test_error' if label=='invalid' else 'stop_error', receipt)

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
