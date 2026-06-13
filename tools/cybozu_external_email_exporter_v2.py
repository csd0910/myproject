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

# ============================================================
# V7.0 改修ポイント（DOM調査結果に基づく）
# 1. 「次へ」リンクはhref=''（空）のAJAXリンク → テキストで検索
# 2. ページ遷移検知はURL変化ではなく「1件目のIDが変わったか」で判定
# 3. 各フォルダで「サイボウズ上の件数」vs「取得件数」を照合してログ出力
# 4. spinner.gif非表示行のスキップは現行通り正しい
# 5. スター/フラグによる誤スキップを削除済み
# ============================================================

class CybozuExternalEmailExporterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cybozu External Exporter V7.0 - DOM Verified")
        self.root.geometry("780x720")
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
        ttk.Label(prog_frame, textvariable=self.global_status_var,
                  font=("Meiryo", 10, "bold"), foreground="#006400").pack(side=tk.TOP, anchor=tk.W)
        self.status_var = tk.StringVar(value="ステータス: 待機中")
        ttk.Label(prog_frame, textvariable=self.status_var,
                  font=("Meiryo", 9), foreground="#0000FF").pack(side=tk.TOP, anchor=tk.W)

        self.log_text = tk.Text(main_frame, height=20, width=92, font=("Consolas", 9), background="#fefefe")
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)

        btn_box = ttk.Frame(main_frame)
        btn_box.pack(pady=5)
        self.btn_extract = ttk.Button(btn_box, text="全ページ制覇・抽出開始(V7.0)",
                                       command=self.start_extraction, state=tk.DISABLED)
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
                options = Options()
                options.add_experimental_option('excludeSwitches', ['enable-logging'])
                self.driver = webdriver.Edge(options=options)
                self.driver.get(url)
                self.btn_extract.config(state=tk.NORMAL)
            except Exception as e:
                self.log(f"!! 起動エラー: {e}")
        threading.Thread(target=_launch, daemon=True).start()

    def _wait_for_list(self, timeout=12):
        """メール一覧テーブルの出現を待つ"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.dataListSummary"))
            )
            return True
        except:
            return False

    def _get_page_mail_ids(self):
        """
        現在ページのメールID一覧を取得。
        DOM調査結果:
          - テーブルクラス: dataList dataListSummary
          - メール行とspinner行(hidden)が交互に並ぶ
          - spinner行は tr.style.display === 'none' で正しくスキップ可能
          - スター/フラグによるスキップは削除（取りこぼし原因だったため）
        """
        script = """
            var results = [];
            var trs = document.querySelectorAll('.dataListSummary tbody tr');
            trs.forEach(tr => {
                // 非表示行(spinner.gif行)とヘッダ行をスキップ
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

    def _get_folder_total_count(self):
        """
        ページ上のページャーから「全XX件」の総件数を取得。
        ドロップダウンの「過去1000件(未読)」等の文字列は除外する。
        """
        try:
            result = self.driver.execute_script("""
                // ページャー専用の要素を探す（ドロップダウンを除く）
                // サイボウズのページャーは通常 .pager や td内に「全X件」形式で表示される
                var pagerEls = document.querySelectorAll(
                    '.pager, [class*="pager"], td.count, span.count, .mailCount'
                );
                for(var el of pagerEls) {
                    var m = el.innerText.match(/全\\s*(\\d+)\\s*件/);
                    if(m) return parseInt(m[1]);
                }
                // フォールバック: select/option を除いたテキストで探す
                // select要素を一時的に非表示にして body テキストを取得
                var selects = document.querySelectorAll('select');
                var origDisplay = [];
                selects.forEach(function(s, i) { origDisplay[i] = s.style.display; s.style.display = 'none'; });
                var bodyText = document.body.innerText;
                selects.forEach(function(s, i) { s.style.display = origDisplay[i]; });
                
                var m = bodyText.match(/全\\s*(\\d+)\\s*件/);
                if(m) return parseInt(m[1]);
                m = bodyText.match(/(\\d+)\\s*件中/);
                if(m) return parseInt(m[1]);
                return -1;
            """)
            return int(result) if result and result > 0 else -1
        except:
            return -1


    def _find_next_page_link(self):
        """
        「次へ」リンクを取得する。
        【重要・DOM調査結果】
        - 「次へ」リンクは href='' （空）のAJAXリンク
        - hrefで絞ると見つからないため、テキストで検索する
        """
        return self.driver.execute_script("""
            // パターン1: テキストが「次へ」「次」「>>」の a要素（href問わず）
            var allLinks = Array.from(document.querySelectorAll('a'));
            for(var a of allLinks) {
                var t = (a.innerText || a.textContent || '').trim();
                if(t === '次へ' || t === '次' || t === '>>' || t === 'Next') {
                    return a;
                }
            }
            // パターン2（フォールバック）: start= を含むhrefで現在より大きいもの
            function getStart(url) { var m = (url||'').match(/start=(\\d+)/); return m ? parseInt(m[1]) : -1; }
            var currentStart = getStart(window.location.href);
            var best = null; var minDiff = 999999;
            document.querySelectorAll('a[href*="start="]').forEach(function(a){
                var s = getStart(a.getAttribute('href'));
                if(s > currentStart && (s - currentStart) < minDiff) {
                    minDiff = s - currentStart; best = a;
                }
            });
            return best;
        """)

    def _click_next_and_wait(self, current_first_id):
        """
        「次へ」をクリックし、ページが切り替わるまで待機する。
        【重要】href=''のAJAXリンクのためURL変化では検知できない。
        → 1件目のメールIDが変わったことで遷移完了を判定する。
        """
        next_link = self._find_next_page_link()
        if not next_link:
            return False  # 「次へ」がない = 最終ページ

        self.driver.execute_script("arguments[0].click();", next_link)

        # ページ切り替わりを「1件目のIDが変わる」で検知（最大10秒）
        deadline = time.time() + 10
        while time.time() < deadline:
            time.sleep(max(0.2, self.wait_page.get()))
            try:
                new_ids = self._get_page_mail_ids()
                if new_ids and new_ids[0]['eid'] != current_first_id:
                    return True  # ページが変わった
            except:
                pass

        # タイムアウトしても次リンクが消えていれば最終ページとみなす
        if not self._find_next_page_link():
            return False
        return True  # 一応Trueで続行（内容は変わっていないかもしれないが）

    def start_extraction(self):
        if not self.save_dir_var.get():
            messagebox.showwarning("設定不足", "保存先フォルダを選択してください。")
            return
        self.is_extracting = True
        self.btn_extract.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        threading.Thread(target=self._extraction_loop,
                         args=(self.save_dir_var.get(),), daemon=True).start()

    def stop_extraction(self):
        self.is_extracting = False
        self.log("!! 中断リクエストを受け付けました。現在の処理が終わり次第停止します。")

    def _extraction_loop(self, save_dir):
        try:
            self.log(">>> [V7.0] フォルダ構造を解析中...")

            # フォルダ一覧を取得（セレクトボックスから）
            get_f_script = """
                var results = [];
                var opts = document.querySelectorAll('select option');
                opts.forEach(function(opt) {
                    if(opt.value && opt.value !== 'sep') {
                        var txt = opt.textContent;
                        var m = txt.match(/^(\\u00a0| |　)+/);
                        var depth = m ? m[0].length : 0;
                        results.push({ name: txt.trim(), fid: opt.value, d: depth });
                    }
                });
                return results;
            """
            raw_folders = self.driver.execute_script(get_f_script) or []

            # 受信箱から開始（それ以前の特殊フォルダ「全件(未読)」等はスキップ）
            inbox_start = 0
            for i, f in enumerate(raw_folders):
                if '受信' in f['name'] or f['fid'] in ('inbox', '1'):
                    inbox_start = i; break
            raw_folders = raw_folders[inbox_start:]

            self.log(f">>> 対象フォルダ数: {len(raw_folders)}")
            base_url = self.driver.current_url.split('?')[0]

            # フォルダごとにパス・ラベルを生成
            folders = []
            path_stack = [""] * 10; indices = [0] * 10; num_stack = [""] * 10
            for f in raw_folders:
                d = min(f['d'], 9)
                for i in range(d + 1, 10):
                    indices[i] = 0; num_stack[i] = ""; path_stack[i] = ""
                indices[d] += 1
                idx_str = (num_stack[d-1] + "-" + str(indices[d])) if d > 0 else str(indices[d])
                num_stack[d] = idx_str
                safe_n = re.sub(r'[\\/:*?"<>|]', '＿', f['name']).strip()
                full_l = f"{idx_str}. {safe_n}"
                path_stack[d] = full_l
                folders.append({
                    "fid": f['fid'], "name": f['name'], "label": full_l,
                    "parts": [path_stack[i] for i in range(d + 1) if path_stack[i]]
                })

            total_global = 0
            folder_summary = []  # 各フォルダの件数チェック結果

            for fi, folder in enumerate(folders):
                if not self.is_extracting: break

                # 保存先ディレクトリを構築
                f_path = save_dir
                for p in folder['parts']:
                    f_path = os.path.join(f_path, p)
                dest_dir = os.path.abspath(os.path.join(f_path, "個別(オリジナル)"))
                os.makedirs(dest_dir, exist_ok=True)

                self.global_status_var.set(
                    f"全体: {fi+1}/{len(folders)} フォルダ処理中 | 累計 {total_global} 件")
                self.log(f"--- [{fi+1}/{len(folders)}] 巡回中: {folder['label']} ---")

                # フォルダへ遷移
                success_nav = False
                for try_p in [f"fid={folder['fid']}", f"FID={folder['fid']}"]:
                    self.driver.get(f"{base_url}?page=MailIndex&{try_p}")
                    time.sleep(max(0.3, self.wait_folder.get()))
                    if self._wait_for_list(timeout=6):
                        # フォルダ名がページに表示されているか確認
                        page_text = self.driver.execute_script("return document.body.innerText")
                        check_name = folder['name'].replace('[', '').replace(']', '')
                        if check_name in page_text:
                            success_nav = True; break

                if not success_nav:
                    self.log(f"  !! ナビゲーション失敗（スキップ）: {folder['name']}")
                    continue

                # === フェーズ1: 全ページをめくりながらメールIDを収集 ===
                # 【V7.2改修】DOM徹底調査の結果、サイボウズのページめくりはAJAXではなく
                # 「次の 50 件へ >>」といったテキストのリンクに本物のURL（PC=2等）が
                # 埋め込まれていることが判明。このhrefを直接取得して遷移する。
                all_items = []
                seen_eids = set()
                cybozu_total = -1
                page_idx = 1

                while self.is_extracting:
                    current_items = self._get_page_mail_ids()

                    if not current_items:
                        self.log(f"  -> Page {page_idx}: メールなし（フォルダ終了）")
                        break

                    # 総件数は最初のページのみ取得
                    if page_idx == 1:
                        cybozu_total = self._get_folder_total_count()

                    new_count = 0
                    for item in current_items:
                        if item['eid'] not in seen_eids:
                            all_items.append(item)
                            seen_eids.add(item['eid'])
                            new_count += 1

                    self.log(f"  -> Page {page_idx}: "
                             f"{len(current_items)}件取得 / 新規{new_count}件 / "
                             f"累計 {len(all_items)}件"
                             + (f" / サイボウズ合計: {cybozu_total}件" if cybozu_total > 0 else ""))

                    # 「次の 〇〇 件へ >>」リンクを探す
                    next_href = self.driver.execute_script("""
                        var links = document.querySelectorAll('a');
                        for(var i=0; i<links.length; i++) {
                            var t = (links[i].innerText || '').trim();
                            if(t.includes('次の') && t.includes('件へ')) {
                                return links[i].getAttribute('href');
                            }
                        }
                        return null;
                    """)

                    if next_href:
                        # hrefが取得できたらそのURLへ直接ジャンプ
                        target_url = next_href if next_href.startswith('http') else f"{base_url.rsplit('/', 1)[0]}/{next_href.lstrip('/')}"
                        self.driver.get(target_url)
                        time.sleep(max(0.3, self.wait_page.get()))
                        self._wait_for_list(timeout=6)
                        page_idx += 1
                    else:
                        self.log(f"  -> Page {page_idx}: 「次へ」リンクなし → 最終ページ")
                        break

                # === 件数チェック ===
                collected = len(all_items)
                if cybozu_total > 0 and collected != cybozu_total:
                    warn = f"  ⚠️ 件数不一致！ サイボウズ:{cybozu_total}件 / 取得:{collected}件 (差:{cybozu_total - collected}件)"
                    self.log(warn)
                    folder_summary.append((folder['label'], cybozu_total, collected, "⚠️ 不一致"))
                else:
                    match_str = f"一致({collected}件)" if cybozu_total > 0 else f"取得:{collected}件(サイボウズ件数不明)"
                    folder_summary.append((folder['label'], cybozu_total, collected, "✅ OK"))
                    self.log(f"  -> 件数チェック: {match_str}")

                # === フェーズ2: 未保存のメールだけ本文を取得して保存 ===
                existing_eids = set()
                try:
                    for n in os.listdir(dest_dir):
                        res = re.search(r'_(\d+)_', n)
                        if res: existing_eids.add(res.group(1))
                except:
                    pass

                skip_count = sum(1 for it in all_items if it['eid'] in existing_eids)
                new_items = [it for it in all_items if it['eid'] not in existing_eids]
                self.log(f"  -> 保存済み: {skip_count}件スキップ / 新規保存: {len(new_items)}件")

                for idx, item in enumerate(new_items):
                    if not self.is_extracting: break

                    target_url = (item['params'] if item['params'].startswith('http')
                                  else f"{base_url.rsplit('/', 1)[0]}/{item['params'].lstrip('/')}")
                    self.driver.get(target_url)
                    time.sleep(max(0.1, self.wait_harvest.get()))

                    try:
                        res = self.driver.execute_script("""
                            var txt = document.body.innerText;
                            var getM = (re) => { var m = txt.match(re); return m ? m[1].trim() : '不明'; };
                            var body = txt.includes('本文') ? txt.split('本文')[1].trim() : txt;
                            if(body.includes('先頭へ |')) body = body.split('先頭へ |')[0].trim();
                            return {
                                date: getM(/日時\\s*[:：]\\s*(.+)/),
                                from: getM(/差出人\\s*[:：]\\s*(.+)/),
                                to: getM(/宛先\\s*[:：]\\s*(.+)/),
                                subject: (document.querySelector('h2, div.Subject')||{innerText:'no title'}).innerText.trim(),
                                body: body
                            };
                        """)
                        safe_subj = re.sub(r'[\\/:*?"<>|\r\n]', '_', res['subject'])[:40]
                        fname = f"_{item['eid']}_{safe_subj}.txt"
                        with open(os.path.join(dest_dir, fname), "w",
                                  encoding="utf-8", errors="replace") as sf:
                            sf.write(
                                f"Date: {res['date']}\nFrom: {res['from']}\n"
                                f"To: {res['to']}\nSubject: {res['subject']}\n\n{res['body']}\n"
                            )
                        total_global += 1
                        self.status_var.set(
                            f"{folder['label']}: {idx+1}/{len(new_items)}件保存中 | 累計 {total_global}件")
                    except Exception as e:
                        self.log(f"  !! 本文取得失敗 EID={item['eid']}: {e}")

                self.log(f"  [完了] {folder['name']} "
                         f"(保存:{len(new_items)}件 / スキップ:{skip_count}件)")

            # === 全フォルダ処理後のサマリーを出力 ===
            self.log("\n" + "="*60)
            self.log(">>> [完了サマリー] 全フォルダの件数チェック結果")
            self.log("="*60)
            warning_count = 0
            for label, expected, got, status in folder_summary:
                if expected > 0:
                    self.log(f"  {status} {label}: 期待{expected}件 / 取得{got}件")
                else:
                    self.log(f"  {status} {label}: 取得{got}件（サイボウズ件数取得不可）")
                if "不一致" in status:
                    warning_count += 1

            self.log("="*60)
            self.log(f">>> 累計保存件数: {total_global}件")
            if warning_count > 0:
                self.log(f">>> ⚠️ {warning_count}個のフォルダで件数不一致あり（上記確認）")
            else:
                self.log(">>> ✅ 全フォルダ件数チェック問題なし")
            self.log(">>> [全工程終了]")

        except Exception as e:
            self.log(f"!! 停止: {e}")
            traceback.print_exc()
        finally:
            self.is_extracting = False
            self.btn_extract.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            self.global_status_var.set("全体状況: 完了")

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
