import csv
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

# 開発関連のキーワード
DEV_KEYWORDS = [
    'Antigravity', 'プログラム', 'スクリプト', 'Python', 'Git', 'コミット',
    'GitHub', 'VS Code', 'Visual Studio', 'コード', 'バッチ', 'PowerShell',
    'Qiita', 'Zenn', 'Stack Overflow', 'API', 'ビルド', 'デバッグ', 'リファクタリング',
    'feat:', 'fix:', 'chore:', 'refactor:', 'docs:', 'style:', 'test:', 'ci:', 'perf:'
]

# AI相談ログから取得したトピックのマッピング（以前のロジックを活用）
# 実際には get_brain_topics.py の結果を使うのが理想的ですが、
# ここでは簡易的に「システム開発・改善」として抽出し、詳細があればそれを優先します。

def is_dev_task(content):
    return any(k.lower() in content.lower() for k in DEV_KEYWORDS)

def extract_development():
    input_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\ActivityLog_0410_0512.csv"
    output_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\Development_Activity_Log.csv"
    
    if not os.path.exists(input_file):
        print("Input file not found.")
        return

    # day -> activity -> list of times
    daily_dev = defaultdict(lambda: defaultdict(list))

    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < 3: continue
            date, time, content = row
            
            # クリーンアップ
            clean_content = re.sub(r'\[.*?\]\s*', '', content).strip()
            
            if is_dev_task(clean_content):
                # 表示名の整形
                if 'Antigravity' in clean_content:
                    # Antigravityの場合はなるべく詳細な相談内容を抽出（実際の実装ではbrain_topicsを使う）
                    display_name = clean_content
                elif 'Git' in clean_content or 'feat:' in clean_content or 'fix:' in clean_content:
                    display_name = f"プログラム（{clean_content}）の実装・修正"
                elif '.py' in clean_content or '.bat' in clean_content:
                    display_name = f"プログラム（{clean_content.split(' ')[0]}）の開発"
                else:
                    display_name = clean_content
                
                dt = datetime.strptime(f"{date} {time}", "%Y/%m/%d %H:%M:%S")
                daily_dev[date][display_name].append(dt)

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['日付', '作業時間帯', '合計時間', '開発プロジェクト・作業内容'])
        
        for date in sorted(daily_dev.keys()):
            for activity, dts in daily_dev[date].items():
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

    print(f"Development log created at: {output_file}")

if __name__ == "__main__":
    extract_development()
