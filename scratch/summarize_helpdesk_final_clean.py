import csv
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

# 完全に除外する具体的でないキーワード
STRICT_EXCLUDE_WORDS = [
    'ログイン', 'エラー', 'プロパティ', '通知', '検索結果', 
    'パスワードを保存', 'ユーザーの詳細', '開いているファイル', '印刷', 
    '起動しています', 'サービスの利用', 'アカウント設定', 'Google アカウント',
    '資格情報', 'アクセシビリティ', 'コピー', '新規 テキスト', 'ジャンプ リスト',
    'Windows セキュリティ', 'ごみ箱', '新しいフォルダー', 'エクスプローラー',
    'システムのプロパティ', 'プログラムと機能', '正常性ダッシュボード', 'クイック設定',
    '詳細設定の確認', 'ネットワーク接続の復元', 'セルの書式設定'
]

VAGUE_WORDS = ['設定', '詳細設定', 'ネットワーク', '詳細', '更新']

def clean_label_ultimate_v3(content):
    res = content
    # 1. 不要な記号や状態表示の削除
    res = re.sub(r' \(応答なし\)$', '', res)
    res = re.sub(r' とその他 \d+ 個のタブ.*$', '', res)
    res = re.sub(r' および他 \d+ ページ.*$', '', res)
    res = re.sub(r' に関するトラブル対応・設定$', '', res)
    res = re.sub(r'^閲覧: ', '', res)
    res = re.sub(r'^@ウェブ \(', '', res)
    
    # 2. 長いURLの処理
    if 'http' in res or 'bing.com' in res or 'google.com' in res:
        if 'admin.microsoft' in res or 'admin.cloud' in res:
            return 'Microsoft 365 管理センター'
        if 'amazon.co.jp' in res.lower():
            return 'Amazonでの周辺機器・PC選定'
        # それ以外の長いURLは「ウェブサイトでの調査」に統合
        return '関連サイト・ウェブ資料での調査'

    # 3. ツール名の徹底削除
    res = re.sub(r' - (Microsoft Edge|Google Chrome|My profile .*?|Comet|サクラエディタ.*?|Excel|Word|Google Gemini|Claude|Thunderbird|Adobe Acrobat Reader.*?|メモ帳|エクスプローラー)$', '', res)
    res = re.sub(r' - Google (検索|Gemini)$', '', res)
    
    # 4. 特定サービスの名称統一
    if 'freee' in res: return 'freee人事労務（勤怠・申請）'
    if 'リモート デスクトップ' in res: return 'リモート デスクトップ接続'
    if 'BitLocker' in res or 'bitlocker' in res.lower(): return 'BitLocker回復キー関連の調査・対応'
    if '脆弱性' in res or 'セキュリティ更新' in res: return 'セキュリティ脆弱性・アップデート情報の確認'
    if '見積' in res or '稟議' in res or 'ディスプレイ' in res: return 'PC・周辺機器の購入稟議・見積依頼'
    if '残業調査' in res or 'サービス残業' in res: return '社員の残業状況・ログ調査および報告書作成'

    # 5. 具体性のない単語のみの場合は除外
    res_clean = res.strip()
    if res_clean in VAGUE_WORDS or len(res_clean) <= 2:
        return ""
        
    # 6. メールの宛先情報などをカット
    res = re.sub(r' - [a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,} - .*$', '', res)
    res = res.replace('（保護ビュー）', '').replace(' - 互換モード', '').replace(' - 保護ビュー', '')
    
    # 7. ファイルパスや拡張子のクリーンアップ
    if '.' in res and not res.startswith('http'):
        res = os.path.splitext(res)[0]
    if '\\' in res:
        res = res.split('\\')[-1]

    return res.strip()

def format_helpdesk_final_clean():
    input_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\ActivityLog_0410_0512.csv"
    output_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\Helpdesk_Report_Final_v5.txt"
    
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
                label = clean_label_ultimate_v3(clean_c)
                if not label or any(w in label for w in STRICT_EXCLUDE_WORDS): continue
                
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")
                daily_events[date_str].append({'time': dt, 'label': label})

    with open(output_file, 'w', encoding='utf-8-sig') as f:
        for date_str in sorted(daily_events.keys()):
            m_d = date_str.split('/')
            f.write(f"\n{int(m_d[1])}/{int(m_d[2])}＊＊＊＊＊＊＊＊＊＊＊＊＊\n")
            
            events = sorted(daily_events[date_str], key=lambda x: x['time'])
            if not events: continue
            
            sessions = []
            if events:
                curr = {'start': events[0]['time'], 'end': events[0]['time'], 'label': events[0]['label']}
                for i in range(1, len(events)):
                    e = events[i]
                    is_same = (e['label'] == curr['label'])
                    time_gap = (e['time'] - curr['end']).total_seconds()
                    
                    # 同一業務なら1時間以内、別業務なら25分以内なら統合
                    if (is_same and time_gap < 3600) or (time_gap < 1500):
                        curr['end'] = e['time']
                        if not is_same and len(e['label']) > len(curr['label']):
                            curr['label'] = e['label']
                    else:
                        sessions.append(curr)
                        curr = {'start': e['time'], 'end': e['time'], 'label': e['label']}
                sessions.append(curr)
            
            last_out = ""
            for s in sessions:
                end_time = s['end'] + timedelta(minutes=15)
                # ユーザーの例示: 9：00　10：00　＊＊＊（内容）
                s_t_str = s['start'].strftime('%H：%M')
                e_t_str = end_time.strftime('%H：%M')
                out_line = f"{s_t_str}　{e_t_str}　{s['label']}"
                
                if out_line != last_out:
                    f.write(out_line + "\n")
                    last_out = out_line

    print(f"Final clean report created at: {output_file}")

if __name__ == "__main__":
    format_helpdesk_final_clean()
