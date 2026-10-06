import json
from pathlib import Path
import tempfile
import unittest
from host_fixtures import create_engine, finish, ControlledSandbox
from forge_host.engine import Engine
from forge_host.store import Store
from forge_host.evaluation import grade, evaluate


class EvaluationTests(unittest.TestCase):
    def test_fresh_positive_and_unpatched_negative_control(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine, _ = create_engine(Path(temporary))
            finish(engine)
            result = grade(engine)
            self.assertEqual(result['status'], 'tests_passed_with_negative_control')
            self.assertFalse(result['model_review_repeated'])
            self.assertIn('/negative-control', ControlledSandbox.executions[-1])
            self.assertTrue(engine.verify_receipts()['locally_authenticated'])

    def test_duplicate_run_cannot_masquerade_as_repeated_sample(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            engine, provider = create_engine(root)
            finish(engine)
            manifest = {'schema_version': '1.0', 'runs': [
                {'label': 'baseline', 'run_dir': str(engine.store.root), 'repeat': 1},
                {'label': 'candidate', 'run_dir': str(engine.store.root), 'repeat': 1}]}
            before = len(engine.store.receipts())
            with self.assertRaisesRegex(ValueError, 'distinct host runs'):
                evaluate(manifest, lambda selected: engine)
            self.assertEqual(len(engine.store.receipts()), before)

    def test_paired_results_include_failures_and_uncertainty(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            engines = {}
            for label in ('baseline', 'candidate'):
                folder = root / label
                folder.mkdir()
                engine, provider = create_engine(folder)
                engines[engine.store.root] = engine
                if label == 'baseline': finish(engine)
                else: engine.cancel()
            manifest = {'schema_version': '1.0', 'runs': [
                {'label': label, 'run_dir': str(root / label / 'run'), 'repeat': 1} for label in ('baseline', 'candidate')]}
            result = evaluate(manifest, lambda selected: engines[selected])
            self.assertEqual([s['passed'] for s in result['summary']], [1, 0])
            self.assertLess(result['summary'][0]['wilson_95'][0], 1)


if __name__ == '__main__': unittest.main()
