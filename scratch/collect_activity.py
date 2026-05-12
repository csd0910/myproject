import os
import sqlite3
import datetime
import shutil
import csv

def get_file_updates():
    updates = []
    # 検索対象ディレクトリ
    search_dirs = [
        os.getcwd(),
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Documents")
    ]
    
    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    for d in search_dirs:
        if not os.path.exists(d): continue
        for root, dirs, files in os.walk(d):
            # Skip hidden dirs
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if f.startswith('~$'): continue # Skip temp office files
                path = os.path.join(root, f)
                try:
                    mtime = os.path.getmtime(path)
                    dt = datetime.datetime.fromtimestamp(mtime)
                    if dt >= today:
                        updates.append({
                            'time': dt,
                            'type': 'FILE',
                            'detail': f"ファイル更新: {f} ({path})"
                        })
                except:
                    continue
    return updates

def get_browser_history():
    history_items = []
    # Edge History Path
    edge_history = os.path.expanduser("~/AppData/Local/Microsoft/Edge/User Data/Default/History")
    temp_history = "scratch/edge_history_temp"
    
    if os.path.exists(edge_history):
        try:
            shutil.copy2(edge_history, temp_history)
            conn = sqlite3.connect(temp_history)
            cursor = conn.cursor()
            
            # Windows time epoch starts from 1601-01-01
            today_start = (datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - datetime.datetime(1601, 1, 1)).total_seconds() * 1000000
            
            cursor.execute("SELECT last_visit_time, url, title FROM urls WHERE last_visit_time >= ? ORDER BY last_visit_time ASC", (today_start,))
            for row in cursor.fetchall():
                # Convert chrome time to datetime
                dt = datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=row[0])
                # Adjust to JST (Roughly +9h if needed, but dt might be UTC)
                # For simplicity, let's just use it as is for now or adjust if it looks wrong
                history_items.append({
                    'time': dt + datetime.timedelta(hours=9), # Assuming system is JST and DB is UTC
                    'type': 'BROWSER',
                    'detail': f"閲覧: {row[2]} ({row[1]})"
                })
            conn.close()
        except Exception as e:
            print(f"Browser history error: {e}")
    return history_items

def main():
    all_events = []
    all_events.extend(get_file_updates())
    all_events.extend(get_browser_history())
    
    # Sort by time
    all_events.sort(key=lambda x: x['time'])
    
    with open('scratch/activity_log_raw.csv', 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['time', 'type', 'detail'])
        writer.writeheader()
        for ev in all_events:
            writer.writerow({
                'time': ev['time'].strftime('%Y-%m-%d %H:%M:%S'),
                'type': ev['type'],
                'detail': ev['detail']
            })

if __name__ == "__main__":
    main()
