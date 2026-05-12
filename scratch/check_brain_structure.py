import os

brain_dir = os.path.expanduser("~/.gemini/antigravity/brain")
for root, dirs, files in os.walk(brain_dir):
    if 'overview.txt' in files:
        p = os.path.join(root, 'overview.txt')
        print(f"--- {p} ---")
        with open(p, 'r', encoding='utf-8', errors='ignore') as f:
            print(f.read(1000))
        break
