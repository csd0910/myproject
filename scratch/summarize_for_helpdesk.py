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
    'Working...', '項目の削除', '複数ファイルの削除'
]

def get_verbed_content(content, topic_map, date):
    text = re.sub(r'\[.*?\]\s*', '', content).strip()
    # 基本クリーンアップ
    for p in ['閲覧: ', '利用: ', 'ファイル更新: ', '件名: ']:
        text = text.replace(p, '')
    
    if any(k.lower() in text.lower() for k in EXCLUDE_KEYWORDS) or len(text) < 4:
        return None, None

    # カテゴリ判定
    cat = "一般"
    verbed = text
    
    if '[AI相談]' in content or 'Antigravity' in text:
        topics = topic_map.get(date, ["システム開発・改善"])
        verbed = f"Antigravityを用いた「{topics[0]}」の開発・相談"
        cat = "開発"
    elif 'Gitコミット:' in text or '[開発]' in content:
        verbed = f"プログラム（{text.replace('Gitコミット:', '').strip()}）の開発・修正"
        cat = "開発"
    elif any(ext in text.lower() for ext in ['.xlsx', '.xlsm', '.csv']):
        filename = text.split('\\')[-1].split(' - ')[0]
        verbed = f"Excelファイル（{filename}）の入力・編集"
        cat = "事務"
    elif any(ext in text.lower() for ext in ['.pdf']):
        filename = text.split('\\')[-1].split(' - ')[0]
        verbed = f"PDF資料（{filename}）の確認"
        cat = "事務"
    elif 'サイボウズ' in text.lower() or 'cybozu' in text.lower():
        title = re.sub(r' - (Microsoft Edge|Google Chrome|My profile .*?)$', '', text).strip()
        verbed = f"サイボウズ（{title}）での情報確認・処理"
        cat = "サイボウズ"
    elif any(k in text.lower() for k in ['thunderbird', 'outlook', 'メール']):
        verbed = f"メール（{text.split(' - ')[0]}）の閲覧・作成"
        cat = "メール"
    else:
        # Web調査全般
        clean_title = re.sub(r' - (Microsoft Edge|Google Chrome|My profile .*?)$', '', text).strip()
        if len(clean_title) > 5:
            verbed = f"Webサイト（{clean_title}）の閲覧・調査"
            cat = "調査"

    return verbed, cat

def summarize_for_helpdesk():
    input_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\ActivityLog_0410_0512.csv"
    output_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\ActivitySummary_Helpdesk.csv"
    
    topic_map = {}
    try:
        import subprocess
        result = subprocess.check_output(['python', 'scratch/get_brain_topics.py'], encoding='utf-8')
        topic_map = json.loads(result)
    except: pass

    if not os.path.exists(input_file): return

    events = []
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < 3: continue
            date, time, content = row
            dt_obj = datetime.strptime(f"{date} {time}", "%Y/%m/%d %H:%M:%S")
            verbed, cat = get_verbed_content(content, topic_map, date)
            if verbed:
                events.append({'dt': dt_obj, 'verbed': verbed, 'cat': cat})

    if not events: return

    # セッション化 (30分以内の連続した動きをまとめる)
    sessions = []
    if events:
        current_session = {
            'start': events[0]['dt'],
            'end': events[0]['dt'],
            'cat': events[0]['cat'],
            'details': {events[0]['verbed']}
        }
        
        for i in range(1, len(events)):
            ev = events[i]
            # 30分以内かつ同じカテゴリなら継続、そうでなければ新規
            time_gap = ev['dt'] - current_session['end']
            if time_gap < timedelta(minutes=30) and (ev['cat'] == current_session['cat'] or current_session['cat'] == "一般"):
                current_session['end'] = ev['dt']
                current_session['details'].add(ev['verbed'])
                if current_session['cat'] == "一般": current_session['cat'] = ev['cat']
            else:
                sessions.append(current_session)
                current_session = {
                    'start': ev['dt'],
                    'end': ev['dt'],
                    'cat': ev['cat'],
                    'details': {ev['verbed']}
                }
        sessions.append(current_session)

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['発生日時', '終了日時', '実作業時間', '主な作業内容'])
        
        for s in sessions:
            duration = s['end'] - s['start']
            # 最低5分として表示（瞬時の操作も多いため）
            display_duration = max(duration, timedelta(minutes=5))
            
            # 時間を "0:15" 形式に
            hours, remainder = divmod(display_duration.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            duration_str = f"{hours}:{minutes:02d}"
            
            # 内容を統合（重複を除いて箇条書き）
            detail_text = " / ".join(sorted(list(s['details'])))
            if len(detail_text) > 200: detail_text = detail_text[:197] + "..."
            
            writer.writerow([
                s['start'].strftime('%Y/%m/%d %H:%M'),
                s['end'].strftime('%Y/%m/%d %H:%M'),
                duration_str,
                detail_text
            ])

if __name__ == "__main__":
    summarize_for_helpdesk()
