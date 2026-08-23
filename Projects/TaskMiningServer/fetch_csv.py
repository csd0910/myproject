import os
import requests
import google.auth.transport.requests
from google.oauth2 import service_account

def fetch_csv():
    url = "https://task-mining-server-1097969102143.asia-northeast1.run.app/api/dashboard/export_csv?user_id=ALL"
    key_path = "client-key.json"
    
    credentials = service_account.IDTokenCredentials.from_service_account_file(
        key_path, target_audience="https://task-mining-server-1097969102143.asia-northeast1.run.app"
    )
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    
    headers = {
        'Authorization': f'Bearer {credentials.token}',
        'X-Admin-Token': 'Bearer super_secret_admin_token'
    }
    
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        with open("client_logs_latest300_from_server.csv", "wb") as f:
            f.write(resp.content)
        print("Success")
    else:
        print("Failed:", resp.status_code, resp.text)

if __name__ == "__main__":
    fetch_csv()
