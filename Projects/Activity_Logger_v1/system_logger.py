import time
import datetime
import csv
import os
import threading
import queue
import psutil
import pyperclip
import win32gui
import win32process
import pythoncom
import win32com.client

# ==========================================
# グローバル設定
# ==========================================
stop_event = threading.Event()
log_queue = queue.Queue()

# ==========================================
# アクティブウィンドウ情報の取得
# ==========================================
def get_active_window_info():
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        
        proc = psutil.Process(pid)
        app_name = proc.name()
        return app_name, title
    except Exception:
        return "Unknown", "Unknown"

# ==========================================
# ログ書き込み（キューへの投入：非同期用）
# ==========================================
def log_system_event(base_dir, app_name, event_type, target, metadata):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # すぐにファイルを開かず、インメモリのキューに放り込んでExcelに即座に処理を返す
    log_queue.put((app_name, event_type, target, metadata, timestamp, base_dir))

# ==========================================
# バックグラウンド書き込みスレッド
# ==========================================
def log_writer_thread():
    # キューに溜まったログを順次ファイルに書き出す（ディスクI/Oによる遅延を吸収）
    while not stop_event.is_set() or not log_queue.empty():
        try:
            item = log_queue.get(timeout=1.0)
        except queue.Empty:
            continue
            
        app_name, event_type, target, metadata, timestamp, base_dir = item
        
        target_date = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%Y%m%d") if timestamp else datetime.datetime.now().strftime("%Y%m%d")
        log_dir = base_dir if base_dir else os.path.join(os.path.dirname(__file__), "activity_logs")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"system_log_{target_date}.csv")
        file_exists = os.path.exists(log_file)
        
        try:
            with open(log_file, "a", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Timestamp", "ActiveApp", "EventType", "TargetName", "Metadata"])
                writer.writerow([timestamp, app_name, event_type, target, metadata])
        except Exception:
            pass
        finally:
            log_queue.task_done()

# ==========================================
# Excelイベント傍受用クラス (win32com)
# ==========================================
class ExcelEventListener:
    base_dir = ""
    
    @classmethod
    def log(cls, event_type, target, metadata):
        log_system_event(cls.base_dir, "excel.exe", event_type, target, metadata)

    def OnWorkbookOpen(self, Wb):
        self.log("WorkbookOpen", Wb.Name, "")

    def OnWorkbookBeforeSave(self, Wb, SaveAsUI, Cancel):
        self.log("WorkbookSave", Wb.Name, "")

    def OnSheetChange(self, Sh, Target):
        # 【重要】マクロによる連続書き換え検知（デバウンス処理）
        # 0.1秒以内に発生した連続変更は間引き、Excelの動作を重くしない
        if not hasattr(self, 'last_change_time'):
            self.last_change_time = 0
            
        current_time = time.time()
        # 連続書き換えによるフリーズを完全に防ぐため、1秒以内のイベントは無視
        if current_time - self.last_change_time < 1.0:
            self.last_change_time = current_time
            return
            
        self.last_change_time = current_time

        try:
            # Target（変更されたセル範囲）のプロパティへのアクセスはCOM通信が発生し激重になるため、あえてアクセスしない
            wb_name = Sh.Parent.Name
            sheet_name = Sh.Name
            self.log("SheetChange (Paste/Edit)", wb_name, f"Sheet:{sheet_name}")
        except Exception:
            pass

# ==========================================
# メインの監視スレッド
# ==========================================
def main(base_dir=None):
    print("【システムロガー】起動しました。（非同期・軽量版）")
    
    ExcelEventListener.base_dir = base_dir
    
    # 書き込み専用スレッドの起動
    writer_thread = threading.Thread(target=log_writer_thread, daemon=True)
    writer_thread.start()
    
    # COM初期化
    pythoncom.CoInitialize()
    
    last_clipboard = ""
    last_active_app = ""
    source_app_of_clipboard = ""
    excel_hooked = False
    excel_events = None
    
    while not stop_event.is_set():
        try:
            # 1. アクティブアプリとAI/Webメール利用の検知
            app_name, title = get_active_window_info()
            browser_names = ["chrome.exe", "msedge.exe", "firefox.exe"]
            ai_keywords = ["ChatGPT", "Claude", "Gemini", "Copilot", "Perplexity"]
            mail_keywords = ["Gmail", "Outlook", "Yahoo"]
            
            if app_name.lower() in browser_names:
                for keyword in ai_keywords:
                    if keyword.lower() in title.lower():
                        app_name = f"AI({keyword})"
                        break
                for keyword in mail_keywords:
                    if keyword.lower() in title.lower():
                        app_name = f"WebMail({keyword})"
                        break

            # 2. アプリ切り替えによる「転記（ペースト可能性）」の検知
            if app_name != last_active_app and last_active_app != "":
                if source_app_of_clipboard and source_app_of_clipboard != app_name and last_clipboard:
                    snippet = last_clipboard[:50].replace('\n', ' ').replace('\r', ' ')
                    log_system_event(base_dir, app_name, "PotentialTransfer (Paste)", title, f"Source: {source_app_of_clipboard}, Data:[{snippet}...]")
            
            last_active_app = app_name

            # 3. クリップボードの監視（コピー元アプリの記憶）
            current_clipboard = pyperclip.paste()
            if current_clipboard != last_clipboard:
                last_clipboard = current_clipboard
                source_app_of_clipboard = app_name
                if current_clipboard:
                    size = len(current_clipboard)
                    snippet = current_clipboard[:100].replace('\n', ' ').replace('\r', ' ')
                    log_system_event(base_dir, app_name, "Copy", title, f"Size:{size} chars, Data:[{snippet}...]")

            # 2. Excelプロセスへのアタッチ
            if not excel_hooked:
                app_name, _ = get_active_window_info()
                if "excel" in app_name.lower():
                    try:
                        excel_app = win32com.client.GetActiveObject("Excel.Application")
                        excel_events = win32com.client.WithEvents(excel_app, ExcelEventListener)
                        excel_hooked = True
                        print("【システムロガー】Excelプロセスへのアタッチに成功しました。")
                    except Exception:
                        pass
        
        except Exception:
            pass
            
        pythoncom.PumpWaitingMessages()
        stop_event.wait(1)
        
    pythoncom.CoUninitialize()
    
    # スレッド停止後、残りのキューを書き切るのを待つ
    log_queue.join()
    print("【システムロガー】終了しました。")

if __name__ == "__main__":
    main()
