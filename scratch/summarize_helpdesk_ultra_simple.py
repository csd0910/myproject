import csv
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

# 完全に除外する具体的でないキーワード（部分一致でも除外）
STRICT_EXCLUDE_WORDS = [
    'ログイン', '設定', 'エラー', 'プロパティ', '通知', '検索結果', 
    '属性の詳細', '閲覧', 'お知らせ', 'プロパティの確認', 'Windows ツール', 
    'クイック設定', '正常性ダッシュボード', 'パスワード', 'ネットワーク', 
    '詳細設定', '詳細設定の確認', 'パスワードを保存しますか', 'ユーザーの詳細パネル',
    '開いているファイル', 'ネットワーク接続の復元', '印刷中', '記録エラー', '出力エラー',
    '起動しています', 'サービスの利用ユーザーの設定', '組織とユーザーの設定', 'アカウント設定',
    'Google アカウント', 'Microsoft 365 管理センター', '資格情報マネージャー',
    'アクセシビリティ設定アシスタント', 'コピー', '新規 テキスト ドキュメント', 'ジャンプ リスト',
    'Windows セキュリティ'
]

def is_meaningful_task(content):
    # 余計な修飾を削除
    core = content
    core = re.sub(r' に関するトラブル対応・設定$', '', core)
    core = re.sub(r' および他 \d+ ページ$', '', core)
    core = re.sub(r'^閲覧: ', '', core)
    core = re.sub(r' - (Microsoft Edge|Google Chrome|My profile .*?)$', '', core)
    core = core.strip()
    
    # 除外リストに含まれる言葉が核心部分に含まれる場合はスキップ
    for ex in STRICT_EXCLUDE_WORDS:
        if ex in core:
            return False
            
    if len(core) <= 4: # 「192.」などは通すが、あまりに短いのはスキップ
        if not re.match(r'^\d+\.', core):
            return False
    
    return True

def clean_label(content):
    res = content
    res = re.sub(r' に関するトラブル対応・設定$', '', res)
    res = re.sub(r' および他 \d+ ページ$', '', res)
    res = re.sub(r'^閲覧: ', '', res)
    res = re.sub(r' - (Microsoft Edge|Google Chrome|My profile .*?|Comet|サクラエディタ.*?|Excel|Word|Google Gemini|Claude)$', '', res)
    res = re.sub(r' のジャンプ リスト$', '', res)
    
    # 特徴的なサービス名を整える
    if 'サイボウズ' in res:
        res = f"サイボウズ：{res.replace('サイボウズ：', '').split(' - ')[0]}"
    elif 'メール' in res:
        res = f"メール：{res.replace('メール：', '').split(' - ')[0]}"
    
    return res.strip()

def format_helpdesk_ultra_simple():
    input_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\ActivityLog_0410_0512.csv"
    output_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\Helpdesk_Report_Final_v4.txt"
    
    if not os.path.exists(input_file):
        return

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
                display_name = clean_label(clean_c)
                temp_data[(date_str, display_name)].append(dt)

    for (date_str, content), dts in temp_data.items():
        dts.sort()
        b_start = dts[0]
        b_prev = dts[0]
        for i in range(1, len(dts)):
            if (dts[i] - b_prev).total_seconds() > 1800: # 30分間隔
                daily_blocks[date_str].append({'start': b_start, 'end': b_prev + timedelta(minutes=5), 'content': content})
                b_start = dts[i]
            b_prev = dts[i]
        daily_blocks[date_str].append({'start': b_start, 'end': b_prev + timedelta(minutes=5), 'content': content})

    with open(output_file, 'w', encoding='utf-8-sig') as f:
        for date_str in sorted(daily_blocks.keys()):
            m_d = date_str.split('/')
            f.write(f"\n{int(m_d[1])}/{int(m_d[2])}＊＊＊＊＊＊＊＊＊＊＊＊＊\n")
            
            sorted_blocks = sorted(daily_blocks[date_str], key=lambda x: x['start'])
            
            for block in sorted_blocks:
                s_t = block['start'].strftime('%H：%M')
                e_t = block['end'].strftime('%H：%M')
                # ユーザーの例示: 9：00　10：00　内容
                f.write(f"{s_t}　{e_t}　{block['content']}\n")

    print(f"Ultra simple report created at: {output_file}")

if __name__ == "__main__":
    format_helpdesk_ultra_simple()
