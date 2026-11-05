from PyQt6.QtCore import Qt, QTime, pyqtSlot, QMetaObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTimeEdit, QMessageBox, QTextEdit, QFrame, QScrollArea
)
import threading
import subprocess
import datetime

from app.secure_token import save_token, load_token
from app.wb_api import WBAPIClient, WBAPIError
from app.scheduler import setup_scheduler, daily_sync_job

# --- Вспомогательный класс для красивой карточки ---
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
            font-size: 14px; 
            font-weight: bold; 
            color: #1f2328;
            border: none;
            background: transparent;
        """)
        self.layout.addWidget(self.title_label)
        
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(10)
        self.layout.addLayout(self.content_layout)

# --- Поток для выполнения Git-команд ---
class GitSyncThread(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd

    def run(self):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            process = subprocess.run(
                self.cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                startupinfo=startupinfo
            )
            if process.returncode == 0:
                self.finished.emit(True, process.stdout)
            else:
                self.finished.emit(False, process.stderr or process.stdout)
        except Exception as e:
            self.finished.emit(False, str(e))


class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        
        # Общие стили для кнопок и полей ввода
        self.setStyleSheet("""
            QLineEdit, QTimeEdit {
                border: 1px solid #d0d7de;
                border-radius: 4px;
                padding: 6px 10px;
                background: #ffffff;
                color: #1f2328;
                font-size: 13px;
            }
            QLineEdit:focus, QTimeEdit:focus {
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
            QPushButton:pressed {
                background: #d0d7de;
            }
            QPushButton:disabled {
                color: #8c959f;
                background: #f6f8fa;
            }
            QTextEdit {
                background-color: #f5f7fa;
                border: 1px solid #d0d7de;
                border-radius: 4px;
                font-family: Consolas, monospace;
                font-size: 11px;
                color: #1f2328;
                padding: 5px;
            }
        """)

        # Основной скролл (на случай, если экран маленький)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # ================= КАРТОЧКА 1: API Токен =================
        card_token = SettingsCard("Доступ к Wildberries API")
        token_row = QHBoxLayout()
        
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText("Вставьте токен...")
        self.token_input.setFixedWidth(260)
        
        existing = load_token()
        if existing:
            self.token_input.setText(existing)

        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.save_api_token)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1f883d; 
                color: white; 
                border: 1px solid #1a7f37;
            }
            QPushButton:hover { background-color: #1a7f37; }
        """)
        
        self.check_btn = QPushButton("Проверить Ping")
        self.check_btn.clicked.connect(self.check_ping)

        token_row.addWidget(QLabel("API-токен:"))
        token_row.addWidget(self.token_input)
        token_row.addWidget(self.save_btn)
        token_row.addWidget(self.check_btn)
        token_row.addStretch()
        
        card_token.content_layout.addLayout(token_row)
        layout.addWidget(card_token)

        # ================= КАРТОЧКА 2: Автосинхронизация =================
        card_sync = SettingsCard("Автоматическая синхронизация")
        
        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("Запускать каждый день в:"))
        
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(6, 0))
        self.time_edit.setFixedWidth(80)
        
        self.apply_schedule_btn = QPushButton("Применить расписание")
        self.apply_schedule_btn.clicked.connect(self.apply_schedule)
        
        time_row.addWidget(self.time_edit)
        time_row.addWidget(self.apply_schedule_btn)
        time_row.addStretch()
        
        manual_row = QHBoxLayout()
        self.manual_sync_btn = QPushButton("Запустить синхронизацию за вчера сейчас")
        self.manual_sync_btn.clicked.connect(self.run_manual_sync)
        manual_row.addWidget(self.manual_sync_btn)
        manual_row.addStretch()
        
        card_sync.content_layout.addLayout(time_row)
        card_sync.content_layout.addLayout(manual_row)
        layout.addWidget(card_sync)

        # ================= КАРТОЧКА 3: Синхронизация с GitHub =================
        card_git = SettingsCard("Синхронизация с GitHub")
        
        git_btn_row = QHBoxLayout()
        
        self.btn_push = QPushButton("📤 Отправить на GitHub (Push)")
        self.btn_push.clicked.connect(self.git_push)
        self.btn_push.setStyleSheet("""
            QPushButton {
                background-color: #ddf4ff; 
                border: 1px solid #54aeff;
                color: #0969da;
            }
            QPushButton:hover { background-color: #b6e3ff; }
        """)
        
        self.btn_pull = QPushButton("📥 Скачать с GitHub (Pull)")
        self.btn_pull.clicked.connect(self.git_pull)
        self.btn_pull.setStyleSheet("""
            QPushButton {
                background-color: #dafbe1; 
                border: 1px solid #4ac26b;
                color: #1a7f37;
            }
            QPushButton:hover { background-color: #aceebb; }
        """)
        
        git_btn_row.addWidget(self.btn_push)
        git_btn_row.addWidget(self.btn_pull)
        git_btn_row.addStretch()
        
        self.git_log = QTextEdit()
        self.git_log.setReadOnly(True)
        self.git_log.setFixedHeight(80)
        self.git_log.append("Здесь будет отображаться статус синхронизации.")
        
        card_git.content_layout.addLayout(git_btn_row)
        card_git.content_layout.addWidget(self.git_log)
        layout.addWidget(card_git)

        # Статус бар
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #1a7f37; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    # --- Универсальное красивое всплывающее окно ---
    def _show_message(self, title: str, text: str, is_error: bool = False):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        
        if is_error:
            # Красное окно для ошибок
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setText(f"<span style='color: #cf222e; font-size: 13px;'>{text}</span>")
        else:
            # Зеленое окно для успеха (убираем стандартную иконку "i")
            msg.setIcon(QMessageBox.Icon.NoIcon)
            msg.setText(f"<span style='color: #1a7f37; font-size: 14px; font-weight: bold;'>✅ {text}</span>")
            # Делаем кнопку ОК зеленой
            msg.setStyleSheet("""
                QPushButton {
                    background-color: #1f883d; 
                    color: white; 
                    border: 1px solid #1a7f37;
                    padding: 4px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #1a7f37; }
            """)
        
        msg.exec()

    # --- Логика API ---
    def save_api_token(self):
        token = self.token_input.text().strip()
        if not token:
            self._show_message("Ошибка", "Токен не может быть пустым", is_error=True)
            return
        save_token(token)
        self.status_label.setText("✅ Токен успешно сохранён")
        self.status_label.setStyleSheet("color: #1a7f37; font-weight: bold;")

    def check_ping(self):
        token = self.token_input.text().strip()
        if not token:
            self._show_message("Внимание", "Сначала введите токен", is_error=True)
            return
        try:
            client = WBAPIClient(token)
            client.ping() # Вызываем пинг, но не сохраняем ответ, чтобы не показывать лишнее
            self._show_message("Успех", "Связь с WB установлена!")
        except WBAPIError as e:
            self._show_message("Ошибка API", str(e), is_error=True)
        except Exception as e:
            self._show_message("Ошибка", f"Неизвестная ошибка: {e}", is_error=True)

    # --- Логика автосинхронизации ---
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

    # --- Логика Git ---
    def git_push(self):
        self.git_log.clear()
        self.git_log.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Запуск отправки...")
        self.btn_push.setEnabled(False)
        self.btn_pull.setEnabled(False)
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cmd = f'git add . & git commit -m "Auto-sync from app {timestamp}" & git push'
        
        self.git_thread = GitSyncThread(cmd)
        self.git_thread.finished.connect(self._on_git_push_finished)
        self.git_thread.start()

    def _on_git_push_finished(self, success, output):
        self.btn_push.setEnabled(True)
        self.btn_pull.setEnabled(True)
        if success or "nothing to commit" in output or "Everything up-to-date" in output:
            self.git_log.append("✅ Успешно отправлено на GitHub!")
            self.git_log.append(output)
        else:
            self.git_log.append("❌ Ошибка при отправке:")
            self.git_log.append(output)

    def git_pull(self):
        reply = QMessageBox.question(
            self, "Внимание", 
            "Вы собираетесь скачать изменения с GitHub.\n\n"
            "⚠️ Если база данных сейчас заблокирована программой, скачивание может завершиться ошибкой.\n\n"
            "Продолжить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            return

        self.git_log.clear()
        self.git_log.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Скачивание...")
        self.btn_push.setEnabled(False)
        self.btn_pull.setEnabled(False)
        
        cmd = 'git fetch origin & git reset --hard origin/master'
        
        self.git_thread = GitSyncThread(cmd)
        self.git_thread.finished.connect(self._on_git_pull_finished)
        self.git_thread.start()

    def _on_git_pull_finished(self, success, output):
        self.btn_push.setEnabled(True)
        self.btn_pull.setEnabled(True)
        if success:
            self.git_log.append("✅ Изменения успешно скачаны!")
            self.git_log.append("⚠️ Закройте и откройте программу заново, чтобы обновить данные.")
        else:
            self.git_log.append("❌ Ошибка (возможно, база занята):")
            self.git_log.append(output)