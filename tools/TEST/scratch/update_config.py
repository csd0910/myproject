import json
import os

path = 'data/config_unified.json'
if os.path.exists(path):
    with open(path, 'r', encoding='utf_8_sig') as f:
        config = json.load(f)
    
    config["status_list"] = ["未完了", "進行中", "完了", "保留", "中止"]
    config["helpdesk_genres"] = ["OA端末関連", "基幹端末関連", "ネットワーク", "サーバー", "開発", "総務関連", "業務運用", "名刺", "配送", "SCAW関連", "その他"]
    
    with open(path, 'w', encoding='utf_8_sig') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    print("Updated config_unified.json")
else:
    print("config_unified.json not found")
