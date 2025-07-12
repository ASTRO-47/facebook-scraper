#!/bin/bash

# Facebook Scraper - Automated Setup Script
# For Ubuntu/Debian systems (Digital Ocean)

set -e  # Exit on any error

echo "🚀 Facebook Scraper - Automated Setup"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_warning "Running as root. This is okay for Digital Ocean."
fi

# 1. Update system
print_status "Updating system packages..."
apt update && apt upgrade -y

# 2. Install Python and basic tools
print_status "Installing Python and basic tools..."
apt install -y python3 python3-pip python3-venv curl wget git

# 3. Install X11 and system dependencies
print_status "Installing X11 and system dependencies..."
apt install -y x11-utils xauth

# 4. Install browser dependencies for Playwright
print_status "Installing browser dependencies..."
apt install -y \
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgtk-3-0 \
    libxss1 \
    libasound2 \
    libxrandr2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libcairo-gobject2 \
    libgdk-pixbuf2.0-0 \
    libgconf-2-4 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libxtst6 \
    libnss3-dev \
    libgconf-2-4

# 5. Configure SSH for X11 forwarding
print_status "Configuring SSH for X11 forwarding..."
if ! grep -q "X11Forwarding yes" /etc/ssh/sshd_config; then
    echo "X11Forwarding yes" >> /etc/ssh/sshd_config
fi
if ! grep -q "X11DisplayOffset 10" /etc/ssh/sshd_config; then
    echo "X11DisplayOffset 10" >> /etc/ssh/sshd_config
fi
if ! grep -q "X11UseLocalhost yes" /etc/ssh/sshd_config; then
    echo "X11UseLocalhost yes" >> /etc/ssh/sshd_config
fi

# Restart SSH service
systemctl restart sshd
print_status "SSH configured for X11 forwarding"

# 6. Create project directories
print_status "Creating project directories..."
mkdir -p static/screenshots
mkdir -p static/output
mkdir -p templates

# Set proper permissions
chmod 755 static/
chmod 755 static/screenshots/
chmod 755 static/output/

# 7. Setup Python environment
print_status "Setting up Python virtual environment..."

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# 8. Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# 9. Install Playwright browsers
print_status "Installing Playwright browsers..."
playwright install chromium

# Install Playwright system dependencies
playwright install-deps

# 10. Test installations
print_status "Testing installations..."

# Test Python imports
python3 -c "import fastapi; print('FastAPI: OK')" || print_error "FastAPI import failed"
python3 -c "from playwright.sync_api import sync_playwright; print('Playwright: OK')" || print_error "Playwright import failed"

# Test X11 tools
which xset > /dev/null && print_status "X11 tools: OK" || print_warning "X11 tools may need manual installation"

# 11. Create systemd service (optional)
print_status "Creating systemd service file..."
cat > /etc/systemd/system/facebook-scraper.service << EOF
[Unit]
Description=Facebook Scraper Web Interface
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
print_status "Systemd service created (not started)"

# 12. Setup firewall
print_status "Configuring firewall..."
if command -v ufw > /dev/null; then
    ufw allow 8080
    print_status "Port 8080 opened for web interface"
fi

# 13. Final setup
print_status "Final setup..."

# Create a simple start script
cat > start.sh << 'EOF'
#!/bin/bash
source venv/bin/activate
python3 main.py
EOF

chmod +x start.sh

# Create login script
cat > login.sh << 'EOF'
#!/bin/bash
source venv/bin/activate
python3 login_manual.py
EOF

chmod +x login.sh

print_status "Setup completed successfully!"

echo ""
echo "🎉 SETUP COMPLETE!"
echo "=================="
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Connect with X11 forwarding:"
echo "   ssh -X root@your-server-ip"
echo ""
echo "2. Test X11 forwarding:"
echo "   xclock"
echo ""
echo "3. Run manual login (first time):"
echo "   ./login.sh"
echo ""
echo "4. Start web interface:"
echo "   ./start.sh"
echo "   # Access: http://your-server-ip:8080"
echo ""
echo "5. Or use systemd service:"
echo "   systemctl start facebook-scraper"
echo "   systemctl enable facebook-scraper"
echo ""
echo "📁 Project structure:"
echo "   - ./start.sh       - Start web interface"
echo "   - ./login.sh       - Manual login setup"
echo "   - main.py          - Web interface"
echo "   - login_manual.py  - Manual login script"
echo "   - fb_scraper_cli.py - CLI interface"
echo ""
print_status "Ready to use!" 