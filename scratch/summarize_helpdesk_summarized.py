import csv
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

# 除外キーワード
STRICT_EXCLUDE_WORDS = [
    'ログイン', 'エラー', 'プロパティ', '通知', '検索結果', 
    'パスワードを保存', 'ユーザーの詳細', '開いているファイル', '印刷', 
    '起動しています', 'サービスの利用', 'アカウント設定', 'Google アカウント',
    '資格情報', 'アクセシビリティ', 'コピー', '新規 テキスト', 'ジャンプ リスト',
    'Windows セキュリティ', 'ごみ箱', '新しいフォルダー', 'エクスプローラー',
    'システムのプロパティ', 'プログラムと機能', '正常性ダッシュボード'
]

def clean_label_final(content):
    res = content
    # ノイズ削除
    res = re.sub(r' に関するトラブル対応・設定$', '', res)
    res = re.sub(r' および他 \d+ ページ.*$', '', res)
    res = re.sub(r'^閲覧: ', '', res)
    res = re.sub(r' - (Microsoft Edge|Google Chrome|My profile .*?|Comet|サクラエディタ.*?|Excel|Word|Google Gemini|Claude|Thunderbird|Adobe Acrobat Reader.*?|メモ帳|エクスプローラー)$', '', res)
    res = re.sub(r' - Google (検索|Gemini)$', '', res)
    
    # URLの簡略化 (admin.microsoft.com/... -> Microsoft 365 管理センター)
    if 'admin.microsoft.com' in res or 'admin.cloud.microsoft' in res:
        return 'Microsoft 365 管理センター'
    if 'amazon.co.jp' in res.lower():
        return 'Amazonでの周辺機器・PC選定'
    if 'freee' in res:
        return 'freee人事労務（勤怠・申請）'
    
    # メールの宛先情報などをカット
    res = re.sub(r' - [a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,} - .*$', '', res)
    res = res.replace('（保護ビュー）', '').replace(' - 互換モード', '').replace(' - 保護ビュー', '')
    
    if 'リモート デスクトップ' in res: return 'リモート デスクトップ接続'
    if 'BitLocker' in res or 'bitlocker' in res.lower(): return 'BitLocker回復キー関連の調査・対応'
    if '脆弱性' in res or 'セキュリティ更新' in res: return 'セキュリティ脆弱性・アップデート情報の確認'
    if '見積' in res or '稟議' in res or 'ディスプレイ' in res: return 'PC・周辺機器の購入稟議・見積依頼'

    # ファイル名から拡張子を削除してシンプルに
    if '.' in res and not res.startswith('http'):
        res = os.path.splitext(res)[0]
    
    # パス名の最後だけ取得
    if '\\' in res:
        res = res.split('\\')[-1]

    return res.strip()

def format_helpdesk_summarized():
    input_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\ActivityLog_0410_0512.csv"
    output_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\Helpdesk_Report_Summary_v1.txt"
    
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
                label = clean_label_final(clean_c)
                if not label or any(w in label for w in STRICT_EXCLUDE_WORDS): continue
                
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")
                daily_events[date_str].append({'time': dt, 'label': label})

    with open(output_file, 'w', encoding='utf-8-sig') as f:
        for date_str in sorted(daily_events.keys()):
            m_d = date_str.split('/')
            f.write(f"\n{int(m_d[1])}/{int(m_d[2])}＊＊＊＊＊＊＊＊＊＊＊＊＊\n")
            
            events = sorted(daily_events[date_str], key=lambda x: x['time'])
            if not events: continue
            
            # 非常に近い時間、または同じ内容のセッションを統合
            sessions = []
            if events:
                curr = {'start': events[0]['time'], 'end': events[0]['time'], 'label': events[0]['label']}
                for i in range(1, len(events)):
                    e = events[i]
                    # 同じ内容なら1時間空いても統合、違う内容でも20分以内なら「一連の作業」として検討
                    is_same = (e['label'] == curr['label'])
                    time_gap = (e['time'] - curr['end']).total_seconds()
                    
                    if (is_same and time_gap < 3600) or (time_gap < 1200):
                        curr['end'] = e['time']
                        # 違うラベルでも近い時間なら、より具体的なラベルを採用する（単純化のため上書きせず保持）
                        if not is_same and len(e['label']) > len(curr['label']):
                            curr['label'] = e['label']
                    else:
                        sessions.append(curr)
                        curr = {'start': e['time'], 'end': e['time'], 'label': e['label']}
                sessions.append(curr)
            
            # 重複を除去して出力
            last_out = ""
            for s in sessions:
                # 終了時間にバッファを持たせる
                end_time = s['end'] + timedelta(minutes=10)
                if (end_time - s['start']).total_seconds() < 900: # 最低15分
                    end_time = s['start'] + timedelta(minutes=15)
                
                # 1つ前のセッションと時間が被る場合は調整
                s_t_str = s['start'].strftime('%H：%M')
                e_t_str = end_time.strftime('%H：%M')
                out_line = f"{s_t_str}　{e_t_str}　{s['label']}"
                
                if out_line != last_out:
                    f.write(out_line + "\n")
                    last_out = out_line

    print(f"Summarized report created at: {output_file}")

if __name__ == "__main__":
    format_helpdesk_summarized()
