import os
import sqlite3
import datetime
import shutil
import csv
import json
import subprocess
import re

START_DATE = datetime.datetime(2026, 4, 10)
END_DATE = datetime.datetime.now()

def get_git_history():
    events = []
    try:
        output = subprocess.check_output(
            ['git', 'log', f'--since={START_DATE.isoformat()}', '--pretty=format:%ad|%s', '--date=iso'],
            encoding='utf-8', errors='ignore'
        )
        for line in output.split('\n'):
            if '|' in line:
                date_str, subject = line.split('|', 1)
                dt = datetime.datetime.fromisoformat(date_str).replace(tzinfo=None)
                events.append({'time': dt, 'type': '開発', 'detail': f"Gitコミット: {subject}"})
    except: pass
    return events

def get_browser_history(browser_name, history_path):
    history_items = []
    temp_history = f"scratch/{browser_name}_final_history_temp"
    if os.path.exists(history_path):
        try:
            shutil.copy2(history_path, temp_history)
            conn = sqlite3.connect(temp_history)
            cursor = conn.cursor()
            start_ts = (START_DATE - datetime.datetime(1601, 1, 1)).total_seconds() * 1000000
            cursor.execute("SELECT last_visit_time, url, title FROM urls WHERE last_visit_time >= ? ORDER BY last_visit_time ASC", (start_ts,))
            for row in cursor.fetchall():
                dt = datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=row[0]) + datetime.timedelta(hours=9)
                if dt <= END_DATE:
                    title = row[2] if row[2] else row[1][:50]
                    history_items.append({'time': dt, 'type': 'ブラウザ', 'detail': f"閲覧: {title}"})
            conn.close()
        except: pass
    return history_items

def get_windows_activity():
    activity_items = []
    base_path = os.path.expandvars(r"%LOCALAPPDATA%\ConnectedDevicesPlatform")
    if not os.path.exists(base_path): return []
    
    for root, dirs, files in os.walk(base_path):
        if 'ActivitiesCache.db' in files:
            db_path = os.path.join(root, 'activitiescache.db')
            temp_db = f"scratch/activity_cache_final_{os.path.basename(root)}"
            try:
                shutil.copy2(db_path, temp_db)
                conn = sqlite3.connect(temp_db)
                cursor = conn.cursor()
                start_ts = int(START_DATE.timestamp())
                cursor.execute("SELECT StartTime, AppId, AppActivityId FROM Activity WHERE StartTime >= ? ORDER BY StartTime ASC", (start_ts,))
                for row in cursor.fetchall():
                    dt = datetime.datetime.fromtimestamp(row[0])
                    if dt <= END_DATE:
                        app_name = row[1]
                        try:
                            app_info = json.loads(row[1])
                            if isinstance(app_info, list) and len(app_info) > 0:
                                app_name = app_info[0].get('application', row[1])
                        except: pass
                        # Clean up common names
                        app_name = app_name.split('\\')[-1].replace('.exe', '')
                        if "Microsoft.Language.InputHistory" in app_name: continue # Skip noise
                        
                        detail = f"利用: {app_name}"
                        if row[2]: detail += f" ({row[2]})"
                        activity_items.append({'time': dt, 'type': 'アプリ', 'detail': detail})
                conn.close()
            except: pass
    return activity_items

def get_ai_logs():
    logs = []
    brain_dir = os.path.expanduser("~/.gemini/antigravity/brain")
    if os.path.exists(brain_dir):
        for root, dirs, files in os.walk(brain_dir):
            if 'overview.txt' in files:
                path = os.path.join(root, 'overview.txt')
                try:
                    mtime = os.path.getmtime(path)
                    dt = datetime.datetime.fromtimestamp(mtime)
                    if dt >= START_DATE:
                        logs.append({'time': dt, 'type': 'AI相談', 'detail': f"Antigravity対話ログの更新"})
                except: pass
    return logs

def main():
    all_events = []
    all_events.extend(get_git_history())
    all_events.extend(get_browser_history("edge", os.path.expanduser("~/AppData/Local/Microsoft/Edge/User Data/Default/History")))
    all_events.extend(get_browser_history("chrome", os.path.expanduser("~/AppData/Local/Google/Chrome/User Data/Default/History")))
    all_events.extend(get_windows_activity())
    all_events.extend(get_ai_logs())
    
    all_events.sort(key=lambda x: x['time'])

    output_dir = r"C:\Users\フォーレスト026\MyProject\tools\Memo"
    output_file = os.path.join(output_dir, "ActivityLog_0410_0512.csv")
    
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['日付', '時間', '作業内容'])
        for ev in all_events:
            writer.writerow([
                ev['time'].strftime('%Y/%m/%d'),
                ev['time'].strftime('%H:%M:%S'),
                f"[{ev['type']}] {ev['detail']}"
            ])

if __name__ == "__main__":
    main()
