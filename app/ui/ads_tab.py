import json
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QMessageBox, QCheckBox, QLineEdit,
    QFrame, QScrollArea, QHeaderView, QSpinBox, QDoubleSpinBox, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
import datetime
from app.ad_budget_db import get_all_limits, update_limit, delete_limit, set_paused_date
from app.secure_token import load_token
from app.wb_ad_api import WBAdAPI
from app.ad_budget_worker import AdBudgetWorker
from app.ad_bidder_worker import AdBidderWorker

BIDDER_CONFIG_PATH = os.path.join("data", "bidder_config.json")

def load_bidder_config() -> dict:
    if os.path.exists(BIDDER_CONFIG_PATH):
        try:
            with open(BIDDER_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_bidder_config(config: dict):
    os.makedirs("data", exist_ok=True)
    with open(BIDDER_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

# ================= КАСТОМНАЯ КНОПКА С КРАСИВОЙ ПОДСКАЗКОЙ =================
class HoverButton(QPushButton):
    def __init__(self, text: str, tooltip_text: str, parent=None):
        super().__init__(text, parent)
        self.tooltip_text = tooltip_text
        
        self.tooltip = QLabel()
        self.tooltip.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.tooltip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tooltip.setStyleSheet("""
            background-color: #24292f; 
            color: #ffffff; 
            padding: 6px 10px; 
            border-radius: 6px; 
            font-size: 12px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        """)
        self.tooltip.hide()

    def enterEvent(self, event):
        super().enterEvent(event)
        self.tooltip.setText(self.tooltip_text)
        self.tooltip.adjustSize()
        
        btn_rect = self.rect()
        global_pos = self.mapToGlobal(btn_rect.bottomLeft())
        
        x = global_pos.x() + (btn_rect.width() - self.tooltip.width()) // 2
        y = global_pos.y() + 5
        
        self.tooltip.move(x, y)
        self.tooltip.show()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.tooltip.hide()
# ===========================================================================

class SettingsCard(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName("SettingsCard")
        self.setStyleSheet("""
            QFrame#SettingsCard {
                background-color: #ffffff;
                border: 1px solid #d0d7de;
                border-radius: 8px;
            }
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(12)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("""
            font-size: 14px; font-weight: bold; color: #1f2328;
            border: none; background: transparent;
        """)
        self.layout.addWidget(self.title_label)
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(10)
        self.layout.addLayout(self.content_layout)

class AdsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.current_stats = {}
        self.bidder_worker = None
        self.campaign_id = None
        
        self.setStyleSheet("""
            QWidget {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                font-size: 13px;
                color: #1f2328;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox {
                border: 1px solid #d0d7de;
                border-radius: 4px;
                padding: 4px 8px;
                background: #ffffff;
                color: #1f2328;
            }
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #0969da;
            }
            QPushButton {
                background: #f6f8fa;
                border: 1px solid #d0d7de;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: bold;
                color: #1f2328;
            }
            QPushButton:hover {
                background: #eaeef2;
                border: 1px solid #0969da;
            }
            QPushButton:pressed { background: #d0d7de; }
            QPushButton:disabled { color: #8c959f; background: #f6f8fa; }
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                gridline-color: #eaeef2;
                selection-background-color: #ddf4ff;
                selection-color: #0969da;
            }
            QHeaderView::section {
                background-color: #f6f8fa;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #d0d7de;
                border-right: 1px solid #d0d7de;
                font-weight: bold;
                color: #1f2328;
            }
            QCheckBox::indicator { width: 18px; height: 18px; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # КАРТОЧКА 1: Загрузка
        card_load = SettingsCard("Кампании Wildberries")
        load_row = QHBoxLayout()
        self.refresh_btn = QPushButton("🔄 Загрузить кампании из WB")
        self.refresh_btn.clicked.connect(self.load_campaigns)
        hint_label = QLabel("💡 Двойной клик по строке кампании загрузит товары и ставки")
        hint_label.setStyleSheet("color: #666; font-size: 12px;")
        load_row.addWidget(self.refresh_btn)
        load_row.addSpacing(15)
        load_row.addWidget(hint_label)
        load_row.addStretch()
        card_load.content_layout.addLayout(load_row)
        layout.addWidget(card_load)

        # КАРТОЧКА 2: Бюджет + Кнопки
        card_table = SettingsCard("Рекламный бюджет")
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["ID", "Название", "Расход (₽)", "Лимит (₽/день)", "Автопауза", "Статус", "Обновлено", ""])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setMinimumHeight(60)
        self.table.setMaximumHeight(120)
        self.table.cellDoubleClicked.connect(self.on_table_double_click)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(1, 350)
        card_table.content_layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.save_btn = QPushButton("💾 Сохранить настройки бюджета")
        self.save_btn.clicked.connect(self.save_settings)
        self.save_btn.setStyleSheet("QPushButton { background-color: #1f883d; color: white; border: 1px solid #1a7f37; } QPushButton:hover { background-color: #1a7f37; }")
        self.start_worker_btn = QPushButton("▶️ Запустить контроль бюджета")
        self.start_worker_btn.setCheckable(True)
        self.start_worker_btn.setStyleSheet("QPushButton { background-color: #dafbe1; border: 1px solid #4ac26b; color: #1a7f37; } QPushButton:hover { background-color: #aceebb; }")
        self.start_worker_btn.clicked.connect(self.toggle_worker)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.start_worker_btn)
        btn_layout.addStretch()
        card_table.content_layout.addLayout(btn_layout)
        layout.addWidget(card_table)

        # КАРТОЧКА 3: Товары и Автобиддер
        card_products = SettingsCard("Товары в кампании и ставки (Автобиддер)")
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(10)
        self.products_table.setHorizontalHeaderLabels([
            "Артикул (nm_id)", "Старая ставка (₽)", "Новая ставка (₽)", "Позиция (ср.)", 
            "Макс. ставка (₽)", "Целевая позиция", "Шаг ↑ (%)", "Шаг ↓ (%)", "Ночная ставка (₽)", "Статус"
        ])
        self.products_table.verticalHeader().setVisible(False)
        self.products_table.setAlternatingRowColors(True)
        self.products_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.products_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.products_table.setMinimumHeight(150)
        
        p_header = self.products_table.horizontalHeader()
        p_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        p_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        p_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        p_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        p_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive) 
        p_header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive) 
        p_header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive) 
        p_header.setSectionResizeMode(7, QHeaderView.ResizeMode.Interactive) 
        p_header.setSectionResizeMode(8, QHeaderView.ResizeMode.Interactive) 
        p_header.setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)
        
        self.products_table.setColumnWidth(4, 120)
        self.products_table.setColumnWidth(5, 140)
        self.products_table.setColumnWidth(6, 100)
        self.products_table.setColumnWidth(7, 100)
        self.products_table.setColumnWidth(8, 140)
        
        card_products.content_layout.addWidget(self.products_table)

        # НАСТРОЙКИ (НОЧНОЙ РЕЖИМ И КНОПКА СТАРТА)
        bidder_settings = QHBoxLayout()
        bidder_settings.setSpacing(15)
        
        bidder_settings.addStretch() # Отодвигаем все вправо

        # НОЧНОЙ РЕЖИМ
        self.night_mode_btn = HoverButton("🌙 Ночной режим: ВЫКЛ", "с 00:00 до 06:00 утра")
        self.night_mode_btn.setCheckable(True)
        self.night_mode_btn.setStyleSheet("""
            QPushButton {
                background-color: #f6f8fa; border: 1px solid #d0d7de; color: #666;
                font-weight: bold; padding: 6px 14px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #eaeef2; }
            QPushButton:checked {
                background-color: #e6f4ea; border: 1px solid #1a7f37; color: #1a7f37;
            }
        """)
        self.night_mode_btn.toggled.connect(self.toggle_night_mode_ui)
        bidder_settings.addWidget(self.night_mode_btn)

        # КНОПКА ЗАПУСКА
        self.start_bidder_btn = QPushButton("🚀 Запустить автобиддер")
        self.start_bidder_btn.setCheckable(True)
        self.start_bidder_btn.clicked.connect(self.toggle_bidder)
        self.start_bidder_btn.setStyleSheet("QPushButton { background-color: #ddf4ff; border: 1px solid #54aeff; color: #0969da; font-weight: bold; padding: 6px 14px; border-radius: 4px; } QPushButton:hover { background-color: #b6e3ff; }")
        bidder_settings.addWidget(self.start_bidder_btn)

        card_products.content_layout.addLayout(bidder_settings)
        layout.addWidget(card_products)

        # КАРТОЧКА 4: ЖУРНАЛ РАБОТЫ
        card_log = SettingsCard("Журнал работы")
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #f6f8fa; 
                border: 1px solid #d0d7de; 
                border-radius: 4px;
                font-family: Consolas, monospace; 
                font-size: 12px; 
                color: #1f2328;
                padding: 5px;
            }
        """)
        self.log_text.append("Готов к работе.")
        card_log.content_layout.addWidget(self.log_text)
        layout.addWidget(card_log)

        layout.addStretch()
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        self.worker = None
        self.load_from_db()
        
        self.start_worker_btn.setChecked(True)
        self.toggle_worker()
        
        QTimer.singleShot(500, self.restore_bidder_state)

    def toggle_night_mode_ui(self, checked):
        if checked:
            self.night_mode_btn.setText("🌙 Ночной режим: ВКЛ")
        else:
            self.night_mode_btn.setText("🌙 Ночной режим: ВЫКЛ")

    def restore_bidder_state(self):
        config = load_bidder_config()
        if not config:
            return
            
        self.campaign_id = config.get("campaign_id")
        
        is_night_mode = config.get("enable_night_mode", False)
        self.night_mode_btn.setChecked(is_night_mode)
        self.toggle_night_mode_ui(is_night_mode)
        
        if self.campaign_id:
            self.log_text.append("Восстановление автобиддера: загрузка товаров...")
            self.load_products(self.campaign_id, config.get("product_settings", {}))
            
            if config.get("enabled", False) or is_night_mode:
                if self.products_table.rowCount() > 0:
                    self.start_bidder_btn.setChecked(True)
                    self.toggle_bidder()
                else:
                    self.log_text.append("⚠️ Не удалось восстановить автобиддер: товары не загрузились.")

    def on_table_double_click(self, row, column):
        camp_id_item = self.table.item(row, 0)
        if camp_id_item:
            camp_id = int(camp_id_item.text())
            config = load_bidder_config()
            prod_settings = config.get("product_settings", {}) if config.get("campaign_id") == camp_id else {}
            self.load_products(camp_id, prod_settings)

    def load_products(self, advert_id: int, saved_settings: dict = None):
        token = load_token()
        if not token: return
        self.campaign_id = advert_id
        api = WBAdAPI(token)
        try:
            products = api.get_campaign_products(advert_id)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить товары: {e}")
            return
            
        if saved_settings is None:
            saved_settings = {}
            
        self.products_table.setRowCount(len(products))
        for i, p in enumerate(products):
            nm_id = p["nm_id"]
            
            item_nm = QTableWidgetItem(str(nm_id))
            item_nm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_nm.setFont(QFont("", -1, QFont.Weight.Bold))
            self.products_table.setItem(i, 0, item_nm)
            
            item_old_bid = QTableWidgetItem(f"{p['current_bid_rub']:.2f}")
            item_old_bid.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_old_bid.setForeground(QColor("#cf222e"))
            item_old_bid.setFont(QFont("", -1, QFont.Weight.Bold))
            self.products_table.setItem(i, 1, item_old_bid)
            
            item_new_bid = QTableWidgetItem(f"{p['current_bid_rub']:.2f}")
            item_new_bid.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_new_bid.setForeground(QColor("#cf222e"))
            item_new_bid.setFont(QFont("", -1, QFont.Weight.Bold))
            self.products_table.setItem(i, 2, item_new_bid)

            item_pos = QTableWidgetItem("—")
            item_pos.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_pos.setForeground(QColor("#1f2328"))
            self.products_table.setItem(i, 3, item_pos)
            
            nm_sett = saved_settings.get(str(nm_id), {
                "max_bid": 30.0, "target_pos": 10, "night_bid": 10.0, "step_up": 10.0, "step_down": 10.0
            })
            
            max_bid_input = QDoubleSpinBox()
            max_bid_input.setRange(1.0, 1000.0)
            max_bid_input.setValue(nm_sett.get("max_bid", 30.0))
            max_bid_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
            max_bid_input.setStyleSheet("color: #cf222e; font-weight: bold;")
            self.products_table.setCellWidget(i, 4, max_bid_input)
            
            target_pos_input = QSpinBox()
            target_pos_input.setRange(1, 100)
            target_pos_input.setValue(nm_sett.get("target_pos", 10))
            target_pos_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
            target_pos_input.setStyleSheet("font-weight: bold;")
            self.products_table.setCellWidget(i, 5, target_pos_input)
            
            step_up_input = QDoubleSpinBox()
            step_up_input.setRange(1.0, 50.0)
            step_up_input.setValue(nm_sett.get("step_up", 10.0))
            step_up_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
            step_up_input.setStyleSheet("font-weight: bold;")
            self.products_table.setCellWidget(i, 6, step_up_input)
            
            step_down_input = QDoubleSpinBox()
            step_down_input.setRange(1.0, 50.0)
            step_down_input.setValue(nm_sett.get("step_down", 10.0))
            step_down_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
            step_down_input.setStyleSheet("font-weight: bold;")
            self.products_table.setCellWidget(i, 7, step_down_input)
            
            night_bid_input = QDoubleSpinBox()
            night_bid_input.setRange(1.0, 1000.0)
            night_bid_input.setValue(nm_sett.get("night_bid", 10.0))
            night_bid_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
            night_bid_input.setStyleSheet("font-weight: bold;")
            self.products_table.setCellWidget(i, 8, night_bid_input)

            item_status = QTableWidgetItem("Ожидание...")
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_status.setForeground(QColor("#666"))
            self.products_table.setItem(i, 9, item_status)
        
        if not self.start_bidder_btn.isChecked():
            self.log_text.append(f"Загружено {len(products)} товаров. Настройте параметры и запускайте.")

    def update_products_ui(self, products: list):
        # === ИСПРАВЛЕНИЕ: Обновляем строго по nm_id, а не по порядку ===
        row_map = {}
        for i in range(self.products_table.rowCount()):
            item = self.products_table.item(i, 0)
            if item:
                row_map[item.text()] = i
                
        for p in products:
            nm_id_str = str(p["nm_id"])
            if nm_id_str not in row_map:
                continue
                
            i = row_map[nm_id_str]
            
            old_bid = p.get('old_bid_rub', p.get('current_bid_rub', 0))
            item_old = QTableWidgetItem(f"{old_bid:.2f}")
            item_old.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_old.setForeground(QColor("#cf222e"))
            item_old.setFont(QFont("", -1, QFont.Weight.Bold))
            self.products_table.setItem(i, 1, item_old)
            
            new_bid = p.get('new_bid_rub', p.get('current_bid_rub', 0))
            item_new = QTableWidgetItem(f"{new_bid:.2f}")
            item_new.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if new_bid > old_bid:
                item_new.setForeground(QColor("#1a7f37"))
            elif new_bid < old_bid:
                item_new.setForeground(QColor("#cf222e"))
            else:
                item_new.setForeground(QColor("#cf222e"))
            item_new.setFont(QFont("", -1, QFont.Weight.Bold))
            self.products_table.setItem(i, 2, item_new)
            
            pos_val = p.get('position')
            pos_text = f"{pos_val:.0f}" if pos_val is not None else "—"
            item_pos = QTableWidgetItem(pos_text)
            item_pos.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_pos.setForeground(QColor("#1f2328"))
            self.products_table.setItem(i, 3, item_pos)
            
            item_status = QTableWidgetItem(p["status"])
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if "✅" in p["status"] or "Повышение" in p["status"] or "Снижение" in p["status"] or "ОК" in p["status"]:
                item_status.setForeground(QColor("#1a7f37"))
            elif "⚠️" in p["status"] or "❌" in p["status"]:
                item_status.setForeground(QColor("#cf222e"))
            else:
                item_status.setForeground(QColor("#1f2328"))
            self.products_table.setItem(i, 9, item_status)

    def toggle_bidder(self):
        config = load_bidder_config()
        
        if self.start_bidder_btn.isChecked():
            if not self.campaign_id:
                QMessageBox.warning(self, "Ошибка", "Сначала дважды кликните по кампании в таблице, чтобы загрузить товары!")
                self.start_bidder_btn.setChecked(False)
                return
                
            product_settings = {}
            for i in range(self.products_table.rowCount()):
                nm_item = self.products_table.item(i, 0)
                max_bid_widget = self.products_table.cellWidget(i, 4)
                target_pos_widget = self.products_table.cellWidget(i, 5)
                step_up_widget = self.products_table.cellWidget(i, 6)
                step_down_widget = self.products_table.cellWidget(i, 7)
                night_bid_widget = self.products_table.cellWidget(i, 8)
                
                if nm_item and max_bid_widget and target_pos_widget and night_bid_widget and step_up_widget and step_down_widget:
                    nm_id = nm_item.text()
                    product_settings[nm_id] = {
                        "max_bid": max_bid_widget.value(),
                        "target_pos": target_pos_widget.value(),
                        "step_up": step_up_widget.value(),
                        "step_down": step_down_widget.value(),
                        "night_bid": night_bid_widget.value()
                    }
                
            config.update({
                "enabled": True,
                "campaign_id": self.campaign_id,
                "product_settings": product_settings,
                "enable_night_mode": self.night_mode_btn.isChecked()
            })
            save_bidder_config(config)
            
            self.start_bidder_btn.setText("⏹ Остановить автобиддер")
            self.start_bidder_btn.setStyleSheet("QPushButton { background-color: #ffebe9; border: 1px solid #cf222e; color: #cf222e; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #ffd8d3; }")
            
            self.bidder_worker = AdBidderWorker(
                advert_id=self.campaign_id,
                product_settings=product_settings,
                interval_min=5,
                enable_night_mode=self.night_mode_btn.isChecked(),
                night_bid=10.0
            )
            self.bidder_worker.log_signal.connect(self.log_text.append)
            self.bidder_worker.products_updated.connect(self.update_products_ui)
            self.bidder_worker.start()
        else:
            config["enabled"] = False
            save_bidder_config(config)
            
            self.start_bidder_btn.setText("🚀 Запустить автобиддер")
            self.start_bidder_btn.setStyleSheet("QPushButton { background-color: #ddf4ff; border: 1px solid #54aeff; color: #0969da; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #b6e3ff; }")
            if self.bidder_worker:
                self.bidder_worker.stop()
                self.bidder_worker.wait(500)
                self.bidder_worker = None
            self.log_text.append("Автобиддер остановлен.")

    def _create_status_widget(self, status_text: str) -> QWidget:
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if "На паузе" in status_text:
            label.setText("На паузе")
            label.setStyleSheet("background-color: #ffebe9; color: #cf222e; border: 1px solid #ffcecb; border-radius: 10px; padding: 0px 6px; font-size: 11px; font-weight: bold;")
        else:
            label.setText("Активна")
            label.setStyleSheet("background-color: #dafbe1; color: #1a7f37; border: 1px solid #aceebb; border-radius: 10px; padding: 0px 6px; font-size: 11px; font-weight: bold;")
        wrapper = QWidget()
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.addWidget(label)
        wrapper_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wrapper_layout.setContentsMargins(2, 2, 2, 2)
        return wrapper

    def _make_red_item(self, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setForeground(QColor("#cf222e"))
        font = QFont()
        font.setBold(True)
        item.setFont(font)
        return item

    def _make_bold_item(self, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setForeground(QColor("#1f2328"))
        font = QFont()
        font.setBold(True)
        item.setFont(font)
        return item

    def load_from_db(self):
        rows = get_all_limits()
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            camp_id, name, limit, auto_pause, last_paused = row
            self.table.setItem(i, 0, self._make_bold_item(str(camp_id)))
            item_name = self._make_bold_item(name)
            item_name.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 1, item_name)
            
            spend_val = self.current_stats.get(camp_id)
            spend_str = f"{spend_val:.2f}" if spend_val is not None else "Загрузка..."
            self.table.setItem(i, 2, self._make_red_item(spend_str))
            
            limit_str = f"{limit:g}" if isinstance(limit, (int, float)) else str(limit)
            limit_input = QLineEdit(limit_str)
            limit_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
            limit_input.setStyleSheet("color: #cf222e; font-weight: bold;")
            self.table.setCellWidget(i, 3, limit_input)
            cb = QCheckBox()
            cb.setChecked(bool(auto_pause))
            cb.setStyleSheet("QCheckBox::indicator:checked { background-color: #1f883d; border: 1px solid #1f883d; border-radius: 4px; }")
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(i, 4, cb_widget)
            status_text = "На паузе" if last_paused else "Активна"
            self.table.setCellWidget(i, 5, self._create_status_widget(status_text))
            self.table.setItem(i, 6, self._make_bold_item("—"))

    def load_campaigns(self):
        token = load_token()
        if not token:
            QMessageBox.warning(self, "Ошибка", "Сначала сохраните API-токен во вкладке Настройки!")
            return
        self.log_text.append("Загрузка кампаний из WB...")
        self.refresh_btn.setEnabled(False)
        try:
            api = WBAdAPI(token)
            campaigns = api.get_active_campaigns()
            
            fetched_ids = {c.get("advertId") for c in campaigns if c.get("advertId")}
            
            if fetched_ids: 
                local_limits = get_all_limits()
                for row in local_limits:
                    if row[0] not in fetched_ids:
                        delete_limit(row[0])
            
            local_ids = {row[0] for row in get_all_limits()}
            for camp in campaigns:
                camp_id = camp.get("advertId")
                status = camp.get("status")
                
                if status == 9:
                    set_paused_date(camp_id, "")
                    
                if camp_id and camp_id not in local_ids:
                    update_limit(camp_id, camp.get("name", "Без названия"), 0, True)
                elif camp_id:
                    update_limit(camp_id, camp.get("name", "Без названия"), 0, True)
            
            self.load_from_db()
            self.log_text.append(f"Синхронизация завершена. Активных кампаний: {len(campaigns)}.")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка API", str(e))
            self.log_text.append("Ошибка загрузки.")
        finally:
            self.refresh_btn.setEnabled(True)

    def save_settings(self):
        for i in range(self.table.rowCount()):
            try:
                camp_id = int(self.table.item(i, 0).text())
                name = self.table.item(i, 1).text()
                limit_widget = self.table.cellWidget(i, 3)
                daily_limit = float(limit_widget.text() or 0)
                cb_widget = self.table.cellWidget(i, 4)
                cb = cb_widget.findChild(QCheckBox)
                auto_pause = cb.isChecked()
                update_limit(camp_id, name, daily_limit, auto_pause)
            except Exception:
                pass
        self.log_text.append("✅ Настройки бюджета сохранены в базу данных.")

    def update_stats_in_ui(self, stats: dict):
        self.current_stats = stats
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        for i in range(self.table.rowCount()):
            try:
                camp_id = int(self.table.item(i, 0).text())
                if camp_id in stats:
                    spend_val = stats[camp_id]
                    spend_str = f"{spend_val:.2f}"
                    self.table.setItem(i, 2, self._make_red_item(spend_str))
                
                self.table.setItem(i, 6, self._make_bold_item(current_time))
                
                for row in get_all_limits():
                    if row[0] == camp_id:
                        last_paused = row[4]
                        status_text = "На паузе" if last_paused else "Активна"
                        self.table.setCellWidget(i, 5, self._create_status_widget(status_text))
                        break
            except Exception:
                pass

    def toggle_worker(self):
        if self.start_worker_btn.isChecked():
            self.start_worker_btn.setText("⏹ Остановить контроль")
            self.start_worker_btn.setStyleSheet("QPushButton { background-color: #ffebe9; border: 1px solid #cf222e; color: #cf222e; font-weight: bold; } QPushButton:hover { background-color: #ffd8d3; }")
            if not self.worker:
                self.worker = AdBudgetWorker()
                self.worker.log_signal.connect(self.log_text.append)
                self.worker.refresh_ui_signal.connect(self.update_stats_in_ui)
                self.worker.start()
        else:
            self.start_worker_btn.setText("▶️ Запустить контроль")
            self.start_worker_btn.setStyleSheet("QPushButton { background-color: #dafbe1; border: 1px solid #4ac26b; color: #1a7f37; font-weight: bold; } QPushButton:hover { background-color: #aceebb; }")
            if self.worker:
                self.worker.stop()
                self.worker.wait(500)
                self.worker = None
            self.log_text.append("Контроль бюджета остановлен.")

    def stop(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait(500)
            self.worker = None
        if self.bidder_worker:
            self.bidder_worker.stop()
            self.bidder_worker.wait(500)
            self.bidder_worker = None