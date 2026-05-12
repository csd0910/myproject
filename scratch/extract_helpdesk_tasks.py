import csv
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

# トラブル・ヘルプデスク関連のキーワード
HELPDESK_KEYWORDS = [
    'BitLocker', '回復キー', '不具合', '故障', 'エラー', 'フリーズ', '真っ白',
    '立ち上がらない', 'できない', 'ログイン', 'パスワード', '設定', '修正',
    '対応', '調査', 'リモート', 'Remote Desktop', 'Sandbox', 'Wi-Fi', 'ネットワーク',
    'ネット回線', 'プリンター', '印刷', 'ディスプレイ', 'キートップ', '不調',
    'タッチパッド', '脆弱性', 'セキュリティ', 'アップデート', '不審', 'ウイルス',
    'ESET', '接続', 'プロパティ', '管理センター', 'admin', 'コントロール パネル'
]

# 除外したいシステム操作（ノイズ）
NOISE_KEYWORDS = [
    'Program Manager', 'Quick Settings', '付箋', 'Working...', 'Snipping Tool'
]

def is_helpdesk_task(content):
    # ノイズチェック
    if any(k.lower() in content.lower() for k in NOISE_KEYWORDS):
        return False
    # キーワードマッチング
    return any(k.lower() in content.lower() for k in HELPDESK_KEYWORDS)

def extract_helpdesk():
    input_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\ActivityLog_0410_0512.csv"
    output_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\Helpdesk_Troubleshooting_Log.csv"
    
    if not os.path.exists(input_file):
        print("Input file not found.")
        return

    # day -> activity -> list of times
    daily_helpdesk = defaultdict(lambda: defaultdict(list))

    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < 3: continue
            date, time, content = row
            
            # クリーンアップ
            clean_content = re.sub(r'\[.*?\]\s*', '', content).strip()
            clean_content = re.sub(r' - (Microsoft Edge|Google Chrome|My profile .*?)$', '', clean_content).strip()
            
            if is_helpdesk_task(clean_content):
                # 読みやすい名称に変換
                if 'サイボウズ' in clean_content or 'cybozu' in clean_content:
                    display_name = f"サイボウズ（{clean_content.split(' - ')[0]}）の調査・対応"
                elif 'メール' in clean_content or 'Thunderbird' in clean_content:
                    display_name = f"メール（{clean_content.split(' - ')[0]}）でのトラブル対応"
                else:
                    display_name = f"{clean_content.split(' - ')[0]} に関するトラブル対応・設定"
                
                dt = datetime.strptime(f"{date} {time}", "%Y/%m/%d %H:%M:%S")
                daily_helpdesk[date][display_name].append(dt)

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['日付', '作業時間帯', '所要時間', 'トラブル・ヘルプデスク対応内容'])
        
        for date in sorted(daily_helpdesk.keys()):
            for activity, dts in daily_helpdesk[date].items():
                dts.sort()
                
                # 時間ブロックの統合（15分以内は連続）
                blocks = []
                b_start = dts[0]
                b_prev = dts[0]
                total_sec = 0
                
                for i in range(1, len(dts)):
                    if (dts[i] - b_prev).total_seconds() > 900:
                        blocks.append((b_start, b_prev))
                        total_sec += (b_prev - b_start).total_seconds() + 300
                        b_start = dts[i]
                    b_prev = dts[i]
                blocks.append((b_start, b_prev))
                total_sec += (b_prev - b_start).total_seconds() + 300
                
                time_range_str = ", ".join([f"{s.strftime('%H:%M')}～{e.strftime('%H:%M') if s != e else (s + timedelta(minutes=5)).strftime('%H:%M')}" for s, e in blocks])
                
                hours, remainder = divmod(int(total_sec), 3600)
                minutes, _ = divmod(remainder, 60)
                duration_str = f"{hours}:{minutes:02d}"
                
                writer.writerow([date, time_range_str, duration_str, activity])

    print(f"Helpdesk log created at: {output_file}")

if __name__ == "__main__":
    extract_helpdesk()
