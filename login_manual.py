#!/usr/bin/env python3
"""
Simple Manual Facebook Login for Digital Ocean X11 Setup

This script:
1. Checks X11 forwarding is working 
2. Opens Chrome/Chromium browser on your LOCAL machine via X11
3. Navigates to Facebook for manual login
4. Saves cookies after you login manually
5. Browser stays open until you press Ctrl+C

Usage:
1. From your local machine: ssh -X root@your-digital-ocean-ip
2. Run: python3 login_manual.py  
3. Login manually in the browser that appears on your local screen
4. Press Ctrl+C when done to save cookies and close
"""

import asyncio
import os
import json
import signal
import sys
import subprocess
from playwright.async_api import async_playwright

class SimpleX11Login:
    def __init__(self):
        self.cookies_file = "facebook_cookies.json"
        self.browser = None
        self.context = None
        self.page = None
        self.should_close = False

    def check_x11_setup(self):
        """Check if X11 forwarding is properly configured"""
        print("🔍 Checking X11 forwarding setup...")
        
        # Check DISPLAY variable
        display = os.environ.get('DISPLAY')
        if not display:
            print("❌ No DISPLAY variable found!")
            print("💡 Make sure you connected with: ssh -X root@your-server")
            return False
        
        print(f"✅ DISPLAY found: {display}")
        
        # Test X11 with a simple command
        try:
            result = subprocess.run(['xset', 'q'], capture_output=True, timeout=10)
            if result.returncode == 0:
                print("✅ X11 is working correctly!")
                return True
            else:
                print("⚠️ X11 test failed, but continuing anyway...")
                return True  # Continue anyway
        except subprocess.TimeoutExpired:
            print("⚠️ X11 test timed out, but continuing...")
            return True
        except FileNotFoundError:
            print("⚠️ xset command not found, installing X11 utils...")
            try:
                subprocess.run(['apt', 'update'], check=True)
                subprocess.run(['apt', 'install', '-y', 'x11-utils'], check=True)
                print("✅ X11 utils installed!")
                return True
            except:
                print("⚠️ Could not install X11 utils, but continuing...")
                return True
        except Exception as e:
            print(f"⚠️ X11 test error: {e}, but continuing...")
            return True

    def setup_interrupt_handler(self):
        """Handle Ctrl+C to save cookies and exit gracefully"""
        def signal_handler(signum, frame):
            print(f"\n🛑 Interrupt received! Saving cookies and closing...")
            self.should_close = True
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def save_cookies(self):
        """Save browser cookies to file"""
        try:
            if self.context:
                cookies = await self.context.cookies()
                with open(self.cookies_file, 'w') as f:
                    json.dump(cookies, f, indent=2)
                print(f"✅ Cookies saved to: {self.cookies_file}")
                print(f"📊 Saved {len(cookies)} cookies")
                return True
        except Exception as e:
            print(f"❌ Error saving cookies: {e}")
            return False

    async def load_existing_cookies(self):
        """Load existing cookies if available"""
        try:
            if os.path.exists(self.cookies_file) and self.context:
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                await self.context.add_cookies(cookies)
                print(f"✅ Loaded {len(cookies)} existing cookies")
                return True
        except Exception as e:
            print(f"⚠️ Could not load existing cookies: {e}")
            return False

    async def open_facebook_browser(self):
        """Open browser and navigate to Facebook"""
        print("🚀 Launching browser for X11 forwarding...")
        
        # Launch Playwright
        playwright = await async_playwright().start()
        
        # Launch browser (will appear on your local machine via X11)
        self.browser = await playwright.chromium.launch(
            headless=False,  # MUST be False for X11
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-extensions',
                '--no-first-run',
                '--start-maximized',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        
        # Create browser context
        self.context = await self.browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # Load existing cookies if any
        await self.load_existing_cookies()
        
        # Create new page
        self.page = await self.context.new_page()
        
        # Add basic stealth
        await self.page.evaluate("""
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            delete window.chrome;
        """)
        
        print("🌐 Navigating to Facebook...")
        await self.page.goto('https://www.facebook.com', wait_until='domcontentloaded')
        
        print("\n" + "="*60)
        print("📱 BROWSER IS NOW OPEN ON YOUR LOCAL MACHINE!")
        print("="*60)
        print("👆 Complete these steps:")
        print("1. 🔐 Login to Facebook manually in the browser")
        print("2. ✅ Complete any security checks") 
        print("3. 🏠 Make sure you reach the main Facebook page")
        print("4. ⌨️ Press Ctrl+C in this terminal when done")
        print("="*60)
        
        # Wait for user interrupt
        try:
            while not self.should_close:
                await asyncio.sleep(1)
        except:
            pass
        
        # Save cookies before closing
        await self.save_cookies()
        
        # Close browser
        await self.browser.close()
        await playwright.stop()
        
        print("✅ Browser closed and cookies saved!")

    async def run(self):
        """Main execution"""
        print("\n🖥️  FACEBOOK MANUAL LOGIN - DIGITAL OCEAN X11")
        print("="*50)
        
        # Check X11 setup
        if not self.check_x11_setup():
            print("\n❌ X11 setup failed. Please:")
            print("1. Disconnect from server")
            print("2. Reconnect with: ssh -X root@your-digital-ocean-ip")
            print("3. Try again")
            return False
        
        # Setup interrupt handler
        self.setup_interrupt_handler()
        
        # Open browser for manual login
        await self.open_facebook_browser()
        
        return True

async def main():
    """Entry point"""
    login = SimpleX11Login()
    try:
        await login.run()
        print("\n🎉 Login session completed!")
        print("💾 Cookies are saved for future automation")
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0) 