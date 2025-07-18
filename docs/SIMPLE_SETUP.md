# 🚀 Simple Local Proxy Setup (Digital Ocean Only)

## What This Does
- Routes your Digital Ocean traffic through your home IP
- Facebook sees your residential IP instead of datacenter IP
- Uses SSH SOCKS proxy (built into SSH)
- The scraper already uses **Playwright** browser

## ⚡ **TWO COMMANDS TO RUN ON DIGITAL OCEAN:**

### 1. Setup SOCKS Proxy
```bash
# Replace YOUR_LOCAL_IP and YOUR_USERNAME with your home details
python3 simple_local_proxy.py --local-host YOUR_LOCAL_IP --local-user YOUR_USERNAME

# Example:
# python3 simple_local_proxy.py --local-host 98.76.54.321 --local-user john
```

### 2. Run Facebook Scraper
```bash
# In a new terminal (keep the proxy running)
python3 main.py

# Navigate to: http://localhost:8080
```

## 🧪 **Test Commands:**

### Test Your IP Without Proxy:
```bash
curl http://httpbin.org/ip
# Shows: Digital Ocean IP
```

### Test Your IP With SOCKS Proxy:
```bash
curl --socks5 127.0.0.1:9999 http://httpbin.org/ip
# Shows: Your HOME IP
```

### Test Scraper Proxy Status:
```bash
curl http://localhost:8080/proxy/current
# Shows: {"type": "local", "url": "socks5://127.0.0.1:9999"}
```

## 🎯 **Expected Results:**

When you run the scraper:
```
🌊 Creating SOCKS proxy to john@98.76.54.321...
✅ SOCKS proxy established on port 9999
🧪 Testing SOCKS proxy on port 9999...
✅ SOCKS proxy working! Your IP appears as: 98.76.54.321
✅ Scraper updated to use SOCKS proxy: socks5://127.0.0.1:9999
🎉 Setup complete!
```

Then when scraping:
```
🏠 Using local proxy: socks5://127.0.0.1:9999
✅ SOCKS5 proxy working! IP: 98.76.54.321
🎯 Starting scrape for username...
```

## 📋 **Requirements:**
- SSH access to your local machine from Digital Ocean
- Your local machine must have SSH server running
- No additional software needed on local machine

## 🛑 **To Stop:**
- Press `Ctrl+C` in the terminal running `simple_local_proxy.py`

That's it! Facebook now sees your home IP instead of Digital Ocean IP. 