from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QMessageBox, QFileDialog, QInputDialog,
    QHeaderView, QAbstractItemView, QStyle
)

from app.costs import (
    list_articles_with_costs, set_cost, set_product_title,
    set_product_vendor_code, import_costs_from_excel
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Панель с кнопками
        top = QHBoxLayout()
        
        self.reload_btn = QPushButton(" Обновить")
        self.reload_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.reload_btn.clicked.connect(self.load_data)
        top.addWidget(self.reload_btn)

        self.save_btn = QPushButton(" Сохранить")
        self.save_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.save_btn.clicked.connect(self.save_all)
        top.addWidget(self.save_btn)
        
        top.addSpacing(20) # Визуальный разделитель

        self.pull_btn = QPushButton(" Подтянуть из WB")
        self.pull_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        self.pull_btn.clicked.connect(self.on_pull_products)
        top.addWidget(self.pull_btn)

        self.import_btn = QPushButton(" Импорт Excel")
        self.import_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.import_btn.clicked.connect(self.on_import_excel)
        top.addWidget(self.import_btn)

        self.add_btn = QPushButton(" Добавить товар")
        self.add_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self.add_btn.clicked.connect(self.on_add_manual)
        top.addWidget(self.add_btn)

        top.addStretch()
        layout.addLayout(top)

        self.status_label = QLabel(
            "Все колонки, кроме «Артикул WB», можно редактировать прямо в таблице. "
            "После правок не забудьте нажать «Сохранить»."
        )
        self.status_label.setStyleSheet("color: #555; font-size: 12px; margin-bottom: 5px;")
        layout.addWidget(self.status_label)

        # Настройка таблицы
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Артикул WB", "Наименование", "Артикул продавца", "Себестоимость, ₽"]
        )
        
        # Визуальные улучшения таблицы
        self.table.setAlternatingRowColors(True)  # Зебра
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setDefaultSectionSize(32) # Высота строк
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # СТИЛИЗАЦИЯ ПОРЯДКОВЫХ НОМЕРОВ
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
        
        # ШИРИНА КОЛОНОК: все ровно по размеру текста
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(False) # Отключаем растягивание последней колонки

        layout.addWidget(self.table)
        self.load_data()

    def load_data(self) -> None:
        rows = list_articles_with_costs()
        self.table.setRowCount(len(rows))
        
        for i, r in enumerate(rows):
            # Артикул WB (только чтение, по центру)
            nm_item = QTableWidgetItem(str(r["nm_id"]))
            nm_item.setFlags(nm_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            nm_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, nm_item)

            # Наименование (жирный шрифт, слева)
            title_item = QTableWidgetItem(r["title"] or "")
            font = QFont()
            font.setBold(True)
            title_item.setFont(font)
            title_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 1, title_item)

            # Артикул продавца (по центру)
            vendor_item = QTableWidgetItem(r["sa_name"] or "")
            vendor_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 2, vendor_item)

            # Себестоимость (ТЕПЕРЬ ПО ЦЕНТРУ)
            cost_val = "" if r["cost_rub"] is None else f"{r['cost_rub']:,.2f}".replace(",", " ")
            cost_item = QTableWidgetItem(cost_val)
            cost_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter) 
            self.table.setItem(i, 3, cost_item)

    def save_all(self) -> None:
        saved_costs = 0
        saved_names = 0
        errors = []
        for i in range(self.table.rowCount()):
            nm_text = self.table.item(i, 0).text() if self.table.item(i, 0) else ""
            if not nm_text:
                continue
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

            if cost_item is None:
                continue
            cost_text = cost_item.text().strip().replace(",", ".").replace(" ", "")
            if not cost_text:
                continue
            try:
                cost = float(cost_text)
            except ValueError:
                errors.append(f"Строка {i + 1}: себестоимость не число")
                continue
            set_cost(
                nm_id,
                name_item.text() if name_item else None,
                cost,
            )
            saved_costs += 1

        self.status_label.setText(
            f"Сохранено: названий/артикулов {saved_names}, себестоимости {saved_costs}"
        )
        self.status_label.setStyleSheet("color: #1a7f37; font-weight: bold; font-size: 12px;")
        
        if errors:
            QMessageBox.warning(self, "Часть строк не сохранена", "\n".join(errors))

    def on_pull_products(self) -> None:
        token = load_token()
        if not token:
            QMessageBox.warning(self, "Нет токена",
                                "Сначала сохраните токен на вкладке «Настройки».")
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
        QMessageBox.warning(
            self, "Не удалось получить карточки",
            f"{err}\n\n"
            "Скорее всего, у токена нет категории «Контент». "
            "Вы можете ввести названия и артикулы вручную."
        )

    def on_import_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Импорт себестоимости", "Себестоимость.xlsx", "Excel Files (*.xlsx);;Все файлы (*)"
        )
        if not path:
            return
        try:
            count = import_costs_from_excel(path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", str(e))
            return
        self.load_data()
        QMessageBox.information(self, "Импорт завершён", f"Импортировано строк: {count}")

    def on_add_manual(self) -> None:
        nm_text, ok = QInputDialog.getText(self, "Новый артикул", "Артикул WB (nmID):")
        if not ok or not nm_text.strip():
            return
        try:
            nm_id = int(nm_text.strip())
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Артикул WB должен быть числом")
            return

        name, _ = QInputDialog.getText(self, "Новый артикул", "Артикул продавца (опционально):")
        cost_text, ok = QInputDialog.getText(self, "Новый артикул", "Себестоимость, ₽:")
        if not ok:
            return
        try:
            cost = float(cost_text.replace(",", "."))
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Себестоимость должна быть числом")
            return

        set_cost(nm_id, name or None, cost)
        self.load_data()