import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from host_fixtures import ROOT, ControlledSandbox, create_engine, finish
from agent_library import agent_for_role, catalog, definition, library, validate
from forge_host.tools import Broker


class AgentLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def copy_library(self):
        for directory in ('agents', 'skills', 'docs/agent'):
            shutil.copytree(ROOT / directory, self.root / directory)
        return self.root

    def test_catalog_covers_every_role_and_keeps_skill_bodies_lazy(self):
        self.assertEqual(validate(), {'agents': 16, 'skills': 18})
        roles = json.loads((ROOT / 'docs/agent/role-contracts.json').read_text())['roles']
        for role in roles:
            self.assertEqual(agent_for_role(role['id'])['role'], role['id'])
        self.assertTrue(all('body' not in entry for entries in catalog().values() for entry in entries))
        self.assertTrue(all(entry['path'].endswith('/SKILL.md') for entry in catalog()['skills']))

    def test_validator_rejects_stale_copies_and_broken_references(self):
        root = self.copy_library()
        mirror = root / '.claude/agents/ai-pipeline-prepare.md'
        mirror.parent.mkdir(parents=True)
        mirror.write_text('stale prompt')
        with self.assertRaisesRegex(ValueError, 'obsolete Forge agent copies'):
            validate(root)
        mirror.unlink()
        (root / 'AGENTS.md').write_text('Read skills/skill-missing/SKILL.md')
        with self.assertRaisesRegex(ValueError, 'Missing file'):
            validate(root)

    def test_duplicate_identity_and_symlinked_definitions_are_rejected(self):
        root = self.copy_library()
        original = root / 'agents/ai-pipeline-prepare.md'
        duplicate = root / 'agents/duplicate.md'
        duplicate.write_bytes(original.read_bytes())
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            library(root)
        duplicate.unlink()
        original.unlink()
        original.symlink_to(ROOT / 'agents/ai-pipeline-prepare.md')
        with self.assertRaisesRegex(ValueError, 'Symlinks'):
            library(root)

    def test_frontmatter_accepts_crlf_without_changing_source_fingerprint(self):
        data = b'---\r\nname: example\r\ndescription: Example.\r\n---\r\nBody.\r\n'
        (self.root / 'example.md').write_bytes(data)
        parsed = definition(self.root, 'example.md')
        self.assertEqual(parsed['body'], 'Body.')
        self.assertEqual(parsed['bytes'], len(data))

    def test_claude_launcher_supplies_current_canonical_prompts_without_mirrors(self):
        spec = importlib.util.spec_from_file_location('launcher', ROOT / 'scripts/launch-claude.py')
        launcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(launcher)
        with patch.object(sys, 'argv', ['launch-claude.py', '--', '-p', 'task with spaces']), \
             patch.object(launcher.shutil, 'which', return_value='/installed/claude'), \
             patch.object(launcher.subprocess, 'call', return_value=0) as execute:
            self.assertEqual(launcher.main(), 0)
        argv = execute.call_args.args[0]
        definitions = json.loads(argv[argv.index('--agents') + 1])
        self.assertEqual(set(definitions), {entry['name'] for entry in library()['agents']})
        for entry in library()['agents']:
            self.assertIn(str(ROOT / entry['path']), definitions[entry['name']]['prompt'])
            self.assertEqual(definitions[entry['name']]['description'], entry['description'])
            self.assertEqual(set(definitions[entry['name']]), {'description', 'prompt'})
        self.assertLess(len(argv[2]), 24000)
        self.assertEqual(argv[-4:], ['--agent', 'ai-pipeline-rgr-orchestrator', '-p', 'task with spaces'])
        self.assertFalse((ROOT / '.claude/agents').exists())

    def test_guidance_reads_the_trusted_library_and_obeys_context_and_write_limits(self):
        engine, _ = create_engine(self.root)
        (engine.workspace / 'AGENTS.md').write_text('untrusted target instructions')
        broker = Broker(engine.store, engine.workspace, engine.bundle, 'prepare', 'repository_analyst',
                        'guidance-test', engine.sandbox, [], {})
        result = broker.execute({'kind': 'guidance', 'path': 'AGENTS.md'})
        self.assertEqual(result['text'], (ROOT / 'AGENTS.md').read_text())
        evidence = broker.reads['forge://AGENTS.md']
        self.assertEqual(evidence['sha256'], hashlib.sha256((ROOT / 'AGENTS.md').read_bytes()).hexdigest())
        self.assertEqual(evidence['kind'], 'convention')
        role_contracts = broker.execute({'kind': 'guidance', 'path': 'docs/agent/role-contracts.json'})
        self.assertIn('roles', json.loads(role_contracts['text']))
        for path in ('../AGENTS.md', '/etc/passwd', 'scripts/forge-host.py'):
            with self.assertRaisesRegex(ValueError, 'canonical'):
                broker.execute({'kind': 'guidance', 'path': path})
        with self.assertRaisesRegex(ValueError, 'Write denied'):
            broker.execute({'kind': 'write', 'path': 'AGENTS.md', 'text': 'replace guidance'})
        state = engine.store.state()
        state['budgets']['max_context_files'] = 2
        with patch.object(engine.store, 'state', return_value=state):
            with self.assertRaisesRegex(ValueError, 'budget exhausted'):
                broker.execute({'kind': 'guidance', 'path': 'skills/skill-security/SKILL.md'})

    def test_completed_host_run_records_canonical_agent_guidance(self):
        ControlledSandbox.executions = []
        engine, _ = create_engine(self.root)
        self.assertEqual(finish(engine)['status'], 'completed')
        manifests = list(engine.bundle.glob('context-*.json'))
        self.assertTrue(manifests)
        combined = '\n'.join(path.read_text() for path in manifests)
        self.assertIn('forge://AGENTS.md', combined)
        self.assertIn('forge://agents/ai-pipeline-quality-gate.md', combined)
        self.assertTrue(engine.verify_receipts()['locally_authenticated'])


if __name__ == '__main__':
    unittest.main()
