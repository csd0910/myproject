import csv
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

# 除外する具体的でないキーワード（これらのみ、またはこれら＋ページ数の場合は除外）
STRICT_VAGUE_KEYWORDS = [
    'ログイン', '設定', 'エラー', 'プロパティ', 'Windows セキュリティ', '通知', 
    '検索結果', '属性の詳細', '閲覧', '起動しています', 'お知らせ', 'プロパティの確認',
    'Windows ツール', 'クイック設定', '正常性ダッシュボード', 'パスワードの入力',
    'ネットワーク', '作成完了', '保存エラー', 'インポート', '詳細設定', '詳細設定の確認',
    'パスワードを保存しますか？', 'パスワードを保存しますか?', 'ユーザーの詳細パネル',
    '開いているファイル', 'ネットワーク接続の復元', '印刷中', '記録エラー', '出力エラー'
]

def is_strictly_vague(content):
    # 余計な修飾を剥ぎ取る
    core = content
    core = re.sub(r' に関するトラブル対応・設定$', '', core)
    core = re.sub(r' および他 \d+ ページ$', '', core)
    core = re.sub(r'^閲覧: ', '', core)
    core = core.strip()
    
    # 剥ぎ取った結果がキーワードリストに含まれる、または極端に短い場合は除外
    if core in STRICT_VAGUE_KEYWORDS:
        return True
    if len(core) <= 2:
        return True
    return False

def simplify_content(content):
    # 内容を報告書向けに短く整形
    res = content
    res = re.sub(r' に関するトラブル対応・設定$', '', res)
    res = re.sub(r' および他 \d+ ページ$', '', res)
    res = re.sub(r'^閲覧: ', '', res)
    res = re.sub(r' のジャンプ リスト$', '', res)
    
    # 特徴的なサービス名を前に出す
    if 'サイボウズ' in res:
        res = f"サイボウズ：{res.replace('サイボウズ：', '').split(' - ')[0]}"
    if 'メール' in res:
        res = f"メール：{res.replace('メール：', '').split(' - ')[0]}"
    
    return res.strip()

def format_helpdesk_report_v2():
    input_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\ActivityLog_0410_0512.csv"
    output_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\Helpdesk_Report_Simple.txt"
    
    if not os.path.exists(input_file):
        return

    daily_data = defaultdict(list)

    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < 3: continue
            date_str, time_str, content = row
            
            clean_content = re.sub(r'\[.*?\]\s*', '', content).strip()
            # ブラウザのゴミを削除
            clean_content = re.sub(r' - (Microsoft Edge|Google Chrome|My profile .*?)$', '', clean_content).strip()
            
            # ヘルプデスク系キーワード判定（前回のロジック流用）
            from extract_helpdesk_tasks import is_helpdesk_task
            
            if is_helpdesk_task(clean_content):
                if is_strictly_vague(clean_content):
                    continue
                
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")
                display_name = simplify_content(clean_content)
                daily_data[date_str].append({'dt': dt, 'content': display_name})

    with open(output_file, 'w', encoding='utf-8-sig') as f:
        for date_str in sorted(daily_data.keys()):
            formatted_date = date_str.replace('2026/', '') # 4/10 形式
            f.write(f"\n{formatted_date} ＊＊＊＊＊＊＊＊＊＊＊＊＊\n")
            
            # 内容ごとに時間を集約
            events = daily_data[date_str]
            activity_times = defaultdict(list)
            for ev in events:
                activity_times[ev['content']].append(ev['dt'])
            
            # 最初の発生時間順にソート
            sorted_activities = sorted(activity_times.items(), key=lambda x: min(x[1]))
            
            for content, dts in sorted_activities:
                dts.sort()
                blocks = []
                b_start = dts[0]
                b_prev = dts[0]
                for i in range(1, len(dts)):
                    if (dts[i] - b_prev).total_seconds() > 1800: # 30分間隔で別ブロック
                        blocks.append((b_start, b_prev))
                        b_start = dts[i]
                    b_prev = dts[i]
                blocks.append((b_start, b_prev))
                
                for start, end in blocks:
                    if start == end:
                        end = start + timedelta(minutes=5)
                    
                    # ユーザー指定の「HH:MM HH:MM 内容」形式
                    f.write(f"{start.strftime('%H:%M')}　{end.strftime('%H:%M')}　{content}\n")

    print(f"Simple report created at: {output_file}")

if __name__ == "__main__":
    format_helpdesk_report_v2()
