from app.db import get_connection

conn = get_connection()
try:
    conn.execute("DELETE FROM ads")
    conn.commit()
    print("Таблица ads очищена от старых данных.")
finally:
    conn.close()