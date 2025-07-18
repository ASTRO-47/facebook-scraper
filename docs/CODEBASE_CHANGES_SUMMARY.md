# Codebase Changes Summary

## Changes Made on July 16, 2025

### 1. Browser Headless Mode Changes

**Changed all browser instances to run in headless mode by default:**

- `account_recovery.py`: Changed both playwright contexts to `headless=True`
- `account_warming.py`: Changed to `headless=True`
- `scraper/session.py`: Changed default parameter to `headless=True`
- `checkpoint_status.py`: Changed to `headless=True`
- `checkpoint_test.py`: Changed to `headless=True`
- `test_session.py`: Changed both sessions to `headless=True`
- `test_security.py`: Changed to `headless=True`
- `test_international_login.py`: Changed both instances to `headless=True`
- `manual_browser.py`: Changed to `headless=True`
- `load_cookies.py`: Changed to `headless=True`
- `fb_scraper_cli.py`: Changed default parameter to `headless=True`
- `test_improved_scraper.py`: Changed default parameter to `headless=True`
- `main.py`: Changed default scrape_profile parameter to `headless=True`

**Exception kept:**
- `login_manual.py`: Kept `headless=False` since it's specifically for manual login

### 2. Friends Scraping Functionality Removed

**Removed friends-only scraping features:**

- `main.py`:
  - Disabled `/api/quick/{username}` endpoint (returns deprecation message)
  - Disabled `/quick-test/{username}` endpoint (returns deprecation message)
  - Removed friends statistics from extraction output
  - Removed friends count from PDF generation
  - Updated API documentation to remove quick friends references
  - Removed friends timeout logic in scraping loop

- `scraper/json_builder.py`:
  - Removed `friends` field from profile JSON structure
  - Removed `_format_friends()` method
  - Removed friends count from statistics counting

### 3. Test Scraper Functionality Removed

**Disabled test scraper endpoints:**

- `main.py`:
  - Disabled `/test/{username}` endpoint (returns deprecation message)
  - Removed test_scraper references from API documentation

### 4. Impact Summary

**What still works:**
- Full profile scraping via `/api/scrape/{username}` and `/scrape/{username}`
- All data except friends list: groups, pages followed, following, posts, comments, locations
- PDF and JSON downloads
- VNC support
- Proxy functionality
- Cookie management
- All stealth features

**What was removed:**
- Friends list scraping
- Quick friends-only test endpoints
- Test scraper endpoints
- Friends statistics in output

**Benefits:**
- Faster scraping (no friends list processing)
- Reduced Facebook detection risk
- Simplified codebase
- All browsers run headless by default for better performance
- Cleaner API with focused functionality

### 5. Usage Changes

**Before:**
```bash
# These no longer work:
curl http://server:8080/api/quick/username -o friends.json
curl http://server:8080/test/username
```

**After:**
```bash
# Use this for all scraping:
curl http://server:8080/api/scrape/username -o profile.json
```

The scraping will now focus on:
- Profile information
- Groups
- Pages followed  
- Following list
- Posts (own, tagged)
- Comments
- Locations

All browsers run in headless mode by default for better performance and security.
