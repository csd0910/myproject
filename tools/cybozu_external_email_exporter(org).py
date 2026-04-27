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
        self.root.title("サイボウズOffice Eメール バックアップツール (手動版)")
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
        
        self.status_var = tk.StringVar(value="ステータス: 待機中 (対象フォルダを開いてから開始してください)")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, font=("Meiryo", 10, "bold"), foreground="blue")
        self.status_label.grid(row=4, column=0, columnspan=4, sticky=tk.W, pady=5)
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=5, column=0, columnspan=4, pady=20)
        
        self.btn_extract = ttk.Button(btn_frame, text="現在のフォルダを抽出", command=self.start_extraction, state=tk.DISABLED)
        self.btn_extract.pack(side=tk.LEFT, padx=10, ipadx=20, ipady=5)

        self.btn_stop = ttk.Button(btn_frame, text="中断・停止", command=self.stop_extraction, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=10, ipadx=20, ipady=5)
        
        note_text = ("【ご利用手順】\n"
                     "① ログイン後、抽出したいフォルダをブラウザで開きます。\n"
                     "② 画面にメール一覧が出ている状態で、[現在のフォルダを抽出]を押します。\n"
                     "※この(org)版は、自動巡回は行いません。")
        ttk.Label(main_frame, text=note_text, foreground="red").grid(row=6, column=0, columnspan=4, sticky=tk.W, pady=5)

    def browse_directory(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.save_dir_var.set(dir_path)

    def launch_browser(self):
        url = self.url_var.get().strip()
        if not url: return
            
        def _launch():
            try:
                self.btn_launch.config(state=tk.DISABLED)
                options = Options()
                options.add_experimental_option('excludeSwitches', ['enable-logging'])
                self.driver = webdriver.Edge(options=options)
                self.driver.get(url)
                self.root.after(0, lambda: self.btn_extract.config(state=tk.NORMAL))
            except: pass
            finally: self.root.after(0, lambda: self.btn_launch.config(state=tk.NORMAL))
                
        threading.Thread(target=_launch, daemon=True).start()

    def start_extraction(self):
        save_dir = self.save_dir_var.get()
        if not save_dir or not self.driver: return

        self.is_extracting = True
        self.btn_extract.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        
        threading.Thread(target=self._extraction_loop, args=(save_dir,), daemon=True).start()

    def stop_extraction(self):
        self.is_extracting = False
        self.btn_stop.config(state=tk.DISABLED)

    def _random_sleep(self):
        time.sleep(random.uniform(0.1, 0.3))

    def _extraction_loop(self, save_dir):
        try:
            raw_title = self.driver.title
            folder_label = re.sub(r'[\\/:*?"<>|]', '_', re.sub(r'[\r\n]', '', raw_title)).strip()
            folder_name = "Eメール_" + folder_label
            
            # 保存先フォルダの作成
            target_path = os.path.join(save_dir, folder_name)
            os.makedirs(target_path, exist_ok=True)
            
            history_file = os.path.join(target_path, "抽出済み履歴.txt")
            processed_items = set()
            if os.path.exists(history_file):
                with open(history_file, "r", encoding="utf-8") as f:
                    for line in f: processed_items.add(line.strip())

            extracted_count = 0
            has_next_page = True
            
            while has_next_page and self.is_extracting:
                current_list_url = self.driver.current_url
                
                # メールURL収集
                mail_urls = []
                try:
                    a_elements = self.driver.find_elements(By.XPATH, "/html/body/div[2]/div[4]/div/table/tbody/tr/td/table/tbody/tr/td[3]/div/div/form/table//a")
                    for a in a_elements:
                        href = a.get_attribute("href") or ""
                        if all(x not in href for x in ["Command=", "Delete", "Order=", "Sort="]):
                            if any(x in href.lower() for x in ["id=", "snum=", "did=", "page=mail"]):
                                if href not in mail_urls: mail_urls.append(href)
                except: break

                for url in mail_urls:
                    if not self.is_extracting: break
                    self.driver.get(url)
                    time.sleep(2.0) # 安定の2秒
                    
                    # データ取得 (簡易版)
                    try:
                        subject = self.driver.find_element(By.XPATH, "/html/body/div[2]/div[4]/div/table/tbody/tr/td/table/tbody/tr[1]/td/div/div/table/tbody/tr/td[1]/h2").text
                        body = self.driver.find_element(By.XPATH, "/html/body/div[2]/div[4]/div/table/tbody/tr/td/table/tbody/tr[2]/td").text
                        
                        header_table = self.driver.find_element(By.XPATH, "/html/body/div[2]/div[4]/div/table/tbody/tr/td/table/tbody/tr[1]/td/div/table")
                        sender, d_str = "不明", ""
                        for row in header_table.find_elements(By.TAG_NAME, "tr"):
                            txt = row.text.strip()
                            if "差出人" in txt: sender = txt.replace("差出人", "").strip(" :\n\t")
                            if "日時" in txt:
                                m = re.search(r'\d{4}[\-/]\d{1,2}[\-/]\d{1,2}.*?(\d{1,2}:\d{2})', txt)
                                if m: d_str = m.group(0).strip()

                        item_key = f"{url}___{d_str}"
                        if item_key not in processed_items:
                            # 保存
                            self._save_data(target_path, subject, sender, d_str, body)
                            processed_items.add(item_key)
                            with open(history_file, "a", encoding="utf-8") as f: f.write(item_key + "\n")
                            extracted_count += 1
                        
                        self.status_var.set(f"抽出中: {folder_label} ({extracted_count}件完了)")
                    except: pass

                if not self.is_extracting: break
                self.driver.get(current_list_url)
                time.sleep(2.0)

                try:
                    next_btn = self.driver.find_element(By.XPATH, "//a[contains(text(), '次の') or contains(text(), '次へ')]")
                    next_btn.click()
                    time.sleep(2.0); has_next_page = True
                except: has_next_page = False

            self.status_var.set(f"完了: {extracted_count}件取得しました。")
        except: traceback.print_exc()
        finally:
            self.is_extracting = False
            self.root.after(0, lambda: self.btn_extract.config(state=tk.NORMAL))

    def _save_data(self, base_path, subject, sender, d_str, body):
        os.makedirs(os.path.join(base_path, "個別(オリジナル)"), exist_ok=True)
        safe_subject = re.sub(r'[\\/:*?"<>|]', '＿', subject[:50])
        filename = f"{d_str.replace('/','').replace(':','').replace(' ','_')}_{safe_subject}.txt"
        with open(os.path.join(base_path, "個別(オリジナル)", filename), "a", encoding="utf-8") as f:
            f.write(f"【日時】{d_str}\n【差出人】{sender}\n【件名】{subject}\n【本文】\n{body}\n")

    def on_closing(self):
        self.is_extracting = False
        if self.driver: self.driver.quit()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CybozuExternalEmailExporterApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
