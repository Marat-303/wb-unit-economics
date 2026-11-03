from datetime import date, timedelta, datetime
from app.db import get_connection
from app.wb_api import WBAPIClient

def _aggregate_sales(rows: list[dict]) -> dict:
    aggregated: dict[tuple[str, int], dict] = {}
    for row in rows:
        nm_id = int(row.get("nmId") or 0)
        if not nm_id: continue
        report_date = str(row.get("date", ""))[:10]
        if not report_date: continue

        sale_id = str(row.get("saleID", ""))
        qty = 1 if sale_id.startswith("S") else -1

        key = (report_date, nm_id)
        agg = aggregated.setdefault(key, {
            "report_date": report_date, "nm_id": nm_id, "sa_name": row.get("sa_name"),
            "quantity": 0, "retail_amount": 0.0, "ppvz_sales_commission": 0.0, "ppvz_for_pay": 0.0,
            "delivery_rub": 0.0, "storage_fee": 0.0, "processing_fee": 0.0,
            "other_deductions": 0.0, "penalty_fee": 0.0, "wb_correction": 0.0,
        })
        agg["quantity"] += qty
        agg["retail_amount"] += float(row.get("forPay") or 0)
        agg["ppvz_sales_commission"] += float(row.get("ppvz_sales_commission") or 0)
        agg["ppvz_for_pay"] += float(row.get("forPay") or 0)
        if not agg["sa_name"]: agg["sa_name"] = row.get("sa_name")
    return aggregated

def save_sales_to_db(rows: list[dict]) -> int:
    aggregated = _aggregate_sales(rows)
    if not aggregated: return 0

    conn = get_connection()
    try:
        for agg in aggregated.values():
            conn.execute(
                """
                INSERT INTO sales
                    (report_date, nm_id, sa_name, quantity, retail_amount,
                     ppvz_sales_commission, ppvz_for_pay, delivery_rub,
                     storage_fee, processing_fee, other_deductions, penalty_fee, wb_correction)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0)
                ON CONFLICT(report_date, nm_id) DO UPDATE SET
                    sa_name = excluded.sa_name,
                    quantity = excluded.quantity
                """,
                (agg["report_date"], agg["nm_id"], agg["sa_name"], agg["quantity"], agg["retail_amount"],
                 agg["ppvz_sales_commission"], agg["ppvz_for_pay"]),
            )
        conn.commit()
    finally:
        conn.close()
    return len(aggregated)

def _log_sync(sync_type: str, status: str, message: str) -> None:
    conn = get_connection()
    try:
        conn.execute("INSERT INTO sync_log (sync_type, status, message) VALUES (?, ?, ?)", (sync_type, status, message))
        conn.commit()
    finally:
        conn.close()

def sync_sales(token: str, date_from: str, date_to: str, progress_cb=None) -> dict:
    if progress_cb: progress_cb(f"Запрос продаж {date_from} → {date_to}...")
    client = WBAPIClient(token)
    rows = client.fetch_sales(date_from, date_to)
    if progress_cb: progress_cb(f"Получено {len(rows)} строк. Сохраняем...")
    saved = save_sales_to_db(rows)
    _log_sync("sales", "ok", f"{date_from}..{date_to}: {saved} агрегатов")
    if progress_cb: progress_cb(f"Готово: сохранено {saved} строк")
    return {"rows": len(rows), "saved": saved}

def load_recent_sales(limit: int = 500) -> list[dict]:
    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM sales ORDER BY report_date DESC, nm_id LIMIT ?", (limit,)).fetchall()]
    finally:
        conn.close()

def sync_products_from_api(token: str, progress_cb=None) -> int:
    if progress_cb: progress_cb("Запрос карточек из WB...")
    client = WBAPIClient(token)
    cards = client.fetch_cards()
    if progress_cb: progress_cb(f"Получено {len(cards)} карточек. Сохраняем...")
    conn = get_connection()
    try:
        for card in cards:
            nm_id = card.get("nmID")
            if not nm_id: continue
            conn.execute(
                "INSERT INTO products (nm_id, vendor_code, title, updated_at) VALUES (?, ?, ?, datetime('now')) ON CONFLICT(nm_id) DO UPDATE SET vendor_code = excluded.vendor_code, title = excluded.title, updated_at = datetime('now')",
                (int(nm_id), card.get("vendorCode"), card.get("title")),
            )
        conn.commit()
    finally:
        conn.close()
    _log_sync("products", "ok", f"сохранено {len(cards)} карточек")
    if progress_cb: progress_cb(f"Сохранено {len(cards)} карточек")
    return len(cards)

def save_ads_to_db(stats: list[dict]) -> int:
    conn = get_connection()
    saved = 0
    try:
        for campaign in stats:
            campaign_id = campaign.get("advertId") or campaign.get("id") or 0
            campaign_name = campaign.get("campaignName") or str(campaign_id)
            for day in campaign.get("days", []):
                day_date = (day.get("date") or "")[:10]
                if not day_date: continue
                sum_rub = float(day.get("sum") or 0)
                sum_price = float(day.get("sum_price") or 0)
                if sum_rub == 0 and "apps" in day:
                    sum_rub = sum(float(app.get("sum") or 0) for app in day["apps"])
                    sum_price = sum(float(app.get("sum_price") or 0) for app in day["apps"])
                if sum_rub == 0 and "apps" in day:
                    for app in day["apps"]:
                        for nm in app.get("nms", []):
                            sum_rub += float(nm.get("sum") or 0)
                            sum_price += float(nm.get("sum_price") or 0)
                if sum_rub == 0 and sum_price == 0: continue
                conn.execute(
                    "INSERT OR REPLACE INTO ads (report_date, campaign_id, campaign_name, nm_id, sum_rub, sum_price) VALUES (?, ?, ?, ?, ?, ?)",
                    (day_date, campaign_id, campaign_name, 0, sum_rub, sum_price),
                )
                saved += 1
        conn.commit()
    finally:
        conn.close()
    return saved

def sync_ads(token: str, date_from: str, date_to: str, progress_cb=None) -> dict:
    if progress_cb: progress_cb("Получаем список кампаний...")
    client = WBAPIClient(token)
    campaigns = client.fetch_campaigns()
    
    campaign_ids = []
    for c in campaigns:
        cid = c.get("id")
        if cid:
            campaign_ids.append(cid)

    if not campaign_ids:
        if progress_cb: progress_cb("Кампаний не найдено")
        _log_sync("ads", "ok", "кампаний нет")
        return {"campaigns": 0, "rows": 0}

    if progress_cb:
        progress_cb(f"Найдено {len(campaign_ids)} кампаний. Запрашиваем статистику...")

    all_stats: list[dict] = []
    for i in range(0, len(campaign_ids), 50):
        chunk = campaign_ids[i:i + 50]
        all_stats.extend(client.fetch_ads_stats(chunk, date_from, date_to))

    if progress_cb:
        progress_cb(f"Получено {len(all_stats)} кампаний со статистикой. Сохраняем...")

    saved = save_ads_to_db(all_stats)
    _log_sync("ads", "ok", f"{date_from}..{date_to}: {saved} строк")

    if progress_cb:
        progress_cb(f"Сохранено {saved} строк рекламы")

    return {"campaigns": len(campaign_ids), "rows": saved}

def sync_financial_report(token: str, date_from: str, date_to: str, progress_cb=None) -> int:
    if progress_cb: progress_cb(f"Запрос финансового отчёта {date_from} → {date_to}...")
    client = WBAPIClient(token)
    
    # РАСШИРЯЕМ ПЕРИОД ЗАПРОСА НА 7 ДНЕЙ В ОБЕ СТОРОНЫ
    dt_from = datetime.strptime(date_from, "%Y-%m-%d").date()
    dt_to = datetime.strptime(date_to, "%Y-%m-%d").date()
    api_date_from = (dt_from - timedelta(days=7)).isoformat()
    api_date_to = (dt_to + timedelta(days=7)).isoformat()
    
    rows = client.fetch_financial_report(api_date_from, api_date_to)
    if progress_cb: progress_cb(f"Получено {len(rows)} строк. Обновляем БД...")

    agg: dict[tuple[str, int], dict] = {}
    dates_covered = set()

    for row in rows:
        nm_id = row.get("nmId") or 0
        
        # ИСПРАВЛЕНИЕ: Берем rrDate, но если его нет (для услуг), берем saleDt
        dt_str = (row.get("rrDate") or row.get("saleDt") or "")[:10]
        if not dt_str: continue
        
        # ФИЛЬТРУЕМ только те даты, которые входят в запрошенный период
        if not (date_from <= dt_str <= date_to):
            continue

        dates_covered.add(dt_str)
        op_name = row.get("sellerOperName")
        
        qty = 0
        return_qty = 0
        
        row_for_pay = float(row.get("ppvzForPay") or row.get("forPay") or 0)
        
        if op_name == "Продажа":
            qty = abs(int(float(row.get("quantity") or 0)))
            row_for_pay = abs(row_for_pay)
        elif op_name == "Возврат":
            return_qty = abs(int(float(row.get("quantity") or 0)))
            qty = -return_qty
            row_for_pay = -abs(row_for_pay)

        delivery = float(row.get("deliveryService") or 0)
        storage = float(row.get("paidStorage") or 0)
        processing = float(row.get("paidAcceptance") or 0)
        penalty = float(row.get("penalty") or 0)
        other = 0.0
        correction = 0.0
        sa_name = row.get("vendorCode") or ""

        key = (dt_str, nm_id)
        if key not in agg:
            agg[key] = {"qty": 0, "return_qty": 0, "for_pay": 0.0, "delivery": 0.0, "storage": 0.0, "processing": 0.0, "other": 0.0, "penalty": 0.0, "correction": 0.0, "sa_name": sa_name}
        
        agg[key]["qty"] += qty
        agg[key]["return_qty"] += return_qty
        agg[key]["for_pay"] += row_for_pay
        agg[key]["delivery"] += delivery
        agg[key]["storage"] += storage
        agg[key]["processing"] += processing
        agg[key]["other"] += other
        agg[key]["penalty"] += penalty
        agg[key]["correction"] += correction
        if not agg[key]["sa_name"] and sa_name: agg[key]["sa_name"] = sa_name

    conn = get_connection()
    updated = 0
    try:
        if dates_covered:
            placeholders = ",".join("?" for _ in dates_covered)
            conn.execute(f"DELETE FROM sales WHERE report_date IN ({placeholders})", tuple(dates_covered))

        for (dt_str, nm_id), data in agg.items():
            payout = data["for_pay"] - data["delivery"] - data["storage"] - data["processing"] - data["other"] - data["penalty"] - data["correction"]
            conn.execute(
                """
                INSERT INTO sales (report_date, nm_id, sa_name, quantity, return_qty, retail_amount, ppvz_sales_commission, ppvz_for_pay, delivery_rub, storage_fee, processing_fee, other_deductions, penalty_fee, wb_correction)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?)
                """,
                (dt_str, nm_id, data["sa_name"], data["qty"], data["return_qty"], data["for_pay"], payout, data["delivery"], data["storage"], data["processing"], data["other"], data["penalty"], data["correction"])
            )
            updated += 1
        conn.commit()
    finally:
        conn.close()
        
    _log_sync("financial", "ok", f"{date_from}..{date_to}: обновлено {updated} строк")
    if progress_cb: progress_cb(f"Обновлено {updated} записей")
    return updated

def sync_recent_days(token: str, days: int = 3, progress_cb=None) -> None:
    today = date.today()
    date_from = (today - timedelta(days=days)).isoformat()
    date_to = today.isoformat()

    if progress_cb: progress_cb(f"Автосинхронизация за {days} дн...")
    
    try: sync_sales(token, date_from, date_to, progress_cb)
    except Exception: pass
    try: sync_ads(token, date_from, date_to, progress_cb)
    except Exception: pass
    try: sync_financial_report(token, date_from, date_to, progress_cb)
    except Exception: pass
    try: sync_products_from_api(token, progress_cb)
    except Exception: pass