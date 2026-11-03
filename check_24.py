from app.wb_api import WBAPIClient
from app.secure_token import load_token

def main():
    date_str = "2026-10-24"
    token = load_token()
    client = WBAPIClient(token)
    rows = client.fetch_financial_report(date_str, date_str)
    
    print(f"\n--- ДЕТАЛИЗАЦИЯ ЗА {date_str} ---")
    
    has_returns = False
    
    for r in rows:
        op = r.get("sellerOperName")
        qty = int(float(r.get("quantity") or 0))
        ppvz = float(r.get("ppvzForPay") or r.get("forPay") or 0)
        
        # Выводим только строки, где есть количество или сумма (игнорируем пустые услуги)
        if qty != 0 or ppvz != 0:
            print(f"Операция: {op:15} | Кол-во: {qty:2} | К перечисл: {ppvz:8.2f}")
            
            if op == "Возврат":
                has_returns = True

    print("-" * 50)
    if has_returns:
        print("⚠️ ВНИМАНИЕ: За этот день БЫЛИ возвраты (см. строки 'Возврат').")
    else:
        print("✅ Возвратов за этот день НЕ БЫЛО.")

if __name__ == "__main__":
    main()