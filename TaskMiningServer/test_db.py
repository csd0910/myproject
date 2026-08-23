import sqlite3
conn = sqlite3.connect('taskmining.db')
cur = conn.cursor()
cur.execute('PRAGMA table_info(client_logs)')
print(cur.fetchall())
