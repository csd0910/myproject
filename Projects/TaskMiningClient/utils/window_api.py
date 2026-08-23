import win32gui
import win32process
import psutil
import urllib.parse
import win32com.client

def get_active_window():
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        app_name = proc.name().lower()
        
        # エクスプローラーの場合はフルパスを取得する
        if app_name == "explorer.exe":
            try:
                shell = win32com.client.Dispatch("Shell.Application")
                for window in shell.Windows():
                    if int(window.HWND) == hwnd:
                        url = window.LocationURL
                        if url and url.startswith("file:///"):
                            # file:///C:/path などを通常のパスに変換
                            path = urllib.parse.unquote(url[8:])
                            path = path.replace("/", "\\")
                            if title:
                                title = f"{title} ({path})"
                            else:
                                title = path
                        break
            except Exception:
                pass
                
        return proc.name(), title
    except Exception:
        return "Unknown", "Unknown"
