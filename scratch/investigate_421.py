import os
import json

brain_dir = os.path.expanduser("~/.gemini/antigravity/brain")
found = False
for root, dirs, files in os.walk(brain_dir):
    if 'overview.txt' in files:
        p = os.path.join(root, 'overview.txt')
        with open(p, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if '2026-04-21' in data.get('created_at', ''):
                        content = data.get('content', '')
                        if '<USER_REQUEST>' in content:
                            print(f"Date: 2026/04/21 | Content: {content[:300]}")
                            found = True
                            break
                except: continue
if not found:
    print("No log found for 2026-04-21 in brain.")
