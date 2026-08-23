import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

try:
    # Delete logs
    cursor.execute("DELETE FROM client_logs WHERE user_id != 'ea8b1d32-6645-4ae3-8ca7-276260105c75'")
    logs_deleted = cursor.rowcount
    
    # Delete employees
    cursor.execute("DELETE FROM employees WHERE user_id != 'ea8b1d32-6645-4ae3-8ca7-276260105c75'")
    emp_deleted = cursor.rowcount
    
    conn.commit()
    print(f"Success! Deleted {emp_deleted} employees and {logs_deleted} logs.")
except Exception as e:
    conn.rollback()
    print(f"Error during deletion: {e}")
finally:
    cursor.close()
    conn.close()
