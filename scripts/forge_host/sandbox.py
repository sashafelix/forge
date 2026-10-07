"""Disposable Docker commands: no network, host secrets, Git history or daemon mount."""
from __future__ import annotations
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET
from pipeline_support.common import contained, read_bytes

def test_summary(text: str, kind: str, report: bytes | None = None) -> dict:
    cases=[]
    if kind=='junit':
        if not report or len(report)>2*1024*1024 or b'<!DOCTYPE' in report or b'<!ENTITY' in report: raise ValueError('Missing/unsafe JUnit report')
        root=ET.fromstring(report); nodes=list(root.iter('testcase'))
        cases=[{'id':'.'.join(filter(None,[c.get('classname'),c.get('name')])), 'outcome':'failed' if c.find('failure') is not None else 'error' if c.find('error') is not None else 'skipped' if c.find('skipped') is not None else 'passed'} for c in nodes]
        failed=sum(c['outcome']=='failed' for c in cases);errors=sum(c['outcome']=='error' for c in cases);skipped=sum(c['outcome']=='skipped' for c in cases)
        collected=len(cases);passed=collected-failed-errors-skipped
    elif kind=='unittest':
        counts=re.findall(r'^Ran (\d+) tests? in ',text,re.M)
        if len(counts)!=1: raise ValueError('Expected one unittest collection/result summary')
        collected=int(counts[0]); failed=errors=skipped=0
        ending=re.search(r'^(?:OK|FAILED)(?: \(([^\n]*)\))?\s*$',text,re.M)
        if not ending: raise ValueError('Missing unittest outcome')
        for key,value in re.findall(r'(failures|errors|skipped)=(\d+)',ending.group(1) or ''):
            if key=='failures': failed=int(value)
            elif key=='errors': errors=int(value)
            else: skipped=int(value)
        passed=collected-failed-errors-skipped
        for name,identity,outcome in re.findall(r'^(\S+) \(([^)]+)\)(?:\n[^\n]*)? \.\.\. (ok|FAIL|ERROR|skipped[^\n]*)\s*$',text,re.M):
            cases.append({'id':identity if identity.endswith('.'+name) else identity+'.'+name,'outcome':{'ok':'passed','FAIL':'failed','ERROR':'error'}.get(outcome,'skipped')})
    else:
        summaries=[line for line in text.splitlines() if re.search(r'\d+ (?:passed|failed|error|skipped)',line) and (line.startswith('=') or re.search(r' in [\d.]+s',line))]
        if not summaries: raise ValueError('Missing pytest result summary')
        counts={key:int(value) for value,key in re.findall(r'(\d+) (passed|failed|errors?|skipped)',summaries[-1])}
        passed=counts.get('passed',0);failed=counts.get('failed',0);errors=counts.get('error',counts.get('errors',0));skipped=counts.get('skipped',0);collected=passed+failed+errors+skipped
        cases=[{'id':identity,'outcome':{'PASSED':'passed','FAILED':'failed','ERROR':'error','SKIPPED':'skipped'}[outcome]} for identity,outcome in re.findall(r'^(\S+::\S+)\s+(PASSED|FAILED|ERROR|SKIPPED)\b',text,re.M)]
    if collected<=0 or passed<0 or collected==skipped: raise ValueError('Empty/all-skipped test suite cannot prove a criterion')
    if len(cases)!=collected or len({c['id'] for c in cases})!=collected:raise ValueError('Tests must report unique case IDs; use verbose unittest/pytest output or JUnit')
    if any(sum(c['outcome']==outcome for c in cases)!=count for outcome,count in [('passed',passed),('failed',failed),('error',errors),('skipped',skipped)]):
        raise ValueError('Test case outcomes contradict the result summary')
    return {'collected':collected,'passed':passed,'failed':failed,'errors':errors,'skipped':skipped,'cases':cases}

class DockerSandbox:
    def __init__(self, policy: dict, run_id: str):self.policy=policy;self.run_id=run_id

    def permissions(self, workspace: Path):
        if hasattr(os,'getuid') and os.getuid()==0:
            for path in [workspace,*workspace.rglob('*')]:
                if path.is_symlink():raise ValueError('Symlink in sandbox workspace')
                os.chown(path,65534,65534)
                executable=path.stat().st_mode & 0o111
                os.chmod(path,0o700 if path.is_dir() or executable else 0o600)

    @staticmethod
    def readiness(image: str | None = None) -> dict:
        if not hasattr(os,'getuid'):return {'ready':False,'reason':'Use Linux/macOS with a Linux Docker engine, or run the host inside WSL.'}
        binary=shutil.which('docker')
        if not binary:return {'ready':False,'reason':'Docker is required for command isolation; no host-shell fallback is provided.'}
        try:
            probe=subprocess.run([binary,'info','--format','{{.OSType}}'],capture_output=True,text=True,timeout=10)
            if probe.returncode or probe.stdout.strip()!='linux': return {'ready':False,'reason':'A reachable Linux Docker engine is required.'}
            if image:
                found=subprocess.run([binary,'image','inspect',image,'--format','{{.Id}}'],capture_output=True,text=True,timeout=10)
                if found.returncode:return {'ready':False,'reason':'The approved immutable image is not installed. Pull/build it explicitly before preparing the run.'}
            return {'ready':True,'backend':'docker','network':'none','capabilities_dropped':'ALL','host_shell':False}
        except (OSError,subprocess.TimeoutExpired):return {'ready':False,'reason':'Docker readiness check failed.'}

    def stop(self):
        if not shutil.which('docker'):return
        result=subprocess.run(['docker','ps','-aq','--filter',f'label=forge.run={self.run_id}'],capture_output=True,text=True,timeout=10)
        ids=result.stdout.split()
        if ids:subprocess.run(['docker','rm','-f',*ids],capture_output=True,timeout=20,check=True)

    def execute(self, workspace: Path, command: str, cancelled=lambda:False) -> dict:
        if not self.readiness(self.policy['image'])['ready']:raise ValueError('Approved Docker sandbox is unavailable')
        argv=self.policy['commands'][command];name='forge-'+uuid.uuid4().hex
        is_test=command in {self.policy['test_command'],self.policy.get('verify_command',self.policy['test_command'])}
        report_path=contained(workspace,self.policy['report_path']) if is_test and self.policy['test_format']=='junit' else None
        if report_path and report_path.exists():raise ValueError('JUnit report must not preexist the command')
        # Only the disposable workspace is mounted. Credentials/provider calls stay in the host.
        uid=os.getuid() if hasattr(os,'getuid') and os.getuid() else 65534
        gid=os.getgid() if hasattr(os,'getgid') and os.getuid() else 65534
        args=['docker','run','--name',name,'--label',f'forge.run={self.run_id}','--rm','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--memory','512m','--cpus','1','--user',f'{uid}:{gid}','--tmpfs','/tmp:rw,nosuid,nodev,size=64m','--mount',f'type=bind,src={workspace},dst=/workspace','--workdir','/workspace','--env','PYTHONDONTWRITEBYTECODE=1','--env','CI=1',self.policy['image'],*argv]
        started=time.monotonic()
        with tempfile.TemporaryFile() as output:
            process=subprocess.Popen(args,stdout=output,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
            reason=None
            try:
                while process.poll() is None:
                    if cancelled():reason='cancelled'
                    elif time.monotonic()-started>self.policy['command_timeout']:reason='timeout'
                    elif output.tell()>self.policy['max_output_bytes']:reason='output limit'
                    if reason:
                        break
                    time.sleep(.05)
                if reason:
                    subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=15)
                    process.terminate()
                try:exit_code=process.wait(timeout=15)
                except subprocess.TimeoutExpired:process.kill();exit_code=process.wait()
            finally:
                if process.poll() is None:
                    # Includes SIGINT/SIGTERM and exceptions from the cancellation probe.
                    try:subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=15)
                    finally:
                        process.kill();process.wait(timeout=15)
            output.seek(0);data=output.read(self.policy['max_output_bytes']+1)
        stop_error=f'Sandbox command stopped: {reason or "output limit"}' if reason or len(data)>self.policy['max_output_bytes'] else None
        text=data[:self.policy['max_output_bytes']].decode('utf-8','replace')
        summary=None;test_error=None
        try:
            if is_test and not stop_error:
                report=read_bytes(workspace,self.policy['report_path']) if report_path else None
                summary=test_summary(text,self.policy['test_format'],report)
                if (exit_code==0 and (summary['failed'] or summary['errors'])) or (exit_code!=0 and not (summary['failed'] or summary['errors'])):
                    raise ValueError('Command exit contradicts executed test results')
        except (ValueError,OSError,ET.ParseError) as exc:
            summary=None;test_error=str(exc)[:1000]
        finally:
            if report_path:
                # The command may have replaced a report ancestor with a link.
                try:contained(workspace,self.policy['report_path']).unlink(missing_ok=True)
                except (ValueError,OSError):
                    summary=None;test_error='Unsafe or unremovable JUnit report'
        result={'argv':argv,'exit_code':exit_code,'output':text,'tests':summary,'wall_time_ms':int((time.monotonic()-started)*1000)}
        if test_error:result['test_error']=test_error
        if stop_error:result['stop_error']=stop_error
        return result
