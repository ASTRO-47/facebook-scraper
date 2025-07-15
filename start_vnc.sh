#!/bin/bash

echo "🚀 Starting VNC Server..."

# Kill any existing processes
echo "🧹 Cleaning up existing processes..."
pkill -f "Xvfb\|x11vnc\|websockify\|fluxbox" 2>/dev/null || true
sleep 2

# Start Xvfb (virtual display)
echo "🖥️  Starting Xvfb virtual display..."
Xvfb :1 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset > /dev/null 2>&1 &
sleep 2

# Set display environment
export DISPLAY=:1
echo "📺 Display set to :1"

# Start window manager
echo "🪟 Starting Fluxbox window manager..."
fluxbox > /dev/null 2>&1 &
sleep 2

# Start x11vnc server
echo "🔗 Starting x11vnc server on port 5901..."
x11vnc -display :1 -nopw -listen 0.0.0.0 -xkb -rfbport 5901 -forever -shared > /dev/null 2>&1 &
sleep 2

# Start NoVNC web interface with proper web root
echo "🌐 Starting NoVNC web interface on port 6080..."
websockify --web /usr/share/novnc 6080 localhost:5901 > /dev/null 2>&1 &
sleep 2

# Get server IP
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")

echo ""
echo "✅ VNC Server is running!"
echo "🌐 Web Access: http://$SERVER_IP:6080/vnc.html"
echo "📱 VNC Client: $SERVER_IP:5901"
echo "📺 Display: :1"
echo ""
echo "🚀 To start the scraper:"
echo "   DISPLAY=:1 python3 main.py"
echo ""
echo "🛑 To stop VNC server:"
echo "   pkill -f \"Xvfb\\|x11vnc\\|websockify\\|fluxbox\""
echo "" 