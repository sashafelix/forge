"""Transient exact-revision symbol map; direct source files only."""
import ast
import hashlib
from pathlib import Path
from pipeline_support.common import contained, read_bytes

IGNORED={'__pycache__','.pytest_cache','.mypy_cache','.ruff_cache'}

def files(root: Path, max_files: int = 5000) -> dict[str,str]:
    result={};total=0
    for path in sorted(root.rglob('*')):
        rel=path.relative_to(root)
        if path.is_symlink():raise ValueError(f'Symlink in workspace: {rel}')
        if any(p in IGNORED for p in rel.parts):continue
        if '.git' in rel.parts:raise ValueError('Git metadata is forbidden in the disposable workspace')
        if not path.is_file():continue
        if len(result)>=max_files:raise ValueError('Workspace file limit exceeded')
        data=read_bytes(root,rel.as_posix());total+=len(data)
        if total>64*1024*1024:raise ValueError('Workspace byte limit exceeded')
        result[rel.as_posix()]=hashlib.sha256(data).hexdigest()
    return result

def repository_map(root: Path, revision: str, max_files=100, max_bytes=300000) -> dict:
    symbols=[];used=[];size=0
    for name in files(root):
        if len(used)>=max_files:break
        if not name.endswith(('.py','.ts','.tsx','.js','.java','.kt','.go','.rs')):continue
        data=read_bytes(root,name)
        if size+len(data)>max_bytes:continue
        size+=len(data);used.append(name)
        if name.endswith('.py'):
            try:
                tree=ast.parse(data.decode('utf-8'))
                for node in ast.walk(tree):
                    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                        symbols.append({'path':name,'name':node.name,'line':node.lineno,'kind':type(node).__name__})
            except (SyntaxError,UnicodeError):continue
        else:
            import re
            for line_no,line in enumerate(data.decode('utf-8','replace').splitlines(),1):
                match=re.search(r'\b(?:function|class|interface|def|fun|fn|func)\s+([A-Za-z_][A-Za-z0-9_]*)',line)
                if match:symbols.append({'path':name,'name':match[1],'line':line_no,'kind':'declaration'})
    return {'schema_version':'1.0','revision':revision,'authority':'advisory','files':used,'bytes':size,'symbols':symbols[:1000],'limits':['Transient direct-source map; declarations outside the inspection budget may be omitted.']}
