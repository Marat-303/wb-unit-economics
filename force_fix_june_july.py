import time
from app.db import get_connection
from app.secure_token import load_token
from app.sync import sync_financial_report

def main():
    token = load_token()
    if not token:
        print("Нет токена")
        return

    print("1. Очищаем старые данные за Июнь и Июль...")
    conn = get_connection()
    try:
        conn.execute("DELETE FROM sales WHERE report_date LIKE '2026-06-%' OR report_date LIKE '2026-07-%'")
        conn.commit()
    finally:
        conn.close()

    print("2. Синхронизируем Июнь...")
    sync_financial_report(token, "2026-06-01", "2026-06-30")
    
    print("⏳ Ждем 65 секунд (лимит API)...")
    time.sleep(65)
    
    print("3. Синхронизируем Июль...")
    sync_financial_report(token, "2026-07-01", "2026-07-31")
    
    print("✅ Готово! Зайдите в приложение на вкладку «Статистика» и нажмите «Обновить».")

if __name__ == "__main__":
    main()