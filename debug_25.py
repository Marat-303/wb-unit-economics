from app.wb_api import WBAPIClient
from app.secure_token import load_token

def main():
    token = load_token()
    client = WBAPIClient(token)
    rows = client.fetch_financial_report("2026-10-25", "2026-10-25")
    
    print(f"Всего строк в отчете: {len(rows)}\n")
    
    for r in rows:
        op_name = r.get("sellerOperName")
        qty = r.get("quantity")
        nm_id = r.get("nmId")
        retail = r.get("retailAmount")
        
        # Выводим только те строки, где есть количество, отличное от нуля
        if float(qty or 0) != 0:
            print(f"Операция: {op_name} | Артикул: {nm_id} | Кол-во: {qty} | Продажа: {retail}")

if __name__ == "__main__":
    main()