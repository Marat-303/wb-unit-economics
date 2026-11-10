from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QMessageBox, QFileDialog, QInputDialog,
    QHeaderView, QAbstractItemView, QStyle, QFrame
)
import calendar

from app.costs import (
    list_articles_with_costs, set_cost, set_product_title,
    set_product_vendor_code, copy_costs_from_previous_month
)
from app.secure_token import load_token
from app.sync import sync_products_from_api


class ProductsSyncWorker(QThread):
    finished_ok = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(self, token: str):
        super().__init__()
        self.token = token

    def run(self) -> None:
        try:
            n = sync_products_from_api(self.token)
            self.finished_ok.emit(n)
        except Exception as e:
            self.failed.emit(str(e))


class CostsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.current_date = QDate.currentDate()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # ================= БЛОК 1: НАВИГАЦИЯ ПО МЕСЯЦАМ =================
        month_card = QFrame()
        month_card.setStyleSheet("QFrame { background-color: #ffffff; border: 1px solid #d0d7de; border-radius: 8px; }")
        month_layout = QHBoxLayout(month_card)
        month_layout.setContentsMargins(15, 15, 15, 15)
        
        self.btn_prev_month = QPushButton("<")
        self.btn_prev_month.setStyleSheet("QPushButton { padding: 6px 16px; font-weight: bold; font-size: 16px; }")
        self.btn_prev_month.clicked.connect(self.prev_month)
        month_layout.addWidget(self.btn_prev_month)
        
        self.month_label = QLabel()
        self.month_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #1f2328; padding: 0 20px;")
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        month_layout.addWidget(self.month_label)
        
        self.btn_next_month = QPushButton(">")
        self.btn_next_month.setStyleSheet("QPushButton { padding: 6px 16px; font-weight: bold; font-size: 16px; }")
        self.btn_next_month.clicked.connect(self.next_month)
        month_layout.addWidget(self.btn_next_month)
        
        month_layout.addSpacing(30)
        
        self.btn_copy_prev = QPushButton("📋 Скопировать с прошлого месяца")
        self.btn_copy_prev.setStyleSheet("""
            QPushButton { background-color: #ddf4ff; color: #0969da; border: 1px solid #54aeff; font-weight: bold; padding: 6px 14px; border-radius: 4px; }
            QPushButton:hover { background-color: #b6e3ff; }
        """)
        self.btn_copy_prev.clicked.connect(self.copy_previous)
        month_layout.addWidget(self.btn_copy_prev)
        
        month_layout.addStretch()
        layout.addWidget(month_card)

        # ================= БЛОК 2: ИНСТРУМЕНТЫ =================
        top = QHBoxLayout()
        
        self.reload_btn = QPushButton(" Обновить")
        self.reload_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.reload_btn.clicked.connect(self.load_data)
        top.addWidget(self.reload_btn)

        self.save_btn = QPushButton(" 💾 Сохранить")
        self.save_btn.setStyleSheet("""
            QPushButton { background-color: #1f883d; color: white; border: 1px solid #1a7f37; font-weight: bold; padding: 6px 14px; border-radius: 4px; }
            QPushButton:hover { background-color: #1a7f37; }
        """)
        self.save_btn.clicked.connect(self.save_all)
        top.addWidget(self.save_btn)
        
        top.addSpacing(20)

        self.pull_btn = QPushButton(" Подтянуть из WB")
        self.pull_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        self.pull_btn.clicked.connect(self.on_pull_products)
        top.addWidget(self.pull_btn)

        self.add_btn = QPushButton(" Добавить товар")
        self.add_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self.add_btn.clicked.connect(self.on_add_manual)
        top.addWidget(self.add_btn)

        top.addStretch()
        layout.addLayout(top)

        self.status_label = QLabel("Выберите месяц и укажите себестоимость. Не забудьте сохранить.")
        self.status_label.setStyleSheet("color: #555; font-size: 12px; margin-bottom: 5px;")
        layout.addWidget(self.status_label)

        # ================= БЛОК 3: ТАБЛИЦА =================
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Артикул WB", "Наименование", "Артикул продавца", "Себестоимость, ₽"]
        )
        
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.table.verticalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #f5f7fa;
                color: #666;
                font-weight: bold;
                border: 1px solid #d0d7de;
                border-top: none;
                padding: 4px;
            }
        """)
        self.table.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # Растягиваем колонку цены

        layout.addWidget(self.table)
        
        self.update_month_ui()
        self.load_data()

    # --- ЛОГИКА МЕСЯЦЕВ ---
    def update_month_ui(self):
        months_ru = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        self.month_label.setText(f"{months_ru[self.current_date.month() - 1]} {self.current_date.year()}")
        
        # Обновляем заголовок колонки
        self.table.setHorizontalHeaderItem(3, QTableWidgetItem(f"Себестоимость на {months_ru[self.current_date.month() - 1]}, ₽"))

    def prev_month(self):
        self.current_date = self.current_date.addMonths(-1)
        self.update_month_ui()
        self.load_data()

    def next_month(self):
        self.current_date = self.current_date.addMonths(1)
        self.update_month_ui()
        self.load_data()

    def copy_previous(self):
        year = self.current_date.year()
        month = self.current_date.month()
        count = copy_costs_from_previous_month(year, month)
        self.load_data()
        if count > 0:
            self.status_label.setText(f"Успешно скопировано {count} позиций из прошлого месяца. Нажмите «Сохранить» для закрепления.")
            self.status_label.setStyleSheet("color: #1a7f37; font-weight: bold; font-size: 12px;")
        else:
            self.status_label.setText("В прошлом месяце не было сохранено себестоимости.")
            self.status_label.setStyleSheet("color: #b36b00; font-size: 12px;")

    # --- ЛОГИКА ДАННЫХ ---
    def load_data(self) -> None:
        year = self.current_date.year()
        month = self.current_date.month()
        rows = list_articles_with_costs(year, month)
        
        self.table.setRowCount(len(rows))
        
        for i, r in enumerate(rows):
            nm_item = QTableWidgetItem(str(r["nm_id"]))
            nm_item.setFlags(nm_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            nm_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, nm_item)

            title_item = QTableWidgetItem(r["title"] or "")
            font = QFont()
            font.setBold(True)
            title_item.setFont(font)
            title_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 1, title_item)

            vendor_item = QTableWidgetItem(r["sa_name"] or "")
            vendor_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 2, vendor_item)

            cost_val = "" if r["cost_rub"] is None else f"{r['cost_rub']:,.2f}".replace(",", " ")
            cost_item = QTableWidgetItem(cost_val)
            cost_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter) 
            
            # Красим пустые цены в красный
            if r["cost_rub"] is None:
                cost_item.setForeground(QColor("#cf222e"))
                
            self.table.setItem(i, 3, cost_item)

    def save_all(self) -> None:
        year = self.current_date.year()
        month = self.current_date.month()
        
        saved_costs = 0
        saved_names = 0
        errors = []
        
        for i in range(self.table.rowCount()):
            nm_text = self.table.item(i, 0).text() if self.table.item(i, 0) else ""
            if not nm_text: continue
            try:
                nm_id = int(nm_text)
            except ValueError:
                errors.append(f"Строка {i + 1}: Артикул WB не число")
                continue

            title_item = self.table.item(i, 1)
            name_item = self.table.item(i, 2)
            cost_item = self.table.item(i, 3)

            if title_item is not None:
                set_product_title(nm_id, title_item.text().strip())
                saved_names += 1
            if name_item is not None:
                set_product_vendor_code(nm_id, name_item.text().strip())

            if cost_item is None: continue
            cost_text = cost_item.text().strip().replace(",", ".").replace(" ", "")
            if not cost_text:
                continue
            try:
                cost = float(cost_text)
            except ValueError:
                errors.append(f"Строка {i + 1}: себестоимость не число")
                continue
            
            set_cost(nm_id, name_item.text() if name_item else None, cost, year, month)
            saved_costs += 1

        self.status_label.setText(f"Сохранено за {month}.{year}: себестоимости {saved_costs}")
        self.status_label.setStyleSheet("color: #1a7f37; font-weight: bold; font-size: 12px;")
        
        if errors:
            QMessageBox.warning(self, "Часть строк не сохранена", "\n".join(errors))

    # --- СТАРЫЕ МЕТОДЫ (Синхронизация, Добавление) ---
    def on_pull_products(self) -> None:
        token = load_token()
        if not token:
            QMessageBox.warning(self, "Нет токена", "Сначала сохраните токен на вкладке «Настройки».")
            return
        self.pull_btn.setEnabled(False)
        self.status_label.setText("Загружаем карточки из WB...")
        self.status_label.setStyleSheet("color: #b36b00; font-size: 12px;")
        
        self.worker = ProductsSyncWorker(token)
        self.worker.finished_ok.connect(self._on_pull_ok)
        self.worker.failed.connect(self._on_pull_fail)
        self.worker.start()

    def _on_pull_ok(self, count: int) -> None:
        self.pull_btn.setEnabled(True)
        self.status_label.setText(f"Подтянуто {count} карточек")
        self.status_label.setStyleSheet("color: #1a7f37; font-weight: bold; font-size: 12px;")
        self.load_data()

    def _on_pull_fail(self, err: str) -> None:
        self.pull_btn.setEnabled(True)
        self.status_label.setText(f"Ошибка: {err}")
        self.status_label.setStyleSheet("color: #cf222e; font-size: 12px;")
        QMessageBox.warning(self, "Не удалось получить карточки", f"{err}\n\nСкорее всего, у токена нет категории «Контент».")

    def on_add_manual(self) -> None:
        nm_text, ok = QInputDialog.getText(self, "Новый артикул", "Артикул WB (nmID):")
        if not ok or not nm_text.strip(): return
        try:
            nm_id = int(nm_text.strip())
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Артикул WB должен быть числом")
            return

        name, _ = QInputDialog.getText(self, "Новый артикул", "Артикул продавца (опционально):")
        cost_text, ok = QInputDialog.getText(self, "Новый артикул", f"Себестоимость на {self.month_label.text()}, ₽:")
        if not ok: return
        try:
            cost = float(cost_text.replace(",", "."))
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Себестоимость должна быть числом")
            return

        set_cost(nm_id, name or None, cost, self.current_date.year(), self.current_date.month())
        self.load_data()