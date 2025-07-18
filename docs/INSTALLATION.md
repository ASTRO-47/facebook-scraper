# Facebook Scraper Installation Guide

## 📋 Prerequisites

- Python 3.8 or higher
- Ubuntu/Debian Linux (for Digital Ocean)
- SSH access with X11 forwarding support

## 🚀 Installation Steps

### 1. **System Dependencies (Ubuntu/Debian)**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install -y python3 python3-pip python3-venv

# Install X11 and system dependencies
sudo apt install -y x11-utils xauth

# Install browser dependencies for Playwright
sudo apt install -y \
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
    libgtk-3-0 \
    libgdk-pixbuf2.0-0
```

### 2. **Setup SSH X11 Forwarding**

```bash
# Edit SSH config
sudo nano /etc/ssh/sshd_config

# Ensure these lines are set:
# X11Forwarding yes
# X11DisplayOffset 10
# X11UseLocalhost yes

# Restart SSH service
sudo systemctl restart sshd
```

### 3. **Project Setup**

```bash
# Navigate to your project directory
cd /path/to/facebook_scraper

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers (IMPORTANT!)
playwright install chromium

# Install Playwright system dependencies
playwright install-deps
```

### 4. **Directory Structure Setup**

```bash
# Create required directories
mkdir -p static/screenshots
mkdir -p static/output
mkdir -p templates

# Set proper permissions
chmod 755 static/
chmod 755 static/screenshots/
chmod 755 static/output/
```

### 5. **Verify Installation**

```bash
# Test X11 forwarding (from local machine)
ssh -X user@your-server-ip
xclock  # Should show a clock on your local machine

# Test Playwright installation
python3 -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"

# Test FastAPI
python3 -c "import fastapi; print('FastAPI OK')"
```

## 🖥️ **Usage**

### **Manual Login (First Time Setup)**
```bash
# Connect with X11 forwarding
ssh -X root@your-server-ip

# Run manual login
python3 login_manual.py
```

### **Web Interface**
```bash
# Start the web server
python3 main.py

# Access from browser: http://your-server-ip:8080
```

### **Command Line Interface**
```bash
# Direct scraping
python3 fb_scraper_cli.py username --headless
```

## 🔧 **Troubleshooting**

### **X11 Issues:**
```bash
# Check DISPLAY variable
echo $DISPLAY

# Test X11 connection
xset q

# Install missing X11 tools
sudo apt install -y x11-apps
```

### **Playwright Issues:**
```bash
# Reinstall browsers
playwright install chromium --force

# Check browser installation
playwright install-deps
```

### **Permission Issues:**
```bash
# Fix permissions
sudo chown -R $USER:$USER /path/to/facebook_scraper
chmod +x *.py
```

## 📦 **File Checklist**

Make sure you have these files:
- ✅ `main.py` - Web interface
- ✅ `login_manual.py` - Manual login script
- ✅ `fb_scraper_cli.py` - CLI interface
- ✅ `requirements.txt` - Dependencies
- ✅ `scraper/` directory - Core modules
- ✅ `templates/` directory - HTML templates
- ✅ `static/` directory - Static files

## 🌐 **Network Configuration**

### **Firewall (if needed):**
```bash
# Allow port 8080 for web interface
sudo ufw allow 8080
```

### **Digital Ocean Specific:**
- Ensure your droplet has X11 forwarding enabled
- Consider using a droplet with at least 2GB RAM
- Choose a region close to your location for better X11 performance

## 🎉 **Ready to Use!**

Your Facebook scraper is now ready to use on the new machine! 