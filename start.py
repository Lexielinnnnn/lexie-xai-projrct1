#!/usr/bin/env python3
"""Loopback-only API proxy; standard-library Python, no dependencies."""
import argparse, hashlib, json, mimetypes, secrets, threading, webbrowser
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent
ASSETS = ('index.html', 'app.js', 'style.css')
class UserError(Exception):
    pass

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def read_config(root=ROOT):
    values = {}
    try:
        for line in (root/'config.env').read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#'): continue
            k, sep, v = line.partition('=')
            if sep: values[k.strip()] = v.strip().strip('\"\'')
    except OSError:
        raise UserError('Missing config.env. Extract the complete ZIP.')
    base = values.get('API_BASE_URL', '').rstrip('/')
    parsed = urlsplit(base)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise UserError('API_BASE_URL must be an HTTPS base URL without credentials, query, or fragment.')
    try:
        limit = None  # Legacy MAX_CALLS settings are ignored.
        output = int(values.get('MAX_OUTPUT_TOKENS','512'))
        if not 32 <= output <= 8192: raise ValueError()
    except ValueError: raise UserError('MAX_OUTPUT_TOKENS must be 32–8192.')
    field = values.get('TOKEN_LIMIT_FIELD','max_tokens')
    if field not in ('max_tokens','max_completion_tokens'): raise UserError('Invalid TOKEN_LIMIT_FIELD.')
    params = {field:output}
    for env, key, high in [('TEMPERATURE','temperature',2),('TOP_P','top_p',1)]:
        if values.get(env):
            try:
                value=float(values[env])
                if not 0 <= value <= high: raise ValueError()
            except ValueError: raise UserError('Invalid '+env)
            params[key]=value
    return {'base':base,'key':values.get('API_KEY',''),'model':values.get('MODEL',''),
            'enabled':values.get('ENABLE_GENERATION','false').lower()=='true','limit':limit,'params':params}

def load_assets(root=ROOT):
    manifest=json.loads((root/'build-manifest.json').read_text())['sha256'];assets={}
    for name in ASSETS:
        data=(root/'dist'/name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=manifest.get(name): raise UserError('Bundled file failed verification: '+name)
        assets['/'+name]=(data, 'text/javascript' if name.endswith('.js') else mimetypes.guess_type(name)[0])
    assets['/']=assets['/index.html'];return assets

class Gateway:
    def __init__(self,config):
        self.config=config;self.models=[];self.calls=0;self.lock=threading.Lock();self.running=threading.Lock()
    def upstream(self,path,payload=None):
        key=self.config['key']
        if not key or key=='PASTE_YOUR_KEY_HERE': raise UserError('Paste your key into config.env, save, and restart start.py.')
        req=Request(self.config['base']+path,data=json.dumps(payload).encode() if payload is not None else None,
                    headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST' if payload is not None else 'GET')
        try:
            with build_opener(NoRedirect).open(req,timeout=90 if payload else 30) as response:
                raw=response.read(2_000_001)
                if len(raw)>2_000_000: raise UserError('Provider response was too large.')
                return json.loads(raw)
        except HTTPError as e:
            messages={400:'Provider rejected the model or parameters. Check TOKEN_LIMIT_FIELD and optional sampling settings.',401:'Key was not accepted. Check config.env.',403:'This key cannot access this resource. Check model permissions.',404:'Endpoint or model not found. Check the base URL and model.',429:'Provider quota or rate limit reached. Wait or check your account budget. No retry was made.'}
            raise UserError(messages.get(e.code,'Provider returned HTTP '+str(e.code)+'. No retry was made.'))
        except (URLError,TimeoutError,OSError): raise UserError('Could not reach the provider. Check your network and any Duke access requirements. No retry was made.')
        except (ValueError,TypeError): raise UserError('Provider returned an invalid response.')
    def list_models(self):
        data=self.upstream('/models')
        self.models=sorted({x['id'] for x in data.get('data',[]) if isinstance(x,dict) and isinstance(x.get('id'),str)})
        return {'models':self.models}
    def chat(self,body):
        if not self.config['enabled']: raise UserError('Generation is disabled. Confirm your budget, set ENABLE_GENERATION=true, and restart.')
        if body.get('model') not in self.models: raise UserError('Select a model from the connected model list.')
        messages=body.get('messages')
        if not isinstance(messages,list) or len(messages)!=2: raise UserError('Expected one system message and one user message.')
        for message,role in zip(messages,['system','user']):
            if not isinstance(message,dict) or message.get('role')!=role or not isinstance(message.get('content'),str) or len(message['content'])>6000: raise UserError('Invalid message.')
        if not self.running.acquire(blocking=False): raise UserError('A previous API call is still running. Please wait before trying again.')
        try:
            with self.lock:
                self.calls+=1
            payload={'model':body['model'],'messages':messages,'stream':False,**self.config['params']}
            data=self.upstream('/chat/completions',payload)
            try:
                choice=data['choices'][0];output=choice['message'].get('content');reason=choice.get('finish_reason')
                if not isinstance(output,str): raise ValueError()
            except (KeyError,IndexError,TypeError,ValueError): raise UserError('No text answer returned. This model may not support chat completions.')
            return {'output':output,'finishReason':reason,'model':body['model'],'usage':data.get('usage'),
                    'parameters':self.config['params'],'callsUsed':self.calls,'callLimit':self.config['limit']}
        finally: self.running.release()

def handler_for(assets,gateway,token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def local(self):
            return self.headers.get('Host') in (f'localhost:{self.server.server_port}',f'127.0.0.1:{self.server.server_port}')
        def send(self,status,data,mime='application/json'):
            raw=json.dumps(data).encode() if mime=='application/json' else data
            self.send_response(status);self.send_header('Content-Type',mime+'; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers()
            if self.command!='HEAD':
                try:self.wfile.write(raw)
                except (BrokenPipeError,ConnectionResetError):pass
        def do_HEAD(self):self.do_GET()
        def do_GET(self):
            if not self.local():return self.send(403,{'error':'Local access only.'})
            path=urlsplit(self.path).path
            if path=='/api/config':return self.send(200,{'token':token,'model':gateway.config['model'],'generationEnabled':gateway.config['enabled']})
            if path in assets:
                data,mime=assets[path];return self.send(200,data,mime)
            self.send(404,{'error':'Not found.'})
        def do_POST(self):
            origin=self.headers.get('Origin')
            allowed=(f'http://localhost:{self.server.server_port}',f'http://127.0.0.1:{self.server.server_port}')
            if not self.local() or (origin and origin not in allowed) or not secrets.compare_digest(self.headers.get('X-Local-Token',''),token):return self.send(403,{'error':'Invalid local request. Refresh this page.'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=24000:raise UserError('Request body too large or empty.')
                body=json.loads(self.rfile.read(size))
                if not isinstance(body,dict):raise UserError('Invalid request.')
                path=urlsplit(self.path).path
                if path=='/api/models':data=gateway.list_models()
                elif path=='/api/chat':data=gateway.chat(body)
                else:return self.send(404,{'error':'Not found.'})
                self.send(200,data)
            except (UserError,ValueError) as e:self.send(400,{'error':str(e) if isinstance(e,UserError) else 'Invalid request.'})
            except Exception:self.send(500,{'error':'Unexpected server error. No automatic retry was made.'})
    return Handler

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
    try:assets=load_assets();config=read_config()
    except (UserError,OSError,ValueError,KeyError) as e:raise SystemExit('Cannot start: '+str(e))
    print('Bundled files and configuration format verified. No API request has been sent.')
    if args.check:raise SystemExit(0)
    gateway=Gateway(config);server=None
    for port in range(8000,8011):
        try:server=ThreadingHTTPServer(('127.0.0.1',port),handler_for(assets,gateway,secrets.token_urlsafe(32)));break
        except OSError:pass
    if server is None:raise SystemExit('Ports 8000–8010 unavailable. Stop the previous server first.')
    url=f'http://localhost:{server.server_port}'
    print(f'Hidden Instructions API: {url}\nGeneration enabled: {config["enabled"]}; no local request cap\nKeep this terminal open. Ctrl+C to stop. Keys are never served to the browser.',flush=True)
    if not args.no_browser:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:print('\nStopped.')
    finally:server.server_close()
