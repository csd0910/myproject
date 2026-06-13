import os
import json
import threading
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

SETTINGS_FILE = "viewer_settings.json"
DEFAULT_ROOT_DIR = r"C:\Users\フォーレスト026\Desktop\サイボウズメール抽出案件\TESTEmailCybouz\20260526TEST"

class CybozuViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("社内メールビューア ver2 (テキスト・MD専用)")
        self.root.geometry("1100x700")
        
        self.settings = self.load_settings()
        self.current_items = [] 
        self.cancel_flag = False
        
        self.create_widgets()
        
        # 初回起動時のデフォルトパス設定（指定の格納フォルダ）
        last_dir = self.settings.get("last_dir")
        if not last_dir or not os.path.exists(last_dir):
            if os.path.exists(DEFAULT_ROOT_DIR):
                last_dir = DEFAULT_ROOT_DIR
                self.settings["last_dir"] = last_dir
                self.save_settings()
        
        # フォルダツリーを読み込み
        if last_dir and os.path.isdir(last_dir):
            self.dir_var.set(last_dir)
            self.load_folder_tree(last_dir)
            
            # 起動後に一番上のフォルダを自動選択して中身をすぐ表示
            children = self.folder_tree.get_children()
            if children:
                self.folder_tree.selection_set(children[0])
                self.folder_tree.focus(children[0])
                self.on_folder_select(None)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"last_dir": "", "history": []}
        
    def save_settings(self):
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def create_widgets(self):
        # 1. 検索・設定バー (Top)
        top_frame = ttk.Frame(self.root, padding=5)
        top_frame.pack(fill=tk.X)
        
        ttk.Label(top_frame, text="ルートフォルダ:").grid(row=0, column=0, sticky=tk.W, pady=2, padx=2)
        self.dir_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.dir_var, width=70).grid(row=0, column=1, sticky=tk.W, pady=2, padx=2)
        ttk.Button(top_frame, text="参照", command=self.browse_dir).grid(row=0, column=2, pady=2, padx=2)
        
        ttk.Label(top_frame, text="検索キーワード\n(カンマ区切り):").grid(row=1, column=0, sticky=tk.W, pady=2, padx=2)
        self.keyword_var = tk.StringVar()
        self.keyword_combo = ttk.Combobox(top_frame, textvariable=self.keyword_var, width=67, values=self.settings.get("history", []))
        self.keyword_combo.grid(row=1, column=1, sticky=tk.W, pady=2, padx=2)
        
        cond_target_frame = ttk.Frame(top_frame)
        cond_target_frame.grid(row=1, column=2, sticky=tk.W, padx=10)
        
        self.search_cond_var = tk.StringVar(value="AND")
        ttk.Radiobutton(cond_target_frame, text="AND", variable=self.search_cond_var, value="AND").pack(side=tk.LEFT)
        ttk.Radiobutton(cond_target_frame, text="OR", variable=self.search_cond_var, value="OR").pack(side=tk.LEFT, padx=5)
        
        ttk.Label(cond_target_frame, text=" | 検索対象: ").pack(side=tk.LEFT, padx=(5,0))
        self.search_target_var = tk.StringVar(value="BODY")
        ttk.Radiobutton(cond_target_frame, text="本文", variable=self.search_target_var, value="BODY").pack(side=tk.LEFT)
        ttk.Radiobutton(cond_target_frame, text="タイトル", variable=self.search_target_var, value="TITLE").pack(side=tk.LEFT, padx=5)
        
        # 期間抽出UIの追加
        ttk.Label(top_frame, text="期間(YYYY/MM/DD):").grid(row=2, column=0, sticky=tk.W, pady=2, padx=2)
        date_frame = ttk.Frame(top_frame)
        date_frame.grid(row=2, column=1, sticky=tk.W, padx=2)
        self.date_start_var = tk.StringVar()
        ttk.Entry(date_frame, textvariable=self.date_start_var, width=15).pack(side=tk.LEFT)
        ttk.Label(date_frame, text=" ～ ").pack(side=tk.LEFT)
        self.date_end_var = tk.StringVar()
        ttk.Entry(date_frame, textvariable=self.date_end_var, width=15).pack(side=tk.LEFT)
        
        # 検索ボタン群 (縦に大きくする)
        btn_frame = ttk.Frame(top_frame)
        btn_frame.grid(row=1, column=3, rowspan=2, sticky=tk.N+tk.S, padx=15)
        
        self.search_btn = tk.Button(btn_frame, text=" 検 索 ", font=("Meiryo UI", 11, "bold"), bg="#e1f0ff", command=self.start_search)
        self.search_btn.pack(side=tk.LEFT, fill=tk.Y, pady=2)
        
        self.cancel_btn = tk.Button(btn_frame, text="中止", font=("Meiryo UI", 10), command=self.cancel_search, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, fill=tk.Y, padx=(5,0), pady=2)
        
        self.status_var = tk.StringVar(value="待機中")
        ttk.Label(top_frame, textvariable=self.status_var).grid(row=3, column=1, columnspan=4, sticky=tk.W, padx=2, pady=2)

        # 2. メインの3ペイン (PanedWindow)
        self.paned_main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左ペイン: フォルダツリー
        left_frame = ttk.Frame(self.paned_main)
        self.paned_main.add(left_frame, weight=1)
        
        self.folder_tree = ttk.Treeview(left_frame, show="tree")
        self.folder_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self.folder_tree.bind("<<TreeviewSelect>>", self.on_folder_select)
        
        f_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.folder_tree.yview)
        f_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.folder_tree.configure(yscrollcommand=f_scroll.set)
        
        # 右ペイン (上下分割)
        self.paned_right = ttk.PanedWindow(self.paned_main, orient=tk.VERTICAL)
        self.paned_main.add(self.paned_right, weight=3)
        
        # 右上: メール一覧
        right_top_frame = ttk.Frame(self.paned_right)
        self.paned_right.add(right_top_frame, weight=1)
        
        columns = ("title", "sender", "date")
        self.mail_list = ttk.Treeview(right_top_frame, columns=columns, show="headings")
        self.mail_list.heading("title", text="タイトル", command=lambda: self.sort_column("title", False))
        self.mail_list.heading("sender", text="送信者", command=lambda: self.sort_column("sender", False))
        self.mail_list.heading("date", text="日時", command=lambda: self.sort_column("date", False))
        
        self.mail_list.column("title", width=400)
        self.mail_list.column("sender", width=120)
        self.mail_list.column("date", width=150)
        self.mail_list.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self.mail_list.bind("<<TreeviewSelect>>", self.on_mail_select)
        
        ml_scroll = ttk.Scrollbar(right_top_frame, orient=tk.VERTICAL, command=self.mail_list.yview)
        ml_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.mail_list.configure(yscrollcommand=ml_scroll.set)
        
        # 右下: メール本文表示
        right_bottom_frame = ttk.Frame(self.paned_right)
        self.paned_right.add(right_bottom_frame, weight=2)
        
        self.mail_content = tk.Text(right_bottom_frame, wrap=tk.WORD, font=("Meiryo UI", 10), bg="#fdfdfd")
        self.mail_content.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self.mail_content.tag_config("highlight", background="yellow", foreground="black")
        
        mc_scroll = ttk.Scrollbar(right_bottom_frame, orient=tk.VERTICAL, command=self.mail_content.yview)
        mc_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.mail_content.configure(yscrollcommand=mc_scroll.set)

    def browse_dir(self):
        d = filedialog.askdirectory(initialdir=self.dir_var.get())
        if d:
            self.dir_var.set(d)
            self.settings["last_dir"] = d
            self.save_settings()
            self.load_folder_tree(d)

    def load_folder_tree(self, root_path):
        self.folder_tree.delete(*self.folder_tree.get_children())
        # ルートフォルダ自体は表示せず、その直下にある「受信箱」「管理部」などをトップレベルとしてツリーに表示する
        self.populate_tree("", root_path)
        
    def populate_tree(self, parent, path):
        try:
            items = os.listdir(path)
            # フォルダだけを抽出。「_MD」で終わる、もしくは「_MD」を含むフォルダを除外
            dirs = [d for d in items if os.path.isdir(os.path.join(path, d)) and "_MD" not in d]
            for d in sorted(dirs):
                p = os.path.join(path, d)
                # トップレベル（parent==""）は開いた状態にする
                node = self.folder_tree.insert(parent, "end", text=d, values=(p,), open=(parent == ""))
                self.populate_tree(node, p)
        except Exception:
            pass

    def on_folder_select(self, event):
        selected = self.folder_tree.selection()
        if not selected: return
        folder_path = self.folder_tree.item(selected[0], "values")[0]
        # フォルダが選択されたら、中身を読み込む
        self.load_mails_in_folder(folder_path)

    def parse_md_file(self, filepath):
        title = "名称不明"
        sender = "不明"
        date = ""
        filename = os.path.basename(filepath)
        
        parts = filename.replace(".md", "").replace(".txt", "").split("_", 3)
        if len(parts) >= 4:
            date = f"{parts[0]} {parts[1]}"
            sender = parts[2]
            title = parts[3]
        elif len(parts) >= 3:
            date = parts[0]
            sender = parts[1]
            title = parts[2]
            
        content = ""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                lines = content.split('\n')
                for line in lines[:15]:
                    # Markdown形式
                    if line.startswith("**日時**:"): date = line.split(":", 1)[1].strip()
                    elif line.startswith("**送信者**:"): sender = line.split(":", 1)[1].strip()
                    elif line.startswith("# "): title = line[2:].strip()
                    # オリジナルテキスト形式
                    elif line.startswith("日時:"): date = line.split(":", 1)[1].strip()
                    elif line.startswith("差出人:"): sender = line.split(":", 1)[1].strip()
                    elif line.startswith("件名:"): title = line.split(":", 1)[1].strip()
        except Exception:
            pass
            
        return {"filepath": filepath, "title": title, "sender": sender, "date": date, "content": content}

    def _parse_date_to_int(self, date_str):
        if not date_str: return 0
        match = re.search(r'(\d{4})[/\-]?(\d{1,2})[/\-]?(\d{1,2})', date_str)
        if match:
            y, m, d = match.groups()
            return int(f"{y}{int(m):02d}{int(d):02d}")
        return 0
        
    def is_in_date_range(self, date_str, start_date, end_date):
        if start_date == 0 and end_date == 99999999:
            return True
        mail_date = self._parse_date_to_int(date_str)
        if mail_date == 0:
            return False
        return start_date <= mail_date <= end_date

    def load_mails_in_folder(self, folder_path):
        self.mail_list.delete(*self.mail_list.get_children())
        self.mail_content.delete(1.0, tk.END)
        self.current_items = []
        
        start_date = self._parse_date_to_int(self.date_start_var.get()) if self.date_start_var.get().strip() else 0
        end_date = self._parse_date_to_int(self.date_end_var.get()) if self.date_end_var.get().strip() else 99999999
        
        try:
            for root, dirs, files in os.walk(folder_path):
                # サブフォルダから「_MD」を含むものを除外
                dirs[:] = [d for d in dirs if "_MD" not in d]
                
                for item in files:
                    if item.lower().endswith(('.md', '.txt')):
                        filepath = os.path.join(root, item)
                        info = self.parse_md_file(filepath)
                        
                        if not self.is_in_date_range(info["date"], start_date, end_date):
                            continue
                            
                        self.current_items.append(info)
                        self.mail_list.insert("", "end", values=(info["title"], info["sender"], info["date"]), tags=(filepath,))
        except Exception:
            pass
            
    def on_mail_select(self, event):
        selected = self.mail_list.selection()
        if not selected: return
        filepath = self.mail_list.item(selected[0], "tags")[0]
        
        info = next((i for i in self.current_items if i["filepath"] == filepath), None)
        if info:
            self.mail_content.delete(1.0, tk.END)
            self.mail_content.insert(tk.END, info["content"])
            
            raw_keyword = self.keyword_var.get().strip().replace('、', ',')
            keywords = [k.strip() for k in raw_keyword.split(',') if k.strip()]
            if keywords:
                for k in keywords:
                    start_idx = "1.0"
                    while True:
                        idx = self.mail_content.search(k, start_idx, tk.END)
                        if not idx: break
                        end_idx = f"{idx}+{len(k)}c"
                        self.mail_content.tag_add("highlight", idx, end_idx)
                        start_idx = end_idx

    def start_search(self):
        root_dir = self.dir_var.get().strip()
        raw_keyword = self.keyword_var.get().strip()
        
        if not root_dir or not os.path.isdir(root_dir):
            messagebox.showwarning("警告", "有効なルートフォルダを選択してください。")
            return
            
        # 期間の取得
        start_date = self._parse_date_to_int(self.date_start_var.get()) if self.date_start_var.get().strip() else 0
        end_date = self._parse_date_to_int(self.date_end_var.get()) if self.date_end_var.get().strip() else 99999999
            
        raw_keyword_fmt = raw_keyword.replace('、', ',')
        keywords = [k.strip() for k in raw_keyword_fmt.split(',') if k.strip()]
        
        # キーワードが空で日付絞り込みもない場合は全件表示として扱う
        if not keywords and start_date == 0 and end_date == 99999999:
            pass
        
        self.settings["last_dir"] = root_dir
        history = self.settings.get("history", [])
        if raw_keyword and raw_keyword not in history:
            history.insert(0, raw_keyword)
            self.settings["history"] = history[:10]
            self.keyword_combo['values'] = self.settings["history"]
        self.save_settings()
        
        self.mail_list.delete(*self.mail_list.get_children())
        self.mail_content.delete(1.0, tk.END)
        self.current_items = []
        self.cancel_flag = False
        self.search_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        
        cond = self.search_cond_var.get()
        target = self.search_target_var.get()
        threading.Thread(target=self.search_worker, args=(root_dir, keywords, cond, target, start_date, end_date), daemon=True).start()

    def cancel_search(self):
        self.cancel_flag = True
        self.status_var.set("検索をキャンセルしています...")

    def search_worker(self, root_dir, keywords, cond, target, start_date, end_date):
        count = 0
        hit_count = 0
        self.status_var.set("検索中...")
        
        for root, dirs, files in os.walk(root_dir):
            if self.cancel_flag: break
            
            # 検索時も「_MD」フォルダを除外する
            dirs[:] = [d for d in dirs if "_MD" not in d]
            
            for f in files:
                if self.cancel_flag: break
                if f.lower().endswith(('.md', '.txt')):
                    filepath = os.path.join(root, f)
                    count += 1
                    
                    try:
                        info = self.parse_md_file(filepath)
                        
                        # 日付チェック
                        if not self.is_in_date_range(info["date"], start_date, end_date):
                            continue
                            
                        # キーワードチェック (キーワードがある場合のみ)
                        match = True
                        if keywords:
                            text = info["title"] if target == "TITLE" else info["content"]
                            match = False
                            if cond == "AND":
                                if all(k in text for k in keywords): match = True
                            else:
                                if any(k in text for k in keywords): match = True
                                
                        if match:
                            hit_count += 1
                            self.current_items.append(info)
                            self.root.after(0, lambda i=info, p=filepath: self.mail_list.insert("", "end", values=(i["title"], i["sender"], i["date"]), tags=(p,)))
                    except Exception:
                        pass
                        
        if self.cancel_flag:
            self.root.after(0, self.status_var.set, f"キャンセルされました。 (対象:{count}件中 ヒット:{hit_count}件)")
        else:
            self.root.after(0, self.status_var.set, f"検索完了！ (対象:{count}件中 ヒット:{hit_count}件)")
            
        self.root.after(0, self.search_btn.config, {"state": tk.NORMAL})
        self.root.after(0, self.cancel_btn.config, {"state": tk.DISABLED})

    def sort_column(self, col, reverse):
        l = [(self.mail_list.set(k, col), k) for k in self.mail_list.get_children('')]
        l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l):
            self.mail_list.move(k, '', index)
        self.mail_list.heading(col, command=lambda: self.sort_column(col, not reverse))

if __name__ == "__main__":
    root = tk.Tk()
    app = CybozuViewerApp(root)
    root.mainloop()
