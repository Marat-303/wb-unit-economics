from app.db import get_connection

conn = get_connection()
try:
    rows = conn.execute("SELECT * FROM ads LIMIT 10").fetchall()
    print(f"Всего строк в таблице ads: {len(rows)}")
    for r in rows:
        print(dict(r))
finally:
    conn.close()