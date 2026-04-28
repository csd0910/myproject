import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import re
import glob
import mailbox
import email
from email.message import EmailMessage
from email.utils import formatdate
import traceback
import threading
from datetime import datetime
import shutil

class CybozuMboxConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cybozu MBOX Converter V3.6 - Native Path Fixed")
        self.root.geometry("850x800")
        
        self.root_dir = ""
        self.tb_local_folders = ""
        self.folder_data = {} 
        
        self.create_widgets()
        self.detect_thunderbird_path()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 1. 入力設定
        input_frame = ttk.LabelFrame(main_frame, text="1. バックアップ済みデータを読み込む", padding=5)
        input_frame.pack(fill=tk.X, pady=5)
        self.src_path_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.src_path_var, width=65).pack(side=tk.LEFT, padx=5)
        ttk.Button(input_frame, text="フォルダ選択", command=self.browse_src).pack(side=tk.LEFT)
        ttk.Button(input_frame, text="データ分析", command=self.scan_folders).pack(side=tk.LEFT, padx=10)

        # 2. プレビュー
        list_frame = ttk.LabelFrame(main_frame, text="2. 階層構造のプレビュー", padding=5)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.tree = ttk.Treeview(list_frame, columns=("count", "status"), show="tree headings")
        self.tree.heading("#0", text="サイボウズのフォルダ構成"); self.tree.heading("count", text="メール通数"); self.tree.heading("status", text="状態")
        self.tree.column("count", width=100); self.tree.column("status", width=100); self.tree.pack(fill=tk.BOTH, expand=True)

        # 3. 実行設定 (MBOXファイル作成)
        exec_frame = ttk.LabelFrame(main_frame, text="3. MBOXデータの作成", padding=5)
        exec_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(exec_frame, text="出力先フォルダ名:").grid(row=0, column=0, sticky=tk.E, pady=5)
        self.target_sub_var = tk.StringVar(value=f"Cybozu_Backup_{datetime.now().strftime('%m%d_%H%M')}")
        ttk.Entry(exec_frame, textvariable=self.target_sub_var, width=35).grid(row=0, column=1, sticky=tk.W, padx=10)
        
        self.btn_convert = ttk.Button(exec_frame, text="ローカルにMBOXファイルを作成する", command=self.start_process, state=tk.DISABLED)
        self.btn_convert.grid(row=0, column=2, padx=5, pady=5)
        
        # 4. Thunderbirdへのエクスポート
        export_frame = ttk.LabelFrame(main_frame, text="4. Thunderbirdへエクスポート (ローカルフォルダにコピー)", padding=5)
        export_frame.pack(fill=tk.X, pady=5)
        ttk.Label(export_frame, text="※Thunderbirdを終了してから実行してください。", foreground="#D32F2F", font=("Meiryo", 9, "bold")).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=2)
        
        self.tb_path_var = tk.StringVar(value="未検出")
        ttk.Label(export_frame, textvariable=self.tb_path_var, font=("Meiryo", 8), foreground="gray").grid(row=1, column=0, padx=10, sticky=tk.W)
        ttk.Button(export_frame, text="手動指定", command=self.manual_browse_tb).grid(row=1, column=1)

        self.btn_export = ttk.Button(export_frame, text="Thunderbirdへエクスポート", command=self.start_export, state=tk.DISABLED)
        self.btn_export.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=5)

        self.status_var = tk.StringVar(value="待機中")
        ttk.Label(main_frame, textvariable=self.status_var, font=("Meiryo", 10, "bold"), foreground="blue").pack(pady=2)

        log_frame = ttk.LabelFrame(main_frame, text="物理階層 構築ログ", padding=5); log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text = tk.Text(log_frame, height=10, font=("Consolas", 9), background="#fefefe"); self.log_text.pack(fill=tk.BOTH, expand=True)

    def log(self, msg):
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.log_text.see(tk.END); self.root.update()

    def browse_src(self):
        p = filedialog.askdirectory(); self.src_path_var.set(os.path.abspath(p)) if p else None

    def manual_browse_tb(self):
        p = filedialog.askdirectory(title="Select Local Folders path")
        if p: self.tb_local_folders = p; self.tb_path_var.set(f"同期先: ...{p[-40:]}")

    def detect_thunderbird_path(self):
        try:
            appdata = os.getenv('APPDATA'); ini = os.path.join(appdata, 'Thunderbird', 'profiles.ini')
            if os.path.exists(ini):
                import configparser; config = configparser.ConfigParser(); config.read(ini, encoding='utf-8')
                for s in config.sections():
                    if config.has_option(s, 'Path'):
                        p = os.path.join(appdata, 'Thunderbird', config.get(s, 'Path')) if config.get(s, 'IsRelative','1')=='1' else config.get(s, 'Path')
                        loc = os.path.join(p, 'Mail', 'Local Folders'); 
                        if os.path.exists(loc): self.tb_local_folders = loc; self.tb_path_var.set(f"同期先: ...{loc[-40:]}"); return
        except: pass

    def scan_folders(self):
        root = self.src_path_var.get()
        if not root or not os.path.exists(root): return
        for it in self.tree.get_children(): self.tree.delete(it)
        self.folder_data = {}; nodes = {"": ""} 
        
        folders_found = 0
        for cur, ds, fs in os.walk(root):
            base_name = os.path.basename(cur)
            # 抽出ツールが作成した「個別(オリジナル)」または「◯◯_個別メール(オリジナル)」を対象にする
            if base_name == "個別(オリジナル)" or "個別メール(オリジナル)" in base_name:
                if base_name == "個別(オリジナル)":
                    rel = os.path.relpath(os.path.dirname(cur), root)
                else:
                    folder_true_name = base_name.replace("_個別メール(オリジナル)", "")
                    parent_rel = os.path.relpath(os.path.dirname(cur), root)
                    rel = folder_true_name if parent_rel == "." else os.path.join(parent_rel, folder_true_name)
                
                parts = rel.split(os.sep); curr_rel = ""; parent_id = ""
                for p in parts:
                    if not p or p == ".": continue
                    curr_rel = os.path.join(curr_rel, p) if curr_rel else p
                    if curr_rel not in nodes: nodes[curr_rel] = self.tree.insert(parent_id, "end", text=p, open=True)
                    parent_id = nodes[curr_rel]
                
                # globを使わずos.listdirで安全にファイルをカウント
                try:
                    txt_count = len([f for f in os.listdir(cur) if f.lower().endswith(".txt")])
                    if txt_count > 0:
                        self.tree.item(parent_id, values=(txt_count, "待機中"))
                        self.folder_data[parent_id] = { "actual_src": cur }
                        folders_found += 1
                except: pass
        
        self.log(f"分析完了。{folders_found}件の有効なフォルダを検出しました。")
        self.btn_convert.config(state=tk.NORMAL)

    def start_process(self):
        sub_name = self.target_sub_var.get().strip()
        if not sub_name: return
        
        # MBOX作成のベースを、読み込んだバックアップデータのあるフォルダ配下にする
        src_path = self.src_path_var.get()
        if not src_path or not os.path.exists(src_path):
            messagebox.showerror("エラー", "入力元の「バックアップ済みデータ」のフォルダが指定されていません。")
            return
            
        base_target = os.path.join(src_path, "MBOX_Output")
        os.makedirs(base_target, exist_ok=True)
        
        # 【最重要】Thunderbirdの物理構造 (MBOXファイル + .sbdフォルダ)
        self.current_output_mbox = os.path.join(base_target, sub_name)
        self.current_output_sbd = os.path.join(base_target, sub_name + ".sbd")
        
        if not os.path.exists(self.current_output_mbox): open(self.current_output_mbox, "wb").close()
        os.makedirs(self.current_output_sbd, exist_ok=True)
        
        self.log(f"【MBOXローカル作成】")
        self.log(f"  出力先フォルダ: {base_target}")
        self.log(f"  入口ファイル: {self.current_output_mbox}")
        self.log(f"  階層フォルダ: {self.current_output_sbd}")
        
        self.btn_convert.config(state=tk.DISABLED)
        threading.Thread(target=self._process, args=(self.current_output_sbd,), daemon=True).start()

    def _process(self, sbd_root):
        try:
            self.log(">>> MBOX作成処理中...")
            self.status_var.set("MBOX作成中...")
            def run_node(node_id, current_sbd_path):
                name_text = self.tree.item(node_id, "text")
                safe_name = re.sub(r'[\\/:*?"<>|]', '_', name_text)
                
                # 自分自身のMBOX
                mbox_file = os.path.join(current_sbd_path, safe_name)
                if node_id in self.folder_data:
                    actual_src = self.folder_data[node_id]["actual_src"]
                    self._convert_to_mbox(actual_src, mbox_file, name_text)
                    
                    # 【追加要望】各元のフォルダ直下にも「フォルダ名.mbox」を配置する
                    try:
                        direct_mbox_file = os.path.join(actual_src, f"{safe_name}.mbox")
                        if os.path.exists(mbox_file) and os.path.getsize(mbox_file) > 0:
                            shutil.copy2(mbox_file, direct_mbox_file)
                    except Exception as e:
                        self.log(f"  -> 個別フォルダへの.mbox配置に失敗: {e}")
                        
                    self.tree.item(node_id, values=(self.tree.item(node_id, "values")[0], "完了"))
                else:
                    if not os.path.exists(mbox_file): open(mbox_file, "wb").close()
                
                # 子がいれば.sbdを作って掘り下げる
                children = self.tree.get_children(node_id)
                if children:
                    child_sbd = os.path.join(current_sbd_path, safe_name + ".sbd")
                    os.makedirs(child_sbd, exist_ok=True)
                    for c in children: run_node(c, child_sbd)

            for rn in self.tree.get_children(""): run_node(rn, sbd_root)
            self.log(f">>> ローカルMBOX作成完了！ (出力先: {sbd_root})")
            self.status_var.set("MBOX作成完了。Thunderbirdへエクスポートできます。")
            messagebox.showinfo("作成完了", f"MBOXファイルの作成が完了しました。\n\n続いて「Thunderbirdへエクスポート」を行ってください。")
            self.btn_export.config(state=tk.NORMAL)
        except Exception as e: 
            self.log(f"!! エラー発生: {e}"); traceback.print_exc()
            self.status_var.set("エラーが発生しました")
        finally: 
            self.btn_convert.config(state=tk.NORMAL)

    def start_export(self):
        if not self.tb_local_folders: self.manual_browse_tb()
        if not self.tb_local_folders: return
        
        self.btn_export.config(state=tk.DISABLED)
        threading.Thread(target=self._export_process, daemon=True).start()
        
    def _export_process(self):
        try:
            self.log(f">>> ThunderbirdのLocal Foldersへデータをコピー中...")
            self.status_var.set("Thunderbirdへエクスポート中...")
            
            sub_name = self.target_sub_var.get().strip()
            tb_target_mbox = os.path.join(self.tb_local_folders, sub_name)
            tb_target_sbd = os.path.join(self.tb_local_folders, sub_name + ".sbd")
            
            # コピー処理
            if os.path.exists(self.current_output_mbox):
                shutil.copy2(self.current_output_mbox, tb_target_mbox)
            if os.path.exists(self.current_output_sbd):
                if os.path.exists(tb_target_sbd):
                    shutil.rmtree(tb_target_sbd)
                shutil.copytree(self.current_output_sbd, tb_target_sbd)
                
            self.log(f">>> エクスポート完了！")
            self.status_var.set("エクスポート完了！")
            messagebox.showinfo("成功", f"Thunderbirdへのエクスポートが完了しました。\n\nThunderbirdを起動し、「ローカルフォルダ」の中に『{sub_name}』が表示されていることを確認してください。")
        except Exception as e:
            self.log(f"!! エクスポートに失敗しました: {e}"); traceback.print_exc()
            self.status_var.set("エクスポートエラー")
            messagebox.showerror("エラー", f"エクスポート中にエラーが発生しました。\nThunderbirdが起動したままでないか確認してください。\n{e}")
        finally:
            self.btn_export.config(state=tk.NORMAL)

    def _convert_to_mbox(self, src_dir, mbox_path, folder_name):
        try:
            txt_files = [os.path.join(src_dir, f) for f in os.listdir(src_dir) if f.lower().endswith(".txt")]
        except: return
        
        if not txt_files: return
        self.log(f"  [結合] {folder_name} ({len(txt_files)}通)")
        with open(mbox_path, "ab") as mf:
            for txt in txt_files:
                try:
                    with open(txt, "r", encoding="utf-8", errors="replace") as f: content = f.read()
                    subject, sender, dt = "No Subject", "unknown@example.com", ""
                    ms = re.search(r'(?:【件名】|Subject:)[\s:：]*([^\n]+)', content); subject = ms.group(1).strip() if ms else subject
                    ms = re.search(r'(?:【(?:差出人|送信者)】|From:)[\s:：]*([^\n]+)', content); sender = ms.group(1).replace("アドレス帳に登録する", "").strip() if ms else sender
                    ms = re.search(r'(?:【(?:日時|最終更新/日時)】|Date:)[\s:：]*([^\n]+)', content); dt = ms.group(1).strip() if ms else ""
                    msg = EmailMessage(); msg['Subject'] = subject; msg['From'] = sender
                    msg['Date'] = self._parse_date(dt); msg.set_content(content)
                    
                    # 【追加】各メールの単独EMLファイルもテキストと同じ場所に出力する
                    eml_path = os.path.splitext(txt)[0] + ".eml"
                    try:
                        with open(eml_path, "wb") as ef:
                            ef.write(msg.as_bytes())
                    except: pass
                    
                    mbox_user = sender.split('<')[-1].strip('> ')
                    mf.write(f"From {mbox_user} {datetime.now().strftime('%a %b %d %H:%M:%S %Y')}\n".encode('ascii','replace'))
                    mf.write(msg.as_bytes()); mf.write(b"\n\n")
                except: continue

    def _parse_date(self, date_str):
        try:
            cl = re.sub(r'\([^\)]+\)', '', date_str)
            dt = datetime.strptime(cl.strip(), '%Y/%m/%d %H:%M')
            return formatdate(dt.timestamp(), localtime=True)
        except: return formatdate(localtime=True)

if __name__ == "__main__":
    root = tk.Tk(); app = CybozuMboxConverterApp(root); root.mainloop()
