import webview
import threading
import uvicorn
import time
from app import app

def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="error")

if __name__ == '__main__':
    # FastAPIサーバーをバックグラウンドで起動
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    
    # サーバー起動を少し待つ
    time.sleep(1)
    
    # pywebviewでデスクトップアプリとして表示
    webview.create_window(
        title='TaskMining Dashboard', 
        url='http://127.0.0.1:8080/dashboard',
        width=1400,
        height=900
    )
    webview.start()
