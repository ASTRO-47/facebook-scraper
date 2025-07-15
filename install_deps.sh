#!/bin/bash

# Simple dependency installation script for Facebook scraper

set -e

echo "🚀 Installing Facebook Scraper Dependencies"
echo "==========================================="

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install essential packages
echo "🔧 Installing essential packages..."
sudo apt install -y curl wget gnupg software-properties-common

# Install Python 3 and pip
echo "🐍 Installing Python 3 and pip..."
sudo apt install -y python3 python3-pip python3-venv python3-dev build-essential

# Install Google Chrome
echo "🌐 Installing Google Chrome..."
if ! command -v google-chrome &> /dev/null; then
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
    sudo apt update
    sudo apt install -y google-chrome-stable
fi

# Install Xvfb for virtual display
echo "🖥️ Installing virtual display..."
sudo apt install -y xvfb

# Install browser dependencies
echo "🔗 Installing browser dependencies..."
sudo apt install -y libgtk-3-dev libgbm-dev libxss1 libasound2

# Create project directory and venv
echo "📁 Setting up project..."
mkdir -p ~/facebook-scraper
cd ~/facebook-scraper
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install playwright asyncio requests beautifulsoup4 selenium fake-useragent

# Install Playwright browsers
echo "🎭 Installing Playwright browsers..."
playwright install
playwright install-deps

echo "✅ Installation complete!"
echo "To use: cd ~/facebook-scraper && source venv/bin/activate" 