import sys
import datetime
import os
import subprocess

def connect_nas(nas_root, user, password):
    # すでにアクセス可能であれば何もしない
    if os.path.exists(nas_root):
        return True
    # net use コマンドで接続情報（資格情報）を送信する
    cmd = f'net use "{nas_root}" {password} /user:{user}'
    try:
        subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    if len(sys.argv) < 4:
        print("Usage: python nas_logger.py <STATUS> <PC_NAME> <MESSAGE>")
        return

    status = sys.argv[1]
    pc_name = sys.argv[2]
    message = sys.argv[3]
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] 状態: {status} | 詳細: {message}\n"
    
    # NASのルートとパス、認証情報
    nas_root = r"\\10.85.33.230\01_全社共有"
    nas_dir = r"\\10.85.33.230\01_全社共有\システム統括部\業改室\★大宮システム部\（NAS）伊藤\AppUpdateログ"
    nas_user = "frt_user"
    nas_pass = "Forest0720@"
    
    # 書き込み前にNASへの認証を試みる
    connect_nas(nas_root, nas_user, nas_pass)
    
    # 同時書き込みによるエラー（ロック）を防ぐため、PCごとにファイルを分ける
    log_filename = f"{pc_name}_更新ログ.txt"
    
    try:
        # フォルダが存在しない場合（ネットワーク未接続など）はエラーになる
        if not os.path.exists(nas_dir):
            os.makedirs(nas_dir, exist_ok=True)
            
        log_file = os.path.join(nas_dir, log_filename)
        with open(log_file, "a", encoding="utf-8-sig") as f:
            f.write(log_entry)
    except Exception as e:
        # NASへのアクセスに失敗した場合（VPN未接続や外出時など）はローカルにバックアップとして残す
        script_dir = os.path.dirname(os.path.abspath(__file__))
        fallback_log = os.path.join(script_dir, "fallback_nas_error.txt")
        with open(fallback_log, "a", encoding="utf-8-sig") as f:
            f.write(f"[{timestamp}] [NAS接続失敗: {e}] PC: {pc_name} | 状態: {status} | 詳細: {message}\n")

if __name__ == "__main__":
    main()
