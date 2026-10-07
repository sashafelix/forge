"""Four HTTP protocols behind one governed action interface. No provider-specific model names."""
from __future__ import annotations
import json
import os
from urllib import request, error
from .store import canonical

ACTION_SCHEMA={'type':'object','additionalProperties':False,'required':['kind'],'properties':{
    'kind':{'type':'string','enum':['list','read','search','write','command','submit']},
    'path':{'type':'string'},'text':{'type':'string'},'command':{'type':'string'},'document':{'type':'object'}}}
TOOL={'name':'forge_action','description':'Request a bounded host action or submit the current stage artifact. This never advances the stage or grants permission.','parameters':ACTION_SCHEMA}

class Unavailable(InterruptedError):pass
class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Provider redirects are disabled')

def fetch(url: str, payload: dict, headers: dict, timeout: float) -> dict:
    req=request.Request(url,data=canonical(payload).encode(),headers={'Content-Type':'application/json',**headers},method='POST')
    try:
        with request.build_opener(NoRedirect).open(req,timeout=timeout) as response:
            data=response.read(2*1024*1024+1)
    except error.HTTPError as exc:
        # Never persist request headers or arbitrary error bodies containing credentials.
        if exc.code in (408,429) or exc.code>=500:raise Unavailable(f'Provider temporarily unavailable: HTTP {exc.code}') from None
        raise ValueError(f'Provider rejected the request: HTTP {exc.code}') from None
    except (error.URLError,TimeoutError):raise Unavailable('Provider connection failed or timed out') from None
    if len(data)>2*1024*1024:raise ValueError('Provider output exceeds the host limit')
    value=json.loads(data)
    if not isinstance(value,dict):raise ValueError('Provider response must be an object')
    return value

class HttpSession:
    def __init__(self, provider: dict, model: dict, system: str, prompt: str, transport=fetch):
        self.provider=provider;self.model=model;self.transport=transport;self.system=system
        self.messages=[{'role':'user','content':prompt}]
        self.responses_input=[{'role':'system','content':system},{'role':'user','content':prompt}]
        self.gemini_contents=[{'role':'user','parts':[{'text':prompt}]}]
        self.calls=[];self.usage=None

    def next(self) -> list[dict]:
        p,m=self.provider,self.model;protocol=p['protocol'];headers={}
        if p['auth']['mode']!='none':
            ref=p['auth']['credentialRef']
            if not isinstance(ref,str) or not ref.startswith('env:'):raise ValueError('The HTTP host requires an operator-supplied env credential reference')
            secret=os.environ.get(ref[4:])
            if not secret:raise Unavailable('The configured provider credential is unavailable')
            headers[p['auth']['header']]=('Bearer ' if p['auth']['mode']=='bearer' else '')+secret
        base=p['baseUrl'].rstrip('/');max_tokens=m['maxOutputTokens']
        if protocol=='openai-chat':
            endpoint=base+'/chat/completions';payload={'model':m['model'],'messages':[{'role':'system','content':self.system},*self.messages],'tools':[{'type':'function','function':{**TOOL,'strict':False}}],'max_completion_tokens':max_tokens}
        elif protocol=='openai-responses':
            endpoint=base+'/responses';payload={'model':m['model'],'input':self.responses_input,'tools':[{'type':'function',**TOOL,'strict':False}],'max_output_tokens':max_tokens,'store':False}
        elif protocol=='anthropic-messages':
            endpoint=base+'/messages';headers['anthropic-version']='2023-06-01';payload={'model':m['model'],'system':self.system,'messages':self.messages,'tools':[{'name':TOOL['name'],'description':TOOL['description'],'input_schema':ACTION_SCHEMA}],'max_tokens':max_tokens}
        elif protocol=='gemini':
            from urllib.parse import quote
            endpoint=base+'/models/'+quote(m['model'],safe='')+':generateContent';payload={'systemInstruction':{'parts':[{'text':self.system}]},'contents':self.gemini_contents,'tools':[{'functionDeclarations':[{'name':TOOL['name'],'description':TOOL['description'],'parametersJsonSchema':ACTION_SCHEMA}]}],'generationConfig':{'maxOutputTokens':max_tokens}}
        else:raise ValueError('Unsupported HTTP protocol')
        if m.get('temperature') is not None:
            if protocol=='gemini':payload['generationConfig']['temperature']=m['temperature']
            else:payload['temperature']=m['temperature']
        effort=m.get('reasoningEffort')
        if effort is not None:
            if protocol=='openai-chat':payload['reasoning_effort']=effort
            elif protocol=='openai-responses':payload['reasoning']={'effort':effort}
            elif protocol=='anthropic-messages':payload['output_config']={'effort':effort}
            else:payload['generationConfig']['thinkingConfig']={'thinkingLevel':effort.upper()}
        result=self.transport(endpoint,payload,headers,p['timeoutMs']/1000)
        self.usage=result.get('usage') or result.get('usageMetadata')
        calls=[]
        if protocol=='openai-chat':
            message=result['choices'][0]['message'];self.messages.append(message)
            for raw in message.get('tool_calls',[]):calls.append({'id':raw['id'],'name':raw['function']['name'],'arguments':json.loads(raw['function']['arguments'])})
        elif protocol=='openai-responses':
            self.responses_input.extend(result.get('output',[]))
            for raw in result.get('output',[]):
                if raw.get('type')=='function_call':calls.append({'id':raw['call_id'],'name':raw['name'],'arguments':json.loads(raw['arguments'])})
        elif protocol=='anthropic-messages':
            self.messages.append({'role':'assistant','content':result.get('content',[])})
            for raw in result.get('content',[]):
                if raw.get('type')=='tool_use':calls.append({'id':raw['id'],'name':raw['name'],'arguments':raw['input']})
        else:
            content=result['candidates'][0]['content'];self.gemini_contents.append(content)
            for index,part in enumerate(content.get('parts',[])):
                if 'functionCall' in part:
                    raw=part['functionCall'];calls.append({'id':raw.get('id',str(index)),'name':raw['name'],'arguments':raw['args'],'gemini_id':raw.get('id')})
        if not 1<=len(calls)<=8 or any(c['name']!='forge_action' or not isinstance(c['arguments'],dict) for c in calls):raise ValueError('Expected bounded forge_action calls, not an unstructured completion')
        self.calls=calls
        return calls

    def reply(self, results: list[tuple[dict,dict]]):
        protocol=self.provider['protocol']
        if protocol=='openai-chat':
            self.messages.extend({'role':'tool','tool_call_id':call['id'],'content':canonical(result)} for call,result in results)
        elif protocol=='openai-responses':
            self.responses_input.extend({'type':'function_call_output','call_id':call['id'],'output':canonical(result)} for call,result in results)
        elif protocol=='anthropic-messages':
            self.messages.append({'role':'user','content':[{'type':'tool_result','tool_use_id':call['id'],'content':canonical(result)} for call,result in results]})
        else:
            self.gemini_contents.append({'role':'user','parts':[{'functionResponse':{'name':'forge_action','response':result,
                **({'id':call['gemini_id']} if call.get('gemini_id') else {})}} for call,result in results]})

    def estimated_input_tokens(self):
        protocol=self.provider['protocol']
        history=self.responses_input if protocol=='openai-responses' else [self.system,self.gemini_contents] if protocol=='gemini' else [self.system,self.messages]
        return (len(canonical(history))+3)//4
