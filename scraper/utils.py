"""
Utility functions for Facebook scraper
"""
import os
import time
import asyncio
import re
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from playwright.async_api import Page, BrowserContext

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('facebook_utils')

class ScraperUtils:
    def __init__(self, page: Page, screenshot_dir: str = "../static/screenshots"):
        self.page = page
        self.screenshot_dir = screenshot_dir
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
    async def take_screenshot(self, filename: str, element_selector: Optional[str] = None) -> str:
        """Take a screenshot of the page or a specific element"""
        filepath = os.path.join(self.screenshot_dir, f"{filename}.png")
        
        if element_selector:
            element = await self.page.query_selector(element_selector)
            if element:
                await element.screenshot(path=filepath)
            else:
                print(f"Element {element_selector} not found for screenshot")
                return ""
        else:
            await self.page.screenshot(path=filepath)
        
        return filepath

    async def scroll_to_bottom(self, max_scrolls: int = 5, scroll_delay: float = 1.5):
        """Scroll to the bottom of the page gradually"""
        prev_height = await self.page.evaluate('document.body.scrollHeight')
        
        for _ in range(max_scrolls):
            await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(scroll_delay)  # Wait for content to load
            
            # Check if we've reached the bottom
            new_height = await self.page.evaluate('document.body.scrollHeight')
            if new_height == prev_height:
                break
            prev_height = new_height

    async def click_see_more_buttons(self):
        """Click on 'See more' buttons to expand content"""
        see_more_buttons = await self.page.query_selector_all('div[role="button"]:text("See more")')
        
        # Click each button with error handling
        for button in see_more_buttons:
            try:
                await button.click()
                await asyncio.sleep(0.5)  # Give time for content to expand
            except Exception as e:
                logger.warning(f"Failed to click 'See more' button: {str(e)}")
                
    async def check_for_login_status(self) -> bool:
        """Check if the user is currently logged in to Facebook"""
        # Look for elements that indicate logged-in state
        user_icon = await self.page.query_selector('[aria-label="Your profile"]')
        home_icon = await self.page.query_selector('[aria-label="Home"]')
        
        # Look for elements that indicate logged-out state
        login_form = await self.page.query_selector('form[data-testid="royal_login_form"]')
        login_button = await self.page.query_selector('button[name="login"]')
        
        return (user_icon is not None or home_icon is not None) and (login_form is None and login_button is None)
        
    async def check_for_security_checkpoint(self) -> bool:
        """
        Detect if Facebook is showing a security checkpoint or CAPTCHA
        Returns True if security checkpoint detected, False otherwise
        """
        # Look for common security checkpoint indicators
        checkpoint_indicators = [
            'a text containing "Confirm it\'s you"',
            'a text containing "Security check"', 
            'a text containing "prove you\'re a person"',
            'a text containing "confirm your identity"',
            'a text containing "verify your account"',
            'a text containing "challenge"',
            'a text containing "puzzle"',
            'div[aria-label="Checkpoint"]',
            'form[action*="checkpoint"]',
            'img[alt*="captcha"]',
            'img[src*="captcha"]',
            'input[name="captcha_response"]',
            'a[href*="checkpoint"]'
        ]
        
        for indicator in checkpoint_indicators:
            try:
                element = None
                if indicator.startswith('a text'):
                    # Extract the text to search for
                    text_to_find = indicator.split('"')[1]
                    # Use evaluate to find text on the page
                    has_text = await self.page.evaluate(f'''
                        () => {{
                            return document.body.innerText.includes("{text_to_find}")
                        }}
                    ''')
                    if has_text:
                        logger.info(f"Security checkpoint detected: Page contains text '{text_to_find}'")
                        return True
                else:
                    # Use regular selector
                    element = await self.page.query_selector(indicator)
                    if element:
                        logger.info(f"Security checkpoint detected: Found element matching {indicator}")
                        return True
            except Exception as e:
                logger.debug(f"Error checking for security indicator {indicator}: {str(e)}")
                
        # Check for generic indicators like unusual activity messages
        page_text = await self.page.evaluate('() => document.body.innerText')
        security_phrases = [
            "unusual activity", "security check", "captcha", "robot", 
            "human", "verify", "puzzle", "checkpoint"
        ]
        
        for phrase in security_phrases:
            if phrase.lower() in page_text.lower():
                logger.info(f"Security checkpoint detected: Page contains phrase '{phrase}'")
                return True
                
        return False
    
    async def handle_dialogs(self):
        """Set up handlers for unexpected dialogs"""
        # Handle dialog automatically
        self.page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
    
    async def wait_for_navigation_to_complete(self, timeout: int = 30000):
        """Wait for page navigation to complete with multiple indicators"""
        try:
            # Wait for network to be mostly idle
            await self.page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception as e:
            logger.warning(f"Network idle wait timed out: {str(e)}")
            
        try:
            # Alternative: wait for DOM content to be loaded
            await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
    
    async def save_cookies_to_file(self, filepath: str = "cookies.json"):
        """Save current cookies to a file"""
        try:
            cookies = await self.page.context.cookies()
            with open(filepath, 'w') as f:
                json.dump(cookies, f, indent=2)
            logger.info(f"Cookies saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save cookies: {str(e)}")
            return False
            
    async def load_cookies_from_file(self, filepath: str = "cookies.json"):
        """Load cookies from a file"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    cookies = json.load(f)
                await self.page.context.add_cookies(cookies)
                logger.info(f"Cookies loaded from {filepath}")
                return True
            else:
                logger.warning(f"Cookies file {filepath} not found")
                return False
        except Exception as e:
            logger.error(f"Failed to load cookies: {str(e)}")
            return False

    async def expand_comments(self, max_expansion: int = 3):
        """Expand comments on posts"""
        for _ in range(max_expansion):
            # Click "View more comments" buttons
            more_comments_buttons = await self.page.query_selector_all('div[role="button"]:text-matches("View (more |\\d+ more |)comments")')
            
            if not more_comments_buttons:
                break
                
            for button in more_comments_buttons:
                try:
                    await button.click()
                    await asyncio.sleep(1)
                except:
                    pass
                    
            # Click "Reply" buttons to expand nested comments
            reply_buttons = await self.page.query_selector_all('div[role="button"]:text("Reply")')
            for button in reply_buttons:
                try:
                    await button.click()
                    await asyncio.sleep(0.5)
                except:
                    pass

    def clean_text(self, text: str) -> str:
        """Clean up text content"""
        if not text:
            return ""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove emojis (basic implementation)
        text = re.sub(r'[^\x00-\x7F]+', '', text)
        return text

    def generate_unique_filename(self, base: str, username: str) -> str:
        """Generate unique filename for screenshots and outputs"""
        timestamp = int(time.time())
        return f"{username}_{base}_{timestamp}"

    async def human_like_delay(self, min_seconds=2, max_seconds=8):
        """Add realistic human-like delays between actions"""
        import random
        delay = random.uniform(min_seconds, max_seconds)
        print(f"⏳ Human-like delay: {delay:.1f} seconds")
        await asyncio.sleep(delay)
    
    async def slow_type(self, selector, text, delay_range=(0.05, 0.3)):
        """Type text slowly like a human"""
        import random
        await self.page.click(selector)
        await asyncio.sleep(random.uniform(0.5, 1.5))  # Pause after clicking
        
        for char in text:
            await self.page.keyboard.type(char)
            await asyncio.sleep(random.uniform(delay_range[0], delay_range[1]))
    
    async def human_scroll(self, pixels=None, direction="down"):
        """Scroll like a human - randomly and in chunks"""
        import random
        
        if pixels is None:
            pixels = random.randint(200, 800)
        
        # Scroll in smaller chunks like humans do
        chunks = random.randint(3, 6)
        chunk_size = pixels // chunks
        
        for i in range(chunks):
            scroll_amount = chunk_size + random.randint(-50, 50)
            if direction == "down":
                await self.page.mouse.wheel(0, scroll_amount)
            else:
                await self.page.mouse.wheel(0, -scroll_amount)
            
            # Random pause between scroll chunks
            await asyncio.sleep(random.uniform(0.2, 0.8))
    
    async def random_mouse_movement(self):
        """Add random mouse movements to simulate human behavior"""
        import random
        
        # Get page dimensions
        viewport = self.page.viewport_size
        width = viewport['width']
        height = viewport['height']
        
        # Generate 2-4 random mouse movements
        movements = random.randint(2, 4)
        
        for _ in range(movements):
            x = random.randint(100, width - 100)
            y = random.randint(100, height - 100)
            
            # Move mouse with some randomness in the path
            await self.page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.5))
    
    async def safe_click(self, selector, human_like=True):
        """Click with human-like behavior"""
        import random
        
        if human_like:
            # Random mouse movement before click
            await self.random_mouse_movement()
            await asyncio.sleep(random.uniform(0.3, 1.0))
        
        # Wait for element to be visible and clickable
        await self.page.wait_for_selector(selector, state="visible", timeout=10000)
        
        # Sometimes hover before clicking
        if random.choice([True, False]):
            await self.page.hover(selector)
            await asyncio.sleep(random.uniform(0.2, 0.7))
        
        await self.page.click(selector)
        
        if human_like:
            await self.human_like_delay(1, 3)
    
    async def facebook_security_check(self):
        """Enhanced security checkpoint detection for international accounts"""
        security_indicators = [
            # Standard checkpoints
            "security checkpoint", "verify your identity", "confirm your identity",
            "unusual activity", "suspicious activity", "verify it's you",
            
            # International login specific
            "login from a new location", "new device", "different country",
            "verify this login", "was this you", "approve this login",
            "location verification", "account security", "protect your account",
            
            # Arabic/French variations (for Moroccan accounts)
            "نقطة أمان", "تأكيد الهوية", "نشاط مشبوه",
            "point de sécurité", "vérifier votre identité", "activité suspecte"
        ]
        
        try:
            page_content = await self.page.content()
            page_text = page_content.lower()
            
            # Check for security checkpoint indicators
            for indicator in security_indicators:
                if indicator.lower() in page_text:
                    print(f"🔒 Security checkpoint detected: {indicator}")
                    return True
            
            # Check for specific security-related selectors
            security_selectors = [
                "[data-testid='security_checkpoint']",
                "[role='dialog'][aria-label*='Security']",
                "[role='dialog'][aria-label*='Verify']", 
                "form[action*='checkpoint']",
                "div[id*='checkpoint']",
                "button[value='Continue']",
                "button[value='This Was Me']"
            ]
            
            for selector in security_selectors:
                if await self.page.is_visible(selector):
                    print(f"🔒 Security checkpoint element found: {selector}")
                    return True
                    
            return False
            
        except Exception as e:
            print(f"Error checking for security checkpoint: {e}")
            return False
    
    async def handle_security_checkpoint(self, wait_time=300):
        """Enhanced security checkpoint handler for international accounts"""
        print("\n" + "="*60)
        print("🔒 SECURITY CHECKPOINT DETECTED")
        print("="*60)
        print("For international accounts (Moroccan account in US):")
        print("1. ✅ Click 'This Was Me' or 'Yes, Continue'")
        print("2. 📱 You may need to verify via SMS or email")
        print("3. 📋 Have your ID ready if asked for verification")
        print("4. 🌍 Confirm the login location is correct")
        print("5. ⚠️ DO NOT use VPN - use your real US location")
        print("6. 📝 Answer any security questions honestly")
        print("="*60)
        
        # Take screenshot for debugging
        checkpoint_screenshot = await self.take_screenshot("security_checkpoint_international")
        print(f"📸 Checkpoint screenshot saved: {checkpoint_screenshot}")
        
        print(f"⏳ Waiting {wait_time} seconds for manual resolution...")
        print("Press Ctrl+C to skip waiting if you've resolved it quickly")
        
        try:
            await asyncio.sleep(wait_time)
        except KeyboardInterrupt:
            print("\n⚡ Manual intervention detected, continuing...")
        
        # Verify checkpoint is resolved
        is_resolved = not await self.facebook_security_check()
        if is_resolved:
            print("✅ Security checkpoint appears to be resolved!")
        else:
            print("⚠️ Security checkpoint may still be active")
        
        return is_resolved