import csv
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

def clean_dev_label(content):
    res = content
    # 不要なプレフィックス削除
    res = re.sub(r'^閲覧: ', '', res)
    res = re.sub(r' - Google (検索|Gemini)$', '', res)
    res = re.sub(r' - (Microsoft Edge|Google Chrome|Mozilla Thunderbird)$', '', res)
    
    low = res.lower()
    
    # 開発系キーワードの統合
    if 'antigravity' in low:
        return 'AIアシスタントを活用した開発・相談'
    if 'visual studio code' in low or 'vscode' in low:
        return 'VS Codeでのプログラム実装・修正'
    if 'powershell' in low or 'terminal' in low or 'コマンド プロンプト' in res:
        return 'システム操作・コマンド実行'
    if 'git' in low or 'github' in low:
        if 'commit' in low or 'コミット' in res:
            return 'Gitコミット・リポジトリ管理'
        return 'GitHubでのソースコード管理・確認'
    if 'qiita' in low or 'stack overflow' in low or 'e-stat' in low or 'api' in low:
        return '技術調査・API仕様の確認（Qiita等）'
    if 'エクスプローラー' in res:
        return 'プロジェクト内のファイル整理・確認'
    
    # 特になければそのまま（ただし長すぎる場合はカット）
    if len(res) > 50:
        res = res[:47] + "..."
    
    return res.strip()

def format_development_report():
    input_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\Development_Activity_Log.csv"
    output_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\Development_Report_Final.txt"
    
    if not os.path.exists(input_file):
        print(f"File not found: {input_file}")
        return

    daily_events = defaultdict(list)

    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        
        for row in reader:
            if len(row) < 4: continue
            date_str = row[0]      # 2026/04/13
            time_ranges = row[1]   # "18:11～18:16, 18:27～18:40, ..."
            content = row[3]       # Content
            
            label = clean_dev_label(content)
            if not label: continue
            
            # 時間範囲を分割してリスト化
            # カンマで区切られた複数の時間を抽出
            ranges = time_ranges.replace('"', '').split(',')
            for r in ranges:
                r = r.strip()
                if '～' not in r: continue
                start_s, end_s = r.split('～')
                
                try:
                    start_dt = datetime.strptime(f"{date_str} {start_s}", "%Y/%m/%d %H:%M")
                    end_dt = datetime.strptime(f"{date_str} {end_s}", "%Y/%m/%d %H:%M")
                    daily_events[date_str].append({'start': start_dt, 'end': end_dt, 'label': label})
                except Exception:
                    continue

    with open(output_file, 'w', encoding='utf-8-sig') as f:
        for date_str in sorted(daily_events.keys()):
            m_d = date_str.split('/')
            f.write(f"\n{int(m_d[1])}/{int(m_d[2])}＊＊＊＊＊＊＊＊＊＊＊＊＊\n")
            
            # 全イベントを時系列でソート
            events = sorted(daily_events[date_str], key=lambda x: x['start'])
            if not events: continue
            
            # セッション統合
            sessions = []
            curr = events[0]
            for i in range(1, len(events)):
                next_e = events[i]
                
                is_same = (next_e['label'] == curr['label'])
                # 同じ作業なら2時間以内、違う作業でも30分以内なら統合
                gap = (next_e['start'] - curr['end']).total_seconds()
                
                if (is_same and gap < 7200) or (gap < 1800):
                    curr['end'] = max(curr['end'], next_e['end'])
                    # ラベルの長い方（具体的な方）を優先
                    if not is_same and len(next_e['label']) > len(curr['label']):
                        curr['label'] = next_e['label']
                else:
                    sessions.append(curr)
                    curr = next_e
            sessions.append(curr)
            
            # 重複ラベルの連続を排除して出力
            last_label = ""
            for s in sessions:
                if s['label'] == last_label: continue
                
                # 最低15分枠にする
                if (s['end'] - s['start']).total_seconds() < 900:
                    s['end'] = s['start'] + timedelta(minutes=15)
                
                s_t = s['start'].strftime('%H：%M')
                e_t = s['end'].strftime('%H：%M')
                f.write(f"{s_t}　{e_t}　{s['label']}\n")
                last_label = s['label']

    print(f"Development report created at: {output_file}")

if __name__ == "__main__":
    format_development_report()
