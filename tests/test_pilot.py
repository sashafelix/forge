import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from host_fixtures import ROOT, create_engine, finish
from forge_host.pilot import create_pilot, evaluation_snapshot, record_run
from runtime_configuration import inspect_configuration, resolve_configuration


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.configuration = ROOT / 'tests/fixtures/runtime-configuration.json'
        self.image = 'sha256:' + 'a' * 64

    def create(self):
        return create_pilot(self.root / 'pilot', self.configuration, self.image)

    def test_drafts_are_consistent_but_never_register_capabilities(self):
        original = self.configuration.read_bytes()
        pilot = self.create()
        self.assertFalse(pilot['ready'])
        self.assertFalse(pilot['execution_authority'])
        config = json.loads(Path(pilot['inputs']['configuration']).read_text())
        inventory = json.loads(Path(pilot['inputs']['inventory']).read_text())
        bindings = inspect_configuration(config)['bindings']
        for registration, binding in zip(inventory['registrations'], bindings):
            self.assertEqual(registration['binding_sha256'], binding['binding_sha256'])
            self.assertFalse(registration['ready'])
            self.assertEqual(registration['capabilities'], [])
        with self.assertRaisesRegex(ValueError, 'No independently registered'):
            resolve_configuration(config, {'stage': 'prepare', 'role': 'repository_analyst'},
                                  inventory, 'operator', 'operator')
        review = json.loads(Path(pilot['review_file']).read_text())
        self.assertIn('repository_analysis', review['models'][0]['requirements_by_role']['repository_analyst'])
        self.assertEqual(self.configuration.read_bytes(), original)
        self.assertFalse(Path(pilot['run_dir']).exists())
        self.assertFalse(Path(pilot['inputs']['facts']).is_relative_to(pilot['target_repo']))
        self.assertFalse((self.root / 'pilot/demo.json').exists())
        clean = subprocess.check_output(['git', '-C', pilot['target_repo'], 'status', '--porcelain'], text=True)
        self.assertEqual(clean, '')

    def test_refuses_overwrites_symlinks_placeholders_and_forge_storage(self):
        pilot = self.create()
        before = Path(pilot['inputs']['inventory']).read_bytes()
        with self.assertRaises(FileExistsError):
            self.create()
        self.assertEqual(Path(pilot['inputs']['inventory']).read_bytes(), before)
        link = self.root / 'link'
        link.symlink_to(self.root / 'pilot', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            create_pilot(link / 'child', self.configuration, self.image)
        for image in ('python:latest', 'sha256:' + '0' * 64):
            with self.assertRaises(ValueError):
                create_pilot(self.root / 'invalid', self.configuration, image)
            self.assertFalse((self.root / 'invalid').exists())
        with self.assertRaisesRegex(ValueError, 'outside the Forge'):
            create_pilot(ROOT / 'generated-pilot', self.configuration, self.image)

    def test_invalid_configuration_fails_before_creating_a_target(self):
        config = json.loads(self.configuration.read_text())
        config['providers'][1]['auth']['credentialRef'] = 'literal-secret'
        source = self.root / 'invalid.json'
        source.write_text(json.dumps(config))
        with self.assertRaises(ValueError):
            create_pilot(self.root / 'pilot', source, self.image)
        self.assertFalse((self.root / 'pilot').exists())

    def test_cli_creates_drafts_without_docker_or_a_provider(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/forge-host.py'), 'pilot',
                                 '--configuration', str(self.configuration), '--image', self.image,
                                 '--output', str(self.root / 'cli')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(json.loads(result.stdout)['ready'])

    def test_report_uses_actual_receipts_and_keeps_fixture_notes_explicit(self):
        pilot = self.create()
        notes_path = Path(pilot['notes_file'])
        notes = json.loads(notes_path.read_text())
        (self.root / 'host').mkdir()
        engine, _ = create_engine(self.root / 'host')
        with self.assertRaises(ValueError):
            record_run(engine, notes_path)
        notes.update(execution_kind='controlled_fixture', runtime_versions={'python': sys.version.split()[0]},
                     interventions=['Controlled fixture supplied stage documents; no live model was used.'])
        notes_path.write_text(json.dumps(notes))
        with self.assertRaisesRegex(ValueError, 'active work'):
            record_run(engine, notes_path)
        self.assertEqual(finish(engine)['status'], 'completed')
        report = record_run(engine, notes_path)
        self.assertEqual(report['operator_declared']['execution_kind'], 'controlled_fixture')
        self.assertTrue(report['receipt_verification']['locally_authenticated'])
        self.assertTrue(any(c['stage'] == 'red_test' and c['exit_code'] != 0 for c in report['commands']))
        self.assertTrue(any(c['stage'] == 'green_code' and c['exit_code'] == 0 for c in report['commands']))
        self.assertTrue(any(e['path'] == 'changes.patch' for e in report['evidence']))
        self.assertGreaterEqual(report['elapsed_seconds_to_last_host_update'], 0)
        rendered = json.dumps(report)
        self.assertNotIn('authority.key', rendered)
        self.assertNotIn('signature', rendered)

    def test_cancelled_attempt_can_be_reported_without_claiming_success(self):
        pilot = self.create()
        notes_path = Path(pilot['notes_file'])
        notes = json.loads(notes_path.read_text())
        notes.update(execution_kind='controlled_fixture', runtime_versions={'python': sys.version.split()[0]})
        notes_path.write_text(json.dumps(notes))
        (self.root / 'host').mkdir()
        engine, _ = create_engine(self.root / 'host')
        engine.cancel()
        report = record_run(engine, notes_path)
        self.assertEqual(report['status'], 'cancelled')
        self.assertFalse(report['receipt_verification']['locally_authenticated'])
        self.assertFalse(any(e['path'] == 'changes.patch' for e in report['evidence']))

    def test_snapshot_pins_both_clean_revisions_and_rejects_local_changes(self):
        for name in ('forge', 'console'):
            root = self.root / name
            root.mkdir()
            (root / 'VERSION').write_text('2.3.0\n')
            (root / 'package.json').write_text(json.dumps({'name': 'agent-pipeline-ui', 'version': '0.9.0'}))
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(root), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                            '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Baseline'], check=True)
        with patch('forge_host.pilot.ROOT', self.root / 'forge'):
            result = evaluation_snapshot(self.root / 'console')
            self.assertEqual(result['qualification'], 'not_established_by_snapshot')
            self.assertEqual(len(result['sources']['forge']['commit']), 40)
            self.assertFalse(result['sources']['console']['dirty'])
            (self.root / 'console/untracked.txt').write_text('Unsaved changes')
            with self.assertRaisesRegex(ValueError, 'must be clean'):
                evaluation_snapshot(self.root / 'console')


if __name__ == '__main__':
    unittest.main()
