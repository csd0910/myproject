import os
import glob
import json

brain_dir = r"C:\Users\フォーレスト026\.gemini\antigravity-ide\brain"
pattern = os.path.join(brain_dir, r"*\.system_generated\logs\transcript.jsonl")

found_chats = []

for filepath in glob.glob(pattern):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if "DX_Reverse_Engineering_Engine" in content:
                chat_id = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(filepath))))
                found_chats.append(chat_id)
    except Exception as e:
        pass

for chat_id in set(found_chats):
    print(f"Found in Chat ID: {chat_id}")
