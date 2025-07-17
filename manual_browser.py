#!/usr/bin/env python3
"""
Simple script to launch browser and keep it alive for manual testing
"""
import os
import asyncio
import signal
import sys
import subprocess
import glob
from playwright.async_api import async_playwright

class ManualBrowser:
    def __init__(self):
        self.playwright = None
        self.context = None
        self.page = None
        self.running = True
        self.user_data_dir = os.path.join(os.path.expanduser("~"), ".facebook_scraper_data")
        
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print("\n👋 Shutting down browser...")
        self.running = False
        
    def kill_existing_chrome_processes(self):
        """Kill any existing Chrome processes that might be using our profile"""
        try:
            print("🔍 Checking for existing Chrome processes...")
            # Kill Chrome processes using our user data directory
            result = subprocess.run(['pkill', '-f', self.user_data_dir], capture_output=True, text=True)
            
            # Also kill any Chrome processes that might be lingering
            subprocess.run(['pkill', '-f', 'google-chrome'], capture_output=True, text=True)
            
            # Wait a moment for processes to die
            import time
            time.sleep(2)
            
            print("✅ Existing Chrome processes cleaned up")
        except Exception as e:
            print(f"⚠️ Warning during Chrome cleanup: {e}")
            
    def cleanup_lock_files(self):
        """Remove lock files that might prevent Chrome from starting"""
        try:
            print("🧹 Cleaning up lock files...")
            
            # Remove SingletonLock file
            lock_file = os.path.join(self.user_data_dir, "SingletonLock")
            if os.path.exists(lock_file):
                os.remove(lock_file)
                print("✅ Removed SingletonLock file")
                
            # Remove any other lock files
            lock_patterns = [
                os.path.join(self.user_data_dir, "*.lock"),
                os.path.join(self.user_data_dir, "lockfile"),
                os.path.join(self.user_data_dir, "Default", "*.lock"),
                os.path.join(self.user_data_dir, "Default", "lockfile")
            ]
            
            for pattern in lock_patterns:
                for lock_file in glob.glob(pattern):
                    try:
                        os.remove(lock_file)
                        print(f"✅ Removed lock file: {lock_file}")
                    except Exception as e:
                        print(f"⚠️ Could not remove {lock_file}: {e}")
                        
        except Exception as e:
            print(f"⚠️ Warning during lock cleanup: {e}")
            
    def prepare_user_data_dir(self):
        """Prepare user data directory by cleaning up any existing locks"""
        print("🔧 Preparing user data directory...")
        
        # Kill existing processes first
        self.kill_existing_chrome_processes()
        
        # Create directory if it doesn't exist
        os.makedirs(self.user_data_dir, exist_ok=True)
        
        # Clean up lock files
        self.cleanup_lock_files()
        
        print("✅ User data directory prepared")
        
    async def initialize_browser(self):
        """Initialize browser with REAL Google Chrome for extensions"""
        print("🚀 Starting browser with real Google Chrome...")
        
        # Set up display for X11 forwarding
        if not os.environ.get("DISPLAY"):
            os.environ["DISPLAY"] = ":1"
        
        # Prepare user data directory
        self.prepare_user_data_dir()
        
        # Start Playwright
        self.playwright = await async_playwright().start()
        
        # Use REAL Google Chrome for extensions (NOT Playwright's Chromium)
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=True,
            executable_path='/usr/bin/google-chrome-stable',  # Use system Chrome
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--no-first-run',
                '--disable-default-browser-check',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding'
            ],
            viewport={'width': 1366, 'height': 768}
        )
        
        self.page = await self.context.new_page()
        
        print("✅ Browser initialized with REAL Google Chrome - extensions fully supported!")
        return self.page
        
    async def navigate_to_facebook(self):
        """Navigate to Facebook"""
        print("🔗 Navigating to Facebook...")
        try:
            await self.page.goto('https://www.facebook.com', wait_until='domcontentloaded', timeout=30000)
            print("✅ Successfully navigated to Facebook!")
        except Exception as e:
            print(f"⚠️ Navigation failed: {e}")
            print("🔄 You can manually navigate to any site in the browser")
      
    async def install_required_extensions(self):
        """Install UrbanVPN and Friend SSH/Proxy extensions"""
        extensions = [
            {
                "name": "Urban VPN", 
                "url": "https://chrome.google.com/webstore/detail/urban-vpn/eppiocemhmnlbhjplcgkofciiegomcon"
            },
            {
                "name": "Friend SSH/Proxy",
                "url": "https://chrome.google.com/webstore/detail/friend-ssh-proxy/jbahhdpabocfnddgnbhkldpacdlpgana"
            }
        ]
        
        for ext in extensions:
            try:
                print(f"🔗 Opening {ext['name']} extension page...")
                ext_page = await self.context.new_page()
                await ext_page.goto(ext['url'])
                await ext_page.wait_for_load_state('domcontentloaded')
                print(f"✅ {ext['name']} page loaded - Click 'Add to Chrome' to install")
                await asyncio.sleep(2)
            except Exception as e:
                print(f"❌ Could not open {ext['name']}: {e}")
                
    async def open_extensions_page(self):
        """Helper function to open Chrome extensions page in a new tab"""
        try:
            extensions_page = await self.context.new_page()
            await extensions_page.goto('chrome://extensions/')
            print("🧩 Extensions management page opened")
        except Exception as e:
            print(f"⚠️ Could not open extensions page: {e}")
            
    async def keep_alive(self):
        """Keep the browser alive until user closes it"""
        print("\n" + "="*60)
        print("🌐 REAL GOOGLE CHROME READY - EXTENSIONS FULLY SUPPORTED!")
        print("="*60)
        print("🧩 REQUIRED EXTENSIONS OPENED:")
        print("   • UrbanVPN - Click 'Add to Chrome' to install")
        print("   • Friend SSH/Proxy - Click 'Add to Chrome' to install")
        print("="*60)
        print("📋 TO INSTALL:")
        print("   1. Click 'Add to Chrome' on each extension tab")
        print("   2. Confirm installation when prompted")
        print("   3. Extensions will be ready immediately")
        print("="*60)
        print("🛑 Press Ctrl+C to close browser")
        print("="*60)
        
        # Keep the script running until interrupted
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """Clean up browser resources"""
        print("\n🧹 Cleaning up...")
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
                
            # Clean up lock files after closing browser
            self.cleanup_lock_files()
            
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
        print("✅ Browser closed successfully!")
        
    async def run(self):
        """Main execution"""
        try:
            # Initialize browser
            await self.initialize_browser()
            
            # Navigate to Facebook
            await self.navigate_to_facebook()
            
            # Open extensions page 
            await self.open_extensions_page()
            
            # Open required extensions for installation
            await self.install_required_extensions()
            
            # Keep browser alive
            await self.keep_alive()
            
        except KeyboardInterrupt:
            print("\n👋 Interrupted by user")
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await self.cleanup()

def main():
    """Entry point"""
    print("🧪 Manual Browser Testing Script")
    print("="*40)
    
    # Create browser instance
    browser = ManualBrowser()
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, browser.signal_handler)
    
    # Run the browser
    try:
        asyncio.run(browser.run())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)

if __name__ == "__main__":
    main() 