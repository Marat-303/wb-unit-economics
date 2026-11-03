import time
from app.secure_token import load_token
from app.sync import sync_financial_report

def main():
    token = load_token()
    if not token:
        print("Нет токена")
        return

    print("⏳ Ждем 65 секунд, чтобы обойти лимит Wildberries...")
    time.sleep(65)

    print("Синхронизируем Июль...")
    try:
        sync_financial_report(token, "2026-07-01", "2026-07-31")
        print("✅ Готово! Июль успешно загружен.")
        print("Зайдите в приложение на вкладку «Статистика» и нажмите «Обновить».")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()