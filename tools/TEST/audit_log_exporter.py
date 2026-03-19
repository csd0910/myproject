import os
import csv
import socket
import datetime
import subprocess
import xml.etree.ElementTree as ET

# --- 設定値 ---
# 監視対象アプリ（イベントログのProcessNameに含まれるか判定）
TARGET_APPS = ['chrome.exe', 'msedge.exe', 'thunderbird.exe', 'outlook.exe']
# NASへの保存先
NAS_DIR = r"Y:\システム統括部\業改室\★大宮システム部\（NAS）伊藤\TESTLOG"
LOCAL_CACHE = os.path.join(os.environ.get('LOCALAPPDATA', 'C:\\'), 'mail_audit_cache.csv')
HOSTNAME = socket.gethostname()

def get_audit_events():
    """
    セキュリティイベントログから イベントID 4663 (ファイルシステムへのアクセス) を抽出し、
    過去1時間（または直近）のイベントリストを返す。
    """
    # PowerShellを使ってイベントログを取得し、XML形式で出力する
    # ※動作を軽くするため過去1時間分(-o 1h など)のみ取得するか、最も新しいN件を取得
    ps_cmd = (
        r'Get-WinEvent -FilterHashtable @{LogName="Security"; Id=4663} -MaxEvents 500 '
        r'-ErrorAction SilentlyContinue | ConvertTo-Xml -As string'
    )
    result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        return []

    events = []
    try:
        root = ET.fromstring(result.stdout)
        for obj in root.findall(".//Object"):
            event_data = {}
            for prop in obj.findall("Property"):
                name = prop.get("Name")
                val = prop.text if prop.text else ""
                event_data[name] = val

            # 必要な情報のみ抽出
            if "ProcessName" in event_data and "ObjectName" in event_data:
                events.append({
                    "TimeCreated": event_data.get("TimeCreated", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    "ProcessName": event_data["ProcessName"],
                    "ObjectName": event_data["ObjectName"],  # フルパス
                    "AccessMask": event_data.get("AccessMask", "")
                })
    except ET.ParseError:
        pass

    return events

def write_log(record):
    """CSVへ書き出す"""
    nas_file = os.path.join(NAS_DIR, f"audit_{HOSTNAME}.csv")

    try:
        if not os.path.exists(NAS_DIR):
            raise FileNotFoundError("NAS is offline")

        # キャッシュの転記
        if os.path.exists(LOCAL_CACHE):
            with open(LOCAL_CACHE, 'r', encoding='utf-8-sig') as f:
                cache_data = f.read()
            with open(nas_file, 'a', encoding='utf-8-sig', newline='') as f:
                f.write(cache_data)
            os.remove(LOCAL_CACHE)

        file_exists = os.path.exists(nas_file)
        with open(nas_file, 'a', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "Hostname", "App", "Target File"])
            writer.writerow(record)

    except Exception:
        file_exists = os.path.exists(LOCAL_CACHE)
        with open(LOCAL_CACHE, 'a', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "Hostname", "App", "Target File"])
            writer.writerow(record)

def main():
    events = get_audit_events()
    for ev in events:
        proc_name = getattr(ev.get("ProcessName", ""), 'lower', lambda: "")()
        target_file = ev.get("ObjectName", "")
        timestamp = ev.get("TimeCreated", "")

        # ターゲットアプリが含まれているか判定
        is_target_app = any(app in proc_name for app in TARGET_APPS)

        # 0x1 は ReadData (ファイルの読み取り) 権限
        is_read_access = "0x1" in ev.get("AccessMask", "")

        if is_target_app and is_read_access:
            # アプリ名だけをきれいに抽出（フルパスから実行ファイル名へ）
            clean_app_name = os.path.basename(proc_name) if "\\" in proc_name else proc_name
            record = [timestamp, HOSTNAME, clean_app_name, target_file]
            write_log(record)

    # 実際には、同じイベント（重複）を再び送らないよう、
    # 最後に処理したイベントの時刻などをローカルに記録しておく仕組みを追加すると完璧です。

if __name__ == "__main__":
    main()
