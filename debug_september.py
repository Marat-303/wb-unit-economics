from app.wb_api import WBAPIClient
from app.secure_token import load_token
from datetime import datetime, timedelta

def main():
    token = load_token()
    client = WBAPIClient(token)
    
    date_from = "2026-09-01"
    date_to = "2026-09-30"
    
    # Расширяем период запроса (как в новом коде)
    dt_from = datetime.strptime(date_from, "%Y-%m-%d").date()
    dt_to = datetime.strptime(date_to, "%Y-%m-%d").date()
    api_date_from = (dt_from - timedelta(days=7)).isoformat()
    api_date_to = (dt_to + timedelta(days=7)).isoformat()
    
    print(f"Запрашиваем данные с {api_date_from} по {api_date_to}...")
    rows = client.fetch_financial_report(api_date_from, api_date_to)
    
    total_qty = 0
    total_pay = 0
    
    for r in rows:
        dt_str = (r.get("saleDt") or "")[:10]
        if not dt_str: continue
        
        # Фильтруем только сентябрь
        if not (date_from <= dt_str <= date_to): continue
        
        op = r.get("sellerOperName")
        
        if op == "Продажа":
            qty = abs(int(float(r.get("quantity") or 0)))
            pay = abs(float(r.get("ppvzForPay") or r.get("forPay") or 0))
        elif op == "Возврат":
            qty = -abs(int(float(r.get("quantity") or 0)))
            pay = -abs(float(r.get("ppvzForPay") or r.get("forPay") or 0))
        else:
            qty = 0
            pay = 0.0
            
        delivery = float(r.get("deliveryService") or 0)
        storage = float(r.get("paidStorage") or 0)
        processing = float(r.get("paidAcceptance") or 0)
        penalty = float(r.get("penalty") or 0)
        
        payout = pay - delivery - storage - processing - penalty
        
        total_qty += qty
        total_pay += payout
        
    print("\n--- РЕЗУЛЬТАТ РАСЧЕТА ---")
    print(f"Количество: {total_qty} шт.")
    print(f"К перечислению: {total_pay:.2f} ₽")
    print(f"Ожидаемая цифра из скриншота WB: 159 192.87 ₽")

if __name__ == "__main__":
    main()