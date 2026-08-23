import sys
import os

# 起動直後に黒画面（コンソール）へメッセージを表示
print("=========================================================")
print("  DX_Reverse_Engineering_Engine を起動しています...")
print("  （AIエンジンやデータ解析ライブラリの展開中です。起動まで数秒〜十数秒お待ちください）")
print("=========================================================\n")

import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
import threading
import sys
import os
import logging
import traceback

# ログファイルの設定
log_file_path = r"C:\AutoAnalysisLogs\error_log.txt"
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# 自作モジュールのインポート
import activity_logger
import system_logger
import generate_daily_report
import generate_visual_excel_report
import merge_logs_to_excel

class ActivityLoggerUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DX推進アシスタント (AIロガー)")
        self.root.geometry("520x400")
        
        # ログフォルダパス
        self.log_dir = r"C:\AutoAnalysisLogs"
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.target_file_var = tk.StringVar()
        self.status_var = tk.StringVar(value="待機中...")
        self.pct_var = tk.StringVar(value="0%")
        
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
        
        # 使い方ボタン
        self.btn_help = tk.Button(left_frame, text="使い方・ヘルプ", command=self.show_help,
                                  font=("Meiryo UI", 10), bg="#ff9800", fg="white")
        self.btn_help.pack(fill=tk.X, padx=5, pady=5)

        # 右側：フォルダ設定・日報生成ボタン
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        tk.Label(right_frame, text="【ログ保存フォルダ】", font=("Helvetica", 9)).pack(anchor="w")
        
        dir_frame = tk.Frame(right_frame)
        dir_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.log_dir_var = tk.StringVar(value=self.log_dir)
        entry = tk.Entry(dir_frame, textvariable=self.log_dir_var, width=22)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        btn_browse = tk.Button(dir_frame, text="参照", command=self.browse_folder)
        btn_browse.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 操作ファイル登録枠
        file_frame = tk.Frame(right_frame)
        file_frame.pack(fill=tk.X, pady=(0, 15))
        tk.Label(file_frame, text="【操作ファイル (記録前に登録)】", font=("Helvetica", 9)).pack(anchor="w")
        
        entry_file = tk.Entry(file_frame, textvariable=self.target_file_var, width=22)
        entry_file.pack(side=tk.LEFT, fill=tk.X, expand=True)
        btn_browse_file = tk.Button(file_frame, text="参照", command=self.browse_target_file)
        btn_browse_file.pack(side=tk.RIGHT, padx=(5, 0))

        # 分析レポート出力ボタン
        self.btn_report = tk.Button(right_frame, text="分析レポートを一括出力する", command=self.start_generate_report,
                                    font=("Meiryo UI", 12), bg="#4CAF50", fg="white", height=2)
        self.btn_report.pack(fill=tk.X, pady=(0, 10))

        # 進捗ステータスとプログレスバー
        self.lbl_status = tk.Label(right_frame, textvariable=self.status_var, font=("Meiryo UI", 9), fg="#333333")
        self.lbl_status.pack(anchor="w")
        
        progress_frame = tk.Frame(right_frame)
        progress_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.progress = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.lbl_pct = tk.Label(progress_frame, textvariable=self.pct_var, font=("Meiryo UI", 9, "bold"), width=5, anchor="e")
        self.lbl_pct.pack(side=tk.RIGHT, padx=(5, 0))

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.log_dir_var.get())
        if folder:
            self.log_dir_var.set(folder)

    def browse_target_file(self):
        file_path = filedialog.askopenfilename(
            title="記録対象のメインファイルを選択",
            filetypes=[("Excel Files", "*.xlsx *.xlsb *.xls *.xlsm")]
        )
        if file_path:
            self.target_file_var.set(file_path)

    def show_help(self):
        help_text = (
            "【DX推進アシスタント 黄金の運用ルール】\n\n"
            "本システムは「1回の記録で1つの独立した業務」を分析します。\n\n"
            "1. 操作ファイル欄に、今回作業するメインファイルを登録\n"
            "2. 「記録開始」を押す\n"
            "3. 普段通りに業務を実施する\n"
            "4. 業務が終わったら「記録停止」を押す\n"
            "5. 「分析レポートを出力する」を押す\n\n"
            "※ これにより、HTMLフロー図、統合Excel生ログ、吹き出しマニュアル、数式解析レポートが一括生成されます。"
        )
        messagebox.showinfo("使い方", help_text)

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
            self.status_var.set("記録中...")
        else:
            # 記録停止
            activity_logger.stop_event.set()
            system_logger.stop_event.set()
            self.btn_toggle.config(text="記録開始", fg="red")
            self.status_var.set("記録停止。出力可能です。")

    def start_generate_report(self):
        t_file = self.target_file_var.get()
        if t_file and os.path.exists(t_file):
            # ファイルロックエラーを防ぐための事前警告
            ans = messagebox.askokcancel(
                "事前の確認", 
                "VisualReport（吹き出しマニュアル）を生成します。\n\n"
                "操作対象のExcelファイルが現在開かれている場合、エラーになります。\n"
                "ファイルを【保存して閉じてから】「OK」を押してください。"
            )
            if not ans:
                return

        # 連続クリック防止
        self.btn_report.config(text="出力中...", state=tk.DISABLED)
        self.progress["value"] = 0
        self.pct_var.set("0%")
        
        # 別スレッドで生成処理を開始（UIのフリーズ防止）
        threading.Thread(target=self._generate_report_worker, daemon=True).start()

    def update_progress(self, val, text):
        self.stop_fake_progress()
        self.progress["value"] = val
        self.pct_var.set(f"{val}%")
        self.status_var.set(text)
        self.root.update_idletasks()

    def start_fake_progress(self, current, target, duration_sec):
        self._stop_fake = False
        steps = target - current
        if steps <= 0: return
        delay = int((duration_sec / steps) * 1000)
        
        def step(val):
            if self._stop_fake or val > target:
                return
            self.progress["value"] = val
            self.pct_var.set(f"{val}%")
            self.root.after(delay, step, val + 1)
            
        self.root.after(delay, step, current + 1)

    def stop_fake_progress(self):
        self._stop_fake = True

    def _generate_report_worker(self):
        try:
            target_dir = self.log_dir_var.get()
            os.makedirs(target_dir, exist_ok=True)
            
            # 1. HTML分析レポートの生成 (AI推論含む)
            self.update_progress(10, "簡易日報をAIで解析中 (1/4)...")
            self.start_fake_progress(10, 20, 10)
            
            import generate_daily_report
            # コールバック関数を渡して、内部から進行度を細かくUIに反映させる
            def report_progress_cb(val, text):
                self.root.after(0, lambda v=val, t=text: self.update_progress(v, t))
                
            generate_daily_report.generate_reports(target_dir=target_dir, progress_callback=report_progress_cb)
            self.stop_fake_progress()
            
            # HTMLが生成されたら、待たせずにすぐブラウザで開く
            import glob
            html_files = glob.glob(os.path.join(target_dir, "daily_reports", "*.html"))
            if html_files:
                latest_html = max(html_files, key=os.path.getmtime)
                try:
                    os.startfile(latest_html)
                except Exception:
                    pass
            
            # 2. Excel統合ログの生成
            self.update_progress(40, "生ログを統合Excelに変換中 (2/4)...")
            merge_logs_to_excel.merge_logs_to_excel(base_dir=target_dir)
            
            # 事前登録されたファイルがあれば、VisualReportと数式解析レポートを生成
            t_file = self.target_file_var.get()
            if t_file and os.path.exists(t_file):
                # 3. VisualReport (吹き出しマニュアル) 生成
                self.update_progress(60, "対象ファイルにAI吹き出しを図解中 (3/4)...")
                generate_visual_excel_report.create_visual_report(log_dir=target_dir, target_file_path=t_file)
                
                # 4. 数式解析レポート生成
                self.update_progress(85, "対象ファイルの裏側数式を全解析中 (4/4)...")
                import formula_analyzer
                out_md = os.path.join(target_dir, "daily_reports", f"formulas_extracted_{os.path.basename(t_file)}.md")
                formula_analyzer.analyze_and_save(t_file, out_md)
            else:
                self.update_progress(70, "操作ファイル未登録のため、旧ロジックで図解中...")
                generate_visual_excel_report.create_visual_report(log_dir=target_dir)
            
            self.update_progress(100, "すべての出力が完了しました！")
            
            # 完了メッセージはメインスレッドで表示
            self.root.after(0, lambda: messagebox.showinfo("成功", "すべてのレポートの生成が完了しました！\nC:\\AutoAnalysisLogs\\daily_reports および出力フォルダを確認してください。"))
            
        except Exception as e:
            self.update_progress(0, "エラーが発生しました")
            err_msg = str(e)
            logging.error("レポート出力中にエラーが発生しました", exc_info=True)
            self.root.after(0, lambda err=err_msg: messagebox.showerror("エラー", f"レポート出力中にエラーが発生しました。\nもう一度お試しください。\n詳細: {err}\n\n※詳細は error_log.txt を確認してください。"))
        finally:
            # 失敗しても成功してもボタンを元に戻す
            self.root.after(0, lambda: self.btn_report.config(text="分析レポートを一括出力する", state=tk.NORMAL))


def main():
    app = ActivityLoggerUI()
    app.root.mainloop()

if __name__ == "__main__":
    main()
