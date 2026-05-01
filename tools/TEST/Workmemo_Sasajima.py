import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import datetime
import csv
import os
import json
import threading
import sys

# 追加ライブラリ (pip install pystray keyboard Pillow)
try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    pystray = None

try:
    import keyboard
except ImportError:
    keyboard = None


# --- ファイルパス設定 ---
if getattr(sys, 'frozen', False):
    # exe版の場合: exeファイルと同じ階層
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # スクリプト版の場合: スクリプトと同じ階層
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

CONFIG_FILE = os.path.join(DATA_DIR, "config_sasajima.json")

# マスタデータ (組織図より)
DEFAULT_DEPT_MASTER = {
    "営業部": ["営業課", "営業推進課"],
    "カスタマーソリューション部": ["カスタマーサポート課", "サービス課"],
    "商品部": ["商品課", "商品管理課"],
    "マーケティング部": ["マーケティング課", "デジタルマーケティング課"],
    "物流部": ["ロジスティクス運営課"],
    "配送部": ["配送サービス課"],
    "管理部": ["総務人事課", "財務経理課"],
    "事業管理部": [],
    "システム部": ["システム課", "システム運営課(大宮)"]
}

DEFAULT_CONFIG = {
    "user_name": "佐々嶌",
    "department_master": DEFAULT_DEPT_MASTER,
    "status_list": ["完了", "着手中", "中断", "中断 フィードバック待ち", "未着手"],
    "csv_path": os.path.join(DATA_DIR, "sasajima_work_log.csv"),
    "hotkey": "ctrl+shift+w"
}

class ConfigManager:
    @staticmethod
    def load():
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf_8_sig") as f:
                    config = json.load(f)
                    for k, v in DEFAULT_CONFIG.items():
                        if k not in config: config[k] = v
                    return config
            except:
                pass
        return DEFAULT_CONFIG.copy()

    @staticmethod
    def save(config):
        with open(CONFIG_FILE, "w", encoding="utf_8_sig") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, config, on_save):
        super().__init__(parent)
        self.title("設定")
        self.geometry("400x380")
        self.config_data = config
        self.on_save = on_save
        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="担当者名:").pack(anchor=tk.W)
        self.ent_user = ttk.Entry(main_frame)
        self.ent_user.insert(0, self.config_data.get("user_name", ""))
        self.ent_user.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(main_frame, text="状況リスト (カンマ区切り):").pack(anchor=tk.W)
        self.txt_status = tk.Text(main_frame, height=3, font=("Segoe UI", 9))
        self.txt_status.insert("1.0", ",".join(self.config_data.get("status_list", [])))
        self.txt_status.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(main_frame, text="呼出ホットキー (例: ctrl+shift+w):").pack(anchor=tk.W)
        self.ent_hotkey = ttk.Entry(main_frame)
        self.ent_hotkey.insert(0, self.config_data.get("hotkey", "ctrl+shift+w"))
        self.ent_hotkey.pack(fill=tk.X, pady=(0, 10))

        # --- スタートアップ登録設定 ---
        startup_frame = ttk.Frame(main_frame)
        startup_frame.pack(fill=tk.X, pady=(5, 10))
        ttk.Label(startup_frame, text="PC起動時の自動起動 (exe版のみ):").pack(side=tk.LEFT)
        ttk.Button(startup_frame, text="登録", command=self.add_to_startup).pack(side=tk.LEFT, padx=5)
        ttk.Button(startup_frame, text="解除", command=self.remove_from_startup).pack(side=tk.LEFT)

        ttk.Label(main_frame, text="※部署・課のマスタ変更は、設定ファイル(config_sasajima.json)\nを直接編集してください。", foreground="gray").pack(anchor=tk.W, pady=(5, 0))

        ttk.Button(main_frame, text="設定を保存", command=self.save).pack(pady=20)

    def add_to_startup(self):
        if not getattr(sys, 'frozen', False):
            messagebox.showinfo("情報", "この機能はexe化されたバージョンでのみ利用可能です。")
            return
        exe_path = sys.executable
        startup_dir = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
        shortcut_path = os.path.join(startup_dir, "Workmemo_Sasajima.lnk")
        
        vbs_path = os.path.join(os.environ.get("TEMP", ""), "create_shortcut.vbs")
        vbs_content = f"""
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{exe_path}"
oLink.WindowStyle = 7
oLink.Save
"""
        try:
            with open(vbs_path, "w", encoding="shift_jis") as f:
                f.write(vbs_content.strip())
            os.system(f'cscript //nologo "{vbs_path}"')
            messagebox.showinfo("完了", "PC起動時の自動起動（スタートアップ）に登録しました。\n次回から自動でタスクトレイに常駐します。")
        except Exception as e:
            messagebox.showerror("エラー", f"登録に失敗しました:\n{e}")

    def remove_from_startup(self):
        startup_dir = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
        shortcut_path = os.path.join(startup_dir, "Workmemo_Sasajima.lnk")
        if os.path.exists(shortcut_path):
            try:
                os.remove(shortcut_path)
                messagebox.showinfo("完了", "スタートアップから解除しました。")
            except Exception as e:
                messagebox.showerror("エラー", f"解除に失敗しました:\n{e}")
        else:
            messagebox.showinfo("情報", "スタートアップには登録されていません。")

    def save(self):
        new_config = {
            "user_name": self.ent_user.get(),
            "department_master": self.config_data.get("department_master", DEFAULT_DEPT_MASTER),
            "status_list": [s.strip() for s in self.txt_status.get("1.0", tk.END).split(",") if s.strip()],
            "csv_path": self.config_data.get("csv_path", ""),
            "hotkey": self.ent_hotkey.get()
        }
        ConfigManager.save(new_config)
        self.on_save(new_config)
        self.destroy()

class HistoryWindow(tk.Toplevel):
    def __init__(self, parent, csv_path, on_select):
        super().__init__(parent)
        self.title("履歴から選択")
        self.geometry("800x400")
        self.csv_path = csv_path
        self.on_select = on_select
        self.setup_ui()

    def setup_ui(self):
        frame = ttk.Frame(self, padding="5")
        frame.pack(fill=tk.BOTH, expand=True)

        columns = ("no", "date", "dept", "title", "status")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings")
        self.tree.heading("no", text="No.")
        self.tree.heading("date", text="依頼日")
        self.tree.heading("dept", text="依頼部署")
        self.tree.heading("title", text="課題件名")
        self.tree.heading("status", text="状況")
        
        self.tree.column("no", width=40, anchor=tk.CENTER)
        self.tree.column("date", width=80, anchor=tk.CENTER)
        self.tree.column("dept", width=120)
        self.tree.column("title", width=400)
        self.tree.column("status", width=60, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.load_history()
        self.tree.bind("<Double-1>", self.select)
        ttk.Button(self, text="選択して入力欄に反映", command=self.select).pack(pady=5)

    def load_history(self):
        if not self.csv_path or not os.path.exists(self.csv_path): return
        self.history_items = []
        try:
            with open(self.csv_path, 'r', encoding='utf_8_sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                for i, r in enumerate(rows[-100:][::-1]):
                    self.history_items.append(r)
                    self.tree.insert("", tk.END, values=(
                        r.get("No.",""), r.get("依頼日",""), r.get("依頼部署","").replace("\n", " "),
                        r.get("課題件名",""), r.get("状況","")), tags=(str(i),))
        except Exception as e:
            print(f"History Load Error: {e}")

    def select(self, event=None):
        selection = self.tree.selection()
        if not selection: return
        item = self.tree.item(selection[0])
        idx = int(item['tags'][0])
        raw_data = self.history_items[idx]
        self.on_select(raw_data)
        self.destroy()

class WorkLogSasajimaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("作業課題記録ツール (佐々嶌仕様)")
        self.root.geometry("550x750")
        self.root.configure(bg="#f0f2f5")

        self.config = ConfigManager.load()

        self.apply_style()
        self.setup_ui()
        self.bind_events()
        
        # タスクトレイ常駐設定
        self.tray_icon = None
        self.setup_tray()
        
        # ホットキー設定
        self.setup_hotkey()

    def apply_style(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background="#f0f2f5")
        self.style.configure("TLabel", background="#f0f2f5", font=("Meiryo", 9))
        self.style.configure("Header.TLabel", font=("Meiryo", 9, "bold"))
        self.style.configure("TButton", font=("Meiryo", 9))
        self.style.configure("Accent.TButton", foreground="white", background="#007bff", font=("Meiryo", 10, "bold"))
        self.style.map("Accent.TButton", background=[('active', '#0056b3')])

    def setup_ui(self):
        self.main_frame = ttk.Frame(self.root, padding="5")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Top Bar (Settings & CSV Path)
        top_bar = ttk.Frame(self.main_frame)
        top_bar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(top_bar, text="⚙", width=3, command=self.open_settings).pack(side=tk.LEFT)
        self.lbl_user_info = ttk.Label(top_bar, text=f"担当: {self.config.get('user_name', '')}", style="Header.TLabel")
        self.lbl_user_info.pack(side=tk.LEFT, padx=5)

        ttk.Button(top_bar, text="📁保存先CSV変更", command=self.change_csv_path).pack(side=tk.RIGHT)
        
        self.lbl_csv_path = ttk.Label(self.main_frame, text=f"保存先: {self.config.get('csv_path', '未設定')}", foreground="blue", font=("Meiryo", 8))
        self.lbl_csv_path.pack(fill=tk.X, pady=(0, 5))
        self.lbl_csv_path.bind("<Button-1>", lambda e: self.open_csv())
        self.lbl_csv_path.configure(cursor="hand2")

        # Row 1: 依頼日, 期限, 状況, 年度
        row1 = ttk.Frame(self.main_frame)
        row1.pack(fill=tk.X, pady=2)
        
        ttk.Label(row1, text="依頼日:").pack(side=tk.LEFT)
        self.ent_date = ttk.Entry(row1, width=12)
        self.ent_date.pack(side=tk.LEFT, padx=(2, 10))
        
        ttk.Label(row1, text="期限:").pack(side=tk.LEFT)
        self.ent_deadline = ttk.Entry(row1, width=12)
        self.ent_deadline.pack(side=tk.LEFT, padx=(2, 10))

        ttk.Label(row1, text="状況:").pack(side=tk.LEFT)
        self.cb_status = ttk.Combobox(row1, values=self.config.get("status_list", []), width=18)
        self.cb_status.pack(side=tk.LEFT, padx=(2, 10))

        ttk.Label(row1, text="年度:").pack(side=tk.LEFT)
        self.ent_nendo = ttk.Entry(row1, width=8)
        self.ent_nendo.pack(side=tk.LEFT, padx=(2, 0))

        # Row 2: 依頼部署 (部 と 課)
        row2 = ttk.Frame(self.main_frame)
        row2.pack(fill=tk.X, pady=5)

        ttk.Label(row2, text="依頼部署 (部):").pack(side=tk.LEFT)
        dept_master = self.config.get("department_master", {})
        self.cb_dept = ttk.Combobox(row2, values=list(dept_master.keys()), width=15)
        self.cb_dept.pack(side=tk.LEFT, padx=(2, 10))
        self.cb_dept.bind("<<ComboboxSelected>>", self.on_dept_selected)
        self.cb_dept.bind("<KeyRelease>", self.on_dept_selected)

        ttk.Label(row2, text="(課):").pack(side=tk.LEFT)
        self.cb_section = ttk.Combobox(row2, width=18)
        self.cb_section.pack(side=tk.LEFT, padx=(2, 0))

        # Row 3: 課題件名
        row3 = ttk.Frame(self.main_frame)
        row3.pack(fill=tk.X, pady=5)
        ttk.Label(row3, text="課題件名:").pack(side=tk.LEFT)
        self.ent_title = ttk.Entry(row3)
        self.ent_title.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

        # Text Areas Helper
        def create_text_area(parent, label_text, height=3):
            frame = ttk.Frame(parent)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=label_text, style="Header.TLabel").pack(anchor=tk.W)
            txt = tk.Text(frame, height=height, font=("Meiryo", 9), bd=1, relief=tk.SOLID)
            txt.pack(fill=tk.X, pady=(2, 0))
            return txt

        # Text Areas
        self.txt_problem = create_text_area(self.main_frame, "課題内容:", height=4)
        self.txt_solution = create_text_area(self.main_frame, "対応内容:", height=4)
        self.txt_note = create_text_area(self.main_frame, "備考:", height=3)
        self.txt_progress = create_text_area(self.main_frame, "進捗:", height=2)
        self.txt_effect = create_text_area(self.main_frame, "効果:", height=2)

        # Footer Buttons
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text="クリア", command=self.reset_inputs, width=8).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="👔 履歴から引用", command=self.open_history).pack(side=tk.LEFT, padx=5)
        
        self.btn_save = ttk.Button(btn_frame, text="保存 (Ctrl+Enter)", command=self.save_log, style="Accent.TButton")
        self.btn_save.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))

        self.set_default_dates()

    def focus_next_widget(self, event):
        # Tabキーでテキストエリアから次のウィジェットへ移動
        event.widget.tk_focusNext().focus()
        return "break"

    def on_dept_selected(self, event=None):
        dept = self.cb_dept.get()
        dept_master = self.config.get("department_master", {})
        if dept in dept_master:
            self.cb_section.config(values=dept_master[dept])
        else:
            self.cb_section.config(values=[])

    def set_default_dates(self):
        now = datetime.datetime.now()
        today_str = now.strftime("%Y/%m/%d")
        nendo = now.year if now.month >= 4 else now.year - 1
        nendo_str = f"{nendo}年度"

        self.ent_date.delete(0, tk.END)
        self.ent_date.insert(0, today_str)

        self.ent_deadline.delete(0, tk.END)
        self.ent_deadline.insert(0, today_str)

        self.ent_nendo.delete(0, tk.END)
        self.ent_nendo.insert(0, nendo_str)

    def bind_events(self):
        self.root.bind('<Control-Return>', lambda e: self.save_log())
        # Xボタン（閉じる）を押したときに終了ではなく非表示にする（常駐）
        self.root.protocol('WM_DELETE_WINDOW', self.hide_window)
        
        # TextウィジェットのTabキーでの移動を有効にする
        self.txt_problem.bind("<Tab>", self.focus_next_widget)
        self.txt_solution.bind("<Tab>", self.focus_next_widget)
        self.txt_note.bind("<Tab>", self.focus_next_widget)
        self.txt_progress.bind("<Tab>", self.focus_next_widget)
        self.txt_effect.bind("<Tab>", self.focus_next_widget)

    # --- トレイアイコン（常駐）設定 ---
    def setup_tray(self):
        if pystray is None: return
        
        def create_image():
            # 簡単なアイコン画像を生成
            image = Image.new('RGB', (64, 64), color=(0, 120, 215))
            dc = ImageDraw.Draw(image)
            dc.rectangle((16, 16, 48, 48), fill=(255, 255, 255))
            return image

        menu = pystray.Menu(
            pystray.MenuItem("画面を表示", self.show_window_from_tray, default=True),
            pystray.MenuItem("終了", self.quit_app)
        )
        self.tray_icon = pystray.Icon("Workmemo_Sasajima", create_image(), "作業記録(佐々嶌仕様)", menu)
        # トレイアイコンを別スレッドで起動
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def hide_window(self):
        self.root.withdraw()

    def show_window_from_tray(self, icon=None, item=None):
        self.root.after(0, self.show_window)

    def show_window(self):
        self.root.deiconify()
        self.root.attributes('-topmost', True)
        self.root.lift()
        self.root.focus_force()
        self.root.after(500, lambda: self.root.attributes('-topmost', False))

    def quit_app(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        if keyboard is not None:
            try:
                keyboard.unhook_all()
            except:
                pass
        self.root.quit()
        self.root.destroy()
        os._exit(0)

    # --- ホットキー設定 ---
    def setup_hotkey(self):
        if keyboard is None: return
        hotkey = self.config.get("hotkey", "ctrl+shift+w")
        try:
            # suppress=Trueで元のキー入力を無効化し、ボタン誤作動を防ぐ
            keyboard.add_hotkey(hotkey, self.on_hotkey_pressed, suppress=True)
        except Exception as e:
            print(f"Hotkey register error: {e}")

    def toggle_window(self):
        if self.root.state() == 'withdrawn' or not self.root.winfo_viewable():
            self.show_window()
        else:
            self.hide_window()

    def on_hotkey_pressed(self):
        self.root.after(0, self.toggle_window)

    def update_hotkey(self, new_hotkey):
        if keyboard is None: return
        try:
            keyboard.unhook_all_hotkeys()
            if new_hotkey:
                keyboard.add_hotkey(new_hotkey, self.on_hotkey_pressed, suppress=True)
        except Exception as e:
            print(f"Hotkey update error: {e}")

    # --- その他の処理 ---
    def open_settings(self):
        SettingsWindow(self.root, self.config, self.update_config)

    def update_config(self, new_config):
        old_hotkey = self.config.get("hotkey")
        self.config = new_config
        self.lbl_user_info.config(text=f"担当: {self.config.get('user_name', '')}")
        
        dept_master = self.config.get("department_master", {})
        self.cb_dept.config(values=list(dept_master.keys()))
        self.cb_status.config(values=self.config.get("status_list", []))
        self.lbl_csv_path.config(text=f"保存先: {self.config.get('csv_path', '未設定')}")
        
        if new_config.get("hotkey") != old_hotkey:
            self.update_hotkey(new_config.get("hotkey"))

    def change_csv_path(self):
        path = filedialog.asksaveasfilename(
            title="CSVファイルの保存先を選択/作成",
            defaultextension=".csv",
            filetypes=[("CSVファイル", "*.csv")],
            initialfile="sasajima_work_log.csv"
        )
        if path:
            self.config["csv_path"] = path
            ConfigManager.save(self.config)
            self.lbl_csv_path.config(text=f"保存先: {path}")

    def open_csv(self):
        path = self.config.get("csv_path", "")
        if path and os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showinfo("情報", "CSVファイルがまだ作成されていないか、パスが未設定です。")

    def open_history(self):
        path = self.config.get("csv_path", "")
        if not path or not os.path.exists(path):
            messagebox.showwarning("警告", "履歴を読み込むCSVファイルがありません。")
            return
        HistoryWindow(self.root, path, self.on_history_select)

    def on_history_select(self, d):
        self.ent_date.delete(0, tk.END); self.ent_date.insert(0, d.get("依頼日",""))
        
        dept_full = d.get("依頼部署","")
        parts = dept_full.split("\n", 1) if "\n" in dept_full else dept_full.split(" ", 1)
        self.cb_dept.set(parts[0] if len(parts) > 0 else "")
        self.on_dept_selected()
        self.cb_section.set(parts[1] if len(parts) > 1 else "")
        
        self.ent_title.delete(0, tk.END); self.ent_title.insert(0, d.get("課題件名",""))
        
        self.txt_problem.delete("1.0", tk.END); self.txt_problem.insert("1.0", d.get("課題内容",""))
        self.txt_solution.delete("1.0", tk.END); self.txt_solution.insert("1.0", d.get("対応内容",""))
        
        self.ent_deadline.delete(0, tk.END); self.ent_deadline.insert(0, d.get("期限",""))
        self.cb_status.set(d.get("状況",""))
        
        self.txt_note.delete("1.0", tk.END); self.txt_note.insert("1.0", d.get("備考",""))
        self.txt_progress.delete("1.0", tk.END); self.txt_progress.insert("1.0", d.get("進捗",""))
        self.txt_effect.delete("1.0", tk.END); self.txt_effect.insert("1.0", d.get("効果",""))
        self.ent_nendo.delete(0, tk.END); self.ent_nendo.insert(0, d.get("年度",""))

    def save_log(self):
        csv_path = self.config.get("csv_path", "")
        if not csv_path:
            messagebox.showwarning("警告", "CSVの保存先が設定されていません。\n右上の「保存先CSV変更」から設定してください。")
            self.change_csv_path()
            csv_path = self.config.get("csv_path", "")
            if not csv_path: return

        irai_date = self.ent_date.get()
        dept_part = self.cb_dept.get().strip()
        section_part = self.cb_section.get().strip()
        
        if dept_part and section_part:
            dept = f"{dept_part}\n{section_part}"
        else:
            dept = dept_part or section_part

        title = self.ent_title.get()
        problem = self.txt_problem.get("1.0", tk.END).strip()
        solution = self.txt_solution.get("1.0", tk.END).strip()
        deadline = self.ent_deadline.get()
        status = self.cb_status.get()
        note = self.txt_note.get("1.0", tk.END).strip()
        progress = self.txt_progress.get("1.0", tk.END).strip()
        effect = self.txt_effect.get("1.0", tk.END).strip()
        nendo = self.ent_nendo.get()

        if not title:
            if not messagebox.askyesno("確認", "課題件名が空ですが保存しますか？"):
                return

        next_no = 1
        if os.path.exists(csv_path):
            try:
                with open(csv_path, 'r', encoding='utf_8_sig') as f:
                    reader = csv.reader(f)
                    lines = list(reader)
                    if len(lines) > 1:
                        last_no = lines[-1][0]
                        if last_no.isdigit(): next_no = int(last_no) + 1
            except: pass

        headers = ["No.", "依頼日", "依頼部署", "課題件名", "課題内容", "対応内容", "期限", "状況", "備考", "進捗", "効果", "年度"]
        data = [next_no, irai_date, dept, title, problem, solution, deadline, status, note, progress, effect, nendo]

        try:
            file_exists = os.path.isfile(csv_path)
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            
            with open(csv_path, 'a', newline='', encoding='utf_8_sig') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(headers)
                writer.writerow(data)
            
            self.root.bell()
            messagebox.showinfo("成功", f"記録しました (No.{next_no})", parent=self.root)
            self.reset_inputs()
            self.hide_window() # 保存したら画面を隠す
        except PermissionError:
            messagebox.showerror("エラー", "CSVファイルがExcel等で開かれているため書き込めません。\n閉じてから再度お試しください。", parent=self.root)
        except Exception as e:
            messagebox.showerror("エラー", f"保存中にエラーが発生しました:\n{e}", parent=self.root)

    def reset_inputs(self):
        self.set_default_dates()
        self.cb_dept.set('')
        self.cb_section.set('')
        self.cb_section.config(values=[])
        self.ent_title.delete(0, tk.END)
        self.txt_problem.delete("1.0", tk.END)
        self.txt_solution.delete("1.0", tk.END)
        self.cb_status.set('')
        self.txt_note.delete("1.0", tk.END)
        self.txt_progress.delete("1.0", tk.END)
        self.txt_effect.delete("1.0", tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = WorkLogSasajimaApp(root)
    root.mainloop()
