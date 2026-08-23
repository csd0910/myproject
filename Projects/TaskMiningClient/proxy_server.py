import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.request
import urllib.error
import os
from google.oauth2 import service_account
import google.auth.transport.requests

SERVER_URL = "https://task-mining-server-1097969102143.asia-northeast1.run.app"
KEY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "client-key.json")
PROXY_PORT = 18080

_cached_token = None
_token_expiry = 0

def get_id_token():
    global _cached_token, _token_expiry
    import time
    
    # トークンの有効期限が5分以上残っていればキャッシュを返す
    if _cached_token and time.time() < _token_expiry - 300:
        return _cached_token
        
    try:
        credentials = service_account.IDTokenCredentials.from_service_account_file(
            KEY_PATH, target_audience=SERVER_URL
        )
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        
        _cached_token = credentials.token
        # credentials.expiry が datetime オブジェクトとして返る
        if hasattr(credentials, 'expiry') and credentials.expiry:
            _token_expiry = credentials.expiry.timestamp()
        else:
            # 取得できない場合はデフォルトで50分間キャッシュ
            _token_expiry = time.time() + 3000
            
        return _cached_token
    except Exception as e:
        print(f"Proxy auth error: {e}")
        return None

class ProxyHTTPRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # ログ出力を抑制

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type, Accept")
        self.end_headers()
        
    def do_GET(self):
        self.proxy_request('GET')
        
    def do_POST(self):
        self.proxy_request('POST')
        
    def proxy_request(self, method):
        url = SERVER_URL + self.path
        req = urllib.request.Request(url, method=method)
        
        # クライアントからのヘッダーをコピー（HostとAuthorizationは除外）
        for key, value in self.headers.items():
            if key.lower() not in ('host', 'authorization'):
                req.add_header(key, value)
                
        # Google IAM認証用のデジタル鍵を注入
        token = get_id_token()
        if token:
            req.add_header('Authorization', f'Bearer {token}')
            
        # POSTボディの読み込み
        if 'Content-Length' in self.headers:
            body = self.rfile.read(int(self.headers['Content-Length']))
            req.data = body
            
        try:
            with urllib.request.urlopen(req) as response:
                self.send_response(response.status)
                self.send_header('Access-Control-Allow-Origin', '*')
                for key, value in response.headers.items():
                    if key.lower() not in ('transfer-encoding', 'connection', 'access-control-allow-origin'):
                        self.send_header(key, value)
                self.end_headers()
                
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header('Access-Control-Allow-Origin', '*')
            for key, value in e.headers.items():
                if key.lower() not in ('transfer-encoding', 'connection', 'access-control-allow-origin'):
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(e.read())
            
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Proxy internal error: {e}".encode('utf-8'))

def start_proxy_server():
    server = HTTPServer(('127.0.0.1', PROXY_PORT), ProxyHTTPRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[Proxy] Internal proxy started on port {PROXY_PORT}")
    return PROXY_PORT
