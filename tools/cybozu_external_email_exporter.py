import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import random
import os
import re
import traceback
import glob
from datetime import datetime

# ※exe化する際にエラーが出ないようseleniumをインポート
try:
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options
    from selenium.webdriver.common.by import By
except ImportError:
    pass

class CybozuExternalEmailExporterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("サイボウズOffice Eメール バックアップツール")
        self.root.geometry("600x450")
        
        self.driver = None
        self.is_extracting = False
        
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 1. 保存先選択
        ttk.Label(main_frame, text="保存先フォルダ:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.save_dir_var = tk.StringVar()
        self.save_dir_entry = ttk.Entry(main_frame, textvariable=self.save_dir_var, width=50)
        self.save_dir_entry.grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        self.btn_browse = ttk.Button(main_frame, text="参照...", command=self.browse_directory)
        self.btn_browse.grid(row=0, column=3, padx=5, pady=5)

        # 2. URL入力欄
        ttk.Label(main_frame, text="サイボウズOffice URL:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.url_var = tk.StringVar(value="https://forestway.cybozu.com/login")
        self.url_entry = ttk.Entry(main_frame, textvariable=self.url_var, width=50)
        self.url_entry.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        self.btn_launch = ttk.Button(main_frame, text="ブラウザ起動", command=self.launch_browser)
        self.btn_launch.grid(row=1, column=3, padx=5, pady=5)
        
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(row=3, column=0, columnspan=4, sticky="ew", pady=15)
        
        self.status_var = tk.StringVar(value="ステータス: 待機中 (ブラウザを起動し、対象のEメールフォルダを開いてください)")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, font=("Meiryo", 10, "bold"), foreground="blue")
        self.status_label.grid(row=4, column=0, columnspan=4, sticky=tk.W, pady=5)
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=5, column=0, columnspan=4, pady=20)
        
        self.btn_extract = ttk.Button(btn_frame, text="Eメール抽出開始", command=self.start_extraction, state=tk.DISABLED)
        self.btn_extract.pack(side=tk.LEFT, padx=10, ipadx=20, ipady=5)

        self.btn_stop = ttk.Button(btn_frame, text="中断・停止", command=self.stop_extraction, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=10, ipadx=20, ipady=5)
        
        note_text = ("【ご利用手順】\n"
                     "① 保存先を指定し、[ブラウザ起動]を押してログイン。\n"
                     "② 左メニューから「Eメール」を選択し、抽出したいフォルダを開く。\n"
                     "③ 画面にメールの一覧が表示された状態で[Eメール抽出開始]をクリックします。\n"
                     "※Eメールは社外通信を含むため、サーバー負荷軽減目的で1件につき約2秒待機します。")
        ttk.Label(main_frame, text=note_text, foreground="red").grid(row=6, column=0, columnspan=4, sticky=tk.W, pady=5)

    def browse_directory(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.save_dir_var.set(dir_path)

    def launch_browser(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("警告", "URLを入力してください。")
            return
            
        def _launch():
            try:
                self.status_var.set("ステータス: ブラウザ起動中...")
                self.btn_launch.config(state=tk.DISABLED)
                if self.driver:
                    try: self.driver.quit()
                    except: pass

                options = Options()
                options.add_experimental_option('excludeSwitches', ['enable-logging'])
                self.driver = webdriver.Edge(options=options)
                self.driver.get(url)
                
                self.status_var.set("ステータス: Eメールの一覧画面を開き、抽出開始を押してください。")
                self.root.after(0, lambda: self.btn_extract.config(state=tk.NORMAL))
            except Exception as e:
                self.status_var.set(f"エラー: {str(e)}")
            finally:
                self.root.after(0, lambda: self.btn_launch.config(state=tk.NORMAL))
                
        threading.Thread(target=_launch, daemon=True).start()

    def start_extraction(self):
        save_dir = self.save_dir_var.get()
        if not save_dir:
            messagebox.showwarning("警告", "保存先フォルダを指定してください。")
            return
        if not self.driver:
            messagebox.showwarning("警告", "ブラウザが起動していません。")
            return

        self.is_extracting = True
        self.btn_extract.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.status_var.set("ステータス: Eメール抽出準備中...")
        
        threading.Thread(target=self._extraction_loop, args=(save_dir,), daemon=True).start()

    def stop_extraction(self):
        if self.is_extracting:
            self.is_extracting = False
            self.status_var.set("ステータス: 中段処理中...（現在のメール保存後に停止します）")
            self.btn_stop.config(state=tk.DISABLED)

    def _random_sleep(self):
        # 前作同様の限界スピード（0.1秒〜0.3秒）へ大幅短縮
        time.sleep(random.uniform(0.1, 0.3))

    def _extraction_loop(self, save_dir):
        try:
            raw_title = self.driver.title
            folder_name = re.sub(r'[\r\n]', '', raw_title)
            folder_name = re.sub(r'[\\/:*?"<>|]', '_', folder_name)
            folder_name = "Eメール_" + re.sub(r'\s+', ' ', folder_name).strip()
            
            history_file = os.path.join(save_dir, f"{folder_name}_抽出済み履歴.txt")
            processed_items = set()
            if os.path.exists(history_file):
                with open(history_file, "r", encoding="utf-8") as f:
                    for line in f:
                        processed_items.add(line.strip())
            
            extracted_count = 0
            skipped_count = 0
            has_next_page = True
            
            while has_next_page and self.is_extracting:
                current_list_url = self.driver.current_url
                
                try:
                    # Eメールのリストから個別メールのリンクを収集する
                    # ユーザーから提供されたXPathの階層（form/table）に従ってリンクを収集する
                    mail_urls = []
                    # form内のtableにあるaタグだけを探せば、一覧以外の無関係なリンクは一切混ざらない
                    a_elements = self.driver.find_elements(By.XPATH, "/html/body/div[2]/div[4]/div/table/tbody/tr/td/table/tbody/tr/td[3]/div/div/form/table//a")
                    for a in a_elements:
                        href = a.get_attribute("href") or ""
                        # ソート用や添付ファイルアイコン等のリンクを除外する
                        if "Command=" not in href and "Delete" not in href and "Order=" not in href and "Sort=" not in href:
                            if "id=" in href.lower() or "snum=" in href.lower() or "did=" in href.lower() or "page=mail" in href.lower():
                                if href not in mail_urls:
                                    mail_urls.append(href)
                except Exception as e:
                    self.status_var.set("ステータス: メール一覧の取得に失敗しました。")
                    break

                # 現在のページのメールを巡回
                for url in mail_urls:
                    if not self.is_extracting:
                        break
                        
                    self.driver.get(url)
                    self._random_sleep()
                    
                    # --- 提供されたXPathに基づく確実なデータ抽出フェーズ ---
                    
                    # 1. 件名
                    try:
                        subject = self.driver.find_element(By.XPATH, "/html/body/div[2]/div[4]/div/table/tbody/tr/td/table/tbody/tr[1]/td/div/div/table/tbody/tr/td[1]/h2").text
                    except Exception:
                        subject = "件名不明"

                    sender = "不明"
                    to_address = ""
                    cc_address = ""
                    date_str = ""
                    
                    # 2. 差出人・宛先・CC・日時
                    # CCなどが存在すると tr[2], tr[3] 等の行がズレる可能性があるため、
                    # tr[1]/td/div/table の内側にあるすべての行(tr)をループして探す安全な仕様にします
                    try:
                        header_table = self.driver.find_element(By.XPATH, "/html/body/div[2]/div[4]/div/table/tbody/tr/td/table/tbody/tr[1]/td/div/table")
                        for row in header_table.find_elements(By.TAG_NAME, "tr"):
                            row_text = row.text.strip()
                            if "差出人" in row_text:
                                sender = row_text.replace("差出人", "").strip(" :\n\t")
                            elif "宛先" in row_text:
                                to_address = row_text.replace("宛先", "").strip(" :\n\t")
                            elif "CC" in row_text or "Cc" in row_text:
                                cc_address = row_text.replace("CC", "").replace("Cc", "").strip(" :\n\t")
                            elif "日時" in row_text:
                                match_date = re.search(r'\d{4}[\-/]\d{1,2}[\-/]\d{1,2}.*?(?:\d{1,2}:\d{2}|$)', row_text)
                                if match_date:
                                    date_str = match_date.group(0).strip()
                    except Exception:
                        pass # 万が一取れなかった場合は後続の処理で空文字として扱う

                    # 3. 本文＆添付ファイル情報
                    # ユーザーから提供された本文領域の「大本（親）」である tr[2]/td の中身を丸ごと取得することで、
                    # メールの文章から添付ファイルの情報まで漏れなくすべて（ここからここまで）を確保できる
                    try:
                        body_element = self.driver.find_element(By.XPATH, "/html/body/div[2]/div[4]/div/table/tbody/tr/td/table/tbody/tr[2]/td")
                        body = body_element.text
                    except Exception:
                        body = "本文領域の取得に失敗"

                    # URLと日時の複合キーで差分スキップ判定
                    item_key = f"{url}___{date_str}"
                    if item_key in processed_items:
                        skipped_count += 1
                        self.status_var.set(f"ステータス: 抽出中... ({extracted_count}件完了 / {skipped_count}件スキップ)")
                        continue

                    if subject == "件名不明" and not date_str:
                        continue # エラー画面などの場合はスキップ

                    # データの保存処理
                    self._save_data(save_dir, folder_name, subject, sender, to_address, cc_address, date_str, body)
                    
                    processed_items.add(item_key)
                    with open(history_file, "a", encoding="utf-8") as f:
                        f.write(item_key + "\n")
                    
                    extracted_count += 1
                    self.status_var.set(f"ステータス: 抽出中... ({extracted_count}件完了 / {skipped_count}件スキップ)")

                if not self.is_extracting:
                    break

                self.driver.get(current_list_url)
                time.sleep(0.5)

                # 「次の◯件」を見つけてページング
                has_next_page = False
                try:
                    # 「前へ」ボタンを誤爆して無限ループループしないよう、必ず「次」という文字を含むリンクだけを探す
                    next_btn = self.driver.find_element(By.XPATH, "//a[contains(text(), '次の') or contains(text(), '次へ')]")
                    next_href = next_btn.get_attribute("href")
                    if next_href and "http" in next_href:
                        self.driver.get(next_href)
                    else:
                        next_btn.click()
                    self._random_sleep()
                    has_next_page = True
                except Exception:
                    # 万が一上のXPathが見つからなかった場合の最後の砦（フォールバック）
                    try:
                        for a in self.driver.find_elements(By.TAG_NAME, "a"):
                            txt = a.text.strip()
                            if "次の" in txt or "次へ" in txt:
                                href = a.get_attribute("href") or ""
                                if "Mail" not in href: # Eメールリンク自体ではないことを確認
                                    if href and href.startswith("http"):
                                        self.driver.get(href)
                                    else:
                                        a.click()
                                    self._random_sleep()
                                    has_next_page = True
                                    break
                    except Exception:
                        has_next_page = False
                    
            if self.is_extracting:
                self.status_var.set(f"完了: 合計 {extracted_count} 件のEメールを展開保存しました。")
                
        except Exception as e:
            err_msg = traceback.format_exc()
            print(err_msg)
            self.status_var.set(f"エラー終了: {str(e)}")
        finally:
            self.is_extracting = False
            self.root.after(0, lambda: self.btn_extract.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_stop.config(state=tk.DISABLED))

    def _save_data(self, base_save_dir, folder_name, subject, sender, to_address, cc_address, date_str, body):
        indiv_dir = os.path.join(base_save_dir, f"{folder_name}_個別(オリジナル)")
        os.makedirs(indiv_dir, exist_ok=True)
        md_dir = os.path.join(base_save_dir, f"{folder_name}_個別_MD")
        os.makedirs(md_dir, exist_ok=True)

        # 案件グループ化を廃止し、件名の「Re:」「Fwd:」などは削らずそのままのサイボウズの件名を使用する
        safe_subject = re.sub(r'[\r\n]', '', subject.strip())
        safe_subject = re.sub(r'[\\/:*?"<>|]', '＿', safe_subject).strip()
        if not safe_subject:
            safe_subject = "件名なし"
        safe_subject_short = safe_subject[:50]

        # 日付の完全ゼロパディング処理 (YYYYMMDD(曜日)_HHMM)
        match_date = re.search(r'(\d{4})[\-/](\d{1,2})[\-/](\d{1,2})\s*(\(.*\))?\s*(?:(\d{1,2}):(\d{2}))?', date_str)
        if match_date:
            y = match_date.group(1)
            m = match_date.group(2).zfill(2)
            d = match_date.group(3).zfill(2)
            weekday = match_date.group(4) or ""
            hh = match_date.group(5).zfill(2) if match_date.group(5) else "00"
            mm = match_date.group(6) if match_date.group(6) else "00"
            safe_date = f"{y}{m}{d}{weekday}_{hh}{mm}"
        else:
            safe_date = re.sub(r'[\r\n]', '', date_str)
            safe_date = re.sub(r'[\\/:*?"<>|]', '', safe_date).replace(' ', '_')[:25].strip()

        # Eメール特有の工夫： 送信者が自分の場合や宛先をファイル名に含めて区別しやすくする
        contact_name = sender
        if "自分" in sender or "自社" in sender: # プロテクト処理（自社ドメインの場合などに宛先を使う）
            contact_name = to_address if to_address else sender
            
        safe_contact = re.sub(r'[\r\n]', '', contact_name.split("<")[0]) # アドレスを除いて名前だけにする
        safe_contact = re.sub(r'[\\/:*?"<>|]', '＿', safe_contact)[:15].strip()
        
        # 1メールごとに固有のファイル名で保存する（同じ分に同じ人が同じ件名を出した場合は追記される安全設計）
        new_filename = f"{safe_date}_{safe_contact}_{safe_subject_short}.txt"
        indiv_path = os.path.join(indiv_dir, new_filename)
        md_path = os.path.join(md_dir, f"{safe_date}_{safe_contact}_{safe_subject_short}.md")
        
        # Eメール向けフォーマットでブロックを生成
        raw_block = (f"【日時】 {date_str}\n"
                     f"【差出人】 {sender}\n"
                     f"【宛先】 {to_address}\n")
        if cc_address:
            raw_block += f"【CC】 {cc_address}\n"
                     
        raw_block += (f"【件名】 {subject}\n"
                      f"【本文】\n"
                      f"{body}\n"
                      f"{'=' * 80}\n\n")

        with open(indiv_path, "a", encoding="utf-8") as f:
            f.write(raw_block)

        # Markdown形式にも同時生成（ノイズは除くが、添付ファイル名は残す方針）
        md_content = self._convert_to_md_format_for_email(raw_block)
        with open(md_path, "a", encoding="utf-8", newline="") as f:
            f.write(md_content)

    def _convert_to_md_format_for_email(self, content):
        # UIノイズ（ボタンなど）を除去。ただし「添付」などのファイル名は残す方針とする。
        noise_patterns = [
            r"確認しました", r"返信する", r"全員に返信", r"転送する", 
            r"詳細を見る", r"削除する", r"迷惑メール", r"ヘッダーを表示",
            r"印刷する"
        ]
        for pattern in noise_patterns:
            content = re.sub(r'[\s]*' + pattern + r'[\s]*', '\n', content)

        thick_line = "ー" * 80
        content = re.sub(r"={10,}", thick_line, content)
        
        # Eメールの項目を見出しや強調に
        content = re.sub(r"【件名】\s*(.+)", r"# \1", content)
        content = re.sub(r"【日時】\s*", "**日時**: ", content)
        content = re.sub(r"【(?:差出人|送信者)】\s*", "**送信者**: ", content)
        content = re.sub(r"【宛先】\s*(.+)", r"**宛先**: \1", content)
        content = re.sub(r"【CC】\s*(.+)", r"**CC**: \1", content)
        content = content.replace("【本文】\n", "")
        content = content.replace("【本文】", "")

        # URLリング化と空行圧縮
        content = re.sub(r'(?<!\[)(https?://[a-zA-Z0-9_/:%#\$&\?\(\)~\.=\+\-]+)(?!\])', r'[\1](\1)', content)
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content

    def on_closing(self):
        self.is_extracting = False
        if self.driver:
            try: self.driver.quit()
            except: pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CybozuExternalEmailExporterApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
