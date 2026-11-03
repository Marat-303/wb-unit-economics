from PyQt6.QtWidgets import QFrame, QPushButton, QGridLayout
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QDate

class MonthSelector(QFrame):
    month_selected = pyqtSignal(int, int)  # year, month

    def __init__(self, parent=None):
        super().__init__(parent)
        # Делаем его всплывающим (как меню)
        self.setWindowFlags(Qt.WindowType.Popup)
        
        self.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: 1px solid #d0d7de;
                border-radius: 8px;
            }
            QPushButton {
                background: #f5f7fa;
                border: 1px solid #d0d7de;
                border-radius: 4px;
                padding: 10px 15px;
                font-size: 13px;
                font-weight: bold;
                color: #1f2328;
            }
            QPushButton:hover {
                background: #eaeef2;
                border: 1px solid #0969da;
            }
            QPushButton:disabled {
                background: #ffffff;
                color: #ccc;
                border: 1px solid #eaeef2;
            }
            QPushButton[active="true"] {
                background: #0969da;
                color: #ffffff;
                border: 1px solid #0969da;
            }
        """)

        layout = QGridLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        self.buttons = {}
        months_ru = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        
        current_date = QDate.currentDate()
        current_year = current_date.year()
        current_month = current_date.month()

        for i, name in enumerate(months_ru):
            m = i + 1
            btn = QPushButton(name)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, y=current_year, mo=m: self.on_btn_click(y, mo))
            
            # Будущие месяцы делаем неактивными
            if m > current_month:
                btn.setEnabled(False)
                
            self.buttons[m] = btn
            row = i // 3
            col = i % 3
            layout.addWidget(btn, row, col)
            
        self.set_active_month(current_month)

    def show_at(self, button):
        """Показывает окно ровно под кнопкой"""
        pos = button.mapToGlobal(QPoint(0, button.height() + 4))
        self.move(pos)
        self.show()

    def on_btn_click(self, year, month):
        self.month_selected.emit(year, month)
        self.hide()

    def set_active_month(self, month):
        for m, btn in self.buttons.items():
            btn.setProperty("active", "true" if m == month else "false")
            # Принудительно обновляем стиль кнопки
            btn.style().unpolish(btn)
            btn.style().polish(btn)