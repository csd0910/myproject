import os
import psycopg2
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
df = pd.read_sql_query("SELECT id, app_name, operation_type, received_at FROM client_logs ORDER BY id DESC LIMIT 20", conn)
print("Latest Logs in Cloud DB:")
print(df.to_string())

import datetime
for ts in df['received_at'].head(5):
    print(f"{ts} -> {datetime.datetime.fromtimestamp(ts)}")
conn.close()
