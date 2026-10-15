"""Synthetic transfer/plan fixtures: these tests are not live model-quality evidence."""
import copy
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from pipeline_support.handoff_transfer import (
    MAX_MEMBER, accept, canonical, inspect_bytes, parse_json, read_local, sha256,
    public_summary, verify_accepted,
)
from pipeline_support.delivery_planning import validate_plan, review_axes


def fixture():
    files = {
        'requirement.md': b'# Cancel a queued operation\r\n\r\nOnly queued operations may be cancelled.\r\n',
        'acceptance.feature': b'Feature: Cancel\r\n  @case_C1\r\n  Scenario: Queued\r\n    Given a queued operation\r\n    When I cancel it\r\n    Then it is cancelled\r\n  @case_C2\r\n  Scenario: Running\r\n    Given a running operation\r\n    When I cancel it\r\n    Then it is unchanged\r\n',
    }
    meta = dict(schema_version=1, kind='clarity-portable-handoff', run_id='REQ1', revision=1,
                profile='cucumber', scenario_ids=['C1', 'C2'],
                files={k: sha256(v) for k, v in files.items()},
                **{key: sha256(key.encode()) for key in ('draft_digest', 'context_digest', 'review_digest', 'engine_digest', 'plan_digest')})
    return files, meta


def packet(files=None, meta=None, extra=None):
    default_files, default_meta = fixture()
    contents = dict(default_files if files is None else files)
    contents['handoff.json'] = canonical(default_meta if meta is None else meta) + b'\n'
    if extra:
        contents.update(extra)
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        for name, body in contents.items():
            z.writestr(name, body)
    return out.getvalue()


def proposal(inspected):
    return {'schema_version': 1, 'story_id': 'STORY1', 'handoff_sha256': inspected['package_sha256'],
            'criteria': [{'sc_id': 'SC-' + str(i), 'scenario_ids': ['C' + str(i)],
                          'test_boundary': {'interface': 'Cancellation command', 'expected_behavior': 'The approved observable outcome',
                                            'oracle': 'The approved scenario and controlled fixture', 'limitations': 'Does not establish production availability'}}
                         for i in (1, 2)],
            'slices': [{'id': 'SLICE1', 'outcome': 'Cancel a queued operation through the public interface',
                        'criterion_ids': ['SC-1'], 'depends_on': []},
                       {'id': 'SLICE2', 'outcome': 'Refuse cancellation of running operations',
                        'criterion_ids': ['SC-2'], 'depends_on': ['SLICE1']}], 'regressions': []}


def quality():
    return {'schema_version': '1.0', 'story_id': 'STORY1', 'verdict': 'PASS',
            'reviewer_role': 'independent_verifier', 'reviewer_identity': 'synthetic-reviewer',
            'criterion_evidence': [{'sc_id': 'SC-' + str(i), 'status': 'PASS', 'tests': ['fixture-' + str(i)],
                                    'evidence_refs': ['synthetic-test-output.txt']} for i in (1, 2)],
            'hard_failures': [], 'changed_files': ['example.py'], 'artifact_refs': ['synthetic-test-output.txt']}


class HandoffTests(unittest.TestCase):
    def test_inspection_preserves_exact_bytes_and_has_no_authority(self):
        result = inspect_bytes(packet())
        self.assertEqual(result['files']['acceptance.feature'], fixture()[0]['acceptance.feature'])
        self.assertFalse(result['execution_authority'])
        self.assertFalse(result['sender_authenticated'])
        self.assertNotIn('files', public_summary(result))
        self.assertNotIn('_archive', public_summary(result))

    def test_changed_payload_is_rejected(self):
        files, meta = fixture(); files['requirement.md'] += b'changed'
        with self.assertRaises(ValueError): inspect_bytes(packet(files, meta))

    def test_private_audit_file_is_rejected(self):
        with self.assertRaises(ValueError): inspect_bytes(packet(extra={'sources.json': b'private'}))

    def test_traversal_is_rejected_without_extracting(self):
        with self.assertRaises(ValueError): inspect_bytes(packet(extra={'../outside.txt': b'bad'}))

    def test_missing_metadata_is_rejected(self):
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w') as z:
            for name, data in fixture()[0].items(): z.writestr(name, data)
        with self.assertRaises(ValueError): inspect_bytes(out.getvalue())

    def test_duplicate_archive_member_is_rejected(self):
        out = io.BytesIO(packet())
        with zipfile.ZipFile(out, 'a') as z:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                z.writestr('requirement.md', b'duplicate')
        with self.assertRaises(ValueError): inspect_bytes(out.getvalue())

    def test_symlink_archive_member_is_rejected(self):
        files, meta = fixture(); out = io.BytesIO()
        with zipfile.ZipFile(out, 'w') as z:
            for name, data in {**files, 'handoff.json': canonical(meta)}.items():
                item = zipfile.ZipInfo(name); item.create_system = 3
                item.external_attr = (stat.S_IFLNK | 0o777) << 16
                z.writestr(item, data)
        with self.assertRaises(ValueError): inspect_bytes(out.getvalue())

    def test_member_expansion_is_bounded(self):
        files, meta = fixture(); files['requirement.md'] = b'a' * (MAX_MEMBER + 1)
        meta['files']['requirement.md'] = sha256(files['requirement.md'])
        with self.assertRaises(ValueError): inspect_bytes(packet(files, meta))

    def test_invalid_utf8_is_rejected(self):
        files, meta = fixture(); files['requirement.md'] = b'\xff'
        meta['files']['requirement.md'] = sha256(files['requirement.md'])
        with self.assertRaises(ValueError): inspect_bytes(packet(files, meta))

    def test_metadata_cannot_declare_permissions(self):
        _, meta = fixture(); meta['execution_authority'] = True
        with self.assertRaises(ValueError): inspect_bytes(packet(meta=meta))

    def test_boolean_revision_is_rejected(self):
        _, meta = fixture(); meta['revision'] = True
        with self.assertRaises(ValueError): inspect_bytes(packet(meta=meta))

    def test_duplicate_scenario_ids_are_rejected(self):
        _, meta = fixture(); meta['scenario_ids'] = ['C1', 'C1']
        with self.assertRaises(ValueError): inspect_bytes(packet(meta=meta))

    def test_scenario_metadata_must_match_feature_tags(self):
        _, meta = fixture(); meta['scenario_ids'] = ['C1', 'C3']
        with self.assertRaises(ValueError): inspect_bytes(packet(meta=meta))

    def test_tag_like_text_inside_doc_string_is_ignored(self):
        files, meta = fixture()
        files['acceptance.feature'] += b'    And a message\n      """\n      @case_NOT_A_SCENARIO\n      """\n'
        meta['files']['acceptance.feature'] = sha256(files['acceptance.feature'])
        self.assertEqual(inspect_bytes(packet(files, meta))['metadata']['scenario_ids'], ['C1', 'C2'])

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaises(ValueError): parse_json(b'{"version":1,"version":2}')

    def test_nonfinite_json_is_rejected(self):
        with self.assertRaises(ValueError): parse_json(b'{"value":NaN}')

    def test_broken_zip_is_rejected(self):
        with self.assertRaises(ValueError): inspect_bytes(b'not a zip')

    def test_read_local_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp); (path / 'real').write_bytes(packet()); (path / 'link').symlink_to(path / 'real')
            with self.assertRaises(ValueError): read_local(path / 'link')

    def test_accept_requires_exact_digest_and_never_overwrites(self):
        result = inspect_bytes(packet())
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'accepted'
            with self.assertRaises(ValueError): accept(result, '0' * 64, target)
            self.assertFalse(target.exists())
            accepted = accept(result, result['package_sha256'], target)
            self.assertFalse(accepted['execution_authority'])
            self.assertEqual((target / 'acceptance.feature').read_bytes(), fixture()[0]['acceptance.feature'])
            self.assertEqual(verify_accepted(target)['status'], 'integrity-verified')
            with self.assertRaises(FileExistsError): accept(result, result['package_sha256'], target)

    def test_saved_payload_tamper_is_rejected(self):
        result = inspect_bytes(packet())
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'accepted'; accept(result, result['package_sha256'], target)
            (target / 'requirement.md').write_text('changed')
            with self.assertRaises(ValueError): verify_accepted(target)

    def test_saved_plan_tamper_is_rejected(self):
        result = inspect_bytes(packet())
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'accepted'; accept(result, result['package_sha256'], target)
            (target / 'plan-input.md').write_text('changed')
            with self.assertRaises(ValueError): verify_accepted(target)

    def test_changing_plan_and_receipt_hash_together_is_rejected(self):
        result = inspect_bytes(packet())
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'accepted'; accept(result, result['package_sha256'], target)
            (target / 'plan-input.md').write_bytes(b'changed')
            receipt = json.loads((target / 'handoff-binding.json').read_text())
            receipt['plan_input_sha256'] = sha256(b'changed')
            (target / 'handoff-binding.json').write_text(json.dumps(receipt))
            with self.assertRaises(ValueError): verify_accepted(target)

    @unittest.skipUnless(hasattr(__import__('os'), 'mkfifo'), 'POSIX FIFO test')
    def test_fifo_input_is_rejected_without_blocking(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'pipe'; os.mkfifo(target)
            with self.assertRaises(ValueError): read_local(target)


class DeliveryPlanTests(unittest.TestCase):
    def setUp(self):
        self.packet = inspect_bytes(packet()); self.plan = proposal(self.packet)

    def test_valid_plan_has_waves_but_no_scheduling_authority(self):
        result = validate_plan(self.packet, self.plan)
        self.assertEqual(result['dependency_waves'], [['SLICE1'], ['SLICE2']])
        self.assertFalse(result['parallel_execution_permitted'])
        self.assertTrue(result['semantic_review_required'])

    def test_stale_handoff_is_rejected(self):
        self.plan['handoff_sha256'] = '0' * 64
        with self.assertRaises(ValueError): validate_plan(self.packet, self.plan)

    def test_missing_scenario_is_rejected(self):
        self.plan['criteria'][1]['scenario_ids'] = ['C1']
        with self.assertRaises(ValueError): validate_plan(self.packet, self.plan)

    def test_unknown_scenario_is_rejected(self):
        self.plan['criteria'][1]['scenario_ids'] = ['NOT-APPROVED']
        with self.assertRaises(ValueError): validate_plan(self.packet, self.plan)

    def test_missing_test_oracle_is_rejected(self):
        self.plan['criteria'][0]['test_boundary']['oracle'] = ''
        with self.assertRaises(ValueError): validate_plan(self.packet, self.plan)

    def test_duplicate_delivery_owner_is_rejected(self):
        self.plan['slices'][1]['criterion_ids'] = ['SC-1', 'SC-2']
        with self.assertRaises(ValueError): validate_plan(self.packet, self.plan)

    def test_dependency_cycle_is_rejected(self):
        self.plan['slices'][0]['depends_on'] = ['SLICE2']
        with self.assertRaises(ValueError): validate_plan(self.packet, self.plan)

    def test_unknown_dependency_is_rejected(self):
        self.plan['slices'][0]['depends_on'] = ['MISSING']
        with self.assertRaises(ValueError): validate_plan(self.packet, self.plan)

    def test_regressions_are_not_required_to_be_red(self):
        self.plan['regressions'] = [{'test_id': 'existing-command', 'behavior': 'Existing commands retain their output', 'boundary': 'Public CLI'}]
        self.assertEqual(validate_plan(self.packet, self.plan)['status'], 'structurally-valid')

    def test_review_axes_preserve_canonical_result_and_identity(self):
        result = review_axes(self.packet, self.plan, quality())
        self.assertEqual(result['requirement_fidelity']['reported_status'], 'PASS')
        self.assertEqual(set(result['requirement_fidelity']['scenarios']), {'C1', 'C2'})
        self.assertFalse(result['tests_rerun']); self.assertFalse(result['publication_authority'])

    def test_hard_findings_block_both_axes(self):
        report = quality(); report['verdict'] = 'FAIL'
        report['hard_failures'] = [{'id': 'SYNTHETIC', 'message': 'Synthetic hard failure', 'evidence_refs': ['fixture.txt']}]
        result = review_axes(self.packet, self.plan, report)
        self.assertEqual(result['requirement_fidelity']['reported_status'], 'FAIL')
        self.assertEqual(result['engineering_quality']['reported_status'], 'FAIL')

    def test_missing_review_criterion_is_rejected(self):
        report = quality(); report['criterion_evidence'].pop()
        with self.assertRaises(ValueError): review_axes(self.packet, self.plan, report)

    def test_wrong_story_review_is_rejected(self):
        report = quality(); report['story_id'] = 'OTHER'
        with self.assertRaises(ValueError): review_axes(self.packet, self.plan, report)

    def test_warning_cannot_hide_failed_criterion(self):
        report = quality(); report['verdict'] = 'WARN'
        report['criterion_evidence'][0]['status'] = 'FAIL'
        with self.assertRaises(ValueError): review_axes(self.packet, self.plan, report)

    def test_warning_cannot_hide_hard_failure(self):
        report = quality(); report['verdict'] = 'WARN'
        report['hard_failures'] = [{'id': 'HARD', 'message': 'Blocking', 'evidence_refs': ['fixture.txt']}]
        with self.assertRaises(ValueError): review_axes(self.packet, self.plan, report)

    def test_contradictory_pass_is_rejected(self):
        report = quality(); report['criterion_evidence'][0]['status'] = 'FAIL'
        with self.assertRaises(ValueError): review_axes(self.packet, self.plan, report)


if __name__ == '__main__':
    unittest.main()
