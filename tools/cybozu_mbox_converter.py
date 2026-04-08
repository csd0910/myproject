import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import glob
import re
import datetime
import uuid
import email.utils
from email.message import EmailMessage
import mailbox
import threading
import time

class CybozuMboxConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("サイボウズ抽出ログ → MBOX変換ツール")
        self.root.geometry("650x400")
        self.is_running = False
        
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 送信元(From)のダミーアドレス設定
        ttk.Label(main_frame, text="設定する『送信元 (From)』のメールアドレス:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.from_email_var = tk.StringVar(value="myemail@company.local")
        self.from_email_entry = ttk.Entry(main_frame, textvariable=self.from_email_var, width=50)
        self.from_email_entry.grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=5)

        # 自身の表示名（名前）
        ttk.Label(main_frame, text="設定する『自分の名前 (表示名)』:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.my_name_var = tk.StringVar(value="私")
        self.my_name_entry = ttk.Entry(main_frame, textvariable=self.my_name_var, width=50)
        self.my_name_entry.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=5)

        # 変換元フォルダ
        ttk.Label(main_frame, text="オリジナル(.txt)が入った抽出済フォルダ:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.src_dir_var = tk.StringVar()
        self.src_dir_entry = ttk.Entry(main_frame, textvariable=self.src_dir_var, width=50)
        self.src_dir_entry.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        self.btn_browse = ttk.Button(main_frame, text="参照...", command=self.browse_directory)
        self.btn_browse.grid(row=2, column=3, padx=5, pady=5)

        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(row=3, column=0, columnspan=4, sticky="ew", pady=15)
        
        # ステータス表示
        self.status_var = tk.StringVar(value="ステータス: 待機中")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, font=("Meiryo", 10, "bold"), foreground="blue")
        self.status_label.grid(row=4, column=0, columnspan=4, sticky=tk.W, pady=5)

        # カウンタ表示
        self.count_var = tk.StringVar(value="完了: 0 ファイル (合計 0 メッセージ)")
        self.count_label = ttk.Label(main_frame, textvariable=self.count_var, font=("Meiryo", 10))
        self.count_label.grid(row=5, column=0, columnspan=4, sticky=tk.W, pady=5)

        # 変換ボタン
        self.btn_convert = ttk.Button(main_frame, text="MBOX変換を開始", command=self.start_conversion)
        self.btn_convert.grid(row=6, column=0, columnspan=4, pady=20, ipadx=30, ipady=10)
        
        note_text = ("※サイボウズから抽出された txt ファイルを読み込み、Gmail(Thunderbird経由)などで\n"
                     "読み込める「cybozu_sent_migration.mbox」を同じフォルダに出力します。")
        ttk.Label(main_frame, text=note_text, foreground="red").grid(row=7, column=0, columnspan=4, sticky=tk.W, pady=5)

    def browse_directory(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.src_dir_var.set(dir_path)

    def parse_cybozu_date_to_rfc(self, date_str):
        # 2024/02/05(月) 15:30 -> RFC2822
        match_date = re.search(r'(\d{4})[\-/](\d{1,2})[\-/](\d{1,2}).*?(?:(\d{1,2}):(\d{2}))?', date_str)
        if match_date:
            y = int(match_date.group(1))
            m = int(match_date.group(2))
            d = int(match_date.group(3))
            hh = int(match_date.group(4)) if match_date.group(4) else 0
            mm = int(match_date.group(5)) if match_date.group(5) else 0
            # 日本時間 (+09:00) を想定
            dt = datetime.datetime(y, m, d, hh, mm, tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
            return email.utils.format_datetime(dt)
        # 解析不能な場合は現在時刻を返す
        return email.utils.format_datetime(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))))

    def remove_noise(self, content):
        noise_patterns = [
            r"確認しました", r"返信する", r"全員に返信", r"転送する", 
            r"詳細を見る", r"削除する", r"迷惑メール", r"ヘッダーを表示",
            r"印刷する", r"宛先をすべて表示する", r"宛先から削除されたユーザー（\d+人）"
        ]
        # ノイズを完全に除去するが、添付ファイル名などの自然なテキストは残る
        for pattern in noise_patterns:
            content = re.sub(r'^\s*' + pattern + r'\s*$', '', content, flags=re.MULTILINE)
        return content

    def generate_message_id(self):
        return f"<{uuid.uuid4()}@cybozu.migration.local>"

    def start_conversion(self):
        target_dir = self.src_dir_var.get().strip()
        from_email = self.from_email_var.get().strip()
        my_name = self.my_name_var.get().strip()
        
        if not target_dir or not os.path.exists(target_dir):
            messagebox.showwarning("警告", "正しい変換元フォルダを選択してください。")
            return
            
        if not from_email:
            messagebox.showwarning("警告", "送信元のダミーメールアドレスを入力してください。")
            return

        self.btn_convert.config(state=tk.DISABLED)
        self.status_var.set("ステータス: 変換リソースを準備中...")
        self.is_running = True
        
        threading.Thread(target=self._conversion_process, args=(target_dir, from_email, my_name), daemon=True).start()

    def _conversion_process(self, target_dir, from_email, my_name):
        output_mbox_path = os.path.join(target_dir, "cybozu_sent_migration.mbox")
        
        try:
            if os.path.exists(output_mbox_path):
                os.remove(output_mbox_path)
                
            mbox = mailbox.mbox(output_mbox_path)
            mbox.lock()
            
            txt_files = glob.glob(os.path.join(target_dir, "*.txt"))
            file_count = 0
            message_count = 0
            
            for filepath in txt_files:
                if not self.is_running:
                    break
                if "抽出済み履歴" in filepath or "README" in filepath:
                    continue
                    
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        text_content = f.read()
                except Exception:
                    continue
                
                # ====== の線で区切られた「各メールの独立した塊」をすべてリスト化する
                # これにより、結合版ルールの当時のテキストであっても一切ロスせずに全件取りこぼしなく抽出できます
                email_blocks = re.split(r'={20,}', text_content)
                
                for block in email_blocks:
                    block = block.strip()
                    if not block:
                        continue
                        
                    # このブロックが通常のメール（親）としての体裁を持っているか確認
                    match_dt = re.search(r'【(?:日時|最終更新/日時)】[\s:：]*([^\n]+)', block)
                    if not match_dt:
                        # 全文が単なる改行やゴミデータ、あるいは「社内メールのコメントの塊」である場合は例外処理
                        # 社内メールのコメントを拾う
                        comment_matches = list(re.finditer(r'^(\d+)\s*:\s*\n+([^\n]+)\s*\n+(\d{4}/\d{1,2}/\d{1,2}[^\n]*)\s*\n', block, flags=re.MULTILINE))
                        if comment_matches:
                            for idx, c_match in enumerate(comment_matches):
                                c_num = c_match.group(1)
                                c_name = c_match.group(2).strip(" \t:：")
                                c_date = c_match.group(3).strip()
                                
                                start_pos = c_match.end()
                                end_pos = comment_matches[idx+1].start() if idx + 1 < len(comment_matches) else len(block)
                                c_body = block[start_pos:end_pos].strip()
                                c_body = self.remove_noise(c_body)
                                
                                c_msg = EmailMessage()
                                # メアドが含まれない名前単体会避用
                                safe_c_name = c_name if ("<" in c_name or "@" in c_name) else f'"{c_name}" <{from_email}>'
                                c_msg['From'] = safe_c_name
                                c_msg['To'] = f'"自分" <{from_email}>'
                                c_msg['Subject'] = "Re: 社内メールコメント"
                                c_msg['Date'] = self.parse_cybozu_date_to_rfc(c_date)
                                c_msg['Message-ID'] = self.generate_message_id()
                                c_msg.set_content(f"【サイボウズ コメント番号 {c_num}】\n発言者: {c_name}\n\n{c_body}")
                                mbox.add(c_msg)
                                message_count += 1
                        continue

                    # 正規のメールブロックの場合
                    date_str = match_dt.group(1).replace("\r", "").replace("\n", "").strip(" \t:：")
                    
                    sender = "Unknown Sender"
                    match_sender = re.search(r'【(?:差出人|送信者)】[\s:：]*([^\n]+)', block)
                    if match_sender:
                        # 末尾の\rやゴミテキストを完全に清掃
                        sender = match_sender.group(1).replace("\r", "").replace("\n", "").replace("アドレス帳に登録する", "").strip(" \t:：")
                    
                    to_address = "Unknown Recipient"
                    match_to = re.search(r'【宛先】[\s:：]*([^\n]+)', block)
                    if match_to:
                        to_address = match_to.group(1).replace("\r", "").replace("\n", "").replace("アドレス帳に登録する", "").strip(" \t:：")
                    
                    subject = "無題"
                    match_subj = re.search(r'【件名】[\s:：]*([^\n]+)', block)
                    if match_subj: subject = match_subj.group(1).replace("\r", "").replace("\n", "").strip(" \t:：")
                    
                    # 本文の切り出し
                    main_body = ""
                    if "【本文】" in block:
                        main_body = block.split("【本文】")[-1].strip()
                    else:
                        main_body = block # ヘッダしかない場合
                    
                    main_body = self.remove_noise(main_body)
                    
                    # メール作成
                    msg = EmailMessage()
                    
                    # Thunderbirdの拡張機能クラッシュを防ぐため、メアドを含まない場合は必ずダミーアドレスで包む
                    safe_sender = sender if ("<" in sender or "@" in sender) else f'"{sender}" <{from_email}>'
                    safe_to = to_address if ("<" in to_address or "@" in to_address) else f'"{to_address}" <dummy_to@cybozu.local>'
                    
                    msg['From'] = safe_sender
                    msg['To'] = safe_to
                    msg['Subject'] = subject
                    msg['Date'] = self.parse_cybozu_date_to_rfc(date_str)
                    
                    parent_message_id = self.generate_message_id()
                    msg['Message-ID'] = parent_message_id
                    
                    msg.set_content(f"【抽出元: サイボウズOffice】\n\n{main_body}")
                    mbox.add(msg)
                    message_count += 1

                file_count += 1
                self.count_var.set(f"完了: {file_count} ファイル (合計 {message_count} メッセージ)")
                
            mbox.flush()
            mbox.unlock()
            
            self.status_var.set(f"変換完了！ '{output_mbox_path}' を出力しました。")
            messagebox.showinfo("成功", f"変換が完了しました！\n{file_count}ファイルの履歴から\n合計 {message_count} 通のMBOXメールデータを生成しました。\n\nThunderbird等でインポートしてGmailに同期させてください。")
            
        except Exception as e:
            self.status_var.set("エラーが発生しました。")
            messagebox.showerror("エラー", f"MBOX変換中にエラーが発生しました:\n{str(e)}")
        finally:
            self.is_running = True
            self.btn_convert.config(state=tk.NORMAL)

    def on_closing(self):
        self.is_running = False
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CybozuMboxConverterApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
