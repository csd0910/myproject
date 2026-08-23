import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import sys
import os

# 自作モジュールのインポート（同一階層にある前提）
import activity_logger
import system_logger
import generate_daily_report

class ActivityLoggerUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DX推進アシスタント (AIロガー)")
        self.root.geometry("450x180")
        
        # ログフォルダパス
        self.log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "activity_logs"))
        
        # UI構築
        self.setup_ui()
        
        # 記録スレッドの管理
        self.record_thread_ai = None
        self.record_thread_sys = None
        
    def setup_ui(self):
        main_frame = tk.Frame(self.root, padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左側：記録開始/停止ボタン
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.btn_toggle = tk.Button(left_frame, text="記録開始", font=("Helvetica", 16, "bold"), fg="red", command=self.toggle_recording)
        self.btn_toggle.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 右側：フォルダ設定・日報生成ボタン
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        tk.Label(right_frame, text="【ログ保存フォルダ】", font=("Helvetica", 9)).pack(anchor="w")
        
        dir_frame = tk.Frame(right_frame)
        dir_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.log_dir_var = tk.StringVar(value=self.log_dir)
        entry = tk.Entry(dir_frame, textvariable=self.log_dir_var, width=22)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        btn_browse = tk.Button(dir_frame, text="参照", command=self.browse_folder)
        btn_browse.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.btn_report = tk.Button(right_frame, text="日報（MD/HTML）を出力する", font=("Helvetica", 10), command=self.generate_report)
        self.btn_report.pack(fill=tk.X)

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.log_dir_var.get())
        if folder:
            self.log_dir_var.set(folder)

    def toggle_recording(self):
        if self.record_thread_ai is None or not self.record_thread_ai.is_alive():
            # 記録開始
            activity_logger.stop_event.clear()
            system_logger.stop_event.clear()
            
            target_dir = self.log_dir_var.get()
            
            # AI画像ロガーの起動
            self.record_thread_ai = threading.Thread(target=activity_logger.main, args=(target_dir,), daemon=True)
            self.record_thread_ai.start()
            
            # システムロガー（Excel/クリップボード監視）の起動
            self.record_thread_sys = threading.Thread(target=system_logger.main, args=(target_dir,), daemon=True)
            self.record_thread_sys.start()
            
            self.btn_toggle.config(text="記録停止", fg="blue")
        else:
            # 記録停止
            activity_logger.stop_event.set()
            system_logger.stop_event.set()
            self.btn_toggle.config(text="記録開始", fg="red")

    def generate_report(self):
        self.btn_report.config(text="出力中...", state=tk.DISABLED)
        self.root.update()
        try:
            target_dir = self.log_dir_var.get()
            generate_daily_report.generate_reports(base_dir=target_dir)
            messagebox.showinfo("完了", "MD版とHTML版の日報を出力しました！\ndaily_reportsフォルダをご確認ください。")
        except Exception as e:
            messagebox.showerror("エラー", f"出力に失敗しました: {e}")
        finally:
            self.btn_report.config(text="日報（MD/HTML）を出力する", state=tk.NORMAL)

def main():
    app = ActivityLoggerUI()
    app.root.mainloop()

if __name__ == "__main__":
    main()
