# Facebook Scraper with VNC Remote Browser

This setup allows you to run a persistent browser session on your Digital Ocean VPS and control it remotely through VNC, perfect for logging into Facebook and saving credentials for automated scraping.

## 🚀 Quick Start

### 1. Install Dependencies (if needed)
```bash
# Run this if you need to install VNC packages
sudo chmod +x /root/facebook_scraper/setup_vnc.sh
sudo /root/facebook_scraper/setup_vnc.sh
```

### 2. Test VNC Setup
```bash
python3 /root/facebook_scraper/test_vnc.py
```

### 3. Start the Browser Session
```bash
cd /root/facebook_scraper
python3 simple_browser.py
```

## 🖥️ Accessing the Remote Browser

### Option A: Direct Access (if server allows)
Open in your browser: `http://157.230.176.33:6080/vnc.html`

### Option B: SSH Tunnel (Recommended)
1. Create SSH tunnel from your local machine:
   ```bash
   ssh -L 6080:localhost:6080 root@157.230.176.33
   ```
2. Open in your local browser: `http://localhost:6080/vnc.html`

## 📋 Step-by-Step Usage

1. **Start the script**: Run `python3 simple_browser.py`
2. **Access VNC**: Open the VNC URL in your browser
3. **Log into Facebook**: Complete login in the remote browser
4. **Save session**: Press `Ctrl+C` in terminal when done
5. **Future use**: Your session is saved in `~/.facebook_scraper_data/`

## 🔧 What the Improved Code Does

### Enhanced VNC Management
- ✅ Automatically detects and installs missing dependencies
- ✅ Robust startup with error checking
- ✅ Better display settings (1366x768 with OpenGL support)
- ✅ Automatic public IP detection
- ✅ Clear access instructions

### Persistent Browser Session
- ✅ Saves login cookies and session data
- ✅ Detects existing sessions on restart
- ✅ Enhanced browser settings for better compatibility
- ✅ Automatic Facebook navigation
- ✅ Session status tracking

### Error Handling & Monitoring
- ✅ Comprehensive error messages
- ✅ Process monitoring and cleanup
- ✅ Network connectivity checks
- ✅ Graceful shutdown handling

## 📁 Files Created/Modified

- `simple_browser.py` - Main browser automation script
- `setup_vnc.sh` - VNC installation script  
- `test_vnc.py` - VNC setup verification
- `start_vnc.sh` - Improved VNC startup script
- Session data stored in: `~/.facebook_scraper_data/`

## 🔍 Troubleshooting

### If VNC doesn't start:
```bash
# Check what's running
ps aux | grep -E "(Xvfb|x11vnc|websockify)"

# Restart VNC manually
/root/start_vnc.sh
```

### If browser doesn't appear:
- Make sure VNC is accessible in your browser
- Check that DISPLAY is set to :1
- Verify Playwright dependencies: `playwright install chromium`

### If login doesn't save:
- Check permissions on `~/.facebook_scraper_data/`
- Look for session_info.json file
- Make sure to press Ctrl+C (not close browser directly)

## 🎯 Next Steps for Automation

Once you have a saved session, you can:
1. Create automated scraping scripts that reuse the saved session
2. Run headless scraping (no VNC needed after login)
3. Scale up with multiple saved sessions
4. Set up scheduled scraping tasks

The persistent session data ensures you don't need to log in manually every time!
