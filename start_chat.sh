#!/bin/bash

# P2P Messenger Launcher for Linux/Mac
# ====================================

echo ""
echo "========================================"
echo "  P2P Messenger - Linux/Mac Launcher"
echo "========================================"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed"
    echo "Please install Python 3:"
    echo "  Ubuntu/Debian: sudo apt-get install python3 python3-pip"
    echo "  macOS: brew install python3"
    exit 1
fi

echo "[OK] Python found:"
python3 --version
echo ""

# Check if cryptography is installed
echo "[*] Checking dependencies..."
python3 -c "import cryptography" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[*] Installing cryptography library..."
    pip3 install cryptography
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to install cryptography"
        exit 1
    fi
fi

# Check if qrcode is installed
python3 -c "import qrcode" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[*] Installing qrcode library (for QR code generation)..."
    pip3 install qrcode[pil]
    if [ $? -ne 0 ]; then
        echo "[WARNING] Could not install qrcode - QR codes will be disabled"
    fi
fi

echo "[OK] All dependencies installed"
echo ""

# Run the messenger
echo "[*] Starting P2P Messenger..."
echo ""

python3 chat.py
