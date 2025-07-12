# Facebook Scraper - SSH X11 Forwarding Setup

## Overview

This setup uses SSH X11 forwarding to display the browser directly on your local machine, eliminating the need for VNC servers or web-based remote access.

## ✅ **Advantages of SSH X11 Forwarding**

- **Simpler setup**: No VNC server configuration needed
- **Better performance**: Direct X11 forwarding is faster than VNC
- **Native experience**: Browser runs as if it's local
- **More secure**: No web-based VNC interface exposed
- **Less resource usage**: No additional server processes

## 🚀 **Quick Start Guide**

### Step 1: Connect with X11 Forwarding

From your **local machine**, connect to your server:

```bash
# Basic X11 forwarding
ssh -X user@your-server-ip

# For better performance (trusted X11 forwarding)
ssh -Y user@your-server-ip

# With compression for slower connections
ssh -XC user@your-server-ip
```

### Step 2: Test X11 Forwarding

Once connected, test that X11 forwarding works:

```bash
# Test with a simple X11 application
xclock

# Or test X11 settings
xset q
```

If a clock appears on your local machine, X11 forwarding is working correctly! ✅

### Step 3: Manual Facebook Login

Run the browser setup script:

```bash
cd /path/to/facebook_scraper
python3 login_manual.py
```

**What happens:**
- Browser opens **on your local machine** 
- Navigate and login to Facebook normally
- Complete any security verifications
- Press Ctrl+C when done to save session

### Step 4: Run the Scraper

```bash
python3 main.py
```

Then open your browser to: `http://localhost:8080`

## 🔧 **Detailed Setup Instructions**

### Prerequisites

1. **Local Machine Requirements:**
   - X11 server running (Linux/macOS with XQuartz)
   - SSH client with X11 forwarding support

2. **Server Requirements:**
   - X11 forwarding enabled in SSH config
   - Playwright and dependencies installed

### Enable X11 Forwarding on Server

Edit SSH configuration:

```bash
sudo nano /etc/ssh/sshd_config
```

Ensure these settings:

```
X11Forwarding yes
X11DisplayOffset 10
X11UseLocalhost yes
```

Restart SSH service:

```bash
sudo systemctl restart sshd
```

### Install X11 Dependencies on Server

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y x11-utils xauth

# CentOS/RHEL
sudo yum install -y xorg-x11-utils xauth
```

### Install Playwright

```bash
pip install playwright
playwright install chromium
```

## 🖥️ **Platform-Specific Setup**

### Linux (Local Machine)

X11 should work out of the box with most Linux distributions.

### macOS (Local Machine)

Install XQuartz:

```bash
# Using Homebrew
brew install --cask xquartz

# Or download from: https://www.xquartz.org/
```

**Important**: Log out and log back in after installing XQuartz.

### Windows (Local Machine)

Install an X11 server:

1. **VcXsrv** (recommended): https://sourceforge.net/projects/vcxsrv/
2. **Xming**: http://www.straightrunning.com/XmingNotes/
3. **X410** (paid): Microsoft Store

**VcXsrv Configuration:**
- Start VcXsrv with default settings
- Enable "Disable access control"
- Use SSH client like PuTTY or Windows Terminal

## 🌍 **International Account Support**

The scraper includes specific support for international accounts (like Moroccan accounts accessing from US servers):

### Enhanced Features:
- **Multi-domain attempts**: Tries different Facebook regional domains
- **Extended timeouts**: Allows more time for security verifications
- **Language support**: Handles Arabic and French security prompts
- **Location verification**: Guides through "This Was Me" prompts

### Expected Security Prompts:
- "Login from new location" - Choose "This Was Me"
- Phone/email verification - Complete as requested
- ID verification - Use real documents if requested
- Security questions - Answer honestly

## 🐛 **Troubleshooting**

### "No DISPLAY variable found"

```bash
# Check if DISPLAY is set
echo $DISPLAY

# Should show something like: localhost:10.0
```

**Solution**: Reconnect with proper X11 forwarding:
```bash
ssh -X user@server
```

### "X11 connection test failed"

```bash
# Test X11 manually
xset q
```

**Solutions:**
1. Install X11 tools: `sudo apt install x11-utils`
2. Check SSH config allows X11 forwarding
3. Restart SSH service on server

### "Browser fails to launch"

**Solutions:**
1. Install Playwright browsers: `playwright install chromium`
2. Check X11 forwarding: `xclock`
3. Verify DISPLAY variable: `echo $DISPLAY`

### "Connection timeout/slow"

**Solutions:**
1. Use compression: `ssh -XC user@server`
2. Use trusted forwarding: `ssh -Y user@server`
3. Check network latency between machines

### "Permission denied" errors

**Solutions:**
1. Check file permissions in user data directory
2. Verify SSH user has proper permissions
3. Run with sudo if necessary (not recommended)

## 📊 **Performance Tips**

### For Better Performance:

```bash
# Use trusted X11 forwarding (faster)
ssh -Y user@server

# Use compression for slow connections
ssh -XC user@server

# Combine both
ssh -YC user@server
```

### For Slower Connections:

- Use mobile Facebook version: `m.facebook.com`
- Run browser in lower resolution
- Disable images in browser if possible

## 🔒 **Security Considerations**

### X11 Forwarding Security:

- **Trusted forwarding (-Y)**: Faster but less secure
- **Untrusted forwarding (-X)**: Slower but more secure
- **Local connections only**: X11 traffic stays on SSH tunnel

### Recommendations:

- Only use on trusted networks
- Use strong SSH authentication (keys preferred)
- Consider VPN for additional security
- Monitor SSH access logs

## 📝 **Usage Examples**

### Basic Usage:

```bash
# Connect with X11 forwarding
ssh -X user@your-server

# Run login setup
python3 login_manual.py
# Login manually in browser, press Ctrl+C when done

# Start scraper
python3 main.py
# Access via http://localhost:8080
```

### With Compression (slow networks):

```bash
ssh -XC user@your-server
python3 login_manual.py
```

### Trusted Mode (faster):

```bash
ssh -Y user@your-server
python3 login_manual.py
```

## 🎯 **Comparison vs VNC**

| Feature | SSH X11 | VNC |
|---------|---------|-----|
| Setup complexity | ⭐⭐ Simple | ⭐⭐⭐⭐ Complex |
| Performance | ⭐⭐⭐⭐ Fast | ⭐⭐ Slower |
| Security | ⭐⭐⭐⭐ Secure | ⭐⭐⭐ Less secure |
| Resource usage | ⭐⭐⭐⭐ Low | ⭐⭐ Higher |
| Network requirements | SSH only | SSH + HTTP ports |
| Browser experience | ⭐⭐⭐⭐ Native | ⭐⭐⭐ Web-based |

## 💡 **Pro Tips**

1. **Keep sessions alive**: Use `screen` or `tmux` for long-running scrapers
2. **Monitor resources**: Check CPU/RAM usage during scraping
3. **Save sessions**: Always press Ctrl+C to properly save login sessions
4. **Test X11 first**: Always verify X11 works before running scraper
5. **Use compression**: Enable SSH compression for remote connections

---

## 🎉 **Result**

You now have a **simpler, faster, and more secure** Facebook scraping setup using SSH X11 forwarding instead of VNC! 

The browser will appear directly on your local machine, making the experience much more natural and responsive. 