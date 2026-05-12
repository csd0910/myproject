import csv
import os
import re
import json
from datetime import datetime, timedelta
from collections import defaultdict

# 除外キーワード（技術ノイズ）
EXCLUDE_KEYWORDS = [
    '付箋', 'Program Manager', 'Quick Settings', 'クイック設定', 'Snipping Tool', 
    'Windows セキュリティ', 'サインイン', 'ログイン', '新しいタブ', '無題', 
    '新しい通知', 'スナップ アシスト', 'タスク マネージャー', 'エクスプローラー',
    'cmd.exe', 'Terminal', 'ecmd.exe', 'ESET', 'freee人事労務', '使用中のファイル',
    'Working...', '項目の削除', '複数ファイルの削除', 'ファイルが更新されました'
]

def get_verbed_content(content, topic_map, date):
    text = re.sub(r'\[.*?\]\s*', '', content).strip()
    for p in ['閲覧: ', '利用: ', 'ファイル更新: ', '件名: ']:
        text = text.replace(p, '')
    
    if any(k.lower() in text.lower() for k in EXCLUDE_KEYWORDS) or len(text) < 4:
        return None, None

    cat = "その他"
    verbed = text
    
    if '[AI相談]' in content or 'Antigravity' in text:
        topics = topic_map.get(date, ["システム開発・改善"])
        verbed = f"Antigravityでの「{topics[0]}」の開発・相談"
        cat = "システム開発"
    elif 'Gitコミット:' in text or '[開発]' in content:
        msg = text.replace('Gitコミット:', '').strip()
        verbed = f"プログラム（{msg}）の開発・修正"
        cat = "システム開発"
    elif any(ext in text.lower() for ext in ['.xlsx', '.xlsm', '.csv']):
        filename = text.split('\\')[-1].split(' - ')[0]
        verbed = f"Excel（{filename}）の入力・編集"
        cat = "事務・データ処理"
    elif any(ext in text.lower() for ext in ['.pdf']):
        filename = text.split('\\')[-1].split(' - ')[0]
        verbed = f"PDF（{filename}）の確認"
        cat = "事務・データ処理"
    elif 'サイボウズ' in text.lower() or 'cybozu' in text.lower():
        title = re.sub(r' - (Microsoft Edge|Google Chrome|My profile .*?)$', '', text).strip()
        # 特定のページ名を抽出
        title = title.split(' - ')[0]
        verbed = f"サイボウズ（{title}）の操作"
        cat = "サイボウズ関連"
    elif any(k in text.lower() for k in ['thunderbird', 'outlook', 'メール']):
        verbed = f"メールの閲覧・作成"
        cat = "メール対応"
    else:
        clean_title = re.sub(r' - (Microsoft Edge|Google Chrome|My profile .*?)$', '', text).strip()
        if len(clean_title) > 5:
            verbed = f"Web（{clean_title.split(' - ')[0]}）の調査"
            cat = "情報調査"

    return verbed, cat

def summarize_final():
    input_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\ActivityLog_0410_0512.csv"
    output_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\ActivitySummary_Helpdesk_Final.csv"
    
    topic_map = {}
    try:
        import subprocess
        result = subprocess.check_output(['python', 'scratch/get_brain_topics.py'], encoding='utf-8')
        topic_map = json.loads(result)
    except: pass

    if not os.path.exists(input_file): return

    # day -> category -> list of events
    daily_data = defaultdict(lambda: defaultdict(list))

    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < 3: continue
            date, time, content = row
            dt_obj = datetime.strptime(f"{date} {time}", "%Y/%m/%d %H:%M:%S")
            verbed, cat = get_verbed_content(content, topic_map, date)
            if verbed:
                daily_data[date][cat].append({'dt': dt_obj, 'verbed': verbed})

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['日付', 'カテゴリ', '発生日時', '終了日時', '実作業時間(概算)', '内容（転記用）'])
        
        for date in sorted(daily_data.keys()):
            for cat in sorted(daily_data[date].keys()):
                events = sorted(daily_data[date][cat], key=lambda x: x['dt'])
                start = events[0]['dt']
                end = events[-1]['dt']
                
                # アクティビティごとに時間帯を管理
                activity_blocks = defaultdict(list)
                for e in events:
                    activity_blocks[e['verbed']].append(e['dt'])
                
                formatted_activities = []
                for verbed, dts in activity_blocks.items():
                    dts.sort()
                    # 時間帯ブロックの作成 (15分以内の間隔なら継続とみなす)
                    blocks = []
                    if dts:
                        b_start = dts[0]
                        b_prev = dts[0]
                        for i in range(1, len(dts)):
                            if (dts[i] - b_prev).total_seconds() > 900: # 15分以上の空き
                                blocks.append(f"{b_start.strftime('%H:%M')}～{b_prev.strftime('%H:%M')}")
                                b_start = dts[i]
                            b_prev = dts[i]
                        # 終了時刻が開始と同じなら最低5分加算して表示
                        end_val = b_prev
                        if b_start == end_val:
                            end_val = b_start + timedelta(minutes=5)
                        blocks.append(f"{b_start.strftime('%H:%M')}～{end_val.strftime('%H:%M')}")
                    
                    time_ranges = ", ".join(blocks)
                    formatted_activities.append(f"{verbed} ({time_ranges})")
                
                content_text = " / ".join(formatted_activities)
                if len(content_text) > 1000: content_text = content_text[:997] + "..."
                
                # 実作業時間の概算（全イベントの合計）
                total_seconds = 0
                if len(events) > 0:
                    # 全体の継続時間を計算（重複を避けるため、15分単位のブロックの和）
                    all_dts = sorted([e['dt'] for e in events])
                    b_start = all_dts[0]
                    b_prev = all_dts[0]
                    for i in range(1, len(all_dts)):
                        if (all_dts[i] - b_prev).total_seconds() > 900:
                            total_seconds += (b_prev - b_start).total_seconds() + 300
                            b_start = all_dts[i]
                        b_prev = all_dts[i]
                    total_seconds += (b_prev - b_start).total_seconds() + 300
                
                hours, remainder = divmod(int(total_seconds), 3600)
                minutes, _ = divmod(remainder, 60)
                duration_str = f"{hours}:{minutes:02d}"

                writer.writerow([
                    date,
                    cat,
                    start.strftime('%H:%M'),
                    end.strftime('%H:%M'),
                    duration_str,
                    content_text
                ])

if __name__ == "__main__":
    summarize_final()
