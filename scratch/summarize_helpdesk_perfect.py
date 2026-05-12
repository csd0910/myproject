import csv
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

# 除外キーワード
STRICT_EXCLUDE_WORDS = [
    'ログイン', '設定', 'エラー', 'プロパティ', '通知', '検索結果', 
    '属性の詳細', '閲覧', 'お知らせ', 'Windows ツール', 'クイック設定', 
    '正常性ダッシュボード', 'パスワード', 'ネットワーク', '詳細設定', 
    'パスワードを保存', 'ユーザーの詳細', '開いているファイル', '印刷', 
    '記録エラー', '出力エラー', '起動しています', 'サービスの利用', 
    '組織とユーザー', 'アカウント設定', 'Google アカウント', '管理センター', 
    '資格情報', 'アクセシビリティ', 'コピー', '新規 テキスト', 'ジャンプ リスト',
    'Windows セキュリティ', 'ごみ箱', '新しいフォルダー', 'エクスプローラー',
    'システムのプロパティ', 'プログラムと機能', '勤務時間修正申請' # 事務処理は基本除外か統合
]

def clean_label_perfect(content):
    res = content
    # 共通ノイズ削除
    res = re.sub(r' に関するトラブル対応・設定$', '', res)
    res = re.sub(r' および他 \d+ ページ$', '', res)
    res = re.sub(r'^閲覧: ', '', res)
    res = re.sub(r' のプロパティ$', '', res)
    res = re.sub(r' - (Microsoft Edge|Google Chrome|My profile .*?|Comet|サクラエディタ.*?|Excel|Word|Google Gemini|Claude|Thunderbird|Adobe Acrobat Reader.*?|メモ帳|エクスプローラー)$', '', res)
    
    # メールの宛先情報などをカット
    res = re.sub(r' - [a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,} - .*$', '', res)
    res = re.sub(r' \| freee人事労務$', '', res)
    res = res.replace('（保護ビュー）', '').replace(' - 互換モード', '').replace(' - 保護ビュー', '')
    
    # 作業内容の純粋化
    if 'リモート デスクトップ接続' in res: return 'リモート デスクトップ接続'
    if 'Chrome リモート デスクトップ' in res: return 'リモート デスクトップ（Chrome）'
    
    # 語尾の「を作成」などを整理
    res = res.replace('を作成', '').replace('の調査と修正', '').replace('対処', '')
    
    # ファイル名から拡張子を削除してシンプルに
    if '.' in res and not res.startswith('http'):
        res = os.path.splitext(res)[0]
    
    # パス名の最後だけ取得
    if '\\' in res:
        res = res.split('\\')[-1]

    return res.strip()

def format_helpdesk_ultimate_v2():
    input_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\ActivityLog_0410_0512.csv"
    output_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\Helpdesk_Report_Perfect.txt"
    
    if not os.path.exists(input_file): return

    daily_events = defaultdict(list)

    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < 3: continue
            date_str, time_str, content = row
            clean_c = re.sub(r'\[.*?\]\s*', '', content).strip()
            
            from extract_helpdesk_tasks import is_helpdesk_task
            if is_helpdesk_task(clean_c):
                # 特定のキーワードが含まれるか、具体的である場合のみ
                label = clean_label_perfect(clean_c)
                if not label or any(w in label for w in ['ログイン', '設定', 'エラー', '通知']): continue
                
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")
                daily_events[date_str].append({'time': dt, 'label': label})

    with open(output_file, 'w', encoding='utf-8-sig') as f:
        for date_str in sorted(daily_events.keys()):
            m_d = date_str.split('/')
            f.write(f"\n{int(m_d[1])}/{int(m_d[2])}＊＊＊＊＊＊＊＊＊＊＊＊＊\n")
            
            events = sorted(daily_events[date_str], key=lambda x: x['time'])
            if not events: continue
            
            # 同じ内容を統合
            merged = []
            if events:
                curr = {'start': events[0]['time'], 'end': events[0]['time'], 'label': events[0]['label']}
                for i in range(1, len(events)):
                    e = events[i]
                    # 同じ内容で、かつ1時間以内の間隔なら統合
                    if e['label'] == curr['label'] and (e['time'] - curr['end']).total_seconds() < 3600:
                        curr['end'] = e['time']
                    else:
                        merged.append(curr)
                        curr = {'start': e['time'], 'end': e['time'], 'label': e['label']}
                merged.append(curr)
            
            # 出力
            for m in merged:
                # 5分未満の単発ログは少し幅を持たせる
                if (m['end'] - m['start']).total_seconds() < 300:
                    m['end'] = m['start'] + timedelta(minutes=15)
                
                s_t = m['start'].strftime('%H：%M')
                e_t = m['end'].strftime('%H：%M')
                f.write(f"{s_t}　{e_t}　{m['label']}\n")

    print(f"Perfect report created at: {output_file}")

if __name__ == "__main__":
    format_helpdesk_ultimate_v2()
