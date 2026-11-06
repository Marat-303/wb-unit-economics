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
        # Обновили текст на 5 мин
        self.log_signal.emit("Фоновый контроль бюджета запущен (интервал: 5 мин).")
        
        while self.running:
            self._check_budgets()
            
            # Ждем 5 минут (300 секунд)
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
            last_paused = row[4]
            
            current_spend = stats.get(camp_id, 0)

            if not auto_pause or limit <= 0:
                continue

            if current_spend > limit and last_paused != today_str:
                success = api.pause_campaign(camp_id)
                if success:
                    self.log_signal.emit(f"🛑 Кампания {camp_id} остановлена (Расход: {current_spend:.2f} > Лимит: {limit})")
                    set_paused_date(camp_id, today_str)
                    self.refresh_ui_signal.emit(stats)
            
            elif current_spend <= limit and last_paused == today_str:
                success = api.start_campaign(camp_id)
                if success:
                    self.log_signal.emit(f"▶️ Кампания {camp_id} возобновлена (Расход вернулся в норму)")
                    set_paused_date(camp_id, "")
                    self.refresh_ui_signal.emit(stats)

    def stop(self):
        self.running = False