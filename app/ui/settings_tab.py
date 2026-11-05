from PyQt6.QtCore import Qt, QTime, pyqtSlot, QMetaObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QTimeEdit, QMessageBox, QTextEdit
)
import threading
import subprocess
import datetime

from app.secure_token import save_token, load_token
from app.wb_api import WBAPIClient, WBAPIError
from app.scheduler import setup_scheduler, daily_sync_job

# --- Поток для выполнения Git-команд без зависания интерфейса ---
class GitSyncThread(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd

    def run(self):
        try:
            # Скрываем черное окно консоли при выполнении команд
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
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # --- Группа 1: API Токен ---
        token_group = QGroupBox("Доступ к Wildberries API")
        token_layout = QVBoxLayout(token_group)
        
        input_layout = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText("Вставьте токен...")
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
        input_layout.addStretch()
        
        token_layout.addLayout(input_layout)
        layout.addWidget(token_group)

        # --- Группа 2: Автосинхронизация ---
        sync_group = QGroupBox("Автоматическая синхронизация")
        sync_layout = QVBoxLayout(sync_group)
        sync_layout.setSpacing(10)

        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Запускать каждый день в:"))
        
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(6, 0))
        self.time_edit.setMaximumWidth(80)
        
        self.apply_schedule_btn = QPushButton("Применить расписание")
        self.apply_schedule_btn.clicked.connect(self.apply_schedule)
        
        time_layout.addWidget(self.time_edit)
        time_layout.addWidget(self.apply_schedule_btn)
        time_layout.addStretch()
        sync_layout.addLayout(time_layout)

        manual_layout = QHBoxLayout()
        self.manual_sync_btn = QPushButton("Запустить синхронизацию за вчера сейчас")
        self.manual_sync_btn.clicked.connect(self.run_manual_sync)
        self.manual_sync_btn.setMaximumWidth(350)
        
        manual_layout.addWidget(self.manual_sync_btn)
        manual_layout.addStretch()
        sync_layout.addLayout(manual_layout)

        layout.addWidget(sync_group)

        # --- Группа 3: Синхронизация с GitHub ---
        git_group = QGroupBox("Синхронизация с GitHub")
        git_layout = QVBoxLayout(git_group)
        
        git_btn_layout = QHBoxLayout()
        self.btn_push = QPushButton("📤 Отправить на GitHub (Push)")
        self.btn_push.clicked.connect(self.git_push)
        self.btn_push.setStyleSheet("background-color: #ddf4ff; padding: 6px;")
        
        self.btn_pull = QPushButton("📥 Скачать с GitHub (Pull)")
        self.btn_pull.clicked.connect(self.git_pull)
        self.btn_pull.setStyleSheet("background-color: #dafbe1; padding: 6px;")
        
        git_btn_layout.addWidget(self.btn_push)
        git_btn_layout.addWidget(self.btn_pull)
        git_btn_layout.addStretch()
        git_layout.addLayout(git_btn_layout)
        
        self.git_log = QTextEdit()
        self.git_log.setReadOnly(True)
        self.git_log.setMaximumHeight(100)
        self.git_log.setStyleSheet("background-color: #f5f7fa; font-family: Consolas, monospace; font-size: 11px; border: 1px solid #d0d7de;")
        self.git_log.append("Здесь будет отображаться статус синхронизации.")
        git_layout.addWidget(self.git_log)
        
        layout.addWidget(git_group)
        
        # Статус бар
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #1a7f37; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()

    # --- Логика API ---
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

    # --- Логика Git-синхронизации ---
    def git_push(self):
        self.git_log.clear()
        self.git_log.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Запуск отправки на GitHub...")
        self.btn_push.setEnabled(False)
        self.btn_pull.setEnabled(False)
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Добавляем, коммитим и отправляем
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
            "⚠️ Если файл базы данных (data/wb.db) сейчас заблокирован программой, скачивание может завершиться ошибкой.\n\n"
            "Продолжить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            return

        self.git_log.clear()
        self.git_log.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Скачивание изменений с GitHub...")
        self.btn_push.setEnabled(False)
        self.btn_pull.setEnabled(False)
        
        # Принудительно берем версию с GitHub
        cmd = 'git fetch origin & git reset --hard origin/master'
        
        self.git_thread = GitSyncThread(cmd)
        self.git_thread.finished.connect(self._on_git_pull_finished)
        self.git_thread.start()

    def _on_git_pull_finished(self, success, output):
        self.btn_push.setEnabled(True)
        self.btn_pull.setEnabled(True)
        if success:
            self.git_log.append("✅ Изменения успешно скачаны!")
            self.git_log.append("⚠️ Пожалуйста, закройте и откройте программу заново, чтобы она подхватила новую базу данных.")
        else:
            self.git_log.append("❌ Ошибка при скачивании (возможно, база данных занята):")
            self.git_log.append(output)
            self.git_log.append("\n💡 Попробуйте закрыть программу, открыть снова и нажать Скачать еще раз.")