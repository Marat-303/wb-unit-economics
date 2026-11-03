from app.db import get_connection
from app.secure_token import load_token
from app.sync import sync_financial_report

def main():
    token = load_token()
    if not token:
        print("Нет токена")
        return

    # 1. Принудительно удаляем старые данные за Июнь и Июль из базы
    print("Очищаем старые данные за Июнь и Июль...")
    conn = get_connection()
    try:
        conn.execute("DELETE FROM sales WHERE report_date LIKE '2026-06-%'")
        conn.execute("DELETE FROM sales WHERE report_date LIKE '2026-07-%'")
        conn.commit()
    finally:
        conn.close()

    # 2. Загружаем заново с группировкой по дате продажи (saleDt)
    print("Синхронизируем Июнь...")
    sync_financial_report(token, "2026-06-01", "2026-06-30")
    
    print("Синхронизируем Июль...")
    sync_financial_report(token, "2026-07-01", "2026-07-31")
    
    print("Готово! Перезапустите приложение и проверьте статистику.")

if __name__ == "__main__":
    main()