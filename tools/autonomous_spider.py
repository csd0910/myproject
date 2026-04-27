import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import time
import json
import datetime
from urllib.parse import urlparse, urljoin
import re

def spider_process(cmd_queue, event_queue, config):
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # 外部プロセスとの同化やプロセスの隔離（幽霊化）を防ぐため、独立したChromiumを使用
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()
            
            # --- セーフティ設定: ダイアログ（アラート等）はすべて自動で閉じる ---
            page.on("dialog", lambda dialog: dialog.dismiss())
            
            # about:blankのままユーザーがURLを入力すると、ブラウザが別プロセスに切り替わってしまい
            # Pythonから見えなくなる現象（幽霊化）を防ぐため、ダミーの起点URLを設定しておく
            page.goto("https://www.google.com/")
            
            event_queue.put({"type": "log", "msg": "ブラウザを起動しました。対象サイトにログインし、巡回を始めたいページで「②自走スタート」を押してください。"})
            
            # 手動操作待機ループ
            while True:
                try:
                    cmd = cmd_queue.get_nowait()
                    if cmd["action"] == "START":
                        # STARTされた瞬間の最新設定を取得
                        if "config" in cmd:
                            config.update(cmd["config"])
                            
                        target_url = config.get("target_url", "")
                        if target_url and target_url.startswith("http"):
                            try:
                                page = context.pages[-1]
                                if target_url.rstrip("/") not in page.url.rstrip("/"):
                                    page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
                                event_queue.put({"type": "log", "msg": f"[OK] 対象を捕捉しました: {page.url[:60]}"})
                                break
                            except Exception as e:
                                if "interrupted" in str(e).lower():
                                    event_queue.put({"type": "log", "msg": "[OK] 移動処理を同期しました"})
                                    break
                                event_queue.put({"type": "log", "msg": f"[!] 移動に関する通知: {e}"})
                                break
                                
                        active_page = None
                        for p in reversed(context.pages):
                            if p.url != "about:blank":
                                active_page = p
                                break
                                    
                        if not active_page:
                            active_page = context.pages[-1]
                            
                        page = active_page
                        event_queue.put({"type": "log", "msg": f"✅ 対象をロックしました: {page.url[:60]}..."})
                        break
                    elif cmd["action"] == "STOP":
                        browser.close()
                        return
                except queue.Empty:
                    time.sleep(0.5)

            # --- ここから完全自立巡回（BFS/DFSスパイダー）開始 ---
            event_queue.put({"type": "log", "msg": "自走探索を開始します..."})
            
            visited_urls = set()
            crawled_data = [] 
            
            target_depth = config["max_depth"]
            max_pages = config["max_pages"]
            no_limits = config["disable_limits"]
            
            pages_crawled = 0
            
            def get_all_links():
                all_raw = []
                for frame in page.frames:
                    try:
                        frame_links = frame.evaluate("""
                        () => {
                            let links = [];
                            document.querySelectorAll("a").forEach(a => {
                                let text = a.innerText.trim();
                                let href = a.href; // ブラウザが絶対URLを自動解決する
                                if (href && href.startsWith("http") && !href.includes("javascript:")) {
                                    function getXPath(el) {
                                        let path = "";
                                        for (; el && el.nodeType == 1; el = el.parentNode) {
                                            let index = 1;
                                            for (let sib = el.previousSibling; sib; sib = sib.previousSibling) {
                                                if (sib.nodeType == 1 && sib.tagName == el.tagName) index++;
                                            }
                                            let tagName = el.tagName.toLowerCase();
                                            path = "/" + tagName + "[" + index + "]" + path;
                                        }
                                        return path;
                                    }
                                    links.push({
                                        text: text,
                                        href: href,
                                        xpath: getXPath(a),
                                        outer_html: a.outerHTML
                                    });
                                }
                            });
                            return links;
                        }
                        """)
                        all_raw.extend(frame_links)
                    except Exception:
                        pass
                return all_raw
            
            # 探索キュー (URL, 深さ, 発見元属性)
            start_url = page.url
            start_domain = urlparse(start_url).netloc
            queue_links = [(start_url, 0, "Root")]
            
            while queue_links:
                try:
                    # ブラウザが生きているか確認
                    if not browser.is_connected():
                        event_queue.put({"type": "log", "msg": "[!] ブラウザが閉じられたため、巡回を中断して保存します。"})
                        break
                        
                    current_url, depth, node_type = queue_links.pop(0)
                except IndexError:
                    break

                # 緊急停止フラグ監視
                try:
                    cmd = cmd_queue.get_nowait()
                    if cmd["action"] == "STOP":
                        event_queue.put({"type": "log", "msg": "強制停止されました。"})
                        break
                except queue.Empty:
                    pass
                
                try: # ページ単位の保護try開始
                    # リミッターチェック (常に最新設定を参照可能にする)
                    target_depth = config.get("max_depth", 3)
                    max_pages = config.get("max_pages", 100)
                    no_limits = config.get("disable_limits", False)
                    
                    if not no_limits:
                        if depth > target_depth or pages_crawled >= max_pages:
                            continue
                            
                    if current_url in visited_urls:
                        continue
                        
                    visited_urls.add(current_url)
                    
                    # ページ遷移と動的待機
                    try:
                        if page.url != current_url:
                            page.goto(current_url, timeout=10000)
                            page.wait_for_load_state("networkidle", timeout=5000)
                    except Exception as e:
                        event_queue.put({"type": "log", "msg": f"読み込みスキップ: {current_url}"})
                        continue
                        
                    pages_crawled += 1
                    event_queue.put({"type": "log", "msg": f"[{pages_crawled}P] 探索中 ({node_type}) 深さ{depth}: {current_url[:60]}..."})
                    
                    # データ抽出とログ記録
                    page_title = "Unknown"
                    content_preview = ""
                    page_html = ""
                    try:
                        page.wait_for_load_state("domcontentloaded", timeout=3000)
                        page_title = page.title()
                        content_preview = page.locator("body").inner_text()[:300].replace("\n", " ")
                        
                        # 重要ページ（ルート、フォルダ切り替え、ページ送り）のみHTMLを保存して肥大化を防ぐ
                        if node_type in ["Root", "Category/Folder", "Pager-Next"]:
                            page_html = page.content()
                    except Exception as e:
                        pass
                        
                    # コンテキスト（今どこにいるか）の抽出
                    # サイボウズのタイトルやパンくずリストから「受信箱」などの名前を特定
                    context_label = page_title.split("-")[0].strip()
                    
                    page_info = {
                        "url": current_url,
                        "depth": depth,
                        "node_type": node_type,
                        "context": context_label,
                        "title": page_title,
                        "content_preview": content_preview,
                        "html": page_html,
                        "discovered_links": []
                    }
                    
                    if depth >= target_depth and not no_limits:
                        crawled_data.append(page_info)
                        continue

                    links = get_all_links()
                    
                    # 指定キーワード（ヘルプ、設定など）によるプレフィルタリング
                    exclude_words = config.get("exclude_words", "").split(",")
                    exclude_words = [w.strip().lower() for w in exclude_words if w.strip()]
                    
                    filtered_links = []
                    for l in links:
                        txt = l['text'].lower()
                        # リンクのテキストが1文字もないか、除外ワードが含まれている場合はスキップ
                        if not txt or any(xw in txt for xw in exclude_words):
                            continue
                        filtered_links.append(l)

                    base_xpath_groups = {}
                    for l in filtered_links:
                        bx = re.sub(r'\[\d+\]', '', l['xpath'])
                        if bx not in base_xpath_groups:
                            base_xpath_groups[bx] = []
                        base_xpath_groups[bx].append(l)
                    
                    # ヒューリスティック: 同一構造のリンクが3つ以上並んでいれば「アイテム一覧」とみなす
                    item_groups = {k: v for k, v in base_xpath_groups.items() if len(v) >= 3}
                    
                    # --- 階層掘り下げロジック: 「詳細ページ」の巡回 ---
                    crawl_mode = config.get("crawl_mode", "recon")
                    
                    for k, group in item_groups.items():
                        # 偵察モードなら1件のみ、全件抽出ならリスト全部
                        target_items = group if crawl_mode == "full" else [group[0]]
                        total_in_group = len(group)
                        
                        for idx, sample_leaf in enumerate(target_items):
                            abs_href = sample_leaf['href']
                            if abs_href.startswith("http") and urlparse(abs_href).netloc == start_domain and abs_href not in visited_urls:
                                progress_msg = f"({idx+1}/{total_in_group}件目)" if crawl_mode == "full" else "(サンプル)"
                                event_queue.put({"type": "log", "msg": f"  >> 詳細へ潜入 {progress_msg}: {abs_href[:30]}..."})
                                try:
                                    # 1. 詳細へ移動
                                    page.goto(abs_href, timeout=10000)
                                    page.wait_for_load_state("domcontentloaded", timeout=5000)
                                    visited_urls.add(abs_href)
                                    pages_crawled += 1
                                    
                                    # 2. 詳細データを抽出
                                    leaf_info = {
                                        "url": abs_href,
                                        "depth": depth + 1,
                                        "node_type": "List Item (Inside)",
                                        "context": f"{context_label} > 詳細",
                                        "title": page.title(),
                                        "content_preview": page.locator("body").inner_text()[:300].replace("\n", " "),
                                        "html": "", # 詳細ページのHTMLは基本不要（プレビューで十分）
                                        "parent_xpath": sample_leaf.get('xpath', ''),
                                        "parent_outer_html": sample_leaf.get('outer_html', ''),
                                        "discovered_links": []
                                    }
                                    crawled_data.append(leaf_info)
                                    
                                    # 3. 戻るボタンで元のページ（一覧）へ復帰
                                    page.go_back(wait_until="domcontentloaded")
                                    time.sleep(0.5) 
                                except Exception as e:
                                    event_queue.put({"type": "log", "msg": f"  [!] 潜入失敗: {str(e)[:40]}"})
                                    try: page.goto(current_url) 
                                    except: pass
                    
                    # 次へボタンやジャンル等の単発リンク（これらは後回しでqueueへ）
                    other_links = []
                    for k, group in base_xpath_groups.items():
                        if len(group) < 3: 
                            for l in group:
                                txt = l['text'].lower()
                                abs_href = l['href']
                                
                                if not abs_href.startswith("http") or urlparse(abs_href).netloc != start_domain:
                                    continue
                                    
                                if any(x in txt for x in ['次', 'next', '>', '»', 'ページ']):
                                    other_links.append((abs_href, "Pager-Next"))
                                    page_info["discovered_links"].append({
                                        "type": "Pager", 
                                        "url": abs_href,
                                        "xpath": l.get('xpath'),
                                        "outer_html": l.get('outer_html')
                                    })
                                elif 'category' in abs_href.lower() or 'folder' in abs_href.lower():
                                    other_links.append((abs_href, "Category/Folder"))
                                    page_info["discovered_links"].append({
                                        "type": "Folder", 
                                        "url": abs_href,
                                        "xpath": l.get('xpath'),
                                        "outer_html": l.get('outer_html')
                                    })
                                        
                    crawled_data.append(page_info)
                                        
                    # キューに次の行動を詰める
                    added = 0
                    for url, ntype in other_links:
                        if url not in visited_urls:
                            queue_links.append((url, depth + 1, ntype))
                            added += 1
                        
                except Exception as e:
                    # 巡回中の個別エラー。ログに残して次のURLへ
                    event_queue.put({"type": "log", "msg": f"  [!] ページ巡回エラー ({current_url[:40]}): {str(e)[:100]}"})
                    if "Target closed" in str(e) or "Browser closed" in str(e):
                        break
                    continue
                
            if browser.is_connected():
                browser.close()
                
            event_queue.put({"type": "finish", "data": crawled_data})
            
    except Exception as e:
        import traceback
        event_queue.put({"type": "log", "msg": f"エラー: {traceback.format_exc()}"})

class AutonomousSpiderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("完全自走型スパイダーエンジン (Autonomous Site Mapper)")
        self.root.geometry("600x550")
        
        self.cmd_queue = queue.Queue()
        self.event_queue = queue.Queue()
        
        # --- UI構築 ---
        mode_frm = tk.LabelFrame(root, text="動作モード選択", padx=10, pady=5)
        mode_frm.pack(fill="x", padx=10, pady=5)
        
        self.mode_var = tk.StringVar(value="recon")
        tk.Radiobutton(mode_frm, text="高速偵察（各リストから1通だけ抜いて構造を把握）", variable=self.mode_var, value="recon").pack(side="left", padx=10)
        tk.Radiobutton(mode_frm, text="全件抽出（見つけたリストすべての詳細を抜く）", variable=self.mode_var, value="full", fg="blue").pack(side="left", padx=10)

        frm = tk.LabelFrame(root, text="巡回リミッター設定", padx=10, pady=10)
        frm.pack(fill="x", padx=10, pady=5)
        
        tk.Label(frm, text="階層の深さ (Max Depth):").grid(row=0, column=0, sticky="w")
        self.max_depth_var = tk.IntVar(value=3)
        tk.Entry(frm, textvariable=self.max_depth_var, width=8).grid(row=0, column=1, sticky="w", padx=5)
        
        tk.Label(frm, text="最大探知ページ数 (Max Pages):").grid(row=1, column=0, sticky="w")
        self.max_pages_var = tk.IntVar(value=100)
        tk.Entry(frm, textvariable=self.max_pages_var, width=8).grid(row=1, column=1, sticky="w", padx=5)
        
        self.disable_limit_var = tk.BooleanVar(value=False)
        tk.Checkbutton(frm, text="リミッター（深さ・枚数制限）を全て解除する (※無限ループ注意)", variable=self.disable_limit_var, fg="red").grid(row=2, column=0, columnspan=2, sticky="w", pady=5)
        
        tk.Label(frm, text="除外テキスト (カンマ区切):").grid(row=3, column=0, sticky="w")
        self.exclude_var = tk.StringVar(value="ヘルプ,設定,ログアウト,トップ,検索,オプション,個人,サポート,help,logout,送信,書き込み,削除,編集,作成,send,edit,delete,create")
        tk.Entry(frm, textvariable=self.exclude_var, width=40).grid(row=3, column=1, sticky="w", padx=5)
        
        tk.Label(frm, text="開始URL (直接手入力):").grid(row=4, column=0, sticky="w")
        self.start_url_var = tk.StringVar(value="")
        tk.Entry(frm, textvariable=self.start_url_var, width=40).grid(row=4, column=1, sticky="w", padx=5)
        
        ctrl = tk.Frame(root)
        ctrl.pack(fill="x", padx=10)
        
        self.btn_launch = tk.Button(ctrl, text="① ブラウザ起動", bg="#2196F3", fg="white", font=("Meiryo", 10, "bold"), command=self.launch_browser)
        self.btn_launch.pack(side="left", padx=5)
        
        self.btn_start = tk.Button(ctrl, text="② 自走スタート!", bg="#4CAF50", fg="white", font=("Meiryo", 10, "bold"), state="disabled", command=self.start_crawl)
        self.btn_start.pack(side="left", padx=5)
        
        self.btn_stop = tk.Button(ctrl, text="強制停止", bg="#e53935", fg="white", command=self.stop_crawl)
        self.btn_stop.pack(side="right", padx=5)
        
        self.log_area = tk.Text(root, height=18, bg="#2b2b2b", fg="#a9b7c6", font=("Consolas", 10))
        self.log_area.pack(fill="both", expand=True, padx=10, pady=10)
        
        out_name = f"SpiderMap_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.output_dir = os.path.join(os.path.expanduser("~"), "Desktop", out_name)
        
    def log(self, text):
        self.log_area.insert(tk.END, text + "\n")
        self.log_area.see(tk.END)
        try:
            print(text)
        except UnicodeEncodeError:
            # 絵文字などがWindowsコンソールでエラーになるのを防ぐ
            print(text.encode('cp932', errors='replace').decode('cp932'))
        
    def check_events(self):
        try:
            while True:
                evt = self.event_queue.get_nowait()
                if evt["type"] == "log":
                    self.log(evt["msg"])
                elif evt["type"] == "finish":
                    self.log("\n=== 全自律巡回が完了しました ===")
                    self.save_data(evt["data"])
                    self.btn_launch.config(state="normal")
                    self.btn_start.config(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self.check_events)
        
    def launch_browser(self):
        self.btn_launch.config(state="disabled")
        self.log("Playwright ブラウザを起動しています...")
        
        config = {
            "crawl_mode": self.mode_var.get(),
            "max_depth": self.max_depth_var.get(),
            "max_pages": self.max_pages_var.get(),
            "disable_limits": self.disable_limit_var.get(),
            "exclude_words": self.exclude_var.get(),
            "target_url": self.start_url_var.get().strip()
        }
        
        self.worker_thread = threading.Thread(target=spider_process, args=(self.cmd_queue, self.event_queue, config), daemon=True)
        self.worker_thread.start()
        
        self.btn_start.config(state="normal")
        self.check_events()
        
    def start_crawl(self):
        self.btn_start.config(state="disabled")
        # スタート時の最新設定をコマンドと一緒に送る
        current_config = {
            "crawl_mode": self.mode_var.get(),
            "max_depth": self.max_depth_var.get(),
            "max_pages": self.max_pages_var.get(),
            "disable_limits": self.disable_limit_var.get(),
            "exclude_words": self.exclude_var.get(),
            "target_url": self.start_url_var.get().strip()
        }
        self.cmd_queue.put({"action": "START", "config": current_config})
        
    def stop_crawl(self):
        self.cmd_queue.put({"action": "STOP"})
        self.btn_launch.config(state="normal")
        self.log("ブラウザの完全停止処理を実行しました。")
        
    def save_data(self, data):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        json_path = os.path.join(self.output_dir, "spider_structure_map.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        self.log(f"サイト構造スナップショットを保存しました:\n{json_path}")
        messagebox.showinfo("収集完了", f"自走スパイダーが帰還しました！\n取得データは以下のフォルダに保存されています:\n{self.output_dir}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AutonomousSpiderApp(root)
    root.mainloop()
