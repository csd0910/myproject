import psycopg2
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL)

df_emp = pd.read_sql_query('SELECT * FROM employees ORDER BY id DESC LIMIT 500', conn)
df_emp.to_csv('employees_latest_500.csv', index=False, encoding='utf-8-sig')

df_logs = pd.read_sql_query('SELECT * FROM client_logs ORDER BY id DESC LIMIT 500', conn)
df_logs.to_csv('client_logs_latest_500.csv', index=False, encoding='utf-8-sig')

cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM employees WHERE user_id != 'ea8b1d32-6645-4ae3-8ca7-276260105c75'")
emp_delete_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM client_logs WHERE user_id != 'ea8b1d32-6645-4ae3-8ca7-276260105c75'")
log_delete_count = cursor.fetchone()[0]

print(f"Emp delete count: {emp_delete_count}")
print(f"Log delete count: {log_delete_count}")

conn.close()
