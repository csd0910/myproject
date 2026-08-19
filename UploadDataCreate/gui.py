import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging

# ロガー設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class UploadDataCreateApp:
    def __init__(self, root):
        self.root = root
        self.root.title("UploadDataCreate ツール")
        self.root.geometry("750x650")  # 全工程が入るように少し縦に拡張
        
        # スタイルの設定
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')
            
        style.configure("TFrame", background="#f0f4f8")
        style.configure("TLabel", background="#f0f4f8", font=("Meiryo UI", 9))
        style.configure("Header.TLabel", font=("Meiryo UI", 14, "bold"), foreground="#102a43", background="#f0f4f8")
        style.configure("TButton", font=("Meiryo UI", 9), padding=3)
        style.configure("Action.TButton", font=("Meiryo UI", 10, "bold"), background="#0078d4", foreground="white")
        style.map("Action.TButton", background=[("active", "#005a9e")])
        
        self.root.configure(bg="#f0f4f8")
        
        self.base_file_path = tk.StringVar()
        self.config_file_path = tk.StringVar()
        
        self._create_widgets()
        
    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_label = ttk.Label(main_frame, text="UploadData 作成ツール", style="Header.TLabel", anchor="center")
        title_label.pack(fill=tk.X, pady=(0, 10))
        
        # --- ファイル選択エリア ---
        file_frame = ttk.Frame(main_frame)
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_frame, text="作業する対象ファイル:").grid(row=0, column=0, sticky="w", pady=2, padx=5)
        ttk.Entry(file_frame, textvariable=self.base_file_path, width=45).grid(row=0, column=1, padx=5)
        ttk.Button(file_frame, text="参照...", command=self._select_base_file).grid(row=0, column=2, padx=5)
        
        ttk.Label(file_frame, text="案件設定ファイル (JSON):").grid(row=1, column=0, sticky="w", pady=2, padx=5)
        ttk.Entry(file_frame, textvariable=self.config_file_path, width=45).grid(row=1, column=1, padx=5)
        ttk.Button(file_frame, text="参照...", command=self._select_config_file).grid(row=1, column=2, padx=5)
        
        # --- 作業開始ボタン ---
        start_btn = ttk.Button(main_frame, text="▼ 作業開始 ▼", style="Action.TButton", command=self._start_process)
        start_btn.pack(pady=10)
        
        # --- ステージ進行エリア ---
        self.stage_frame = ttk.LabelFrame(main_frame, text=" 処理ステータス ", padding="10")
        self.stage_frame.pack(fill=tk.BOTH, expand=True)
        
        # process_specification.md に基づく全工程
        self.stages = [
            {"name": "1. 更新除外データの削除", "status_var": tk.StringVar(value="未実行"), "btn_text": "内容確認 → Stage 2へ"},
            {"name": "2. 取り寄せ品の除外", "status_var": tk.StringVar(value="未実行"), "btn_text": "内容確認 → Stage 3へ"},
            {"name": "3. 医薬品の除外", "status_var": tk.StringVar(value="未実行"), "btn_text": "内容確認 → Stage 4へ"},
            {"name": "4. 特定文字列の削除", "status_var": tk.StringVar(value="未実行"), "btn_text": "内容確認 → Stage 5へ"},
            {"name": "5. 送料無料の付与 (楽天)", "status_var": tk.StringVar(value="未実行"), "btn_text": "内容確認 → Stage 6へ"},
            {"name": "6. イベント別キーワード付与 (楽天)", "status_var": tk.StringVar(value="未実行"), "btn_text": "内容確認 → Stage 7へ"},
            {"name": "7. 文字数制限の調整 (楽天)", "status_var": tk.StringVar(value="未実行"), "btn_text": "内容確認 → Stage 8へ"},
            {"name": "8. 最終フォーマット調整", "status_var": tk.StringVar(value="未実行"), "btn_text": "作業終了 (次工程へ)"},
        ]
        
        self.stage_buttons = []
        for i, stage in enumerate(self.stages):
            frame = ttk.Frame(self.stage_frame)
            frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(frame, text=stage["name"], width=30, anchor="w").pack(side=tk.LEFT, padx=5)
            ttk.Label(frame, textvariable=stage["status_var"], width=10, anchor="center").pack(side=tk.LEFT, padx=5)
            
            btn = ttk.Button(frame, text=stage["btn_text"], state=tk.DISABLED, 
                             command=lambda idx=i: self._confirm_stage(idx))
            btn.pack(side=tk.RIGHT, padx=5)
            self.stage_buttons.append(btn)

    def _select_base_file(self):
        filepath = filedialog.askopenfilename(
            title="ベースファイルを選択",
            filetypes=[("Excel Files", "*.xlsx"), ("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if filepath:
            self.base_file_path.set(filepath)

    def _select_config_file(self):
        filepath = filedialog.askopenfilename(
            title="案件設定ファイルを選択",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if filepath:
            self.config_file_path.set(filepath)

    def _start_process(self):
        """全体の処理を開始し、Stage1を実行する"""
        if not self.base_file_path.get() or not self.config_file_path.get():
            messagebox.showwarning("確認", "対象ファイルと案件設定ファイル(JSON)を選択してください。")
            # 実際の環境では return させますが、テスト用にコメントアウト可能
            # return
            
        logger.info("作業を開始します。")
        messagebox.showinfo("開始", "処理を開始します。\n（実際のロジック連携は後ほど実装します）")
        
        # Stage1完了の状態をシミュレート
        self.stages[0]["status_var"].set("処理完了")
        self.stage_buttons[0].config(state=tk.NORMAL)

    def _confirm_stage(self, stage_index):
        """各ステージの確認ボタンが押されたときの処理"""
        # 該当ステージの中間ファイルを開く処理などをここに実装
        logger.info(f"Stage {stage_index + 1} のファイルを確認しています...")
        
        messagebox.showinfo("確認", f"Stage {stage_index + 1} の中間データファイルを開きます。\n確認後、OKを押すと次のステージへ進みます。")
        
        # 次のステージがあれば実行をシミュレート
        next_index = stage_index + 1
        if next_index < len(self.stages):
            self.stages[next_index]["status_var"].set("処理完了")
            self.stage_buttons[next_index].config(state=tk.NORMAL)
            self.stage_buttons[stage_index].config(state=tk.DISABLED) # 現在のボタンは無効化
        else:
            messagebox.showinfo("完了", "すべての前処理が完了しました！\n次工程（佐々木exe）へ進みます。")
            self.stage_buttons[stage_index].config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = UploadDataCreateApp(root)
    root.mainloop()
