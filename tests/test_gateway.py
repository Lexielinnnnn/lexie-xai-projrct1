import unittest
from unittest.mock import patch
import io
import start
class GatewayTests(unittest.TestCase):
 def config(self):return {'base':'https://example.com/v1','key':'fake-secret','model':'chat','enabled':True,'limit':2,'params':{'max_tokens':512}}
 def body(self):return {'model':'chat','messages':[{'role':'system','content':'fictional'},{'role':'user','content':'email'}]}
 def test_disabled_and_validation_never_call_provider(self):
  g=start.Gateway(self.config());g.models=['chat'];g.config['enabled']=False
  with patch.object(g,'upstream') as call:
   with self.assertRaises(start.UserError):g.chat(self.body())
   call.assert_not_called()
 def test_limit_params_and_model_validation(self):
  g=start.Gateway(self.config());g.models=['chat']
  with patch.object(g,'upstream',return_value={'choices':[{'message':{'content':'answer'},'finish_reason':'stop'}]}) as call:
   self.assertEqual(g.chat(self.body())['output'],'answer');g.chat(self.body())
   with self.assertRaises(start.UserError):g.chat(self.body())
   self.assertEqual(call.call_count,2);self.assertNotIn('temperature',call.call_args.args[1])
   self.assertEqual(call.call_args.args[1]['max_tokens'],512)
 def test_model_list_no_generation(self):
  g=start.Gateway(self.config())
  with patch.object(g,'upstream',return_value={'data':[{'id':'chat'}]}) as call:
   self.assertEqual(g.list_models(),{'models':['chat']});call.assert_called_once_with('/models');self.assertEqual(g.calls,0)
 def test_failures_consume_attempt_no_retry(self):
  g=start.Gateway(self.config());g.models=['chat']
  with patch.object(g,'upstream',side_effect=start.UserError('quota')) as call:
   with self.assertRaises(start.UserError):g.chat(self.body())
   self.assertEqual(call.call_count,1);self.assertEqual(g.calls,1)
 def test_env_default_disabled(self):self.assertFalse(start.read_config()['enabled'])
 def test_static_assets_exclude_config(self):self.assertNotIn('/config.env',start.load_assets())
class Socket:
 def __init__(self,request):self.request=io.BytesIO(request);self.output=bytearray()
 def makefile(self,*args):return self.request
 def sendall(self,data):self.output.extend(data)
class HTTPTests(unittest.TestCase):
 def request(self,path,headers='',method='GET',body=''):
  g=start.Gateway(GatewayTests().config());socket=Socket(f'{method} {path} HTTP/1.0\r\nHost: localhost:8000\r\n{headers}Content-Length: {len(body)}\r\n\r\n{body}'.encode());server=type('S',(),{'server_port':8000})();start.handler_for(start.load_assets(),g,'token')(socket,('127.0.0.1',1),server);return bytes(socket.output)
 def test_config_has_no_key(self):
  response=self.request('/api/config');self.assertIn(b'200 OK',response);self.assertNotIn(b'fake-secret',response)
 def test_file_not_served(self):self.assertIn(b'404',self.request('/config.env'))
 def test_foreign_origin_rejected(self):self.assertIn(b'403',self.request('/api/chat','Origin: https://evil.example\r\nX-Local-Token: token\r\n','POST','{}'))
 def test_missing_token_rejected(self):self.assertIn(b'403',self.request('/api/models','','POST','{}'))
