"""Fresh patch grading and paired, repeated-run summaries. No model-quality claims from fixtures."""
import math
from pathlib import Path
import shutil
import uuid
from .engine import Engine, read_json, write_json
from .store import Store
from .tools import Broker
from .sandbox import DockerSandbox
from pipeline_support.common import contained, read_bytes


def grade(engine):
    with engine.store.worker():
        state = engine.store.state()
        if state['status'] != 'completed' or not engine.verify_receipts()['locally_authenticated']:
            raise ValueError('Grade requires a completed run with reconciled local host receipts')
        try:
            return grade_completed(engine, state)
        finally:
            # Failed regrades also append command receipts and events.
            engine.project()


def grade_completed(engine, state):
    broker = Broker(engine.store, engine.workspace, engine.bundle, 'quality_gate', 'independent_verifier',
                    uuid.uuid4().hex, engine.sandbox, [], state['frozen_tests'])
    command = state['policy'].get('verify_command', state['policy']['test_command'])
    broker.purpose = 'regrade-positive'
    engine.fresh_verify(broker, command)
    positive = broker.commands[-1]
    if positive.get('test_error') or not positive['tests'] or positive['exit_code'] or any(c['outcome'] != 'passed' for c in positive['tests']['cases']):
        raise ValueError('Fresh patch regrade failed or skipped tests')
    control = engine.store.root / 'negative-control'
    if control.exists(): shutil.rmtree(control)
    shutil.copytree(engine.store.root / 'base', control)
    for name in state['frozen_tests']:
        from .store import atomic
        atomic(contained(control, name), read_bytes(engine.workspace, name))
    engine.sandbox.permissions(control)
    broker.workspace = control
    broker.purpose = 'regrade-negative-control'
    broker.command(command)
    negative = broker.commands[-1]
    if negative.get('test_error') or not negative['tests'] or not negative['exit_code'] or not negative['tests']['failed'] or negative['tests']['errors']:
        raise ValueError('Negative control did not fail a regression assertion on the unpatched base')
    result = {'schema_version': '1.0', 'run_id': state['id'], 'base_revision': state['base_revision'],
              'status': 'tests_passed_with_negative_control', 'positive_receipt': positive['id'],
              'negative_receipt': negative['id'], 'model_review_repeated': False,
              'limits': ['Tests and their semantic sufficiency still require independent review.']}
    write_json(engine.bundle, f"evidence/grade-{broker.invocation}.json", result)
    engine.record_invocation(broker, f"evidence/grade-{broker.invocation}.json", result, 'host-regrade')
    return result


def wilson(passed, total):
    z = 1.96
    rate = passed / total
    scale = 1 + z*z/total
    center = (rate + z*z/(2*total))/scale
    half = z * math.sqrt(rate*(1-rate)/total + z*z/(4*total*total))/scale
    return [round(max(0, center-half), 4), round(min(1, center+half), 4)]


def evaluate(manifest, engine_factory=None):
    if not isinstance(manifest, dict) or set(manifest) != {'schema_version', 'runs'} or manifest['schema_version'] != '1.0':
        raise ValueError('Evaluation manifest requires schema_version and runs')
    rows = manifest['runs']
    if not isinstance(rows, list) or not 2 <= len(rows) <= 100:
        raise ValueError('Supply 2–100 independently executed runs')
    result, paired, seen, group, prepared = [], {}, set(), {}, []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'label', 'run_dir', 'repeat'} or not isinstance(row['label'], str) or not 1 <= len(row['label']) <= 80 or type(row['repeat']) is not int or not 1 <= row['repeat'] <= 100:
            raise ValueError('Each run requires label, run_dir and repeat')
        root = Path(row['run_dir']).resolve()
        if root in seen: raise ValueError('Repeated rows must use distinct host runs, not replay one successful run')
        seen.add(root)
        engine = engine_factory(root) if engine_factory else Engine(Store(root))
        state = engine.store.state()
        key = (state['story_id'], state['base_revision'], state['task'], state['policy_sha256'], row['repeat'])
        labels = paired.setdefault(key, set())
        if row['label'] in labels: raise ValueError('Duplicate paired repeat')
        labels.add(row['label'])
        config = group.setdefault(row['label'], state['configuration_sha256'])
        if config != state['configuration_sha256']: raise ValueError('A label must bind one immutable model configuration')
        prepared.append((row, engine, state, config))
    if len(group) < 2 or any(labels != set(group) for labels in paired.values()):
        raise ValueError('Use at least two labels, with the same tasks/revisions/policies/repeats for every label')
    # Validate the entire pairing before appending any fresh grading evidence.
    for row, engine, state, config in prepared:
        outcome = {'label': row['label'], 'repeat': row['repeat'], 'run_id': state['id'],
                   'story_id': state['story_id'], 'base_revision': state['base_revision'],
                   'configuration_sha256': config, 'status': state['status'], 'tokens_estimated': state['tokens_estimated']}
        if state['status'] == 'completed':
            try:
                outcome['grade'] = grade(engine)
                outcome['passed'] = True
            except (ValueError, OSError, RuntimeError) as exc:
                outcome.update(passed=False, failure=str(exc)[:1000])
        else:
            outcome.update(passed=False, failure='Run did not complete')
        result.append(outcome)
    summary = []
    for label in sorted(group):
        samples = [r for r in result if r['label'] == label]
        passed = sum(r['passed'] for r in samples)
        summary.append({'label': label, 'runs': len(samples), 'passed': passed,
                        'pass_rate': passed/len(samples), 'wilson_95': wilson(passed, len(samples)),
                        'tokens_estimated_total': sum(r['tokens_estimated'] for r in samples)})
    return {'schema_version': '1.0', 'kind': 'paired-host-evaluation', 'runs': result, 'summary': summary,
            'warnings': ['Use multiple pinned tasks and at least three independent repeats per configuration.',
                         'Token counts are estimates; provider billing/cost is not inferred.',
                         'Fixture conformance does not establish production model quality or sandbox strength.']}
