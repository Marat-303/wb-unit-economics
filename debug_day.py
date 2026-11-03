from app.wb_api import WBAPIClient
from app.secure_token import load_token

def main():
    date_str = input("Введите дату, которая не сходится (например, 2026-10-15): ").strip()
    
    token = load_token()
    client = WBAPIClient(token)
    rows = client.fetch_financial_report(date_str, date_str)
    
    print(f"\n--- ВСЕ СТРОКИ ИЗ API ЗА {date_str} ---")
    
    total_qty = 0
    total_payout = 0
    
    for r in rows:
        op = r.get("sellerOperName")
        qty = int(float(r.get("quantity") or 0))
        ppvz = float(r.get("ppvzForPay") or r.get("forPay") or 0)
        
        # Выводим только те строки, где есть количество или сумма к перечислению
        if qty != 0 or ppvz != 0:
            print(f"Операция: {op:20} | Кол-во: {qty:3} | К перечисл: {ppvz:10.2f}")
            
            # Считаем итоги только для Продаж и Возвратов
            if op in ("Продажа", "Возврат"):
                total_qty += qty
                total_payout += ppvz

    print("-" * 50)
    print(f"ИТОГО по API (Продажи+Возвраты):")
    print(f"Количество: {total_qty} шт.")
    print(f"К перечислению: {total_payout:.2f} ₽")

if __name__ == "__main__":
    main()