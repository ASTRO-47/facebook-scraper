"""
Facebook session management using Playwright
"""
import os
import json
import asyncio
from typing import Dict, Any, Optional, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

class FacebookSession:
    def __init__(self, headless=True, user_data_dir="./user_data", proxy=None):
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.proxy = proxy  # Add proxy support
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        
        # Create user data directory
        os.makedirs(user_data_dir, exist_ok=True)
    
    async def initialize(self):
        """Initialize browser with enhanced stealth and international account support"""
        self.playwright = await async_playwright().start()
        
        # Enhanced browser args for stealth and international accounts
        browser_args = [
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-field-trial-config',
            '--disable-back-forward-cache',
            '--disable-background-networking',
            '--enable-features=NetworkService,NetworkServiceLogging',
            '--disable-background-media-suspend',
            '--disable-back-forward-cache',
            '--disable-backgrounding-occluded-windows',
            '--disable-background-timer-throttling',
            '--disable-breakpad',
            '--disable-client-side-phishing-detection',
            '--disable-component-extensions-with-background-pages',
            '--disable-default-apps',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--disable-features=TranslateUI',
            '--disable-hang-monitor',
            '--disable-ipc-flooding-protection',
            '--disable-popup-blocking',
            '--disable-prompt-on-repost',
            '--disable-renderer-backgrounding',
            '--disable-sync',
            '--force-color-profile=srgb',
            '--metrics-recording-only',
            '--no-crash-upload',
            '--no-first-run',
            '--no-default-browser-check',
            '--safebrowsing-disable-auto-update',
            '--enable-automation',
            '--password-store=basic',
            '--use-mock-keychain',
            '--hide-scrollbars',
            '--mute-audio',
            '--no-sandbox',
            '--disable-setuid-sandbox',
        ]
        
        # Add proxy args if proxy is provided
        if self.proxy:
            browser_args.extend([
                f'--proxy-server={self.proxy}',
                '--proxy-bypass-list=<-loopback>'
            ])
        
        if not self.headless:
            # For SSH X11 forwarding, we need to ensure proper display
            display = os.environ.get('DISPLAY', ':0')
            os.environ['DISPLAY'] = display
            print(f"Using X11 display: {display}")
        
        # Prepare context options
        context_options = {
            'user_data_dir': self.user_data_dir,
            'headless': self.headless,
            'args': browser_args,
            'viewport': {'width': 1366, 'height': 768},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'ignore_default_args': ['--enable-automation'],
            'ignore_https_errors': True,
            'accept_downloads': True,
            'has_touch': False,
            'is_mobile': False,
            'java_script_enabled': True,
            'permissions': ['geolocation', 'notifications']
        }
        
        # Add proxy to context if provided
        if self.proxy:
            context_options['proxy'] = {'server': self.proxy}
        
        # Launch browser with persistent context for session saving
        self.context = await self.playwright.chromium.launch_persistent_context(**context_options)
        
        # Create new page
        self.page = await self.context.new_page()
        
        # Enhanced stealth measures for international accounts
        await self.page.evaluate("""
            // Hide webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Mock languages for Morocco (Arabic, French, English)
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ar-MA', 'fr-FR', 'ar', 'fr', 'en-US', 'en'],
            });
            
            // Override geolocation to Morocco
            Object.defineProperty(navigator, 'geolocation', {
                get: () => ({
                    getCurrentPosition: (success, error) => {
                        success({
                            coords: {
                                latitude: 33.9716,  // Rabat, Morocco
                                longitude: -6.8498,
                                accuracy: 20
                            }
                        });
                    }
                })
            });
            
            // Override permissions - handle null/undefined permissions
            if (window.navigator.permissions) {
            const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => {
                    if (!parameters || typeof parameters !== 'object') {
                        return Promise.resolve({ state: 'granted' });
                    }
                    return parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters);
                };
            } else {
                // Create permissions object if it doesn't exist
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: (parameters) => {
                            if (!parameters || typeof parameters !== 'object') {
                                return Promise.resolve({ state: 'granted' });
                            }
                            if (parameters.name === 'notifications') {
                                return Promise.resolve({ state: 'granted' });
                            }
                            return Promise.resolve({ state: 'granted' });
                        }
                    })
                });
            }
        """)
        
        # Set extra headers for Morocco
        await self.page.set_extra_http_headers({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ar-MA,ar;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Upgrade-Insecure-Requests': '1'
        })
        
        print("Browser initialized successfully for SSH X11 forwarding with Morocco settings")
        return self.page
    
    async def prefill_login(self, email="boy240930@gmail.com"):
        """Navigate to Facebook and prefill login email for manual completion"""
        print("🔍 Navigating to Facebook login...")
        
        # Try multiple Facebook domains for international accounts
        facebook_domains = [
            "https://m.facebook.com",  # Mobile version often less restricted
            "https://www.facebook.com",
            "https://ar-ar.facebook.com",  # Arabic version for Moroccan users
            "https://fr-fr.facebook.com"   # French version common in Morocco
        ]
        
        for domain in facebook_domains:
            try:
                print(f"🌐 Trying domain: {domain}")
                await self.page.goto(domain, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)
                
                # Check if we successfully loaded Facebook
                if "facebook" in self.page.url.lower():
                    print(f"✅ Successfully loaded: {domain}")
                    break
                    
            except Exception as e:
                print(f"⚠️ Failed to load {domain}: {e}")
                continue
        
        # Prefill email if on login page
        try:
            email_input = await self.page.query_selector('input[name="email"]')
            if email_input:
                await email_input.fill(email)
                print(f"📧 Pre-filled email: {email}")
                print("👤 Please complete the login manually...")
            else:
                print("👤 Please log in manually...")
        except Exception as e:
            print(f"Could not prefill email: {e}")
            print("👤 Please log in manually...")

    async def login_check(self):
        """Check if user is logged in and handle login process"""
        print("🔍 Checking login status...")
        
        # First check if we're already on Facebook and logged in (e.g., after loading cookies)
        current_url = self.page.url
        if "facebook.com" in current_url:
            print("🌐 Already on Facebook, checking login status...")
            
            # Check for multiple login indicators
            login_indicators = [
                'div[role="navigation"]',  # Main navigation
                'div[role="main"]',        # Main content area
                'a[href*="/logout"]',      # Logout link
                'div[data-pagelet="LeftRail"]',  # Left sidebar
                'div[aria-label*="Facebook"]'    # Facebook branding
            ]
            
            # Check if already logged in
            for indicator in login_indicators:
                try:
                    element = await self.page.query_selector(indicator)
                    if element:
                        # Additional check - make sure we're not on login page
                        login_form = await self.page.query_selector('form[data-testid="royal_login_form"]')
                        if not login_form:
                            print("✅ Already logged in with loaded cookies!")
                            return True
                except Exception:
                    continue
        
        # If not logged in or not on Facebook, navigate to Facebook with international account support
        print("🔑 Not logged in, navigating to Facebook...")
        await self.prefill_login()
        
        # Wait for page to stabilize
        await asyncio.sleep(5)
        
        # Check for multiple login indicators
        login_indicators = [
            'div[role="navigation"]',  # Main navigation
            'div[role="main"]',        # Main content area
            'a[href*="/logout"]',      # Logout link
            'div[data-pagelet="LeftRail"]',  # Left sidebar
            'div[aria-label*="Facebook"]'    # Facebook branding
        ]
        
        # Check if already logged in after navigation
        for indicator in login_indicators:
            try:
                element = await self.page.query_selector(indicator)
                if element and "facebook.com" in self.page.url:
                    # Additional check - make sure we're not on login page
                    login_form = await self.page.query_selector('form[data-testid="royal_login_form"]')
                    if not login_form:
                        print("✅ Already logged in!")
                        return True
            except Exception:
                continue
        
        print("🔑 Login required - please complete login manually...")
        print("🌍 This may take longer for international accounts due to security checks")
        print("💡 Tips for Moroccan accounts:")
        print("   - Choose 'This Was Me' for location verification")
        print("   - Complete phone/email verification if requested")
        print("   - Use your real information for verification")
        
        # Wait for login completion with extended timeout for international accounts
        max_wait_time = 600  # 10 minutes for international account verification
        check_interval = 10   # Check every 10 seconds
        
        for attempt in range(max_wait_time // check_interval):
            await asyncio.sleep(check_interval)
            
            # Check login status
            current_url = self.page.url
            print(f"⏳ Checking login progress... ({attempt * check_interval}s/{max_wait_time}s)")
            print(f"📍 Current URL: {current_url}")
            
            # Look for successful login indicators
            for indicator in login_indicators:
                try:
                    element = await self.page.query_selector(indicator)
                    if element and "facebook.com" in current_url:
                        # Double-check we're not on login page
                        login_form = await self.page.query_selector('form[data-testid="royal_login_form"]')
                        if not login_form:
                            print("✅ Login successful!")
                            # Save session after successful login
                            await self.save_session_cookies()
                            return True
                except Exception:
                    continue
                    
            # Check for common error pages
            if "checkpoint" in current_url or "security" in current_url:
                print("🔒 Security checkpoint detected - this is normal for international accounts")
                print("⏳ Continue solving the security challenge...")
            elif "help" in current_url or "disabled" in current_url:
                print("❌ Account may be disabled or restricted")
                break
                
        print("⏰ Login timeout reached - please ensure you completed the login process")
        return False

    async def close(self):
        """Close the browser session"""
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        print("🔒 Browser session closed")

    async def save_session_cookies(self):
        """Save session cookies to file"""
        try:
            if self.context:
                cookies = await self.context.cookies()
                session_file = os.path.join(self.user_data_dir, "session_cookies.json")
                with open(session_file, 'w') as f:
                    json.dump(cookies, f)
                print("💾 Session cookies saved")
        except Exception as e:
            print(f"⚠️ Could not save session cookies: {e}")

    async def load_session_cookies(self):
        """Load session cookies from file"""
        try:
            session_file = os.path.join(self.user_data_dir, "session_cookies.json")
            if os.path.exists(session_file):
                with open(session_file, 'r') as f:
                    cookies = json.load(f)
                await self.context.add_cookies(cookies)
                print("📂 Session cookies loaded")
                return True
        except Exception as e:
            print(f"⚠️ Could not load session cookies: {e}")
        return False