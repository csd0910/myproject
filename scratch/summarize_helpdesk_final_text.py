import csv
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

# 具体的でないキーワード（これら単体の場合は除外）
VAGUE_KEYWORDS = [
    'エラー', 'ログイン', '設定', 'プロパティ', 'Windows セキュリティ', '通知', 
    '検索結果', '属性の詳細', '閲覧', '起動しています', 'お知らせ', 'プロパティの確認',
    'Windows ツール', 'クイック設定', '正常性ダッシュボード', 'パスワードの入力',
    'ネットワーク', '作成完了', '保存エラー', 'インポート'
]

def is_vague(content):
    # 「～ に関するトラブル対応・設定」を削除して純粋な内容を確認
    core = re.sub(r' に関するトラブル対応・設定$', '', content)
    core = re.sub(r'^閲覧: ', '', core)
    core = re.sub(r'^サイボウズ（(.*?)）の調査・対応$', r'\1', core)
    core = re.sub(r'^メール（(.*?)）でのトラブル対応$', r'\1', core)
    
    # 短すぎる、または具体的でない単語のみの場合は除外
    if len(core) <= 4 and core in VAGUE_KEYWORDS:
        return True
    if core in VAGUE_KEYWORDS:
        return True
    return False

def format_helpdesk_report():
    input_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\ActivityLog_0410_0512.csv"
    output_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\Helpdesk_Report_Formatted.txt"
    
    if not os.path.exists(input_file):
        return

    # 日付 -> [(開始, 終了, 内容)]
    daily_data = defaultdict(list)

    # 1. ログの読み込みとフィルタリング
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < 3: continue
            date_str, time_str, content = row
            
            # クリーンアップ
            clean_content = re.sub(r'\[.*?\]\s*', '', content).strip()
            clean_content = re.sub(r' - (Microsoft Edge|Google Chrome|My profile .*?)$', '', clean_content).strip()
            
            # ヘルプデスク系キーワード（前回のスクリプトの基準）
            from extract_helpdesk_tasks import is_helpdesk_task, HELPDESK_KEYWORDS
            
            if is_helpdesk_task(clean_content):
                # 具体的でないものを除外
                if is_vague(clean_content):
                    continue
                
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")
                
                # 作業内容の整形
                if 'サイボウズ' in clean_content:
                    display_name = f"サイボウズ：{clean_content.split(' - ')[0]}"
                elif 'メール' in clean_content:
                    display_name = f"メール：{clean_content.split(' - ')[0]}"
                else:
                    display_name = clean_content.split(' - ')[0]
                
                # 同日の同じ作業をグループ化するために一時保存
                daily_data[date_str].append({'dt': dt, 'content': display_name})

    # 2. テキスト生成
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        for date_str in sorted(daily_data.keys()):
            # 日付ヘッダー
            formatted_date = date_str.replace('2026/', '') # 4/10 形式
            f.write(f"\n{formatted_date} ＊＊＊＊＊＊＊＊＊＊＊＊＊\n")
            
            # 作業内容ごとに時間をまとめる
            events = daily_data[date_str]
            # 内容ごとに時間を集計
            activity_times = defaultdict(list)
            for ev in events:
                activity_times[ev['content']].append(ev['dt'])
            
            # 時系列順に出力したいので、各作業の「最初の時間」でソート
            sorted_activities = sorted(activity_times.items(), key=lambda x: min(x[1]))
            
            for content, dts in sorted_activities:
                dts.sort()
                # 連続する時間を統合
                blocks = []
                b_start = dts[0]
                b_prev = dts[0]
                for i in range(1, len(dts)):
                    if (dts[i] - b_prev).total_seconds() > 1800: # 30分空いたら別作業
                        blocks.append((b_start, b_prev))
                        b_start = dts[i]
                    b_prev = dts[i]
                blocks.append((b_start, b_prev))
                
                for start, end in blocks:
                    # 終了時間が同じなら+5分
                    if start == end:
                        end = start + timedelta(minutes=5)
                    
                    time_str = f"{start.strftime('%H:%M')} {end.strftime('%H:%M')}"
                    # 特徴的な言葉だけを抽出してシンプルに
                    simple_content = content.replace(' に関するトラブル対応・設定', '')
                    f.write(f"{time_str}　{simple_content}\n")

    print(f"Formatted report created at: {output_file}")

if __name__ == "__main__":
    format_helpdesk_report()
