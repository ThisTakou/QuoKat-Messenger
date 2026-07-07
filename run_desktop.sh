#!/bin/bash
echo "Installing dependencies..."
pip install PyQt5 cryptography "qrcode[pil]" --quiet --break-system-packages 2>/dev/null \
  || pip install PyQt5 cryptography "qrcode[pil]" --quiet
echo ""
echo "Launching QuoKat Desktop..."
python3 quokat_desktop.py
