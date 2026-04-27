import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd

class FileSplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Excel/CSV 分割ツール (Ver 1.1)")
        self.root.geometry("600x650")
        
        # タイトル
        title_label = tk.Label(root, text="Excel/CSV 分割ツール", font=("Meiryo", 16, "bold"))
        title_label.pack(pady=10)

        # 1. ファイルリスト選択
        file_frame = tk.LabelFrame(root, text="1. 処理するファイル（複数選択可）", padx=10, pady=10)
        file_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        self.file_listbox = tk.Listbox(file_frame, selectmode="extended", height=6)
        self.file_listbox.pack(side="left", fill="both", expand=True, padx=5)
        
        scrollbar = tk.Scrollbar(file_frame, orient="vertical", command=self.file_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        
        btn_frame = tk.Frame(file_frame)
        btn_frame.pack(side="right", fill="y", padx=5)
        tk.Button(btn_frame, text="ファイル追加", command=self.add_files).pack(fill="x", pady=2)
        tk.Button(btn_frame, text="選択を削除", command=self.remove_selected).pack(fill="x", pady=2)
        tk.Button(btn_frame, text="リストクリア", command=self.clear_list).pack(fill="x", pady=2)

        # 2. 保存先設定
        save_frame = tk.LabelFrame(root, text="2. 保存先の指定", padx=10, pady=10)
        save_frame.pack(fill="x", padx=20, pady=5)
        
        self.save_dir = tk.StringVar(value="(ファイルと同じ場所)")
        tk.Entry(save_frame, textvariable=self.save_dir, width=50, state="readonly").pack(side="left", padx=5)
        tk.Button(save_frame, text="フォルダ選択", command=self.select_save_dir).pack(side="left")

        # 3. 設定項目
        settings_frame = tk.LabelFrame(root, text="3. 分割設定", padx=10, pady=10)
        settings_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(settings_frame, text="ヘッダー行数:").grid(row=0, column=0, sticky="w", pady=5)
        self.header_rows = tk.IntVar(value=1)
        tk.Entry(settings_frame, textvariable=self.header_rows, width=10).grid(row=0, column=1, sticky="w")

        tk.Label(settings_frame, text="1ファイルあたりのデータ行数:").grid(row=1, column=0, sticky="w", pady=5)
        self.split_rows = tk.IntVar(value=50000)
        tk.Entry(settings_frame, textvariable=self.split_rows, width=10).grid(row=1, column=1, sticky="w")

        tk.Label(settings_frame, text="出力形式:").grid(row=2, column=0, sticky="w", pady=5)
        self.out_format = tk.StringVar(value="xlsx")
        format_frame = tk.Frame(settings_frame)
        format_frame.grid(row=2, column=1, sticky="w")
        tk.Radiobutton(format_frame, text="Excel (.xlsx)", variable=self.out_format, value="xlsx").pack(side="left")
        tk.Radiobutton(format_frame, text="CSV (.csv)", variable=self.out_format, value="csv").pack(side="left")

        # 4. 実行ボタン
        self.run_btn = tk.Button(root, text="処理開始", font=("Meiryo", 12, "bold"), 
                                 bg="#4CAF50", fg="white", height=2, width=20, command=self.run_all)
        self.run_btn.pack(pady=10)

        # 進捗状況
        self.progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=5)
        self.status = tk.Label(root, text="準備完了", fg="gray")
        self.status.pack()

    def add_files(self):
        paths = filedialog.askopenfilenames(
            filetypes=[("データファイル", "*.xlsx *.csv"), ("Excel", "*.xlsx"), ("CSV", "*.csv")]
        )
        for p in paths:
            if p not in self.file_listbox.get(0, tk.END):
                self.file_listbox.insert(tk.END, p)

    def remove_selected(self):
        selected = self.file_listbox.curselection()
        for i in reversed(selected):
            self.file_listbox.delete(i)

    def clear_list(self):
        self.file_listbox.delete(0, tk.END)

    def select_save_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.save_dir.set(path)

    def update_status(self, text, color="black"):
        self.status.config(text=text, fg=color)
        self.root.update_idletasks()

    def run_all(self):
        files = self.file_listbox.get(0, tk.END)
        if not files:
            messagebox.showerror("エラー", "ファイルを追加してください。")
            return

        try:
            h_rows = self.header_rows.get()
            s_rows = self.split_rows.get()
            out_ext = self.out_format.get()
            custom_save_dir = self.save_dir.get()
            if custom_save_dir == "(ファイルと同じ場所)":
                custom_save_dir = None

            self.run_btn.config(state="disabled")
            self.progress["maximum"] = len(files)
            self.progress["value"] = 0

            for idx, input_file in enumerate(files):
                self.update_status(f"処理中 ({idx+1}/{len(files)}): {os.path.basename(input_file)}", "blue")
                self.split_single_file(input_file, h_rows, s_rows, out_ext, custom_save_dir)
                self.progress["value"] = idx + 1

            self.update_status("すべての処理が完了しました！", "green")
            messagebox.showinfo("完了", f"合計 {len(files)} 個のファイルの処理が完了しました。")

        except Exception as e:
            self.update_status("エラーが発生しました", "red")
            messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n{str(e)}")
        
        finally:
            self.run_btn.config(state="normal")
            self.progress["value"] = 0

    def split_single_file(self, input_file, h_rows, s_rows, out_ext, custom_save_dir):
        _, input_ext = os.path.splitext(input_file)
        input_ext = input_ext.lower()
        header_list = list(range(h_rows))
        
        if input_ext == ".csv":
            df = pd.read_csv(input_file, header=header_list)
        else:
            df = pd.read_excel(input_file, header=header_list)

        total_rows = len(df)
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        # 保存先の決定
        dir_name = custom_save_dir if custom_save_dir else os.path.dirname(input_file)
        
        count = 0
        for i in range(0, total_rows, s_rows):
            count += 1
            chunk = df.iloc[i : i + s_rows]
            output_name = f"{base_name}(分割済み{count}).{out_ext}"
            output_path = os.path.join(dir_name, output_name)
            
            if out_ext == "csv":
                chunk.to_csv(output_path, index=False, encoding="utf-8-sig")
            else:
                chunk.to_excel(output_path, index=False)

if __name__ == "__main__":
    try:
        import pandas
        import openpyxl
    except ImportError:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("起動エラー", "pandas または openpyxl がインストールされていません。")
        sys.exit(1)

    root = tk.Tk()
    app = FileSplitterApp(root)
    root.mainloop()
