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
        
        print(f"📺 Using display: {os.environ.get('DISPLAY')}")
        
        # Test if display is working
        try:
            result = subprocess.run(['xset', 'q'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("✅ Display is working properly")
            else:
                print("⚠️ Display might have issues")
        except Exception as e:
            print(f"⚠️ Could not test display: {e}")
        
        # Prepare user data directory
        self.prepare_user_data_dir()
        
        # Start Playwright
        self.playwright = await async_playwright().start()
        
        # Use REAL Google Chrome for extensions (NOT Playwright's Chromium)
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=False,
            executable_path='/usr/bin/google-chrome-stable',  # Use system Chrome
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--no-first-run',
                '--disable-default-browser-check',
                '--start-maximized',
                '--window-size=1920,1080',
                '--window-position=0,0',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-background-mode',
                '--disable-background-networking',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                '--disable-popup-blocking',
                '--disable-prompt-on-repost',
                '--disable-sync',
                '--force-color-profile=srgb',
                '--metrics-recording-only',
                '--no-crash-upload',
                '--safebrowsing-disable-auto-update',
                '--enable-automation',
                '--password-store=basic',
                '--use-mock-keychain',
                '--hide-scrollbars',
                '--mute-audio',
                '--disable-setuid-sandbox'
            ],
            viewport=None  # Remove viewport to allow full screen
        )
        
        self.page = await self.context.new_page()
        
        # Wait a moment for browser to stabilize
        await asyncio.sleep(2)
        
        # Force full screen using JavaScript
        if self.page:
            try:
                await self.page.evaluate("""
                    // Request full screen
                    if (document.documentElement.requestFullscreen) {
                        document.documentElement.requestFullscreen();
                    } else if (document.documentElement.webkitRequestFullscreen) {
                        document.documentElement.webkitRequestFullscreen();
                    } else if (document.documentElement.msRequestFullscreen) {
                        document.documentElement.msRequestFullscreen();
                    }
                    
                    // Also ensure window is maximized
                    window.focus();
                    window.moveTo(0, 0);
                    window.resizeTo(screen.width, screen.height);
                """)
            except Exception as e:
                print(f"⚠️ Full screen request failed: {e}")
        
        print("✅ Browser initialized with REAL Google Chrome - FULL SCREEN MODE!")
        return self.page
        
    async def navigate_to_facebook(self):
        """Navigate to Facebook"""
        print("🔗 Navigating to Facebook...")
        try:
            await self.page.goto('https://www.facebook.com', wait_until='domcontentloaded', timeout=30000)
            print("✅ Successfully navigated to Facebook in KIOSK FULL SCREEN MODE!")
        except Exception as e:
            print(f"⚠️ Navigation failed: {e}")
            print("🔄 You can manually navigate to any site in the browser")
      

            
    async def keep_alive(self):
        """Keep the browser alive until user closes it"""
        print("\n" + "="*60)
        print("🌐 BROWSER READY!")
        print("="*60)
        print("📋 WHAT YOU CAN DO:")
        print("   • Navigate to any website")
        print("   • Login to Facebook manually")
        print("   • Test the browser functionality")
        print("="*60)
        print("🛑 Press Ctrl+C to close browser")
        print("="*60)
        
        # Keep the script running until interrupted
        try:
            while self.running:
                # Periodically ensure window stays focused and maximized
                try:
                    await self.page.evaluate("""
                        // Keep window focused and maximized
                        window.focus();
                        if (window.screen && window.screen.width) {
                            window.moveTo(0, 0);
                            window.resizeTo(screen.width, screen.height);
                        }
                    """)
                except Exception:
                    pass  # Ignore errors if page is closed
                
                await asyncio.sleep(5)  # Check every 5 seconds
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
