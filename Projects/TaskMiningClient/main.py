import threading
import customtkinter as ctk
import time
import json
import os
import uuid
import socket
import webbrowser
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item

from trackers.macro_tracker import start_macro_tracking
from trackers.micro_tracker import start_micro_tracking
from trackers.excel_tracker import start_excel_tracking

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

CONFIG_FILE = "config.json"

DEPARTMENTS = {
    "業務改革室": ["-"],
    "Eコマース部": ["Eコマース課", "-"],
    "マーケティング部": ["マーケティング課", "-"],
    "商品部": ["商品課", "在庫管理課", "-"],
    "営業部": ["営業課", "営業運営課", "-"],
    "カスタマーソリューション部": ["カスタマーサポート課", "サービス課", "-"],
    "物流統括部": ["-"],
    "物流部": ["ロジスティクス運営課", "-"],
    "配送部": ["配送サービス課", "-"],
    "管理統括部": ["-"],
    "管理本部": ["-"],
    "管理部": ["総務人事課", "財務経理課", "-"],
    "事業管理部": ["-"],
    "システム統括部": ["-"],
    "ITシステム本部": ["-"],
    "システム部": ["システム課", "システム運営課", "-"]
}

class SetupWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ForestTaskMiningSystem - INITIAL SETUP")
        self.geometry("350x450")
        self.resizable(False, False)
        self.configure(fg_color="#0a0a0a")
        
        self.label_title = ctk.CTkLabel(
            self, text="AGENT INITIALIZATION", 
            font=ctk.CTkFont(family="Consolas", size=18, weight="bold"),
            text_color="#00e5ff"
        )
        self.label_title.pack(pady=(30, 20))

        # 部署名
        self.label_dept = ctk.CTkLabel(self, text="DEPARTMENT (部/室)", font=ctk.CTkFont(family="Consolas", size=12), text_color="#cccccc")
        self.label_dept.pack(anchor="w", padx=50)
        
        self.combo_dept = ctk.CTkComboBox(
            self, values=list(DEPARTMENTS.keys()), command=self.update_sections,
            font=ctk.CTkFont(family="Consolas", size=12), fg_color="#1a1a1a", border_color="#00e5ff", text_color="#ffffff"
        )
        self.combo_dept.pack(pady=(0, 15), padx=50, fill="x")

        # 課名
        self.label_section = ctk.CTkLabel(self, text="SECTION (課)", font=ctk.CTkFont(family="Consolas", size=12), text_color="#cccccc")
        self.label_section.pack(anchor="w", padx=50)
        
        self.combo_section = ctk.CTkComboBox(
            self, values=DEPARTMENTS["業務改革室"],
            font=ctk.CTkFont(family="Consolas", size=12), fg_color="#1a1a1a", border_color="#00e5ff", text_color="#ffffff"
        )
        self.combo_section.pack(pady=(0, 15), padx=50, fill="x")

        # 氏名 (任意)
        self.label_name = ctk.CTkLabel(self, text="NAME (氏名・任意)", font=ctk.CTkFont(family="Consolas", size=12), text_color="#cccccc")
        self.label_name.pack(anchor="w", padx=50)
        
        self.entry_name = ctk.CTkEntry(
            self, font=ctk.CTkFont(family="Consolas", size=12), fg_color="#1a1a1a", border_color="#00e5ff", text_color="#ffffff"
        )
        self.entry_name.pack(pady=(0, 20), padx=50, fill="x")

        # 保存ボタン
        self.btn_save = ctk.CTkButton(
            self, text="INITIALIZE", 
            command=self.save_config,
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            fg_color="#00e5ff", text_color="#000000", hover_color="#00b3cc"
        )
        self.btn_save.pack(pady=20)

    def update_sections(self, choice):
        sections = DEPARTMENTS.get(choice, ["-"])
        self.combo_section.configure(values=sections)
        self.combo_section.set(sections[0])

    def save_config(self):
        dept = self.combo_dept.get()
        section = self.combo_section.get()
        name = self.entry_name.get().strip()
        if section == "-":
            section = ""
            
        uid = str(uuid.uuid4())
        
        # UUIDとPCのホスト名を自動取得
        config_data = {
            "uuid": uid,
            "hostname": socket.gethostname(),
            "department": dept,
            "section": section,
            "name": name
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
            
        # サーバーへ登録リクエストを送信
        try:
            import requests
            from google.oauth2 import service_account
            import google.auth.transport.requests
            
            KEY_PATH = os.path.join(os.path.dirname(__file__), "client-key.json")
            url = "https://task-mining-server-1097969102143.asia-northeast1.run.app/api/auth/register_employee"
            
            credentials = service_account.IDTokenCredentials.from_service_account_file(
                KEY_PATH, target_audience="https://task-mining-server-1097969102143.asia-northeast1.run.app"
            )
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {credentials.token}'
            }
            
            payload = {"user_id": uid, "name": name, "department": dept, "section": section}
            requests.post(url, json=payload, headers=headers, timeout=5)
        except Exception as e:
            print(f"Failed to send registration: {e}")
        
        print("[SETUP] 端末の初期設定とUUIDの発行が完了しました。")
        self.destroy()

def create_image():
    # タスクバー用のアイコン画像を生成（Forest Greenのシンプルなアイコン）
    image = Image.new('RGB', (64, 64), color=(0, 0, 0))
    dc = ImageDraw.Draw(image)
    dc.rectangle((16, 16, 48, 48), fill=(34, 139, 34)) 
    return image

def open_dashboard(icon, item):
    import threading
    import launcher_ui
    threading.Thread(target=launcher_ui.launch, daemon=True).start()

def exit_app(icon, item):
    icon.stop()
    os._exit(0)

def main():
    # 内蔵プロキシの起動（クラウドのWebダッシュボードを認証エラーなしで開くため）
    try:
        from proxy_server import start_proxy_server
        start_proxy_server()
    except Exception as e:
        print(f"Proxy start failed: {e}")

    def register_existing_config():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            
            uid = config_data.get("uuid")
            name = config_data.get("name", "Unknown")
            dept = config_data.get("department", "Unknown")
            section = config_data.get("section", "")
            
            import requests
            from google.oauth2 import service_account
            import google.auth.transport.requests
            
            KEY_PATH = os.path.join(os.path.dirname(__file__), "client-key.json")
            url = "https://task-mining-server-1097969102143.asia-northeast1.run.app/api/auth/register_employee"
            
            credentials = service_account.IDTokenCredentials.from_service_account_file(
                KEY_PATH, target_audience="https://task-mining-server-1097969102143.asia-northeast1.run.app"
            )
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {credentials.token}'
            }
            
            payload = {"user_id": uid, "name": name, "department": dept, "section": section}
            requests.post(url, json=payload, headers=headers, timeout=5)
        except Exception as e:
            print(f"Failed to register existing config: {e}")

    # PC起動時に自動起動するためのスタートアップ登録
    def add_to_startup():
        try:
            import win32com.client
            import sys, os
            if not getattr(sys, 'frozen', False):
                return # exe実行時のみ登録する
                
            exe_path = sys.executable
            startup_dir = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
            shortcut_path = os.path.join(startup_dir, "ForestTaskMiningSystem.lnk")
            
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            if shortcut.Targetpath != exe_path:
                shortcut.Targetpath = exe_path
                shortcut.WorkingDirectory = os.path.dirname(exe_path)
                shortcut.IconLocation = exe_path
                shortcut.save()
        except Exception as e:
            print(f"Startup error: {e}")
            
    # 初回起動チェック（config.jsonが無ければセットアップ画面へ）
    if not os.path.exists(CONFIG_FILE):
        app = SetupWindow()
        app.mainloop()
        if not os.path.exists(CONFIG_FILE):
            return
    else:
        register_existing_config()
            
    # 初期設定が終わったら（または既にされていれば）スタートアップに登録
    add_to_startup()

    def global_log_action(payload):
        try:
            app = payload.get("app_name") or payload.get("app", "Unknown")
            title = payload.get("file_name") or payload.get("title", "Unknown")
            t = payload.get("type", "Unknown")
            log_msg = f"[TRACK] {t} : {app} - {title}\n"
            
            log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stream.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(log_msg)
                
            if os.path.exists(log_path) and os.path.getsize(log_path) > 1024 * 50:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(log_msg)
        except:
            pass

    # タスクマイニングをバックグラウンドで強制開始（停止不可）
    threading.Thread(target=start_macro_tracking, args=(global_log_action,), daemon=True).start()
    threading.Thread(target=start_micro_tracking, args=(global_log_action,), daemon=True).start()
    threading.Thread(target=start_excel_tracking, args=(global_log_action,), daemon=True).start()

    # タスクバー（システムトレイ）に常駐
    menu = pystray.Menu(
        item('ダッシュボードを開く', open_dashboard),
        item('アプリを終了', exit_app)
    )
    
    icon = pystray.Icon("ForestTaskMiningSystem", create_image(), "ForestTaskMiningSystem", menu)
    icon.run()

if __name__ == "__main__":
    main()
