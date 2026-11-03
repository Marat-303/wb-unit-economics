from apscheduler.schedulers.background import BackgroundScheduler
from app.secure_token import load_token
from app.sync import sync_recent_days
from app.db import get_connection

scheduler = BackgroundScheduler()

def log_to_db(sync_type: str, status: str, message: str):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO sync_log (sync_type, status, message) VALUES (?, ?, ?)",
            (sync_type, status, message),
        )
        conn.commit()
    finally:
        conn.close()

def daily_sync_job():
    """Фоновая задача: синхронизация за последние 3 дня."""
    token = load_token()
    if not token:
        log_to_db("auto", "error", "Нет токена для автосинхронизации")
        return

    try:
        # Синхронизируем последние 3 дня, чтобы захватить задержки API
        sync_recent_days(token, days=3)
        log_to_db("auto", "ok", "Успешно: автосинхронизация завершена")
        print("[Автосинхронизация] Успех")
    except Exception as e:
        log_to_db("auto", "error", str(e))
        print(f"[Автосинхронизация] Ошибка: {e}")

def setup_scheduler(hour: int = 6, minute: int = 0):
    scheduler.add_job(
        daily_sync_job, 
        'cron', 
        hour=hour, 
        minute=minute, 
        id='daily_sync', 
        replace_existing=True,
        misfire_grace_time=None,
    )
    if not scheduler.running:
        scheduler.start()