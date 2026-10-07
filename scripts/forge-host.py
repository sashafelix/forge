#!/usr/bin/env python3
"""Opt-in governed Forge host. All policy/configuration inputs are supplied by the operator."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import signal
from forge_host.engine import Engine, read_json
from forge_host.store import Store
from forge_host.policy import bind
from forge_host.sandbox import DockerSandbox
from forge_host.context import repository_map
from runtime_configuration import load, resolve_configuration
from pipeline_support.common import STAGES, read_bytes, git, repository_root


def doctor(configuration=None, policy=None, inventory=None):
    result = {'schema_version': '1.0', 'host_version': '1.0', 'python': sys.version.split()[0],
              'sandbox': DockerSandbox.readiness(policy.get('image') if policy else None),
              'configuration': 'not supplied', 'routes': [], 'execution_authority': False}
    if configuration is not None:
        from forge_host.engine import ROLES
        result['routes'] = [resolve_configuration(configuration, {'stage': s, 'role': ROLES[s]},
                           inventory, 'operator', 'trusted_platform') for s in STAGES]
        result['configuration'] = 'valid operator bindings'
    result['ready'] = result['sandbox']['ready'] and configuration is not None
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    diagnostic = sub.add_parser('doctor')
    for name in ('configuration', 'policy', 'inventory'):
        diagnostic.add_argument('--' + name, type=Path)
    diagnostic.add_argument('--facts', type=Path)
    pilot = sub.add_parser('pilot', help='Create a disposable target and draft operator inputs; no model calls')
    pilot.add_argument('--configuration', type=Path, required=True)
    pilot.add_argument('--image', required=True, help='Reviewed, installed immutable test image ID')
    pilot.add_argument('--output', type=Path, required=True, help='New directory outside Forge; never overwritten')
    snapshot = sub.add_parser('snapshot', help='Record exact clean Forge and Console commits for evaluation')
    snapshot.add_argument('--console', type=Path, required=True)
    prepare = sub.add_parser('prepare')
    for name in ('repo', 'run-dir', 'task-file', 'facts', 'configuration', 'policy', 'inventory'):
        prepare.add_argument('--' + name, type=Path, required=True)
    for name in ('status', 'events', 'approve', 'advance', 'resume', 'retry', 'cancel', 'verify', 'grade', 'report'):
        command = sub.add_parser(name)
        command.add_argument('run_dir', type=Path)
        if name == 'report':
            command.add_argument('--notes', type=Path, required=True)
        if name == 'approve':
            command.add_argument('--approval-id', required=True)
            command.add_argument('--binding', required=True)
        if name == 'retry':
            command.add_argument('--stage', choices=STAGES, required=True)
        if name == 'events':
            command.add_argument('--after', type=int, default=0)
            command.add_argument('--limit', type=int, default=200)
    inspect = sub.add_parser('inspect')
    inspect.add_argument('bundle', type=Path)
    mapping = sub.add_parser('map')
    mapping.add_argument('repo', type=Path)
    evaluate = sub.add_parser('evaluate')
    evaluate.add_argument('manifest', type=Path)
    args = parser.parse_args()
    engine = None
    try:
        if args.command == 'snapshot':
            from forge_host.pilot import evaluation_snapshot
            result = evaluation_snapshot(args.console)
        elif args.command == 'pilot':
            from forge_host.pilot import create_pilot
            result = create_pilot(args.output, args.configuration, args.image)
        elif args.command == 'doctor':
            paths = (args.configuration, args.policy, args.inventory)
            if any(paths) and not all(paths):
                raise ValueError('Supply configuration, policy and inventory together')
            result = doctor(*bind(*paths)) if all(paths) else doctor()
            if args.facts:
                if not all(paths):raise ValueError('Task facts require the complete operator input set')
                from forge_host.engine import module
                resolver = module('resolve-profile')
                _, facts = resolver.require_facts(load(args.facts))
                profile, _, _ = resolver.classify(facts)
                configuration, policy, inventory = bind(*paths)
                if resolver.PROFILE_RANK[policy.get('minimum_profile','small')] > resolver.PROFILE_RANK[profile]:profile = policy['minimum_profile']
                selected = next(p for p in read_json(Path(__file__).resolve().parents[1], 'docs/agent/workflow-profiles.json')['profiles'] if p['id']==profile)
                result.update(profile=profile, manual_checkpoints=selected['manual_checkpoints'], specialist_roles=resolver.resolve_specialists(selected,facts))
                result['routes'] += [resolve_configuration(configuration, {'stage': stage, 'role': role},
                                    inventory, 'operator', 'trusted_platform')
                                    for role in result['specialist_roles'] for stage in ('analyze', 'quality_gate')]
        elif args.command == 'prepare':
            configuration, policy, inventory = bind(args.configuration, args.policy, args.inventory)
            task = read_bytes(args.task_file.parent, args.task_file.name).decode('utf-8')
            engine = Engine.prepare(args.repo, args.run_dir, task, load(args.facts),
                                    configuration, policy, inventory)
            result = engine.view()
        elif args.command == 'inspect':
            from forge_host.engine import module
            errors = module('validate-run-bundle').validate(args.bundle) + module('validate-run-governance').validate(args.bundle)
            result = {'schema_version': '1.0', 'status': 'blocked' if errors else 'consistent',
                      'authority': 'advisory', 'authenticated_execution': False, 'errors': errors,
                      'limits': ['Bundle labels and signatures alone do not authenticate execution or approvals.']}
        elif args.command == 'map':
            import tempfile
            from forge_host.engine import archive_repository
            repo = repository_root(args.repo)
            revision = git(repo, 'rev-parse', 'HEAD').decode().strip()
            with tempfile.TemporaryDirectory() as temporary:
                snapshot = Path(temporary) / 'source'
                archive_repository(repo, revision, snapshot)
                result = repository_map(snapshot, revision)
        elif args.command == 'evaluate':
            from forge_host.evaluation import evaluate
            result = evaluate(load(args.manifest))
        else:
            engine = Engine(Store(args.run_dir))
            if args.command == 'status':
                result = engine.view()
            elif args.command == 'events':
                events = engine.store.events(args.after, args.limit)
                result = {'events': events, 'next_cursor': events[-1]['sequence'] if events else args.after}
            elif args.command == 'approve':
                engine.approve(args.approval_id, args.binding)
                result = engine.view()
            elif args.command == 'advance':
                result = engine.advance()
            elif args.command in ('resume', 'retry'):
                result = engine.recover(args.stage if args.command == 'retry' else None)
            elif args.command == 'cancel':
                result = engine.cancel()
            elif args.command == 'verify':
                result = engine.verify_receipts()
            elif args.command == 'report':
                from forge_host.pilot import record_run
                result = record_run(engine, args.notes)
            else:
                from forge_host.evaluation import grade
                result = grade(engine)
        print(json.dumps(result, sort_keys=True))
        return 1 if result.get('status') == 'blocked' or result.get('locally_authenticated') is False else 0
    except KeyboardInterrupt:
        if engine:
            engine.cancel()
        print(json.dumps({'status': 'cancelled', 'error': 'Operator interrupted the command'}))
        return 130
    except (ValueError, OSError, RuntimeError, KeyError, TypeError, UnicodeError, RecursionError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)[:2000]}))
        return 1


if __name__ == '__main__':
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    raise SystemExit(main())
