@echo off
python -m PyInstaller --noconfirm --clean --onefile --name "Unit_Economics_WB" --icon="wb_icon.ico" --add-data "data;data" --add-data "app;app" main.py
pause