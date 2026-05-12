import os
import json
import datetime
import re
from collections import defaultdict

def get_dev_topics():
    brain_dir = os.path.expanduser("~/.gemini/antigravity/brain")
    topics = defaultdict(set)
    
    if not os.path.exists(brain_dir):
        return {}

    for root, dirs, files in os.walk(brain_dir):
        # 1. overview.txt から具体的な「依頼内容」を探す
        if 'overview.txt' in files:
            path = os.path.join(root, 'overview.txt')
            try:
                # 最初にその会話の「目的」を特定
                objective = "システム開発・改善"
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    # 最初のUSER_INPUTを探す
                    for line in lines:
                        try:
                            d = json.loads(line)
                            if d.get('type') == 'USER_INPUT' and '<USER_REQUEST>' in d.get('content', ''):
                                req = d['content'].split('<USER_REQUEST>')[1].split('</USER_REQUEST>')[0].strip()
                                objective = req.split('\n')[0][:50]
                                objective = re.sub(r'[#<>\"\'\[\]]', '', objective)
                                break
                        except: continue
                    
                    # その会話内の各アクションの日付に、その目的を紐付ける
                    for line in lines:
                        try:
                            d = json.loads(line)
                            ts = d.get('created_at')
                            if ts:
                                dt = ts.split('T')[0].replace('-', '/')
                                topics[dt].add((10, objective))
                        except: continue
            except: pass
        
        # 2. メタデータからの補完
        for f in files:
            if f.endswith('.metadata.json'):
                path = os.path.join(root, f)
                try:
                    with open(path, 'r', encoding='utf-8') as j:
                        data = json.load(j)
                        ts = data.get('updatedAt') or data.get('createdAt')
                        if ts:
                            dt = ts.split('T')[0].replace('-', '/')
                            name = f.replace('.metadata.json', '')
                            if 'web_element' in name.lower():
                                topics[dt].add((5, "Web要素抽出ツールの開発"))
                            elif 'overtime' in name.lower():
                                topics[dt].add((5, "残業調査報告書生成ツールの開発"))
                except: pass
            
    final_topics = {}
    for dt in topics:
        sorted_items = sorted(list(topics[dt]), key=lambda x: x[0], reverse=True)
        final_topics[dt] = [item[1] for item in sorted_items[:3]]
            
    return final_topics

if __name__ == "__main__":
    print(json.dumps(get_dev_topics(), ensure_ascii=False))
