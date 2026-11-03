from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel, QDialog,
    QSystemTrayIcon, QMenu, QApplication, QProgressBar
)
from pathlib import Path

from app.ui.dashboard_tab import DashboardTab
from app.ui.stats_tab import StatsTab
from app.ui.reports_tab import ReportsTab
from app.ui.costs_tab import CostsTab
from app.ui.settings_tab import SettingsTab
from app.secure_token import load_token
from app.sync import sync_recent_days


class SyncThread(QThread):
    finished_ok = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, token):
        super().__init__()
        self.token = token

    def run(self):
        try:
            sync_recent_days(self.token, days=3)
            self.finished_ok.emit()
        except Exception as e:
            self.error.emit(str(e))


class LoadingDialog(QDialog):
    """Маленькое аккуратное окно загрузки поверх главного окна."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(380, 110)
        self.setStyleSheet("""
            QDialog { 
                background: #ffffff; 
                border: 1px solid #d0d7de; 
                border-radius: 10px; 
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        
        label = QLabel("Загрузка данных из Wildberries...")
        label.setStyleSheet("font-size: 13px; font-weight: bold; color: #1f2328;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 0) # Бесконечный режим
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { border: none; background: #eaeef2; border-radius: 3px; }
            QProgressBar::chunk { background: #0969da; border-radius: 3px; }
        """)
        
        layout.addWidget(label)
        layout.addWidget(self.progress)
    
    def center_on_parent(self, parent):
        if parent:
            geo = parent.geometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Юнит-экономика Wildberries")
        self.resize(1650, 860)

        icon_path = Path(__file__).parent.parent.parent / "wb_icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # ================= ЛЕНИВАЯ ЗАГРУЗКА ВКЛАДОК =================
        # Сразу создаем только Дашборд (самый быстрый)
        self.dashboard = DashboardTab()
        self.tabs.addTab(self.dashboard, "Дашборд")
        
        # Для остальных вкладок создаем заглушки
        self._placeholders = {}
        self.reports = None
        self.costs = None
        self.stats = None
        self.settings = None
        
        for name in ["Статистика", "Товары", "Отчёты", "Настройки"]:
            ph = QWidget()
            self._placeholders[name] = ph
            self.tabs.addTab(ph, name)
        
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # ================= ИКОНКА В ТРЕЕ =================
        self.tray_icon = QSystemTrayIcon(self)
        
        if icon_path.exists():
            self.tray_icon.setIcon(QIcon(str(icon_path)))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(
                QApplication.style().StandardPixmap.SP_ComputerIcon
            ))
            
        self.tray_icon.setToolTip("Юнит-экономика Wildberries")

        show_action = QAction("Показать", self)
        show_action.triggered.connect(self.show_normal)
        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(QApplication.instance().quit)

        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tab_changed(self, index: int) -> None:
        name = self.tabs.tabText(index)
        widget = self.tabs.widget(index)
        
        # Если это заглушка — создаем реальную вкладку (ленивая загрузка)
        if name in self._placeholders and widget is self._placeholders[name]:
            if name == "Отчёты":
                self.reports = ReportsTab()
                actual = self.reports
            elif name == "Товары":
                self.costs = CostsTab()
                actual = self.costs
            elif name == "Статистика":
                self.stats = StatsTab()
                actual = self.stats
            else:
                self.settings = SettingsTab()
                actual = self.settings
            
            self.tabs.removeTab(index)
            self.tabs.insertTab(index, actual, name)
            self.tabs.setCurrentIndex(index)
            return
        
        # Обновление данных при переключении
        if widget is self.dashboard:
            self.dashboard.refresh()
        elif widget is self.stats:
            self.stats.refresh()

    def start_sync(self):
        """Запускает фоновую синхронизацию с окном загрузки."""
        token = load_token()
        if not token:
            return
        
        # Создаем окно загрузки
        self.loading_dialog = LoadingDialog(self)
        self.loading_dialog.center_on_parent(self)
        
        # Показываем окно только если синхронизация длится дольше 300 мс
        self._dialog_timer = QTimer()
        self._dialog_timer.setSingleShot(True)
        self._dialog_timer.timeout.connect(self.loading_dialog.show)
        self._dialog_timer.start(300)
        
        # Запускаем поток
        self.sync_thread = SyncThread(token)
        self.sync_thread.finished_ok.connect(self.on_sync_finished)
        self.sync_thread.error.connect(self.on_sync_error)
        self.sync_thread.start()

    def on_sync_finished(self):
        self._dialog_timer.stop()
        self.loading_dialog.close()
        
        # Обновляем все созданные вкладки
        self.dashboard.refresh()
        if self.reports: self.reports.load_data()
        if self.costs: self.costs.load_data()
        if self.stats: self.stats.refresh()

    def on_sync_error(self, err):
        self._dialog_timer.stop()
        self.loading_dialog.close()

    def show_normal(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        self.raise_() 
        self.activateWindow()
        if self.windowHandle():
            self.windowHandle().requestActivate()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_normal()

    def closeEvent(self, event):
        QApplication.instance().quit()
        event.accept()