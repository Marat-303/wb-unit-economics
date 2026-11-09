import time
import traceback
import datetime
from PyQt6.QtCore import QThread, pyqtSignal
from app.secure_token import load_token
from app.wb_ad_api import WBAdAPI
from app.telegram_notifier import send_telegram_message

class AdBidderWorker(QThread):
    log_signal = pyqtSignal(str)
    products_updated = pyqtSignal(list)

    def __init__(self, advert_id: int, product_settings: dict, step_up: float = 5.0, step_down: float = 3.0, 
                 interval_min: int = 5, enable_night_mode: bool = False, night_bid: float = 10.0):
        super().__init__()
        self.advert_id = advert_id
        self.product_settings = product_settings # { "nm_id": {"max_bid": X, "target_pos": Y} }
        self.step_up = step_up
        self.step_down = step_down
        self.interval_sec = interval_min * 60
        self.enable_night_mode = enable_night_mode
        self.night_bid = night_bid
        self.running = True

    def run(self):
        self.log_signal.emit(f"🤖 Автобиддер (Индивидуальные настройки) запущен.")
        if self.enable_night_mode:
            self.log_signal.emit(f"🌙 Ночной режим ВКЛ: с 00:00 до 06:00 ставка будет падать до {self.night_bid} ₽.")
            
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

        now_hour = datetime.datetime.now().hour
        is_night = self.enable_night_mode and (now_hour < 6)

        initial_state = []
        for p in products:
            initial_state.append({
                "nm_id": p["nm_id"],
                "old_bid_rub": p["current_bid_rub"],
                "new_bid_rub": p["current_bid_rub"],
                "position": None,
                "status": "Загрузка..." if not is_night else "Ночной режим..."
            })
        self.products_updated.emit(initial_state)

        positions = {}
        if not is_night:
            nm_ids = [p["nm_id"] for p in products]
            positions = api.get_product_positions(self.advert_id, nm_ids)
        else:
            self.log_signal.emit(f"🌙 Ночной режим. Проверка ставок...")

        updated_products = []
        actions_to_apply = []

        for p in products:
            nm_id = p["nm_id"]
            current_bid = p["current_bid_rub"]
            pos = positions.get(nm_id)
            
            # ЖЕСТКО ПРИВОДИМ К ТИПАМ ДЛЯ НАДЕЖНОСТИ
            p_sett = self.product_settings.get(str(nm_id), {"max_bid": 30.0, "target_pos": 10})
            p_max_bid = float(p_sett.get("max_bid", 30.0))
            p_target_pos = int(p_sett.get("target_pos", 10))

            status = "—"
            new_bid = current_bid
            action = None

            if is_night:
                # === НОЧНОЙ РЕЖИМ ===
                new_bid = self.night_bid
                if abs(current_bid - new_bid) > 0.01:
                    status = f"🌙 Снижение на ночь до {new_bid:.2f} ₽"
                    action = new_bid
                else:
                    status = "🌙 Ночной режим (ОК)"
            else:
                # === ДНЕВНОЙ РЕЖИМ ===
                if current_bid > p_max_bid:
                    new_bid = p_max_bid
                    status = f"⬇️ Снижение до лимита {new_bid:.2f} ₽"
                    action = new_bid
                elif pos is None:
                    status = "⚠️ Нет данных о позиции"
                elif pos > p_target_pos:
                    # Позиция хуже цели — повышаем
                    if current_bid < p_max_bid:
                        new_bid = min(current_bid * (1 + self.step_up / 100), p_max_bid)
                        if new_bid > current_bid:
                            status = f"⬆️ Повышение (Поз. {pos:.0f} > {p_target_pos})"
                            action = new_bid
                        else:
                            status = "Уже макс."
                    else:
                        status = f"⚠️ Лимит {p_max_bid:.2f} ₽"
                else:
                    # Позиция в топе или лучше — снижаем
                    if current_bid > 1.0:
                        new_bid = max(current_bid * (1 - self.step_down / 100), 1.0)
                        if new_bid < current_bid:
                            status = f"⬇️ Снижение (Поз. {pos:.0f} < {p_target_pos})"
                            action = new_bid
                        else:
                            status = "Уже мин."
                    else:
                        status = "Мин. ставка"

            updated_products.append({
                "nm_id": nm_id,
                "old_bid_rub": current_bid,
                "new_bid_rub": new_bid,
                "position": pos,
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
                send_telegram_message(f"🤖 <b>Автобиддер</b>\n{log_msg}")
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