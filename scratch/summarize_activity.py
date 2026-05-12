import csv
import os
import re
import json
from collections import defaultdict

# 除外キーワード（究極のノイズフィルター）
EXCLUDE_KEYWORDS = [
    '付箋', 'Program Manager', 'Quick Settings', 'クイック設定', 
    'Snipping Tool', 'Windows セキュリティ', 'サインイン', 
    'Microsoft account', 'ようこそ', 'パスキー', 'コントロール パネル',
    '設定', 'Default.rdp', '新しいタブ', 'New Tab', '無題', 'Untitled',
    '新しい通知', 'スナップ アシスト', 'タスク マネージャー', 'フォルダーの選択',
    '名前を付けて保存', '項目の検出', 'リサイクルされました', 'スナップショット',
    'ログイン', 'Login', 'Bing', 'Google', 'data:', 'パスワードを保存',
    'ロック画面', 'エクスプローラー', 'デスクトップ', '検索', '新しい Microsoft Word 文書',
    'Antigravity対話ログの更新', '正常性ダッシュボード',
    'および他', 'My profile', 'Microsoft? Edge', 'Google Chrome',
    '複数ファイルの削除', '項目の削除', 'ファイルのコピー', '移動中',
    'ごみ箱', 'ゴミ箱', 'Trash', '空にする', '迷惑メール', 'アーカイブ', 'フォルダーの削除',
    '読み込み中', 'ホーム', 'Terminal', 'cmd.exe', 'コマンド プロンプト', 
    'freee人事労務', 'ESET', 'ecmd.exe', 'システム トレイ', 'オーバーフロー ウィンドウ',
    'ファイルが更新されました', '項目が見つかりません', '翻訳しています', '使用中のファイル',
    '項目のプロパティ', 'ファイルを開く', '名前を変更', 'のジャンプ リスト', 'スナップショット',
    'Working...', '待機しています', '接続中', '読み込んでいます', 'Google アカウント'
]

def get_verbed_content(content, topic_map, date):
    text = re.sub(r'\[.*?\]\s*', '', content).strip()
    lower_text = text.lower()
    
    # 除外キーワードチェック（大文字小文字無視）
    if any(k.lower() in lower_text for k in EXCLUDE_KEYWORDS):
        return None
    
    # URLやパラメータが長いものは除外
    if 'http' in lower_text or 'bing.com/ck/' in lower_text or 'admin.cloud.microsoft' in lower_text:
        return None

    # 進捗表示を除外
    if re.search(r'\d+%\s*完了', text):
        return None

    # プレフィックスの除去
    for p in ['閲覧: ', '利用: ', 'ファイル更新: ', '件名: ']:
        text = text.replace(p, '')
    
    if not text or len(text) < 4: return None

    # AI相談（具体化）
    if '[AI相談]' in content or 'Antigravity' in text:
        topics = topic_map.get(date, ["システム開発・改善"])
        topic_str = topics[0] if topics else "システム開発・改善"
        # 意味のないファイル名の場合はデフォルトに
        if '.md' in topic_str or '.py' in topic_str:
            topic_str = "システム機能の開発・修正"
        return f"Antigravityを用いた「{topic_str}」の開発・相談"

    # 開発・Git
    if 'Gitコミット:' in text or '[開発]' in content:
        msg = text.replace('Gitコミット:', '').strip()
        return f"プログラム（{msg}）の開発および修正"

    # Excel / CSV / Word / PDF
    if any(ext in text.lower() for ext in ['.xlsx', '.xlsm', '.csv', '.docx', '.doc', '.pdf']):
        filename = text.split('\\')[-1].split(' - ')[0]
        if len(filename) < 5: return None
        if any(ext in filename.lower() for ext in ['.xls', '.csv']):
            return f"Excelファイル（{filename}）のデータ入力・編集"
        if '.doc' in filename.lower():
            return f"Word文書（{filename}）の資料作成・編集"
        if '.pdf' in filename.lower():
            return f"PDF資料（{filename}）の閲覧・内容確認"

    # Web閲覧
    web_keywords = ['サイボウズ office', 'yahoo', 'gemini', 'thunderbird', 'outlook', 'teams', 'notebooklm', 'amazon', 'qiita', 'github']
    if any(k in text.lower() for k in web_keywords) or '[ブラウザ' in content:
        clean_title = re.sub(r' - (Microsoft Edge|Google Chrome|Mozilla Thunderbird|My profile .*?)$', '', text)
        clean_title = clean_title.split(' および他 ')[0].strip()
        if not clean_title or len(clean_title) < 5 or clean_title.lower() in ['login', '新しいタブ', 'working...']: return None
        return f"Webサイト（{clean_title}）の閲覧・調査"

    # スクリプト
    if any(ext in text.lower() for ext in ['.py', '.bat', '.ps1', '.vba']):
        filename = text.split('\\')[-1]
        return f"スクリプト（{filename}）の開発・デバッグ"

    # その他
    if ' - ' in text and len(text) > 10:
        clean_name = text.split(' - ')[0]
        if len(clean_name) > 4:
            return f"「{clean_name}」の操作・実務"
    
    return None

def summarize_activity():
    input_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\ActivityLog_0410_0512.csv"
    output_file = r"C:\Users\フォーレスト026\MyProject\tools\Memo\ActivitySummary_0410_0512.csv"
    
    topic_map = {}
    try:
        import subprocess
        result = subprocess.check_output(['python', 'scratch/get_brain_topics.py'], encoding='utf-8')
        topic_map = json.loads(result)
    except: pass

    if not os.path.exists(input_file): return

    summary_data = defaultdict(lambda: defaultdict(list))
    seen_in_hour = defaultdict(lambda: defaultdict(set))

    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < 3: continue
            date, time, content = row
            
            # 生データレベルでの除外
            if any(k.lower() in content.lower() for k in EXCLUDE_KEYWORDS): continue
            
            hour = time.split(':')[0]
            verbed = get_verbed_content(content, topic_map, date)
            
            if verbed and verbed not in seen_in_hour[date][hour]:
                summary_data[date][hour].append(verbed)
                seen_in_hour[date][hour].add(verbed)

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['日付', '時間帯', '主な作業・検討内容'])
        
        for date in sorted(summary_data.keys()):
            for hour in sorted(summary_data[date].keys()):
                activities = summary_data[date][hour]
                if activities:
                    writer.writerow([
                        date,
                        f"{hour}:00 - {hour}:59",
                        "\n".join(activities)
                    ])

if __name__ == "__main__":
    summarize_activity()
