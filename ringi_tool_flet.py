import os
import sys
import json
import re
import base64
import asyncio
from datetime import datetime
import urllib.request
import urllib.error
import flet as ft
from PIL import Image
from PyPDF2 import PdfReader, PdfMerger
import win32com.client

# ==========================================
# 定数とデフォルトディレクトリの設定
# ==========================================
DEFAULT_TEMPLATE_DIR = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\006.稟議書\モニター4台購入の件"
DEFAULT_OUTPUT_DIR = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\006.稟議書\モニター4台購入の件"
CONFIG_FILE = "ringi_config.json"
TEMPLATES_JSON = "ringi_text_templates.json"


def split_text_by_chars(text, max_chars):
    """Excelのセル文字数制限に合わせてテキストを安全に分割する"""
    if not text:
        return []
    lines = text.replace("\r\n", "\n").split("\n")
    formatted_lines = []
    for line in lines:
        while len(line) > max_chars:
            formatted_lines.append(line[:max_chars])
            line = line[max_chars:]
        formatted_lines.append(line)
    return formatted_lines


# ==========================================
# メインアプリケーションクラス (Flet 0.86 async対応版)
# ==========================================
class RingiFletApp:
    def __init__(self):
        self.api_key = ""
        self.template_path = ""
        self.attached_images = []
        self.attached_pdf = ""
        self.last_saved_excel_path = ""
        self.page = None
        self.load_config()

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.api_key = cfg.get("api_key", "")
        except Exception:
            pass

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"api_key": self.api_key}, f, ensure_ascii=False)
        except Exception:
            pass

    async def main(self, page: ft.Page):
        self.page = page
        page.title = "稟議書作成システム"
        page.theme_mode = ft.ThemeMode.DARK
        page.window_width = 1200
        page.window_height = 950
        page.scroll = ft.ScrollMode.AUTO
        page.padding = 12

        # ------------------------------------------
        # コントロール定義
        # ------------------------------------------
        self.api_entry = ft.TextField(
            value=self.api_key,
            label="APIキー",
            password=True,
            can_reveal_password=True,
            width=200,
            height=45,
            text_size=12
        )

        self.use_case_combo = ft.Dropdown(
            label="📁 用途テンプレート",
            value="✨ カスタム (自由に手書き)",
            options=[
                ft.dropdown.Option("✨ カスタム (自由に手書き)"),
                ft.dropdown.Option("💻 パソコン購入・更新"),
                ft.dropdown.Option("🖥️ ディスプレイ・モニター購入"),
                ft.dropdown.Option("🔌 周辺機器・ネットワーク機器"),
                ft.dropdown.Option("💿 ソフトウェア・ライセンス"),
            ],
            width=230,
            text_size=12
        )
        self.use_case_combo.on_change = self.on_use_case_change

        self.tpl_combo = ft.Dropdown(
            label="テンプレートExcel",
            width=260,
            text_size=12
        )
        self.tpl_combo.on_change = self.on_template_combo_change

        # 基本起案者データ
        self.dept_entry = ft.TextField(label="起案部署名", value="システム部システム運営課", height=40, text_size=12, expand=True)
        self.date_entry = ft.TextField(label="申請年月日", value=datetime.now().strftime("%Y年%m月%d日"), height=40, text_size=12, expand=True)
        self.title_entry = ft.TextField(label="役職", value="主任", height=40, text_size=12, expand=True)
        self.author_entry = ft.TextField(label="起案者名", value="伊藤 健人", height=40, text_size=12, expand=True)
        self.subject_entry = ft.TextField(label="件名", value="", height=40, text_size=12, expand=True)

        self.img_lbl = ft.Text("選択されていません", color=ft.Colors.GREY_500, size=11)
        self.pdf_lbl = ft.Text("選択されていません", color=ft.Colors.GREY_500, size=11)

        self.img_page_combo = ft.Dropdown(
            value="2ページ目",
            options=[
                ft.dropdown.Option("2ページ目"),
                ft.dropdown.Option("3ページ目"),
                ft.dropdown.Option("4ページ目"),
                ft.dropdown.Option("挿入しない")
            ],
            width=110, text_size=11
        )
        self.pdf_page_combo = ft.Dropdown(
            value="3ページ目",
            options=[
                ft.dropdown.Option("2ページ目"),
                ft.dropdown.Option("3ページ目"),
                ft.dropdown.Option("4ページ目"),
                ft.dropdown.Option("結合しない")
            ],
            width=110, text_size=11
        )

        # 文章エリア
        self.reason_preview = ft.TextField(
            label="起案目的・理由文章 (最大6行・1行40文字制限)",
            multiline=True,
            min_lines=11, max_lines=11,
            text_size=13, expand=True
        )
        self.memo_text = ft.TextField(
            label="導入の目的 (最大5行・1行55文字制限)",
            multiline=True,
            min_lines=11, max_lines=11,
            text_size=13, expand=True
        )

        # 下部詳細グリッド
        self.ent_ex_tax = ft.TextField(label="税抜金額", value="", height=40, text_size=12)
        self.ent_ex_tax.on_change = self.calc_tax_from_ex
        self.ent_in_tax = ft.TextField(label="税込金額", value="", height=40, text_size=12)
        self.ent_in_tax.on_change = self.calc_tax_from_in
        self.mng_no_entry = ft.TextField(label="管理番号 (予算内)", value="", height=40, text_size=12)
        self.purchase_entry = ft.TextField(label="購入先名", value="", height=40, text_size=12)
        self.pay_date_entry = ft.TextField(label="支払日", value="", height=40, text_size=12)
        self.pay_combo = ft.Dropdown(
            label="支払方法", value="振込",
            options=[ft.dropdown.Option("振込"), ft.dropdown.Option("現金"), ft.dropdown.Option("その他")],
            height=40, text_size=12
        )
        self.model_info_entry = ft.TextField(label="型番・仕様", value="", height=40, text_size=12, expand=True)
        self.delivery_date_entry = ft.TextField(label="希望納期", value="別途打合せ", height=40, text_size=12)
        self.effect_entry = ft.TextField(label="期待効果", value="", height=40, text_size=12)

        # ------------------------------------------
        # FilePicker インスタンス (Flet 0.86: オーバーレイ不要)
        # ------------------------------------------
        self.fp_template = ft.FilePicker()
        self.fp_images = ft.FilePicker()
        self.fp_pdf = ft.FilePicker()
        self.fp_excel_save = ft.FilePicker()
        self.fp_pdf_save = ft.FilePicker()
        self.fp_oneclick_save = ft.FilePicker()

        # ------------------------------------------
        # ヘッダー AppBar
        # ------------------------------------------
        page.appbar = ft.AppBar(
            title=ft.Text("📊 稟議書作成・提出PDF自動結合システム", size=16, weight=ft.FontWeight.BOLD),
            center_title=False
        )

        # ------------------------------------------
        # 1. システム設定カード
        # ------------------------------------------
        setting_card = ft.Container(
            content=ft.Column([
                ft.Text("🔧 1. システム設定 & テンプレート選択", size=14, weight=ft.FontWeight.BOLD),
                ft.Row([
                    self.api_entry,
                    ft.FilledButton("キー保存", on_click=self.save_api_key),
                    ft.VerticalDivider(width=10),
                    self.tpl_combo,
                    ft.IconButton(
                        icon=ft.Icons.FOLDER_OPEN,
                        on_click=self.pick_template_file
                    ),
                    self.use_case_combo,
                ], spacing=8, wrap=True),
            ], spacing=8),
            padding=12,
            border_radius=8,
            bgcolor=ft.Colors.BLUE_900,
        )

        # ------------------------------------------
        # 2. 起案データ入力 ＆ 添付 横並び
        # ------------------------------------------
        left_input = ft.Container(
            content=ft.Column([
                ft.Text("📝 3. 稟議起案データ入力", size=13, weight=ft.FontWeight.BOLD),
                ft.Row([self.dept_entry, self.date_entry], spacing=6),
                ft.Row([self.title_entry, self.author_entry], spacing=6),
                self.subject_entry,
            ], spacing=6),
            padding=12, border_radius=8,
            bgcolor=ft.Colors.GREY_900,
            expand=True
        )

        right_attach = ft.Container(
            content=ft.Column([
                ft.Text("📎 2. 見積書・参考資料の添付 & 自動読込", size=13, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.FilledButton("📥 画像選択", on_click=self.pick_images),
                    ft.FilledButton("📄 PDF選択", on_click=self.pick_pdf),
                ], spacing=6),
                ft.FilledButton("🔍 自動読込実行", on_click=self.analyze_attached_file),
                ft.Row([
                    ft.Icon(ft.Icons.IMAGE, size=16, color=ft.Colors.GREEN_400),
                    ft.Column([self.img_lbl, self.img_page_combo], spacing=2),
                    ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED_400, icon_size=16,
                                  on_click=lambda _: self.clear_attachment("image"))
                ], spacing=6),
                ft.Row([
                    ft.Icon(ft.Icons.PICTURE_AS_PDF, size=16, color=ft.Colors.RED_400),
                    ft.Column([self.pdf_lbl, self.pdf_page_combo], spacing=2),
                    ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED_400, icon_size=16,
                                  on_click=lambda _: self.clear_attachment("pdf"))
                ], spacing=6),
            ], spacing=8),
            padding=12, border_radius=8,
            bgcolor=ft.Colors.GREY_900,
            width=310
        )

        upper_row = ft.Row([left_input, right_attach], spacing=10, vertical_alignment=ft.CrossAxisAlignment.START)

        # ------------------------------------------
        # 3. 文章エリア 左右並び
        # ------------------------------------------
        text_row = ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("📘 4. 【① 起案目的・理由】", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
                        ft.FilledButton("✨ AI再生成", on_click=self.generate_reason),
                        ft.FilledButton("📂 過去稟議コピー", on_click=self.import_past_ringi_text),
                    ], spacing=6, wrap=True),
                    self.reason_preview,
                ], spacing=6),
                padding=12, border_radius=8,
                bgcolor=ft.Colors.BLUE_GREY_900,
                expand=True
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("📙 5. 【② 導入の目的】", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_200),
                    ft.Text("※ Excelの文字枠を綺麗に保つため行数を揃えています", size=10, color=ft.Colors.GREY_500),
                    self.memo_text,
                ], spacing=6),
                padding=12, border_radius=8,
                bgcolor=ft.Colors.BROWN_900,
                expand=True
            ),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.START)

        # ------------------------------------------
        # 4. 詳細グリッド
        # ------------------------------------------
        detail_card = ft.Container(
            content=ft.Column([
                ft.Text("📙 5. 【③ 商品・金額などの詳細】エリア", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_300),
                ft.Row([
                    self.ent_ex_tax, self.ent_in_tax,
                    self.mng_no_entry, self.purchase_entry,
                    self.pay_date_entry, self.pay_combo,
                ], spacing=6, wrap=True),
                ft.Row([
                    self.model_info_entry,
                    self.delivery_date_entry,
                    self.effect_entry,
                ], spacing=6, wrap=True),
            ], spacing=8),
            padding=12, border_radius=8,
            bgcolor=ft.Colors.BROWN_900
        )

        # ------------------------------------------
        # 5. アクションボタン
        # ------------------------------------------
        action_buttons = ft.Row([
            ft.FilledButton("📥 Excel出力", icon=ft.Icons.INSERT_DRIVE_FILE, on_click=self.do_excel_save),
            ft.FilledButton("📄 PDF変換・結合", icon=ft.Icons.PICTURE_AS_PDF, on_click=self.do_pdf_save),
            ft.FilledButton("⚡ Excel→PDF一括実行", icon=ft.Icons.AUTO_MODE, on_click=self.do_oneclick_save),
        ], spacing=12, wrap=True)

        page.add(
            ft.Column([
                setting_card,
                upper_row,
                text_row,
                detail_card,
                ft.Divider(height=10),
                action_buttons,
                ft.Container(height=20)
            ], spacing=12)
        )

        # テンプレートの初期読込
        self.reload_templates()

    # ==========================================
    # ファイル選択 (Flet 0.86: 戻り値直接受け取り)
    # ==========================================
    async def pick_template_file(self, e):
        result = await self.fp_template.pick_files_async(
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["xlsx"]
        )
        if result:
            fpath = result[0].path
            self.template_path = fpath
            new_val = os.path.basename(fpath)
            if new_val not in [opt.key for opt in (self.tpl_combo.options or [])]:
                self.tpl_combo.options.append(ft.dropdown.Option(new_val))
            self.tpl_combo.value = new_val
            self.load_template_to_ui(fpath)
            self.page.update()

    async def pick_images(self, e):
        result = await self.fp_images.pick_files_async(
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["png", "jpg", "jpeg", "gif", "bmp"],
            allow_multiple=True
        )
        if result:
            self.attached_images = [os.path.normpath(os.path.abspath(f.path)) for f in result]
            self.img_lbl.value = f"{len(result)}個の画像を選択中"
            self.img_lbl.color = ft.Colors.GREEN_400
        else:
            self.attached_images = []
            self.img_lbl.value = "選択されていません"
            self.img_lbl.color = ft.Colors.GREY_500
        self.page.update()

    async def pick_pdf(self, e):
        result = await self.fp_pdf.pick_files_async(
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["pdf"]
        )
        if result:
            self.attached_pdf = os.path.normpath(os.path.abspath(result[0].path))
            self.pdf_lbl.value = os.path.basename(self.attached_pdf)
            self.pdf_lbl.color = ft.Colors.GREEN_400
        else:
            self.attached_pdf = ""
            self.pdf_lbl.value = "選択されていません"
            self.pdf_lbl.color = ft.Colors.GREY_500
        self.page.update()

    async def do_excel_save(self, e):
        result = await self.fp_excel_save.save_file_async(
            dialog_title="稟議書Excelの保存先を選択",
            file_name="稟議書.xlsx",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["xlsx"]
        )
        if result:
            self.show_loading_dialog("作成中", "稟議書Excelを作成しています...")
            res = self.write_excel_common(result, is_pdf_mode=False)
            self.close_dialog()
            if res:
                self.last_saved_excel_path = res
                self.show_info_dialog("保存成功", f"稟議書Excelの作成が完了しました！\n出力先:\n{res}")

    async def do_pdf_save(self, e):
        target_excel = self.last_saved_excel_path
        if not target_excel or not os.path.exists(target_excel):
            self.show_error_dialog("エラー", "前回の保存済みExcelが見つかりません。一括実行を最初に行うか、直接Excelを出力してから手直ししてください。")
            return
        result = await self.fp_pdf_save.save_file_async(
            dialog_title="PDF保存先を選択",
            file_name="稟議書.pdf",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["pdf"]
        )
        if result:
            self.show_loading_dialog("変換中", "ExcelをPDFへ変換・結合中...")
            self._run_pdf_save(result, target_excel)

    def _run_pdf_save(self, output_path, target_excel):
        temp_pdf = output_path.replace(".pdf", "_temp_conv.pdf")
        excel_app = None
        try:
            excel_app = win32com.client.DispatchEx("Excel.Application")
            excel_app.Visible = False
            excel_app.DisplayAlerts = False
            wb = excel_app.Workbooks.Open(target_excel)
            wb.ActiveSheet.ExportAsFixedFormat(0, temp_pdf)
            wb.Close(False)
            excel_app.Quit()
            excel_app = None

            merger = PdfMerger()
            merger.append(temp_pdf)
            img_pdf_path = self._make_image_pdf(temp_pdf)
            self._merge_extra_pages(merger, img_pdf_path)
            merger.write(output_path)
            merger.close()
            self._cleanup([temp_pdf, img_pdf_path])
            self.close_dialog()
            self.show_info_dialog("成功", f"PDFの変換・結合が完了しました！\n出力先:\n{output_path}")
        except Exception as ex:
            if excel_app: excel_app.Quit()
            self.close_dialog()
            self.show_error_dialog("変換失敗", f"PDF変換・結合に失敗しました:\n{ex}")

    async def do_oneclick_save(self, e):
        result = await self.fp_oneclick_save.save_file_async(
            dialog_title="PDF保存先を選択 (Excel→PDF一括)",
            file_name="稟議書_完成.pdf",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["pdf"]
        )
        if result:
            self.show_loading_dialog("一括処理中", "Excel作成・PDF結合を処理しています...")
            temp_excel = result.replace(".pdf", "_temp_write.xlsx")
            try:
                main_pdf_path = self.write_excel_common(temp_excel, is_pdf_mode=True)
                if not main_pdf_path:
                    self.close_dialog()
                    return
                merger = PdfMerger()
                merger.append(main_pdf_path)
                img_pdf_path = self._make_image_pdf(temp_excel.replace(".xlsx", "_img.pdf"))
                self._merge_extra_pages(merger, img_pdf_path)
                merger.write(result)
                merger.close()
                self._cleanup([temp_excel, main_pdf_path, img_pdf_path])
                self.close_dialog()
                self.show_info_dialog("大成功", f"一括ドキュメント出力が完了しました！\n出力先:\n{result}")
            except Exception as ex:
                self.close_dialog()
                self.show_error_dialog("処理失敗", f"一括処理に失敗しました:\n{ex}")

    def _make_image_pdf(self, base_path):
        """画像をPDFに変換して返す (添付画像がない場合はNone)"""
        if not self.attached_images or self.img_page_combo.value == "挿入しない":
            return None
        img_pdf_path = base_path if base_path.endswith(".pdf") else base_path + "_img.pdf"
        img_list = []
        for img_p in self.attached_images:
            if os.path.exists(img_p):
                img_list.append(Image.open(img_p).convert("RGB"))
        if img_list:
            img_list[0].save(img_pdf_path, save_all=True, append_images=img_list[1:])
            return img_pdf_path
        return None

    def _merge_extra_pages(self, merger, img_pdf_path):
        """画像PDF・添付PDFを所定のページに結合する"""
        pages = {"2ページ目": [], "3ページ目": [], "4ページ目": []}
        if img_pdf_path and self.img_page_combo.value in pages:
            pages[self.img_page_combo.value].append(img_pdf_path)
        if self.attached_pdf and self.pdf_page_combo.value in pages:
            pages[self.pdf_page_combo.value].append(self.attached_pdf)
        for k in ["2ページ目", "3ページ目", "4ページ目"]:
            for p in pages[k]:
                merger.append(p)

    def _cleanup(self, paths):
        for p in paths:
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

    # ==========================================
    # コールバック & ビジネスロジック
    # ==========================================
    def save_api_key(self, e):
        self.api_key = self.api_entry.value.strip()
        self.save_config()
        self.show_info_dialog("保存完了", "Gemini APIキーを安全に保存しました。")

    def reload_templates(self):
        templates = []
        if os.path.exists(DEFAULT_TEMPLATE_DIR):
            for f in os.listdir(DEFAULT_TEMPLATE_DIR):
                if f.endswith(".xlsx") and not f.startswith("~$") and ("稟議書" in f or "原紙" in f):
                    templates.append(os.path.join(DEFAULT_TEMPLATE_DIR, f))
        if templates:
            opts = [ft.dropdown.Option(os.path.basename(t)) for t in templates]
            self.tpl_combo.options = opts
            self.tpl_combo.value = os.path.basename(templates[0])
            self.template_path = templates[0]
            self.load_template_to_ui(templates[0])
        else:
            self.tpl_combo.options = [ft.dropdown.Option("テンプレートが見つかりません")]
            self.tpl_combo.value = "テンプレートが見つかりません"
        self.page.update()

    def on_template_combo_change(self, e):
        choice = self.tpl_combo.value
        if choice == "テンプレートが見つかりません":
            return
        tpl_path = os.path.join(DEFAULT_TEMPLATE_DIR, choice)
        self.template_path = tpl_path
        self.load_template_to_ui(tpl_path)

    def clear_attachment(self, target):
        if target == "image":
            self.attached_images = []
            self.img_lbl.value = "選択されていません"
            self.img_lbl.color = ft.Colors.GREY_500
        elif target == "pdf":
            self.attached_pdf = ""
            self.pdf_lbl.value = "選択されていません"
            self.pdf_lbl.color = ft.Colors.GREY_500
        self.page.update()

    def calc_tax_from_ex(self, e):
        val = self.ent_ex_tax.value.strip()
        num_str = re.sub(r"[^\d]", "", val)
        if num_str:
            ex_val = int(num_str)
            self.ent_in_tax.value = f"{int(ex_val * 1.1):,}"
            self.page.update()

    def calc_tax_from_in(self, e):
        val = self.ent_in_tax.value.strip()
        num_str = re.sub(r"[^\d]", "", val)
        if num_str:
            in_val = int(num_str)
            self.ent_ex_tax.value = f"{int(in_val / 1.1):,}"
            self.page.update()

    def on_use_case_change(self, e):
        self.apply_use_case_template_replacement()

    def apply_use_case_template_replacement(self):
        choice = self.use_case_combo.value
        if choice == "✨ カスタム (自由に手書き)":
            return
        json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEMPLATES_JSON)
        if not os.path.exists(json_path):
            json_path = TEMPLATES_JSON
        if not os.path.exists(json_path):
            return
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                templates = json.load(f)
        except Exception as ex:
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
        new_model = self.model_info_entry.value.strip() or self.subject_entry.value.strip() or "最新ノートPC"
        new_purchase = self.purchase_entry.value.strip() or "別途選定"
        new_amount_in = self.ent_in_tax.value.strip() or "価格確認中"
        new_amount_ex = self.ent_ex_tax.value.strip() or "価格確認中"
        if json_key == "PC購入・更新":
            reason = reason.replace("フォーレスト専用ノートPC", new_model).replace("HP製端末", new_model)
            purpose = purpose.replace("HP ELITEBOOK 630 G10 CT", new_model).replace("HP EliteBook 630 G10 Notebook PC", new_model)
            reason = reason.replace("エディオン", new_purchase)
            purpose = purpose.replace("株式会社EDIONクロスベンチャーズ", new_purchase).replace("エディオン", new_purchase)
            reason = reason.replace("169,073円", new_amount_ex)
            purpose = purpose.replace("140,000円", new_amount_ex).replace("154,000円", new_amount_in).replace("185,980円", new_amount_in)
        elif json_key == "モニター・ディスプレイ購入":
            reason = reason.replace("高解像度 （2560x1440）のモニター", f"モニター（{new_model}）")
            purpose = purpose.replace("高解像度：2560x1440以上", f"仕様：{new_model}")
        elif json_key == "ソフトウェア・ライセンス":
            reason = reason.replace("AIプレゼンツール【Gamma】", f"【{new_model}】").replace("【Gamma】", f"【{new_model}】")
            purpose = purpose.replace("Gamma", new_model)
        elif json_key == "その他・周辺機器":
            reason = reason.replace("Firepower1010", new_model)
            purpose = purpose.replace("Firepower1010", new_model)
        self.reason_preview.value = reason
        self.memo_text.value = purpose
        if effect:
            self.effect_entry.value = effect
        self.page.update()

    # ==========================================
    # PDF/画像解析 & 自動入力 (Gemini API)
    # ==========================================
    def analyze_attached_file(self, e):
        self.api_key = self.api_entry.value.strip()
        target_file = ""
        is_pdf = False
        if self.attached_pdf and os.path.exists(self.attached_pdf):
            target_file = self.attached_pdf
            is_pdf = True
        elif self.attached_images:
            target_file = self.attached_images[-1]
            is_pdf = False
        if not target_file:
            self.show_error_dialog("エラー", "解析対象のファイル（見積書PDFまたは製品画像）が添付されていません。")
            return
        local_data = {}
        pdf_text = ""
        if is_pdf:
            try:
                reader = PdfReader(target_file)
                for pg in reader.pages:
                    txt = pg.extract_text()
                    if txt:
                        pdf_text += txt + "\n"
                if pdf_text.strip():
                    for pat in [r"(?:請求金額|請求額|御請求額|合計金額|税込合計|お支払額|お支払合計)[^\d\n]*([\d,]+)",
                                r"([\d,]+)\s*(?:円|Yen)?\s*\(税込\)", r"合計[^\d\n]*([\d,]+)"]:
                        m = re.findall(pat, pdf_text, re.IGNORECASE)
                        if m:
                            val = m[0].replace(",", "")
                            if val.isdigit() and int(val) > 100:
                                local_data["amount_in_tax"] = f"{int(val):,}円"
                                break
                    for pat in [r"(?:税抜合計|税別合計|小計|税抜額|税別)[^\d\n]*([\d,]+)",
                                r"([\d,]+)\s*(?:円|Yen)?\s*\(税別\)"]:
                        m = re.findall(pat, pdf_text, re.IGNORECASE)
                        if m:
                            val = m[0].replace(",", "")
                            if val.isdigit() and int(val) > 100:
                                local_data["amount_ex_tax"] = f"{int(val):,}円"
                                break
                    companies = []
                    for cl in pdf_text.split("\n"):
                        cl_clean = cl.strip()
                        if any(w in cl_clean for w in ["フォーレスト", "Forest", "ﾌｫｰﾚｽﾄ", "フォレスト"]):
                            continue
                        co_m = re.search(r"([^\s]*(?:株式会社|有限会社|合同会社)[^\s]*)", cl_clean)
                        if co_m:
                            co_name = co_m.group(1).replace("：", "").replace(":", "").replace("御中", "").replace("様", "").strip()
                            if len(co_name) > 4:
                                companies.append(co_name)
                    if companies:
                        local_data["purchase_from"] = companies[0]
            except Exception as ex:
                print(f"Local PDF parse error: {ex}")

        if local_data.get("amount_in_tax") and local_data.get("purchase_from"):
            self.ent_in_tax.value = local_data["amount_in_tax"].replace("円", "")
            if local_data.get("amount_ex_tax"):
                self.ent_ex_tax.value = local_data["amount_ex_tax"].replace("円", "")
            self.purchase_entry.value = local_data["purchase_from"]
            self.apply_use_case_template_replacement()
            self.page.update()
            self.show_info_dialog("成功", "PDFから金額と取引先データをローカル高速抽出しました！")
            return

        if not self.api_key:
            self.show_error_dialog("エラー", "Gemini APIキーが設定されていません。")
            return

        self.show_loading_dialog("AI解析中", "AIが見積書/画像を読み取っています...")
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            prompt = (
                "あなたは優秀な社内SEです。提供された情報（見積書または製品画像）から、以下のキーを持つJSONオブジェクトのみを出力してください。\n"
                "subject, amount_ex_tax, amount_in_tax, purchase_from, model_info, effect, delivery, reason_area1, purpose_area2\n"
                "```json\n{}\n```"
            )
            if is_pdf:
                if not pdf_text.strip():
                    raise Exception("PDFからテキストを抽出できませんでした。")
                data = {"contents": [{"parts": [{"text": f"{prompt}\n\n【PDFテキスト】\n{pdf_text}"}]}]}
            else:
                with open(target_file, "rb") as f:
                    img_base64 = base64.b64encode(f.read()).decode("utf-8")
                data = {"contents": [{"parts": [{"text": prompt}, {"inlineData": {"mimeType": "image/png", "data": img_base64}}]}]}
            req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                text_out = res_data["candidates"][0]["content"]["parts"][0]["text"]
                json_str = text_out.replace("```json", "").replace("```", "").strip()
                rj = json.loads(json_str)
                if "subject" in rj: self.subject_entry.value = rj["subject"]
                if rj.get("amount_ex_tax"): self.ent_ex_tax.value = rj["amount_ex_tax"].replace("円", "").strip()
                if rj.get("amount_in_tax"): self.ent_in_tax.value = rj["amount_in_tax"].replace("円", "").strip()
                if "purchase_from" in rj: self.purchase_entry.value = rj["purchase_from"]
                if "model_info" in rj: self.model_info_entry.value = rj["model_info"]
                if "effect" in rj: self.effect_entry.value = rj["effect"]
                if "delivery" in rj: self.delivery_date_entry.value = rj["delivery"]
                if rj.get("reason_area1"): self.reason_preview.value = rj["reason_area1"]
                if rj.get("purpose_area2"): self.memo_text.value = rj["purpose_area2"]
                self.apply_use_case_template_replacement()
                self.close_dialog()
                self.page.update()
                self.show_info_dialog("成功", "AIによる自動入力が完了しました！")
        except Exception as ex:
            self.close_dialog()
            self.show_error_dialog("エラー", f"AI解析に失敗しました:\n{ex}")

    def generate_reason(self, e):
        self.api_key = self.api_entry.value.strip()
        if not self.api_key:
            self.show_error_dialog("エラー", "起案理由をAIで生成するにはAPIキーが必要です。")
            return
        subject = self.subject_entry.value.strip()
        if not subject:
            self.show_error_dialog("エラー", "件名を入力した状態で生成してください。")
            return
        self.show_loading_dialog("生成中", "AIが説得力のある稟議文を作成しています...")
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            prompt = (f"件名「{subject}」の稟議書の「起案目的・理由」を200文字程度の自然な日本語で書いてください。文章のみ出力してください。")
            data = {"contents": [{"parts": [{"text": prompt}]}]}
            req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                text_out = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                self.reason_preview.value = text_out
                self.close_dialog()
                self.page.update()
                self.show_info_dialog("生成完了", "AI起案理由文を生成しました！")
        except Exception as ex:
            self.close_dialog()
            self.show_error_dialog("エラー", f"生成に失敗しました:\n{ex}")

    def import_past_ringi_text(self, e):
        self.apply_use_case_template_replacement()
        self.show_info_dialog("コピー完了", "選択中の用途テンプレートの標準文面をロードしました。")

    # ==========================================
    # テンプレートExcelからデータを読み込んでUIに反映
    # ==========================================
    def load_template_to_ui(self, tpl_path):
        if not tpl_path or not os.path.exists(tpl_path):
            return
        self.show_loading_dialog("読込中", "テンプレートから既存データを読込中...")
        excel_app = None
        try:
            excel_app = win32com.client.DispatchEx("Excel.Application")
            excel_app.Visible = False
            excel_app.DisplayAlerts = False
            wb = excel_app.Workbooks.Open(tpl_path, ReadOnly=True)
            ws = wb.ActiveSheet
            dept = str(ws.Range("S2").Value or "").strip()
            date_val = str(ws.Range("AH1").Value or "").strip()
            title = str(ws.Range("AH3").Value or "").strip()
            author = str(ws.Range("AS1").Value or "").strip()
            subject = str(ws.Range("E7").Value or "").strip()
            if dept: self.dept_entry.value = dept
            if date_val: self.date_entry.value = date_val
            if title: self.title_entry.value = title
            if author: self.author_entry.value = author
            if subject: self.subject_entry.value = subject
            e10_val = str(ws.Range("E10").Value or "").strip()
            mng_match = re.search(r"【[^】]*?([A-Za-z0-9\-]+)[^】]*?】", e10_val)
            self.mng_no_entry.value = mng_match.group(1) if mng_match else ""
            amt = str(ws.Range("AT14").Value or "").strip()
            pay_date = str(ws.Range("AT16").Value or "").strip()
            pay_method_raw = str(ws.Range("AT17").Value or "").strip()
            if amt:
                self.ent_in_tax.value = amt.replace("円", "").strip()
                self.ent_ex_tax.value = amt.replace("円", "").strip()
            if pay_date: self.pay_date_entry.value = pay_date
            if pay_method_raw:
                if "■ 現金" in pay_method_raw: self.pay_combo.value = "現金"
                elif "■ 振込" in pay_method_raw: self.pay_combo.value = "振込"
            reason_lines = [str(ws.Range("B" + str(r)).Value or "").strip() for r in range(15, 21)]
            self.reason_preview.value = "\n".join(l for l in reason_lines if l)
            purpose_lines = []
            for r in range(23, 28):
                val = str(ws.Range("B" + str(r)).Value or "").strip() or str(ws.Range("C" + str(r)).Value or "").strip()
                if val and "■目的" not in val and val != "目的":
                    purpose_lines.append(val)
            self.memo_text.value = "\n".join(purpose_lines)
            effect_lines = [str(ws.Range("C" + str(r)).Value or "").strip() for r in range(38, 40)]
            self.effect_entry.value = "\n".join(l for l in effect_lines if l)
            found_model = found_purchase = found_delivery = ""
            details_text = "".join(str(ws.Range("C" + str(r)).Value or "").strip() + "\n" for r in range(29, 37))
            for pat, attr in [(r"・商品　　：([^\n]+)", "model"), (r"  取引先　：([^\n]+)", "purchase"), (r"  希望納期：([^\n]+)", "delivery")]:
                m = re.search(pat, details_text)
                if m:
                    if attr == "model": found_model = m.group(1).strip()
                    elif attr == "purchase": found_purchase = m.group(1).strip()
                    elif attr == "delivery": found_delivery = m.group(1).strip()
            if found_model: self.model_info_entry.value = found_model
            if found_purchase: self.purchase_entry.value = found_purchase
            if found_delivery: self.delivery_date_entry.value = found_delivery
            wb.Close(False)
            excel_app.Quit()
            self.close_dialog()
            self.page.update()
        except Exception as ex:
            if excel_app: excel_app.Quit()
            self.close_dialog()
            self.show_error_dialog("読込エラー", f"テンプレートのロードに失敗しました:\n{ex}")

    # ==========================================
    # Excel書き込み共通処理
    # ==========================================
    def write_excel_common(self, output_excel_path, is_pdf_mode=False):
        tpl_path = self.template_path
        if not tpl_path or not os.path.exists(tpl_path):
            self.show_error_dialog("エラー", "Excelテンプレートファイルが正しく選択されていません。")
            return False
        subject = self.subject_entry.value.strip()
        if not subject:
            self.show_error_dialog("エラー", "件名を入力してください。")
            return False
        reason_text = self.reason_preview.value.strip()
        if not reason_text:
            self.show_error_dialog("エラー", "起案目的・理由が空欄です。")
            return False
        excel_app = None
        try:
            import shutil
            shutil.copy(tpl_path, output_excel_path)
            excel_app = win32com.client.DispatchEx("Excel.Application")
            excel_app.Visible = False
            excel_app.DisplayAlerts = False
            wb = excel_app.Workbooks.Open(output_excel_path)
            ws = wb.ActiveSheet
            for rng in ["B15:B20", "B22:B42", "C23:C27", "B28:AT42", "C28:C42", "F29:F30", "G29:Z30", "Q31:Z31", "Q34:Z34"]:
                ws.Range(rng).Value = ""
            ws.Range("S2").Value = self.dept_entry.value
            ws.Range("AH1").Value = self.date_entry.value
            ws.Range("AH3").Value = self.title_entry.value
            ws.Range("AS1").Value = self.author_entry.value
            ws.Range("E7").Value = subject
            mng_no = self.mng_no_entry.value.strip()
            ws.Range("E10").Value = (
                "■　 予算内　　【　　　　　" + mng_no + " 　　　　　　】　　　　　□　 予算外　　　　　　※経費の支出を伴う場合のみ記載" if mng_no
                else "□　 予算内　　【　管理番号　：　　　　　　　　　　　】　　　　　■　 予算外　　　　　　※経費の支出を伴う場合のみ記載"
            )
            amt_val = self.ent_in_tax.value.strip()
            if amt_val and "円" not in amt_val: amt_val += "円"
            ws.Range("AT14").Value = amt_val
            ws.Range("AT16").Value = self.pay_date_entry.value
            pay_method = self.pay_combo.value
            if pay_method == "現金": ws.Range("AT17").Value = "■ 現金 ・ □ 振込 ・ □ （　       　　）"
            elif pay_method == "振込": ws.Range("AT17").Value = "□ 現金 ・ ■ 振込 ・ □ （　       　　）"
            else: ws.Range("AT17").Value = "□ 現金 ・ □ 振込 ・ ■ （　" + pay_method + "　）"
            ws.Range("AS18").Value = "■見積書" if (self.attached_pdf and self.pdf_page_combo.value != "結合しない") else "□見積書"
            ws.Range("AS19").Value = "■サイト画像" if (self.attached_images and self.img_page_combo.value != "挿入しない") else "□サイト画像"
            ws.Range("AS20").Value = "□その他"
            formatted_lines_1 = split_text_by_chars(reason_text, 40)
            for i in range(min(len(formatted_lines_1), 6)):
                ws.Range("B" + str(15 + i)).Value = formatted_lines_1[i]
            ws.Range("B22").Value = "■目的"
            purpose_lines = split_text_by_chars(self.memo_text.value.strip(), 55)
            for i in range(min(len(purpose_lines), 5)):
                ws.Range("C" + str(23 + i)).Value = purpose_lines[i]
            ws.Range("B28").Value = "■"
            ws.Range("C28").Value = "実施内容"
            ex_val = in_val = 0
            try:
                ex_val = int("".join(c for c in self.ent_ex_tax.value if c.isdigit()))
                in_val = int("".join(c for c in self.ent_in_tax.value if c.isdigit()))
            except: pass
            tax_val = in_val - ex_val
            model = self.model_info_entry.value.strip() or subject
            pur = self.purchase_entry.value.strip() or "別途選定"
            deliv = self.delivery_date_entry.value.strip()
            detail_lines = [
                f"・商品　　：{model}", f"  取引先　：{pur}", f"  購入数　：1台",
                f"  購入金額：{ex_val:,}円 (税込 {in_val:,}円) [内税:{tax_val:,}円]",
                f"  希望納期：{deliv}"
            ]
            current_row = 29
            for d_line in detail_lines:
                for wl in split_text_by_chars(d_line, 55):
                    if current_row <= 36:
                        ws.Cells(current_row, 3).Value = wl
                        current_row += 1
            for r in range(current_row, 37):
                ws.Cells(r, 3).Value = ""
            ws.Range("B37").Value = "■対応の効果について"
            effect_lines = split_text_by_chars(self.effect_entry.value.strip(), 55)
            for i in range(min(len(effect_lines), 2)):
                ws.Range("C" + str(38 + i)).Value = effect_lines[i]
            if self.attached_images and not is_pdf_mode:
                current_cell = ws.Range("BH5")
                current_top = current_cell.Top
                left_pos = current_cell.Left
                for img_path in self.attached_images:
                    if not os.path.exists(img_path): continue
                    with Image.open(img_path) as img:
                        orig_w, orig_h = img.size
                    max_w = 500
                    w = max_w if orig_w > max_w else orig_w
                    h = int(orig_h * (max_w / orig_w)) if orig_w > max_w else orig_h
                    ws.Shapes.AddPicture(img_path, False, True, left_pos, current_top, w, h)
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
        except Exception as ex:
            if excel_app: excel_app.Quit()
            self.show_error_dialog("Excel出力エラー", f"書き込みに失敗しました:\n{ex}")
            return False

    # ==========================================
    # ヘルパーダイアログ (Flet 0.86: show_dialog/pop_dialog)
    # ==========================================
    def show_info_dialog(self, title, msg):
        dlg = ft.AlertDialog(
            title=ft.Text(title, weight=ft.FontWeight.BOLD),
            content=ft.Text(msg),
            actions=[ft.TextButton("閉じる", on_click=lambda _: self.page.pop_dialog())]
        )
        self.page.show_dialog(dlg)

    def show_error_dialog(self, title, msg):
        dlg = ft.AlertDialog(
            title=ft.Text(title, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400),
            content=ft.Text(msg),
            actions=[ft.TextButton("閉じる", on_click=lambda _: self.page.pop_dialog())]
        )
        self.page.show_dialog(dlg)

    def show_loading_dialog(self, title, msg):
        self._loading_dlg = ft.AlertDialog(
            title=ft.Text(title, weight=ft.FontWeight.BOLD),
            content=ft.Row([ft.ProgressRing(width=20, height=20), ft.Text(msg, size=12)], spacing=10),
            modal=True
        )
        self.page.show_dialog(self._loading_dlg)

    def close_dialog(self):
        try:
            self.page.pop_dialog()
        except Exception:
            pass


# ==========================================
# アプリケーション起動
# ==========================================
if __name__ == "__main__":
    app_instance = RingiFletApp()
    ft.run(app_instance.main)
