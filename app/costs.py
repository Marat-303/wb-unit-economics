import sqlite3
from datetime import datetime
from app.db import get_connection

def list_articles_with_costs(year: int, month: int):
    """Возвращает список всех товаров и их себестоимость за конкретный месяц."""
    with get_connection() as conn:
        # Берем товары из справочника products и цепляем себестоимость за месяц
        cursor = conn.execute("""
            SELECT p.nm_id, p.title, p.vendor_code as sa_name, c.cost_rub
            FROM products p
            LEFT JOIN cost_prices c ON p.nm_id = c.nm_id AND c.year = ? AND c.month = ?
            ORDER BY p.title ASC
        """, (year, month))
        return cursor.fetchall()

def set_cost(nm_id: int, sa_name: str | None, cost_rub: float, year: int, month: int):
    """Сохраняет себестоимость для конкретного месяца."""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO cost_prices (nm_id, year, month, sa_name, cost_rub)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(nm_id, year, month) DO UPDATE SET
                sa_name = excluded.sa_name,
                cost_rub = excluded.cost_rub,
                updated_at = datetime('now')
        """, (nm_id, year, month, sa_name, cost_rub))
        conn.commit()

def copy_costs_from_previous_month(target_year: int, target_month: int) -> int:
    """Копирует себестоимость с прошлого месяца в текущий. Возвращает кол-во скопированных строк."""
    if target_month == 1:
        prev_month = 12
        prev_year = target_year - 1
    else:
        prev_month = target_month - 1
        prev_year = target_year

    with get_connection() as conn:
        # Получаем данные за прошлый месяц
        cursor = conn.execute("SELECT nm_id, sa_name, cost_rub FROM cost_prices WHERE year = ? AND month = ?", (prev_year, prev_month))
        prev_data = cursor.fetchall()
        
        count = 0
        for row in prev_data:
            conn.execute("""
                INSERT INTO cost_prices (nm_id, year, month, sa_name, cost_rub)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(nm_id, year, month) DO UPDATE SET
                    cost_rub = excluded.cost_rub,
                    updated_at = datetime('now')
            """, (row["nm_id"], target_year, target_month, row["sa_name"], row["cost_rub"]))
            count += 1
        conn.commit()
        return count

def set_product_title(nm_id: int, title: str):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO products (nm_id, title) VALUES (?, ?)
            ON CONFLICT(nm_id) DO UPDATE SET title = excluded.title, updated_at = datetime('now')
        """, (nm_id, title))
        conn.commit()

def set_product_vendor_code(nm_id: int, vendor_code: str):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO products (nm_id, vendor_code) VALUES (?, ?)
            ON CONFLICT(nm_id) DO UPDATE SET vendor_code = excluded.vendor_code, updated_at = datetime('now')
        """, (nm_id, vendor_code))
        conn.commit()

def get_cost_for_date(nm_id: int, date_str: str) -> float | None:
    """Вспомогательная функция для экономики: берет себестоимость по дате продажи."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.execute("SELECT cost_rub FROM cost_prices WHERE nm_id = ? AND year = ? AND month = ?", (nm_id, dt.year, dt.month))
        row = cursor.fetchone()
        return row["cost_rub"] if row else None

def import_costs_from_excel(path: str) -> int:
    # Заглушка, если у тебя была реализация, верни ее сюда, 
    # передавая year и month из интерфейса.
    # Но для работы интерфейса она должна принимать (path, year, month)
    pass