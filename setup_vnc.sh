#!/bin/bash

echo "🔧 Setting up VNC server for Facebook scraper..."
echo "This will install all required packages for remote browser access"

# Update package list
echo "📦 Updating package list..."
sudo apt update

# Install required packages
echo "📥 Installing VNC and browser dependencies..."
sudo apt install -y \
    xvfb \
    x11vnc \
    novnc \
    websockify \
    chromium-browser \
    fonts-liberation \
    fonts-noto-color-emoji \
    xfonts-cyrillic \
    xfonts-100dpi \
    xfonts-75dpi \
    xfonts-scalable \
    xfonts-base

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip3 install playwright
playwright install chromium

# Create VNC directory
echo "📁 Creating VNC directory..."
mkdir -p /root/.vnc

# Make scripts executable
chmod +x /root/start_vnc.sh
chmod +x /root/facebook_scraper/simple_browser.py

echo ""
echo "✅ VNC setup complete!"
echo ""
echo "🚀 To use the Facebook scraper:"
echo "1. Run: python3 /root/facebook_scraper/simple_browser.py"
echo "2. Open the VNC URL in your browser"
echo "3. Log in to Facebook in the remote browser"
echo "4. Press Ctrl+C when done to save session"
echo ""
echo "💡 Access VNC via SSH tunnel:"
echo "   ssh -L 6080:localhost:6080 user@your-server"
echo "   Then open: http://localhost:6080/vnc.html"
echo ""
