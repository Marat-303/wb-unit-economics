from PyQt6.QtCore import Qt, QTime, pyqtSlot, QMetaObject
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QTimeEdit, QMessageBox
)
import threading

from app.secure_token import save_token, load_token
from app.wb_api import WBAPIClient, WBAPIError
from app.scheduler import setup_scheduler, daily_sync_job


class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # --- Группа 1: API Токен ---
        token_group = QGroupBox("Доступ к Wildberries API")
        token_layout = QVBoxLayout(token_group)
        
        # Строка с полем ввода и кнопками
        input_layout = QHBoxLayout()
        
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText("Вставьте токен...")
        
        # ДЕЛАЕМ ПОЛЕ ЕЩЕ МЕНЬШЕ (250-350 пикселей)
        self.token_input.setMinimumWidth(250)
        self.token_input.setMaximumWidth(350)
        
        existing = load_token()
        if existing:
            self.token_input.setText(existing)

        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.save_api_token)
        
        self.check_btn = QPushButton("Проверить Ping")
        self.check_btn.clicked.connect(self.check_ping)

        input_layout.addWidget(QLabel("API-токен:"))
        input_layout.addWidget(self.token_input)
        input_layout.addWidget(self.save_btn)
        input_layout.addWidget(self.check_btn)
        input_layout.addStretch() # Прижимаем все элементы влево
        
        token_layout.addLayout(input_layout)
        layout.addWidget(token_group)

        # --- Группа 2: Автосинхронизация ---
        sync_group = QGroupBox("Автоматическая синхронизация")
        sync_layout = QVBoxLayout(sync_group)
        sync_layout.setSpacing(10)

        # Строка настройки времени
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Запускать каждый день в:"))
        
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(6, 0))
        self.time_edit.setMaximumWidth(80) # Компактное поле времени
        
        self.apply_schedule_btn = QPushButton("Применить расписание")
        self.apply_schedule_btn.clicked.connect(self.apply_schedule)
        
        time_layout.addWidget(self.time_edit)
        time_layout.addWidget(self.apply_schedule_btn)
        time_layout.addStretch()
        sync_layout.addLayout(time_layout)

        # Кнопка ручной синхронизации
        manual_layout = QHBoxLayout()
        self.manual_sync_btn = QPushButton("Запустить синхронизацию за вчера сейчас")
        self.manual_sync_btn.clicked.connect(self.run_manual_sync)
        # Ограничиваем ширину кнопки, чтобы она не растягивалась
        self.manual_sync_btn.setMaximumWidth(350)
        
        manual_layout.addWidget(self.manual_sync_btn)
        manual_layout.addStretch()
        sync_layout.addLayout(manual_layout)

        layout.addWidget(sync_group)
        
        # Статус бар
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #1a7f37; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        # Прижимаем все блоки к верху вкладки
        layout.addStretch()

    def save_api_token(self):
        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "Ошибка", "Токен не может быть пустым")
            return
        save_token(token)
        self.status_label.setText("Токен успешно сохранён в Windows Credential Manager.")
        self.status_label.setStyleSheet("color: #1a7f37; font-weight: bold;")

    def check_ping(self):
        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "Ошибка", "Сначала введите токен")
            return
        try:
            client = WBAPIClient(token)
            resp = client.ping()
            QMessageBox.information(self, "Успех", f"Связь с WB установлена!\nОтвет: {resp}")
        except WBAPIError as e:
            QMessageBox.critical(self, "Ошибка API", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Неизвестная ошибка: {e}")

    def apply_schedule(self):
        t = self.time_edit.time()
        setup_scheduler(hour=t.hour(), minute=t.minute())
        self.status_label.setText(f"Автосинхронизация настроена на {t.toString('HH:mm')} ежедневно.")
        self.status_label.setStyleSheet("color: #1a7f37; font-weight: bold;")

    def run_manual_sync(self):
        self.manual_sync_btn.setEnabled(False)
        self.status_label.setText("Синхронизация запущена в фоне...")
        self.status_label.setStyleSheet("color: #b36b00; font-weight: bold;")
        
        def task():
            daily_sync_job()
            QMetaObject.invokeMethod(self, "sync_finished", Qt.ConnectionType.QueuedConnection)
        
        threading.Thread(target=task, daemon=True).start()

    @pyqtSlot()
    def sync_finished(self):
        self.manual_sync_btn.setEnabled(True)
        self.status_label.setText("Синхронизация завершена. Проверьте вкладку «Дашборд».")
        self.status_label.setStyleSheet("color: #1a7f37; font-weight: bold;")