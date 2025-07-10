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
    def __init__(self, headless=False, user_data_dir="./user_data"):
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
            # Random realistic user agents for better stealth
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            ]
            
            import random
            selected_user_agent = random.choice(user_agents)
            print(f"Using user agent: {selected_user_agent}")
            
            # Randomize viewport to look more human
            viewports = [
                {"width": 1366, "height": 768},
                {"width": 1920, "height": 1080},
                {"width": 1440, "height": 900},
                {"width": 1536, "height": 864}
            ]
            selected_viewport = random.choice(viewports)
            
            self.browser = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=self.headless,
                user_agent=selected_user_agent,
                viewport=selected_viewport,
                ignore_https_errors=True,
                locale="en-US",
                timezone_id="America/New_York",  # Use US timezone since you're in US
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
                    "--force-single-process",  # Force single process to avoid ProcessSingleton issues
                    # Enhanced stealth arguments
                    "--disable-blink-features=AutomationControlled",
                    "--exclude-switches=enable-automation", 
                    "--use-fake-ui-for-media-stream",
                    "--disable-default-apps",
                    "--disable-component-extensions-with-background-pages",
                    "--disable-ipc-flooding-protection",
                    "--enable-features=NetworkService,NetworkServiceLogging",
                    "--force-webrtc-ip-handling-policy=default_public_interface_only",
                    "--disable-features=TranslateUI",
                    "--disable-background-networking",
                    "--disable-sync",
                    "--metrics-recording-only",
                    "--disable-default-apps",
                    "--mute-audio",
                    "--no-reporting",
                    "--no-crash-upload"
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
            // Advanced stealth - Remove all automation indicators
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            
            // Hide automation-specific properties
            delete navigator.__proto__.webdriver;
            
            // Fake realistic navigator properties
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'ar', 'fr'],
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                    {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                    {name: 'Native Client', filename: 'internal-nacl-plugin'}
                ],
            });
            
            // Realistic screen properties
            Object.defineProperty(screen, 'colorDepth', {
                get: () => 24,
            });
            
            Object.defineProperty(screen, 'pixelDepth', {
                get: () => 24,
            });
            
            // Hide automation-specific console messages
            const originalLog = console.log;
            console.log = (...args) => {
                if (!args.join(' ').includes('automation')) {
                    originalLog.apply(console, args);
                }
            };
            
            // Realistic permissions
            navigator.permissions.query = (query) => {
                return Promise.resolve({state: 'granted'});
            };
            
            // Fake canvas fingerprint to avoid detection
            const getImageData = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(a) {
                if (a === 'image/webp') {
                    // Return randomized but consistent fake data
                    const fakeData = 'UklGRiIAAABXRUJQVlA4IBYAAAAwAQCdASoBAAEADsD+JaQAA3AAAAAA';
                    return 'data:image/webp;base64,' + fakeData + Math.random().toString(36).substr(2, 5);
                }
                return getImageData.apply(this, arguments);
            };
            
            // Override WebGL fingerprinting
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.'; // Fake but common GPU vendor
                }
                if (parameter === 37446) {
                    return 'Intel(R) HD Graphics'; // Fake but common GPU
                }
                return getParameter.call(this, parameter);
            };
            
            // Hide Playwright-specific properties
            delete window.playwright;
            delete window.__playwright;
            delete window._$playwright;
            
            // Randomize timezone (but keep consistent for session)
            const originalTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
            
            // Add realistic mouse and touch events
            window.addEventListener('load', () => {
                // Simulate some mouse movement after page load
                setTimeout(() => {
                    const event = new MouseEvent('mousemove', {
                        clientX: Math.random() * window.innerWidth,
                        clientY: Math.random() * window.innerHeight
                    });
                    document.dispatchEvent(event);
                }, Math.random() * 3000 + 1000);
            });
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
            
            # For international accounts, try different Facebook domains first
            print("Attempting international login flow...")
            
            # Try Morocco-specific Facebook domain first, then international
            facebook_urls = [
                "https://m.facebook.com",  # Mobile version is less restricted
                "https://www.facebook.com", 
                "https://ar-ar.facebook.com",  # Arabic version
                "https://fr-fr.facebook.com"   # French version (common in Morocco)
            ]
            
            login_successful = False
            
            for url in facebook_urls:
                try:
                    print(f"Trying login via: {url}")
                    await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(5)  # Wait for page to load
                    
                    # Check if account is accessible on this domain
                    page_content = await self.page.content()
                    
                    # Look for account not found indicators
                    if any(phrase in page_content.lower() for phrase in [
                        "account disabled", "account not found", "user not found",
                        "this content isn't available", "page not found"
                    ]):
                        print(f"Account not accessible via {url}, trying next...")
                        continue
                    
                    # Check if already logged in
                    is_logged_in = await self.page.is_visible("[data-testid='royal_name']") or \
                                   await self.page.is_visible("[aria-label='Home']") or \
                                   await self.page.is_visible("[data-testid='blue_bar']") or \
                                   await self.page.is_visible("div[role='banner']")
                    
                    if is_logged_in:
                        print(f"Already logged in via {url}!")
                        return True
                    
                    # Check if login form is available
                    email_field = await self.page.query_selector('input[name="email"]')
                    if email_field:
                        print(f"Login form found on {url}")
                        login_successful = True
                        break
                        
                except Exception as e:
                    print(f"Error with {url}: {e}")
                    continue
            
            if not login_successful:
                print("Could not access login form on any Facebook domain")
                return False
            
            utils = ScraperUtils(self.page)
            
            print("\n" + "="*80)
            print("INTERNATIONAL ACCOUNT LOGIN - MANUAL ACTION REQUIRED")
            print("For Moroccan accounts logging in from US:")
            print("1. Facebook may ask for additional verification")
            print("2. You may need to verify your identity with ID or phone")
            print("3. Choose 'This was me' for location verification prompts")
            print("4. Complete any security challenges that appear")
            print("5. Consider logging in via mobile.facebook.com first")
            print("="*80 + "\n")
            
            # Pre-fill the login form with email if available
            await self.prefill_login()
            
            # Wait indefinitely for user to press Enter
            input("Press Enter when you have finished logging in and completed any security steps...")
            
            # After user presses Enter, verify login success
            await asyncio.sleep(3)  # Give a moment to ensure the page updates
            
            # Check login status again across all domains
            for url in facebook_urls:
                try:
                    await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(2)
                    
                    is_logged_in = await self.page.is_visible("[data-testid='royal_name']") or \
                                   await self.page.is_visible("[aria-label='Home']") or \
                                   await self.page.is_visible("[data-testid='blue_bar']")
                    
                    if is_logged_in:
                        print(f"Login successful via {url}! Session will be saved for future use.")
                        # Save cookies for session persistence
                        await self.save_session_cookies()
                        return True
                        
                except Exception as e:
                    continue
            
            print("Login verification failed. Please try again.")
            return False
            
        except Exception as e:
            print(f"Error during login check: {e}")
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