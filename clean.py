import urllib.request
import google.auth.transport.requests
import google.oauth2.id_token
import json
import os

audience = "https://task-mining-server-1097969102143.asia-northeast1.run.app"
url = audience + "/api/admin/generate_mock_data"

try:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"c:\Users\フォーレスト026\MyProject\TaskMiningClient\client-key.json"
    auth_req = google.auth.transport.requests.Request()
    token = google.oauth2.id_token.fetch_id_token(auth_req, audience)
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
except Exception as e:
    print(f"Error: {e}")
