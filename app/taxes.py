import calendar
from datetime import datetime, date
from app.db import get_connection

def get_taxes_and_premiums() -> tuple[dict[str, float], dict[str, float]]:
    """Возвращает два словаря: {месяц: налог} и {месяц: взносы}"""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT month_str, tax_amount, premiums_amount FROM taxes").fetchall()
        taxes = {r["month_str"]: r["tax_amount"] for r in rows}
        premiums = {r["month_str"]: r["premiums_amount"] for r in rows}
        return taxes, premiums
    finally:
        conn.close()

def get_taxes_and_premiums_for_period(date_from_str: str, date_to_str: str) -> tuple[float, float]:
    """
    Считает сумму налогов и взносов за период.
    Если выбранный период попадает на месяц (хотя бы одним днем), 
    берется ПОЛНАЯ сумма налогов и взносов за этот месяц.
    """
    start_date = datetime.strptime(date_from_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(date_to_str, "%Y-%m-%d").date()
    
    taxes, premiums = get_taxes_and_premiums()
    
    total_tax = 0.0
    total_prem = 0.0
    
    current_year = start_date.year
    current_month = start_date.month
    
    # Итерируемся по всем месяцам, которые попадают в период
    while (current_year < end_date.year) or (current_year == end_date.year and current_month <= end_date.month):
        month_str = f"{current_year}-{current_month:02d}"
        
        _, last_day = calendar.monthrange(current_year, current_month)
        month_start = date(current_year, current_month, 1)
        month_end = date(current_year, current_month, last_day)
        
        # Проверяем, пересекается ли выбранный период с текущим месяцем
        if max(start_date, month_start) <= min(end_date, month_end):
            total_tax += taxes.get(month_str, 0.0)
            total_prem += premiums.get(month_str, 0.0)
            
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1
            
    return round(total_tax, 2), round(total_prem, 2)

def set_tax(month_str: str, amount: float) -> None:
    """Сохраняет сумму налога."""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO taxes (month_str, tax_amount)
            VALUES (?, ?)
            ON CONFLICT(month_str) DO UPDATE SET tax_amount = excluded.tax_amount
            """,
            (month_str, amount)
        )
        conn.commit()
    finally:
        conn.close()

def set_premium(month_str: str, amount: float) -> None:
    """Сохраняет сумму страховых взносов."""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO taxes (month_str, premiums_amount)
            VALUES (?, ?)
            ON CONFLICT(month_str) DO UPDATE SET premiums_amount = excluded.premiums_amount
            """,
            (month_str, amount)
        )
        conn.commit()
    finally:
        conn.close()

def set_quarter_taxes(quarter: int, year: int, total_amount: float, monthly_revenues: dict[int, float]) -> None:
    """Распределяет сумму налога за квартал по месяцам пропорционально выручке."""
    months = [(quarter - 1) * 3 + 1, (quarter - 1) * 3 + 2, quarter * 3]
    total_revenue = sum(monthly_revenues.get(m, 0) for m in months)
    
    total_amount = float(total_amount)
    distributed = 0.0

    for i, m in enumerate(months):
        month_str = f"{year}-{m:02d}"
        
        if i == len(months) - 1:
            share_amount = total_amount - distributed
        else:
            if total_revenue > 0:
                share = (monthly_revenues.get(m, 0) / total_revenue)
                share_amount = round(total_amount * share, 2)
            else:
                share_amount = round(total_amount / 3, 2)
            distributed += share_amount
            
        set_tax(month_str, share_amount)

def set_yearly_premium(year: int, total_amount: float, monthly_revenues: dict[int, float]) -> None:
    """Распределяет ГОДОВУЮ сумму фиксированных взносов по всем месяцам с выручкой."""
    total_amount = float(total_amount)
    total_revenue = sum(monthly_revenues.values())
    distributed = 0.0
    
    months = sorted(monthly_revenues.keys())
    
    for i, m in enumerate(months):
        month_str = f"{year}-{m:02d}"
        
        if i == len(months) - 1:
            share_amount = total_amount - distributed
        else:
            if total_revenue > 0:
                share = monthly_revenues[m] / total_revenue
                share_amount = round(total_amount * share, 2)
            else:
                share_amount = round(total_amount / len(months), 2)
            distributed += share_amount
            
        set_premium(month_str, share_amount)