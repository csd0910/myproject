import psycopg2
import pandas as pd
import os
from dotenv import load_dotenv
import sys

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()
conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
df = pd.read_sql_query("SELECT operation_type, COUNT(*) FROM client_logs WHERE user_id = 'ea8b1d32-6645-4ae3-8ca7-276260105c75' GROUP BY operation_type", conn)
print(df.to_string())
conn.close()
