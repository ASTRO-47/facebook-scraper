# 🇲🇦 Morocco Proxy Setup Guide

This guide explains how to use the **FREE Morocco proxy functionality** that makes Facebook think you're connecting from Morocco, reducing security checkpoints and improving scraping success.

## 🎯 What This Does

- **Automatically fetches free Moroccan proxies** from multiple sources
- **Tests proxies** to ensure they work
- **Rotates between working proxies** for reliability
- **Prioritizes Moroccan IPs** but falls back to nearby countries (Algeria, Tunisia)
- **Reduces Facebook security checkpoints** for Moroccan accounts

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install aiohttp==3.9.1
# or update all dependencies
pip install -r requirements.txt
```

### 2. Test Proxy System
```bash
python test_proxy.py
```

This will show you:
- ✅ If proxies are working
- 🌍 Your apparent location
- 📊 Available proxy count

### 3. Use with Scraper

**API Usage:**
```bash
# With Morocco proxy (default)
curl "http://localhost:8080/scrape/john.doe?use_morocco_proxy=true"

# Without proxy
curl "http://localhost:8080/scrape/john.doe?use_morocco_proxy=false"
```

**Python Usage:**
```python
# The scraper now automatically uses Morocco proxies by default
# You'll see output like:
# 🌍 Fetching working Morocco proxy...
# 🇲🇦 Using proxy from: Morocco, Casablanca
# 📍 Proxy IP: http://41.77.129.154:3128
```

## 📊 Monitoring Proxy Status

### Health Check
```bash
curl http://localhost:8080/health
```
Shows: Available proxies, Moroccan proxy count, last refresh time

### Detailed Proxy Status
```bash
curl http://localhost:8080/proxy/status
```
Shows: All proxy details, countries, refresh times

### Test Current Proxy
```bash
curl http://localhost:8080/proxy/test
```
Tests a proxy and shows your apparent location

### Manually Refresh Proxies
```bash
curl -X POST http://localhost:8080/proxy/refresh
```

## 🔧 How It Works

### Proxy Sources
1. **proxy-list.download API** - Country-specific (Morocco priority)
2. **proxyscrape.com API** - General and Morocco-specific
3. **Backup hardcoded list** - Known working Moroccan proxies

### Proxy Testing
- Tests each proxy with `httpbin.org/ip`
- Verifies response time < 10 seconds
- Checks if proxy actually works
- Gets location information

### Smart Selection
- **Moroccan proxies first** (🇲🇦 MA)
- **North African backup** (🇩🇿 DZ, 🇹🇳 TN, 🇪🇬 EG)
- **Automatic rotation** between working proxies
- **Hourly refresh** of proxy list

## 🎯 Benefits for Facebook Scraping

### ✅ Reduces Security Issues
- Fewer "suspicious location" alerts
- Less likely to trigger 2FA requests
- Matches expected account location

### ✅ Better Success Rate
- Fewer redirect loops
- Less aggressive rate limiting
- More consistent access

### ✅ Realistic Behavior
- Appears as normal Moroccan user
- Reduces automation detection
- Natural IP geolocation

## 🚨 Important Notes

### Legal & Ethical
- **Only use with your own accounts**
- **Respect Facebook's terms of service**
- **Don't use for malicious purposes**

### Technical Limitations
- **Free proxies can be slow** (5-15 seconds response time)
- **Proxies may go offline** (automatic rotation helps)
- **Not 100% reliable** (has fallback to no proxy)

### Privacy
- **Free proxies are shared** - don't send sensitive data
- **Your traffic goes through third parties**
- **Use only for non-sensitive automation**

## 🛠️ Troubleshooting

### No Working Proxies
```bash
# Check your internet connection
ping google.com

# Try manual refresh
curl -X POST http://localhost:8080/proxy/refresh

# Test without proxy
curl "http://localhost:8080/scrape/john.doe?use_morocco_proxy=false"
```

### Slow Performance
- **Normal for free proxies** - expect 5-15 second delays
- **Quality varies** - some proxies are faster than others
- **Try refreshing** to get different proxies

### Connection Errors
- **Proxy may have died** - automatic rotation will try next one
- **Firewall blocking** - check your network settings
- **API sources down** - uses backup hardcoded list

## 📈 Advanced Usage

### Custom Proxy Integration
If you have premium Morocco proxies, you can modify `scraper/proxy_manager.py`:

```python
# Add your premium proxies to _get_backup_proxies()
backup_proxies = [
    {'ip': 'your-premium-proxy.com', 'port': '8080', 'type': 'http', 'country': 'MA', 'source': 'premium'},
    # ... more proxies
]
```

### Monitoring
- Check logs for proxy status
- Monitor `/proxy/status` endpoint
- Set up alerts for proxy failures

## 🔄 Automatic Features

### Self-Healing
- **Dead proxy detection** - removes non-working proxies
- **Automatic refresh** - gets new proxies every hour
- **Fallback behavior** - continues without proxy if none work

### Load Balancing
- **Round-robin rotation** through working proxies
- **Country prioritization** (Morocco → North Africa → Others)
- **Performance-based selection**

---

## 🎉 Success Indicators

When working correctly, you'll see:
```
🌍 Fetching working Morocco proxy...
✅ Found working proxy: http://41.77.129.154:3128
🇲🇦 Using proxy from: Morocco, Casablanca
📍 Proxy IP: http://41.77.129.154:3128
🎯 Starting scrape for input: john.doe
✅ Login successful!
```

This means Facebook sees you as connecting from Morocco! 🇲🇦 