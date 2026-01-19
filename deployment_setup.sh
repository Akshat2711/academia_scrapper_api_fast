#!/bin/bash

# Deployment Setup Script for Academia Fast Scraper API
# This script installs all required system dependencies and Python packages

echo "=========================================="
echo "Academia Fast Scraper - Deployment Setup"
echo "=========================================="

# Update package lists
echo "📦 Updating package lists..."
sudo apt-get update -y

# Install Tesseract OCR (required for CAPTCHA solving)
echo "📦 Installing Tesseract OCR..."
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng

# Install Python dependencies from requirements.txt
echo "📦 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "❌ requirements.txt not found!"
    exit 1
fi

# Verify installation
echo ""
echo "=========================================="
echo "Verifying Installation"
echo "=========================================="

python3 << 'EOF'
try:
    import cv2
    print("✅ OpenCV (cv2) installed")
except ImportError:
    print("❌ OpenCV (cv2) NOT found")

try:
    import numpy
    print("✅ NumPy installed")
except ImportError:
    print("❌ NumPy NOT found")

try:
    import pytesseract
    print("✅ Pytesseract installed")
except ImportError:
    print("❌ Pytesseract NOT found")

import subprocess
try:
    result = subprocess.run(['tesseract', '--version'], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Tesseract binary installed")
    else:
        print("❌ Tesseract binary NOT found")
except FileNotFoundError:
    print("❌ Tesseract binary NOT found")

print("\n✅ Setup Complete!")
print("You can now run: uvicorn app:app --host 0.0.0.0 --port 8000")
EOF
