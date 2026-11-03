from app.wb_api import WBAPIClient
from app.secure_token import load_token

def main():
    token = load_token()
    client = WBAPIClient(token)
    
    # Берем строго 19 октября
    date_from = "2026-10-19"
    date_to = "2026-10-19"
    
    print(f"Запрашиваем данные у WB за {date_from}...")
    rows = client.fetch_financial_report(date_from, date_to)
    
    # Итоговые переменные
    total_for_pay = 0
    total_delivery = 0
    total_storage = 0
    total_processing = 0
    total_other = 0
    total_penalty = 0
    total_correction = 0
    
    for r in rows:
        # Складываем все значения из всех строк за этот день
        total_for_pay += float(r.get("forPay") or 0)
        total_delivery += float(r.get("deliveryService") or 0)
        total_storage += float(r.get("paidStorage") or 0)
        total_processing += float(r.get("paidAcceptance") or 0)
        total_other += float(r.get("deduction") or 0)
        total_penalty += float(r.get("penalty") or 0)
        total_correction += float(r.get("wbCorrection") or 0)
        
    payout = total_for_pay - total_delivery - total_storage - total_processing - total_other - total_penalty - total_correction

    print("\n--- РЕЗУЛЬТАТЫ ЗА 19 ОКТЯБРЯ ---")
    print(f"К перечислению за товар (forPay): {total_for_pay:.2f}")
    print(f"Стоимость доставки: {total_delivery:.2f}")
    print(f"Стоимость хранения: {total_storage:.2f}")
    print(f"Стоимость обработки: {total_processing:.2f}")
    print(f"Прочие удержания: {total_other:.2f}")
    print(f"Штрафы: {total_penalty:.2f}")
    print(f"Корректировка: {total_correction:.2f}")
    print(f"-------------------------------")
    print(f"ИТОГО К ОПЛАТЕ: {payout:.2f}")

if __name__ == "__main__":
    main()