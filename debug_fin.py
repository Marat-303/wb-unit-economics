from app.wb_api import WBAPIClient
from app.secure_token import load_token

token = load_token()
client = WBAPIClient(token)
# Берем только 1 октября
rows = client.fetch_financial_report("2026-10-01", "2026-10-01")

total_forpay = 0
total_delivery = 0
total_storage = 0
total_acceptance = 0
total_acquiring = 0
total_penalty = 0
total_deduction = 0

for r in rows:
    total_forpay += float(r.get("forPay") or 0)
    total_delivery += float(r.get("deliveryService") or 0)
    total_storage += float(r.get("paidStorage") or 0)
    total_acceptance += float(r.get("paidAcceptance") or 0)
    total_acquiring += float(r.get("acquiringFee") or 0)
    total_penalty += float(r.get("penalty") or 0)
    total_deduction += float(r.get("deduction") or 0)

print("--- СУММЫ ИЗ API ЗА 1 ОКТЯБРЯ ---")
print(f"forPay: {total_forpay}")
print(f"Доставка: {total_delivery}")
print(f"Хранение: {total_storage}")
print(f"Обработка: {total_acceptance}")
print(f"Эквайринг: {total_acquiring}")
print(f"Штрафы: {total_penalty}")
print(f"Прочие удержания: {total_deduction}")
print("--- ВАРИАНТЫ РАСЧЕТА ---")
print(f"Вариант 1 (forPay - дост - хран - обраб - экв): {total_forpay - total_delivery - total_storage - total_acceptance - total_acquiring}")
print(f"Вариант 2 (forPay - дост - хран - обраб): {total_forpay - total_delivery - total_storage - total_acceptance}")
print(f"Вариант 3 (Вариант 1 - штрафы): {total_forpay - total_delivery - total_storage - total_acceptance - total_acquiring - total_penalty}")
print(f"Вариант 4 (Вариант 1 - прочие): {total_forpay - total_delivery - total_storage - total_acceptance - total_acquiring - total_deduction}")