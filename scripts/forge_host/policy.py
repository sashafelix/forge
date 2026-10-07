"""Validate independently supplied execution policy. No repository-discovered grants."""
from pathlib import Path
import re
from pipeline_support.common import relative_path, read_bytes, STAGES
from runtime_configuration import load, validate_configuration
from .store import digest

def within(name: str, roots: list[str]) -> bool:
    return any(name == p or name.startswith(p+'/') for p in roots)

def validate(policy: dict) -> dict:
    allowed={'schema_version','source_paths','test_paths','commands','test_command','verify_command','test_format','report_path','image','max_turns','max_output_bytes','command_timeout','minimum_profile'}
    required=allowed-{'verify_command','report_path','minimum_profile'}
    if not isinstance(policy,dict) or set(policy)-allowed or required-set(policy) or policy['schema_version']!='1.0': raise ValueError('Invalid execution policy fields')
    for key in ('source_paths','test_paths'):
        values=policy[key]
        if not isinstance(values,list) or not 1<=len(values)<=100 or not all(isinstance(p,str) and relative_path(p) and not p.startswith(('.forge','docs/agent','agents/','.claude/')) for p in values): raise ValueError(f'{key}: literal bounded paths required')
    if any(within(a,[b]) or within(b,[a]) for a in policy['source_paths'] for b in policy['test_paths']): raise ValueError('Source and test write surfaces overlap')
    if not isinstance(policy['image'],str) or not re.fullmatch(r'(?:[A-Za-z0-9._:/-]+@)?sha256:[a-f0-9]{64}',policy['image']): raise ValueError('Sandbox image must be an immutable digest or local image ID')
    commands=policy['commands']
    if not isinstance(commands,dict) or not 1<=len(commands)<=20: raise ValueError('Register bounded commands')
    for name,argv in commands.items():
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',name) or not isinstance(argv,list) or not 1<=len(argv)<=40 or not all(isinstance(v,str) and v and len(v)<=1000 and not any(c in v for c in '\0\r\n') for v in argv): raise ValueError('Commands are fixed argv arrays, never model-generated shell strings')
    if not isinstance(policy['test_command'],str) or not isinstance(policy.get('verify_command',policy['test_command']),str) or policy['test_command'] not in commands or policy.get('verify_command',policy['test_command']) not in commands: raise ValueError('Unknown test or verification command')
    if policy['test_format'] not in ('unittest','pytest','junit'): raise ValueError('Supported test formats: unittest, pytest, junit')
    if policy['test_format']=='junit' and (not relative_path(policy.get('report_path','')) or within(policy['report_path'],policy['source_paths']+policy['test_paths'])): raise ValueError('JUnit requires a separate relative report_path outside source/test write surfaces')
    for key,maximum in [('max_turns',100),('max_output_bytes',2*1024*1024),('command_timeout',300)]:
        if type(policy[key]) is not int or not 1<=policy[key]<=maximum: raise ValueError(f'{key}: exceeds host limit {maximum}')
    if policy.get('minimum_profile','small') not in ('small','standard','high-risk'): raise ValueError('Unknown minimum profile')
    return policy

def bind(configuration_path: Path, policy_path: Path, inventory_path: Path) -> tuple[dict,dict,dict]:
    configuration=load(configuration_path);errors=validate_configuration(configuration)
    if errors: raise ValueError('; '.join(errors))
    policy=validate(load(policy_path));inventory=load(inventory_path)
    return configuration,policy,inventory
