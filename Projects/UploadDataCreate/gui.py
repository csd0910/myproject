import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
from pathlib import Path
import pandas as pd
from main import DataProcessor
import os
import threading

# ロガー設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class UploadDataCreateWizard:
    def __init__(self, root):
        self.root = root
        self.root.title("UploadDataCreate 対話型アシスタント")
        self.root.geometry("900x700")
        
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure("TFrame", background="#f4f7f6")
        style.configure("TLabel", background="#f4f7f6", font=("Meiryo UI", 10))
        style.configure("Flow.TLabel", background="white", font=("Meiryo UI", 9))
        style.configure("Action.TButton", font=("Meiryo UI", 11, "bold"), padding=10)
        
        self.root.configure(bg="#f4f7f6")
        
        self.base_file_path = tk.StringVar()
        self.config_file_path = tk.StringVar()
        self.file_stage1 = tk.StringVar()
        self.file_stage2 = tk.StringVar()
        self.file_stage5 = tk.StringVar()
        self.file_stage6 = tk.StringVar()
        self.output_dir = Path("output")
        self.processor = None
        self.current_stage = 0
        self.stages_info = [
            {
                "methods": ["stage1_remove_exclude"], 
                "name": "【手順1】 更新除外データの削除",
                "desc": "「更新除外（品目）」および「更新除外（注文番号）」リストと突き合わせ、該当する行を削除します。"
            },
            {
                "methods": ["stage2_remove_stock_order", "stage3_remove_medicine", "stage4_remove_specific_string"], 
                "name": "【手順2～7 一括処理】 キーワード・医薬品等の除外",
                "desc": "111取り寄せの有効在庫など不要な品目、第2類・第3類などの医薬品、および【※】等の特定の不要文字が含まれる商品を判別し、一括でリストから削除します。"
            },
            {
                "methods": ["stage5_add_free_shipping"], 
                "name": "【手順8】 送料無料の付与 (楽天用)",
                "desc": "「111倉庫_売価変更用」のリストと突き合わせ、条件に合致する商品の特定列に【送料無料】の文字を追加します。"
            },
            {
                "methods": ["stage6_add_event_keyword"], 
                "name": "【手順9】 イベント別キーワード付与",
                "desc": "「イベント別キーワード一覧」と照合し、商品名などの頭に指定されたイベント用のキーワードを自動で付加します。"
            },
            {
                "methods": ["stage7_truncate_bytes", "stage8_final_format"], 
                "name": "【手順10】 バイト数調整・最終フォーマット整形",
                "desc": "楽天のアップロード仕様に合わせて文字数（全角・半角のバイト数）を計算し、制限を超えないように調整した上で、最終的なCSV用フォーマットに整形出力します。"
            }
        ]
        

        self.flow_labels = []
        
        self._create_widgets()
        self._auto_detect_files()
        
    def _create_widgets(self):
        # --- ノートブック（タブ）の作成 ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.tab_main = ttk.Frame(self.notebook, padding="10")
        self.tab_settings = ttk.Frame(self.notebook, padding="10")
        
        self.notebook.add(self.tab_main, text=" 実行 (Execution) ")
        self.notebook.add(self.tab_settings, text=" 設定 (Settings) ")
        
        self._build_main_tab()
        self._build_settings_tab()
        
    def _build_main_tab(self):
        # 画面上部: ファイル選択 ＆ メインアクション
        top_frame = ttk.Frame(self.tab_main)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 左側: ファイル選択エリア
        file_frame = ttk.LabelFrame(top_frame, text=" 準備 (ファイルのセット) ", padding="10")
        file_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(file_frame, text="対象ファイル:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(file_frame, textvariable=self.base_file_path, width=70).grid(row=0, column=1, padx=5)
        ttk.Button(file_frame, text="参照...", command=lambda: self._select_file(self.base_file_path, [("Excel", "*.xlsx")])).grid(row=0, column=2)
        
        ttk.Label(file_frame, text="[Stage1] 除外 (例: 社外キーワード追加対応):").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(file_frame, textvariable=self.file_stage1, width=70).grid(row=1, column=1, padx=5)
        ttk.Button(file_frame, text="参照...", command=lambda: self._select_file(self.file_stage1, [("Excel", "*.xlsx"), ("CSV", "*.csv")])).grid(row=1, column=2)

        ttk.Label(file_frame, text="[Stage2] 除外 (例: 111取り寄せ＋有効在庫):").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(file_frame, textvariable=self.file_stage2, width=70).grid(row=2, column=1, padx=5)
        ttk.Button(file_frame, text="参照...", command=lambda: self._select_file(self.file_stage2, [("Excel", "*.xlsx"), ("CSV", "*.csv")])).grid(row=2, column=2)

        ttk.Label(file_frame, text="[Stage5] 送料無料付与 (例: 111倉庫_売価変更用):").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(file_frame, textvariable=self.file_stage5, width=70).grid(row=3, column=1, padx=5)
        ttk.Button(file_frame, text="参照...", command=lambda: self._select_file(self.file_stage5, [("CSV", "*.csv"), ("Excel", "*.xlsx")])).grid(row=3, column=2)

        ttk.Label(file_frame, text="[Stage6] キーワードマスタ (例: イベント別キーワード一覧):").grid(row=4, column=0, sticky="w", pady=2)
        ttk.Entry(file_frame, textvariable=self.file_stage6, width=70).grid(row=4, column=1, padx=5)
        ttk.Button(file_frame, text="参照...", command=lambda: self._select_file(self.file_stage6, [("Excel", "*.xlsx")])).grid(row=4, column=2)
        
        # 右側: アクションボタンエリア (右上へ移動)
        self.action_frame = ttk.LabelFrame(top_frame, text=" メイン操作 ", padding="10")
        self.action_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        self.progress = ttk.Progressbar(self.action_frame, mode='indeterminate')
        
        self.btn_primary = ttk.Button(self.action_frame, text="データの読み込みを開始", style="Action.TButton", command=self._start_process)
        self.btn_primary.pack(fill=tk.X, pady=5)
        
        self.btn_secondary = ttk.Button(self.action_frame, text="比較ファイルを開く", command=self._open_diff_file)
        # 初期状態ではpackしない

        # --- 中央エリア (フロー表示 ＆ チャット) ---
        center_frame = ttk.Frame(self.tab_main)
        center_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 左側: 処理フロー
        flow_frame = ttk.LabelFrame(center_frame, text=" 全体の処理フロー ", padding="5")
        flow_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        self.flow_labels = []
        for i, stage in enumerate(self.stages_info):
            f = ttk.Frame(flow_frame)
            f.pack(fill=tk.X, pady=2)
            lbl = tk.Label(f, text="[未実行] " + stage["name"], bg="white", fg="gray", font=("Meiryo UI", 9), anchor="w", width=30, padx=5)
            lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.flow_labels.append(lbl)
            
            # 各工程ごとの「確認」ボタンを追加
            btn = ttk.Button(f, text="確認", width=4, command=lambda idx=i: self._open_stage_file_by_idx(idx))
            btn.pack(side=tk.RIGHT, padx=2)
            
        # 右側: 対話/ログエリア ＆ プレビューエリア
        right_pane = ttk.PanedWindow(center_frame, orient=tk.VERTICAL)
        right_pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 上部: 進行アシスタント（ログ）
        chat_frame = ttk.LabelFrame(right_pane, text=" 進行アシスタント ", padding="5")
        right_pane.add(chat_frame, weight=1)
        
        self.log_text = tk.Text(chat_frame, wrap=tk.WORD, font=("Meiryo UI", 10), bg="white", state=tk.DISABLED, spacing1=3, spacing3=3, height=8)
        scrollbar = ttk.Scrollbar(chat_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 下部: データプレビューエリア（Excel風）
        preview_frame = ttk.LabelFrame(right_pane, text=" データプレビュー (先頭1000件) ", padding="5")
        right_pane.add(preview_frame, weight=2)
        
        self.tree = ttk.Treeview(preview_frame, show="headings")
        
        # 縦スクロール
        vsb = ttk.Scrollbar(preview_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        # 横スクロール
        hsb = ttk.Scrollbar(preview_frame, orient="horizontal", command=self.tree.xview)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self._add_log("システム", "こんにちは！UploadData作成アシスタントです。\n「設定」タブから出力先モール等の設定が行えます。\n準備ができたら開始ボタンを押してください。")

    def _build_settings_tab(self):
        # サイト設定
        site_frame = ttk.LabelFrame(self.tab_settings, text=" ターゲットサイト設定 ", padding="10")
        site_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(site_frame, text="出力先モール:").grid(row=0, column=0, sticky="w", pady=5)
        self.site_combo = ttk.Combobox(site_frame, values=["楽天 (255バイト制限)"], state="readonly", width=30)
        self.site_combo.current(0)
        self.site_combo.grid(row=0, column=1, padx=10, pady=5)
        
        # イベント設定
        event_frame = ttk.LabelFrame(self.tab_settings, text=" 出力イベント（シート名）設定 ", padding="10")
        event_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        ttk.Label(event_frame, text="※ここで設定した名前で、ファイル・シートが分割出力されます。").pack(anchor="w", pady=(0, 5))
        
        # リストボックスとスクロールバー
        list_frame = ttk.Frame(event_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.event_listbox = tk.Listbox(list_frame, font=("Meiryo UI", 10), selectmode=tk.SINGLE)
        self.event_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ev_scroll = ttk.Scrollbar(list_frame, command=self.event_listbox.yview)
        ev_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.event_listbox.configure(yscrollcommand=ev_scroll.set)
        
        # コントロール
        ctrl_frame = ttk.Frame(event_frame)
        ctrl_frame.pack(fill=tk.X, pady=5)
        
        self.new_event_var = tk.StringVar()
        ttk.Entry(ctrl_frame, textvariable=self.new_event_var, width=30).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(ctrl_frame, text="追加", command=self._add_event).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_frame, text="選択したイベントを削除", command=self._delete_event).pack(side=tk.RIGHT)
        
        # JSONから初期値ロード
        self._load_settings_from_json()
        
    def _add_event(self):
        val = self.new_event_var.get().strip()
        if val and val not in self.event_listbox.get(0, tk.END):
            self.event_listbox.insert(tk.END, val)
            self.new_event_var.set("")
            self._save_settings_to_json()
            
    def _delete_event(self):
        selection = self.event_listbox.curselection()
        if selection:
            self.event_listbox.delete(selection[0])
            self._save_settings_to_json()
            
    def _load_settings_from_json(self):
        self.config_path = self.output_dir / "events.json"
        if not self.config_path.parent.exists():
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
        events = ["目玉", "その他"] # デフォルト
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    events = data.get("events", events)
            except:
                pass
                
        for ev in events:
            self.event_listbox.insert(tk.END, ev)
            
        # 起動時からパスをセットしておく
        self.config_file_path.set(str(self.config_path))
            
    def _save_settings_to_json(self):
        events = list(self.event_listbox.get(0, tk.END))
        data = {"events": events, "target_site": "楽天"}
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        # 設定ファイルのパスを変数にセットしておく
        self.config_file_path.set(str(self.config_path))

    def _update_flow_ui(self, index, status):
        lbl = self.flow_labels[index]
        name = self.stages_info[index]["name"]
        if status == "active":
            lbl.config(text=f"▶ [実行中] {name}", fg="blue", font=("Meiryo UI", 10, "bold"), bg="#e6f2ff")
        elif status == "done":
            lbl.config(text=f"✔ [完了済] {name}", fg="green", font=("Meiryo UI", 10, "bold"), bg="#e6ffe6")

    def _add_log(self, sender, message):
        self.log_text.config(state=tk.NORMAL)
        icon = "🤖" if sender == "システム" else "⚠️" if sender == "エラー" else "👤"
        self.log_text.insert(tk.END, f"{icon} 【{sender}】\n{message}\n\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _update_preview(self, file_path=None):
        """保存されたExcelファイルを直接読み込んでTreeviewに表示する（内容のズレ防止）"""
        if not file_path or not os.path.exists(file_path):
            self._add_log("システム", "プレビューの対象ファイルがまだ生成されていません。")
            return
            
        try:
            df = pd.read_excel(file_path)
            if df.empty:
                return
                
            # 既存のデータをクリア
            self.tree.delete(*self.tree.get_children())
            
            # ヘッダーの設定（重複カラムエラー対策）
            unique_cols = []
            seen = set()
            for c in df.columns:
                new_c = str(c)
                while new_c in seen:
                    new_c += "_"
                seen.add(new_c)
                unique_cols.append(new_c)
                
            self.tree["columns"] = unique_cols
            for col in unique_cols:
                self.tree.heading(col, text=col)
                self.tree.column(col, width=100, anchor=tk.W) # 初期幅
                
            # データの追加（最大1000行）
            preview_limit = 1000
            preview_df = df.head(preview_limit)
            
            for idx, row in preview_df.iterrows():
                row_values = [str(x) if pd.notnull(x) else "" for x in row.tolist()]
                self.tree.insert("", tk.END, values=row_values)
                
        except Exception as e:
            logger.error(f"プレビュー更新エラー: {e}")
            self._add_log("エラー", f"プレビューの描画に失敗しました。\n詳細: {e}")

    def _auto_detect_files(self):
        # 実行フォルダ配下の「元データ」フォルダ、またはカレントディレクトリを探す
        base_dir = Path("元データ")
        if not base_dir.exists():
            base_dir = Path.cwd()
            
        if base_dir.exists():
            for f in base_dir.glob("result_*.xlsx"):
                self.base_file_path.set(str(f))
                self._add_log("システム", f"自動検出: 対象ファイルとして {f.name} をセットしました。")
                break
                
        json_path = Path("events.json")
        if not json_path.exists():
            json_path = self.output_dir / "events.json"
        if json_path.exists():
            self.config_file_path.set(str(json_path))

    def _select_file(self, var, filetypes):
        filepath = filedialog.askopenfilename(title="ファイルを選択", filetypes=filetypes + [("All", "*.*")])
        if filepath: var.set(filepath)

    def _open_temp_file(self):
        if self.current_stage == 0: return
        if self.current_stage >= len(self.stages_info):
            temp_file = self.output_dir / "normal_item_result.xlsx"
        else:
            temp_file = self.output_dir / f"temp_stage{self.current_stage}.xlsx"
            
        if temp_file.exists():
            os.startfile(str(temp_file))
            self._add_log("システム", f"{temp_file.name} を開きました。")
        else:
            messagebox.showwarning("警告", "ファイルが見つかりません。")

    def _check_thread(self, thread, callback):
        """別スレッドの終了を監視し、終わったらcallbackを呼ぶ"""
        if thread.is_alive():
            self.root.after(100, self._check_thread, thread, callback)
        else:
            callback()

    def _start_process(self):
        if not self.base_file_path.get():
            messagebox.showerror("エラー", "対象ファイルを選択してください。")
            return
            
        self.btn_primary.config(state=tk.DISABLED)
        self._add_log("あなた", "データの読み込みを開始して！")
        
        # プログレスバー（待機スピナー）を表示して回す
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.progress.start(10)
        
        thread = threading.Thread(target=self._thread_load_data)
        thread.start()
        self.root.after(100, self._check_thread, thread, self._post_load_data)

    def _thread_load_data(self):
        try:
            self.processor = DataProcessor(
                self.base_file_path.get(), 
                self.config_file_path.get(), 
                self.output_dir,
                file_stage1=self.file_stage1.get(),
                file_stage2=self.file_stage2.get(),
                file_stage5=self.file_stage5.get(),
                file_stage6=self.file_stage6.get()
            )
            self.processor.load_data()
            self.thread_error = None
        except Exception as e:
            self.thread_error = e

    def _post_load_data(self):
        self.progress.stop()
        self.progress.pack_forget()
        
        if getattr(self, 'thread_error', None):
            self._add_log("エラー", f"エラーが発生しました:\n{self.thread_error}")
            self.btn_primary.config(state=tk.NORMAL)
            return

        # JSON設定エラーの警告ダイアログ
        if getattr(self.processor, 'config_error', None):
            messagebox.showwarning("設定ファイルエラー", self.processor.config_error)
            self._add_log("エラー", f"⚠️ {self.processor.config_error}")

        count = len(self.processor.df_base)
        self._add_log("システム", f"読み込み完了（{count:,}件）。\n\n次は「{self.stages_info[0]['name']}」を行います。よろしいですか？")
        self.btn_primary.config(text="はい、進めます", command=self._run_next_stage, state=tk.NORMAL)
        self._update_flow_ui(0, "active")
        
        # プレビュー表示更新（読み込み時はベースファイルを直接表示）
        if self.base_file_path.get():
            self._update_preview(self.base_file_path.get())

    def _run_next_stage(self):
        if self.current_stage >= len(self.stages_info):
            return
            
        stage_info = self.stages_info[self.current_stage]
        methods = stage_info["methods"]
        stage_name = stage_info["name"]
        
        self.btn_primary.config(state=tk.DISABLED)
        self.btn_secondary.pack_forget()
        self._add_log("あなた", f"「{stage_name}」を実行して！")
        
        # 処理中スピナー表示
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.progress.start(10)
        
        thread = threading.Thread(target=self._thread_run_stage, args=(methods,))
        thread.start()
        self.root.after(100, self._check_thread, thread, self._post_run_stage)

    def _thread_run_stage(self, methods):
        try:
            self.before_count = len(self.processor.df_base)
            for m in methods:
                func = getattr(self.processor, m)
                func()
            self.after_count = len(self.processor.df_base)
            self.thread_error = None
        except Exception as e:
            self.thread_error = e

    def _post_run_stage(self):
        self.progress.stop()
        self.progress.pack_forget()
        
        if getattr(self, 'thread_error', None):
            self._add_log("エラー", f"エラーが発生しました:\n{self.thread_error}")
            self.btn_primary.config(state=tk.NORMAL)
            return

        diff = self.before_count - self.after_count
        stage_name = self.stages_info[self.current_stage]["name"]
        
        self._update_flow_ui(self.current_stage, "done")
        stage_num = self.current_stage + 1
        self.current_stage += 1
        
        msg = f"【完了】{stage_name}\n"
        if diff > 0:
            msg += f"データが {self.after_count:,}件 になりました（{diff:,}件 除外）。\n"
        else:
            msg += f"件数に変更なし（現在 {self.after_count:,}件）。\n"
            
        # 差分比較の実行
        try:
            import color_diff
            ojima_file = Path(rf"C:\Users\フォーレスト026\MyProject\UploadDataCreate\【テスト用】商品名作成 尾島手作業\【手順{stage_num}】result_260819_154419.xlsx")
            temp_file = self.output_dir / f"temp_stage{stage_num}.xlsx"
            diff_file = self.output_dir / f"diff_stage{stage_num}.xlsx"
            
            # 前工程のファイルパス
            if stage_num == 1:
                prev_temp_file = Path(self.base_file_path.get())
            else:
                prev_temp_file = self.output_dir / f"temp_stage{stage_num - 1}.xlsx"
            
            if ojima_file.exists() and temp_file.exists():
                success, diff_msg = color_diff.generate_diff_excel(str(prev_temp_file), str(temp_file), str(ojima_file), str(diff_file))
                if success:
                    msg += f"\n📊 自動比較結果:\n{diff_msg}\n"
                    # 中間ファイル確認ボタンで開く対象を差分ファイルに変更する
                    self.last_diff_file = diff_file
        except Exception as e:
            logger.error(f"差分チェックエラー: {e}")
            
        if self.current_stage < len(self.stages_info):
            next_name = self.stages_info[self.current_stage]["name"]
            next_desc = self.stages_info[self.current_stage]["desc"]
            self._update_flow_ui(self.current_stage, "active")
            msg += f"\n色付けされた比較ファイルを出力しました。確認しますか？\n\n↓↓↓ 次の工程へ進む ↓↓↓\n「{next_name}」を行います。\n\n【📝 処理内容】\n{next_desc}"
            
            self.btn_primary.config(text=f"次へ ({next_name})", state=tk.NORMAL)
            self.btn_secondary.config(text="比較ファイルを開いて確認", command=self._open_diff_file)
            self.btn_secondary.pack(side=tk.RIGHT, padx=5)
        else:
            msg += f"\n🎉 すべての処理が完了しました！\n{self.output_dir.name} フォルダ内に normal_item_result.xlsx が作成されました。"
            self.btn_primary.config(text="完了", state=tk.DISABLED)
            self.btn_secondary.config(text="最終ファイルを開く", command=self._open_temp_file)
            self.btn_secondary.pack(side=tk.RIGHT, padx=5)
            
        self._add_log("システム", msg)
        
        # プレビュー表示更新（メモリからではなく、実際に出力されたファイルから読み込む）
        preview_target = None
        if hasattr(self, 'last_diff_file') and self.last_diff_file.exists():
            preview_target = str(self.last_diff_file)
        elif self.current_stage <= len(self.stages_info):
            # temp_stageX.xlsx があればそれを表示
            stage_num = self.current_stage # すでに += 1 されているのでこの時点での stage_num は今終わったステージ
            temp_file = self.output_dir / f"temp_stage{stage_num}.xlsx"
            if temp_file.exists():
                preview_target = str(temp_file)
        
        if preview_target:
            self._update_preview(preview_target)

    def _open_diff_file(self):
        if hasattr(self, 'last_diff_file') and self.last_diff_file.exists():
            os.startfile(str(self.last_diff_file))
            self._add_log("システム", f"{self.last_diff_file.name} を開きました。")
        else:
            # 差分ファイルが無ければ通常の中間ファイルを開くフォールバック
            self._open_temp_file()

    def _open_stage_file_by_idx(self, idx):
        stage_num = idx + 1
        diff_file = self.output_dir / f"diff_stage{stage_num}.xlsx"
        temp_file = self.output_dir / f"temp_stage{stage_num}.xlsx"
        
        if diff_file.exists():
            os.startfile(str(diff_file))
            self._add_log("システム", f"{diff_file.name} を開きました。")
        elif temp_file.exists():
            os.startfile(str(temp_file))
            self._add_log("システム", f"{temp_file.name} を開きました。")
        else:
            messagebox.showwarning("ファイルなし", f"Stage {stage_num} の出力ファイルがまだありません。")

if __name__ == "__main__":
    root = tk.Tk()
    app = UploadDataCreateWizard(root)
    root.mainloop()
