import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import re
import time
import threading
import os
import configparser
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw

# ==========================================
# 定数・設定値
# ==========================================
WEB_URL = "https://a832-y.sharestage.com/"  # Bizストレージ本番URL
CONFIG_FILE = "config.ini"
CYBOZU_URL = "https://cybozu.com/" # ユーザーのCybozu環境URL(後で変更可能)

# ==========================================
# Selenium操作補助関数
# ==========================================
def wait_for_element(driver, by, value, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )

def safe_click(driver, by, value, timeout=10):
    elem = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, value))
    )
    elem.click()

def safe_send_keys(driver, by, value, text, timeout=10):
    elem = wait_for_element(driver, by, value, timeout)
    elem.clear()
    elem.send_keys(text)

# ==========================================
# メインアプリケーション
# ==========================================
class CybozuBizAgentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bizストレージ連携エージェント")
        self.root.geometry("450x460")
        self.root.attributes("-topmost", True)  # 常に最前面

        # [×]ボタンを押したときの動作を「終了」から「タスクトレイ格納」へ変更
        self.root.protocol('WM_DELETE_WINDOW', self.hide_window)

        self.driver = None
        self.upload_file_path = ""
        self.biz_id = ""
        self.biz_pass = ""
        self.tray_icon = None

        self.load_or_prompt_config()
        self.setup_gui()

    # --- タスクトレイ常駐機能 ---
    def create_image(self):
        """タスクトレイに表示するダミーのアイコン画像を生成"""
        image = Image.new('RGB', (64, 64), color=(0, 102, 204))
        d = ImageDraw.Draw(image)
        d.text((15, 25), "Biz", fill=(255, 255, 255))
        return image

    def hide_window(self):
        """ウインドウを隠し、タスクトレイにアイコンを表示する"""
        self.root.withdraw() # 画面から非表示
        image = self.create_image()
        menu = (
            item('ウィンドウを表示', self.show_window),
            item('完全に終了する', self.quit_window)
        )
        self.tray_icon = pystray.Icon("BizAgent", image, "Bizストレージ連携エージェント", menu)
        # pystrayのrunはブロックするため別スレッドで実行
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self, icon, item):
        """タスクトレイからウインドウを復帰させる"""
        icon.stop()
        self.root.after(0, self.root.deiconify)

    def quit_window(self, icon, item):
        """アプリを完全に終了する"""
        icon.stop()
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.root.quit()

    def load_or_prompt_config(self):
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE, encoding='utf-8')
            if 'BizStorage' in config:
                self.biz_id = config['BizStorage'].get('LoginID', '')
                self.biz_pass = config['BizStorage'].get('Password', '')

        if not self.biz_id or not self.biz_pass:
            messagebox.showinfo("初期設定", "初回起動（または設定不足）です。\nBizストレージのログイン用IDとパスワードを設定します。\n※次回から自動で入力されます。")
            self.biz_id = simpledialog.askstring("設定", "Bizストレージの【ログインID】を入力してください:") or ""
            self.biz_pass = simpledialog.askstring("設定", "Bizストレージの【パスワード】を入力してください:", show='*') or ""

            config['BizStorage'] = {'LoginID': self.biz_id, 'Password': self.biz_pass}
            with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
                config.write(configfile)

    def setup_gui(self):
        frame = tk.Frame(self.root, padx=15, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # 1. 宛先アドレスリスト
        tk.Label(frame, text="【宛先アドレス】(複数ある場合は改行)", font=("", 10, "bold")).pack(anchor=tk.W)
        self.text_dests = tk.Text(frame, height=3, width=55)
        self.text_dests.pack(pady=(0, 5))

        # 2. 宛先氏名
        tk.Label(frame, text="【宛先氏名】", font=("", 10, "bold")).pack(anchor=tk.W)
        self.entry_dest_name = tk.Entry(frame, width=55)
        self.entry_dest_name.pack(pady=(0, 5))

        # 3. 件名
        tk.Label(frame, text="【件名(標題)】", font=("", 10, "bold")).pack(anchor=tk.W)
        self.entry_subject = tk.Entry(frame, width=55)
        self.entry_subject.pack(pady=(0, 5))

        # 4. パスワード
        tk.Label(frame, text="【抽出パスワード】", font=("", 10, "bold")).pack(anchor=tk.W)
        self.entry_password = tk.Entry(frame, width=55)
        self.entry_password.pack(pady=(0, 5))

        # 5. ファイル選択
        tk.Label(frame, text="【添付ファイル】", font=("", 10, "bold")).pack(anchor=tk.W)
        file_frame = tk.Frame(frame)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        btn_file = tk.Button(file_frame, text="ファイルを選択", command=self.select_file)
        btn_file.pack(side=tk.LEFT)
        self.lbl_file = tk.Label(file_frame, text="未選択", fg="blue", wraplength=280, justify="left")
        self.lbl_file.pack(side=tk.LEFT, padx=10)

        # セパレータ
        tk.Frame(frame, height=2, bd=1, relief=tk.SUNKEN).pack(fill=tk.X, pady=10)

        # 操作ボタン
        btn_frame = tk.Frame(frame)
        btn_frame.pack()

        # 1. 抽出ボタン
        btn_extract = tk.Button(btn_frame, text="1. 開いているブラウザから抽出", command=self.extract_cybozu_worker,
                                bg="#e0f7fa", font=("", 10, "bold"), width=25, height=2)
        btn_extract.grid(row=0, column=0, padx=5)

        # 2. 送信ボタン
        btn_send = tk.Button(btn_frame, text="2. Bizストレージ送信", command=self.execute_bizstorage_worker,
                             bg="#ffe0b2", font=("", 10, "bold"), width=18, height=2)
        btn_send.grid(row=0, column=1, padx=5)

        # ステータスバー
        self.status_var = tk.StringVar()
        self.status_var.set(f"設定済ID: {self.biz_id} │ 待機中...")
        status_label = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def select_file(self):
        path = filedialog.askopenfilename(title="送信するファイルを選択")
        if path:
            self.upload_file_path = path
            self.lbl_file.config(text=path)

    def get_or_create_driver(self):
        # 死んでいるWebDriverセッションを破棄 (invalid session id エラー対策)
        if self.driver:
            try:
                _ = self.driver.current_url
            except Exception:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None

        if self.driver is None:
            options = Options()
            options.add_argument('--disable-gpu')
            self.driver = webdriver.Edge(options=options)
        return self.driver

    # --- 1. 情報取得処理 (UIAスキャン・スレッド実行) ---
    def extract_cybozu_worker(self):
        threading.Thread(target=self._extract_cybozu_logic, daemon=True).start()

    def _extract_cybozu_logic(self):
        self.status_var.set("ステータス: 開いているブラウザをスキャン中(UIA)...")
        try:
            from pywinauto import Desktop
            app_desktop = Desktop(backend="uia")

            # 「メールの送信」か「メール」が含まれる画面を探す
            windows = app_desktop.windows(title_re=".*メール.*")
            if not windows:
                messagebox.showwarning("警告", "Cybozuの「メールの送信」画面が見つかりません。\nご自身のEdge/Chromeでメール作成画面を一番手前に表示してください。")
                self.status_var.set("ステータス: 待機中...")
                return

            target_win = windows[0]
            texts = []

            # ブラウザ内のEdit(テキストボックス)等を強制的に読み取る
            try:
                # 宛先や件名のテキストボックスなどを洗い出し
                for elem in target_win.descendants(control_type="Edit"):
                    val = elem.window_text()
                    if val:
                        texts.append(val)
                # 本文などのドキュメントエリア
                for elem in target_win.descendants(control_type="Document"):
                    val = elem.window_text()
                    if val:
                        texts.append(val)
            except Exception as e:
                pass

            # 念のためクリップボードも混ぜる
            try:
                clip_text = self.root.clipboard_get()
                if clip_text:
                    texts.append(clip_text)
            except:
                pass

            copied_text = "\n".join(texts)

            emails = []
            dest_name = ""
            subject = ""
            password = ""

            # 抽出（パターンマッチ）
            found_emails = re.findall(r'[\w\.-]+@[\w\.-]+', copied_text)
            for em in found_emails:
                if em not in emails:
                    emails.append(em)

            match_name = re.search(r'"?([^"<]+)"?\s*<', copied_text)
            if match_name:
                dest_name = match_name.group(1).strip()
            elif emails:
                dest_name = "お客様"

            match_subj = re.search(r'(?:標題|件名|Subject)\s*[:：]?\s*([^\r\n]+)', copied_text, re.IGNORECASE)
            if match_subj:
                subject = match_subj.group(1).strip()

            match_pass = re.search(r"パスワードは\s*([a-zA-Z0-9!@#$%^&*()_+={}\[\]|\\:;\"'<>,.?/-]+)\s*です", copied_text)
            if match_pass:
                password = match_pass.group(1).strip()

            # GUI更新
            self.root.after(0, self._update_gui_after_extract, emails, dest_name, subject, password)
            self.status_var.set("ステータス: 抽出完了")

            if not emails and not subject and not password:
                messagebox.showwarning("抽出失敗", "情報は取得できましたが、宛先等を抽出できませんでした。\nUIAがブラウザの文字を完全に読めなかった可能性があります。手動でご入力ください。")
            else:
                messagebox.showinfo("抽出完了", "情報を抽出しました。\n内容を確認・修正し、送信へ進んでください。")

        except Exception as e:
            self.status_var.set("ステータス: 抽出エラー")
            messagebox.showerror("エラー", f"情報抽出中にエラーが発生しました:\n{e}")

    def _update_gui_after_extract(self, emails, dest_name, subject, password):
        if emails:
            self.text_dests.delete("1.0", tk.END)
            self.text_dests.insert(tk.END, "\n".join(emails))
        if dest_name:
            self.entry_dest_name.delete(0, tk.END)
            self.entry_dest_name.insert(0, dest_name)
        if subject:
            self.entry_subject.delete(0, tk.END)
            self.entry_subject.insert(0, subject)
        if password:
            self.entry_password.delete(0, tk.END)
            self.entry_password.insert(0, password)

    # --- 2. 送信実行処理 (スレッド実行) ---
    def execute_bizstorage_worker(self):
        dests = self.text_dests.get("1.0", tk.END).strip().split('\n')
        dests = [d.strip() for d in dests if d.strip()]

        if not dests:
            messagebox.showwarning("警告", "宛先が指定されていません。")
            return
        if not self.upload_file_path:
            messagebox.showwarning("警告", "送信するファイルを選択してください。")
            return

        threading.Thread(target=self._execute_bizstorage_logic, args=(dests,), daemon=True).start()

    def _execute_bizstorage_logic(self, dests):
        self.status_var.set("ステータス: Bizストレージ操作中...")
        try:
            dest_name = self.entry_dest_name.get().strip() or "お客様"
            subject = self.entry_subject.get().strip()
            password = self.entry_password.get().strip()

            # 自動操縦ブラウザ(Selenium Edge)を立ち上げ直す (セッション継続)
            driver = self.get_or_create_driver()

            # 1. ログイン & 画面遷移
            self.status_var.set("ステータス: URLアクセス・ログイン中...")
            driver.get(WEB_URL)
            time.sleep(2)

            # ログインフォーム入力
            try:
                safe_send_keys(driver, By.ID, "textfieldLoginId", self.biz_id, timeout=3)
                safe_send_keys(driver, By.XPATH, "/html/body/form[1]/div[1]/div/div[3]/div[1]/table[2]/tbody/tr/td[2]/input", self.biz_pass, timeout=3)
                safe_click(driver, By.XPATH, "/html/body/form[1]/div[1]/div/div[3]/div[2]/span/input", timeout=3)
                time.sleep(3)
            except:
                pass # 既にログイン済みの場合はスキップ

            # メニュー移動: ShareDisk -> ファイル送信
            self.status_var.set("ステータス: 送信画面へ移動中...")
            safe_click(driver, By.XPATH, "/html/body/form/div[1]/div[1]/div[3]/div[3]/div/ul/li[2]/a")
            time.sleep(1)
            safe_click(driver, By.XPATH, "/html/body/form/div[2]/div/div[2]/div[1]/div/div/ul/li[1]/a")
            time.sleep(2)

            # 2. ファイルアップロード操作
            self.status_var.set("ステータス: ファイル選択中...")
            safe_click(driver, By.ID, "uploadFiles")
            time.sleep(3)

            # pywinauto直接操作でファイルダイアログへパス入力
            from pywinauto import Desktop
            app_desktop = Desktop(backend="win32")
            dialog = app_desktop.window(title="開く", class_name="#32770")

            # パスをダブルクォーテーションで囲む
            safe_path = f'"{os.path.abspath(self.upload_file_path)}"'

            # Editへセットしてから、Edit内でEnterを押す
            dialog.Edit.set_focus()
            dialog.Edit.set_edit_text(safe_path)
            time.sleep(2)

            try:
                dialog.Edit.type_keys('{ENTER}')
            except Exception:
                dialog.type_keys('{ENTER}')
            time.sleep(3)

            # 3. 宛先のループ入力 (iframe切り替え)
            self.status_var.set("ステータス: 宛先・情報の入力中...")
            driver.switch_to.frame("SEND_CONTENT")

            for dest in dests:
                safe_send_keys(driver, By.NAME, "USER_MAIL", dest)
                safe_send_keys(driver, By.NAME, "USER_NAME", dest_name)

                # リストへ追加ボタン
                safe_click(driver, By.XPATH, "//input[@name='Submit2' and not(@id='contentComfirm')]")
                time.sleep(1)

            # 4. 件名とパスワード入力
            safe_send_keys(driver, By.NAME, "SD_SUBJECT", subject)

            if password:
                # パスワード入力欄
                try:
                    safe_send_keys(driver, By.NAME, "DL_PASS1", password, timeout=3)
                except:
                    pass

            # 5. 送信実行
            self.status_var.set("ステータス: 最終送信実行中...")
            safe_click(driver, By.ID, "contentComfirm")
            time.sleep(2)

            # 送信確定ボタン
            try:
                safe_click(driver, By.XPATH, "/html/body/form/div/div/div[14]/div[1]/input", timeout=5)
            except:
                safe_click(driver, By.XPATH, "//input[contains(@value, '送信') or contains(@value, '実行')][not(@id='contentComfirm')]")

            self.status_var.set("ステータス: 完了")
            messagebox.showinfo("完了", "Bizストレージの送信操作が完了しました。\nブラウザ上でエラーが出ていないか最終確認をしてください。")

        except Exception as e:
            self.status_var.set("ステータス: エラー停止")
            messagebox.showerror("エラー", f"Bizストレージ操作中にエラーが発生しました:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = CybozuBizAgentApp(root)
    root.mainloop()
