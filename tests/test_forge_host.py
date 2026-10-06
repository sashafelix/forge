import json
from pathlib import Path
import tempfile
import unittest
from host_fixtures import create_engine, approve, finish, ControlledSandbox, inputs
from forge_host.engine import Engine
from forge_host.store import Store
from forge_host.sandbox import test_summary
from forge_host.policy import validate
from forge_host.tools import PolicyViolation


class HostTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        ControlledSandbox.executions = []
        ControlledSandbox.fail_once = False
    def tearDown(self): self.temporary.cleanup()

    def test_nine_stage_run_actual_red_green_and_fresh_regrade(self):
        engine, provider = create_engine(self.root)
        self.assertEqual(finish(engine)['status'], 'completed')
        self.assertTrue(engine.verify_receipts()['locally_authenticated'])
        self.assertEqual(len(engine.view()['completed_stages']), 9)
        commands = [r for r in engine.store.receipts() if r['kind'] == 'command']
        self.assertEqual([r['exit_code'] for r in commands], [1, 0, 0, 0])
        self.assertNotEqual(engine.store.state()['stage_receipts']['green_code'],
                            engine.store.state()['stage_receipts']['quality_gate'])
        self.assertIn('/verification', ControlledSandbox.executions[-1])
        lanes = json.loads((engine.bundle / 'green-result.json').read_text())['lane_results']
        self.assertEqual(len(lanes), 2)
        self.assertEqual(len([s for s in provider.sessions if s[0] == 'green_code']), 2)
        self.assertTrue((engine.bundle / 'changes.patch').read_text().startswith('--- a/'))

    def test_restart_events_and_modified_evidence(self):
        engine, provider = create_engine(self.root)
        approve(engine)
        engine.advance()
        restarted = Engine(Store(engine.store.root), session_factory=provider, sandbox_factory=ControlledSandbox)
        self.assertEqual(restarted.view()['stage'], 'brainstorm')
        self.assertEqual(finish(restarted)['status'], 'completed')
        page = restarted.store.events(0, 3)
        self.assertEqual(len(page), 3)
        self.assertGreater(restarted.store.events(page[-1]['sequence'], 3)[0]['sequence'], page[-1]['sequence'])
        receipt = next(r for r in restarted.store.receipts() if r['kind'] == 'command')
        (restarted.bundle / receipt['output_ref']).write_text('forged result')
        self.assertFalse(restarted.verify_receipts()['locally_authenticated'])

    def test_stale_approval_and_cancel_cannot_restart(self):
        engine, _ = create_engine(self.root)
        approval = engine.view()['approval']
        (engine.workspace / 'backend/fixture.py').write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'stale'):
            engine.approve(approval['id'], approval['binding_sha256'])
        stale = engine.store.state()
        engine.cancel()
        stale['status'] = 'ready'
        with self.assertRaisesRegex(ValueError, 'cancelled'): engine.store.update(stale)
        with self.assertRaises(ValueError): engine.advance()

    def test_interruption_restores_snapshot_requires_new_approval(self):
        engine, _ = create_engine(self.root)
        approve(engine)
        for _ in range(4): engine.advance()
        ControlledSandbox.fail_once = True
        with self.assertRaises(InterruptedError): engine.advance()
        self.assertTrue(engine.view()['recoverable'])
        self.assertIn('FixtureTests', (engine.workspace / 'test_fixture.py').read_text())
        engine.recover()
        self.assertNotIn('FixtureTests', (engine.workspace / 'test_fixture.py').read_text())
        self.assertEqual(engine.view()['status'], 'awaiting_approval')
        self.assertEqual(finish(engine)['status'], 'completed')

    def test_rejected_work_cannot_resume_and_remediation_is_bounded(self):
        engine, provider = create_engine(self.root, minimum='standard')
        provider.reject_verifier = True
        approve(engine)
        for _ in range(7): engine.advance()
        with self.assertRaisesRegex(ValueError, 'verifier'): engine.advance()
        with self.assertRaisesRegex(ValueError, 'bounded'): engine.recover()
        engine.recover('quality_gate')
        provider.reject_verifier = False
        self.assertEqual(finish(engine)['status'], 'completed')
        self.assertEqual(engine.view()['attempt'], 2)
        self.assertTrue(engine.verify_receipts()['locally_authenticated'])

    def test_locked_test_id_must_execute(self):
        engine, provider = create_engine(self.root)
        provider.documents['plan']['criterion_test_map'][0]['test_ids'] = ['invented.test']
        approve(engine)
        for _ in range(4): engine.advance()
        with self.assertRaisesRegex(ValueError, 'mapped executed RED'): engine.advance()
        with self.assertRaisesRegex(ValueError, 'exhausted'): engine.recover('plan')

    def test_readonly_role_command_cannot_modify_source(self):
        engine, _ = create_engine(self.root)
        from forge_host.tools import Broker
        class Mutating(ControlledSandbox):
            def execute(self, workspace, command, cancelled):
                (workspace / 'backend/fixture.py').write_text('bad')
                return {'exit_code': 0, 'output': 'changed'}
        broker = Broker(engine.store, engine.workspace, engine.bundle, 'quality_gate', 'independent_verifier',
                        'fixture-id', Mutating(engine.store.state()['policy'], 'id'), [], {})
        with self.assertRaises(PolicyViolation): broker.command('tests')

    def test_worker_lease_rejects_concurrent_worker(self):
        engine, _ = create_engine(self.root)
        with engine.store.worker():
            with self.assertRaisesRegex(ValueError, 'Another worker'):
                with engine.store.worker(): pass

    def test_source_edit_after_verification_revokes_authentication(self):
        engine, _ = create_engine(self.root)
        finish(engine)
        (engine.workspace / 'backend/fixture.py').write_text('def fixture_value():\n    return 999\n')
        self.assertFalse(engine.verify_receipts()['locally_authenticated'])

    def test_high_risk_reviews_and_checkpoint_bindings(self):
        from host_fixtures import target_repository, fixture_documents, ControlledProvider
        repo = self.root / 'target'; target_repository(repo)
        configuration, policy, inventory, facts = inputs()
        facts['facts'].update(security_sensitive=True, risk_tags=['security'])
        provider = ControlledProvider(fixture_documents(self.root / 'documents'))
        engine = Engine.prepare(repo, self.root / 'run', 'Implement fixture safely.', facts, configuration,
                                policy, inventory, session_factory=provider, sandbox_factory=ControlledSandbox)
        self.assertEqual(engine.view()['profile'], 'high-risk')
        approve(engine)
        for _ in range(5): engine.advance()
        self.assertEqual(engine.view()['approval']['reason'], 'before green_code')
        self.assertEqual(finish(engine)['status'], 'completed')
        self.assertTrue(engine.verify_receipts()['locally_authenticated'])
        for role in ('risk_reviewer', 'threat_modeler'):
            reviews = [s for s in provider.sessions if s[1] == role]
            self.assertEqual([s[0] for s in reviews], ['analyze', 'quality_gate'])
        checkpoints = [e['safe_summary'] for e in engine.store.events(0, 1000) if e['event_type']=='checkpoint.accepted']
        self.assertEqual(checkpoints, ['start run', 'before green_code', 'before close'])

    def test_missing_locked_artifact_fails_and_rejected_proposal_survives(self):
        engine, _ = create_engine(self.root, minimum='standard'); approve(engine); engine.advance()
        (engine.bundle / 'repository-intelligence.json').unlink()
        with self.assertRaisesRegex(ValueError, 'Locked stage artifact'): engine.advance()
        self.assertEqual(engine.view()['status'], 'failed')
        self.assertTrue(list((engine.bundle / 'evidence').glob('proposal-*.json')))

    def test_prepare_refuses_dirty_checkout(self):
        from host_fixtures import target_repository
        repo=self.root/'target';target_repository(repo)
        (repo/'uncommitted.txt').write_text('local work')
        config, policy, inventory, facts=inputs()
        with self.assertRaisesRegex(ValueError, 'must be clean'):
            Engine.prepare(repo,self.root/'run','Task',facts,config,policy,inventory,sandbox_factory=ControlledSandbox)
        self.assertFalse((self.root/'run').exists())

    def test_profile_projection_cannot_rewrite_host_governance(self):
        engine, _=create_engine(self.root,minimum='high-risk');approve(engine)
        path=engine.bundle/'profile-resolution.json';resolution=json.loads(path.read_text())
        resolution['manual_checkpoints']=[];path.write_text(json.dumps(resolution))
        with self.assertRaisesRegex(ValueError,'Pinned input'):engine.advance()
        self.assertEqual(engine.store.state()['manual_checkpoints'],['before green_code','before close'])

    def test_receipt_and_context_projections_cannot_forge_verified_display(self):
        engine, _=create_engine(self.root);finish(engine)
        context=engine.bundle/'context-prepare.json';original=context.read_bytes()
        context.write_text(context.read_text()+' ')
        self.assertFalse(engine.verify_receipts()['locally_authenticated']);context.write_bytes(original)
        ledger=engine.bundle/'host-receipts.json';document=json.loads(ledger.read_text())
        next(r for r in document['receipts'] if r['kind']=='command')['tests']['collected']=999
        ledger.write_text(json.dumps(document))
        self.assertFalse(engine.verify_receipts()['locally_authenticated'])

    def test_model_can_read_bound_command_logs_within_context_budget(self):
        from forge_host.tools import Broker
        engine, _=create_engine(self.root);approve(engine)
        for _ in range(5):engine.advance()
        receipt=next(r for r in engine.store.receipts() if r['kind']=='command')
        broker=Broker(engine.store,engine.workspace,engine.bundle,'green_code','implementer','log-reader',engine.sandbox,[],{})
        result=broker.execute({'kind':'read','path':receipt['output_ref']})
        self.assertIn('AssertionError',result['text'])
        self.assertEqual(broker.reads[receipt['output_ref']]['kind'],'test_output')
        (engine.bundle/receipt['output_ref']).write_text('changed log')
        with self.assertRaisesRegex(PolicyViolation,'evidence changed'):broker.execute({'kind':'read','path':receipt['output_ref']})

    def test_dead_worker_can_restore_checkpoint(self):
        engine, _=create_engine(self.root);approve(engine);engine.advance()
        state=engine.store.state();state['status']='running';state['stage']='prepare'
        engine.store.update(state)
        import time
        with engine.store.connect() as db:
            db.execute('INSERT OR REPLACE INTO lease VALUES (1,?,?,?)', ('abandoned',time.time()+600,99999999))
        self.assertIn('resume',engine.view()['available_actions'])
        engine.recover()
        self.assertEqual(engine.view()['status'],'awaiting_approval')

    def test_approved_fallback_only_before_first_action(self):
        engine, provider = create_engine(self.root)
        from forge_host.providers import Unavailable
        def unavailable_first(p,m,system,prompt):
            if m['id'] == 'local-coder':
                class Missing:
                    def estimated_input_tokens(self):return 10
                    def next(self):raise Unavailable('fixture unavailable')
                return Missing()
            return provider(p,m,system,prompt)
        engine.session_factory=unavailable_first;approve(engine);engine.advance()
        self.assertEqual(provider.sessions[-1][2],'frontier-reviewer')
        self.assertTrue(any(e['event_type']=='runtime.fallback' for e in engine.store.events()))
        class InterruptedAfterRead:
            calls=0
            def estimated_input_tokens(self):return 10
            def next(self):
                self.calls+=1
                if self.calls==1:return [{'id':'r','name':'forge_action','arguments':{'kind':'read','path':'backend/fixture.py'}}]
                raise Unavailable('fixture interrupted after read')
            def reply(self,results):pass
        engine.session_factory=lambda *args:InterruptedAfterRead()
        with self.assertRaises(Unavailable):engine.advance()
        self.assertTrue(engine.view()['recoverable'])

    def test_patch_can_be_checked_and_applied_in_the_original_checkout(self):
        import subprocess
        engine, _=create_engine(self.root);finish(engine)
        command=['git','-C',str(self.root/'target'),'apply']
        subprocess.run(command+['--check',str(engine.bundle/'changes.patch')],check=True,capture_output=True)
        subprocess.run(command+[str(engine.bundle/'changes.patch')],check=True,capture_output=True)
        result=subprocess.run(['python3','-B','-m','unittest','-v','test_fixture'],cwd=self.root/'target',capture_output=True)
        self.assertEqual(result.returncode,0)

    def test_credential_read_and_command_authority_follow_role_contract(self):
        from forge_host.tools import Broker
        engine, _=create_engine(self.root)
        (engine.workspace/'.env').write_text('PASSWORD=do-not-read')
        broker=Broker(engine.store,engine.workspace,engine.bundle,'brainstorm','specifier','fixture',engine.sandbox,[],{})
        self.assertNotIn('.env',broker.execute({'kind':'list'})['files'])
        with self.assertRaisesRegex(ValueError,'Credential'):broker.execute({'kind':'read','path':'.env'})
        with self.assertRaisesRegex(ValueError,'authority'):broker.command('tests')


class TestResultTests(unittest.TestCase):
    def test_missing_empty_all_skipped_and_nonverbose(self):
        for output in ('Ran 0 tests in 0s\n\nOK\n', 'Ran 1 test in 0s\n\nOK\n',
                       "test_a (test.A.test_a) ... skipped 'skip'\nRan 1 test in 0s\nOK (skipped=1)\n"):
            with self.assertRaises(ValueError): test_summary(output, 'unittest')
    def test_junit_and_pytest_case_ids(self):
        junit = b'<testsuite><testcase classname="pkg.Case" name="test_one"/></testsuite>'
        self.assertEqual(test_summary('', 'junit', junit)['cases'][0]['id'], 'pkg.Case.test_one')
        pytest = 'tests/test_x.py::test_one PASSED [100%]\n==== 1 passed in 0.01s ====\n'
        self.assertEqual(test_summary(pytest, 'pytest')['passed'], 1)
        with self.assertRaises(ValueError): test_summary('', 'junit', b'<!DOCTYPE a><testsuite/>')
    def test_policy_rejects_mutable_images_overlaps_and_unknown_command(self):
        policy = inputs()[1]
        for key, value in (('image', 'python:latest'), ('source_paths', ['test_fixture.py']), ('test_command', [])):
            changed = dict(policy, **{key: value})
            with self.assertRaises(ValueError): validate(changed)


if __name__ == '__main__': unittest.main()
