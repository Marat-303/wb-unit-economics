from app.db import get_connection

conn = get_connection()
try:
    conn.execute("DELETE FROM sales")
    conn.execute("DELETE FROM ads")
    conn.commit()
    print("Таблицы sales и ads успешно очищены. Себестоимость сохранена.")
finally:
    conn.close()