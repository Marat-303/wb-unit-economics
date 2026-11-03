import csv
import openpyxl
from pathlib import Path

from app.db import get_connection


def list_articles_with_costs() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT s.nm_id,
                   MAX(COALESCE(NULLIF(p.vendor_code, ''), s.sa_name)) AS sa_name,
                   MAX(p.title) AS title,
                   c.cost_rub
            FROM sales s
            LEFT JOIN products p ON p.nm_id = s.nm_id
            LEFT JOIN cost_prices c ON c.nm_id = s.nm_id
            WHERE s.nm_id != 0
            GROUP BY s.nm_id
            ORDER BY COALESCE(MAX(p.title), MAX(s.sa_name)), s.nm_id
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def set_product_title(nm_id: int, title: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO products (nm_id, title, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(nm_id) DO UPDATE SET
                title = excluded.title,
                updated_at = datetime('now')
            """,
            (nm_id, title),
        )
        conn.commit()
    finally:
        conn.close()


def set_product_vendor_code(nm_id: int, vendor_code: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO products (nm_id, vendor_code, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(nm_id) DO UPDATE SET
                vendor_code = excluded.vendor_code,
                updated_at = datetime('now')
            """,
            (nm_id, vendor_code),
        )
        conn.commit()
    finally:
        conn.close()


def set_cost(nm_id: int, sa_name: str | None, cost_rub: float) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO cost_prices (nm_id, sa_name, cost_rub, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(nm_id) DO UPDATE SET
                sa_name = excluded.sa_name,
                cost_rub = excluded.cost_rub,
                updated_at = datetime('now')
            """,
            (nm_id, sa_name, cost_rub),
        )
        conn.commit()
    finally:
        conn.close()


def delete_cost(nm_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM cost_prices WHERE nm_id = ?", (nm_id,))
        conn.commit()
    finally:
        conn.close()


def get_costs_map() -> dict[int, float]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT nm_id, cost_rub FROM cost_prices").fetchall()
        return {r["nm_id"]: r["cost_rub"] for r in rows}
    finally:
        conn.close()


def import_costs_from_csv(path: str | Path) -> int:
    path = Path(path)
    count = 0
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                nm_id = int(row["nm_id"])
                cost = float(str(row["cost_rub"]).replace(",", "."))
            except (KeyError, ValueError):
                continue
            set_cost(nm_id, row.get("sa_name"), cost)
            count += 1
    return count


def import_costs_from_excel(path: str | Path) -> int:
    path = Path(path)
    count = 0
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"Не удалось открыть файл Excel: {e}")
        
    sheet = wb.active
    
    # Читаем заголовки
    headers = [str(cell.value).strip().lower() if cell.value else "" for cell in sheet[1]]
    
    try:
        nm_idx = headers.index('nm_id')
        cost_idx = headers.index('cost_rub')
        name_idx = headers.index('sa_name') if 'sa_name' in headers else -1
    except ValueError:
        wb.close()
        raise ValueError("В файле должны быть колонки: nm_id, cost_rub (и опционально sa_name)")
    
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if not row or row[nm_idx] is None:
            continue
        try:
            nm_id = int(row[nm_idx])
            cost = float(row[cost_idx])
        except (ValueError, TypeError):
            continue
            
        sa_name = str(row[name_idx]) if name_idx != -1 and row[name_idx] is not None else None
        set_cost(nm_id, sa_name, cost)
        count += 1
    
    wb.close()
    return count