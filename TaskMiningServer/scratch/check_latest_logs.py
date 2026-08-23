import psycopg2
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
df = pd.read_sql_query("SELECT id, operation_type, manual_typing_count, click_count, received_at FROM client_logs WHERE user_id = 'ea8b1d32-6645-4ae3-8ca7-276260105c75' ORDER BY id DESC LIMIT 10", conn)
print(df.to_string())
conn.close()
