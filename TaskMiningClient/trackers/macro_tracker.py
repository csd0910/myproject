import time
import psutil
from utils.window_api import get_active_window
from storage.db_client import enqueue_data
from config import settings

def get_browser_tab_count():
    try:
        # Heuristic: count chrome/msedge processes as a proxy for browser activity
        count = 0
        for p in psutil.process_iter(attrs=['name']):
            if p.info['name'] in ['chrome.exe', 'msedge.exe', 'firefox.exe']:
                count += 1
        return max(1, count // 4) if count > 0 else 0
    except Exception:
        return 0

def start_macro_tracking(log_callback=None):
    # 非常に軽量に、アクティブウィンドウ名やシステム負荷をポーリングしてDBキューに送る
    while True:
        try:
            app_name, title = get_active_window()
            
            # CPU & Memory tracking
            cpu_usage = psutil.cpu_percent(interval=None)
            mem_info = psutil.virtual_memory()
            memory_usage_mb = mem_info.used / (1024 * 1024)
            browser_tabs = get_browser_tab_count() if app_name.lower() in ['chrome.exe', 'msedge.exe', 'firefox.exe'] else 0
            
            payload = {
                "type": "macro",
                "app_name": app_name,
                "file_name": title,
                "duration_seconds": settings.MACRO_INTERVAL_SEC,
                "cpu_usage_percent": cpu_usage,
                "memory_usage_mb": memory_usage_mb,
                "browser_tab_count": browser_tabs,
                "timestamp": time.time()
            }
            enqueue_data(payload)
            
            if log_callback:
                log_callback(payload)
        except Exception:
            pass
            
        time.sleep(settings.MACRO_INTERVAL_SEC)
