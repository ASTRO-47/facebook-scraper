#!/usr/bin/env python3
"""
Facebook Cookie Loader - Run this on cloud machine (Frankfurt)
Loads cookies from facebook_cookies.json and starts browser session
"""

import asyncio
import json
import os
from playwright.async_api import async_playwright

class FacebookCookieLoader:
    def __init__(self):
        self.cookies_file = "facebook_cookies.json"
        self.user_data_dir = os.path.expanduser("~/.facebook_scraper_data")
        
    def load_cookie_data(self):
        """Load cookie data from JSON file"""
        if not os.path.exists(self.cookies_file):
            print(f"❌ Cookie file not found: {self.cookies_file}")
            print("Make sure you've transferred facebook_cookies.json to this directory")
            return None
            
        try:
            with open(self.cookies_file, 'r') as f:
                data = json.load(f)
            print(f"✅ Loaded cookie file: {len(data['cookies'])} cookies")
            return data
        except Exception as e:
            print(f"❌ Error loading cookies: {e}")
            return None
    
    def kill_existing_chrome(self):
        """Kill existing Chrome processes"""
        try:
            import subprocess
            subprocess.run(['pkill', '-f', 'google-chrome'], capture_output=True)
            subprocess.run(['pkill', '-f', self.user_data_dir], capture_output=True)
            
            # Clean up lock files
            lock_file = os.path.join(self.user_data_dir, "SingletonLock")
            if os.path.exists(lock_file):
                os.remove(lock_file)
            print("🧹 Cleaned up existing Chrome processes")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
    
    async def start_browser_with_cookies(self):
        """Start browser and load cookies"""
        # Load cookie data
        cookie_data = self.load_cookie_data()
        if not cookie_data:
            return False
            
        print("🚀 Starting browser with loaded cookies...")
        
        # Clean up existing processes
        self.kill_existing_chrome()
        
        # Ensure user data directory exists
        os.makedirs(self.user_data_dir, exist_ok=True)
        
        async with async_playwright() as p:
            # Launch browser
            context = await p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=True,
                executable_path='/usr/bin/google-chrome-stable',
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--no-first-run',
                    '--disable-default-browser-check',
                    '--disable-blink-features=AutomationControlled',
                    '--exclude-switches=enable-automation'
                ],
                user_agent=cookie_data.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
                viewport={'width': 1366, 'height': 768},
                locale="en-US"
            )
            
            page = await context.new_page()
            
            # Hide automation
            await page.evaluate("""
                Object.defineProperty(navigator, 'webdriver', {get: () => false});
                if (window.chrome && window.chrome.runtime) {
                    delete window.chrome.runtime.onConnect;
                }
            """)
            
            print("🍪 Loading cookies into browser...")
            
            # Add cookies
            try:
                await context.add_cookies(cookie_data['cookies'])
                print(f"✅ Added {len(cookie_data['cookies'])} cookies")
            except Exception as e:
                print(f"⚠️ Cookie loading warning: {e}")
            
            # Navigate to Facebook
            print("🌐 Navigating to Facebook...")
            await page.goto("https://www.facebook.com", wait_until="domcontentloaded")
            
            # Load localStorage if available
            if 'local_storage' in cookie_data:
                try:
                    await page.evaluate("""
                        (storage) => {
                            for (const [key, value] of Object.entries(storage)) {
                                localStorage.setItem(key, value);
                            }
                        }
                    """, cookie_data['local_storage'])
                    print(f"✅ Loaded {len(cookie_data['local_storage'])} localStorage items")
                except Exception as e:
                    print(f"⚠️ localStorage warning: {e}")
            
            # Refresh page to apply all data
            await page.reload(wait_until="domcontentloaded")
            
            print("\n🎉 BROWSER READY WITH COOKIES!")
            print("=" * 50)
            print("✅ Cookies loaded from Morocco session")
            print("🇩🇪 Running from Frankfurt droplet")
            print("🌐 Facebook should be logged in")
            print("=" * 50)
            print("⏳ Browser will stay open - Press Ctrl+C to close")
            
            # Keep browser open
            try:
                while True:
                    await asyncio.sleep(10)
                    print("🔄 Session active... (Press Ctrl+C to close)")
            except KeyboardInterrupt:
                print("\n👋 Closing browser...")
                
            await context.close()
            return True

async def main():
    loader = FacebookCookieLoader()
    
    print("🍪 Facebook Cookie Loader - Step 2 (Cloud)")
    print("=" * 50)
    print("This loads cookies from your Morocco session")
    print("=" * 50)
    
    # Set display for X11
    if not os.environ.get("DISPLAY"):
        os.environ["DISPLAY"] = ":1"
        print("🖥️ Set DISPLAY=:1")
    
    success = await loader.start_browser_with_cookies()
    
    if success:
        print("\n✅ Cookie loading completed!")
    else:
        print("\n❌ Cookie loading failed!")

if __name__ == "__main__":
    asyncio.run(main()) 