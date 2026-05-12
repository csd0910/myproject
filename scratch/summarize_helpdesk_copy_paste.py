import csv
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

# 除外キーワード（これらが含まれる行は報告書に載せない）
STRICT_EXCLUDE_WORDS = [
    'ログイン', '設定', 'エラー', 'プロパティ', '通知', '検索結果', 
    '属性の詳細', '閲覧', 'お知らせ', 'Windows ツール', 'クイック設定', 
    '正常性ダッシュボード', 'パスワード', 'ネットワーク', '詳細設定', 
    'パスワードを保存', 'ユーザーの詳細', '開いているファイル', '印刷', 
    '記録エラー', '出力エラー', '起動しています', 'サービスの利用', 
    '組織とユーザー', 'アカウント設定', 'Google アカウント', '管理センター', 
    '資格情報', 'アクセシビリティ', 'コピー', '新規 テキスト', 'ジャンプ リスト',
    'Windows セキュリティ', 'ごみ箱', '新しいフォルダー', 'エクスプローラー',
    'システムのプロパティ', 'プログラムと機能'
]

def is_meaningful_task(content):
    core = re.sub(r'\[.*?\]\s*', '', content).strip()
    # 除外ワードチェック
    for ex in STRICT_EXCLUDE_WORDS:
        if ex in core:
            return False
    # 短すぎるのもノイズ
    if len(core) <= 3 and not re.match(r'^\d+\.', core):
        return False
    return True

def clean_label_ultimate(content):
    res = content
    # 共通のノイズを削除
    res = re.sub(r' に関するトラブル対応・設定$', '', res)
    res = re.sub(r' および他 \d+ ページ$', '', res)
    res = re.sub(r'^閲覧: ', '', res)
    res = re.sub(r' のプロパティ$', '', res)
    
    # ツール名の削除 (ブラウザ、エディタ、AIなど)
    res = re.sub(r' - (Microsoft Edge|Google Chrome|My profile .*?|Comet|サクラエディタ.*?|Excel|Word|Google Gemini|Claude|Thunderbird|Adobe Acrobat Reader.*?|メモ帳)$', '', res)
    
    # リモート接続系の統一
    if 'リモート デスクトップ接続' in res:
        res = 'リモート デスクトップ接続'
    
    # パス名の簡略化
    if '\\\\' in res or ':\\' in res:
        res = res.split('\\')[-1]
    
    # サービス名の整形
    res = res.replace('サイボウズ：', '').replace('メール：', '')
    if 'freee' in res:
        res = res.split(' | ')[0].split(' - ')[0]
    
    return res.strip()

def format_helpdesk_copy_paste():
    input_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\ActivityLog_0410_0512.csv"
    output_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\Helpdesk_Report_Simple_Final.txt"
    
    if not os.path.exists(input_file): return

    daily_blocks = defaultdict(list)
    temp_data = defaultdict(list)

    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < 3: continue
            date_str, time_str, content = row
            clean_c = re.sub(r'\[.*?\]\s*', '', content).strip()
            
            from extract_helpdesk_tasks import is_helpdesk_task
            if is_helpdesk_task(clean_c) and is_meaningful_task(clean_c):
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")
                display_name = clean_label_ultimate(clean_c)
                if not display_name: continue
                temp_data[(date_str, display_name)].append(dt)

    for (date_str, content), dts in temp_data.items():
        dts.sort()
        b_start = dts[0]
        b_prev = dts[0]
        for i in range(1, len(dts)):
            if (dts[i] - b_prev).total_seconds() > 2700: # 45分以上の空きで別作業
                daily_blocks[date_str].append({'start': b_start, 'end': b_prev + timedelta(minutes=10), 'content': content})
                b_start = dts[i]
            b_prev = dts[i]
        daily_blocks[date_str].append({'start': b_start, 'end': b_prev + timedelta(minutes=10), 'content': content})

    with open(output_file, 'w', encoding='utf-8-sig') as f:
        for date_str in sorted(daily_blocks.keys()):
            m_d = date_str.split('/')
            f.write(f"\n{int(m_d[1])}/{int(m_d[2])}＊＊＊＊＊＊＊＊＊＊＊＊＊\n")
            
            # 開始時間順に並べて出力
            sorted_blocks = sorted(daily_blocks[date_str], key=lambda x: x['start'])
            
            # 直前と同じ内容はスキップ（あるいは時間を統合）
            last_content = ""
            for block in sorted_blocks:
                if block['content'] == last_content: continue
                
                s_t = block['start'].strftime('%H：%M')
                e_t = block['end'].strftime('%H：%M')
                f.write(f"{s_t}　{e_t}　{block['content']}\n")
                last_content = block['content']

    print(f"Simple final report created at: {output_file}")

if __name__ == "__main__":
    format_helpdesk_copy_paste()
