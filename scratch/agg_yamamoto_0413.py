import pandas as pd
from datetime import datetime

def format_est_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    if h == 0: return f"{m}分"
    return f"{h}時間{m:02d}分"

def run_agg():
    csv_path = r'C:\Users\フォーレスト026\Desktop\伊藤作業用\残業調査\山本光克\山本光克_ログ検索結果-20260413.csv'
    df = pd.read_csv(csv_path, encoding='cp932', engine='python')
    df['dt'] = pd.to_datetime(df.iloc[:, 6])
    
    # 04/13 00:00 ～ 04/14 00:17
    target_logs = df[(df['dt'] >= pd.Timestamp('2026-04-13 00:00:00')) & (df['dt'] <= pd.Timestamp('2026-04-14 00:17:00'))].copy()
    target_logs = target_logs.sort_values('dt')
    target_logs['next_dt'] = target_logs['dt'].shift(-1)
    target_logs['diff'] = (target_logs['next_dt'] - target_logs['dt']).dt.total_seconds().fillna(0)
    target_logs['op_sec'] = target_logs['diff'].apply(lambda x: min(x, 300) if x > 0 else 0)
    
    # 22:00以降の残業
    overtime_logs = target_logs[target_logs['dt'] > pd.Timestamp('2026-04-13 22:00:00')]
    
    col_title = df.columns[14]
    stats = overtime_logs[overtime_logs[col_title].notna()].groupby(col_title).agg(
        total_sec=('op_sec', 'sum'),
        start=('dt', 'min'),
        end=('dt', 'max')
    ).sort_values('total_sec', ascending=False)
    
    print("--- 22:00以降の作業詳細データ ---")
    for title, row in stats.iterrows():
        print(f"{title}: {row['start'].strftime('%H:%M')} ～ {row['end'].strftime('%H:%M')} ({format_est_time(row['total_sec'])})")

if __name__ == "__main__":
    run_agg()
