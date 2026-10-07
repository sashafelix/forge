"""Role-scoped broker. Authoritative command receipts are always generated here."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import uuid
from pipeline_support.common import ROOT, contained, read_bytes
from agent_library import guidance_paths
from .context import files
from .policy import within
from .store import atomic, now, digest

ROLE_COMMANDS = {role['id'] for role in json.loads(read_bytes(Path(__file__).resolve().parents[2],
                 'docs/agent/role-contracts.json'))['roles'] if 'command_execute' in role['capabilities']}

def credential_path(name: str) -> bool:
    path = Path(name)
    return any(part in ('.ssh', '.aws', '.gnupg') for part in path.parts) or path.name in ('.env', 'id_rsa', 'id_ed25519') or path.name.startswith('.env.') or path.suffix in ('.pem', '.key', '.p12', '.pfx')

class PolicyViolation(RuntimeError):
    """An executed action crossed a boundary. Stop the stage, never invite another tool call."""

class Broker:
    def __init__(self, store, workspace: Path, bundle: Path, stage: str, role: str, invocation: str, sandbox, allowed_outputs: list[str], frozen: dict[str,str]):
        self.store=store;self.workspace=workspace;self.bundle=bundle;self.stage=stage;self.role=role;self.invocation=invocation
        self.sandbox=sandbox;self.policy=store.state()['policy'];self.allowed_outputs=allowed_outputs;self.frozen=frozen
        self.reads={};self.commands=[]

    def can_write(self,name: str) -> bool:
        if name not in self.allowed_outputs:return False
        if name in self.frozen:return False
        if self.role=='test_author':return within(name,self.policy['test_paths'])
        if self.role in ('implementer','refactorer'):return within(name,self.policy['source_paths'])
        return False

    def check_changes(self,before: dict[str,str]):
        try:after=files(self.workspace)
        except (ValueError,OSError) as exc:raise PolicyViolation('Unsafe command workspace: '+str(exc)[:1000]) from exc
        changes={name for name in set(before)|set(after) if before.get(name)!=after.get(name)}
        bad=[name for name in changes if not self.can_write(name)]
        if bad:raise PolicyViolation('Command changed files outside the active role/locked plan: '+', '.join(sorted(bad)[:20]))
        if any(after.get(name)!=fingerprint for name,fingerprint in self.frozen.items()):raise PolicyViolation('Frozen RED tests changed')
        return after

    def execute(self,action: dict) -> dict:
        if self.store.state()['status']=='cancelled':raise PolicyViolation('Run cancelled')
        if not isinstance(action,dict) or set(action)-{'kind','path','text','command','document'}:raise ValueError('Unknown broker action fields')
        kind=action.get('kind')
        if kind=='list':return {'files':[n for n in files(self.workspace) if not credential_path(n)][:self.store.state()['budgets']['max_context_files']]}
        if kind in ('read','search','guidance'):
            name=action.get('path','')
            if not isinstance(name,str) or credential_path(name):raise ValueError('Credential file reads are denied')
            receipt = None if kind=='guidance' else next((r for r in self.store.receipts() if r['kind']=='command' and r['output_ref']==name), None)
            if kind=='guidance':
                if name not in guidance_paths():raise ValueError('Read only a canonical agent, skill, catalog or convention')
                data=read_bytes(ROOT,name);read_name='forge://'+name;read_kind='convention'
            else:
                data=read_bytes(self.bundle if receipt else self.workspace,name);read_name=name;read_kind='test_output' if receipt else 'source'
            if receipt and hashlib.sha256(data).hexdigest()!=receipt['output_sha256']:
                raise PolicyViolation('Command evidence changed outside the host')
            budget=self.store.state()['budgets']
            if read_name not in self.reads and (len(self.reads)>=budget['max_context_files'] or sum(r['bytes'] for r in self.reads.values())+len(data)>budget['max_context_bytes']):raise ValueError('Stage context budget exhausted')
            self.reads[read_name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'kind':read_kind};text=data.decode('utf-8')
            for provider in self.store.state()['configuration']['providers']:
                ref=provider['auth'].get('credentialRef')
                secret=os.environ.get(ref[4:],'') if isinstance(ref,str) and ref.startswith('env:') else ''
                if secret:text=text.replace(secret,'[REDACTED]')
            if kind=='search':
                needle=action.get('text','')
                if not isinstance(needle,str) or not 1<=len(needle)<=200:raise ValueError('Use a bounded literal search')
                return {'path':name,'matches':[{'line':i,'text':line} for i,line in enumerate(text.splitlines(),1) if needle in line][:100]}
            return {'path':name,'text':text}
        if kind=='write':
            name=action.get('path','');target=contained(self.workspace,name)
            if not self.can_write(name):raise ValueError('Write denied by role, locked plan or frozen test policy')
            text=action.get('text')
            if not isinstance(text,str) or len(text.encode())>200000 or '\0' in text:raise ValueError('Write must be bounded UTF-8 text')
            executable=target.exists() and target.stat().st_mode & 0o111
            atomic(target,text.encode())
            if executable:os.chmod(target,0o700)
            self.sandbox.permissions(self.workspace)
            return {'path':name,'sha256':hashlib.sha256(text.encode()).hexdigest()}
        if kind=='command':return self.command(action.get('command',''))
        raise ValueError('Unknown action; submission is handled by the coordinator')

    def command(self, name: str) -> dict:
        if self.store.state()['status']=='cancelled':raise PolicyViolation('Run cancelled')
        if self.role not in ROLE_COMMANDS:raise ValueError('Role has no command authority')
        if not isinstance(name,str) or name not in self.policy['commands']:raise ValueError('Only registered command IDs may execute')
        before=files(self.workspace);command_id=uuid.uuid4().hex
        self.store.event('command.started',stage=self.stage,actor_role=self.role,invocation_id=self.invocation,safe_summary=name)
        started=now(); result=self.sandbox.execute(self.workspace,name,lambda:self.store.state()['status']=='cancelled')
        violation=None
        try:
            after=self.check_changes(before)
            if name in {self.policy['test_command'], self.policy.get('verify_command', self.policy['test_command'])} and after!=before:
                raise PolicyViolation('Test command changed story files; its result cannot authenticate this patch')
        except PolicyViolation as exc:
            violation=str(exc)[:1000];result['policy_error']=violation
        output=result.pop('output')
        # Known host credentials never enter evidence even if a provider/command echoes one.
        for provider in self.store.state()['configuration']['providers']:
            ref=provider['auth'].get('credentialRef')
            secret=os.environ.get(ref[4:],'') if isinstance(ref,str) and ref.startswith('env:') else ''
            if secret:output=output.replace(secret,'[REDACTED]')
        ref=f'evidence/command-{command_id}.log';atomic(self.bundle/ref,output.encode())
        receipt=self.store.receipt({'id':command_id,'kind':'command','invocation_id':self.invocation,'stage':self.stage,'role':self.role,'attempt':self.store.state()['attempt'],
            'configuration_sha256':self.store.state()['configuration_sha256'],'purpose':getattr(self,'purpose','stage'),
            'policy_sha256':self.store.state()['policy_sha256'],'base_revision':self.store.state()['base_revision'],'workspace_sha256':digest(before),'command_id':name,'started_at':started,
            **result,'output_ref':ref,'output_sha256':hashlib.sha256(output.encode()).hexdigest()})
        atomic(self.bundle/f'evidence/receipt-{command_id}.json',json.dumps(receipt,indent=2).encode())
        self.commands.append(receipt)
        failure=violation or result.get('stop_error') or result.get('test_error')
        self.store.event('command.completed',stage=self.stage,actor_role=self.role,invocation_id=self.invocation,artifact_refs=[ref,f'evidence/receipt-{command_id}.json'],safe_summary=f'{name}: exit {receipt["exit_code"]}'+('; rejected: '+failure if failure else ''))
        if violation:raise PolicyViolation(violation)
        if result.get('stop_error'):raise InterruptedError(result['stop_error'])
        return {key:receipt[key] for key in ('id','command_id','exit_code','tests','output_ref','test_error') if key in receipt}
