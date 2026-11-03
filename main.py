import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from pathlib import Path

from app.db import init_db
from app.ui.main_window import MainWindow

def main():
    init_db()
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Глобальный стиль для календаря (фон, цвета выделения)
    app.setStyleSheet("""
        QCalendarWidget QWidget {
            alternate-background-color: #ffffff;
        }
        QCalendarWidget QAbstractItemView:enabled {
            background-color: #ffffff;
            color: #1f2328;
            selection-background-color: #0969da;
            selection-color: #ffffff;
            font-size: 13px;
            font-weight: bold;
        }
        QCalendarWidget QWidget#qt_calendar_navigationbar {
            background-color: #f5f7fa;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            border-bottom: 1px solid #d0d7de;
        }
        QCalendarWidget QToolButton {
            color: #1f2328;
            font-weight: bold;
            background-color: transparent;
            border: none;
            border-radius: 4px;
            padding: 5px;
        }
        QCalendarWidget QToolButton:hover {
            background-color: #eaeef2;
        }
        QCalendarWidget QMenu {
            background-color: #ffffff;
            border: 1px solid #d0d7de;
            border-radius: 4px;
        }
        QCalendarWidget QSpinBox {
            border: 1px solid #d0d7de;
            border-radius: 4px;
            selection-background-color: #0969da;
            selection-color: #ffffff;
        }
        QCalendarWidget QAbstractItemView:disabled {
            color: #ccc;
        }
    """)

    icon_path = Path(__file__).parent / "wb_icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()
    
    window.start_sync()
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())