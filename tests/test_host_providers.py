"""Protocol conformance, including preserved response state and tool-result IDs."""
import copy
import json
import os
import unittest
from host_fixtures import inputs
from forge_host.providers import HttpSession, Unavailable, NoRedirect


class ProviderTests(unittest.TestCase):
    def test_four_protocol_roundtrips_use_operator_model_names(self):
        for protocol in ('openai-chat', 'openai-responses', 'anthropic-messages', 'gemini'):
            with self.subTest(protocol=protocol):
                provider = copy.deepcopy(inputs()[0]['providers'][0])
                provider.update(protocol=protocol, baseUrl='https://provider.example.test/v1')
                model = dict(inputs()[0]['profile']['models'][0], model='operator-model', reasoningEffort='high')
                action = {'kind': 'read', 'path': 'fixture.py'}
                if protocol == 'openai-chat':
                    response = {'choices': [{'message': {'role': 'assistant', 'content': None,
                        'tool_calls': [{'id': 'call-1', 'type': 'function', 'function': {'name': 'forge_action', 'arguments': json.dumps(action)}}]}}]}
                elif protocol == 'openai-responses':
                    response = {'output': [{'type': 'function_call', 'call_id': 'call-1', 'name': 'forge_action', 'arguments': json.dumps(action)}]}
                elif protocol == 'anthropic-messages':
                    response = {'content': [{'type': 'tool_use', 'id': 'call-1', 'name': 'forge_action', 'input': action}]}
                else:
                    response = {'candidates': [{'content': {'role': 'model', 'parts': [{'thoughtSignature': 'opaque-state',
                        'functionCall': {'id':'gemini-call-1','name': 'forge_action', 'args': action}}]}}]}
                requests = []
                def transport(url, payload, headers, timeout):
                    requests.append((url, copy.deepcopy(payload), headers, timeout))
                    return copy.deepcopy(response)
                session = HttpSession(provider, model, 'host policy', 'task', transport)
                call = session.next()[0]
                session.reply([(call, {'path': 'fixture.py', 'text': 'source'})])
                session.next()
                self.assertEqual(call['arguments'], action)
                self.assertIn('operator-model', json.dumps(requests[0][:2]))
                second = json.dumps(requests[1][1])
                self.assertIn('source', second)
                self.assertIn('opaque-state' if protocol == 'gemini' else 'call-1', second)
                if protocol == 'gemini':self.assertIn('gemini-call-1',second)
                if protocol == 'openai-responses':self.assertFalse(requests[0][1]['tools'][0]['strict'])
                self.assertGreater(session.estimated_input_tokens(), 0)

    def test_no_tools_and_unknown_function_fail_closed(self):
        provider, model = inputs()[0]['providers'][0], inputs()[0]['profile']['models'][0]
        for message in ({'role': 'assistant', 'content': 'I declare PASS'},
                        {'tool_calls': [{'id': 'x', 'function': {'name': 'publish', 'arguments': '{}'}}]}):
            session = HttpSession(provider, model, 'policy', 'task',
                                  lambda *args: {'choices': [{'message': message}]})
            with self.assertRaisesRegex(ValueError, 'forge_action'): session.next()

    def test_missing_credential_and_redirect_are_rejected(self):
        provider = copy.deepcopy(inputs()[0]['providers'][0])
        provider['auth'] = {'mode': 'bearer', 'header': 'Authorization', 'credentialRef': 'env:FORGE_ABSENT_TEST_KEY'}
        os.environ.pop('FORGE_ABSENT_TEST_KEY', None)
        with self.assertRaises(Unavailable):
            HttpSession(provider, inputs()[0]['profile']['models'][0], 'p', 't').next()
        with self.assertRaises(ValueError): NoRedirect().redirect_request(None, None, None, None, None, None)


if __name__ == '__main__': unittest.main()
