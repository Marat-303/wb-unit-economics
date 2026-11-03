from app.wb_api import WBAPIClient
from app.secure_token import load_token

def main():
    token = load_token()
    client = WBAPIClient(token)
    date_str = "2026-10-27"
    
    print(f"--- 1. ЗАПРАШИВАЕМ ПРОДАЖИ ЗА {date_str} ---")
    sales_rows = client.fetch_sales(date_str, date_str)
    total_for_pay = sum(float(r.get("forPay") or 0) for r in sales_rows)
    print(f"Строк: {len(sales_rows)}. Сумма forPay: {total_for_pay:.2f} ₽")
    
    print(f"\n--- 2. ЗАПРАШИВАЕМ ФИНАНСОВЫЙ ОТЧЕТ ЗА {date_str} ---")
    fin_rows = client.fetch_financial_report(date_str, date_str)
    print(f"Строк: {len(fin_rows)}")
    
    if len(fin_rows) > 0:
        total_ppvz = 0
        total_delivery = 0
        for r in fin_rows:
            total_ppvz += float(r.get("ppvzForPay") or r.get("forPay") or 0)
            total_delivery += float(r.get("deliveryService") or 0)
        print(f"Сумма ppvzForPay/forPay: {total_ppvz:.2f} ₽")
        print(f"Сумма deliveryService: {total_delivery:.2f} ₽")
    else:
        print("⚠ API вернул ПУСТОЙ список за эту дату. Данные еще не сформированы на стороне WB.")

if __name__ == "__main__":
    main()