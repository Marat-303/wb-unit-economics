import time
import traceback
from PyQt6.QtCore import QThread, pyqtSignal
from app.secure_token import load_token
from app.wb_ad_api import WBAdAPI
from app.telegram_notifier import send_telegram_message

class AdBidderWorker(QThread):
    log_signal = pyqtSignal(str)
    products_updated = pyqtSignal(list)

    def __init__(self, advert_id: int, target_drr: float = 15.0, max_bid: float = 25.0,
                 step_up: float = 5.0, step_down: float = 3.0, interval_min: int = 10):
        super().__init__()
        self.advert_id = advert_id
        self.target_drr = target_drr
        self.max_bid = max_bid
        self.step_up = step_up
        self.step_down = step_down
        self.interval_sec = interval_min * 60
        self.running = True

    def run(self):
        self.log_signal.emit(f"🤖 Автобиддер (Общий ДРР) запущен. Цель: {self.target_drr}%, макс. ставка: {self.max_bid} ₽.")
        while self.running:
            try:
                self._process_cycle()
            except Exception as e:
                self.log_signal.emit(f"❌ Критическая ошибка: {e}")
                print(traceback.format_exc())
            for _ in range(self.interval_sec):
                if not self.running: break
                time.sleep(1)

    def _process_cycle(self):
        token = load_token()
        if not token:
            self.log_signal.emit("⚠️ Токен не найден.")
            return
        api = WBAdAPI(token)
        try:
            products = api.get_campaign_products(self.advert_id)
        except Exception as e:
            self.log_signal.emit(f"❌ Ошибка получения товаров: {e}")
            return
        if not products:
            self.log_signal.emit("ℹ️ В кампании не найдено товаров.")
            return

        initial_state = [{
            "nm_id": p["nm_id"],
            "old_bid_rub": p["current_bid_rub"],
            "new_bid_rub": p["current_bid_rub"],
            "campaign_drr": None,
            "status": "Загрузка статистики..."
        } for p in products]
        self.products_updated.emit(initial_state)

        nm_ids = [p["nm_id"] for p in products]
        try:
            stats = api.get_campaign_stats(self.advert_id, nm_ids, days=7)
        except Exception as e:
            self.log_signal.emit(f"❌ Ошибка API: {e}")
            return
            
        total_spend = stats["total_spend"]
        total_revenue = stats["total_revenue"]
        drr = stats["drr"]
        
        drr_text = "∞" if drr == 999.9 else f"{drr}%"
        self.log_signal.emit(f"📊 За 7 дней: Расход {total_spend:.2f} ₽, Выручка {total_revenue:.2f} ₽, ДРР {drr_text}")

        updated_products = []
        actions_to_apply = []

        for p in products:
            nm_id = p["nm_id"]
            current_bid = p["current_bid_rub"]
            
            status = "—"
            new_bid = current_bid
            action = None

            # 1. ЖЕСТКИЙ ЛИМИТ (Если ставка превышает Макс. ставку, срезаем её принудительно)
            if current_bid > self.max_bid:
                new_bid = self.max_bid
                status = f"⬇️ Снижение до лимита {new_bid:.2f} ₽"
                action = new_bid
            # 2. Логика по ДРР (если лимит не превышен)
            elif total_spend == 0:
                status = "⏸ Нет расхода (ставка не меняется)"
            elif total_revenue == 0:
                if current_bid > 1.0:
                    new_bid = max(current_bid * (1 - self.step_down / 100), 1.0)
                    if new_bid < current_bid:
                        status = f"⬇️ Снижение (Нет продаж!)"
                        action = new_bid
                    else:
                        status = "Мин. ставка"
                else:
                    status = "Мин. ставка"
            else:
                if drr > self.target_drr + 2.0:
                    if current_bid > 1.0:
                        new_bid = max(current_bid * (1 - self.step_down / 100), 1.0)
                        if new_bid < current_bid:
                            status = f"⬇️ Снижение (ДРР {drr}%)"
                            action = new_bid
                        else:
                            status = "Уже мин."
                    else:
                        status = "Мин. ставка"
                elif drr < self.target_drr - 2.0:
                    if current_bid < self.max_bid:
                        new_bid = min(current_bid * (1 + self.step_up / 100), self.max_bid)
                        if new_bid > current_bid:
                            status = f"⬆️ Повышение (ДРР {drr}%)"
                            action = new_bid
                        else:
                            status = "Уже макс."
                    else:
                        status = f"⚠️ Лимит {self.max_bid} ₽"
                else:
                    status = f"✅ В норме (ДРР {drr}%)"

            updated_products.append({
                "nm_id": nm_id,
                "old_bid_rub": current_bid,
                "new_bid_rub": new_bid,
                "campaign_drr": drr,
                "status": status
            })
            
            if action:
                actions_to_apply.append((nm_id, action))

        self.products_updated.emit(updated_products)

        for idx, (nm_id, new_bid) in enumerate(actions_to_apply):
            if not self.running: break
            success = api.update_bid(self.advert_id, nm_id, new_bid)
            if success:
                log_msg = f"Товар {nm_id}: ставка изменена на {new_bid:.2f} ₽"
                self.log_signal.emit(f"🔄 {log_msg}")
                send_telegram_message(f"🤖 <b>Автобиддер (ДРР)</b>\n{log_msg}")
                for up in updated_products:
                    if up["nm_id"] == nm_id:
                        up["new_bid_rub"] = new_bid
            else:
                self.log_signal.emit(f"❌ Не удалось изменить ставку для {nm_id}")
                for up in updated_products:
                    if up["nm_id"] == nm_id:
                        up["status"] = "❌ Ошибка смены ставки"
            
            if self.running and idx < len(actions_to_apply) - 1:
                self.log_signal.emit("⏳ Ожидание 30 сек. (лимиты API)...")
                for _ in range(30):
                    if not self.running: break
                    time.sleep(1)

        self.products_updated.emit(updated_products)

    def stop(self):
        self.running = False