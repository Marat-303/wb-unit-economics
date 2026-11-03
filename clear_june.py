from app.db import get_connection

def main():
    conn = get_connection()
    try:
        # Удаляем продажи и рекламу за июнь 2026
        conn.execute("DELETE FROM sales WHERE report_date LIKE '2026-06-%'")
        conn.execute("DELETE FROM ads WHERE report_date LIKE '2026-06-%'")
        conn.commit()
        print("✅ Данные за июнь 2026 года успешно удалены из базы.")
    except Exception as e:
        print(f"Ошибка при удалении: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()