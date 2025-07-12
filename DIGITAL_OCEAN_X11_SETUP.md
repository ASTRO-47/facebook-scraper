# Digital Ocean X11 Setup Guide

## 🎯 Goal
Set up X11 forwarding on your Digital Ocean server so you can see the browser on your local machine for manual Facebook login.

## 📋 Prerequisites
- Digital Ocean droplet (Ubuntu/Debian)
- Local machine with X11 support:
  - **Linux**: Built-in ✅
  - **macOS**: Install XQuartz
  - **Windows**: Install VcXsrv or X410

## 🔧 Step 1: Setup X11 on Digital Ocean Server

### Connect to your server:
```bash
ssh root@your-digital-ocean-ip
```

### Install X11 and dependencies:
```bash
# Update system
apt update && apt upgrade -y

# Install X11 forwarding support
apt install -y xauth x11-apps x11-utils

# Install Chrome/Chromium for Playwright
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
apt update
apt install -y google-chrome-stable

# Install Playwright dependencies
apt install -y libnss3 libnspr4 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgtk-3-0 libxss1 libasound2
```

### Configure SSH for X11 forwarding:
```bash
# Edit SSH config
nano /etc/ssh/sshd_config

# Make sure these lines are set:
X11Forwarding yes
X11DisplayOffset 10
X11UseLocalhost yes

# Restart SSH service
systemctl restart sshd
```

## 🖥️ Step 2: Setup Your Local Machine

### For macOS:
```bash
# Install XQuartz
brew install --cask xquartz
# Log out and log back in after installation
```

### For Windows:
1. Download and install VcXsrv: https://sourceforge.net/projects/vcxsrv/
2. Start VcXsrv with default settings
3. Enable "Disable access control"

### For Linux:
```bash
# Usually works out of the box
# If needed: sudo apt install x11-apps
```

## 🔗 Step 3: Connect with X11 Forwarding

### From your local machine:
```bash
# Basic X11 forwarding
ssh -X root@your-digital-ocean-ip

# For better performance (trusted)
ssh -Y root@your-digital-ocean-ip

# With compression for slow connections
ssh -XC root@your-digital-ocean-ip
```

### Test X11 forwarding:
```bash
# This should open a clock on your LOCAL machine
xclock

# If it works, press Ctrl+C to close it
```

## 📱 Step 4: Run the Login Script

```bash
cd /root/facebook_scraper
python3 login_manual.py
```

**What happens:**
1. Browser opens on your LOCAL machine
2. Navigate to Facebook and login manually
3. Complete any security verifications
4. Press Ctrl+C in terminal when done
5. Cookies are saved automatically

## 🌐 Step 5: Change IP Address (Facebook Block Bypass)

### Option 1: Create New Digital Ocean Droplet
```bash
# 1. Create snapshot of current droplet
# 2. Create new droplet from snapshot in different region
# 3. This gives you a new IP address
```

### Option 2: Use Digital Ocean Reserved IP
```bash
# 1. Go to Digital Ocean dashboard
# 2. Networking > Reserved IPs
# 3. Create new reserved IP
# 4. Assign to your droplet
# 5. Your droplet now has a new public IP
```

### Option 3: Destroy and Recreate Droplet
```bash
# 1. Backup your data/code
# 2. Destroy current droplet
# 3. Create new droplet (automatic new IP)
# 4. Restore your data/code
```

## 🛠️ Troubleshooting

### "No DISPLAY variable"
```bash
# Make sure you connected with X11:
ssh -X root@your-ip

# Check DISPLAY:
echo $DISPLAY
# Should show something like: localhost:10.0
```

### "xclock: command not found"
```bash
# Install X11 apps:
apt install -y x11-apps
```

### "Browser doesn't appear"
```bash
# Check if X11 forwarding is working:
xset q

# If not working, reconnect:
exit
ssh -X root@your-ip
```

### Browser crashes or doesn't start
```bash
# Install missing dependencies:
apt install -y libnss3 libnspr4 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgtk-3-0

# Try running with more verbose output:
python3 login_manual.py
```

## 📝 Current IP Check

### Check your current IP:
```bash
curl ifconfig.me
```

### Check if IP is blocked by Facebook:
```bash
curl -I https://www.facebook.com
# If you get 403 or other errors, IP might be blocked
```

## 🎯 Success Indicators

✅ **X11 Working**: `xclock` opens a window on your local machine  
✅ **Browser Opens**: Chrome/Chromium appears on your local screen  
✅ **Facebook Loads**: You can navigate to facebook.com  
✅ **Cookies Saved**: File `facebook_cookies.json` is created  

## 🚀 Next Steps

After successful manual login:
1. Your cookies are saved in `facebook_cookies.json`
2. You can now modify the main scraper to use these cookies
3. Automation will work without manual login

---

## 💡 Pro Tips

- Use `ssh -Y` for better performance (trusted X11)
- Use `ssh -C` for compression on slow connections  
- Keep terminal open during browser session
- Save your work frequently
- Test with different regions if IP is blocked 