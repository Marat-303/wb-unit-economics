from app.db import get_connection

conn = get_connection()
try:
    row = conn.execute("""
        SELECT SUM(delivery_rub) as delivery, 
               SUM(storage_fee) as storage, 
               SUM(penalty) as penalty,
               SUM(ppvz_for_pay) as for_pay
        FROM sales 
        WHERE report_date BETWEEN '2026-10-01' AND '2026-10-24'
    """).fetchone()
    print("Данные из базы за период 1-24 октября:")
    print(f"Логистика: {row['delivery'] or 0} ₽")
    print(f"Хранение: {row['storage'] or 0} ₽")
    print(f"Штрафы: {row['penalty'] or 0} ₽")
    print(f"К перечислению (до вычета расходов): {row['for_pay'] or 0} ₽")
finally:
    conn.close()