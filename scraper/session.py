"""
Session management module for Facebook scraper
Handles browser initialization and session persistence
"""
import os
import json
import asyncio
from playwright.async_api import async_playwright, Page, BrowserContext
import logging
from .utils import ScraperUtils  # Add this import
import json  # Import json for cookie handling

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('facebook_scraper')

class FacebookSession:
    def __init__(self, headless=True, user_data_dir="./user_data"):
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.browser = None
        self.playwright = None
        self.page = None

    async def initialize(self):
        """Initialize Playwright browser with persistent context"""
        # Handle ProcessSingleton issues more gracefully
        singleton_lock = os.path.join(self.user_data_dir, "SingletonLock")
        singleton_cookie = os.path.join(self.user_data_dir, "SingletonCookie")
        
        # If lock files exist, wait a bit for any existing process to finish
        if os.path.exists(singleton_lock) or os.path.exists(singleton_cookie):
            print("Found existing browser session files, waiting for cleanup...")
            # Wait up to 10 seconds for existing process to close
            for i in range(10):
                await asyncio.sleep(1)
                if not os.path.exists(singleton_lock) and not os.path.exists(singleton_cookie):
                    break
            
            # If still exists after waiting, try to remove them
            if os.path.exists(singleton_lock) or os.path.exists(singleton_cookie):
                try:
                    if os.path.exists(singleton_lock):
                        os.remove(singleton_lock)
                        print(f"Removed existing singleton lock: {singleton_lock}")
                    if os.path.exists(singleton_cookie):
                        os.remove(singleton_cookie)
                        print(f"Removed existing singleton cookie: {singleton_cookie}")
                except Exception as e:
                    print(f"Warning: Could not remove singleton files: {e}")
        
        os.makedirs(self.user_data_dir, exist_ok=True)
        
        self.playwright = await async_playwright().start()
        
        # Launch browser with persistent context to maintain session data
        logger.info(f"Launching browser with persistent context at {self.user_data_dir}")
        
        try:
            # Use the default Chromium browser that comes with Playwright
            self.browser = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=self.headless,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
                ignore_https_errors=True,
                locale="en-US",
                accept_downloads=True,
                proxy=None,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-dev-shm-usage",
                    "--disable-web-security",
                    "--disable-extensions-except=",
                    "--disable-extensions",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-gpu-sandbox",
                    "--disable-software-rasterizer",
                    "--force-single-process"  # Force single process to avoid ProcessSingleton issues
                ]
            )
        except Exception as e:
            if "ProcessSingleton" in str(e):
                print("ProcessSingleton error detected. Trying alternative approach...")
                # If ProcessSingleton fails, try launching without persistent context first
                self.browser = await self.playwright.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-web-security",
                        "--force-single-process"
                    ]
                )
                # Then create a context with the user data dir
                self.browser = await self.browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    viewport={"width": 1366, "height": 768},
                    ignore_https_errors=True,
                    locale="en-US"
                )
            else:
                raise e
        
        # Configure request interception to avoid being detected as bot
        await self.browser.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            
            // Disable fingerprinting
            navigator.permissions.query = (query) => {
                return Promise.resolve({state: 'granted'});
            };
        """)
        
        # Use existing pages or create a new one
        if hasattr(self.browser, 'pages') and len(self.browser.pages) > 0:
            self.page = self.browser.pages[0]
        else:
            self.page = await self.browser.new_page()
            
        logger.info("Browser session initialized successfully")
        return self.page
    
    async def prefill_login(self, email="boy240930@gmail.com"):
        """Pre-fill the login form with the provided email"""
        try:
            # Navigate to login page if not already there
            current_url = self.page.url
            if "facebook.com" not in current_url:
                await self.page.goto("https://www.facebook.com", wait_until="networkidle")
            
            # Check if we're already on a login page
            email_field = await self.page.query_selector('input[name="email"]')
            if email_field:
                await self.page.fill('input[name="email"]', email)
                print(f"Pre-filled email: {email}")
            
        except Exception as e:
            print(f"Error pre-filling login: {e}")
    
    async def login_check(self):
        """Check if the user is logged in, and wait for manual login if needed"""
        try:
            print("Checking if logged in to Facebook...")
            # Use longer timeout and less strict wait condition
            await self.page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)  # Extra wait for dynamic content
            
            # Various login detection methods - remove timeout argument for compatibility
            try:
                is_logged_in = await self.page.is_visible("[data-testid='royal_name']") or \
                               await self.page.is_visible("[aria-label='Home']") or \
                               await self.page.is_visible("[data-testid='blue_bar']") or \
                               await self.page.is_visible("div[role='banner']")
            except Exception as e:
                print(f"Error checking login visibility: {e}")
                is_logged_in = False
            
            utils = ScraperUtils(self.page)
            
            if not is_logged_in:
                print("\n" + "="*80)
                print("NOT LOGGED IN - MANUAL ACTION REQUIRED")
                print("Please log in or create an account in the browser window.")
                print("The browser will remain open until you press Enter in this terminal.")
                print("Take your time to complete any security challenges or account creation.")
                print("="*80 + "\n")
                
                # Pre-fill the login form with email if available
                await self.prefill_login()
                
                # Wait indefinitely for user to press Enter
                input("Press Enter when you have finished logging in...")
                
                # After user presses Enter, verify login success
                await asyncio.sleep(2)  # Give a moment to ensure the page updates
                
                # Check login status again - remove timeout argument for compatibility
                try:
                    is_logged_in = await self.page.is_visible("[data-testid='royal_name']") or \
                                   await self.page.is_visible("[aria-label='Home']") or \
                                   await self.page.is_visible("[data-testid='blue_bar']")
                except Exception as e:
                    print(f"Error checking login after user input: {e}")
                    is_logged_in = False
                
                if is_logged_in:
                    print("Login successful! Session will be saved for future use.")
                    # Save cookies for session persistence
                    await self.save_session_cookies()
                    return True
                else:
                    print("Still not logged in. Please try again.")
                    return False
            else:
                print("Already logged in!")
                # Try to load any saved cookies to maintain session
                await self.load_session_cookies()
                return True
                
        except Exception as e:
            print(f"Error checking login: {e}")
            return False
    
    async def close(self):
        """Close browser and session"""
        try:
            if self.browser:
                logger.info("Closing browser session")
                await self.browser.close()
            
            if self.playwright:
                await self.playwright.stop()
                
        except Exception as e:
            logger.error(f"Error closing session: {str(e)}")
    
    async def save_session_cookies(self):
        """Save cookies to a file for manual session persistence"""
        try:
            cookies_file = os.path.join(self.user_data_dir, "session_cookies.json")
            if self.page:
                cookies = await self.page.context.cookies()
                with open(cookies_file, 'w') as f:
                    json.dump(cookies, f, indent=2)
                print(f"Session cookies saved to: {cookies_file}")
                return True
        except Exception as e:
            print(f"Error saving session cookies: {e}")
            return False
    
    async def load_session_cookies(self):
        """Load cookies from file for manual session persistence"""
        try:
            cookies_file = os.path.join(self.user_data_dir, "session_cookies.json")
            if os.path.exists(cookies_file) and self.page:
                with open(cookies_file, 'r') as f:
                    cookies = json.load(f)
                await self.page.context.add_cookies(cookies)
                print(f"Session cookies loaded from: {cookies_file}")
                return True
        except Exception as e:
            print(f"Error loading session cookies: {e}")
            return False