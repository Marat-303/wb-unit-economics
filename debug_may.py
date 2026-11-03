from app.wb_api import WBAPIClient
from app.secure_token import load_token
from collections import defaultdict

def main():
    token = load_token()
    if not token:
        print("Нет токена")
        return

    client = WBAPIClient(token)
    date_from = "2026-05-01"
    date_to = "2026-05-31"
    
    print(f"Запрашиваем данные за Май ({date_from} - {date_to})...")
    rows = client.fetch_financial_report(date_from, date_to)
    
    sum_by_rr = 0.0
    sum_by_sale = 0.0
    
    for r in rows:
        op = r.get("sellerOperName")
        if op == "Продажа":
            val = abs(float(r.get("ppvzForPay") or 0))
        elif op == "Возврат":
            val = -abs(float(r.get("ppvzForPay") or 0))
        else:
            continue
            
        rr_date = (r.get("rrDate") or "")[:10]
        sale_date = (r.get("saleDt") or "")[:10]
        
        # Суммируем по дате проводки (как в нашем приложении)
        if rr_date.startswith("2026-05"):
            sum_by_rr += val
            
        # Суммируем по дате продажи (как в отчетах WB)
        if sale_date.startswith("2026-05"):
            sum_by_sale += val

    print("\n--- РЕЗУЛЬТАТЫ ЗА МАЙ ---")
    print(f"Сумма по дате ПРОВОДКИ (rrDate, как в нашем приложении): {sum_by_rr:,.2f} ₽")
    print(f"Сумма по дате ПРОДАЖИ (saleDt, как в отчете WB): {sum_by_sale:,.2f} ₽")
    print(f"Сумма из вашего скриншота WB: 736 052.89 ₽")

if __name__ == "__main__":
    main()