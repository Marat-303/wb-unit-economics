import math
from app.db import get_connection
from app.costs import get_costs_map

def calculate_unit_economics(date_from: str, date_to: str) -> dict:
    conn = get_connection()
    try:
        sales_rows = conn.execute(
            """
            SELECT s.report_date, s.nm_id, COALESCE(p.title, s.sa_name, '') AS name, SUM(s.quantity) AS qty,
                   SUM(s.return_qty) AS return_qty,
                   SUM(s.retail_amount) AS revenue, SUM(s.ppvz_for_pay) AS payout,
                   SUM(s.delivery_rub) AS delivery, SUM(s.storage_fee) AS storage, SUM(s.processing_fee) AS processing,
                   SUM(s.other_deductions) AS other, SUM(s.penalty_fee) AS penalty, SUM(s.wb_correction) AS correction
            FROM sales s LEFT JOIN products p ON p.nm_id = s.nm_id
            WHERE s.report_date BETWEEN ? AND ? GROUP BY s.report_date, s.nm_id
            """, (date_from, date_to)
        ).fetchall()

        ads_rows = conn.execute(
            "SELECT report_date, nm_id, SUM(sum_rub) AS ads_sum FROM ads WHERE report_date BETWEEN ? AND ? AND nm_id != 0 GROUP BY report_date, nm_id",
            (date_from, date_to)
        ).fetchall()
        ads_map = {(r["report_date"], r["nm_id"]): r["ads_sum"] for r in ads_rows}

        ads_daily_rows = conn.execute(
            "SELECT report_date, SUM(sum_rub) AS ads_sum FROM ads WHERE report_date BETWEEN ? AND ? GROUP BY report_date",
            (date_from, date_to)
        ).fetchall()
        daily_ads_map = {r["report_date"]: float(r["ads_sum"] or 0) for r in ads_daily_rows}

        ads_total_row = conn.execute(
            "SELECT SUM(sum_rub) AS total, SUM(sum_price) AS total_price FROM ads WHERE report_date BETWEEN ? AND ?",
            (date_from, date_to)
        ).fetchone()
        ads_total = float(ads_total_row["total"] or 0)
        ads_total_price = float(ads_total_row["total_price"] or 0)
    finally:
        conn.close()

    costs = get_costs_map()
    by_article: dict[int, dict] = {}
    by_day: dict[str, dict] = {}

    for r in sales_rows:
        nm_id = r["nm_id"]
        date_key = r["report_date"]
        qty = int(r["qty"] or 0)
        return_qty = int(r["return_qty"] or 0)
        revenue = float(r["revenue"] or 0)
        payout = float(r["payout"] or 0)
        wb_costs = revenue - payout

        cost_unit = costs.get(nm_id)
        has_cost = cost_unit is not None
        cost_total = cost_unit * qty if has_cost else 0.0
        profit_article = payout - cost_total

        if nm_id not in by_article:
            by_article[nm_id] = {
                "nm_id": nm_id, "name": r["name"], "qty": 0, "return_qty": 0, "revenue": 0.0, "delivery": 0.0,
                "storage": 0.0, "processing": 0.0, "other": 0.0, "penalty": 0.0, "correction": 0.0,
                "wb_costs": 0.0, "payout": 0.0, "cost": 0.0, "ads": 0.0, "profit": 0.0, "has_cost": has_cost,
            }
        a = by_article[nm_id]
        a["qty"] += qty
        a["return_qty"] += return_qty
        a["revenue"] += revenue
        a["delivery"] += float(r["delivery"] or 0)
        a["storage"] += float(r["storage"] or 0)
        a["processing"] += float(r["processing"] or 0)
        a["other"] += float(r["other"] or 0)
        a["penalty"] += float(r["penalty"] or 0)
        a["correction"] += float(r["correction"] or 0)
        a["wb_costs"] += wb_costs
        a["payout"] += payout
        a["cost"] += cost_total
        a["profit"] += profit_article

        if date_key not in by_day:
            by_day[date_key] = {
                "date": date_key, "qty": 0, "return_qty": 0, "revenue": 0.0, "delivery": 0.0, "storage": 0.0,
                "processing": 0.0, "other": 0.0, "penalty": 0.0, "correction": 0.0,
                "wb_costs": 0.0, "payout": 0.0, "cost": 0.0, "ads": 0.0, "profit": 0.0,
            }
        d = by_day[date_key]
        d["qty"] += qty
        d["return_qty"] += return_qty
        d["revenue"] += revenue
        d["delivery"] += float(r["delivery"] or 0)
        d["storage"] += float(r["storage"] or 0)
        d["processing"] += float(r["processing"] or 0)
        d["other"] += float(r["other"] or 0)
        d["penalty"] += float(r["penalty"] or 0)
        d["correction"] += float(r["correction"] or 0)
        d["wb_costs"] += wb_costs
        d["payout"] += payout
        d["cost"] += cost_total
        d["profit"] += profit_article

    for date_key, d in by_day.items():
        daily_ads = daily_ads_map.get(date_key, 0.0)
        d["ads"] = daily_ads
        d["profit"] = d["profit"] - round(daily_ads)
        d["margin"] = (d["profit"] / d["revenue"] * 100) if d["revenue"] else 0.0
        d["drr"] = (daily_ads / d["revenue"] * 100) if d["revenue"] else 0.0

    for a in by_article.values():
        a["margin"] = (a["profit"] / a["revenue"] * 100) if a["revenue"] else 0.0
        a["drr"] = 0.0 

    totals = {
        "revenue": sum(a["revenue"] for a in by_article.values()),
        "delivery": sum(a["delivery"] for a in by_article.values()),
        "storage": sum(a["storage"] for a in by_article.values()),
        "processing": sum(a["processing"] for a in by_article.values()),
        "other": sum(a["other"] for a in by_article.values()),
        "penalty": sum(a["penalty"] for a in by_article.values()),
        "correction": sum(a["correction"] for a in by_article.values()),
        "wb_costs": sum(a["wb_costs"] for a in by_article.values()),
        "payout": sum(a["payout"] for a in by_article.values()),
        "cost": sum(a["cost"] for a in by_article.values()),
        "ads": ads_total,
        "ads_total_price": ads_total_price,
        "profit": sum(a["profit"] for a in by_article.values()) - round(ads_total),
        "qty": sum(a["qty"] for a in by_article.values()),
        "return_qty": sum(a["return_qty"] for a in by_article.values()),
        "articles_without_cost": [a["nm_id"] for a in by_article.values() if not a["has_cost"] and a["nm_id"] != 0],
    }
    
    totals["margin"] = (totals["profit"] / totals["revenue"] * 100) if totals["revenue"] else 0.0
    totals["drr"] = (totals["ads"] / totals["ads_total_price"] * 100) if totals["ads_total_price"] else 0.0

    return {
        "totals": totals,
        "by_article": sorted([a for a in by_article.values() if a["nm_id"] != 0], key=lambda x: -x["revenue"]),
        "by_day": sorted(by_day.values(), key=lambda x: x["date"], reverse=False),
    }