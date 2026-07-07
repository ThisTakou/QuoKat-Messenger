@echo off
chcp 65001 >nul
pip install PyQt5 cryptography --quiet --break-system-packages 2>nul || pip install PyQt5 cryptography --quiet
start "" pythonw "%~dp0quokat_desktop.py"
