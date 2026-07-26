import os
import sys
import json
import urllib.request
import base64
import re
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

# 依存ライブラリの自動チェックおよびインストール
def install_dependencies():
    required_libs = {
        "win32com": "pywin32",
        "pypdf": "pypdf",
        "PIL": "Pillow",
        "windnd": "windnd"
    }
    for module_name, pip_name in required_libs.items():
        try:
            __import__(module_name)
        except ImportError:
            import subprocess
            print(f"必要なライブラリ {pip_name} をインストールしています...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
            except Exception as e:
                print(f"インストール失敗: {pip_name}, エラー: {e}")

install_dependencies()

import win32com.client
from pypdf import PdfReader, PdfWriter
from PIL import Image

# ドラッグ＆ドロップ用ライブラリが利用可能かチェック
WINDND_AVAILABLE = False
try:
    import windnd
    WINDND_AVAILABLE = True
except ImportError:
    pass

# 定数と設定ファイルのパス
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ringi_config.json")
DEFAULT_TEMPLATE_DIR = r"C:\Users\フォーレスト026\Desktop\伊藤作業用"
DEFAULT_OUTPUT_DIR = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\006.稟議書\2024年4月～2025年3月"


def split_text_by_chars(text, max_chars):
    """
    全角・半角を問わず、文字数ベースで最大文字数ごとに改行を挿入してリスト化する。
    """
    lines = []
    for line in text.split('\n'):
        if not line:
            lines.append("")
            continue
        while len(line) > max_chars:
            lines.append(line[:max_chars])
            line = line[max_chars:]
        if line:
            lines.append(line)
    return lines

class RingiToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("稟議書作成・PDF結合システム")
        
        # 画面サイズ
        self.root.geometry("880x550")
        self.root.minsize(800, 450)
        
        # 設定のロード
        self.config = self.load_config()
        self.api_key = self.config.get("api_key", "")
        
        # 変数定義
        self.template_path_var = tk.StringVar()
        self.dept_var = tk.StringVar(value=self.config.get("default_dept", "システム運営課"))
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y年%m月%d日"))
        self.title_var = tk.StringVar(value=self.config.get("default_title", "取締役"))
        self.author_var = tk.StringVar(value=self.config.get("default_author", "伊藤 健人"))
        self.subject_var = tk.StringVar()
        self.mng_no_var = tk.StringVar()
        self.pay_date_var = tk.StringVar()
        self.pay_method_var = tk.StringVar(value="振込")
        
        # 詳細入力項目
        self.amount_ex_tax_var = tk.StringVar()
        self.amount_in_tax_var = tk.StringVar()
        self.amount_var = tk.StringVar()        
        self.purchase_var = tk.StringVar()       
        self.model_info_var = tk.StringVar()    
        self.delivery_date_var = tk.StringVar(value="別途打合せ")
        self.effect_var = tk.StringVar(value="業務継続性の確保およびトラブルの未然防止")
        
        # 添付ファイル
        self.attached_images = []
        self.attached_pdf = ""
        self.use_case_var = tk.StringVar(value="✨ カスタム (自由に手書き)")
        self.last_saved_excel_path = None
        

        
        self.setup_styles()
        self.create_widgets()
        self.reload_templates()
        
        # ドラッグ＆ドロップのフックを登録 (クラッシュ防止のためafter経由で安全に実行)
        if WINDND_AVAILABLE:
            try:
                windnd.hook_dropfiles(self.root, func=self.handle_dropfiles)
            except Exception as e:
                print(f"ドラッグ＆ドロップ登録失敗: {e}")
        
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
        
    def save_config(self):
        config_data = {
            "api_key": self.api_key,
            "default_dept": self.dept_var.get(),
            "default_title": self.title_var.get(),
            "default_author": self.author_var.get()
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"設定保存エラー: {e}")

    def setup_styles(self):
        self.bg_window = ("#F1F5F9", "#1E293B")
        self.bg_card = ("#FFFFFF", "#0F172A")
        self.color_primary = ("#1E293B", "#F8FAFC")
        self.color_border = ("#E2E8F0", "#334155")
        self.color_accent = "#0F766E"
        self.color_accent_hover = "#115E59"
        self.color_info = "#0284C7"
        self.color_info_hover = "#0369A1"
        self.color_success = "#059669"
        self.color_success_hover = "#047857"


    def create_card(self, parent, title):
        card = ctk.CTkFrame(parent, fg_color=("gray95", "gray15"), corner_radius=10)
        
        title_lbl = ctk.CTkLabel(card, text=title, font=("Meiryo", 14, "bold"), anchor="w")
        title_lbl.pack(fill=ctk.X, padx=15, pady=(10, 5))
        
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill=ctk.BOTH, expand=True, padx=15, pady=(0, 10))
        
        return card, content

    def _old_create_card(self, parent, title):
        card = ctk.CTkFrame(parent, fg_color="transparent", highlightbackground=self.color_border)
        
        header = ctk.CTkFrame(card, fg_color="#F8FAFC", height=32)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)
        
        title_lbl = tk.Label(header, text=title, font=("Meiryo", 9, "bold"), fg="#1E293B", bg="#F8FAFC", anchor="w")
        title_lbl.pack(fill=tk.BOTH, expand=True, padx=12)
        
        content = ctk.CTkFrame(card, fg_color="transparent", padx=12, pady=10)
        content.pack(fill=tk.BOTH, expand=True)
        
        return card, content

    def create_widgets(self):
        # 1. ヘッダーバー
        header_bar = ctk.CTkFrame(self.root, fg_color="#1f538d", height=55)
        header_bar.pack(fill=tk.X, side=tk.TOP)
        header_bar.pack_propagate(False)
        
        header_title = ctk.CTkLabel(
            header_bar, 
            text="稟議書作成・提出PDF自動結合システム", 
            font=("Meiryo", 14, "bold"), 
            text_color="#FFFFFF",
            anchor="w"
        )
        header_title.pack(fill=tk.BOTH, expand=True, padx=20)
        
        # スクロール可能なメインエリア (CTkScrollableFrame)
        self.scrollable_frame = ctk.CTkScrollableFrame(self.root, fg_color="transparent")
        self.scrollable_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)
        
        # ==========================================
        # CARD 1: 設定 & テンプレート (最上部・スリム化横並び)
        # ==========================================
        card1, body1 = self.create_card(self.scrollable_frame, "🔧 1. システム設定 & テンプレート選択")
        card1.pack(fill=tk.X, pady=(0, 10))
        
        # 横に1行でスリムに並べる
        body1.columnconfigure(1, weight=1)
        body1.columnconfigure(3, weight=1)
        
        ctk.CTkLabel(body1, text="APIキー:", ).grid(row=0, column=0, sticky=tk.W, padx=5, pady=4)
        self.api_entry = ctk.CTkEntry(body1, show="*", width=180)
        self.api_entry.insert(0, self.api_key)
        self.api_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=4)
        
        def save_api():
            self.api_key = self.api_entry.get().strip()
            self.save_config()
            messagebox.showinfo("保存完了", "Gemini APIキーを安全に保存しました。")
            
        save_api_btn = self.create_flat_button(body1, "キー保存", "#1f538d", "#334155", save_api)
        save_api_btn.grid(row=0, column=2, padx=5, pady=4)
        
        ctk.CTkLabel(body1, text="テンプレートExcel:", ).grid(row=0, column=3, sticky=tk.W, padx=5, pady=4)
        self.tpl_combo = ctk.CTkComboBox(body1, width=220, command=self.on_template_combo_change)
        self.tpl_combo.grid(row=0, column=4, sticky=tk.W, padx=5, pady=4)
        
        ref_tpl_btn = self.create_flat_button(body1, "参照...", "#64748B", "#475569", self.select_template_file)
        ref_tpl_btn.grid(row=0, column=5, padx=5, pady=4)
        
        # 📁 用途テンプレートの追加
        ctk.CTkLabel(body1, text="用途テンプレート:", ).grid(row=1, column=0, sticky=tk.W, padx=5, pady=4)
        self.use_case_combo = ctk.CTkComboBox(
            body1, 
            width=180, 
            variable=self.use_case_var,
            values=[
                "✨ カスタム (自由に手書き)",
                "💻 パソコン購入・更新",
                "🖥️ ディスプレイ・モニター購入",
                "🔌 周辺機器・ネットワーク機器",
                "💿 ソフトウェア・ライセンス"
            ],
            command=self.on_use_case_change
        )
        self.use_case_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=4)

        # ==========================================
        # 上部横並びコンテナ (起案データ入力 ＆ 添付ファイル自動読込)
        # ==========================================
        top_container = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        top_container.pack(fill=tk.X, pady=(0, 10))
        
        # グリッドの列比率
        top_container.columnconfigure(0, weight=1)
        top_container.columnconfigure(1, weight=1)
        
        # 上部左: 3. 稟議起案データ入力
        top_left = ctk.CTkFrame(top_container, fg_color="transparent")
        top_left.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 5))
        
        # 上部右: 2. 見積書・参考資料の添付 ＆ 自動読込
        top_right = ctk.CTkFrame(top_container, fg_color="transparent")
        top_right.grid(row=0, column=1, sticky=tk.NSEW, padx=(5, 0))

        # --- [左半分] CARD 2: 稟議起案データ入力 ---
        card2 = ctk.CTkFrame(top_left, fg_color=("white", "gray15"), corner_radius=10)
        card2.pack(fill=tk.BOTH, expand=True)
        
        ctk.CTkLabel(card2, text="📝 3. 稟議起案データ入力", font=("Meiryo", 13, "bold"), anchor="w").pack(fill=ctk.X, padx=12, pady=(8, 3))
        body2 = ctk.CTkFrame(card2, fg_color="transparent")
        body2.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        
        body2.columnconfigure(1, weight=1)
        body2.columnconfigure(3, weight=1)
        
        fields = [
            ("起案部署名:", self.dept_var, 0, 0),
            ("申請年月日:", self.date_var, 0, 2),
            ("役職:", self.title_var, 1, 0),
            ("起案者名:", self.author_var, 1, 2),
        ]
        
        for label_text, var, r, c in fields:
            ctk.CTkLabel(body2, text=label_text, font=("Meiryo", 9)).grid(row=r, column=c, sticky=tk.W, padx=3, pady=2)
            ent = ctk.CTkEntry(body2, textvariable=var, height=22, font=("Meiryo", 9))
            ent.grid(row=r, column=c+1, sticky=tk.EW, padx=3, pady=2)
            
        ctk.CTkLabel(body2, text="件名:", font=("Meiryo", 9)).grid(row=2, column=0, sticky=tk.W, padx=3, pady=4)
        self.subject_ent = ctk.CTkEntry(body2, textvariable=self.subject_var, height=22, font=("Meiryo", 9))
        self.subject_ent.grid(row=2, column=1, columnspan=3, sticky=tk.EW, padx=3, pady=4)

        # --- [右半分] CARD 5: 添付資料 ＆ 自動読込 (★ここに移動) ---
        card5 = ctk.CTkFrame(top_right, fg_color=("white", "gray15"), corner_radius=10)
        card5.pack(fill=tk.BOTH, expand=True)
        
        ctk.CTkLabel(card5, text="📎 2. 見積書・参考資料の添付 ＆ 自動読込", font=("Meiryo", 13, "bold"), anchor="w").pack(fill=ctk.X, padx=12, pady=(8, 3))
        body5 = ctk.CTkFrame(card5, fg_color="transparent")
        body5.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        
        # 横並びレイアウト用のフレーム
        main_layout = ctk.CTkFrame(body5, fg_color="transparent")
        main_layout.pack(fill=tk.X)
        
        # 超スリム化されたドラッグ＆ドロップエリア
        self.dnd_frame = ctk.CTkFrame(
            main_layout, 
            fg_color="#F1F5F9", 
            border_width=1,
            border_color="#CBD5E1",
            height=36,
            cursor="hand2"
        )
        self.dnd_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.dnd_frame.pack_propagate(False)
        
        dnd_title = tk.Label(
            self.dnd_frame, 
            text="📥 ドロップまたはクリックして見積書を添付", 
            font=("Meiryo", 8, "bold"), 
            fg="#475569", 
            bg="#F1F5F9",
            cursor="hand2"
        )
        dnd_title.pack(fill=tk.BOTH, expand=True, pady=6)
        
        def on_dnd_click(event):
            self.click_select_file()
        self.dnd_frame.bind("<Button-1>", on_dnd_click)
        dnd_title.bind("<Button-1>", on_dnd_click)
        
        ocr_btn = self.create_flat_button(
            main_layout, 
            "🔍 自動読込実行", 
            "#0284c7", 
            "#0369a1", 
            self.analyze_attached_file
        )
        ocr_btn.pack(side=tk.RIGHT, padx=2)
        
        status_frame = ctk.CTkFrame(body5, fg_color="transparent")
        status_frame.pack(fill=tk.X, pady=(4, 0))
        
        self.img_page_var = tk.StringVar(value="2ページ目")
        self.pdf_page_var = tk.StringVar(value="3ページ目")
        
        # 添付画像行
        img_row = ctk.CTkFrame(status_frame, fg_color="transparent")
        img_row.pack(fill=tk.X, pady=1)
        ctk.CTkLabel(img_row, text="📸 画像:", width=50, anchor="w", font=("Meiryo", 9)).pack(side=tk.LEFT)
        self.img_lbl = ctk.CTkLabel(img_row, text="選択されていません", text_color="gray", fg_color="transparent", font=("Meiryo", 8), anchor="w")
        self.img_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        ctk.CTkComboBox(img_row, variable=self.img_page_var, values=["2ページ目", "3ページ目", "4ページ目", "挿入しない"], width=80, height=20, font=("Meiryo", 8)).pack(side=tk.LEFT, padx=2)
        self.create_flat_button(img_row, "選択", "#64748B", "#475569", self.select_images).pack(side=tk.LEFT, padx=1)
        self.create_flat_button(img_row, "取消", "#EF4444", "#DC2626", lambda: self.clear_attachment("image")).pack(side=tk.LEFT, padx=1)
        
        # 添付PDF行
        pdf_row = ctk.CTkFrame(status_frame, fg_color="transparent")
        pdf_row.pack(fill=tk.X, pady=1)
        ctk.CTkLabel(pdf_row, text="📄 PDF:", width=50, anchor="w", font=("Meiryo", 9)).pack(side=tk.LEFT)
        self.pdf_lbl = ctk.CTkLabel(pdf_row, text="選択されていません", text_color="gray", fg_color="transparent", font=("Meiryo", 8), anchor="w")
        self.pdf_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        ctk.CTkComboBox(pdf_row, variable=self.pdf_page_var, values=["2ページ目", "3ページ目", "4ページ目", "結合しない"], width=80, height=20, font=("Meiryo", 8)).pack(side=tk.LEFT, padx=2)
        self.create_flat_button(pdf_row, "選択", "#64748B", "#475569", self.select_pdf).pack(side=tk.LEFT, padx=1)
        self.create_flat_button(pdf_row, "取消", "#EF4444", "#DC2626", lambda: self.clear_attachment("pdf")).pack(side=tk.LEFT, padx=1)

        # ==========================================
        # 中部横並びコンテナ (起案目的 Area 1 ＆ 導入の目的 Area 2)
        # ==========================================
        columns_container = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        columns_container.pack(fill=tk.X, pady=(0, 10))
        
        columns_container.columnconfigure(0, weight=1)
        columns_container.columnconfigure(1, weight=1)
        
        # 左カラム: ① 起案目的・理由
        col_left = ctk.CTkFrame(columns_container, fg_color="transparent")
        col_left.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 5))
        
        # 右カラム: ② 導入の目的
        col_right = ctk.CTkFrame(columns_container, fg_color="transparent")
        col_right.grid(row=0, column=1, sticky=tk.NSEW, padx=(5, 0))

        # --- CARD 4: ① 起案目的・理由 [左カラム・青系] ---
        card4 = ctk.CTkFrame(col_left, fg_color=("#E0F2FE", "#0C4A6E"), corner_radius=10, border_width=1, border_color=("#38BDF8", "#0284C7"))
        card4.pack(fill=tk.BOTH, expand=True)
        
        ctk.CTkLabel(card4, text="📘 4. 【① 起案目的・理由】 (Area 1)", font=("Meiryo", 13, "bold"), text_color=("#0369A1", "#F0F9FF"), anchor="w").pack(fill=ctk.X, padx=12, pady=(8, 3))
        body4 = ctk.CTkFrame(card4, fg_color="transparent")
        body4.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        
        ctk.CTkLabel(body4, text="起案目的・理由文章 (最大6行・1行40文字制限):", text_color=("#0369A1", "#F0F9FF"), anchor="w").pack(fill=tk.X, pady=(2, 4))
        # 縦幅を 180 から 260 に大幅に広げる！
        self.reason_preview = ctk.CTkTextbox(body4, height=260, font=("Meiryo", 10))
        self.reason_preview.pack(fill=tk.BOTH, expand=True, pady=4)
        
        btn_frame = ctk.CTkFrame(body4, fg_color="transparent")
        btn_frame.pack(fill=tk.X, pady=(4, 0))
        
        ai_btn = self.create_flat_button(btn_frame, "✨ AI再生成", "#2fa572", "#106a43", self.generate_reason)
        ai_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        import_btn = self.create_flat_button(
            btn_frame, 
            "📂 過去稟議コピー", 
            "#3B82F6", 
            "#2563EB", 
            self.import_past_ringi_text
        )
        import_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # --- CARD 3-A: ② 導入の目的 [右カラム・橙系] ---
        card3_purpose = ctk.CTkFrame(col_right, fg_color=("#FFF7ED", "#451A03"), corner_radius=10, border_width=1, border_color=("#FDBA74", "#C2410C"))
        card3_purpose.pack(fill=tk.BOTH, expand=True)
        
        ctk.CTkLabel(card3_purpose, text="📙 5. 【② 導入の目的】 (Area 2)", font=("Meiryo", 13, "bold"), text_color=("#C2410C", "#FFEDD5"), anchor="w").pack(fill=ctk.X, padx=12, pady=(8, 3))
        body3_purpose = ctk.CTkFrame(card3_purpose, fg_color="transparent")
        body3_purpose.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        
        ctk.CTkLabel(body3_purpose, text="導入の目的 (最大5行・1行55文字制限):", text_color=("#C2410C", "#FFEDD5"), anchor="w").pack(fill=tk.X, pady=(2, 4))
        # 導入目的テキストボックスも高さを 260 に大幅に広げる！
        self.memo_text = ctk.CTkTextbox(body3_purpose, height=260, font=("Meiryo", 10))
        self.memo_text.pack(fill=tk.BOTH, expand=True, pady=4)
        # ==========================================
        # CARD 3-B: ② 商品・金額などの詳細情報 [全幅（横幅いっぱい）配置]
        # ==========================================
        card3 = ctk.CTkFrame(self.scrollable_frame, fg_color=("#FFF7ED", "#451A03"), corner_radius=10, border_width=1, border_color=("#FDBA74", "#C2410C"))
        card3.pack(fill=tk.X, pady=(0, 10))
        
        ctk.CTkLabel(card3, text="📙 5. 【② 商品・金額などの詳細】エリア", font=("Meiryo", 13, "bold"), text_color=("#C2410C", "#FFEDD5"), anchor="w").pack(fill=ctk.X, padx=15, pady=(10, 5))
        body3 = ctk.CTkFrame(card3, fg_color="transparent")
        body3.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        # 商品詳細情報グリッド (全幅を使い、元画像のゆったり並列レイアウトを完全に再現)
        grid_frame = ctk.CTkFrame(body3, fg_color="transparent")
        grid_frame.pack(fill=tk.X, pady=4)
        
        # グリッドの列比率引き伸ばし
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.columnconfigure(3, weight=1)
        
        # 金額（税抜・税込）
        ctk.CTkLabel(grid_frame, text="税抜金額:", text_color=("#C2410C", "#FFEDD5")).grid(row=0, column=0, sticky=tk.W, padx=5, pady=4)
        self.ent_ex_tax = ctk.CTkEntry(grid_frame, textvariable=self.amount_ex_tax_var, width=220)
        self.ent_ex_tax.grid(row=0, column=1, sticky=tk.W, padx=5, pady=4)
        
        ctk.CTkLabel(grid_frame, text="税込金額:", text_color=("#C2410C", "#FFEDD5")).grid(row=0, column=2, sticky=tk.W, padx=5, pady=4)
        self.ent_in_tax = ctk.CTkEntry(grid_frame, textvariable=self.amount_in_tax_var, width=220)
        self.ent_in_tax.grid(row=0, column=3, sticky=tk.W, padx=5, pady=4)
        
        self.ent_ex_tax.bind("<KeyRelease>", self.calc_tax_from_ex)
        self.ent_in_tax.bind("<KeyRelease>", self.calc_tax_from_in)
        
        # 管理番号、購入先
        ctk.CTkLabel(grid_frame, text="管理番号 (予算内):", text_color=("#C2410C", "#FFEDD5")).grid(row=1, column=0, sticky=tk.W, padx=5, pady=4)
        ctk.CTkEntry(grid_frame, textvariable=self.mng_no_var, width=220).grid(row=1, column=1, sticky=tk.W, padx=5, pady=4)
        
        ctk.CTkLabel(grid_frame, text="購入先名:", text_color=("#C2410C", "#FFEDD5")).grid(row=1, column=2, sticky=tk.W, padx=5, pady=4)
        ctk.CTkEntry(grid_frame, textvariable=self.purchase_var, width=220).grid(row=1, column=3, sticky=tk.W, padx=5, pady=4)
        
        # 支払日、支払方法
        ctk.CTkLabel(grid_frame, text="支払日:", text_color=("#C2410C", "#FFEDD5")).grid(row=2, column=0, sticky=tk.W, padx=5, pady=4)
        ctk.CTkEntry(grid_frame, textvariable=self.pay_date_var, width=220).grid(row=2, column=1, sticky=tk.W, padx=5, pady=4)
        
        ctk.CTkLabel(grid_frame, text="支払方法:", text_color=("#C2410C", "#FFEDD5")).grid(row=2, column=2, sticky=tk.W, padx=5, pady=4)
        self.pay_combo = ctk.CTkComboBox(grid_frame, variable=self.pay_method_var, values=["振込", "現金", "その他"], width=220)
        self.pay_combo.grid(row=2, column=3, sticky=tk.W, padx=5, pady=4)
        
        # 型番仕様 (全幅表示)
        ctk.CTkLabel(grid_frame, text="型番・仕様:", text_color=("#C2410C", "#FFEDD5")).grid(row=3, column=0, sticky=tk.W, padx=5, pady=4)
        ctk.CTkEntry(grid_frame, textvariable=self.model_info_var, width=540).grid(row=3, column=1, columnspan=3, sticky=tk.W, padx=5, pady=4)
        
        # 希望納期、期待効果
        ctk.CTkLabel(grid_frame, text="希望納期:", text_color=("#C2410C", "#FFEDD5")).grid(row=4, column=0, sticky=tk.W, padx=5, pady=4)
        ctk.CTkEntry(grid_frame, textvariable=self.delivery_date_var, width=220).grid(row=4, column=1, sticky=tk.W, padx=5, pady=4)
        
        ctk.CTkLabel(grid_frame, text="期待効果 (最大2行):", text_color=("#C2410C", "#FFEDD5")).grid(row=4, column=2, sticky=tk.W, padx=5, pady=4)
        ctk.CTkEntry(grid_frame, textvariable=self.effect_var, width=220).grid(row=4, column=3, sticky=tk.W, padx=5, pady=4)
        


# CARD 6: 実行エリア
        # ==========================================
        bottom_frame = ctk.CTkFrame(self.scrollable_frame, fg_color=self.bg_window)
        bottom_frame.pack(fill=tk.X, pady=5)
        
        excel_btn = self.create_flat_button(
            bottom_frame, 
            "📊 まずはExcelで稟議書を作成・保存する", 
            "#0284c7", 
            "#0284c7", 
            self.generate_ringi_excel
        )
        excel_btn.pack(fill=tk.X, ipady=6, pady=(0, 5))

        convert_btn = self.create_flat_button(
            bottom_frame, 
            "📝 手直ししたExcelをPDF化 ＆ 添付ファイルと結合", 
            "#8B5CF6", 
            "#7C3AED", 
            self.convert_saved_excel_to_pdf
        )
        convert_btn.pack(fill=tk.X, ipady=6, pady=(0, 5))

        run_btn = self.create_flat_button(
            bottom_frame, 
            "📂 Excel作成 ＋ PDF出力・添付ファイル結合まで一括実行", 
            "#059669", 
            "#059669", 
            self.generate_ringi_document
        )
        run_btn.pack(fill=tk.X, ipady=6)

    def calc_tax_from_ex(self, event=None):
        val = self.amount_ex_tax_var.get().strip()
        num_str = re.sub(r"[^\d]", "", val)
        if num_str:
            ex_val = int(num_str)
            in_val = int(ex_val * 1.1)
            self.amount_in_tax_var.set(f"{in_val:,}")
            self.amount_var.set(f"{in_val:,}円")

    def calc_tax_from_in(self, event=None):
        val = self.amount_in_tax_var.get().strip()
        num_str = re.sub(r"[^\d]", "", val)
        if num_str:
            in_val = int(num_str)
            ex_val = int(in_val / 1.1)
            self.amount_ex_tax_var.set(f"{ex_val:,}")
            self.amount_var.set(f"{in_val:,}円")

    def update_scroll_region(self):
        pass

    def create_flat_button(self, parent, text, color, hover_color, command):
        # CTKButtonにラップする
        return ctk.CTkButton(parent, text=text, command=command, fg_color=color, hover_color=hover_color, font=("Meiryo", 12, "bold"))

    def _old_create_flat_button(self, parent, text, color, hover_color, command):
        btn = tk.Button(
            parent, 
            text=text, 
            command=command, 
            bg=color, 
            fg="white", 
            activebackground=hover_color, 
            activeforeground="white",
            font=("Meiryo", 9, "bold"), 
            relief=tk.FLAT,
            padx=12,
            pady=5,
            cursor="hand2"
        )
        def on_enter(e):
            btn.configure(bg=hover_color)
        def on_leave(e):
            btn.configure(bg=color)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    def handle_dropfiles(self, files):
        # GIL競合とスレッド保護のため、Tkinterのメインループに「安全な非同期タイミング」で処理を依頼
        self.root.after(50, self.process_dropfiles_safe, files)

    def process_dropfiles_safe(self, files):
        image_extensions = (".png", ".jpg", ".jpeg", ".gif", ".bmp")
        pdf_extension = ".pdf"
        
        added_images = []
        added_pdf = ""
        
        for f_bytes in files:
            try:
                fpath = f_bytes.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    fpath = f_bytes.decode('cp932')
                except Exception:
                    continue
            
            fpath = os.path.normpath(os.path.abspath(fpath))
            
            if not os.path.exists(fpath):
                continue
                
            ext = os.path.splitext(fpath)[1].lower()
            if ext in image_extensions:
                added_images.append(fpath)
            elif ext == pdf_extension:
                added_pdf = fpath
                
        if added_images:
            self.attached_images.extend(added_images)
            self.attached_images = list(dict.fromkeys(self.attached_images))
            self.img_lbl.configure(text=f"{len(self.attached_images)}個の画像を選択中", text_color="#2fa572")
            
        if added_pdf:
            self.attached_pdf = added_pdf
            self.pdf_lbl.configure(text=os.path.basename(self.attached_pdf), text_color="#2fa572")
            
        if added_images or added_pdf:
            msg = f"ドロップされたファイルを読み込みました。\n"
            if added_images:
                msg += f"・画像: {len(added_images)}件 追加\n"
            if added_pdf:
                msg += f"・PDF見積書: 設定完了\n"
            messagebox.showinfo("ファイル読込完了", msg)
        pass

    def click_select_file(self):
        # ドロップエリアをクリックした時の選択ダイアログ (フォールバック)
        ans = messagebox.askyesnocancel("ファイル選択", "見積書などの『PDF』を選択しますか？\n(いいえを押すと『画像』選択になります)")
        if ans is True:
            self.select_pdf()
        elif ans is False:
            self.select_images()

    def reload_templates(self):
        templates = []
        if os.path.exists(DEFAULT_TEMPLATE_DIR):
            for f in os.listdir(DEFAULT_TEMPLATE_DIR):
                if f.endswith(".xlsx") and not f.startswith("~$") and ("稟議書" in f or "原紙" in f):
                    templates.append(os.path.join(DEFAULT_TEMPLATE_DIR, f))
        
        if templates:
            vals = [os.path.basename(t) for t in templates]
            self.tpl_combo.configure(values=vals)
            self.tpl_combo.set(vals[0])
            self.template_path_var.set(templates[0])
            self.load_template_to_ui(templates[0])
        else:
            self.tpl_combo.configure(values=["テンプレートが見つかりません"])
            self.tpl_combo.set("テンプレートが見つかりません")
            
    def select_template_file(self):
        fpath = filedialog.askopenfilename(
            title="テンプレートExcelファイルを選択",
            filetypes=[("Excel Files", "*.xlsx")]
        )
        if fpath:
            self.template_path_var.set(fpath)
            curr_values = list(self.tpl_combo.cget("values"))
            new_val = os.path.basename(fpath)
            if new_val not in curr_values:
                curr_values.append(new_val)
            self.tpl_combo.configure(values=curr_values)
            self.tpl_combo.set(new_val)
            self.load_template_to_ui(fpath)
        pass


    def clear_attachment(self, target):
        if target == "image":
            self.attached_images = []
            self.img_lbl.configure(text="選択されていません", text_color="gray")
        elif target == "pdf":
            self.attached_pdf = ""
            self.pdf_lbl.configure(text="選択されていません", text_color="gray")
    def select_images(self):
        fpaths = filedialog.askopenfilenames(
            title="添付画像ファイルを選択 (複数選択可)",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp")]
        )
        if fpaths:
            self.attached_images = [os.path.normpath(os.path.abspath(fp)) for fp in fpaths]
            self.img_lbl.configure(text=f"{len(fpaths)}個の画像を選択中", text_color="#2fa572")
        else:
            self.attached_images = []
            self.img_lbl.configure(text="選択されていません", text_color="gray")
        pass

    def select_pdf(self):
        fpath = filedialog.askopenfilename(
            title="添付PDFファイル（見積書など）を選択",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if fpath:
            self.attached_pdf = os.path.normpath(os.path.abspath(fpath))
            self.pdf_lbl.configure(text=os.path.basename(fpath), text_color="#2fa572")
        else:
            self.attached_pdf = ""
            self.pdf_lbl.configure(text="選択されていません", text_color="gray")

    def analyze_attached_file(self):
        self.api_key = self.api_entry.get().strip()
        
        target_file = ""
        is_pdf = False
        
        if self.attached_pdf and os.path.exists(self.attached_pdf):
            target_file = self.attached_pdf
            is_pdf = True
        elif self.attached_images:
            target_file = self.attached_images[-1]
            is_pdf = False
            
        if not target_file:
            messagebox.showerror("エラー", "解析対象のファイル（見積書PDFまたは製品画像）が添付されていません。")
            return
            
        # PDFの場合、まずはローカルで高速テキスト解析（正規表現ルールベース）を試みる
        local_data = {}
        pdf_text = ""
        if is_pdf:
            try:
                reader = PdfReader(target_file)
                for page in reader.pages:
                    txt = page.extract_text()
                    if txt:
                        pdf_text += txt + "\n"
                
                if pdf_text.strip():
                    # --- ローカル正規表現解析エンジン ---
                    import re
                    # 1. 税込合計の探索
                    in_tax_pats = [
                        r"(?:請求金額|請求額|御請求額|合計金額|税込合計|お支払額|お支払合計)[^\d\n]*([\d,]+)",
                        r"([\d,]+)\s*(?:円|Yen)?\s*\(税込\)",
                        r"合計[^\d\n]*([\d,]+)"
                    ]
                    for pat in in_tax_pats:
                        m = re.findall(pat, pdf_text, re.IGNORECASE)
                        if m:
                            # カンマを除去して数字だけにする
                            val = m[0].replace(",", "")
                            if val.isdigit() and int(val) > 100:
                                local_data["amount_in_tax"] = f"{int(val):,}円"
                                break
                    
                    # 2. 税抜合計の探索
                    ex_tax_pats = [
                        r"(?:税抜合計|税別合計|小計|税抜額|税別)[^\d\n]*([\d,]+)",
                        r"([\d,]+)\s*(?:円|Yen)?\s*\(税別\)"
                    ]
                    for pat in ex_tax_pats:
                        m = re.findall(pat, pdf_text, re.IGNORECASE)
                        if m:
                            val = m[0].replace(",", "")
                            if val.isdigit() and int(val) > 100:
                                local_data["amount_ex_tax"] = f"{int(val):,}円"
                                break
                                
                    # 3. 取引先の探索 (自社名「フォーレスト」を除外した上で、株式会社や有限会社を抽出)
                    co_lines = pdf_text.split("\n")
                    companies = []
                    for cl in co_lines:
                        cl_clean = cl.strip()
                        # 自社名「フォーレスト」関連ワードが含まれる場合は除外
                        if any(w in cl_clean for w in ["フォーレスト", "Forest", "ﾌｫｰﾚｽﾄ", "フォレスト"]):
                            continue
                        # 株式会社、有限会社、合同会社などの検索
                        co_m = re.search(r"([^\s]*(?:株式会社|有限会社|合同会社)[^\s]*)", cl_clean)
                        if co_m:
                            co_name = co_m.group(1).replace("：", "").replace(":", "").replace("御中", "").replace("様", "").strip()
                            if len(co_name) > 4:
                                companies.append(co_name)
                                
                    if companies:
                        local_data["purchase_from"] = companies[0]
                        
                    # 4. 商品名の探索
                    # 「品名」「型番」「商品名」などの行から推測するが、簡易的に
                    # 見積書内でよく使われる最初の行や件名など
                    lines = [l.strip() for l in pdf_text.split("\n") if l.strip()]
                    for l in lines[:10]:
                        if "御見積" in l or "件名" in l or "品名" in l:
                            local_data["subject"] = l.replace("御見積", "").replace("件名", "").replace("品名", "").replace("：", "").replace(":", "").strip()
                            break
                            
            except Exception as e:
                print(f"ローカルPDF解析エラー: {e}")

        # ローカル解析で税込金額と取引先が両方取得できたら、APIを使わずに一瞬で完了させる！
        if local_data.get("amount_in_tax") and local_data.get("purchase_from"):
            # UIへの反映
            self.amount_in_tax_var.set(local_data["amount_in_tax"])
            if local_data.get("amount_ex_tax"):
                self.amount_ex_tax_var.set(local_data["amount_ex_tax"])
            else:
                # 1.1で割って簡易計算
                try:
                    val = int("".join([c for c in local_data["amount_in_tax"] if c.isdigit()]))
                    ex_val = int(val / 1.1)
                    self.amount_ex_tax_var.set(f"{ex_val:,}円")
                except:
                    pass
            
            self.purchase_var.set(local_data["purchase_from"])
            if local_data.get("subject"):
                self.subject_var.set(local_data["subject"][:30])
                self.model_info_var.set(local_data["subject"])
                
            # 金額連動の呼び出し
            self.calc_tax_from_ex()
            
            # 用途テンプレートの自動置換を適用
            self.apply_use_case_template_replacement()
            
            messagebox.showinfo("成功", "PDFから金額と取引先データをローカル高速抽出しました！\n(API料金は発生していません)")
            return

        # ローカル解析で情報が不足している場合、または画像の場合は従来通りGemini APIを使用する
        if not self.api_key:
            messagebox.showerror("エラー", "Gemini APIキーが設定されていません。ローカル解析で情報が不足したため、AI解析を行うにはAPIキーが必要です。")
            return
            
        progress_win = tk.Toplevel(self.root)
        progress_win.title("解析中")
        progress_win.geometry("300x100")
        progress_win.transient(self.root)
        progress_win.grab_set()
        
        lbl = ctk.CTkLabel(progress_win, text="AIが添付ファイルを読み取っています...\n(しばらくお待ちください)")
        lbl.pack(pady=20)
        self.root.update()
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            
            prompt = (
                "あなたは優秀な社内SEです。提供された情報は、購入予定の「見積書」または「製品ページの画像」です。\n"
                "この情報から、以下のキーを持つJSONオブジェクトのみを出力してください。説明文は一切含めないでください。\n\n"
                "【抽出項目】\n"
                "1. subject: 稟議の件名に相応しい簡潔なタイトル。例: 「ノートPC購入の件」「ディスプレイ購入の件」（30文字以内）\n"
                "2. amount_ex_tax: 税抜の合計金額（数字のみ、またはカンマ付き）。無い場合は空文字列。\n"
                "3. amount_in_tax: 税込の合計金額（数字のみ、またはカンマ付き）。無い場合は空文字列。\n"
                "4. purchase_from: 購入先（販売会社名、メーカー名等）。例: 「株式会社イオシス」「株式会社デル」\n"
                "5. model_info: 購入する機器の品名、型番、主要スペック。例: 「HP ProBook 430 G8 (Core i5/16GB/256GB SSD)」\n"
                "6. effect: 期待される導入効果。例: 「老朽化による故障トラブルの回避」「業務効率向上」\n"
                "7. delivery: 納期や導入予定時期。例: 「別途打合せ」「来年1月下旬」\n"
                "8. reason_area1: この見積から推測した「起案目的・理由」（150文字以内の自然な文章。例：老朽化対応や不足分の補充など。AIが推測して説得力のある文章を作成）。\n"
                "9. purpose_area2: この機器を導入することで得られる「具体的な業務改善効果」（150文字以内の自然な文章。例：作業効率の向上、視認性の向上など。AIが判断して作成）。\n\n"
                "【出力フォーマット】\n"
                "```json\n"
                                "{\n"
                "  \"subject\": \"...\",\n"
                "  \"amount_ex_tax\": \"...\",\n"
                "  \"amount_in_tax\": \"...\",\n"
                "  \"purchase_from\": \"...\",\n"
                "  \"model_info\": \"...\",\n"
                "  \"effect\": \"...\",\n"
                "  \"delivery\": \"...\",\n"
                "  \"reason_area1\": \"...\",\n"
                "  \"purpose_area2\": \"...\"\n"
                "}\n"
                "```"
            )
            
            if is_pdf:
                # すでに抽出したpdf_textを利用
                if not pdf_text.strip():
                    raise Exception("PDFからテキスト情報を抽出できませんでした。")
                    
                data = {
                    "contents": [{
                        "parts": [
                            {"text": f"{prompt}\n\n【情報ソース(PDFテキスト)】\n{pdf_text}"}
                        ]
                    }]
                }
            else:
                with open(target_file, "rb") as f:
                    img_base64 = base64.b64encode(f.read()).decode("utf-8")
                    
                data = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {
                                "inlineData": {
                                    "mimeType": "image/png",
                                    "data": img_base64
                                }
                            }
                        ]
                    }]
                }
                
            req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req) as response:
                res_data = response.read().decode("utf-8")
                res_json = json.loads(res_data)
                
                # レスポンスからテキスト抽出
                text_out = res_json["candidates"][0]["content"]["parts"][0]["text"]
                # markdownコードブロックを削除して純粋なJSONにする
                json_str = text_out.replace("```json", "").replace("```", "").strip()
                
                # パース
                try:
                    res_json = json.loads(json_str)
                    
                    if "subject" in res_json:
                        self.subject_var.set(res_json["subject"])
                    if "amount_ex_tax" in res_json and res_json["amount_ex_tax"]:
                        val = res_json["amount_ex_tax"]
                        if not val.endswith("円"): val += "円"
                        self.amount_ex_tax_var.set(val)
                    if "amount_in_tax" in res_json and res_json["amount_in_tax"]:
                        val = res_json["amount_in_tax"]
                        if not val.endswith("円"): val += "円"
                        self.amount_in_tax_var.set(val)
                    if "purchase_from" in res_json:
                        self.purchase_var.set(res_json["purchase_from"])
                    if "model_info" in res_json:
                        self.model_info_var.set(res_json["model_info"])
                    if "effect" in res_json:
                        self.effect_var.set(res_json["effect"])
                    if "delivery" in res_json:
                        self.delivery_date_var.set(res_json["delivery"])

                    if "reason_area1" in res_json and res_json["reason_area1"]:
                        self.reason_preview.delete("1.0", tk.END)
                        self.reason_preview.insert(tk.END, res_json["reason_area1"])

                    if "purpose_area2" in res_json and res_json["purpose_area2"]:
                        self.memo_text.delete("1.0", tk.END)
                        self.memo_text.insert(tk.END, res_json["purpose_area2"])
                        
                    # 金額連動
                    self.calc_tax_from_ex()
                    
                    # 用途テンプレートの自動置換を適用
                    self.apply_use_case_template_replacement()
                    
                except Exception as je:
                    raise Exception(f"JSONパースエラー: {je}\n生の出力:\n{text_out}")
                    
            progress_win.destroy()
            messagebox.showinfo("成功", "AIによる見積書/画像解析およびフォームへの自動入力が完了しました！")
            
        except Exception as e:
            progress_win.destroy()
            messagebox.showerror("エラー", f"AI解析に失敗しました:\n{e}")
    def generate_local_template(self):
        subject = self.subject_var.get().strip()
        if not subject:
            messagebox.showerror("エラー", "件名を入力してください。")
            return
            
        dept = self.dept_var.get().strip()
        ex_tax = self.amount_ex_tax_var.get().strip()
        in_tax = self.amount_in_tax_var.get().strip()
        pay_date = self.pay_date_var.get().strip()
        pay_method = self.pay_method_var.get().strip()
        
        purchase = self.purchase_var.get().strip()
        model_info = self.model_info_var.get().strip()
        delivery = self.delivery_date_var.get().strip()
        effect = self.effect_var.get().strip()
        
        memo = self.memo_text.get("1.0", tk.END).strip()
        if "例: 経年劣化による液晶の不具合" in memo:
            memo = "経年劣化が進んでいるため"
            
        text = ""
        if self.apply_type_var.get() == "更新":
            pc_no = self.old_pc_no_var.get().strip()
            user_name = self.old_pc_user_var.get().strip()
            if not pc_no or not user_name:
                messagebox.showerror("エラー", "更新の場合は「更新元管理番号」と「使用者氏名」を入力してください。")
                return
                
            text += f"{subject}の件について、現在{dept}にて使用しております機器（管理番号：{pc_no}、使用者：{user_name}）が、{memo}となっております。\n"
            text += "経年劣化（または不具合）により正常な動作が困難となっており、業務の継続やセキュリティ維持に支障が生じる恐れがあります。\n"
            text += f"つきましては、業務継続性の確保のため、代替機として新規（または中古）端末を調達・更新させていただきたく、起案いたします。\n\n"
            
            text += "■目的\n"
            text += "老朽化した機器の更新により、業務停止リスクを回避し、稼働の安定性を確保します。\n\n"
            
            text += "■購入品・仕様\n"
            text += f"品名/件名：{subject}\n"
            if model_info:
                text += f"型番/仕様：{model_info}\n"
            text += f"合計金額：{in_tax}円（税抜：{ex_tax}円、支払方法：{pay_method}、支払予定日：{pay_date}）\n\n"
            
            if purchase:
                text += "■購入先\n"
                text += f"{purchase}\n\n"
                
            if delivery:
                text += "■納期\n"
                text += f"{delivery}\n\n"
                
            text += f"■効果\n{effect}"
        else:
            reason = self.add_reason_var.get().strip()
            if not reason:
                messagebox.showerror("エラー", "追加の場合は「追加理由」を入力してください。")
                return
                
            text += f"{subject}の件について、{reason}に伴い、新たに機器を配備する必要があります。\n"
            text += f"本件は、{memo}のため、新規に機器を導入するものです。\n"
            text += "導入により業務効率の向上を図るとともに、円滑な運用体制の確立を目指します。つきましては、購入手続きについてご承認をお願い申し上げます。\n\n"
            
            text += "■目的\n"
            text += f"{reason}に対応するための機器導入および業務環境の整備。\n\n"
            
            text += "■購入品・仕様\n"
            text += f"品名/件名：{subject}\n"
            if model_info:
                text += f"型番/仕様：{model_info}\n"
            text += f"合計金額：{in_tax}円（税抜：{ex_tax}円、支払方法：{pay_method}、支払予定日：{pay_date}）\n\n"
            
            if purchase:
                text += "■購入先\n"
                text += f"{purchase}\n\n"
                
            if delivery:
                text += "■納期\n"
                text += f"{delivery}\n\n"
                
            text += f"■効果\n{effect}"
            
        self.reason_preview.delete("1.0", tk.END)
        self.reason_preview.insert(tk.END, text)
        self.check_preview_limit()
        pass



    def on_template_combo_change(self, choice):
        # コンボボックスで選択されたファイルをフルパスに変換してロード
        if choice == "テンプレートが見つかりません":
            return
        tpl_path = os.path.join(DEFAULT_TEMPLATE_DIR, choice)
        self.template_path_var.set(tpl_path)
        self.load_template_to_ui(tpl_path)

    def load_template_to_ui(self, tpl_path):
        if not tpl_path or not os.path.exists(tpl_path):
            return
            
        progress_win = tk.Toplevel(self.root)
        progress_win.title("テンプレート読込中")
        progress_win.geometry("300x100")
        progress_win.transient(self.root)
        progress_win.grab_set()
        lbl = ctk.CTkLabel(progress_win, text="テンプレートから既存データを読込中...")
        lbl.pack(pady=20)
        self.root.update()
        
        excel_app = None
        try:
            import win32com.client, re
            excel_app = win32com.client.DispatchEx("Excel.Application")
            excel_app.Visible = False
            excel_app.DisplayAlerts = False
            
            wb = excel_app.Workbooks.Open(tpl_path, ReadOnly=True)
            ws = wb.ActiveSheet
            
            # 1. 起案者基本情報 (S2, AH1, AH3, AS1, E7)
            dept = str(ws.Range("S2").Value or "").strip()
            date_val = str(ws.Range("AH1").Value or "").strip()
            title = str(ws.Range("AH3").Value or "").strip()
            author = str(ws.Range("AS1").Value or "").strip()
            subject = str(ws.Range("E7").Value or "").strip()
            
            if dept: self.dept_var.set(dept)
            if date_val: self.date_var.set(date_val)
            if title: self.title_var.set(title)
            if author: self.author_var.set(author)
            if subject: self.subject_var.set(subject)
            
            # 2. 管理番号 (E10)
            e10_val = str(ws.Range("E10").Value or "").strip()
            mng_match = re.search(r"【[^】]*?([A-Za-z0-9\-]+)[^】]*?】", e10_val)
            if mng_match:
                self.mng_no_var.set(mng_match.group(1))
            else:
                self.mng_no_var.set("")
                
            # 3. 予算額 (AT14), 支払日 (AT16), 支払方法 (AT17)
            amt = str(ws.Range("AT14").Value or "").strip()
            pay_date = str(ws.Range("AT16").Value or "").strip()
            pay_method_raw = str(ws.Range("AT17").Value or "").strip()
            
            if amt:
                if "円" not in amt: amt += "円"
                self.amount_var.set(amt)
                self.amount_in_tax_var.set(amt)
                self.amount_ex_tax_var.set(amt)
            if pay_date:
                self.pay_date_var.set(pay_date)
            if pay_method_raw:
                if "■ 現金" in pay_method_raw:
                    self.pay_method_var.set("現金")
                elif "■ 振込" in pay_method_raw:
                    self.pay_method_var.set("振込")
                else:
                    custom_match = re.search(r"■\s*（\s*([^）\s]+)\s*）", pay_method_raw)
                    if custom_match:
                        self.pay_method_var.set(custom_match.group(1))
                    else:
                        self.pay_method_var.set("振込")
            
            # 4. 起案目的・理由 (B15:B20)
            reason_lines = []
            for r in range(15, 21):
                val = str(ws.Range("B" + str(r)).Value or "").strip()
                if val: reason_lines.append(val)
            reason_text = "\n".join(reason_lines)
            self.reason_preview.delete("1.0", tk.END)
            self.reason_preview.insert(tk.END, reason_text)
            
            # 5. 目的 (C23:C27 または B23:B27 ハイブリッド)
            # 古いテンプレートでは目的がB列に入っているため、両方を走査する
            purpose_lines = []
            for r in range(23, 28):
                b_val = str(ws.Range("B" + str(r)).Value or "").strip()
                c_val = str(ws.Range("C" + str(r)).Value or "").strip()
                val = b_val or c_val
                if val and "■目的" not in val and "目的" != val:
                    purpose_lines.append(val)
            purpose_text = "\n".join(purpose_lines)
            self.memo_text.delete("1.0", tk.END)
            self.memo_text.insert(tk.END, purpose_text)
            
            # 6. 効果 (C38:C39)
            effect_lines = []
            for r in range(38, 40):
                val = str(ws.Range("C" + str(r)).Value or "").strip()
                if val: effect_lines.append(val)
            effect_text = "\n".join(effect_lines)
            if effect_text:
                self.effect_var.set(effect_text)
                
            # 7. 実施内容 (C27:C42, G27:G42, J27:J42, N27:N42 などの多次元逆引きスキャン)
            # 旧Excel（J列に値）と新Excel（C列に結合テキスト）の双方を完全にパースする
            found_model = ""
            found_purchase = ""
            found_delivery = ""
            found_ex_tax = ""
            found_in_tax = ""
            
            # まずはC29:C36の結合テキスト（新形式）を走査
            details_text = ""
            for r in range(29, 37):
                val = str(ws.Range("C" + str(r)).Value or "").strip()
                if val:
                    details_text += val + "\n"
                    
            item_match = re.search(r"・商品　　：([^\n]+)", details_text)
            pur_match = re.search(r"  取引先　：([^\n]+)", details_text)
            deliv_match = re.search(r"  希望納期：([^\n]+)", details_text)
            amt_match = re.search(r"  購入金額：([^\n]+)", details_text)
            if item_match: found_model = item_match.group(1).strip()
            if pur_match: found_purchase = pur_match.group(1).strip()
            if deliv_match: found_delivery = deliv_match.group(1).strip()
            if amt_match:
                amt_str = amt_match.group(1)
                ex_m = re.search(r"([\d,]+)円", amt_str)
                in_m = re.search(r"税込\s*([\d,]+)円", amt_str)
                if ex_m: found_ex_tax = ex_m.group(1) + "円"
                if in_m: found_in_tax = in_m.group(1) + "円"
            
            # 見つからなかった項目について、セル単位のグリッド走査（旧形式）を試みる
            for r in range(26, 43):
                c_val = str(ws.Cells(r, 3).Value or "").strip()  # C列 (3)
                g_val = str(ws.Cells(r, 7).Value or "").strip()  # G列 (7)
                j_val = str(ws.Cells(r, 10).Value or "").strip() # J列 (10)
                n_val = str(ws.Cells(r, 14).Value or "").strip() # N列 (14)
                
                # C列に特定の項目名がある場合、G列またはJ列から値を取り出す
                if "商品" in c_val or "型番" in c_val or "・商品" in c_val:
                    val = j_val or g_val
                    if val and not found_model:
                        found_model = val
                elif "取引先" in c_val:
                    val = j_val or g_val
                    if val and not found_purchase:
                        found_purchase = val
                elif "納期" in c_val:
                    val = j_val or g_val
                    if val and not found_delivery:
                        found_delivery = val
                elif "金額" in c_val or "小計" in c_val:
                    val = j_val or g_val
                    if val:
                        if "税別" in val or "税抜" in val:
                            if not found_ex_tax: found_ex_tax = val
                        elif "税込" in val:
                            if not found_in_tax: found_in_tax = val
                        elif not found_ex_tax:
                            found_ex_tax = val
                            
                # N列(14) や J列の合計金額テキストもパース
                # 例: "10%対象額　169,073円　税額　16,907円　税込み合計額　185,980円"
                for target_text in [n_val, j_val, g_val]:
                    if "税込み合計額" in target_text or "税込" in target_text:
                        in_match = re.search(r"税込み合計額\s*([\d,]+)", target_text)
                        if in_match:
                            found_in_tax = in_match.group(1) + "円"
                        ex_match = re.search(r"10%対象額\s*([\d,]+)", target_text)
                        if ex_match:
                            found_ex_tax = ex_match.group(1) + "円"
                            
            # 抽出した詳細データをUIにセット
            if found_model: self.model_info_var.set(found_model)
            if found_purchase: self.purchase_var.set(found_purchase)
            if found_delivery: self.delivery_date_var.set(found_delivery)
            if found_ex_tax: self.amount_ex_tax_var.set(found_ex_tax.replace("（税抜き）", "").replace("(税抜)", "").strip())
            if found_in_tax:
                self.amount_in_tax_var.set(found_in_tax.strip())
                self.amount_var.set(found_in_tax.strip())
                
            # 金額計算とUIの連動をトリガー
            self.calc_tax_from_ex()
            
            wb.Close(False)
            excel_app.Quit()
            excel_app = None
            
        except Exception as e:
            print(f"テンプレート読込エラー: {e}")
            if excel_app is not None:
                try: excel_app.Quit()
                except: pass
        finally:
            progress_win.destroy()
            
    def import_past_ringi_text(self):
        # 過去の稟議書Excelを選択させる
        fpath = filedialog.askopenfilename(
            title="参考にする過去の稟議書Excelを選択",
            initialdir=DEFAULT_OUTPUT_DIR,
            filetypes=[("Excel Files", "*.xlsx;*.xls")]
        )
        if not fpath: return
        
        progress_win = tk.Toplevel(self.root)
        progress_win.title("読み込み中")
        progress_win.geometry("300x100")
        progress_win.transient(self.root)
        progress_win.grab_set()
        lbl = ctk.CTkLabel(progress_win, text="過去の稟議書から文章を抽出しています...")
        lbl.pack(pady=20)
        self.root.update()
        
        excel_app = None
        try:
            import win32com.client
            excel_app = win32com.client.DispatchEx("Excel.Application")
            excel_app.Visible = False
            excel_app.DisplayAlerts = False
            
            wb = excel_app.Workbooks.Open(fpath, ReadOnly=True)
            ws = wb.ActiveSheet
            
            # ① Area 1 (B15:B20) のテキスト抽出
            reason_lines = []
            for r in range(15, 21):
                val = str(ws.Range("B" + str(r)).Value or "").strip()
                if val:
                    reason_lines.append(val)
            reason_text = "\n".join(reason_lines)
            
            # ② Area 2 (C23:C27) の目的テキスト抽出
            purpose_lines = []
            for r in range(23, 28):
                val = str(ws.Range("C" + str(r)).Value or "").strip()
                if val:
                    purpose_lines.append(val)
            purpose_text = "\n".join(purpose_lines)
            
            # ② Area 2 (C38:C39) の効果テキスト抽出
            effect_lines = []
            for r in range(38, 40):
                val = str(ws.Range("C" + str(r)).Value or "").strip()
                if val:
                    effect_lines.append(val)
            effect_text = "\n".join(effect_lines)
            
            # 件名 (E7) の抽出（もし入っていれば参考にする）
            subject_val = str(ws.Range("E7").Value or "").strip()
            
            wb.Close(False)
            excel_app.Quit()
            excel_app = None
            
            # UIに反映
            if reason_text:
                self.reason_preview.delete("1.0", tk.END)
                self.reason_preview.insert(tk.END, reason_text)
                
            if purpose_text:
                self.memo_text.delete("1.0", tk.END)
                self.memo_text.insert(tk.END, purpose_text)
                
            if effect_text:
                self.effect_var.set(effect_text)
                
            if subject_val:
                self.subject_var.set(subject_val)
                
            progress_win.destroy()
            messagebox.showinfo("成功", "過去の稟議書から文章のコピーが完了しました！\nUI上の内容をご確認ください。")
            
        except Exception as e:
            if excel_app is not None:
                try:
                    excel_app.Quit()
                except:
                    pass
            progress_win.destroy()
            messagebox.showerror("エラー", f"過去の稟議書の読み込みに失敗しました:\n{e}")
    def generate_reason(self):
        self.api_key = self.api_entry.get().strip()
        if not self.api_key:
            messagebox.showerror("エラー", "Gemini APIキーを入力してください。")
            return
            
        subject = self.subject_var.get().strip()
        if not subject:
            messagebox.showerror("エラー", "件名を入力してください。")
            return
            
        model_info = self.model_info_var.get().strip()
        in_tax = self.amount_in_tax_var.get().strip()
        ex_tax = self.amount_ex_tax_var.get().strip()
        pay_method = self.pay_method_var.get().strip()
        pay_date = self.pay_date_var.get().strip()
        purchase = self.purchase_var.get().strip()
        delivery = self.delivery_date_var.get().strip()
        effect = self.effect_var.get().strip()
        
        memo = self.memo_text.get("1.0", tk.END).strip()
        if "例: 経年劣化による液晶の不具合" in memo or not memo:
            memo = "経年劣化のため動作が不安定となっており、業務の継続やセキュリティ維持に支障が生じる恐れがあります。"
            
        text = ""
        if self.apply_type_var.get() == "更新":
            pc_no = self.old_pc_no_var.get().strip()
            user_name = self.old_pc_user_var.get().strip()
            
            text += f"件名につきましては、業務継続性の確保および老朽化に伴うトラブルの未然防止のため、機器の更新を行いたく申請いたします。\n\n"
            text += "■目的\n"
            text += f"対象機器（管理番号：{pc_no}、使用者：{user_name}）の老朽化に伴い動作遅延等が発生しているため、最新機種へ更新し、業務効率化とセキュリティ維持を図ります。\n\n"
            text += "■詳細仕様\n"
            text += f"商品名：{subject}\n"
            if model_info:
                text += f"型番・仕様：{model_info}\n"
            
            ex_val = 0
            in_val = 0
            try:
                ex_val = int(''.join([c for c in ex_tax if c.isdigit()]))
                in_val = int(''.join([c for c in in_tax if c.isdigit()]))
            except:
                pass
            tax_val = in_val - ex_val
            
            text += f"金額：{in_tax}円（税抜き：{ex_tax}円、消費税：{tax_val:,}円）\n"
            text += f"支払方法：{pay_method}、希望納期：{delivery}\n"
            if purchase:
                text += f"購入先：{purchase}\n\n"
            else:
                text += "\n"
            text += f"■対応の効果について\n{effect}"
        else:
            reason = self.add_reason_var.get().strip()
            if not reason:
                messagebox.showerror("エラー", "追加・新規購入の場合は「追加理由」を入力してください。")
                return
                
            text += f"件名につきましては、新規導入（追加配備）による業務効率の向上を図るため、機器の調達を行いたく申請いたします。\n\n"
            text += "■目的\n"
            text += f"{reason}\n\n"
            text += "■詳細仕様\n"
            text += f"商品名：{subject}\n"
            if model_info:
                text += f"型番・仕様：{model_info}\n"
            text += f"金額：{in_tax}円（税抜き：{ex_tax}円）\n"
            text += f"支払方法：{pay_method}、希望納期：{delivery}\n"
            if purchase:
                text += f"購入先：{purchase}\n\n"
            else:
                text += "\n"
            text += f"■対応の効果について\n{effect}"
            
        prompt = "あなたは優秀な社内SEです。ユーザーが入力した稟議書の「件名」「起案目的・理由」のメモを元に、役員や社長が決裁しやすい、論理的で説得力のある「起案目的・理由（Area ①）」の文章を作成してください。\n"
        prompt += f"件名: {subject}\n"
        prompt += f"起案目的・理由のメモ: {memo}\n"
        
        if memo:
            prompt += f"追加の目的・状況メモ: {memo}\n"
            
        prompt += "\n【文章構成ルール】\n"
        prompt += "1. 冒頭で「件名について、○○のため購入（または更新）したく申請いたします。」のように簡潔に結論を述べてください。\n"
        prompt += "2. その後、現在の問題点や、購入することで得られる効果・メリットなどを記述してください。\n"
        prompt += "3. 全体の文章は、改行を含めて150文字～200文字程度、最大でも240文字以内で作成してください。\n"
        prompt += "4. 丁寧な表現（～です、～ます、～いたします）を使用してください。\n"
        prompt += "5. 余計な前置きやタイトル（「拝啓」や「起案目的・理由：」という文字など）は含めず、本文のみを出力してください。\n"
        prompt += "6. ExcelのB列（B15～B20セル,最大6行）に書き込まれます。1行あたりの最大文字数は日本語で「40文字」です。意味の切れ目の良いところ（読点「、」や句点「。」、文脈の区切り）で自然に改行（\\n）を挟み、最大6行に収まるよう綺麗に成型して出力してください。1行が40文字を超えないように特に配慮してください。\n"
        
        prompt += "\n【過去に承認された稟議書の例文（社内の雰囲気や言い回しの参考にしてください）】\n"
        prompt += "例文1（経年劣化による交換）：\n"
        prompt += "大宮本社で使用しているUPS2台のバッテリーを購入したく稟議申請いたします。\n"
        prompt += "使用年数が伸び、バッテリーの劣化が進んだため、エラー表示とアラートが発報されております。\n"
        prompt += "落雷の際の停電などで機能が働かなくなり、接続される機器の故障の可能性があるので交換が必要となります。\n\n"
        
        prompt += "例文2（業務効率化・追加購入）：\n"
        prompt += "人員増員と作業量増加のため、端末の設置方法を変更するために切替器の購入を稟議申請致します。\n"
        prompt += "端末の設置方法を変更することにより、今まで以上の業務効率化をはかります。\n\n"
        
        prompt += "例文3（故障対応・予備在庫）：\n"
        prompt += "PCモニターの故障があり、システム部で使用中のものを代わりに使用して対応いたしました。\n"
        prompt += "その補充用として新たにモニターを購入したく申請いたします。\n"
        prompt += "また、もう一台は今後発生する故障対応への在庫として保管します。\n"
        
        self.reason_preview.delete("1.0", tk.END)
        self.reason_preview.insert(tk.END, "AI文章を生成中...")
        self.root.update()
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                result_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                
                if result_text.startswith("```"):
                    result_text = "\n".join(result_text.split("\n")[1:-1])
                
                self.reason_preview.delete("1.0", tk.END)
                self.reason_preview.insert(tk.END, result_text)
                
                self.check_preview_limit()
                
        except Exception as e:
            self.reason_preview.delete("1.0", tk.END)
            self.reason_preview.insert(tk.END, f"生成エラーが発生しました。\nAPIキーが正しいか、ネットワーク接続を確認してください。\n詳細: {e}")
        pass

    def check_preview_limit(self):
        text = self.reason_preview.get("1.0", tk.END).strip()
        lines = text.split("\n")
        
        formatted_lines = []
        for line in lines:
            while len(line) > 55:
                formatted_lines.append(line[:55])
                line = line[55:]
            formatted_lines.append(line)
            
        total_lines = len(formatted_lines)
        if total_lines > 28:
            messagebox.showwarning(
                "文字数・行数過多警告",
                f"現在の文章はレイアウトの行数上限（28行）を超えています（現在換算で約 {total_lines} 行）。\n"
                "ExcelからPDFにした際に、下部が決裁欄にはみ出してしまう可能性が高いため、文章を短く調整してください。"
            )

    def select_template_path_actual(self):
        tpl_name = self.tpl_combo.get()
        if tpl_name == "テンプレートが見つかりません":
            return ""
        path = os.path.join(DEFAULT_TEMPLATE_DIR, tpl_name)
        if os.path.exists(path):
            return path
        return self.template_path_var.get()

    def write_excel_common(self, output_excel_path, is_pdf_mode=False):
        tpl_path = self.select_template_path_actual()
        if not tpl_path or not os.path.exists(tpl_path):
            messagebox.showerror("エラー", "Excelテンプレートファイルが正しく選択されていません。")
            return False
            
        subject = self.subject_var.get().strip()
        if not subject:
            messagebox.showerror("エラー", "件名を入力してください。")
            return False
            
        reason_text = self.reason_preview.get("1.0", tk.END).strip()
        if not reason_text or "AI文章を生成中..." in reason_text:
            messagebox.showerror("エラー", "起案目的・理由が空欄です。AIで生成するか手動で入力してください。")
            return False
            
        excel_app = None
        try:
            import shutil, win32com.client
            shutil.copy(tpl_path, output_excel_path)
            
            excel_app = win32com.client.DispatchEx("Excel.Application")
            excel_app.Visible = False
            excel_app.DisplayAlerts = False
            
            wb = excel_app.Workbooks.Open(output_excel_path)
            ws = wb.ActiveSheet
            
            # ①および②エリア全体のクリア (全列にわたる古いデータの残骸を完全にクリーンアップ)
            ws.Range("B15:B20").Value = ""
            ws.Range("B22:B42").Value = ""
            ws.Range("C23:C27").Value = ""
            # B28からAT42(実施内容、スペック、効果を含む全グリッド)のデータを横列全てクリア
            ws.Range("B28:AT42").Value = ""
            ws.Range("C28:C42").Value = ""
            ws.Range("F29:F30").Value = ""
            ws.Range("G29:Z30").Value = ""
            ws.Range("Q31:Z31").Value = ""
            ws.Range("Q34:Z34").Value = ""
            
            ws.Range("S2").Value = self.dept_var.get()
            ws.Range("AH1").Value = self.date_var.get()
            ws.Range("AH3").Value = self.title_var.get()
            ws.Range("AS1").Value = self.author_var.get()
            ws.Range("E7").Value = subject
            
            mng_no = self.mng_no_var.get().strip()
            if mng_no:
                ws.Range("E10").Value = "■　 予算内　　【　　　　　" + mng_no + " 　　　　　　】　　　　　□　 予算外　　　　　　※経費の支出を伴う場合のみ記載"
            else:
                ws.Range("E10").Value = "□　 予算内　　【　管理番号　：　　　　　　　　　　　】　　　　　■　 予算外　　　　　　※経費の支出を伴う場合のみ記載"
                
            ws.Range("AT14").Value = self.amount_var.get()
            ws.Range("AT16").Value = self.pay_date_var.get()
            
            pay_method = self.pay_method_var.get()
            if pay_method == "現金":
                ws.Range("AT17").Value = "■ 現金 ・ □ 振込 ・ □ （　       　　）"
            elif pay_method == "振込":
                ws.Range("AT17").Value = "□ 現金 ・ ■ 振込 ・ □ （　       　　）"
            else:
                ws.Range("AT17").Value = "□ 現金 ・ □ 振込 ・ ■ （　" + pay_method + "　）"
                
            if self.attached_pdf and self.pdf_page_var.get() != "結合しない":
                ws.Range("AS18").Value = "■見積書"
            else:
                ws.Range("AS18").Value = "□見積書"
                
            if self.attached_images and self.img_page_var.get() != "挿入しない":
                ws.Range("AS19").Value = "■サイト画像"
            else:
                ws.Range("AS19").Value = "□サイト画像"
                
            ws.Range("AS20").Value = "□その他"
            
            # ①エリアへの書き込み (B15:B20) - 1行最大40文字、最大6行制限を厳格に適用
            formatted_lines_1 = split_text_by_chars(reason_text, 40)
            max_write_lines_1 = min(len(formatted_lines_1), 6)
            for i in range(max_write_lines_1):
                ws.Range("B" + str(15 + i)).Value = formatted_lines_1[i]
                
            # ②エリアへの書き込み
            ws.Range("B22").Value = "■目的"
            purpose_text = self.memo_text.get("1.0", tk.END).strip()
            if "例: 経年劣化による液晶の不具合" in purpose_text or not purpose_text:
                purpose_text = "業務継続性の確保および老朽化に伴うトラブルの未然防止のため、機器の更新を行います。"
            
            # 目的: 1行最大55文字、最大5行制限
            purpose_lines = split_text_by_chars(purpose_text, 55)
            max_write_purpose = min(len(purpose_lines), 5)
            for i in range(max_write_purpose):
                ws.Range("C" + str(23 + i)).Value = purpose_lines[i]
                
            # 実施内容: 表示方法をC列(幅広セル)に統一して流し込み、PDF化時のはみ出しを防止
            ws.Range("B28").Value = "■"
            ws.Range("C28").Value = "実施内容"
            
            # 金額情報の数値変換
            ex_tax_str = self.amount_ex_tax_var.get().strip()
            in_tax_str = self.amount_in_tax_var.get().strip()
            ex_val = 0
            in_val = 0
            try:
                ex_val = int("".join([c for c in ex_tax_str if c.isdigit()]))
                in_val = int("".join([c for c in in_tax_str if c.isdigit()]))
            except:
                pass
            tax_val = in_val - ex_val
            
            # 表示テキストのリスト構築 (商品名、取引先、金額などを1列の改行テキストにまとめる)
            model = self.model_info_var.get().strip() or subject
            pur = self.purchase_var.get().strip() or "別途選定"
            deliv = self.delivery_date_var.get().strip()
            
            detail_lines = []
            detail_lines.append(f"・商品　　：{model}")
            detail_lines.append(f"  取引先　：{pur}")
            detail_lines.append(f"  購入数　：1台")
            detail_lines.append(f"  購入金額：{ex_val:,}円 (税込 {in_val:,}円) [内税:{tax_val:,}円]")
            detail_lines.append(f"  希望納期：{deliv}")
            
            # C29から最大C36までの範囲(最大8行)に、55文字で折り返しながら順次書き込み
            current_row = 29
            for d_line in detail_lines:
                wrapped_lines = split_text_by_chars(d_line, 55)
                for wl in wrapped_lines:
                    if current_row <= 36:
                        ws.Cells(current_row, 3).Value = wl
                        current_row += 1
                        
            # 余ったC列の行をクリア
            for r in range(current_row, 37):
                ws.Cells(r, 3).Value = ""
                
            # 効果の書き込み: 1行最大55文字、最大2行制限
            ws.Range("B37").Value = "■対応の効果について"
            effect_text = self.effect_var.get().strip()
            effect_lines = split_text_by_chars(effect_text, 55)
            max_write_effect = min(len(effect_lines), 2)
            for i in range(max_write_effect):
                ws.Range("C" + str(38 + i)).Value = effect_lines[i]
            
                        # 画像をExcelに直接挿入するかどうか
            if self.attached_images and not is_pdf_mode:
                # PDFモードではない(Excelのみ出力)場合は、シート上に貼り付ける
                current_cell = ws.Range("BH5")
                current_top = current_cell.Top
                left_pos = current_cell.Left
                for img_path in self.attached_images:
                    norm_path = os.path.normpath(os.path.abspath(img_path))
                    if not os.path.exists(norm_path): continue
                    with Image.open(norm_path) as img:
                        orig_w, orig_h = img.size
                    max_w = 500
                    if orig_w > max_w:
                        w = max_w
                        h = int(orig_h * (max_w / orig_w))
                    else:
                        w = orig_w
                        h = orig_h
                    ws.Shapes.AddPicture(norm_path, False, True, left_pos, current_top, w, h)
                    current_top += h + 20
            
            wb.Save()
            if is_pdf_mode:
                pdf_path = output_excel_path.replace(".xlsx", ".pdf")
                wb.ActiveSheet.ExportAsFixedFormat(0, pdf_path)
                wb.Close(False)
                excel_app.Quit()
                return pdf_path
            else:
                wb.Close(False)
                excel_app.Quit()
                return output_excel_path
                
        except Exception as e:
            if excel_app is not None:
                try:
                    excel_app.Quit()
                except:
                    pass
            messagebox.showerror("エラー", f"Excel出力に失敗しました:\n{e}")
            return False


    def convert_saved_excel_to_pdf(self):
        target_excel = self.last_saved_excel_path
        if not target_excel or not os.path.exists(target_excel):
            target_excel = filedialog.askopenfilename(
                title="PDF化するExcelファイルを選択",
                filetypes=[("Excel Files", "*.xlsx;*.xls")]
            )
            if not target_excel: return
            self.last_saved_excel_path = target_excel
            
        default_filename = os.path.splitext(os.path.basename(target_excel))[0] + ".pdf"
        output_pdf_path = filedialog.asksaveasfilename(
            title="提出用PDFを保存",
            initialdir=os.path.dirname(target_excel),
            initialfile=default_filename,
            filetypes=[("PDF Files", "*.pdf")]
        )
        if not output_pdf_path: return
        
        progress_win = tk.Toplevel(self.root)
        progress_win.title("処理中")
        progress_win.geometry("320x130")
        progress_win.transient(self.root)
        progress_win.grab_set()
        lbl = ctk.CTkLabel(progress_win, text="ExcelをPDFへ変換・結合中...", font=("Meiryo", 9, "bold"))
        lbl.pack(pady=20)
        self.root.update()
        
        temp_pdf = os.path.join(os.path.dirname(output_pdf_path), f"temp_conv_{datetime.now().strftime('%H%M%S')}.pdf")
        
        excel_app = None
        try:
            import win32com.client
            excel_app = win32com.client.DispatchEx("Excel.Application")
            excel_app.Visible = False
            excel_app.DisplayAlerts = False
            
            wb = excel_app.Workbooks.Open(target_excel)
            wb.ActiveSheet.ExportAsFixedFormat(0, temp_pdf)
            wb.Close(False)
            excel_app.Quit()
            excel_app = None
            
            # 結合処理
            try:
                from PyPDF2 import PdfMerger
                from PIL import Image
                merger = PdfMerger()
                merger.append(temp_pdf)
                
                # 画像のPDF化
                img_pdf_path = None
                if self.attached_images and self.img_page_var.get() != "挿入しない":
                    img_pdf_path = temp_pdf.replace(".pdf", "_img.pdf")
                    img_list = []
                    for img_p in self.attached_images:
                        if os.path.exists(img_p):
                            img = Image.open(img_p).convert("RGB")
                            img_list.append(img)
                    if img_list:
                        img_list[0].save(img_pdf_path, save_all=True, append_images=img_list[1:])
                
                # 追加ページの順序設定
                pages = {"2ページ目": [], "3ページ目": [], "4ページ目": []}
                if img_pdf_path and self.img_page_var.get() in pages:
                    pages[self.img_page_var.get()].append(img_pdf_path)
                if self.attached_pdf and self.pdf_page_var.get() in pages:
                    pages[self.pdf_page_var.get()].append(self.attached_pdf)
                
                for k in ["2ページ目", "3ページ目", "4ページ目"]:
                    for p in pages[k]:
                        merger.append(p)
                        
                merger.write(output_pdf_path)
                merger.close()
                
                # 一時ファイル削除
                try:
                    os.remove(temp_pdf)
                    if img_pdf_path and os.path.exists(img_pdf_path):
                        os.remove(img_pdf_path)
                except:
                    pass
            except Exception as e:
                import shutil
                shutil.copy(temp_pdf, output_pdf_path)
                print(f"PDF結合エラー: {e}")
                
            progress_win.destroy()
            messagebox.showinfo("成功", f"手直ししたExcelのPDF変換・結合が完了しました！\n出力先:\n{output_pdf_path}")
            
        except Exception as e:
            if excel_app is not None:
                try:
                    excel_app.Quit()
                except:
                    pass
            progress_win.destroy()
            messagebox.showerror("エラー", f"変換に失敗しました:\n{e}")

    def generate_ringi_excel(self):
        subject = self.subject_var.get().strip() or "稟議書"
        default_filename = f"{datetime.now().strftime('%Y%m%d')}_{subject}_④稟議書（システム関連,社長決裁）.xlsx"
        output_excel_path = filedialog.asksaveasfilename(
            title="Excel稟議書を保存",
            initialdir=DEFAULT_OUTPUT_DIR,
            initialfile=default_filename,
            filetypes=[("Excel Files", "*.xlsx")]
        )
        if not output_excel_path: return
        
        res = self.write_excel_common(output_excel_path, is_pdf_mode=False)
        if res:
            messagebox.showinfo("成功", f"稟議書Excelの作成が完了しました！\n出力先:\n{res}")

    def generate_ringi_document(self):
        subject = self.subject_var.get().strip() or "稟議書"
        default_filename = f"{datetime.now().strftime('%Y%m%d')}_{subject}_④稟議書（システム関連,社長決裁）.pdf"
        output_pdf_path = filedialog.asksaveasfilename(
            title="提出用PDFを保存",
            initialdir=DEFAULT_OUTPUT_DIR,
            initialfile=default_filename,
            filetypes=[("PDF Files", "*.pdf")]
        )
        if not output_pdf_path: return
        
        progress_win = tk.Toplevel(self.root)
        progress_win.title("処理中")
        progress_win.geometry("320x130")
        progress_win.transient(self.root)
        progress_win.grab_set()
        lbl = ctk.CTkLabel(progress_win, text="稟議書を作成しています...\n(Excel・PDF処理中)", font=("Meiryo", 9, "bold"))
        lbl.pack(pady=20)
        self.root.update()
        
        temp_excel = os.path.join(os.path.dirname(output_pdf_path), f"temp_{datetime.now().strftime('%H%M%S')}.xlsx")
        
        try:
            main_pdf_path = self.write_excel_common(temp_excel, is_pdf_mode=True)
            if not main_pdf_path:
                progress_win.destroy()
                return
                
            # PDF結合処理
            try:
                from PyPDF2 import PdfMerger
                merger = PdfMerger()
                merger.append(main_pdf_path)
                
                # 画像のPDF化
                img_pdf_path = None
                if self.attached_images and self.img_page_var.get() != "挿入しない":
                    img_pdf_path = temp_excel.replace(".xlsx", "_img.pdf")
                    # 画像をPillowでPDFとして保存
                    img_list = []
                    for img_p in self.attached_images:
                        if os.path.exists(img_p):
                            img = Image.open(img_p).convert("RGB")
                            img_list.append(img)
                    if img_list:
                        img_list[0].save(img_pdf_path, save_all=True, append_images=img_list[1:])
                
                # 追加ページの順序設定
                pages = {"2ページ目": [], "3ページ目": [], "4ページ目": []}
                
                if img_pdf_path and self.img_page_var.get() in pages:
                    pages[self.img_page_var.get()].append(img_pdf_path)
                    
                if self.attached_pdf and self.pdf_page_var.get() in pages:
                    pages[self.pdf_page_var.get()].append(self.attached_pdf)
                
                # 順番にマージ
                for k in ["2ページ目", "3ページ目", "4ページ目"]:
                    for p in pages[k]:
                        merger.append(p)
                        
                merger.write(output_pdf_path)
                merger.close()
                
                # 不要な一時ファイルの削除
                try:
                    os.remove(temp_excel)
                    os.remove(main_pdf_path)
                    if img_pdf_path and os.path.exists(img_pdf_path):
                        os.remove(img_pdf_path)
                except:
                    pass
                    
            except Exception as e:
                # pypdf がない場合などのフォールバック
                import shutil
                shutil.copy(main_pdf_path, output_pdf_path)
                print(f"PDF結合エラー: {e}")
                
            progress_win.destroy()
            messagebox.showinfo("成功", f"稟議書PDFの作成・結合が完了しました！\n出力先:\n{output_pdf_path}")
            
        except Exception as e:
            progress_win.destroy()
            messagebox.showerror("エラー", f"予期せぬエラーが発生しました:\n{e}")

    def on_use_case_change(self, choice):
        self.apply_use_case_template_replacement()
        
    def apply_use_case_template_replacement(self):
        choice = self.use_case_var.get()
        if choice == "✨ カスタム (自由に手書き)":
            return
            
        json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ringi_text_templates.json")
        if not os.path.exists(json_path):
            json_path = "ringi_text_templates.json"
        if not os.path.exists(json_path):
            return
            
        try:
            import json
            with open(json_path, "r", encoding="utf-8") as f:
                templates = json.load(f)
        except Exception as e:
            print("Error loading json in replacement:", e)
            return
            
        key_map = {
            "💻 パソコン購入・更新": "PC購入・更新",
            "🖥️ ディスプレイ・モニター購入": "モニター・ディスプレイ購入",
            "🔌 周辺機器・ネットワーク機器": "その他・周辺機器",
            "💿 ソフトウェア・ライセンス": "ソフトウェア・ライセンス"
        }
        
        json_key = key_map.get(choice)
        if not json_key or json_key not in templates:
            return
            
        tpl_data = templates[json_key]
        reason = tpl_data.get("reason", "")
        purpose = tpl_data.get("purpose", "")
        effect = tpl_data.get("effect", "")
        
        # 最新のUI入力値を取得
        new_model = self.model_info_var.get().strip() or self.subject_var.get().strip() or "最新ノートPC"
        new_purchase = self.purchase_var.get().strip() or "別途選定"
        new_amount_in = self.amount_in_tax_var.get().strip() or self.amount_var.get().strip() or "価格確認中"
        new_amount_ex = self.amount_ex_tax_var.get().strip() or "価格確認中"
        
        # 過去のテンプレート情報を最新情報で置換
        if json_key == "PC購入・更新":
            reason = reason.replace("フォーレスト専用ノートPC", new_model)
            reason = reason.replace("HP製端末", new_model)
            purpose = purpose.replace("HP ELITEBOOK 630 G10 CT", new_model)
            purpose = purpose.replace("HP EliteBook 630 G10 Notebook PC", new_model)
            
            reason = reason.replace("エディオン", new_purchase)
            purpose = purpose.replace("株式会社EDIONクロスベンチャーズ", new_purchase)
            purpose = purpose.replace("エディオン", new_purchase)
            
            reason = reason.replace("169,073円", new_amount_ex)
            purpose = purpose.replace("140,000円", new_amount_ex)
            purpose = purpose.replace("154,000円", new_amount_in)
            purpose = purpose.replace("185,980円", new_amount_in)
            
        elif json_key == "モニター・ディスプレイ購入":
            reason = reason.replace("高解像度 （2560x1440）のモニター", f"モニター（{new_model}）")
            purpose = purpose.replace("高解像度：2560x1440以上", f"仕様：{new_model}")
            
        elif json_key == "ソフトウェア・ライセンス":
            reason = reason.replace("AIプレゼンツール【Gamma】", f"【{new_model}】")
            reason = reason.replace("【Gamma】", f"【{new_model}】")
            purpose = purpose.replace("Gamma", new_model)
            
        elif json_key == "その他・周辺機器":
            reason = reason.replace("Firepower1010", new_model)
            purpose = purpose.replace("Firepower1010", new_model)
            
        # テキストエリアへ流し込み
        self.reason_preview.delete("1.0", tk.END)
        self.reason_preview.insert(tk.END, reason)
        
        self.memo_text.delete("1.0", tk.END)
        self.memo_text.insert(tk.END, purpose)
        
        if effect:
            self.effect_var.set(effect)

if __name__ == '__main__':
    ctk.set_appearance_mode('System')
    ctk.set_default_color_theme('blue')
    root = ctk.CTk()
    app = RingiToolApp(root)
    root.mainloop()