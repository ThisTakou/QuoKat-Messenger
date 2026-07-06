@echo off
REM P2P Messenger Launcher for Windows
REM ====================================

echo.
echo ========================================
echo  P2P Messenger - Windows Launcher
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo [OK] Python found:
python --version
echo.

REM Check if cryptography is installed, if not install it
echo [*] Checking dependencies...
python -c "import cryptography" >nul 2>&1
if errorlevel 1 (
    echo [*] Installing cryptography library...
    pip install cryptography
    if errorlevel 1 (
        echo [ERROR] Failed to install cryptography
        pause
        exit /b 1
    )
)

REM Check if qrcode is installed, if not install it
python -c "import qrcode" >nul 2>&1
if errorlevel 1 (
    echo [*] Installing qrcode library (for QR code generation)...
    pip install qrcode[pil]
    if errorlevel 1 (
        echo [WARNING] Could not install qrcode - QR codes will be disabled
    )
)

echo [OK] All dependencies installed
echo.

REM Run the messenger
echo [*] Starting P2P Messenger...
echo.

python chat.py

pause
