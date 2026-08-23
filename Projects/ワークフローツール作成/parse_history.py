import json
import os
import re
from datetime import datetime

# 共通ディレクトリ定義
brain_dirs = [
    r"C:\Users\フォーレスト026\.gemini\antigravity-ide\brain",
    r"C:\Users\フォーレスト026\.gemini\antigravity\brain"
]
workspace_dir = r"c:\Users\フォーレスト026\MyProject"
docs_dir = os.path.join(workspace_dir, "Docs")
desktop_dir = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\ワークフローツール作成\アクセス頻度を計算する"

catalog_path = os.path.join(docs_dir, "社内システム開発・運用ツール総合カタログ.md")
desktop_catalog_path = os.path.join(desktop_dir, "社内システム開発・運用ツール総合カタログ.md")

def main():
    if not os.path.exists(catalog_path):
        print(f"Error: カタログファイルが見つかりません: {catalog_path}")
        return

    # 1. カタログファイルの読み込み
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog_content = f.read()

    # 重複を避けるために既存の「4. 全開発チャット作業履歴」以降を切り捨てる
    if "## 4. 全開発チャット作業履歴" in catalog_content:
        catalog_content = catalog_content.split("## 4. 全開発チャット作業履歴")[0].strip()

    # 2. 全チャットIDとパスのリスト取得と英語タイトルのスキャン
    chat_ids_paths = []
    for b_dir in brain_dirs:
        try:
            if os.path.exists(b_dir):
                for d in os.listdir(b_dir):
                    p = os.path.join(b_dir, d)
                    if os.path.isdir(p) and not d.startswith('.'):
                        chat_ids_paths.append((d, p))
        except Exception as e:
            print(f"Error listing brain directory {b_dir}: {e}")

    english_titles = {}
    
    # 既知の英語タイトル
    known_titles = {
        "656008f8-457e-451e-b31f-c580e6fb6710": "Developing Ringi Tool",
        "02f07a7f-d9f8-4f31-be61-059361587039": "Analyzing Price Revision Logic",
        "1efa56b8-4c4e-4ca1-840b-322dfd4fcd78": "Analyzing Access Frequency",
        "cf7a6533-9b3a-4a80-bf5d-22cc238b97d2": "Analyzing Overtime Evidence",
        "1bb4638f-62da-4814-87cf-451372fb79a3": "Integrating PDF Tools",
        "0d4c9c86-6ad8-450a-8bf8-d62f4405391e": "Exporting Cybozu Emails",
        "56ad1a75-17e6-47d2-9721-655bb7090391": "Backing Up Cybozu Workflows"
    }
    english_titles.update(known_titles)

    # ログファイル内から英語タイトルを自動スキャン
    for cid, path in chat_ids_paths:
        log_file = os.path.join(path, ".system_generated", "logs", "transcript.jsonl")
        if not os.path.exists(log_file):
            continue
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    data = json.loads(line)
                    content = data.get("content", "")
                    if content:
                        matches = re.findall(r'## Conversation ([a-f0-9\-]+):\s*([^\n\r]+)', content)
                        for matched_id, matched_title in matches:
                            english_titles[matched_id] = matched_title.strip()
        except:
            pass

    # 各チャットの履歴を収集
    chat_records = []
    for cid, path in chat_ids_paths:
        log_file = os.path.join(path, ".system_generated", "logs", "transcript.jsonl")
        if not os.path.exists(log_file):
            continue
            
        jp_title = "名称未設定のチャット"
        last_model_content = ""
        last_update_time = None
        
        try:
            stat = os.stat(log_file)
            last_update_time = datetime.fromtimestamp(stat.st_mtime)
        except:
            pass
            
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    data = json.loads(line)
                    if data.get("source") == "MODEL" and data.get("type") == "PLANNER_RESPONSE":
                        content = data.get("content", "")
                        if content:
                            last_model_content = content
                            match = re.search(r'【推奨タイトル：([^】]+)】', content)
                            if match:
                                jp_title = match.group(1)
        except:
            pass
                    
        summary = "作業内容の詳細情報がありません。"
        if last_model_content:
            lines = [l.strip() for l in last_model_content.split('\n') if l.strip()]
            bullets = [l for l in lines if l.startswith('*') or l.startswith('-') or l.startswith('1.') or l.startswith('2.')]
            if bullets:
                summary = "\n".join(bullets[:5])
            else:
                summary = "\n".join(lines[:3])
                
        eng_title = english_titles.get(cid, "Conversation " + cid[:8])
        
        chat_records.append({
            "id": cid,
            "eng_title": eng_title,
            "jp_title": jp_title,
            "summary": summary,
            "time": last_update_time
        })

    # 新しい順にソート
    chat_records = sorted(chat_records, key=lambda x: x["time"] if x["time"] else datetime.min, reverse=True)

    # 3. 追加用マークダウンの生成
    history_md = "\n\n## 4. 全開発チャット作業履歴\n\nこれまでに本環境で実施したすべての開発チャット名（英名および日本語推奨タイトル）と作業内容の一覧です（最新順）。\n\n---\n"
    for record in chat_records:
        time_str = record["time"].strftime("%Y/%m/%d %H:%M:%S") if record["time"] else "不明"
        history_md += f"""
### 💬 チャット名 (英名): `{record["eng_title"]}`
* **日本語推奨タイトル**: `【推奨タイトル：{record["jp_title"]}】`
* **最終更新日時**: `{time_str}`
* **チャットID**: `{record["id"]}`
* **主な作業内容 / 出力サマリー**:
{record["summary"]}

---
"""

    final_content = catalog_content.strip() + history_md

    # ワークスペースに保存
    with open(catalog_path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    print(f"ワークスペースのカタログを更新しました: {catalog_path}")

    # デスクトップに同期コピー
    if os.path.exists(desktop_dir):
        try:
            with open(desktop_catalog_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
            print(f"デスクトップのカタログへ同期しました: {desktop_catalog_path}")
        except Exception as e:
            print(f"デスクトップへの同期に失敗しました: {e}")

if __name__ == "__main__":
    main()
