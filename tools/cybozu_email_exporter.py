import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import random
import os
import csv
import re
import traceback
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as EdgeService
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class CybozuEmailExporterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("サイボウズOffice メールエクスポートツール")
        self.root.geometry("600x450")
        
        self.driver = None
        self.is_extracting = False
        
        self.create_widgets()

    def create_widgets(self):
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 1. 保存先選択（上部へ移動）
        ttk.Label(main_frame, text="保存先フォルダ:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.save_dir_var = tk.StringVar()
        self.save_dir_entry = ttk.Entry(main_frame, textvariable=self.save_dir_var, width=50)
        self.save_dir_entry.grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        self.btn_browse = ttk.Button(main_frame, text="参照...", command=self.browse_directory)
        self.btn_browse.grid(row=0, column=3, padx=5, pady=5)

        # 2. URL入力欄（下部へ移動、デフォルト値セット）
        ttk.Label(main_frame, text="サイボウズOffice URL:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.url_var = tk.StringVar(value="https://forestway.cybozu.com/login")
        self.url_entry = ttk.Entry(main_frame, textvariable=self.url_var, width=50)
        self.url_entry.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        # ブラウザ起動ボタン
        self.btn_launch = ttk.Button(main_frame, text="ブラウザ起動", command=self.launch_browser)
        self.btn_launch.grid(row=1, column=3, padx=5, pady=5)
        
        # 区切り線
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(row=3, column=0, columnspan=4, sticky="ew", pady=15)
        
        # 4. ステータスと進行状況
        self.status_var = tk.StringVar(value="ステータス: 待機中 (URLを入力してブラウザを起動してください)")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, font=("Meiryo", 10, "bold"))
        self.status_label.grid(row=4, column=0, columnspan=4, sticky=tk.W, pady=5)
        
        # 5. 抽出開始・停止ボタン配置用フレーム
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=5, column=0, columnspan=4, pady=20)
        
        self.btn_extract = ttk.Button(btn_frame, text="抽出開始", command=self.start_extraction, state=tk.DISABLED)
        self.btn_extract.pack(side=tk.LEFT, padx=10, ipadx=20, ipady=5)

        self.btn_stop = ttk.Button(btn_frame, text="中断・停止", command=self.stop_extraction, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=10, ipadx=20, ipady=5)
        
        # 注意書き（ステップ形式で丁寧に）
        note_text = ("【ご利用手順】\n"
                     "① 保存先のフォルダを任意で作成（変更）してください。\n"
                     "② ログイン時のURLを確認し[ブラウザ起動]を押してください。\n"
                     "③ サイボウズが開いたら自分のアカウントでサインインをしてください。\n"
                     "④ サインインできたら社内メールへ進み、左側の保存したいフォルダを開いてください。\n"
                     "⑤ 当アプリの[抽出開始]をクリックしてお待ちください。")
        ttk.Label(main_frame, text=note_text, foreground="red").grid(row=6, column=0, columnspan=4, sticky=tk.W, pady=5)

    def browse_directory(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.save_dir_var.set(dir_path)

    def launch_browser(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("警告", "サイボウズOfficeのURLを入力してください。")
            return
            
        def _launch():
            try:
                self.status_var.set("ステータス: ブラウザ起動中...")
                self.btn_launch.config(state=tk.DISABLED)
                
                # もし既にエラーで死んだブラウザ等があれば掃除する
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass

                options = Options()
                options.add_experimental_option('excludeSwitches', ['enable-logging'])
                self.driver = webdriver.Edge(options=options)
                self.driver.get(url)
                
                self.status_var.set("ステータス: 手動でログインし、対象フォルダを開いてください。")
                self.root.after(0, lambda: self.btn_extract.config(state=tk.NORMAL))
            except Exception as e:
                self.status_var.set(f"エラー: {str(e)}")
            finally:
                # 起動が成功しても失敗しても、ブラウザ再起動用にボタンは押せる状態に戻す
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
        self.status_var.set("ステータス: 抽出準備中...")
        
        threading.Thread(target=self._extraction_loop, args=(save_dir,), daemon=True).start()

    def stop_extraction(self):
        if self.is_extracting:
            self.is_extracting = False
            self.status_var.set("ステータス: 中段処理中...（現在のメール保存後に停止します）")
            self.btn_stop.config(state=tk.DISABLED)

    def _random_sleep(self):
        # 限界までスピードアップするため0.1秒〜0.3秒へ大幅短縮
        time.sleep(random.uniform(0.1, 0.3))

    def _extraction_loop(self, save_dir):
        try:
            # ページタイトル（フォルダ名）に大量の改行や空白が含まれる場合があるため綺麗にする
            raw_title = self.driver.title
            folder_name = re.sub(r'[\r\n]', '', raw_title)
            folder_name = re.sub(r'[\\/:*?"<>|]', '_', folder_name)
            folder_name = re.sub(r'\s+', ' ', folder_name).strip()
            
            self.status_var.set("ステータス: 抽出を開始しました（月別一覧と個別ファイルに保存します）。")
            
            # --- 差分スキップ用の履歴管理 ---
            history_file = os.path.join(save_dir, f"{folder_name}_抽出済み履歴.txt")
            processed_items = set()
            if os.path.exists(history_file):
                with open(history_file, "r", encoding="utf-8") as f:
                    for line in f:
                        processed_items.add(line.strip())
            
            extracted_count = 0
            skipped_count = 0
            has_next_page = True
            
            # --- 抽出ロジック（XPath適用）---
            mail_link_selector_xpath = "/html/body/div[2]/div[4]/div/table/tbody/tr/td/table/tbody/tr/td[3]/div/div/form/table/tbody/tr/td[3]/a"
            
            while has_next_page and self.is_extracting:
                # ページ遷移後の「現在の一覧画面のURL」を記憶しておく（これで確実に戻れます）
                current_list_url = self.driver.current_url
                
                try:
                    elements = self.driver.find_elements(By.XPATH, mail_link_selector_xpath)
                    mail_urls = []
                    for elm in elements:
                        href = elm.get_attribute("href")
                        if href and ("MailView" in href or "ag.cgi" in href) and "Command" not in href:
                            mail_urls.append(href)
                except Exception as e:
                    self.status_var.set("ステータス: メールリンクの取得に失敗しました。セレクタを確認してください。")
                    break

                for url in mail_urls:
                    if not self.is_extracting:
                        break
                        
                    # ページを開いて日付まで取得しないと更新有無がわからないため、ここではアクセスだけ行う
                    self.driver.get(url)
                    self._random_sleep()
                    
                    try:
                        subject = self.driver.find_element(By.XPATH, "/html/body/div[2]/div[4]/div/table/tbody/tr/td/table/tbody/tr[1]/td/div/div/table/tbody/tr/td[1]/h2").text
                    except Exception:
                        subject = "取得エラー"

                    # 送信者を tr[1]/td[3] から取得
                    try:
                        raw_create_text = self.driver.find_element(By.XPATH, "/html/body/div[2]/div[4]/div/table/tbody/tr/td/table/tbody/tr[1]/td/div/form/table/tbody/tr[1]/td[3]").text
                        # "YYYY/MM/DD"の開始位置より前が確実に差出人名になる
                        match_create = re.search(r'\d{4}/\d{1,2}/\d{1,2}', raw_create_text)
                        if match_create:
                            sender = raw_create_text[:match_create.start()].strip()
                        else:
                            sender = raw_create_text.split(" ")[0].strip()
                    except Exception:
                        sender = "取得エラー"
                        raw_create_text = ""

                    # 日時を tr[2]/td[3]（なければ tr[1]/td[3]）から取得し、宛先などの無関係な文字を除外する
                    try:
                        raw_update_text = self.driver.find_element(By.XPATH, "/html/body/div[2]/div[4]/div/table/tbody/tr/td/table/tbody/tr[1]/td/div/form/table/tbody/tr[2]/td[3]").text
                        # テキスト内に日付表記があるかチェック（宛先リストなどを誤検知しないため）
                        match_update = re.search(r'\d{4}/\d{1,2}/\d{1,2}.*?(?:\d{1,2}:\d{2}|$)', raw_update_text)
                        if match_update:
                            date_str = match_update.group(0).strip()
                        else:
                            raise Exception("日付行ではありません")
                    except Exception:
                        # 最終更新行がない場合は作成日の行から純粋な日付文字列だけを抜く
                        match_create_full = re.search(r'\d{4}/\d{1,2}/\d{1,2}.*?(?:\d{1,2}:\d{2}|$)', raw_create_text)
                        if match_create_full:
                            date_str = match_create_full.group(0).strip()
                        else:
                            date_str = ""

                    # --- 万全の差分スキップ判定（URL ＋ 最終更新日 が完全に同じならスキップ） ---
                    item_key = f"{url}___{date_str}"
                    if item_key in processed_items:
                        skipped_count += 1
                        self.status_var.set(f"ステータス: 抽出中... ({extracted_count}件完了 / {skipped_count}件スキップ)")
                        continue

                    try:
                        # --- コメントが省略されている場合（続きを読むなど）の展開処理 ---
                        while True:
                            try:
                                # "続きを読む" や "すべてのコメントを表示" などのリンクを探す
                                read_more_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), '続きを読む') or contains(text(), 'のコメント') or contains(text(), 'もっと見る') or contains(text(), 'すべて表示')]")
                                # ユーザー提示の指定パスも念のため複合で探す
                                read_more_links += self.driver.find_elements(By.XPATH, "/html/body/div[2]/div[4]/div/table/tbody/tr/td/table/tbody/tr[2]/td/div/div/div[5]/div[2]/ol/li/a")
                                
                                clicked = False
                                for link in read_more_links:
                                    if link.is_displayed():
                                        link.click()
                                        time.sleep(0.2) # 展開を待つ時間も極限まで短縮
                                        clicked = True
                                        break
                                if not clicked:
                                    break # 展開できるリンクがなくなったら本文取得へ
                            except Exception:
                                break

                        # 本文もコメントもすべて含めるため、親のtd要素（tr[2]/td）の中身を丸ごと取得します
                        body_element = self.driver.find_element(By.XPATH, "/html/body/div[2]/div[4]/div/table/tbody/tr/td/table/tbody/tr[2]/td")
                        body = body_element.text
                    except Exception:
                        body = "本文の取得に失敗（要素不一致）"
                    
                    if subject == "取得エラー" and sender == "取得エラー":
                        continue

                    # データの保存（月別CSV ＆ スレッド別TXT）
                    self._save_data(save_dir, folder_name, subject, sender, date_str, body)
                    
                    # 履歴ファイルに記録（再開時の完全スキップ用）
                    processed_items.add(item_key)
                    with open(history_file, "a", encoding="utf-8") as f:
                        f.write(item_key + "\n")
                    
                    extracted_count += 1
                    self.status_var.set(f"ステータス: 抽出中... ({extracted_count}件完了 / {skipped_count}件スキップ)")
                    
                    # 以前はここで毎回「一覧画面に戻る」をしていて通信の無駄があったため削除。
                    # 次のURLへ直接 driver.get することで劇的に高速化させます。

                if not self.is_extracting:
                    break

                # 現在のページ（最大50件）のメールURLをすべて回り終えたら、1度だけ一覧画面へ戻る
                self.status_var.set("ステータス: ページ読み込み・次ページ検索中...")
                self.driver.get(current_list_url)
                time.sleep(0.5)

                # --- ページングの修正 ---
                # メール一覧画面の最後まできたとき、次へボタンを探してクリックします。
                # 絶対パスのXPATHだと2ページ目以降の [a[1]] → [a[2]] の変化で探せなくなるため、
                # 画面内のすべてのaタグから「次の◯件」などを探すロジックに変更しています。
                try:
                    time.sleep(1.0) # 念のためDOMが安定するのを待つ
                    has_next_page = False
                    for a in self.driver.find_elements(By.TAG_NAME, "a"):
                        txt = a.text.strip()
                        href = a.get_attribute("href") or ""
                        
                        # リンクのテキストが「次の」「次へ」を含み、かつ個別のメールリンク(MailView)ではないもの
                        if ("次の" in txt or "次へ" in txt) and "MailView" not in href:
                            print(f"次のページリンクを発見: {txt}") # ログ出力
                            self.status_var.set("ステータス: 次のページを読み込んでいます...")
                            
                            if href and href.startswith("http"):
                                self.driver.get(href)
                            else:
                                a.click()
                                
                            time.sleep(1.5) # ページめくり時にロードが完了するのを確実に待つ
                            has_next_page = True
                            break
                except Exception as e:
                    print("ページング検索中にエラー:", e)
                    has_next_page = False
                    
            if self.is_extracting:
                self.status_var.set(f"完了: 合計 {extracted_count} 件のメールを保存・結合しました。")
                
        except Exception as e:
            err_msg = traceback.format_exc()
            print(err_msg)  # コンソールに詳細エラーを出す
            self.status_var.set(f"エラー終了: {str(e)}")
        finally:
            self.is_extracting = False
            self.root.after(0, lambda: self.btn_extract.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_stop.config(state=tk.DISABLED))

    def _save_data(self, base_save_dir, folder_name, subject, sender, date_str, body):
        # 日時から 年・月 を抽出
        match = re.search(r'(\d{4})/(\d{1,2})/', date_str)
        if match:
            year, month = match.groups()
            month = month.zfill(2)
        else:
            year, month = "0000", "00"

        # 【1】 月別TXTの作成（プレビューではなく全文を出力）
        list_filename = f"{folder_name}_{year}年{month}月.txt"
        list_path = os.path.join(base_save_dir, list_filename)
        
        with open(list_path, "a", encoding="utf-8") as f:
            f.write(f"【最終更新/日時】 {date_str}\n")
            f.write(f"【送信者】 {sender}\n")
            f.write(f"【件名】 {subject}\n")
            f.write("【本文】\n")
            f.write(f"{body}\n")
            f.write("=" * 80 + "\n\n")

        # 【2】 個別詳細TXTの作成（スレッドごと）と同時にMDファイルの生成
        indiv_dir = os.path.join(base_save_dir, f"{folder_name}_個別メール(オリジナル)")
        os.makedirs(indiv_dir, exist_ok=True)
        
        md_dir = os.path.join(base_save_dir, f"{folder_name}_個別メール_MD")
        os.makedirs(md_dir, exist_ok=True)

        # スレッドごとにまとめるため、件名の接頭辞「Re:」「Fw:」を削除する
        # （re.IGNORECASEを指定して大文字小文字を区別せずに削除）
        base_subject = re.sub(r'^(?:re|fw|fwd|返信|転送)\s*[:：]\s*', '', subject.strip(), flags=re.IGNORECASE)
        
        # Windowsのファイル名に使えない文字を全角などに置換し、改行も除去
        safe_subject = re.sub(r'[\r\n]', '', base_subject)
        safe_subject = re.sub(r'[\\/:*?"<>|]', '＿', safe_subject).strip()

        if not safe_subject:
            safe_subject = "件名なし"
            
        # 件名が長すぎるとOSエラー(Errno 22)になるため、ファイル名用に長さを制限（60文字）
        safe_subject_short = safe_subject[:60]

        # 既に同じスレッドが作成されているかファイル名を検索する
        import glob
        indiv_path = None
        # 件名が長い場合でも一致させるため後ろにワイルドカード(*)をつける
        search_pattern = os.path.join(indiv_dir, f"*_{safe_subject_short}*.txt")
        existing_files = glob.glob(search_pattern)
        
        if existing_files:
            # 既存のファイルに追記
            indiv_path = existing_files[0]
            base_filename = os.path.basename(indiv_path)
            md_filename = os.path.splitext(base_filename)[0] + ".md"
            md_path = os.path.join(md_dir, md_filename)
        else:
            # 新規作成時は ファイル名に「日時_送信者_件名」を付与する
            
            # Windowsのファイル名仕様制限（OSエラー）を防ぐための改行削除と文字数制限
            safe_sender = re.sub(r'[\r\n]', '', sender)
            safe_sender = re.sub(r'[\\/:*?"<>|]', '＿', safe_sender)[:20].strip()
            
            # 日付のゼロパディング処理 (例: 2026/4/6(月) 13:58 -> 20260406(月)_1358)
            match_date = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})\s*(\(.*\))?\s*(?:(\d{1,2}):(\d{2}))?', date_str)
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
                safe_date = re.sub(r'[\\/]', '', safe_date)
                safe_date = re.sub(r'[:*?"<>|]', '', safe_date).replace(' ', '_')[:25].strip()
            
            # 件名も長すぎるとパス長制限に引っかかる場合があるため制限
            new_filename = f"{safe_date}_{safe_sender}_{safe_subject_short}.txt"
            indiv_path = os.path.join(indiv_dir, new_filename)
            md_path = os.path.join(md_dir, f"{safe_date}_{safe_sender}_{safe_subject_short}.md")
        
        # 保存する実データ（共通）
        raw_block = (f"【日時】 {date_str}\n"
                     f"【送信者】 {sender}\n"
                     f"【件名】 {subject}\n"
                     f"【本文】\n"
                     f"{body}\n"
                     f"{'=' * 80}\n\n")

        # 追記モード("a")にすることで、同じ件名のメールが過去から未来まで同じファイルに連結されていく
        with open(indiv_path, "a", encoding="utf-8") as f:
            f.write(raw_block)

        # 全く同じ内容をMarkdown形式にリアルタイム整形してMD用フォルダにも追記保存する
        md_content = self._convert_to_md_format(raw_block)
        with open(md_path, "a", encoding="utf-8", newline="") as f:
            f.write(md_content)

    def _convert_to_md_format(self, content):
        # 1. サイボウズ特有のノイズ・不要な文字の除去
        noise_patterns = [
            r"確認しました", r"\d+名", r"返信する", r"宛先をすべて表示する",
            r"宛先から削除されたユーザー（\d+人）", r"詳細を見る", r"ファイルを追加",
            r"詳細\s+\d+\s*[KMG]?B", r"プレビュー"
        ]
        for pattern in noise_patterns:
            content = re.sub(r'[\s]*' + pattern + r'[\s]*', '\n', content)

        # 2. Markdown 見出しの構成
        thick_line = "ー" * 80
        content = re.sub(r"={10,}", thick_line, content)
        content = re.sub(r"【件名】\s*(.+)", r"# \1", content)
        content = re.sub(r"【(?:最終更新/)?日時】\s*", "**日時**: ", content)
        content = re.sub(r"【送信者】\s*", "**送信者**: ", content)
        content = content.replace("【本文】\n", "")
        content = content.replace("【本文】", "")

        # 3. コメント行のサブ見出し化と枠線の追加
        def comment_header(match):
            num = match.group(1)
            name = match.group(2).strip()
            date = match.group(3).strip()
            return f"\n\n{thick_line}\n\n## 💬 コメント {num}： {name} ({date})\n\n"
            
        content = re.sub(r"^(\d+)\s*:\s*\n+([^\n]+)\s*\n+(\d{4}/\d{1,2}/\d{1,2}[^\n]+)\s*\n*", 
                         comment_header, content, flags=re.MULTILINE)

        # 4. URLの自動リンク化
        content = re.sub(r'(?<!\[)(https?://[a-zA-Z0-9_/:%#\$&\?\(\)~\.=\+\-]+)(?!\])', r'[\1](\1)', content)
        
        # 空白行の圧縮
        content = re.sub(r'\n{3,}', '\n\n', content)
        return content

    def on_closing(self):
        self.is_extracting = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CybozuEmailExporterApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
