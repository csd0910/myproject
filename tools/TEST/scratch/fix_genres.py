import json
import os

path = 'data/config_unified.json'
genres = [
    "SCAW関連", "OA端末関連", "基幹端末関連", "ネットワーク", 
    "サーバー", "開発", "総務関連", "業務運用", 
    "名刺", "配送", "その他"
]

if os.path.exists(path):
    with open(path, 'r', encoding='utf_8_sig') as f:
        config = json.load(f)
    
    config["helpdesk_genres"] = genres
    
    with open(path, 'w', encoding='utf_8_sig') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    print("Updated config_unified.json with correct genres.")
else:
    print("config_unified.json not found")
