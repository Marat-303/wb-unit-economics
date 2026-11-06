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
from app.ad_budget_db import get_all_limits, update_limit
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
        card_products = SettingsCard("Товары в кампании и ставки (Автобиддер по общему ДРР)")
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(5)
        self.products_table.setHorizontalHeaderLabels(["Артикул (nm_id)", "Старая ставка (₽)", "Новая ставка (₽)", "ДРР кампании (7 дн.)", "Статус"])
        self.products_table.verticalHeader().setVisible(False)
        self.products_table.setAlternatingRowColors(True)
        self.products_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.products_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.products_table.setMaximumHeight(200)
        p_header = self.products_table.horizontalHeader()
        p_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        p_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        p_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        p_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        p_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        card_products.content_layout.addWidget(self.products_table)

        bidder_settings = QHBoxLayout()
        bidder_settings.setSpacing(15)
        bidder_settings.addWidget(QLabel("Макс. ставка (₽):"))
        self.max_bid_spin = QDoubleSpinBox()
        self.max_bid_spin.setRange(1.0, 1000.0)
        self.max_bid_spin.setValue(25.0)
        bidder_settings.addWidget(self.max_bid_spin)

        bidder_settings.addWidget(QLabel("Целевой ДРР (%):"))
        self.target_drr_spin = QDoubleSpinBox()
        self.target_drr_spin.setRange(1.0, 100.0)
        self.target_drr_spin.setValue(15.0)
        self.target_drr_spin.setSingleStep(0.5)
        bidder_settings.addWidget(self.target_drr_spin)

        bidder_settings.addWidget(QLabel("Шаг ↑ (%):"))
        self.step_up_spin = QDoubleSpinBox()
        self.step_up_spin.setRange(1.0, 50.0)
        self.step_up_spin.setValue(5.0)
        bidder_settings.addWidget(self.step_up_spin)

        bidder_settings.addWidget(QLabel("Шаг ↓ (%):"))
        self.step_down_spin = QDoubleSpinBox()
        self.step_down_spin.setRange(1.0, 50.0)
        self.step_down_spin.setValue(3.0)
        bidder_settings.addWidget(self.step_down_spin)
        bidder_settings.addStretch()

        self.start_bidder_btn = QPushButton("🚀 Запустить автобиддер")
        self.start_bidder_btn.setCheckable(True)
        self.start_bidder_btn.clicked.connect(self.toggle_bidder)
        self.start_bidder_btn.setStyleSheet("QPushButton { background-color: #ddf4ff; border: 1px solid #54aeff; color: #0969da; font-weight: bold; padding: 6px 14px; border-radius: 4px; } QPushButton:hover { background-color: #b6e3ff; }")
        bidder_settings.addWidget(self.start_bidder_btn)
        card_products.content_layout.addLayout(bidder_settings)
        layout.addWidget(card_products)

        # ================= КАРТОЧКА 4: ЖУРНАЛ РАБОТЫ =================
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
        # ============================================================

        layout.addStretch()
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        self.worker = None
        self.load_from_db()
        
        self.start_worker_btn.setChecked(True)
        self.toggle_worker()
        
        # Запускаем восстановление автобиддера с задержкой
        QTimer.singleShot(500, self.restore_bidder_state)

    def restore_bidder_state(self):
        config = load_bidder_config()
        if not config:
            return
            
        self.campaign_id = config.get("campaign_id")
        self.max_bid_spin.setValue(config.get("max_bid", 25.0))
        self.target_drr_spin.setValue(config.get("target_drr", 15.0))
        self.step_up_spin.setValue(config.get("step_up", 5.0))
        self.step_down_spin.setValue(config.get("step_down", 3.0))
        
        if self.campaign_id:
            self.log_text.append("Восстановление автобиддера: загрузка товаров...")
            self.load_products(self.campaign_id)
            
            if config.get("enabled", False):
                if self.products_table.rowCount() > 0:
                    self.start_bidder_btn.setChecked(True)
                    self.toggle_bidder()
                else:
                    self.log_text.append("⚠️ Не удалось восстановить автобиддер: товары не загрузились.")

    def on_table_double_click(self, row, column):
        camp_id_item = self.table.item(row, 0)
        if camp_id_item:
            camp_id = int(camp_id_item.text())
            self.load_products(camp_id)

    def load_products(self, advert_id: int):
        token = load_token()
        if not token: return
        self.campaign_id = advert_id
        api = WBAdAPI(token)
        try:
            products = api.get_campaign_products(advert_id)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить товары: {e}")
            return
        self.products_table.setRowCount(len(products))
        for i, p in enumerate(products):
            item_nm = QTableWidgetItem(str(p["nm_id"]))
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

            item_drr = QTableWidgetItem("—")
            item_drr.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_drr.setForeground(QColor("#1f2328"))
            self.products_table.setItem(i, 3, item_drr)
            
            item_status = QTableWidgetItem("Ожидание...")
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_status.setForeground(QColor("#666"))
            self.products_table.setItem(i, 4, item_status)
        
        if not self.start_bidder_btn.isChecked():
            self.log_text.append(f"Загружено {len(products)} товаров. Можно запускать автобиддер.")

    def update_products_ui(self, products: list):
        self.products_table.setRowCount(len(products))
        for i, p in enumerate(products):
            item_nm = QTableWidgetItem(str(p["nm_id"]))
            item_nm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_nm.setFont(QFont("", -1, QFont.Weight.Bold))
            self.products_table.setItem(i, 0, item_nm)
            
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
                item_new.setForeground(QColor("#1a7f37")) # Зеленый при повышении
            elif new_bid < old_bid:
                item_new.setForeground(QColor("#cf222e")) # Красный при понижении
            else:
                item_new.setForeground(QColor("#cf222e")) # Красный по умолчанию
            item_new.setFont(QFont("", -1, QFont.Weight.Bold))
            self.products_table.setItem(i, 2, item_new)
            
            drr_val = p.get('campaign_drr')
            if drr_val == 999.9:
                drr_text = "∞"
            elif drr_val is not None:
                drr_text = f"{drr_val:.1f}%"
            else:
                drr_text = "—"
                
            item_drr = QTableWidgetItem(drr_text)
            item_drr.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_drr.setForeground(QColor("#1f2328"))
            self.products_table.setItem(i, 3, item_drr)
            
            item_status = QTableWidgetItem(p["status"])
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if "✅" in p["status"]:
                item_status.setForeground(QColor("#1a7f37"))
            elif "⚠️" in p["status"] or "❌" in p["status"]:
                item_status.setForeground(QColor("#cf222e"))
            else:
                item_status.setForeground(QColor("#1f2328"))
            self.products_table.setItem(i, 4, item_status)

    def toggle_bidder(self):
        config = load_bidder_config()
        
        if self.start_bidder_btn.isChecked():
            if not self.campaign_id:
                QMessageBox.warning(self, "Ошибка", "Сначала дважды кликните по кампании в таблице, чтобы загрузить товары!")
                self.start_bidder_btn.setChecked(False)
                return
                
            config.update({
                "enabled": True,
                "campaign_id": self.campaign_id,
                "max_bid": self.max_bid_spin.value(),
                "target_drr": self.target_drr_spin.value(),
                "step_up": self.step_up_spin.value(),
                "step_down": self.step_down_spin.value()
            })
            save_bidder_config(config)
            
            self.start_bidder_btn.setText("⏹ Остановить автобиддер")
            self.start_bidder_btn.setStyleSheet("QPushButton { background-color: #ffebe9; border: 1px solid #cf222e; color: #cf222e; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #ffd8d3; }")
            for i in range(self.products_table.rowCount()):
                item = self.products_table.item(i, 4)
                if item: item.setText("Запуск...")
            self.bidder_worker = AdBidderWorker(
                advert_id=self.campaign_id,
                target_drr=self.target_drr_spin.value(),
                max_bid=self.max_bid_spin.value(),
                step_up=self.step_up_spin.value(),
                step_down=self.step_down_spin.value(),
                interval_min=10
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
        self.log_text.append("Загрузка кампаний...")
        self.refresh_btn.setEnabled(False)
        try:
            api = WBAdAPI(token)
            campaigns = api.get_active_campaigns()
            self.table.setRowCount(len(campaigns))
            for i, camp in enumerate(campaigns):
                camp_id = camp.get("advertId")
                name = camp.get("name", "Без названия")
                status_code = camp.get("status")
                status_text = "Активна" if status_code == 9 else "На паузе"
                self.table.setItem(i, 0, self._make_bold_item(str(camp_id)))
                item_name = self._make_bold_item(name)
                item_name.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i, 1, item_name)
                self.table.setItem(i, 2, self._make_red_item("Загрузка..."))
                limit_input = QLineEdit("0")
                limit_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
                limit_input.setStyleSheet("color: #cf222e; font-weight: bold;")
                self.table.setCellWidget(i, 3, limit_input)
                cb = QCheckBox()
                cb.setChecked(True)
                cb.setStyleSheet("QCheckBox::indicator:checked { background-color: #1f883d; border: 1px solid #1f883d; border-radius: 4px; }")
                cb_widget = QWidget()
                cb_layout = QHBoxLayout(cb_widget)
                cb_layout.addWidget(cb)
                cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cb_layout.setContentsMargins(0, 0, 0, 0)
                self.table.setCellWidget(i, 4, cb_widget)
                self.table.setCellWidget(i, 5, self._create_status_widget(status_text))
                self.table.setItem(i, 6, self._make_bold_item("—"))
            self.log_text.append(f"Загружено {len(campaigns)} кампаний. Ожидание статистики...")
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
                spend_val = stats.get(camp_id)
                spend_str = f"{spend_val:.2f}" if spend_val is not None else "0.00"
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