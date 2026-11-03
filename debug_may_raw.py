from app.wb_api import WBAPIClient
from app.secure_token import load_token
import json

def main():
    token = load_token()
    if not token:
        print("Нет токена")
        return

    client = WBAPIClient(token)
    
    print("Запрашиваем данные за Май 2026...")
    rows = client.fetch_financial_report("2026-05-01", "2026-05-31")
    
    print(f"\nВсего получено строк от API: {len(rows)}")
    
    if len(rows) == 0:
        print("⚠ API вернул пустой список. Возможно, за этот период данные еще не сформированы или есть ограничение по датам.")
        return
        
    print("\n=== СОДЕРЖИМОЕ ПЕРВОЙ СТРОКИ ===")
    # Печатаем первые 2000 символов первой строки, чтобы понять структуру
    print(json.dumps(rows[0], ensure_ascii=False, indent=2)[:2000])
    print("===============================")
    
    # Пытаемся сложить разные поля, чтобы понять, где лежит выручка
    sum_for_pay = 0.0
    sum_ppvz_for_pay = 0.0
    sum_retail = 0.0
    
    sales_count = 0
    returns_count = 0

    for r in rows:
        op = r.get("sellerOperName")
        if op == "Продажа":
            sales_count += 1
        elif op == "Возврат":
            returns_count += 1
            
        sum_for_pay += float(r.get("forPay") or 0)
        sum_ppvz_for_pay += float(r.get("ppvzForPay") or 0)
        sum_retail += float(r.get("retailAmount") or 0)

    print(f"\nВсего строк 'Продажа': {sales_count}")
    print(f"Всего строк 'Возврат': {returns_count}")
    print(f"\nСумма поля 'forPay': {sum_for_pay:,.2f} ₽")
    print(f"Сумма поля 'ppvzForPay': {sum_ppvz_for_pay:,.2f} ₽")
    print(f"Сумма поля 'retailAmount': {sum_retail:,.2f} ₽")
    print(f"\nЦифра из вашего скриншота WB: 736 052.89 ₽")

if __name__ == "__main__":
    main()