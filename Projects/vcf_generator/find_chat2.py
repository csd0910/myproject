import os
import json

chat_ids = ['5a843f32-d507-4b9e-856a-4ef2e258b09b', '72534331-0355-4e4a-a173-69fd193a7a89']
brain_dir = r"C:\Users\フォーレスト026\.gemini\antigravity-ide\brain"

for cid in chat_ids:
    path = os.path.join(brain_dir, cid, r".system_generated\logs\transcript.jsonl")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                if data.get('type') == 'USER_INPUT':
                    content = data.get('content', '')[:100]
                    print(f"Chat {cid}:\n  First input: {content}\n")
                    break
    except Exception as e:
        print(e)
