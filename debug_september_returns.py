from app.wb_api import WBAPIClient
from app.secure_token import load_token

def main():
    token = load_token()
    if not token:
        print("Нет токена")
        return

    client = WBAPIClient(token)
    # Берем ВЕСЬ сентябрь
    date_from = "2026-09-01"
    date_to = "2026-09-30"
    
    print(f"Запрашиваем финансовый отчет за {date_from} - {date_to}...")
    rows = client.fetch_financial_report(date_from, date_to)
    
    print(f"\nВсего строк в отчете: {len(rows)}")
    
    returns_found = 0

    print("\n--- ПОИСК ВОЗВРАТОВ ЗА СЕНТЯБРЬ ---")
    for r in rows:
        op = r.get("sellerOperName")
        
        if op == "Возврат":
            returns_found += 1
            nm_id = r.get("nmId")
            qty = r.get("quantity")
            rr_date = r.get("rrDate")
            sale_date = r.get("saleDt")
            for_pay = r.get("ppvzForPay") or r.get("forPay")
            
            print(f"Возврат #{returns_found}")
            print(f"  Артикул: {nm_id}")
            print(f"  Кол-во: {qty}")
            print(f"  Дата продажи (saleDt): {sale_date}")
            print(f"  Дата проводки (rrDate): {rr_date}")
            print(f"  К перечисл: {for_pay}")
            print("-" * 30)

    if returns_found == 0:
        print("⚠ В API за сентябрь ВООБЩЕ НЕТ строк со словом 'Возврат'.")
    else:
        print(f"\nИТОГО найдено возвратов в API за сентябрь: {returns_found}")

if __name__ == "__main__":
    main()