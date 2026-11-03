from app.wb_api import WBAPIClient
from app.secure_token import load_token

def main():
    token = load_token()
    if not token:
        print("Нет токена")
        return

    client = WBAPIClient(token)
    # Берем период с 1 по 25 октября
    date_from = "2026-10-01"
    date_to = "2026-10-25"
    
    print(f"Запрашиваем финансовый отчет за {date_from} - {date_to}...")
    rows = client.fetch_financial_report(date_from, date_to)
    
    print(f"\nВсего строк в отчете: {len(rows)}")
    
    # Собираем уникальные названия операций, чтобы понять, как WB называет возвраты
    operations = set()
    returns_found = 0

    print("\n--- ПОИСК ВОЗВРАТОВ ---")
    for r in rows:
        op = r.get("sellerOperName")
        operations.add(op)
        
        # Ищем любые упоминания возврата
        if op and "Возврат" in op:
            returns_found += 1
            nm_id = r.get("nmId")
            qty = r.get("quantity")
            rr_date = r.get("rrDate")
            sale_date = r.get("saleDt")
            for_pay = r.get("ppvzForPay") or r.get("forPay")
            
            print(f"Найден возврат!")
            print(f"  Операция: {op}")
            print(f"  Артикул: {nm_id}")
            print(f"  Кол-во: {qty}")
            print(f"  Дата продажи (saleDt): {sale_date}")
            print(f"  Дата проводки (rrDate): {rr_date}")
            print(f"  К перечисл: {for_pay}")
            print("-" * 30)

    if returns_found == 0:
        print("⚠ В API вообще НЕТ строк со словом 'Возврат' за этот период.")
    
    print("\n--- ВСЕ ТИПЫ ОПЕРАЦИЙ В ОТЧЕТЕ ---")
    for op in sorted(operations):
        if op: # Пропускаем пустые
            print(f"- {op}")

if __name__ == "__main__":
    main()