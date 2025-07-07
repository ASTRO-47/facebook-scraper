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
        
        # Check for security checkpoint/CAPTCHA
        security_check = await self.check_for_security_checkpoint()
        if security_check:
            return False
        
        return (user_icon is not None or home_icon is not None) and (login_form is None and login_button is None)
        
    async def check_for_security_checkpoint(self) -> bool:
        """Check if Facebook is showing a security checkpoint or CAPTCHA"""
        # Common security checkpoint indicators
        security_indicators = [
            'captcha', 
            'security check', 
            'confirm your identity',
            'prove you\'re not a robot',
            'checkpoint',
            'verification',
            'something went wrong',
            'we need to confirm it\'s you',
            'confirm it\'s you'
        ]
        
        # Check page title
        title = await self.page.title()
        if any(indicator.lower() in title.lower() for indicator in security_indicators):
            logger.info("Security checkpoint detected in page title")
            return True
            
        # Check for common security checkpoint elements
        security_elements = []
        for indicator in security_indicators:
            elements = await self.page.query_selector_all(f'text="{indicator}"i')
            security_elements.extend(elements)
            
        # Check for captcha iframe or image
        captcha_elements = await self.page.query_selector_all('iframe[src*="captcha"], img[src*="captcha"]')
        security_elements.extend(captcha_elements)
        
        if security_elements:
            logger.info("Security checkpoint detected on page")
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
    
    async def handle_security_checkpoint(self, timeout: int = 300000):
        """Pause for manual intervention if a security checkpoint is detected
        
        Args:
            timeout: Maximum time to wait for manual intervention in milliseconds (default: 5 minutes)
        """
        security_detected = await self.check_for_security_checkpoint()
        
        if security_detected:
            logger.warning("SECURITY CHECKPOINT DETECTED! Please solve the CAPTCHA or security challenge manually.")
            print("\n" + "*" * 80)
            print("* SECURITY CHECKPOINT DETECTED!")
            print("* Please solve the CAPTCHA or security verification in the browser window.")
            print("* The script will wait until you complete the verification.")
            print("* Press Enter in the terminal after completing the verification to continue.")
            print("*" * 80 + "\n")
            
            # Take a screenshot to help with debugging
            await self.take_screenshot("security_checkpoint")
            
            # Wait for user input to continue
            input_future = asyncio.Future()
            
            def on_input():
                if not input_future.done():
                    input_future.set_result(None)
            
            # Schedule getting input in a separate thread
            asyncio.get_event_loop().run_in_executor(
                None, lambda: [input("Press Enter after solving the verification..."), on_input()]
            )
            
            # Wait for either user input or timeout
            try:
                await asyncio.wait_for(input_future, timeout=timeout/1000)  # Convert to seconds
                logger.info("User confirmed security checkpoint has been resolved")
                return True
            except asyncio.TimeoutError:
                logger.warning(f"Security checkpoint wait timed out after {timeout/1000} seconds")
                return False
        
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