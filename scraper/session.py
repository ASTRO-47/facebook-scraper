"""
Session management module for Facebook scraper
Handles browser initialization and session persistence
"""
import os
import asyncio
from playwright.async_api import async_playwright, Page, BrowserContext
import logging
from .utils import ScraperUtils  # Add this import

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
        os.makedirs(self.user_data_dir, exist_ok=True)
        
        self.playwright = await async_playwright().start()
        
        # Launch browser with persistent context to maintain session data
        logger.info(f"Launching browser with persistent context at {self.user_data_dir}")
        
        # Use the default Chromium browser that comes with Playwright
        self.browser = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=True,
            locale="en-US",
            accept_downloads=True,
            proxy=None,
            # Remove the channel parameter completely
        )
        
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
        if len(self.browser.pages) > 0:
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
            await self.page.goto("https://www.facebook.com", wait_until="networkidle")
            
            # Various login detection methods
            is_logged_in = await self.page.is_visible("[data-testid='royal_name']", timeout=3000) or \
                           await self.page.is_visible("[aria-label='Home']", timeout=1000) or \
                           await self.page.is_visible("[data-testid='blue_bar']", timeout=1000)
            
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
                
                # Check login status again
                is_logged_in = await self.page.is_visible("[data-testid='royal_name']", timeout=3000) or \
                               await self.page.is_visible("[aria-label='Home']", timeout=1000) or \
                               await self.page.is_visible("[data-testid='blue_bar']", timeout=1000)
                
                if is_logged_in:
                    print("Login successful! Session will be saved for future use.")
                    return True
                else:
                    print("Still not logged in. Please try again.")
                    return False
            else:
                print("Already logged in!")
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