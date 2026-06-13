import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import os
import re
import traceback
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    pass

class CybozuExternalEmailExporterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cybozu Exporter V6.42 - Infinite Scroll Fix")
        self.root.geometry("750x700")
        self.driver = None
        self.is_extracting = False
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        config_frame = ttk.LabelFrame(main_frame, text="基本設定", padding=5)
        config_frame.pack(fill=tk.X, pady=5)
        ttk.Label(config_frame, text="保存先:").grid(row=0, column=0, sticky=tk.W)
        self.save_dir_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.save_dir_var, width=55).grid(row=0, column=1, padx=5)
        ttk.Button(config_frame, text="参照", command=lambda: self.save_dir_var.set(filedialog.askdirectory())).grid(row=0, column=2)
        ttk.Label(config_frame, text="URL:").grid(row=1, column=0, sticky=tk.W)
        self.url_var = tk.StringVar(value="https://forestway.cybozu.com/login")
        ttk.Entry(config_frame, textvariable=self.url_var, width=55).grid(row=1, column=1, padx=5)
        self.btn_launch = ttk.Button(config_frame, text="ブラウザ起動", command=self.launch_browser)
        self.btn_launch.grid(row=1, column=2)

        speed_frame = ttk.LabelFrame(main_frame, text="速度・ページめくり調整", padding=5)
        speed_frame.pack(fill=tk.X, pady=5)
        ttk.Label(speed_frame, text="フォルダ移動:").grid(row=0, column=0, padx=5)
        self.wait_folder = tk.DoubleVar(value=0.5)
        ttk.Entry(speed_frame, textvariable=self.wait_folder, width=5).grid(row=0, column=1)
        ttk.Label(speed_frame, text=" 次ページ:").grid(row=0, column=2, padx=5)
        self.wait_page = tk.DoubleVar(value=1.5)
        ttk.Entry(speed_frame, textvariable=self.wait_page, width=5).grid(row=0, column=3)
        ttk.Label(speed_frame, text=" 本文取得:").grid(row=0, column=4, padx=5)
        self.wait_harvest = tk.DoubleVar(value=1.1)
        ttk.Entry(speed_frame, textvariable=self.wait_harvest, width=5).grid(row=0, column=5)
        preset_box = ttk.Frame(speed_frame)
        preset_box.grid(row=1, column=0, columnspan=6, pady=5)
        ttk.Button(preset_box, text="標準", command=lambda: self._set_preset(1.0, 2.5, 2.2)).pack(side=tk.LEFT, padx=5)
        ttk.Button(preset_box, text="高速", command=lambda: self._set_preset(0.5, 1.5, 1.1)).pack(side=tk.LEFT, padx=5)
        ttk.Button(preset_box, text="ニトロ", command=lambda: self._set_preset(0.2, 0.9, 0.8)).pack(side=tk.LEFT, padx=5)

        prog_frame = ttk.Frame(main_frame, padding=5)
        prog_frame.pack(fill=tk.X)
        self.global_status_var = tk.StringVar(value="全体状況: 待機中")
        ttk.Label(prog_frame, textvariable=self.global_status_var, font=("Meiryo", 10, "bold"), foreground="#006400").pack(side=tk.TOP, anchor=tk.W)
        self.status_var = tk.StringVar(value="ステータス: 待機中")
        ttk.Label(prog_frame, textvariable=self.status_var, font=("Meiryo", 9), foreground="#0000FF").pack(side=tk.TOP, anchor=tk.W)

        self.log_text = tk.Text(main_frame, height=18, width=90, font=("Consolas", 9), background="#fefefe")
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        btn_box = ttk.Frame(main_frame)
        btn_box.pack(pady=5)
        self.btn_extract = ttk.Button(btn_box, text="全ページ制覇・抽出開始(V6.42)", command=self.start_extraction, state=tk.DISABLED)
        self.btn_extract.pack(side=tk.LEFT, padx=10, ipadx=30)
        self.btn_stop = ttk.Button(btn_box, text="中断", command=self.stop_extraction, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=10)

    def _set_preset(self, f, p, h):
        self.wait_folder.set(f); self.wait_page.set(p); self.wait_harvest.set(h)
        self.log(f"!! 設定更新: フォルダ{f}s / ページ{p}s / 本文{h}s")

    def log(self, msg):
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.log_text.see(tk.END); self.root.update()

    def launch_browser(self):
        url = self.url_var.get().strip()
        def _launch():
            try:
                options = Options(); options.add_experimental_option('excludeSwitches', ['enable-logging'])
                self.driver = webdriver.Edge(options=options); self.driver.get(url)
                self.btn_extract.config(state=tk.NORMAL)
            except Exception as e: self.log(f"!! 起動エラー: {e}")
        threading.Thread(target=_launch, daemon=True).start()

    def _wait_for_list(self, timeout=12):
        try:
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.dataListSummary")))
            return True
        except: return False

    def _get_page_mail_ids(self):
        script = """
            var results = [];
            var trs = document.querySelectorAll('.dataListSummary tbody tr');
            trs.forEach(tr => {
                if(tr.style.display === 'none' || tr.querySelector('th')) return;
                var a = tr.querySelector("a[href*='MailView'], a[href*='MailSent'], a[href*='mailId']");
                if (a) {
                    var h = a.getAttribute('href') || "";
                    var m = h.match(/(?:EID|mEID|id|did|mDID|mailId|snum)=(\\d+)/i);
                    if(m && !h.includes("Command=") && !h.includes("Delete")) {
                        results.push({ eid: m[1], params: h });
                    }
                }
            });
            return results;
        """
        return self.driver.execute_script(script) or []

    def start_extraction(self):
        if not self.save_dir_var.get(): return
        self.is_extracting = True
        self.btn_extract.config(state=tk.DISABLED); self.btn_stop.config(state=tk.NORMAL)
        threading.Thread(target=self._extraction_loop, args=(self.save_dir_var.get(),), daemon=True).start()

    def stop_extraction(self): self.is_extracting = False

    def _extraction_loop(self, save_dir):
        try:
            self.log(">>> [Step 1] 指示プロンプトに基づき全フォルダを解析(V6.42)...")
            get_f_script = "var results = []; var opts = document.querySelectorAll('select option'); opts.forEach(function(opt) { if(opt.value && opt.value !== 'sep') { var txt = opt.textContent; var m = txt.match(/^(\\u00a0| |　)+/); var depth = m ? m[0].length : 0; results.push({ name: txt.trim(), fid: opt.value, d: depth }); } }); return results;"
            raw_folders = self.driver.execute_script(get_f_script) or []
            
            inbox_start = 0
            for i, f in enumerate(raw_folders):
                if '受信箱' in f['name'] or f['fid'] == 'inbox': inbox_start = i; break
            raw_folders = raw_folders[inbox_start:]

            base_url = self.driver.current_url.split('?')[0]
            folders = []
            path_stack = [""]*10; indices = [0]*10; num_stack = [""]*10
            for f in raw_folders:
                d = min(f['d'], 9)
                for i in range(d+1, 10): indices[i]=0; num_stack[i]=""; path_stack[i]=""
                indices[d] += 1
                idx_str = (num_stack[d-1] + "-" + str(indices[d])) if d > 0 else str(indices[d])
                num_stack[d] = idx_str; safe_n = re.sub(r'[\\/:*?"<>|]', '＿', f['name']).strip()
                full_l = f"{idx_str}. {safe_n}"; path_stack[d] = full_l
                folders.append({"fid": f['fid'], "name": f['name'], "label": full_l, "parts": [path_stack[i] for i in range(d+1) if path_stack[i]]})

            self.log(f">>> 指示書通りの「ページめくり」で全フォルダを完遂します。")
            total_global = 0

            for folder in folders:
                if not self.is_extracting: break
                f_path = save_dir
                for p in folder['parts']: f_path = os.path.join(f_path, p)
                dest_dir = os.path.abspath(os.path.join(f_path, "個別(オリジナル)"))
                os.makedirs(dest_dir, exist_ok=True)
                
                self.log(f"--- 巡回中: {folder['label']} ---")
                
                success_nav = False
                for try_p in [f"fid={folder['fid']}", f"FID={folder['fid']}"]:
                    self.driver.get(f"{base_url}?page=MailIndex&{try_p}"); time.sleep(max(0.1, self.wait_folder.get()))
                    if self._wait_for_list(timeout=4):
                        if folder['name'].replace('[','').replace(']','') in self.driver.execute_script("return document.body.innerText"):
                            success_nav = True; break
                
                if not success_nav: continue

                all_items_in_folder = []
                seen_eids = set()
                page_idx = 1
                while self.is_extracting:
                    current_items = self._get_page_mail_ids()
                    if not current_items: break
                    for item in current_items:
                        if item['eid'] not in seen_eids:
                            all_items_in_folder.append(item); seen_eids.add(item['eid'])
                    
                    self.log(f"  -> Page {page_idx}: {len(current_items)}通捕捉 (累計 {len(all_items_in_folder)}通)")
                    
                    # --- 多層パターンの「次へ」判定 (指示プロンプト準拠) ---
                    find_next_script = """
                        function getStartValue(url) { var m = url.match(/start=(\\d+)/); return m ? parseInt(m[1]) : 0; }
                        var currentStart = getStartValue(window.location.href);
                        var links = document.querySelectorAll("a[href*='start=']");
                        
                        // パターンA: テキストベース (次へ, >>)
                        for(var a of links) {
                            var t = a.innerText;
                            if(t.includes('次') || t.includes('>>')) return a;
                        }
                        
                        // パターンB: ページ番号ベース (現在の次の数字)
                        var pageLinks = Array.from(document.querySelectorAll("a")).filter(a => /^[0-9]+$/.test(a.innerText.trim()));
                        for(var a of pageLinks) {
                             if(parseInt(a.innerText.trim()) === arguments[0] + 1) return a;
                        }
                        
                        // パターンC: start値ベース (今の値より大きい最小のstartを探す)
                        var nextBetter = null; var minDiff = 999999;
                        for(var a of links) {
                            var s = getStartValue(a.href);
                            if(s > currentStart && (s - currentStart) < minDiff) {
                                minDiff = s - currentStart; nextBetter = a;
                            }
                        }
                        return nextBetter;
                    """
                    next_link = self.driver.execute_script(find_next_script, page_idx)
                    if next_link:
                        old_url = self.driver.current_url
                        old_first_id = current_items[0]['eid']
                        self.driver.execute_script("arguments[0].click();", next_link)
                        
                        # 遷移確認 (URLまたは1件目のIDが変わるまで待機)
                        wait_start = time.time()
                        while time.time() - wait_start < 6:
                            time.sleep(max(0.1, self.wait_page.get()))
                            if self.driver.current_url != old_url: break
                            try:
                                new_ids = self._get_page_mail_ids()
                                if new_ids and new_ids[0]['eid'] != old_first_id: break
                            except: pass
                        
                        page_idx += 1
                    else: break

                total_in_f = len(all_items_in_folder)
                self.log(f"  -> 全 {total_in_f}通をクリーン抽出します。")

                existing_eids = set()
                try:
                    for n in os.listdir(dest_dir):
                        res = re.search(r'_(\d+)_', n)
                        if res: existing_eids.add(res.group(1))
                except: pass

                folder_done = sum(1 for it in all_items_in_folder if it['eid'] in existing_eids)

                for item in all_items_in_folder:
                    if not self.is_extracting: break
                    if item['eid'] in existing_eids: continue

                    target_url = item['params'] if item['params'].startswith('http') else f"{base_url.rsplit('/', 1)[0]}/{item['params']}"
                    self.driver.get(target_url); time.sleep(max(0.1, self.wait_harvest.get()))
                    
                    try:
                        res = self.driver.execute_script("""
                            var txt = document.body.innerText;
                            var getM = (re) => { var m = txt.match(re); return m ? m[1].trim() : "不明"; };
                            var body = txt.includes("本文") ? txt.split("本文")[1].trim() : txt;
                            if(body.includes("先頭へ |")) body = body.split("先頭へ |")[0].trim();
                            return { date: getM(/日時\\s*[:：]\\s*(.+)/), from: getM(/差出人\\s*[:：]\\s*(.+)/), to: getM(/宛先\\s*[:：]\\s*(.+)/), subject: (document.querySelector('h2, div.Subject')||{innerText:'no title'}).innerText.trim(), body: body };
                        """)
                        safe_subj = re.sub(r'[\\/:*?"<>|\\r\\n]', '_', res['subject'])[:40]
                        fname = f"_{item['eid']}_{safe_subj}.txt"
                        with open(os.path.join(dest_dir, fname), "w", encoding="utf-8", errors="replace") as sf:
                            sf.write(f"Date: {res['date']}\nFrom: {res['from']}\nTo: {res['to']}\nSubject: {res['subject']}\n\n{res['body']}\n")
                        total_global += 1
                        self.status_var.set(f"フォルダ進捗: {len(seen_eids)}通中 {total_global}通")
                    except Exception as e: pass
                
                self.log(f"  [完了] {folder['name']}")

            self.log(">>> [全工程終了] 全ページ巡回抽出が完了しました。")
        except Exception as e: self.log(f"!! 停止: {e}"); traceback.print_exc()
        finally: self.is_extracting = False; self.btn_extract.config(state=tk.NORMAL)

    def on_closing(self): self.is_extracting = False; (self.driver.quit() if self.driver else None); self.root.destroy()

if __name__ == "__main__": root = tk.Tk(); app = CybozuExternalEmailExporterApp(root); root.protocol("WM_DELETE_WINDOW", app.on_closing); root.mainloop()
