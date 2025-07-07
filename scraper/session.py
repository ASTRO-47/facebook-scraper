"""
Session management module for Facebook scraper
Handles browser initialization and session persistence
"""
import os
import asyncio
from playwright.async_api import async_playwright, Page, BrowserContext
import logging

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
        self.browser = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=True,
            locale="en-US",
            accept_downloads=True,
            proxy=None  # No proxy to avoid session issues
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
    
    async def login_check(self):
        """Check if user is logged in to Facebook with improved detection"""
        logger.info("Checking login status...")
        
        try:
            await self.page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_load_state("networkidle", timeout=20000)
            
            # Check for security checkpoint
            from .utils import ScraperUtils
            utils = ScraperUtils(self.page)
            
            # Check and handle security checkpoint (this pauses for 2 minutes if detected)
            checkpoint_detected = await utils.check_for_security_checkpoint()
            if checkpoint_detected:
                logger.warning("Security checkpoint detected during login! Please solve the puzzle manually.")
                # Wait for the user to solve the puzzle (2 minutes)
                await utils.handle_security_checkpoint(wait_time=120)
            
            # Check for login indicators
            # Method 1: Check for login form presence
            login_form = await self.page.query_selector('form[data-testid="royal_login_form"]')
            
            # Method 2: Check for login button presence
            login_button = await self.page.query_selector('button[name="login"]')
            
            # Method 3: Try to find user menu (indicates logged in)
            user_menu = await self.page.query_selector('[aria-label="Your profile"], [aria-label="Account"], [data-testid="user-icon"]')
            
            if (login_form or login_button) and not user_menu:
                logger.info("Not logged in. Please log in manually...")
                
                # Wait for login to complete
                await self.page.wait_for_selector(
                    'a[aria-label="Home"], a[href="https://www.facebook.com/?ref=logo"], [data-testid="user-icon"]', 
                    timeout=120000
                )
                
                logger.info("Login detected!")
                # Session is automatically persisted with the persistent browser context
                return False
            else:
                logger.info("Already logged in")
                return True
                
        except Exception as e:
            logger.error(f"Error during login check: {str(e)}")
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