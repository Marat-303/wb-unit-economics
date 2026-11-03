from datetime import date

from PyQt6.QtCore import QThread, pyqtSignal, QDate, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QDateEdit, QMessageBox,
    QStyle, QAbstractItemView, QHeaderView
)

from app.secure_token import load_token
from app.sync import sync_sales, sync_ads, sync_financial_report, load_recent_sales
from app.ui.month_selector import MonthSelector, CustomDateEdit


class SyncWorker(QThread):
    finished_ok = pyqtSignal(dict)
    failed = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, func, token: str, date_from: str, date_to: str):
        super().__init__()
        self.func = func
        self.token = token
        self.date_from = date_from
        self.date_to = date_to

    def run(self) -> None:
        try:
            result = self.func(self.token, self.date_from, self.date_to, self.progress.emit)
            
            if isinstance(result, int):
                result = {"saved": result}
                
            self.finished_ok.emit(result)
        except Exception as e:
            self.failed.emit(str(e))


class ReportsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        top = QHBoxLayout()
        
        top.addWidget(QLabel("С:"))
        self.date_from = CustomDateEdit()
        today = QDate.currentDate()
        first_day = QDate(today.year(), today.month(), 1)
        self.date_from.setDate(first_day)
        top.addWidget(self.date_from)

        top.addWidget(QLabel("По:"))
        self.date_to = CustomDateEdit()
        yesterday = today.addDays(-1)
        self.date_to.setDate(yesterday)
        top.addWidget(self.date_to)

        button_style = """
            QPushButton {
                background: #f5f7fa;
                border: 1px solid #d0d7de;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: bold;
                color: #1f2328;
            }
            QPushButton:hover {
                background: #eaeef2;
                border: 1px solid #0969da;
            }
            QPushButton:pressed {
                background: #d0d7de;
            }
        """

        self.month_btn = QPushButton("Выбрать месяц")
        self.month_btn.setStyleSheet(button_style)
        self.month_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.month_btn.setMinimumWidth(140)
        self.month_btn.clicked.connect(self.show_month_selector)
        top.addWidget(self.month_btn)

        top.addSpacing(20)

        self.sync_btn = QPushButton(" Синхронизировать продажи")
        self.sync_btn.setStyleSheet(button_style)
        self.sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        self.sync_btn.clicked.connect(lambda: self.on_sync("sales"))
        top.addWidget(self.sync_btn)

        self.sync_ads_btn = QPushButton(" Синхронизировать рекламу")
        self.sync_ads_btn.setStyleSheet(button_style)
        self.sync_ads_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_ads_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        self.sync_ads_btn.clicked.connect(lambda: self.on_sync("ads"))
        top.addWidget(self.sync_ads_btn)

        self.sync_fin_btn = QPushButton(" Синхронизировать удержания WB")
        self.sync_fin_btn.setStyleSheet(button_style)
        self.sync_fin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_fin_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        self.sync_fin_btn.clicked.connect(lambda: self.on_sync("financial"))
        top.addWidget(self.sync_fin_btn)

        top.addSpacing(20)

        self.refresh_btn = QPushButton(" Обновить таблицу")
        self.refresh_btn.setStyleSheet(button_style)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.refresh_btn.clicked.connect(self.load_data)
        top.addWidget(self.refresh_btn)

        top.addStretch()
        layout.addLayout(top)

        # ИНИЦИАЛИЗИРУЕМ СЕТКУ МЕСЯЦЕВ ЗАРАНЕЕ
        self.month_selector = MonthSelector(self)
        self.month_selector.month_selected.connect(self.on_month_selected)

        self.status_label = QLabel("Готово")
        self.status_label.setStyleSheet("color: #555; font-size: 12px; margin-bottom: 5px;")
        layout.addWidget(self.status_label)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Дата", "Артикул WB", "Артикул продавца", "Кол-во",
            "Выручка", "Комиссия", "К перечислению", "Логистика",
        ])
        
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header = self.table.horizontalHeader()
        for col in range(8):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.table)
        self.load_data()

    def show_month_selector(self):
        self.month_selector.show_at(self.month_btn)

    def on_month_selected(self, year, month):
        qdate_start = QDate(year, month, 1)
        current_date = QDate.currentDate()
        
        if year == current_date.year() and month == current_date.month():
            qdate_end = current_date.addDays(-1)
            if qdate_end < qdate_start:
                qdate_end = qdate_start
        else:
            qdate_end = qdate_start.addMonths(1).addDays(-1)
            
        self.date_from.setDate(qdate_start)
        self.date_to.setDate(qdate_end)
        
        months_ru = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        self.month_btn.setText(f"{months_ru[month-1]} {year}")
        self.month_selector.set_active_month(month)

    def _set_buttons_enabled(self, enabled: bool) -> None:
        self.sync_btn.setEnabled(enabled)
        self.sync_ads_btn.setEnabled(enabled)
        self.sync_fin_btn.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)

    def on_sync(self, kind: str) -> None:
        token = load_token()
        if not token:
            QMessageBox.warning(self, "Нет токена", "Сначала сохраните токен на вкладке «Настройки».")
            return

        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")

        if date_from > date_to:
            QMessageBox.warning(self, "Ошибка дат", "Дата начала не может быть позже даты окончания.")
            return

        if kind == "sales":
            fn = sync_sales
            self.status_label.setText("Запрос продаж...")
        elif kind == "ads":
            fn = sync_ads
            self.status_label.setText("Запрос рекламы...")
        else:
            fn = sync_financial_report
            self.status_label.setText("Запрос удержаний...")

        self._set_buttons_enabled(False)
        self.status_label.setStyleSheet("color: #b36b00; font-weight: bold; font-size: 12px;")

        self.worker = SyncWorker(fn, token, date_from, date_to)
        self.worker.finished_ok.connect(self.on_sync_ok)
        self.worker.failed.connect(self.on_sync_fail)
        self.worker.progress.connect(self.status_label.setText)
        self.worker.start()

    def on_sync_ok(self, result: dict) -> None:
        self._set_buttons_enabled(True)
        self.status_label.setText("Синхронизация завершена")
        self.status_label.setStyleSheet("color: #1a7f37; font-weight: bold; font-size: 12px;")
        self.load_data()

    def on_sync_fail(self, err: str) -> None:
        self._set_buttons_enabled(True)
        self.status_label.setText(f"Ошибка: {err}")
        self.status_label.setStyleSheet("color: #cf222e; font-size: 12px;")
        QMessageBox.critical(self, "Ошибка синхронизации", err)

    def load_data(self) -> None:
        self.table.setUpdatesEnabled(False)
        try:
            rows = load_recent_sales(limit=1000)
            self.table.setRowCount(len(rows))
            
            for i, r in enumerate(rows):
                raw_date = r["report_date"]
                formatted_date = f"{raw_date[8:10]}.{raw_date[5:7]}.{raw_date[0:4]}"
                
                nm_id_str = str(r["nm_id"])
                vendor_name = r["sa_name"] or ""
                
                if r["nm_id"] == 0:
                    nm_id_str = "—"
                    vendor_name = "Общие удержания/корректировки"

                values = [
                    formatted_date, nm_id_str, vendor_name, str(r["quantity"]),
                    f"{r['retail_amount']:,.2f}".replace(",", " "), 
                    f"{r['ppvz_sales_commission']:,.2f}".replace(",", " "),
                    f"{r['ppvz_for_pay']:,.2f}".replace(",", " "), 
                    f"{r['delivery_rub']:,.2f}".replace(",", " "),
                ]
                
                for col, val in enumerate(values):
                    item = QTableWidgetItem(val)
                    
                    if col == 2: 
                        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    else:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    if r["nm_id"] == 0:
                        item.setForeground(QColor("#888"))
                    
                    if col in [6, 7]: 
                        font = QFont()
                        font.setBold(True)
                        item.setFont(font)

                    self.table.setItem(i, col, item)
        finally:
            self.table.setUpdatesEnabled(True)