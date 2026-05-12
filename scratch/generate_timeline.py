import os
import sqlite3
import datetime
import shutil
import csv
import re

def get_file_updates():
    updates = []
    search_dirs = [
        os.getcwd(),
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Documents")
    ]
    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    for d in search_dirs:
        if not os.path.exists(d): continue
        for root, dirs, files in os.walk(d):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if f.startswith('~$'): continue
                path = os.path.join(root, f)
                try:
                    mtime = os.path.getmtime(path)
                    dt = datetime.datetime.fromtimestamp(mtime)
                    if dt >= today:
                        updates.append({'time': dt, 'type': 'ファイル', 'detail': f"{f}"})
                except: continue
    return updates

def get_browser_history(browser_name, history_path):
    history_items = []
    temp_history = f"scratch/{browser_name}_history_temp"
    if os.path.exists(history_path):
        try:
            shutil.copy2(history_path, temp_history)
            conn = sqlite3.connect(temp_history)
            cursor = conn.cursor()
            today_start = (datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - datetime.datetime(1601, 1, 1)).total_seconds() * 1000000
            cursor.execute("SELECT last_visit_time, url, title FROM urls WHERE last_visit_time >= ? ORDER BY last_visit_time ASC", (today_start,))
            for row in cursor.fetchall():
                dt = datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=row[0]) + datetime.timedelta(hours=9)
                history_items.append({'time': dt, 'type': 'ブラウザ', 'detail': f"{row[2][:50]}"})
            conn.close()
        except: pass
    return history_items

def get_ai_logs():
    logs = []
    brain_dir = os.path.expanduser("~/.gemini/antigravity/brain")
    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if os.path.exists(brain_dir):
        for root, dirs, files in os.walk(brain_dir):
            if 'overview.txt' in files:
                path = os.path.join(root, 'overview.txt')
                try:
                    mtime = os.path.getmtime(path)
                    dt = datetime.datetime.fromtimestamp(mtime)
                    if dt >= today:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            # 最後のやり取りを少し抽出
                            last_msg = content.split('\n')[-2] if len(content.split('\n')) > 1 else ""
                            logs.append({'time': dt, 'type': 'AI相談', 'detail': f"対話ログ更新: {last_msg[:50]}"})
                except: pass
    return logs

def main():
    all_events = []
    all_events.extend(get_file_updates())
    all_events.extend(get_browser_history("edge", os.path.expanduser("~/AppData/Local/Microsoft/Edge/User Data/Default/History")))
    all_events.extend(get_browser_history("chrome", os.path.expanduser("~/AppData/Local/Google/Chrome/User Data/Default/History")))
    all_events.extend(get_ai_logs())
    all_events.sort(key=lambda x: x['time'])

    # 15分単位で集計
    timeline = {}
    for ev in all_events:
        # Round down to 15 mins
        rounded_time = ev['time'].replace(minute=(ev['time'].minute // 15) * 15, second=0, microsecond=0)
        time_str = rounded_time.strftime('%H:%M')
        if time_str not in timeline:
            timeline[time_str] = []
        timeline[time_str].append(f"[{ev['type']}] {ev['detail']}")

    with open('scratch/daily_timeline.md', 'w', encoding='utf-8') as f:
        f.write("# 本日の業務記録 (15分単位)\n\n")
        f.write("| 時間 | 作業内容・検討事項 |\n")
        f.write("| :--- | :--- |\n")
        for t in sorted(timeline.keys()):
            details = "<br>".join(list(dict.fromkeys(timeline[t]))) # 重複排除
            f.write(f"| {t} | {details} |\n")

if __name__ == "__main__":
    main()
