import time
import threading
import pythoncom
import win32com.client
from storage.db_client import enqueue_data
from utils.window_api import get_active_window

stop_event = threading.Event()

class ExcelEventListener:
    log_callback = None
    
    @classmethod
    def log(cls, event_type, target_name, metadata):
        payload = {
            "type": "micro_event",
            "event": "EXCEL_COM_EVENT",
            "app_name": "Excel (COM Hook)",
            "file_name": target_name,
            "operation_type": event_type,
            "snippet": metadata,
            "manual_typing_count": 0,
            "click_count": 0,
            "scroll_count": 0,
            "mouse_distance": 0,
            "window_switch_count": 0,
            "duration_seconds": 0,
            "timestamp": time.time()
        }
        enqueue_data(payload)
        if cls.log_callback:
            cls.log_callback(payload)

    def OnWorkbookOpen(self, Wb):
        self.log("WorkbookOpen", Wb.Name, "")

    def OnWorkbookBeforeSave(self, Wb, SaveAsUI, Cancel):
        self.log("WorkbookSave", Wb.Name, "")

    def OnSheetChange(self, Sh, Target):
        if not hasattr(self, 'last_change_time'):
            self.last_change_time = 0
            
        current_time = time.time()
        # デバウンス処理
        if current_time - self.last_change_time < 0.1:
            return  
            
        self.last_change_time = current_time

        try:
            try:
                sheet_name = Sh.Name
            except Exception:
                sheet_name = "Unknown"
                
            try:
                address = Target.Address
            except Exception:
                address = "Unknown"
                
            try:
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
                
            self.log("SheetChange", Wb.Name if hasattr(Wb, 'Name') else "Excel", meta)
        except Exception as e:
            pass

def excel_com_thread(log_callback=None):
    pythoncom.CoInitialize()
    ExcelEventListener.log_callback = log_callback
    excel_hooked = False
    
    while not stop_event.is_set():
        if not excel_hooked:
            app_name, _ = get_active_window()
            if "excel" in app_name.lower():
                try:
                    excel_app = win32com.client.GetActiveObject("Excel.Application")
                    excel_events = win32com.client.WithEvents(excel_app, ExcelEventListener)
                    excel_hooked = True
                    print("【Excelロガー】アタッチ成功")
                except Exception:
                    pass
        
        if excel_hooked:
            try:
                pythoncom.PumpWaitingMessages()
            except Exception:
                # Excel crashed or closed
                excel_hooked = False
            time.sleep(0.01)
        else:
            time.sleep(1)
            
    pythoncom.CoUninitialize()

def start_excel_tracking(log_callback=None):
    t = threading.Thread(target=excel_com_thread, args=(log_callback,), daemon=True)
    t.start()
