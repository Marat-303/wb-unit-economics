from app.wb_api import WBAPIClient
from app.secure_token import load_token

def main():
    token = load_token()
    client = WBAPIClient(token)
    rows = client.fetch_financial_report("2026-10-24", "2026-10-24")
    
    total_retail = 0
    total_spp = 0
    total_comm = 0
    total_forpay = 0
    
    total_retail_sales = 0
    total_spp_sales = 0
    total_comm_sales = 0
    total_forpay_sales = 0

    for r in rows:
        retail = float(r.get("retailAmount") or 0)
        spp = float(r.get("spp") or 0)
        comm = float(r.get("ppvzSalesCommission") or 0)
        forpay = float(r.get("forPay") or 0)
        op = r.get("sellerOperName")

        total_retail += retail
        total_spp += spp
        total_comm += comm
        total_forpay += forpay

        if op in ("Продажа", "Возврат"):
            total_retail_sales += retail
            total_spp_sales += spp
            total_comm_sales += comm
            total_forpay_sales += forpay

    print("--- ВСЕ СТРОКИ ---")
    print(f"retailAmount: {total_retail:.2f}")
    print(f"spp: {total_spp:.2f}")
    print(f"ppvzSalesCommission: {total_comm:.2f}")
    print(f"forPay: {total_forpay:.2f}")
    print(f"retail - spp - comm: {total_retail - total_spp - total_comm:.2f}")
    
    print("\n--- ТОЛЬКО ПРОДАЖИ И ВОЗВРАТЫ ---")
    print(f"retailAmount: {total_retail_sales:.2f}")
    print(f"spp: {total_spp_sales:.2f}")
    print(f"ppvzSalesCommission: {total_comm_sales:.2f}")
    print(f"forPay: {total_forpay_sales:.2f}")
    print(f"retail - spp - comm: {total_retail_sales - total_spp_sales - total_comm_sales:.2f}")

if __name__ == "__main__":
    main()