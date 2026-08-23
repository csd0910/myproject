import os
import re
import time
import sqlite3
import imaplib
import email.utils
import pickle
from datetime import datetime
from email.message import EmailMessage

# Google OAuth 用のライブラリ
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# ==========================================
# --- 設定値 ---
# ==========================================
# サイボウズのテキストデータが入っているフォルダ（適宜書き換えてください）
SOURCE_DIR = r"C:\Users\フォーレスト026\Desktop\サイボウズメール抽出案件\KatoTEST3"

# 配置していただいたJSONファイルのパス
CLIENT_SECRET_FILE = r"C:\Users\フォーレスト026\MyProject\tools\Thunderbird.To.Gmail\client_secret_267873789173-97hptdc8k66skml4l5df8v2g81n5ovt6.apps.googleusercontent.com.json"

# 対象のGmailアドレス（ブラウザでログインするアカウントと同じものを指定してください）
EMAIL_USER = "ご自身のメールアドレス@forest.co.jp"

# システム設定
DB_PATH = "gmail_sync_status.db"
TOKEN_PATH = "token.pickle"
DAILY_LIMIT_BYTES = 450 * 1024 * 1024
IMAP_SERVER = "imap.gmail.com"
PARENT_LABEL = "サイボウズ"
SLEEP_SECONDS_ON_LIMIT = (24 * 60 * 60) + (5 * 60)
SCOPES = ['https://mail.google.com/'] # Gmailの全権限（IMAP操作用）

# ==========================================
# --- OAuth2 認証処理 ---
# ==========================================
def get_imap_connection():
    """OAuth2で認証し、IMAPセッションを返す"""
    creds = None
    # 過去に取得したトークンがあれば読み込む
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
            
    # トークンがない、または期限切れの場合は再取得・リフレッシュ
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"トークンの更新に失敗しました。再認証します: {e}")
                creds = None
                
        if not creds:
            print("ブラウザを開いてGoogleログイン認証を行います...")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # 取得したトークンを次回用に保存
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)

    # IMAPのXOAUTH2用認証文字列を生成
    auth_string = 'user=%s\1auth=Bearer %s\1\1' % (EMAIL_USER, creds.token)
    
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993)
    mail.authenticate('XOAUTH2', lambda x: auth_string.encode('utf-8'))
    return mail

# ==========================================
# --- コンバート・DB管理処理 ---
# ==========================================
def convert_txt_to_email(file_path):
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    msg = EmailMessage()
    body_lines = []
    
    date_pattern = re.compile(r'^Date:\s*(\d{4}/\d{1,2}/\d{1,2})\([日月火水木金土]\)\s*(\d{1,2}:\d{2})')
    from_pattern = re.compile(r'^From:\s*(.*?)(?:\s*アドレス帳に登録する)?$')
    to_pattern = re.compile(r'^To:\s*(.*?)(?:\s*アドレス帳に登録する)?$')
    subject_pattern = re.compile(r'^Subject:\s*(.*)$')
    
    in_header = True
    internal_date = None
    
    for line in lines:
        if in_header:
            date_match = date_pattern.match(line)
            if date_match:
                date_str = f"{date_match.group(1)} {date_match.group(2)}"
                dt = datetime.strptime(date_str, "%Y/%m/%d %H:%M")
                msg['Date'] = email.utils.format_datetime(dt)
                internal_date = imaplib.Time2Internaldate(dt)
                continue
            from_match = from_pattern.match(line)
            if from_match:
                msg['From'] = from_match.group(1).strip()
                continue
            to_match = to_pattern.match(line)
            if to_match:
                msg['To'] = to_match.group(1).strip()
                continue
            subject_match = subject_pattern.match(line)
            if subject_match:
                msg['Subject'] = subject_match.group(1).strip()
                continue
            if line.strip() == "":
                in_header = False
                continue
        else:
            if "HTMLメールの解析処理により" in line or "変更前の内容を確認する場合は" in line:
                continue
            body_lines.append(line)

    msg.set_content("".join(body_lines))
    return msg.as_bytes(), internal_date

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS processed_mails (message_id TEXT PRIMARY KEY, synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS daily_traffic (date TEXT PRIMARY KEY, bytes_sent INTEGER DEFAULT 0)''')
    conn.commit()
    return conn

def get_today_traffic(conn):
    today = time.strftime("%Y-%m-%d")
    cursor = conn.cursor()
    cursor.execute("SELECT bytes_sent FROM daily_traffic WHERE date = ?", (today,))
    row = cursor.fetchone()
    return row[0] if row else 0

def update_today_traffic(conn, size_bytes):
    today = time.strftime("%Y-%m-%d")
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO daily_traffic (date, bytes_sent) VALUES (?, ?) ON CONFLICT(date) DO UPDATE SET bytes_sent = bytes_sent + ?''', (today, size_bytes, size_bytes))
    conn.commit()

# ==========================================
# --- メイン同期処理 ---
# ==========================================
def sync_emails():
    print("=== OAuth2対応: テキスト➔Gmail 自動移行ジョブを開始 ===")
    conn = init_db()
    cursor = conn.cursor()
    
    while True:
        try:
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] IMAPサーバーに接続しています...")
            mail = get_imap_connection()
            print("接続に成功しました！")
        except Exception as e:
            print(f"❌ 接続エラー（10分後に再試行します）: {e}")
            time.sleep(600)
            continue

        success_count = 0
        skip_count = 0
        all_completed = True
        limit_reached = False

        # カレントディレクトリをスクリプトと同じ場所にしてDB作成を安定させる
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        for root, dirs, files in os.walk(SOURCE_DIR):
            if limit_reached: break

            for file in files:
                if not file.endswith(".txt"):
                    continue
                    
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                msg_id = f"TXT_{file}_{file_size}"
                
                cursor.execute("SELECT 1 FROM processed_mails WHERE message_id = ?", (msg_id,))
                if cursor.fetchone():
                    skip_count += 1
                    continue
                
                today_traffic = get_today_traffic(conn)
                if today_traffic + file_size > DAILY_LIMIT_BYTES:
                    print(f"\n⚠️ 本日のアップロード上限（450MB）に達しました。")
                    limit_reached = True
                    all_completed = False
                    break

                try:
                    converted_bytes, internal_date = convert_txt_to_email(file_path)
                except Exception as e:
                    print(f"\n⚠️ 変換エラー ({file}): {e}")
                    continue

                rel_path = os.path.relpath(root, SOURCE_DIR)
                gmail_label = PARENT_LABEL if rel_path == "." else f"{PARENT_LABEL}_{rel_path.replace('\\', '/')}"

                try:
                    print(f"   -> [{gmail_label}] へ転送中: {file}...", end="")
                    mail.append(f'"{gmail_label}"', '\\Seen', internal_date, converted_bytes)
                    
                    cursor.execute("INSERT INTO processed_mails (message_id) VALUES (?)", (msg_id,))
                    update_today_traffic(conn, len(converted_bytes))
                    conn.commit()
                    
                    print(" 完了")
                    success_count += 1
                    time.sleep(1.0) # Google側の負担軽減
                    
                except Exception as e:
                    print(f"\n❌ IMAPアップロードエラー: {e}")
                    all_completed = False
                    limit_reached = True
                    break

        try:
            mail.logout()
        except:
            pass
        
        print(f"\n[セッション結果] 新規同期: {success_count} 件 / スキップ: {skip_count} 件")

        if all_completed:
            print("\n🎉 すべてのメールデータ移行が終了しました！")
            break
            
        if limit_reached:
            print(f"💤 Googleの制限を回避するため、24時間5分待機します。")
            time.sleep(SLEEP_SECONDS_ON_LIMIT)

if __name__ == "__main__":
    sync_emails()
