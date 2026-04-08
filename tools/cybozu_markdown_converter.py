import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading

class CybozuMarkdownConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cybozu TXT to Markdown 変換ツール")
        self.root.geometry("550x350")
        
        # UI構築
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Markdownに一括変換したいTXTファイルが入っている「フォルダ」を選択してください。", 
                  font=("Meiryo", 9)).pack(pady=10)
        
        # ※標準ライブラリ（tkinter単体）ではドラッグ＆ドロップ機能が非対応のため、フォルダ選択方式にしています
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.target_var = tk.StringVar()
        ttk.Entry(btn_frame, textvariable=self.target_var, width=45).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="フォルダを参照...", command=self.browse_folder).pack(side=tk.LEFT)
        
        self.status_var = tk.StringVar(value="ステータス: 待機中")
        ttk.Label(main_frame, textvariable=self.status_var, font=("Meiryo", 10, "bold"), foreground="blue").pack(pady=20)
        
        self.btn_convert = ttk.Button(main_frame, text="Markdown (.md) へ変換", command=self.start_conversion)
        self.btn_convert.pack(pady=10, ipadx=30, ipady=10)
        
        note_text = ("【変換のルール】\n"
                     "・【件名】などをMarkdownの見出し（#）に変換します\n"
                     "・コメント番号や日時をサブ見出し（##）に変換します\n"
                     "・URLの自動リンク化およびシステム由来のノイズテキストの除去を行います")
        ttk.Label(main_frame, text=note_text, foreground="gray", justify=tk.LEFT).pack(side=tk.BOTTOM, anchor=tk.W)

    def browse_folder(self):
        d = filedialog.askdirectory()
        if d:
            self.target_var.set(d)

    def start_conversion(self):
        target_dir = self.target_var.get().strip()
        if not target_dir or not os.path.isdir(target_dir):
            messagebox.showwarning("エラー", "有効なフォルダパスを指定してください。")
            return
            
        self.btn_convert.config(state=tk.DISABLED)
        self.status_var.set("ステータス: 変換処理中...")
        
        # UIをフリーズさせないよう別スレッドで実行
        threading.Thread(target=self.process_files, args=(target_dir,), daemon=True).start()

    def process_files(self, target_dir):
        try:
            txt_files = [f for f in os.listdir(target_dir) if f.lower().endswith('.txt') and not "抽出済み履歴" in f]
            if not txt_files:
                self.root.after(0, lambda: self.status_var.set("ステータス: エラー - TXTファイルが見つかりません"))
                self.root.after(0, lambda: self.btn_convert.config(state=tk.NORMAL))
                return

            # 出力用の専用フォルダを作成する
            output_dir = os.path.join(target_dir, "md変換済み")
            os.makedirs(output_dir, exist_ok=True)

            converted_count = 0
            
            for filename in txt_files:
                filepath = os.path.join(target_dir, filename)
                self.convert_to_markdown(filepath, output_dir)
                converted_count += 1
                
            self.root.after(0, lambda: self.status_var.set(f"完了！ 合計 {converted_count} 件のファイルをMarkdownに変換しました。"))
            self.root.after(0, lambda: messagebox.showinfo("完了", f"{converted_count}件のファイルを「.md」へ変換しました！\n（フォルダ内の『md変換済み』フォルダに保存されています）"))
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"ステータス: エラー発生 ({str(e)})"))
        finally:
            self.root.after(0, lambda: self.btn_convert.config(state=tk.NORMAL))

    def convert_to_markdown(self, filepath, output_dir):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # ----------------------------------------------------
        # 1. サイボウズ特有のノイズ・不要な文字の除去
        # ----------------------------------------------------
        noise_patterns = [
            r"確認しました",
            r"\d+名",
            r"返信する",
            r"宛先をすべて表示する",
            r"宛先から削除されたユーザー（\d+人）",
            r"詳細を見る",
            r"ファイルを追加",
            r"詳細\s+\d+\s*[KMG]?B",
            r"プレビュー"
        ]
        for pattern in noise_patterns:
            # 万全を期すため空行を残さないよう、不要な文字の周りの空白も含めて消す
            content = re.sub(r'[\s]*' + pattern + r'[\s]*', '\n', content)

        # ----------------------------------------------------
        # 2. Markdown 見出しの構成
        # ----------------------------------------------------
        # メールやスレッドの本文仕切り線 ========== を より長く目立つ全角の長線に
        thick_line = "ー" * 80
        content = re.sub(r"={10,}", thick_line, content)

        # 【件名】 を一番大きい見出し (# ) に変換
        content = re.sub(r"【件名】\s*(.+)", r"# \1", content)
        
        # リストのメタデータを太字に
        content = re.sub(r"【日時】\s*", "**日時**: ", content)
        content = re.sub(r"【送信者】\s*", "**送信者**: ", content)
        content = re.sub(r"【最終更新/日時】\s*", "**最終更新**: ", content)
        
        # 【本文】ラベルは消す（Markdownでは本文がすぐに始まるのが自然なため）
        content = content.replace("【本文】\n", "")
        content = content.replace("【本文】", "")

        # ----------------------------------------------------
        # 3. コメント行のサブ見出し化と「枠線（区切り線）」の追加
        # ----------------------------------------------------
        # 実際のサイボウズデータは以下のような複数行に分かれているため行またぎで検出する
        # (例)
        # 200 :
        #
        # 岡村浩司
        #
        # 2026/4/6(月) 13:58
        def comment_header(match):
            num = match.group(1)
            name = match.group(2).strip()
            date = match.group(3).strip()
            
            # Notebook上で折り返されるくらい長く明確な区切り線
            thick_line = "ー" * 80
            return f"\n\n{thick_line}\n\n## 💬 コメント {num}： {name} ({date})\n\n"
            
        content = re.sub(r"^(\d+)\s*:\s*\n+([^\n]+)\s*\n+(\d{4}/\d{1,2}/\d{1,2}[^\n]+)\s*\n*", 
                         comment_header, content, flags=re.MULTILINE)

        # ----------------------------------------------------
        # 4. URLの自動リンク化 ([URL](URL))
        # ----------------------------------------------------
        # すでにMarkdownリンクの手順がされている部分を壊さずにリンク化する
        content = re.sub(r'(?<!\[)(https?://[a-zA-Z0-9_/:%#\$&\?\(\)~\.=\+\-]+)(?!\])', r'[\1](\1)', content)
        
        # 余分な改行（3行以上の連続する改行）を2行に圧縮して綺麗にする
        content = re.sub(r'\n{3,}', '\n\n', content)

        # ----------------------------------------------------
        # 出力保存（専用の出力先フォルダへ .md として出力）
        # ----------------------------------------------------
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        # BOMなしUTF-8での書き出し
        new_filepath = os.path.join(output_dir, f"{base_name}.md")
        
        with open(new_filepath, 'w', encoding='utf-8', newline="") as f:
            f.write(content)

if __name__ == "__main__":
    root = tk.Tk()
    app = CybozuMarkdownConverterApp(root)
    root.mainloop()
