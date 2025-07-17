#!/bin/bash

# Facebook Scraper Service Startup Script
# This script ensures proper environment setup before starting the service

set -e

echo "🚀 Starting Facebook Scraper Service..."

# Change to the project directory
cd /root/facebook-scraper

# Activate virtual environment
source venv/bin/activate

# Ensure Chrome is available
if ! command -v google-chrome-stable &> /dev/null; then
    echo "❌ Google Chrome not found. Installing..."
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
    apt update
    apt install -y google-chrome-stable
fi

# Ensure Playwright browsers are installed
echo "🔧 Installing Playwright browsers..."
playwright install chromium

# Set up display for headless mode
export DISPLAY=:1
export XAUTHORITY=/root/.Xauthority

# Create necessary directories
mkdir -p /root/.config
mkdir -p /root/.cache
mkdir -p /tmp/playwright

# Start the service
echo "✅ Environment ready. Starting main application..."
exec python main.py 