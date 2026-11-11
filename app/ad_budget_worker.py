import time
import datetime
from PyQt6.QtCore import QThread, pyqtSignal
from app.secure_token import load_token
from app.wb_ad_api import WBAdAPI
from app.ad_budget_db import get_all_limits, set_paused_date

class AdBudgetWorker(QThread):
    log_signal = pyqtSignal(str)
    refresh_ui_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        self.log_signal.emit("Фоновый контроль бюджета запущен (интервал: 5 мин).")
        
        while self.running:
            self._check_budgets()
            for _ in range(300):
                if not self.running:
                    break
                time.sleep(1)

    def _check_budgets(self):
        token = load_token()
        if not token:
            self.log_signal.emit("⚠️ Токен не найден. Проверка бюджета пропущена.")
            return

        api = WBAdAPI(token)
        limits = get_all_limits()
        
        if not limits:
            return
            
        campaign_ids = [row[0] for row in limits]
        
        try:
            stats = api.get_today_stats(campaign_ids)
        except Exception as e:
            self.log_signal.emit(f"❌ Ошибка статистики: {e}")
            return
        
        # Отправляем данные в интерфейс
        self.refresh_ui_signal.emit(stats)
        
        # Логика контроля бюджета
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        
        for row in limits:
            camp_id = row[0]
            limit = row[2]
            auto_pause = row[3]
            last_paused = row[4] or "" # Если None, делаем пустую строку
            
            current_spend = stats.get(camp_id, 0)

            if not auto_pause or limit <= 0:
                continue

            # 1. Превышен лимит — ставим на паузу (если еще не ставили сегодня)
            if current_spend > limit and last_paused != today_str:
                success = api.pause_campaign(camp_id)
                if success:
                    self.log_signal.emit(f"🛑 Кампания {camp_id} остановлена (Расход: {current_spend:.2f} > Лимит: {limit})")
                    set_paused_date(camp_id, today_str)
                    self.refresh_ui_signal.emit(stats)
                else:
                    self.log_signal.emit(f"⚠️ Не удалось остановить кампанию {camp_id} (ошибка API)")
            
            # 2. Наступил НОВЫЙ ДЕНЬ, а кампания была на паузе
            elif last_paused and last_paused != today_str:
                # Пытаемся запустить и ПРОВЕРЯЕМ результат
                success = api.start_campaign(camp_id)
                if success:
                    self.log_signal.emit(f"▶️ Новый день! Кампания {camp_id} успешно снята с паузы.")
                    set_paused_date(camp_id, "") # Очищаем дату паузы только при успехе
                    self.refresh_ui_signal.emit(stats)
                else:
                    self.log_signal.emit(f"⚠️ Не удалось запустить кампанию {camp_id} в новый день. Попробуем позже...")
                
            # 3. Расход в норме, но мы ее останавливали сегодня (например, подняли лимит)
            elif current_spend <= limit and last_paused == today_str:
                success = api.start_campaign(camp_id)
                if success:
                    self.log_signal.emit(f"▶️ Кампания {camp_id} возобновлена (Расход вернулся в норму)")
                    set_paused_date(camp_id, "")
                    self.refresh_ui_signal.emit(stats)

    def stop(self):
        self.running = False