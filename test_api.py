import sys
from app.secure_token import save_token, load_token
from app.wb_api import WBAPIClient, WBAPIError


def main() -> int:
    token = input("Вставьте WB API-токен: ").strip()
    if not token:
        print("Токен не введён")
        return 1

    save_token(token)
    print("Токен сохранён в Windows Credential Manager")

    client = WBAPIClient(load_token())
    try:
        pong = client.ping()
        print(f"Ping: {pong}")
    except WBAPIError as e:
        print(f"Ошибка ping: {e}")
        return 1

    try:
        sales = client.fetch_sales("2026-10-20", "2026-10-24")
        print(f"Продажи: получено строк — {len(sales)}")
        if sales:
            print("Пример строки:", {k: sales[0].get(k) for k in ("nmId", "saleID", "totalPrice", "forPay")})
    except WBAPIError as e:
        print(f"Ошибка продаж: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())