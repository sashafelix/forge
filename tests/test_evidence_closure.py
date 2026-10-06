"""False-pass and history regressions from the research probes."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from evidence_validation import validate_attempts

def load(name):
    spec=importlib.util.spec_from_file_location(name, ROOT/'scripts'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

fixture=load('generate-contract-fixture')
validators=[load('validate-run-bundle'),load('validate-run-governance')]

class EvidenceTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.run=Path(self.temp.name)/'run';fixture.generate(self.run)

    def check_rejected(self, text):
        for validator in validators:
            self.assertTrue(any(text in e for e in validator.validate(self.run)))

    def test_baseline_and_missing_log(self):
        for validator in validators:self.assertEqual(validator.validate(self.run),[])
        (self.run/'evidence/verify-test.log').unlink();self.check_rejected('Missing file')

    def test_failed_green_and_empty_suite(self):
        path=self.run/'green-result.json';doc=json.loads(path.read_text())
        doc['commands'][0]['exit_code']=17;path.write_text(json.dumps(doc))
        self.check_rejected('nonzero')
        (self.run/'evidence/green-test.log').write_text('Ran 0 tests in 0.000s\nOK')
        self.check_rejected('no executed tests')

    def test_red_success_cannot_prove_regression(self):
        path=self.run/'red-result.json';doc=json.loads(path.read_text())
        doc['commands'][0]['exit_code']=0;path.write_text(json.dumps(doc))
        self.check_rejected('expected failure')

    def test_symlink_and_traversal_evidence(self):
        p=self.run/'evidence/verify-test.log';p.unlink();p.symlink_to(self.run/'brainstorm.json')
        self.check_rejected('Symlinks')
        p=self.run/'quality-gates.json';doc=json.loads(p.read_text())
        doc['criterion_evidence'][0]['evidence_refs']=['../outside.log'];p.write_text(json.dumps(doc))
        self.check_rejected('Unsafe relative path')

    def test_attempt_suffix_preserves_prefix_and_rejects_skips(self):
        events=[json.loads(line) for line in (self.run/'events.jsonl').read_text().splitlines()]
        # A full first attempt requiring remediation may rerun from GREEN, never after terminal closure.
        events=[e for e in events if e['event_type']!='run.completed']
        stages=['green_code','refactor','quality_gate','converge']
        unrejected = list(events)
        events.append({'attempt':1,'stage':'close','event_type':'stage.failed'})
        events.append({'attempt':2,'stage':'green_code','event_type':'attempt.started'})
        events += [{'attempt':2,'stage':s,'event_type':'stage.completed'} for s in stages]
        self.assertEqual(validate_attempts(events,2),[])
        self.assertTrue(validate_attempts(events[:-1],2))
        self.assertTrue(validate_attempts(events+[{'attempt':2,'stage':'green_code','event_type':'stage.completed'}],2))
        self.assertTrue(validate_attempts(unrejected + events[-5:],2))

if __name__=='__main__':unittest.main()
