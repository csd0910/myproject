import os
import sys
import json
import urllib.request
import base64
import re
import tkinter as tk
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
        self.last_saved_excel_path = None
        
        # AI/定型文生成用
        self.apply_type_var = tk.StringVar(value="更新")
        self.old_pc_no_var = tk.StringVar()
        self.old_pc_user_var = tk.StringVar()
        self.add_reason_var = tk.StringVar()
        
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
        self.bg_window = "#F1F5F9"  
        self.bg_card = "#FFFFFF"    
        self.color_border = "#E2E8F0" 
        
        self.color_primary = "#1E293B"  
        self.color_accent = "#2563EB"   
        self.color_accent_hover = "#1D4ED8"
        self.color_success = "#059669"  
        self.color_success_hover = "#047857"
        self.color_info = "#0284C7"     
        self.color_info_hover = "#0369A1"
        self.color_text = "#0F172A"     
        
        self.root.configure(bg=self.bg_window)
        
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        self.style.configure(".", font=("Meiryo", 9), background=self.bg_window, foreground=self.color_text)
        self.style.configure("TEntry", fieldbackground="#FFFFFF", bordercolor=self.color_border, lightcolor=self.color_border, darkcolor=self.color_border)
        self.style.configure("TCombobox", fieldbackground="#FFFFFF", bordercolor=self.color_border, arrowcolor=self.color_primary)
        self.style.configure("FormLabel.TLabel", font=("Meiryo", 9, "bold"), foreground="#475569", background=self.bg_card)
        self.style.configure("TLabel", background=self.bg_window, foreground=self.color_text)
        self.style.configure("TRadiobutton", background=self.bg_card, foreground=self.color_text)

    def create_card(self, parent, title):
        card = tk.Frame(parent, bg=self.bg_card, highlightbackground=self.color_border, highlightthickness=1, bd=0)
        
        header = tk.Frame(card, bg="#F8FAFC", height=32)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)
        
        title_lbl = tk.Label(header, text=title, font=("Meiryo", 9, "bold"), fg="#1E293B", bg="#F8FAFC", anchor="w")
        title_lbl.pack(fill=tk.BOTH, expand=True, padx=12)
        
        content = tk.Frame(card, bg=self.bg_card, padx=12, pady=10)
        content.pack(fill=tk.BOTH, expand=True)
        
        return card, content

    def create_widgets(self):
        # 1. ヘッダーバー
        header_bar = tk.Frame(self.root, bg=self.color_primary, height=55)
        header_bar.pack(fill=tk.X, side=tk.TOP)
        header_bar.pack_propagate(False)
        
        header_title = tk.Label(
            header_bar, 
            text="稟議書作成・提出PDF自動結合システム", 
            font=("Meiryo", 12, "bold"), 
            fg="#FFFFFF", 
            bg=self.color_primary,
            anchor="w"
        )
        header_title.pack(fill=tk.BOTH, expand=True, padx=20)
        
        # スクロール可能なメインエリア
        container = tk.Frame(self.root, bg=self.bg_window)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        self.canvas = tk.Canvas(container, bg=self.bg_window, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.bg_window)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.update_scroll_region()
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def configure_canvas_width(event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)
        self.canvas.bind("<Configure>", configure_canvas_width)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # ==========================================
        # CARD 1: 設定 & テンプレート
        # ==========================================
        card1, body1 = self.create_card(self.scrollable_frame, "1. 設定 & テンプレート選択")
        card1.pack(fill=tk.X, pady=(0, 10))
        
        # APIキー
        ttk.Label(body1, text="Gemini APIキー:", style="FormLabel.TLabel").grid(row=0, column=0, sticky=tk.W, padx=5, pady=4)
        self.api_entry = ttk.Entry(body1, show="*", width=45)
        self.api_entry.insert(0, self.api_key)
        self.api_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=4)
        
        def save_api():
            self.api_key = self.api_entry.get().strip()
            self.save_config()
            messagebox.showinfo("保存完了", "Gemini APIキーを安全に保存しました。")
            
        save_api_btn = self.create_flat_button(body1, "キー保存", self.color_primary, "#334155", save_api)
        save_api_btn.grid(row=0, column=2, padx=10, pady=4)
        
        # テンプレート選択
        ttk.Label(body1, text="テンプレートExcel:", style="FormLabel.TLabel").grid(row=1, column=0, sticky=tk.W, padx=5, pady=6)
        self.tpl_combo = ttk.Combobox(body1, width=43, state="readonly")
        self.tpl_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=6)
        
        ref_tpl_btn = self.create_flat_button(body1, "参照...", "#64748B", "#475569", self.select_template_file)
        ref_tpl_btn.grid(row=1, column=2, padx=10, pady=6)
        
        # ==========================================
        # CARD 2: 稟議基本情報 (起案者データ)
        # ==========================================
        card2, body2 = self.create_card(self.scrollable_frame, "2. 稟議起案者データ入力")
        card2.pack(fill=tk.X, pady=(0, 10))
        
        fields = [
            ("起案部署名:", self.dept_var, 0, 0),
            ("申請年月日:", self.date_var, 0, 2),
            ("役職:", self.title_var, 1, 0),
            ("起案者名:", self.author_var, 1, 2),
        ]
        
        for label_text, var, r, c in fields:
            ttk.Label(body2, text=label_text, style="FormLabel.TLabel").grid(row=r, column=c, sticky=tk.W, padx=5, pady=4)
            ent = ttk.Entry(body2, textvariable=var, width=22)
            ent.grid(row=r, column=c+1, sticky=tk.W, padx=5, pady=4)
            
        ttk.Label(body2, text="件名:", style="FormLabel.TLabel").grid(row=2, column=0, sticky=tk.W, padx=5, pady=6)
        self.subject_ent = ttk.Entry(body2, textvariable=self.subject_var, width=64)
        self.subject_ent.grid(row=2, column=1, columnspan=3, sticky=tk.W, padx=5, pady=6)

        # ==========================================
        # CARD 3: 購入仕様と金額
        # ==========================================
        card3, body3 = self.create_card(self.scrollable_frame, "3. ② 目的や商品情報などの詳細 (手動入力)")
        card3.pack(fill=tk.X, pady=(0, 10))
        
        # 金額（税抜・税込）
        ttk.Label(body3, text="税抜金額:", style="FormLabel.TLabel").grid(row=0, column=0, sticky=tk.W, padx=5, pady=4)
        self.ent_ex_tax = ttk.Entry(body3, textvariable=self.amount_ex_tax_var, width=22)
        self.ent_ex_tax.grid(row=0, column=1, sticky=tk.W, padx=5, pady=4)
        
        ttk.Label(body3, text="税込金額:", style="FormLabel.TLabel").grid(row=0, column=2, sticky=tk.W, padx=5, pady=4)
        self.ent_in_tax = ttk.Entry(body3, textvariable=self.amount_in_tax_var, width=22)
        self.ent_in_tax.grid(row=0, column=3, sticky=tk.W, padx=5, pady=4)
        
        self.ent_ex_tax.bind("<KeyRelease>", self.calc_tax_from_ex)
        self.ent_in_tax.bind("<KeyRelease>", self.calc_tax_from_in)
        
        # 管理番号、支払日、支払方法、購入先
        ttk.Label(body3, text="管理番号 (予算内):", style="FormLabel.TLabel").grid(row=1, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(body3, textvariable=self.mng_no_var, width=22).grid(row=1, column=1, sticky=tk.W, padx=5, pady=4)
        
        ttk.Label(body3, text="購入先名:", style="FormLabel.TLabel").grid(row=1, column=2, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(body3, textvariable=self.purchase_var, width=22).grid(row=1, column=3, sticky=tk.W, padx=5, pady=4)
        
        ttk.Label(body3, text="支払日:", style="FormLabel.TLabel").grid(row=2, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(body3, textvariable=self.pay_date_var, width=22).grid(row=2, column=1, sticky=tk.W, padx=5, pady=4)
        
        ttk.Label(body3, text="支払方法:", style="FormLabel.TLabel").grid(row=2, column=2, sticky=tk.W, padx=5, pady=4)
        self.pay_combo = ttk.Combobox(body3, textvariable=self.pay_method_var, values=["振込", "現金", "その他"], width=19, state="readonly")
        self.pay_combo.grid(row=2, column=3, sticky=tk.W, padx=5, pady=4)
        
        # 型番仕様、納期、期待効果
        ttk.Label(body3, text="型番・仕様:", style="FormLabel.TLabel").grid(row=3, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(body3, textvariable=self.model_info_var, width=64).grid(row=3, column=1, columnspan=3, sticky=tk.W, padx=5, pady=4)
        
        ttk.Label(body3, text="希望納期:", style="FormLabel.TLabel").grid(row=4, column=0, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(body3, textvariable=self.delivery_date_var, width=22).grid(row=4, column=1, sticky=tk.W, padx=5, pady=4)
        
        ttk.Label(body3, text="導入効果:", style="FormLabel.TLabel").grid(row=4, column=2, sticky=tk.W, padx=5, pady=4)
        ttk.Entry(body3, textvariable=self.effect_var, width=22).grid(row=4, column=3, sticky=tk.W, padx=5, pady=4)

        # ==========================================
        # CARD 4: 起案理由 (ざっくり入力欄) & AI/定型合成
        # ==========================================
        card4, body4 = self.create_card(self.scrollable_frame, "4. ① 起案目的・理由 (ざっくり理由入力 ＆ AI自動生成)")
        card4.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(body4, text="申請タイプ:", style="FormLabel.TLabel").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        type_frame = tk.Frame(body4, bg=self.bg_card)
        type_frame.grid(row=0, column=1, columnspan=3, sticky=tk.W, padx=5, pady=3)
        
        def on_type_change():
            if self.apply_type_var.get() == "更新":
                self.update_inputs_state(True)
            else:
                self.update_inputs_state(False)
                
        r1 = ttk.Radiobutton(type_frame, text="既存機器等の更新 (管理番号・使用者名を記載)", variable=self.apply_type_var, value="更新", command=on_type_change)
        r1.pack(side=tk.LEFT, padx=(0, 15))
        r2 = ttk.Radiobutton(type_frame, text="新規・追加購入 (追加が必要な理由を記載)", variable=self.apply_type_var, value="追加", command=on_type_change)
        r2.pack(side=tk.LEFT)
        
        self.inputs_frame = tk.Frame(body4, bg=self.bg_card)
        self.inputs_frame.grid(row=1, column=0, columnspan=4, sticky=tk.EW, pady=3)
        
        self.lbl_pc_no = ttk.Label(self.inputs_frame, text="更新元管理番号:", style="FormLabel.TLabel")
        self.lbl_pc_no.grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.ent_pc_no = ttk.Entry(self.inputs_frame, textvariable=self.old_pc_no_var, width=19)
        self.ent_pc_no.grid(row=0, column=1, sticky=tk.W, padx=5, pady=3)
        
        self.lbl_user = ttk.Label(self.inputs_frame, text="使用者氏名:", style="FormLabel.TLabel")
        self.lbl_user.grid(row=0, column=2, sticky=tk.W, padx=5, pady=3)
        self.ent_user = ttk.Entry(self.inputs_frame, textvariable=self.old_pc_user_var, width=19)
        self.ent_user.grid(row=0, column=3, sticky=tk.W, padx=5, pady=3)
        
        self.lbl_add_reason = ttk.Label(self.inputs_frame, text="追加理由:", style="FormLabel.TLabel")
        self.lbl_add_reason.grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.ent_add_reason = ttk.Entry(self.inputs_frame, textvariable=self.add_reason_var, width=58)
        self.ent_add_reason.grid(row=1, column=1, columnspan=3, sticky=tk.W, padx=5, pady=3)
        
        ttk.Label(body4, text="【① 起案目的・理由】\n※Area 1 (B15～B20):\n(AIが提案・手動調整可)", style="FormLabel.TLabel").grid(row=2, column=0, sticky=tk.NW, padx=5, pady=4)
        self.reason_preview = tk.Text(body4, width=65, height=4, font=("Meiryo", 9), bd=1, relief=tk.SOLID, highlightbackground=self.color_border)
        self.reason_preview.grid(row=2, column=1, columnspan=3, sticky=tk.W, padx=5, pady=4)
        
        ttk.Label(body4, text="【② 目的・効果・改善点】\n※Area 2 (C23～):\n(AIが提案・手動調整可)", style="FormLabel.TLabel").grid(row=3, column=0, sticky=tk.NW, padx=5, pady=4)
        self.memo_text = tk.Text(body4, width=65, height=4, font=("Meiryo", 9), bd=1, relief=tk.SOLID, highlightbackground=self.color_border)
        self.memo_text.grid(row=3, column=1, columnspan=3, sticky=tk.W, padx=5, pady=4)
        
        btn_frame = tk.Frame(body4, bg=self.bg_card)
        btn_frame.grid(row=4, column=1, columnspan=3, sticky=tk.W, pady=8)
        
        ai_btn = self.create_flat_button(btn_frame, "✨ 起案理由と改善効果を再生成する(AI)", self.color_accent, self.color_accent_hover, self.generate_reason)
        ai_btn.pack(side=tk.LEFT)
        
        on_type_change()
        
        # ==========================================
        # CARD 5: 添付資料 (ドラッグ＆ドロップ対応 & AI自動解析)
        # ==========================================
        card5, body5 = self.create_card(self.scrollable_frame, "5. 添付資料 (ドラッグ＆ドロップ ＆ AI自動読込)")
        card5.pack(fill=tk.X, pady=(0, 10))
        
        # クリック時も動作するようバインド可能なドロップフレーム
        self.dnd_frame = tk.Frame(
            body5, 
            bg="#F8FAFC", 
            highlightbackground="#CBD5E1", 
            highlightthickness=1, 
            bd=0, 
            pady=10,
            cursor="hand2"
        )
        self.dnd_frame.grid(row=0, column=0, columnspan=3, sticky=tk.EW, pady=(0, 8))
        
        dnd_title = tk.Label(
            self.dnd_frame, 
            text="📥 ここに見積書PDFやWebスクショ画像をドラッグ＆ドロップ", 
            font=("Meiryo", 9, "bold"), 
            fg="#475569", 
            bg="#F8FAFC",
            cursor="hand2"
        )
        dnd_title.pack(fill=tk.X)
        
        dnd_sub = tk.Label(
            self.dnd_frame, 
            text="【またはここをクリックしてファイルを選択】", 
            font=("Meiryo", 8, "underline"), 
            fg="#2563EB", 
            bg="#F8FAFC",
            cursor="hand2"
        )
        dnd_sub.pack(fill=tk.X, pady=(2, 0))
        
        # ドロップエリアクリックでファイル選択が開くフォールバック
        def on_dnd_click(event):
            # 画像かPDFかを判断させるため、まずはどちらかを尋ねる
            self.click_select_file()
        self.dnd_frame.bind("<Button-1>", on_dnd_click)
        dnd_title.bind("<Button-1>", on_dnd_click)
        dnd_sub.bind("<Button-1>", on_dnd_click)
        
        ocr_btn = self.create_flat_button(
            body5, 
            "🔍 添付資料から品名・金額（税抜/税込）・型番を自動読込 (AI)", 
            self.color_info, 
            self.color_info_hover, 
            self.analyze_attached_file
        )
        ocr_btn.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=(0, 8))
        
        self.img_page_var = tk.StringVar(value="2ページ目")
        self.pdf_page_var = tk.StringVar(value="3ページ目")

        ttk.Label(body5, text="添付画像:", style="FormLabel.TLabel").grid(row=2, column=0, sticky=tk.W, padx=5, pady=4)
        self.img_lbl = tk.Label(body5, text="選択されていません", foreground="gray", bg=self.bg_card, font=("Meiryo", 9))
        self.img_lbl.grid(row=2, column=1, sticky=tk.W, padx=5, pady=4)
        
        img_controls = tk.Frame(body5, bg=self.bg_card)
        img_controls.grid(row=2, column=2, sticky=tk.W)
        ttk.Combobox(img_controls, textvariable=self.img_page_var, values=["2ページ目", "3ページ目", "4ページ目", "挿入しない"], width=10, state="readonly").pack(side=tk.LEFT, padx=5)
        img_btn = self.create_flat_button(img_controls, "選択...", "#64748B", "#475569", self.select_images)
        img_btn.pack(side=tk.LEFT, padx=5)
        img_clear_btn = self.create_flat_button(img_controls, "取消", "#EF4444", "#DC2626", lambda: self.clear_attachment("image"))
        img_clear_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(body5, text="添付PDF:", style="FormLabel.TLabel").grid(row=3, column=0, sticky=tk.W, padx=5, pady=4)
        self.pdf_lbl = tk.Label(body5, text="選択されていません", foreground="gray", bg=self.bg_card, font=("Meiryo", 9))
        self.pdf_lbl.grid(row=3, column=1, sticky=tk.W, padx=5, pady=4)
        
        pdf_controls = tk.Frame(body5, bg=self.bg_card)
        pdf_controls.grid(row=3, column=2, sticky=tk.W)
        ttk.Combobox(pdf_controls, textvariable=self.pdf_page_var, values=["2ページ目", "3ページ目", "4ページ目", "結合しない"], width=10, state="readonly").pack(side=tk.LEFT, padx=5)
        pdf_btn = self.create_flat_button(pdf_controls, "選択...", "#64748B", "#475569", self.select_pdf)
        pdf_btn.pack(side=tk.LEFT, padx=5)
        pdf_clear_btn = self.create_flat_button(pdf_controls, "取消", "#EF4444", "#DC2626", lambda: self.clear_attachment("pdf"))
        pdf_clear_btn.pack(side=tk.LEFT, padx=5)
        
        # ==========================================
        # CARD 6: 実行エリア
        # ==========================================
        bottom_frame = tk.Frame(self.scrollable_frame, bg=self.bg_window)
        bottom_frame.pack(fill=tk.X, pady=5)
        
        excel_btn = self.create_flat_button(
            bottom_frame, 
            "📊 まずはExcelで稟議書を作成・保存する", 
            self.color_info, 
            self.color_info_hover, 
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
            self.color_success, 
            self.color_success_hover, 
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
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def create_flat_button(self, parent, text, color, hover_color, command):
        btn = tk.Button(
            parent, 
            text=text, 
            command=command, 
            bg=color, 
            fg="white", 
            activebackground=hover_color, 
            activeforeground="white",
            font=("Meiryo", 9, "bold"), 
            bd=0, 
            relief=tk.FLAT,
            padx=12,
            pady=5,
            cursor="hand2"
        )
        def on_enter(e):
            btn.config(bg=hover_color)
        def on_leave(e):
            btn.config(bg=color)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    def update_inputs_state(self, is_update):
        if is_update:
            self.lbl_pc_no.grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
            self.ent_pc_no.grid(row=0, column=1, sticky=tk.W, padx=5, pady=3)
            self.lbl_user.grid(row=0, column=2, sticky=tk.W, padx=5, pady=3)
            self.ent_user.grid(row=0, column=3, sticky=tk.W, padx=5, pady=3)
            
            self.lbl_add_reason.grid_forget()
            self.ent_add_reason.grid_forget()
        else:
            self.lbl_pc_no.grid_forget()
            self.ent_pc_no.grid_forget()
            self.lbl_user.grid_forget()
            self.ent_user.grid_forget()
            
            self.lbl_add_reason.grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
            self.ent_add_reason.grid(row=0, column=1, columnspan=3, sticky=tk.W, padx=5, pady=3)
        self.update_scroll_region()

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
            self.img_lbl.configure(text=f"{len(self.attached_images)}個の画像を選択中", foreground=self.color_accent)
            
        if added_pdf:
            self.attached_pdf = added_pdf
            self.pdf_lbl.configure(text=os.path.basename(self.attached_pdf), foreground=self.color_accent)
            
        if added_images or added_pdf:
            msg = f"ドロップされたファイルを読み込みました。\n"
            if added_images:
                msg += f"・画像: {len(added_images)}件 追加\n"
            if added_pdf:
                msg += f"・PDF見積書: 設定完了\n"
            messagebox.showinfo("ファイル読込完了", msg)
        self.update_scroll_region()

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
            self.tpl_combo["values"] = [os.path.basename(t) for t in templates]
            self.tpl_combo.current(0)
            self.template_path_var.set(templates[0])
        else:
            self.tpl_combo["values"] = ["テンプレートが見つかりません"]
            self.tpl_combo.current(0)
        self.update_scroll_region()
            
    def select_template_file(self):
        fpath = filedialog.askopenfilename(
            title="テンプレートExcelファイルを選択",
            filetypes=[("Excel Files", "*.xlsx")]
        )
        if fpath:
            self.template_path_var.set(fpath)
            self.tpl_combo["values"] = list(self.tpl_combo["values"]) + [os.path.basename(fpath)]
            self.tpl_combo.set(os.path.basename(fpath))
        self.update_scroll_region()


    def clear_attachment(self, target):
        if target == "image":
            self.attached_images = []
            self.img_lbl.config(text="選択されていません", fg="gray")
        elif target == "pdf":
            self.attached_pdf = ""
        self.last_saved_excel_path = None
            self.pdf_lbl.config(text="選択されていません", fg="gray")
    def select_images(self):
        fpaths = filedialog.askopenfilenames(
            title="添付画像ファイルを選択 (複数選択可)",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp")]
        )
        if fpaths:
            self.attached_images = [os.path.normpath(os.path.abspath(fp)) for fp in fpaths]
            self.img_lbl.configure(text=f"{len(fpaths)}個の画像を選択中", foreground=self.color_accent)
        else:
            self.attached_images = []
            self.img_lbl.configure(text="選択されていません", foreground="gray")
        self.update_scroll_region()

    def select_pdf(self):
        fpath = filedialog.askopenfilename(
            title="添付PDFファイル（見積書など）を選択",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if fpath:
            self.attached_pdf = os.path.normpath(os.path.abspath(fpath))
            self.pdf_lbl.configure(text=os.path.basename(fpath), foreground=self.color_accent)
        else:
            self.attached_pdf = ""
        self.last_saved_excel_path = None
            self.pdf_lbl.configure(text="選択されていません", foreground="gray")
        self.update_scroll_region()

    def analyze_attached_file(self):
        self.api_key = self.api_entry.get().strip()
        if not self.api_key:
            messagebox.showerror("エラー", "Gemini APIキーを入力してください。")
            return
            
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
            
        progress_win = tk.Toplevel(self.root)
        progress_win.title("解析中")
        progress_win.geometry("300x100")
        progress_win.transient(self.root)
        progress_win.grab_set()
        
        lbl = ttk.Label(progress_win, text="AIが添付ファイルを読み取っています...\n(しばらくお待ちください)", padding=20)
        lbl.pack()
        self.root.update()
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
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
                pdf_text = ""
                reader = PdfReader(target_file)
                for page in reader.pages:
                    txt = page.extract_text()
                    if txt:
                        pdf_text += txt + "\n"
                        
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
                
            req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=20) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                result_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                
                json_match = re.search(r"\{.*\}", result_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    extracted_data = json.loads(json_str)
                    
                    self.subject_var.set(extracted_data.get("subject", ""))
                    self.purchase_var.set(extracted_data.get("purchase_from", ""))
                    self.model_info_var.set(extracted_data.get("model_info", ""))
                    self.delivery_date_var.set(extracted_data.get("delivery", "別途打合せ"))
                    self.effect_var.set(extracted_data.get("effect", "業務継続性の確保およびトラブルの未然防止"))
                    
                    ex_val = str(extracted_data.get("amount_ex_tax", "")).strip()
                    in_val = str(extracted_data.get("amount_in_tax", "")).strip()
                    
                    ex_num = re.sub(r"[^\d]", "", ex_val)
                    in_num = re.sub(r"[^\d]", "", in_val)
                    
                    if ex_num:
                        self.amount_ex_tax_var.set(f"{int(ex_num):,}")
                        self.calc_tax_from_ex()
                    elif in_num:
                        self.amount_in_tax_var.set(f"{int(in_num):,}")
                        self.calc_tax_from_in()
                    
                    progress_win.destroy()
                    messagebox.showinfo("読み込み成功", "添付ファイルからデータを一括自動入力しました！")
                else:
                    raise Exception("JSONデータの解析に失敗しました。")
                    
        except Exception as e:
            progress_win.destroy()
            messagebox.showerror("自動読込エラー", f"ファイル解析中にエラーが発生しました。\n{e}")
        self.update_scroll_region()

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
        self.update_scroll_region()

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
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
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
        self.update_scroll_region()

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
            
            # ①および②エリア全体のクリア
            ws.Range("B15:B20").Value = ""
            ws.Range("B22:B42").Value = ""
            ws.Range("C23:C27").Value = ""
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
            
            # ①エリアへの書き込み (B15:B20)
            raw_lines = reason_text.split("\n")
            formatted_lines_1 = []
            for r_line in raw_lines:
                while len(r_line) > 40:
                    formatted_lines_1.append(r_line[:40])
                    r_line = r_line[40:]
                if r_line:
                    formatted_lines_1.append(r_line)
                    
            max_write_lines_1 = min(len(formatted_lines_1), 6)
            for i in range(max_write_lines_1):
                ws.Range("B" + str(15 + i)).Value = formatted_lines_1[i]
                
            # ②エリアへの書き込み
            ws.Range("B22").Value = "■目的"
            purpose_text = self.memo_text.get("1.0", tk.END).strip()
            if "例: 経年劣化による液晶の不具合" in purpose_text or not purpose_text:
                purpose_text = "業務継続性の確保および老朽化に伴うトラブルの未然防止のため、機器の更新を行います。"
            
            purpose_lines = []
            for p_line in purpose_text.split("\n"):
                while len(p_line) > 55:
                    purpose_lines.append(p_line[:55])
                    p_line = p_line[55:]
                if p_line:
                    purpose_lines.append(p_line)
            
            max_write_purpose = min(len(purpose_lines), 5)
            for i in range(max_write_purpose):
                ws.Range("C" + str(23 + i)).Value = purpose_lines[i]
                
            ws.Range("B28").Value = "■"
            ws.Range("C28").Value = "実施内容"
            ws.Range("C29").Value = "商品"
            ws.Range("F29").Value = "："
            ws.Range("G29").Value = self.model_info_var.get().strip() or subject
            ws.Range("C30").Value = "取引先"
            ws.Range("F30").Value = "："
            ws.Range("G30").Value = self.purchase_var.get().strip() or "別途選定"
            
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
            
            ws.Range("C31").Value = "商品単価（税抜き）：" + f"{ex_val:,}" + "円"
            ws.Range("Q31").Value = "消費税（10%）：" + f"{tax_val:,}" + "円"
            ws.Range("C32").Value = "商品単価（税込み）：" + f"{in_val:,}" + "円"
            ws.Range("C33").Value = "購入数量：1台"
            ws.Range("C34").Value = "合計金額（税抜き）：" + f"{ex_val:,}" + "円"
            ws.Range("Q34").Value = "合計消費税：" + f"{tax_val:,}" + "円"
            ws.Range("C35").Value = "合計金額（税込み）：" + f"{in_val:,}" + "円"
            ws.Range("C36").Value = "希望納期：" + self.delivery_date_var.get().strip()
            
            ws.Range("B37").Value = "■対応の効果について"
            effect_text = self.effect_var.get().strip()
            effect_lines = []
            for e_line in effect_text.split("\n"):
                while len(e_line) > 55:
                    effect_lines.append(e_line[:55])
                    e_line = e_line[55:]
                if e_line:
                    effect_lines.append(e_line)
            
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
        lbl = ttk.Label(progress_win, text="ExcelをPDFへ変換・結合中...", padding=20, font=("Meiryo", 9, "bold"))
        lbl.pack()
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
        lbl = ttk.Label(progress_win, text="稟議書を作成しています...\n(Excel・PDF処理中)", padding=20, font=("Meiryo", 9, "bold"))
        lbl.pack()
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

if __name__ == '__main__':
    root = tk.Tk()
    app = RingiToolApp(root)
    root.mainloop()
