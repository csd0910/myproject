import os
import subprocess
import socket
from datetime import datetime
import threading
import traceback

class NASLogger:
    def __init__(self, nas_path, username=None, password=None):
        self.nas_path = nas_path
        self.username = username
        self.password = password

    def _authenticate(self):
        # ネットワークドライブの認証を試みる
        if self.username and self.password:
            cmd = f'net use "{self.nas_path}" "{self.password}" /user:"{self.username}"'
            try:
                # パスワードがログに残らないように配慮
                subprocess.run(cmd, shell=True, capture_output=True, text=True)
            except Exception:
                pass

    def log_usage(self, count, elapsed_seconds, char_count=0, comment_count=0):
        def _write():
            try:
                # NASへのアクセス確認と認証
                if not os.path.exists(self.nas_path):
                    self._authenticate()
                
                # フォルダが存在しなければ作成を試みる
                os.makedirs(self.nas_path, exist_ok=True)
                
                # ファイル名の生成: PC名_YYYYMMDDHHMM.txt
                hostname = socket.gethostname()
                date_str = datetime.now().strftime('%Y%m%d%H%M')
                filename = f"{hostname}_{date_str}.txt"
                filepath = os.path.join(self.nas_path, filename)
                
                # 時間削減のよりリアルな計算
                # 1. 基本動作: メール1件開いてファイルを作るのに60秒
                base_time = count * 60
                # 2. コメント展開・コピペの手間: コメント1件につき15秒の追加
                comment_time = comment_count * 15
                # 3. テキストのスクロール・選択の手間: 500文字ごとに5秒の追加
                text_time = (char_count // 500) * 5
                
                manual_time_seconds = base_time + comment_time + text_time
                saved_seconds = manual_time_seconds - elapsed_seconds
                
                def format_time(sec):
                    if sec < 0: return "0秒"
                    m, s = divmod(int(sec), 60)
                    h, m = divmod(m, 60)
                    if h > 0: return f"{h}時間{m}分{s}秒"
                    if m > 0: return f"{m}分{s}秒"
                    return f"{s}秒"

                # ログの書き込み（追記モード）
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_content = (
                    f"[{timestamp}] 抽出完了\n"
                    f"  ・抽出件数: {count} 件\n"
                    f"  ・総文字数: 約 {char_count:,} 文字 (コメント {comment_count} 件含有)\n"
                    f"  ・ツール実行時間: {format_time(elapsed_seconds)}\n"
                    f"  ・手作業想定時間: {format_time(manual_time_seconds)} (基本60秒/件 + 長文・コメント加算)\n"
                    f"  ★削減できた時間: {format_time(saved_seconds)}\n"
                    f"{'-'*40}\n"
                )
                with open(filepath, "a", encoding="utf-8") as f:
                    f.write(log_content)
                    
            except Exception as e:
                # ログ転送エラー時はローカルのerror_log.txtに書き込んで原因を追えるようにする
                try:
                    with open("error_log.txt", "a", encoding="utf-8") as f:
                        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] NASロガーエラー: {str(e)}\n")
                except:
                    pass

        # メインスレッド（抽出処理など）をブロックしないようにバックグラウンドで実行
        threading.Thread(target=_write, daemon=True).start()

    def log_error(self, err_msg):
        def _write():
            try:
                if not os.path.exists(self.nas_path):
                    self._authenticate()
                os.makedirs(self.nas_path, exist_ok=True)
                
                hostname = socket.gethostname()
                date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{hostname}_エラー_{date_str}.txt"
                filepath = os.path.join(self.nas_path, filename)
                
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_content = f"[{timestamp}] エラー発生\n{err_msg}\n"
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(log_content)
            except Exception as e:
                try:
                    with open("error_log.txt", "a", encoding="utf-8") as f:
                        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] NASロガーエラー(log_error): {str(e)}\n")
                except:
                    pass

        threading.Thread(target=_write, daemon=True).start()
