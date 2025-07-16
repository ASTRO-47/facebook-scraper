"""
Improved Facebook Profile Scraper
Modern, clean, and robust implementation with comprehensive error handling
"""
import asyncio
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
import logging

from .utils import ScraperUtils

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProfileScraper:
    """
    Improved Facebook Profile Scraper with robust error handling and modern design patterns
    """
    
    def __init__(self, page: Page, utils: ScraperUtils):
        """Initialize the ProfileScraper with page and utilities"""
        self.page = page
        self.utils = utils
        self.original_username = None
        self.profile_url = None
        self.profile_type = None
        self.profile_identifier = None
        
        # Configuration
        self.max_retries = 3
        self.default_timeout = 30000
        self.navigation_timeout = 60000
        
    def _clean_input(self, username: str) -> str:
        """Clean and normalize input username/URL"""
        if not username:
            raise ValueError("Username cannot be empty")
        
        return username.strip().rstrip('/').lstrip('@')
    
    def _detect_profile_type(self, username: str) -> Tuple[str, str]:
        """
        Detect if input is username or profile ID and return type and identifier
        
        Returns:
            Tuple[str, str]: (profile_type, profile_identifier)
        """
        username = self._clean_input(username)
        
        # Handle full Facebook URLs
        if "facebook.com" in username.lower():
            return self._extract_from_url(username)
        
        # Handle profile.php format without domain
        if "profile.php?id=" in username:
            match = re.search(r'profile\.php\?id=(\d+)', username)
            if match:
                profile_id = match.group(1)
                logger.info(f"Detected profile.php format: {profile_id}")
                return "id", profile_id
        
        # Handle numeric ID only
        if username.isdigit():
            self._validate_profile_id(username)
            logger.info(f"Detected numeric profile ID: {username}")
            return "id", username
        
        # Handle username format
        logger.info(f"Detected username format: {username}")
        return "username", username
    
    def _extract_from_url(self, url: str) -> Tuple[str, str]:
        """Extract profile information from Facebook URL"""
        if "profile.php?id=" in url:
            match = re.search(r'profile\.php\?id=(\d+)', url)
            if match:
                profile_id = match.group(1)
                logger.info(f"Extracted profile ID from URL: {profile_id}")
                return "id", profile_id
        else:
            # Extract username from URL
            try:
                parts = url.lower().split('facebook.com/')
                if len(parts) > 1:
                    username_part = parts[1].split('/')[0].split('?')[0].split('#')[0]
                    if username_part and not username_part.isdigit() and len(username_part) > 0:
                        logger.info(f"Extracted username from URL: {username_part}")
                        return "username", username_part
            except Exception as e:
                logger.warning(f"Error extracting username from URL: {e}")
        
        raise ValueError(f"Could not extract profile information from URL: {url}")
    
    def _validate_profile_id(self, profile_id: str) -> None:
        """Validate profile ID format"""
        if len(profile_id) < 5 or len(profile_id) > 20:
            logger.warning(f"Profile ID {profile_id} has unusual length ({len(profile_id)} digits)")
    
    def _construct_profile_url(self, username: str, section: str = "") -> str:
        """Construct the correct Facebook URL for both username and profile ID formats"""
        profile_type, profile_identifier = self._detect_profile_type(username)
        
        if profile_type == "id":
            base_url = f"https://www.facebook.com/profile.php?id={profile_identifier}"
            if section:
                return f"{base_url}&sk={section}"
            return base_url
        else:
            base_url = f"https://www.facebook.com/{profile_identifier}"
            if section:
                return f"{base_url}/{section}"
            return base_url
    
    async def navigate_to_profile(self, username: str) -> bool:
        """
        Navigate to a user's profile page with comprehensive error handling
        
        Args:
            username: Username or profile URL to navigate to
            
        Returns:
            bool: True if navigation successful, False otherwise
        """
        self.original_username = username
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Navigation attempt {attempt + 1}/{self.max_retries}")
                
                # Construct URL and get profile info
                profile_url = self._construct_profile_url(username)
                self.profile_url = profile_url
                self.profile_type, self.profile_identifier = self._detect_profile_type(username)
                
                logger.info(f"Navigating to: {profile_url}")
                
                # Handle retries with alternative approaches
                if attempt > 0:
                    await self._handle_retry_logic(attempt, username)
                    profile_url = self._get_alternative_url(attempt, username)
                
                # Navigate to profile
                await self.page.goto(profile_url, wait_until="domcontentloaded", timeout=self.navigation_timeout)
                logger.info("Page loaded successfully")
                
                # Wait for page to settle
                await self._wait_for_page_load()
                
                # Validate navigation success
                if await self._validate_navigation():
                    logger.info(f"Successfully navigated to profile: {self.profile_identifier}")
                    return True
                
                if attempt < self.max_retries - 1:
                    logger.warning(f"Navigation validation failed, retrying...")
                    continue
                else:
                    logger.error(f"Failed to navigate after {self.max_retries} attempts")
                    return False
                    
            except Exception as e:
                logger.error(f"Navigation error on attempt {attempt + 1}: {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(5)
                    continue
                else:
                    return False
        
        return False
    
    async def _handle_retry_logic(self, attempt: int, username: str) -> None:
        """Handle retry-specific logic"""
        logger.info(f"Retry attempt {attempt}: Clearing cookies to avoid redirect loops")
        await self.page.context.clear_cookies()
        await asyncio.sleep(10)
    
    def _get_alternative_url(self, attempt: int, username: str) -> str:
        """Get alternative URL formats for retries"""
        if self.profile_type == "id":
            if attempt == 1:
                url = f"https://m.facebook.com/profile.php?id={self.profile_identifier}"
                logger.info(f"Trying mobile URL: {url}")
                return url
            elif attempt == 2:
                url = f"https://www.facebook.com/people/{self.profile_identifier}"
                logger.info(f"Trying people URL: {url}")
                return url
        
        return self.profile_url
    
    async def _wait_for_page_load(self) -> None:
        """Wait for page content to load with multiple fallback selectors"""
        selectors_to_try = [
            "div[role='main']",
            "[data-pagelet='ProfileTilesFeed']",
            "[data-pagelet='ProfileTimeline']",
            "div[data-pagelet='ProfileActions']",
            "h1"
        ]
        
        content_loaded = False
        for selector in selectors_to_try:
            try:
                await self.page.wait_for_selector(selector, timeout=10000)
                logger.info(f"Content loaded using selector: {selector}")
                content_loaded = True
                break
            except PlaywrightTimeoutError:
                continue
        
        if not content_loaded:
            logger.warning("No expected selectors found, but continuing...")
        
        # Human-like page observation time
        await asyncio.sleep(12)
    
    async def _validate_navigation(self) -> bool:
        """Validate that navigation was successful"""
        current_url = self.page.url
        
        try:
            page_title = await self.page.title()
            logger.info(f"Current URL: {current_url}")
            logger.info(f"Page title: {page_title}")
        except Exception:
            logger.warning("Could not get page title")
        
        # Check for error redirects
        if "facebook.com" not in current_url or "error" in current_url.lower():
            logger.warning(f"Unexpected redirect to: {current_url}")
            return False
        
        # Check for profile-specific validation
        if not await self._validate_profile_page(current_url):
            return False
        
        # Check for security checkpoints
        if await self.utils.check_for_security_checkpoint():
            logger.warning("Security checkpoint detected")
            await self.utils.handle_security_checkpoint(wait_time=60)
            await asyncio.sleep(3)
        
        return True
    
    async def _validate_profile_page(self, current_url: str) -> bool:
        """Validate we're on the correct profile page"""
        # Check for redirect to home/feed
        if any(pattern in current_url.lower() for pattern in ['/home', '/feed', '/?sk=', 'facebook.com/?']):
            logger.error(f"Redirected to home/feed: {current_url}")
            return False
        
        # Validate profile-specific content
        if self.profile_type == "id":
            if f"id={self.profile_identifier}" not in current_url:
                logger.error(f"Profile ID mismatch: expected {self.profile_identifier}")
                return False
        else:
            if self.profile_identifier not in current_url and f"/{self.profile_identifier}" not in current_url:
                logger.error(f"Username mismatch: expected {self.profile_identifier}")
                return False
        
        return True
    
    async def get_basic_info(self) -> Dict[str, Any]:
        """
        Extract basic profile information with improved error handling
        
        Returns:
            Dict containing profile information
        """
        try:
            logger.info("Extracting basic profile information...")
            
            # Get profile name
            name = await self._extract_profile_name()
            logger.info(f"Profile name: {name}")
            
            # Get bio/description
            bio = await self._extract_profile_bio()
            logger.info(f"Profile bio: {bio[:50]}..." if bio else "No bio found")
            
            # Get About page information
            about_data = await self._extract_about_info()
            
            result = {
                "name": self.utils.clean_text(name),
                "bio": self.utils.clean_text(bio),
                "profile_picture": "",
                "work": about_data.get("work", []),
                "education": about_data.get("education", []),
                "current_city": about_data.get("current_city", ""),
                "hometown": about_data.get("hometown", ""),
                "email": about_data.get("email", ""),
                "phone": about_data.get("phone", ""),
                "birthday": about_data.get("birthday", ""),
            }
            
            logger.info(f"Basic info extracted: {len([v for v in result.values() if v])} fields found")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting basic info: {e}")
            return self._get_default_basic_info()
    
    def _get_default_basic_info(self) -> Dict[str, Any]:
        """Return default basic info structure"""
        return {
            "name": "Unknown",
            "bio": "",
            "profile_picture": "",
            "work": [],
            "education": [],
            "current_city": "",
            "hometown": "",
            "email": "",
            "phone": "",
            "birthday": "",
        }
    
    async def _extract_profile_name(self) -> str:
        """Extract profile name with multiple fallback selectors"""
        name_selectors = [
            'h1',
            'span[dir="auto"]',
            '[data-testid="profile-name"]',
            'div[role="main"] h1',
            'div[data-pagelet*="Profile"] h1',
        ]
        
        for selector in name_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                for element in elements:
                    text = await element.text_content()
                    if text and self._is_valid_name(text):
                        name = self._clean_name(text)
                        logger.info(f"Found name using selector: {selector}")
                        return name
            except Exception as e:
                logger.warning(f"Name selector {selector} failed: {e}")
                continue
        
        return "Unknown"
    
    def _is_valid_name(self, text: str) -> bool:
        """Validate if text looks like a name"""
        text = text.strip()
        
        # Skip obvious non-name content
        invalid_patterns = [
            "notification", "friend", "mutual", "•", "see all", "photos",
            "about", "more", "home", "settings", "search"
        ]
        
        if any(pattern in text.lower() for pattern in invalid_patterns):
            return False
        
        # Must be meaningful length
        if len(text) < 2 or text.isdigit():
            return False
        
        return True
    
    def _clean_name(self, name: str) -> str:
        """Clean and format name"""
        name = name.strip()
        
        # Extract just the name part (before parentheses if any)
        if '(' in name:
            name = name.split('(')[0].strip()
        
        return name
    
    async def _extract_profile_bio(self) -> str:
        """Extract profile bio/description"""
        bio_selectors = [
            '[data-testid="profile-bio"]',
            'div[data-pagelet*="Profile"] div[dir="auto"]',
            'div[role="main"] div[dir="auto"]',
        ]
        
        for selector in bio_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                for element in elements:
                    text = await element.text_content()
                    if text and self._is_valid_bio(text):
                        logger.info(f"Found bio using selector: {selector}")
                        return text.strip()
            except Exception as e:
                logger.warning(f"Bio selector {selector} failed: {e}")
                continue
        
        return ""
    
    def _is_valid_bio(self, text: str) -> bool:
        """Validate if text looks like a bio"""
        text = text.strip()
        
        # Skip friend counts, navigation, and other non-bio content
        invalid_patterns = [
            "friend", "mutual", "•", "notification", "see all", "photos",
            "about", "more", "home", "settings", "likes", "followers"
        ]
        
        if any(pattern in text.lower() for pattern in invalid_patterns):
            return False
        
        # Must be meaningful bio content
        return len(text) > 10 and not text.isdigit()
    
    async def _extract_about_info(self) -> Dict[str, Any]:
        """Extract detailed information from About page"""
        about_data = {}
        
        try:
            logger.info("Attempting to navigate to About page...")
            
            # Try to find and click About link
            if await self._navigate_to_about_page():
                about_data.update(await self._extract_work_education())
                about_data.update(await self._extract_places())
                about_data.update(await self._extract_contact_info())
                about_data.update(await self._extract_basic_details())
            else:
                logger.warning("Could not navigate to About page")
                
        except Exception as e:
            logger.error(f"Error extracting about info: {e}")
        
        return about_data
    
    async def _navigate_to_about_page(self) -> bool:
        """Navigate to the About page"""
        about_selectors = [
            'a[href*="/about"]',
            'nav a:text("About")',
            'div[role="tablist"] a:text("About")',
            '[data-testid*="about"]',
        ]
        
        for selector in about_selectors:
            try:
                about_link = await self.page.query_selector(selector)
                if about_link:
                    await about_link.click()
                    await asyncio.sleep(6)
                    await self.page.wait_for_load_state("domcontentloaded", timeout=self.default_timeout)
                    logger.info(f"Navigated to About using selector: {selector}")
                    return True
            except Exception as e:
                logger.warning(f"About selector {selector} failed: {e}")
                continue
        
        return False
    
    async def _extract_work_education(self) -> Dict[str, Any]:
        """Extract work and education information"""
        result = {"work": [], "education": []}
        
        try:
            await asyncio.sleep(2)
            
            # Work extraction
            work_selectors = [
                '[data-overviewsection="work"] div[role="button"]',
                '[aria-label*="Work"] div',
                'div:has-text("Works at") + div',
                'div:has-text("Worked at") + div'
            ]
            
            result["work"] = await self._extract_section_data(work_selectors, "work")
            result["education"] = await self._extract_section_data([
                '[data-overviewsection="education"] div[role="button"]',
                '[aria-label*="Education"] div',
                'div:has-text("Studies at") + div',
                'div:has-text("Studied at") + div'
            ], "education")
            
        except Exception as e:
            logger.error(f"Error extracting work/education: {e}")
        
        return result
    
    async def _extract_section_data(self, selectors: List[str], section_type: str) -> List[str]:
        """Extract data from a specific section"""
        data = []
        
        for selector in selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                for element in elements:
                    text = await element.text_content()
                    if text and self._is_valid_section_data(text, section_type):
                        clean_text = self.utils.clean_text(text)
                        if clean_text not in data:
                            data.append(clean_text)
            except Exception:
                continue
        
        return data
    
    def _is_valid_section_data(self, text: str, section_type: str) -> bool:
        """Validate section data"""
        text = text.strip().lower()
        
        # Skip notification patterns
        notification_patterns = [
            "accepted your friend request", "sent you a friend request",
            "tagged you in", "commented on your", "liked your", "shared your",
            "notification", "ago", "minutes ago", "hours ago", "days ago"
        ]
        
        if any(pattern in text for pattern in notification_patterns):
            return False
        
        # Skip common non-content text
        skip_patterns = [
            f"add a {section_type}", section_type, "overview",
            "see all", "more", "edit", "delete", "hide"
        ]
        
        if any(pattern in text for pattern in skip_patterns):
            return False
        
        return len(text) > 5 and not text.isdigit()
    
    async def _extract_places(self) -> Dict[str, Any]:
        """Extract location information"""
        result = {}
        
        try:
            location_selectors = [
                'div[data-overviewsection="places"]',
                'div:has-text("Places lived")',
                'div:has-text("Lives in")',
                'div:has-text("From")',
            ]
            
            for selector in location_selectors:
                try:
                    location_section = await self.page.query_selector(selector)
                    if location_section:
                        entries = await location_section.query_selector_all('div[role="button"], a[role="link"]')
                        for entry in entries:
                            text = await entry.text_content()
                            if text and len(text.strip()) > 3:
                                clean_location = self.utils.clean_text(text)
                                if "lives in" in clean_location.lower():
                                    result["current_city"] = clean_location.replace("Lives in", "").strip()
                                elif "from" in clean_location.lower():
                                    result["hometown"] = clean_location.replace("From", "").strip()
                        if result:
                            break
                except Exception as e:
                    logger.warning(f"Location selector {selector} failed: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting places: {e}")
        
        return result
    
    async def _extract_contact_info(self) -> Dict[str, Any]:
        """Extract contact information"""
        result = {}
        
        try:
            page_text = await self.page.evaluate('() => document.body.innerText')
            
            # Extract email
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_matches = re.findall(email_pattern, page_text)
            if email_matches:
                result["email"] = email_matches[0]
            
            # Extract phone
            phone_pattern = r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
            phone_matches = re.findall(phone_pattern, page_text)
            if phone_matches:
                result["phone"] = ''.join(phone_matches[0]) if isinstance(phone_matches[0], tuple) else phone_matches[0]
                
        except Exception as e:
            logger.error(f"Error extracting contact info: {e}")
        
        return result
    
    async def _extract_basic_details(self) -> Dict[str, Any]:
        """Extract basic details like birthday"""
        result = {}
        
        try:
            birthday_patterns = [
                'div:has-text("Birthday")',
                'div:has-text("Born")',
                '[data-testid*="birthday"]',
            ]
            
            for pattern in birthday_patterns:
                try:
                    elements = await self.page.query_selector_all(pattern)
                    for element in elements:
                        text = await element.text_content()
                        if text and ("Birthday" in text or "Born" in text):
                            birthday = text.replace("Birthday", "").replace("Born", "").strip()
                            if birthday:
                                result["birthday"] = self.utils.clean_text(birthday)
                                break
                except Exception:
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting basic details: {e}")
        
        return result

    # Additional methods for friends, groups, etc. will be added in the next part...

    async def get_friends_list(self, max_scrolls: int = 20) -> List[Dict[str, str]]:
        """Extract friends list with simplified approach"""
        try:
            logger.info("Extracting friends list...")
            
            # Navigate to friends page
            friends_url = self._construct_profile_url(self.original_username, "friends")
            await self.page.goto(friends_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)
            
            # Check for privacy restrictions
            page_content = await self.page.content()
            if "This content isn't available" in page_content or "Friends list is private" in page_content:
                logger.warning("Friends list is private or restricted")
                return []
            
            # Extract friends with efficient scrolling
            friends_list = []
            stable_rounds = 0
            
            for scroll in range(max_scrolls):
                # Extract current batch
                current_batch = await self._extract_current_friends_batch()
                
                # Add new friends
                new_count = 0
                for friend in current_batch:
                    if not any(f["name"] == friend["name"] for f in friends_list):
                        friends_list.append(friend)
                        new_count += 1
                
                logger.info(f"Scroll {scroll + 1}: Found {len(friends_list)} total (+{new_count} new)")
                
                # Check for stability - stop earlier if no new friends
                if new_count == 0:
                    stable_rounds += 1
                    if stable_rounds >= 2:  # Reduced from 3 to 2
                        logger.info("No new friends found for 2 rounds, stopping")
                        break
                else:
                    stable_rounds = 0
                
                # Stop if we've found a good amount of friends
                if len(friends_list) >= 500:  # Stop at 500 friends to prevent infinite scrolling
                    logger.info("Found 500+ friends, stopping to prevent timeout")
                    break
                
                # Scroll down with shorter delay
                await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(1.5)  # Reduced from 3 to 1.5 seconds
            
            logger.info(f"Extracted {len(friends_list)} friends total")
            return friends_list
            
        except Exception as e:
            logger.error(f"Error getting friends list: {e}")
            return []
    
    def _validate_page_availability(self) -> bool:
        """Check if page/browser is still available"""
        if not self.page or self.page.is_closed():
            logger.error("Page is closed, cannot continue")
            return False
        return True
    
    async def _navigate_with_retries(self, url: str, retries: int = 3) -> bool:
        """Navigate to URL with retries"""
        for attempt in range(retries):
            try:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=self.default_timeout)
                await asyncio.sleep(8)  # Human-like delay
                return True
            except Exception as e:
                logger.warning(f"Navigation attempt {attempt + 1} failed: {e}")
                if attempt == retries - 1:
                    return False
                await asyncio.sleep(10)
        return False
    
    async def _check_privacy_restrictions(self) -> bool:
        """Check for privacy restrictions on the page"""
        privacy_texts = [
            "This content isn't available",
            "Friends list is private",
            "No friends to show",
            "Only you can see",
            "Content not available"
        ]
        
        try:
            page_content = await self.page.content()
            return any(text in page_content for text in privacy_texts)
        except Exception:
            return False
    
    async def _extract_friends_with_scrolling(self, max_scrolls: int) -> List[Dict[str, str]]:
        """Extract friends with intelligent scrolling"""
        friends_list = []
        last_count = 0
        stable_rounds = 0
        max_stable_rounds = 5
        
        logger.info(f"Starting scrolling extraction (max {max_scrolls} scrolls)")
        
        for scroll_attempt in range(max_scrolls):
            # Extract current batch of friends
            current_batch = await self._extract_current_friends_batch()
            
            # Add new friends to list
            for friend in current_batch:
                if not any(f["name"] == friend["name"] for f in friends_list):
                    friends_list.append(friend)
            
            current_count = len(friends_list)
            new_friends = current_count - last_count
            logger.info(f"Scroll {scroll_attempt + 1}: Found {current_count} total (+{new_friends} new)")
            
            # Check for stability (no new friends found)
            if current_count == last_count:
                stable_rounds += 1
                if stable_rounds >= max_stable_rounds:
                    logger.info(f"No new friends found for {max_stable_rounds} rounds, stopping")
                    break
            else:
                stable_rounds = 0
            
            last_count = current_count
            
            # Perform human-like scrolling
            await self._perform_human_scrolling()
        
        return friends_list
    
    async def _extract_current_friends_batch(self) -> List[Dict[str, str]]:
        """Extract friends from current page state - simplified and robust"""
        current_batch = []
        
        try:
            # Simple approach - just get all Facebook profile links
            friend_elements = await self.page.query_selector_all('a[href*="facebook.com/"]')
            
            for element in friend_elements:
                try:
                    # Skip if element is None or not a proper element
                    if not element:
                        continue
                    
                    # Get href
                    href = await element.get_attribute('href')
                    if not href or not self._is_valid_friend_link(href):
                        continue
                    
                    # Get name - simplified approach
                    name = await element.text_content()
                    if not name:
                        continue
                    
                    name = name.strip()
                    if not self._is_valid_friend_name(name):
                        continue
                    
                    friend_data = {
                        "name": self.utils.clean_text(name),
                        "profile_url": href,
                        "bio": ""
                    }
                    
                    current_batch.append(friend_data)
                    
                except Exception:
                    # Skip problematic elements silently
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting friends batch: {e}")
        
        return current_batch
    
    def _is_valid_friend_link(self, href: str) -> bool:
        """Validate if link is a valid friend profile"""
        # Skip navigation links
        skip_patterns = [
            '/friends/', '/photos/', '/videos/', '/about/', '/posts/',
            '/likes/', '/groups/', '/events/', '/reviews/', '/places/',
            '?sk=', '?ref=', '/home/', '/feed/', '/search/', '/browse/',
            'mutual', 'message', '/settings/', '/notifications/',
            '/stories/', '/reels/', '/watch/', '/marketplace/',
            '/gaming/', '/pages/', '/ads/', '/help/'
        ]
        
        if any(pattern in href for pattern in skip_patterns):
            return False
        
        # Skip if it's the user's own profile
        if self.profile_identifier and (f"/{self.profile_identifier}" in href or href.endswith(self.profile_identifier)):
            return False
        
        return True
    
    async def _extract_friend_name(self, element) -> str:
        """Extract name from friend element (legacy method)"""
        # Try direct text content
        direct_text = await element.text_content()
        if direct_text and len(direct_text.strip()) > 1:
            return direct_text.strip()
        
        # Try child elements
        try:
            name_elements = await element.query_selector_all('span, div')
            for name_elem in name_elements:
                text = await name_elem.text_content()
                if text and len(text.strip()) > 1:
                    return text.strip()
        except Exception:
            pass
        
        return ""
    

    
    def _is_valid_friend_name(self, name: str) -> bool:
        """Validate if text is a valid friend name"""
        if not name or len(name) < 2:
            return False
        
        invalid_names = [
            "see all", "more", "photos", "videos", "about", "friends",
            "mutual", "message", "follow", "add friend", "home", "settings",
            "notifications", "stories", "reels", "watch", "marketplace",
            "gaming", "pages", "ads", "help", "search", "browse",
            "like", "comment", "share", "save", "edit", "delete",
            "report", "block", "unfriend", "unfollow", "hide",
            "ago", "min", "hour", "day", "week", "month", "year",
            "•", "·", "...", "view", "show", "hide", "close"
        ]
        
        if any(invalid in name.lower() for invalid in invalid_names):
            return False
        
        if name.isdigit():
            return False
        
        # Skip notification patterns
        notification_patterns = [
            "accepted your", "friend request", "notification",
            "tagged you", "commented on", "liked your", "shared your"
        ]
        
        if any(pattern in name.lower() for pattern in notification_patterns):
            return False
        
        # Skip all uppercase (likely navigation)
        if name.isupper() and len(name) > 5:
            return False
        
        return True
    
    async def _perform_human_scrolling(self) -> None:
        """Perform human-like scrolling behavior"""
        try:
            # Gradual scrolling
            for i in range(3):
                await self.page.evaluate(f'window.scrollBy(0, {300 + i * 100})')
                await asyncio.sleep(1.5)
            
            # Final scroll to bottom
            await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(5)
            
            # Try to click "See more" buttons
            await self._click_see_more_buttons()
            
        except Exception as e:
            logger.warning(f"Error during scrolling: {e}")
    
    async def _click_see_more_buttons(self) -> None:
        """Click 'See more' buttons if available"""
        see_more_selectors = [
            'text="See more"',
            'text="Show more"',
            'text="Load more"',
            '[aria-label*="See more"]'
        ]
        
        for selector in see_more_selectors:
            try:
                buttons = await self.page.query_selector_all(selector)
                for button in buttons:
                    try:
                        if await button.is_visible():
                            await asyncio.sleep(2)
                            await button.click()
                            await asyncio.sleep(4)
                    except Exception:
                        continue
            except Exception:
                continue
    
    async def get_groups(self) -> List[Dict[str, str]]:
        """Extract groups the user is a member of"""
        try:
            logger.info("Extracting groups list...")
            
            if not self._validate_page_availability():
                return []
            
            groups_url = self._construct_profile_url(self.original_username, "groups")
            logger.info(f"Navigating to groups page: {groups_url}")
            
            if not await self._navigate_with_retries(groups_url):
                return []
            
            if await self._check_privacy_restrictions():
                logger.warning("Groups list is private or empty")
                return []
            
            # Scroll to load more content
            await self._perform_simple_scroll()
            
            # Extract groups
            groups_list = await self._extract_groups_data()
            
            logger.info(f"Extracted {len(groups_list)} groups")
            return groups_list
            
        except Exception as e:
            logger.error(f"Error getting groups: {e}")
            return []
    
    async def _perform_simple_scroll(self) -> None:
        """Perform simple scrolling to load content"""
        try:
            await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(6)
        except Exception as e:
            logger.warning(f"Error during simple scroll: {e}")
    
    async def _extract_groups_data(self) -> List[Dict[str, str]]:
        """Extract groups data from page"""
        groups_list = []
        
        try:
            group_links = await self.page.query_selector_all('a[href*="/groups/"]')
            
            for link in group_links:
                try:
                    name = await link.text_content()
                    href = await link.get_attribute('href')
                    
                    if name and href and name.strip() and "/groups/" in href:
                        # Skip navigation elements
                        if any(skip in name.lower() for skip in ["see all", "more", "groups", "discover", "create"]):
                            continue
                        
                        group_data = {
                            "group_name": self.utils.clean_text(name.strip()),
                            "group_url": href,
                            "bio": ""
                        }
                        
                        # Avoid duplicates
                        if not any(g["group_name"] == group_data["group_name"] for g in groups_list):
                            groups_list.append(group_data)
                            
                except Exception:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error extracting groups data: {e}")
        
        return groups_list
    
    async def get_pages_followed(self) -> List[Dict[str, str]]:
        """Extract pages the user follows"""
        try:
            logger.info("Extracting pages followed...")
            
            if not self._validate_page_availability():
                return []
            
            likes_url = self._construct_profile_url(self.original_username, "likes")
            logger.info(f"Navigating to likes page: {likes_url}")
            
            if not await self._navigate_with_retries(likes_url):
                return []
            
            if await self._check_privacy_restrictions():
                logger.warning("Pages list is private or empty")
                return []
            
            await self._perform_simple_scroll()
            
            pages_list = await self._extract_pages_data()
            
            logger.info(f"Extracted {len(pages_list)} pages")
            return pages_list
            
        except Exception as e:
            logger.error(f"Error getting pages: {e}")
            return []
    
    async def _extract_pages_data(self) -> List[Dict[str, str]]:
        """Extract pages data from page"""
        pages_list = []
        
        try:
            all_links = await self.page.query_selector_all('a[href*="facebook.com/"]')
            
            for link in all_links:
                try:
                    href = await link.get_attribute('href')
                    name = await link.text_content()
                    
                    if not href or not name or not name.strip():
                        continue
                    
                    name = name.strip()
                    
                    # Skip navigation and user profile links
                    if any(skip in href for skip in ['/likes', '/friends', '/photos', '/videos', '/about', '?ref=', '?sk=', '/home', '/feed']):
                        continue
                    
                    # Skip navigation text
                    if any(invalid in name.lower() for invalid in ["see all", "more", "likes", "following", "pages", "mutual", "message", "home", "settings"]):
                        continue
                    
                    # Skip if this is the user's own profile
                    if self.profile_identifier and self.profile_identifier in href:
                        continue
                    
                    page_data = {
                        "page_name": self.utils.clean_text(name),
                        "page_url": href,
                        "bio": ""
                    }
                    
                    # Avoid duplicates
                    if not any(p["page_name"] == page_data["page_name"] for p in pages_list):
                        pages_list.append(page_data)
                        
                except Exception:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error extracting pages data: {e}")
        
        return pages_list
    
    async def get_following_list(self) -> List[Dict[str, str]]:
        """Extract following list with improved filtering"""
        try:
            logger.info("Extracting following list...")
            
            if not self._validate_page_availability():
                return []
            
            following_url = self._construct_profile_url(self.original_username, "following")
            logger.info(f"Navigating to following page: {following_url}")
            
            if not await self._navigate_with_retries(following_url):
                return []
            
            page_content = await self.page.content()
            if "This content isn't available" in page_content:
                logger.warning("Following list is private or empty")
                return []
            
            await self._perform_simple_scroll()
            
            following_list = await self._extract_following_data()
            
            logger.info(f"Extracted {len(following_list)} following")
            return following_list
            
        except Exception as e:
            logger.error(f"Error getting following list: {e}")
            return []
    
    async def _extract_following_data(self) -> List[Dict[str, str]]:
        """Extract following data from page"""
        following_list = []
        
        try:
            all_links = await self.page.query_selector_all('a[href*="facebook.com/"]')
            
            for link in all_links:
                try:
                    href = await link.get_attribute('href')
                    name = await link.text_content()
                    
                    if not href or not name or not name.strip():
                        continue
                    
                    name = name.strip()
                    
                    # Skip the user's own profile (CRITICAL)
                    if self.profile_identifier and (f"/{self.profile_identifier}" in href or href.endswith(self.profile_identifier) or self.profile_identifier in href):
                        continue
                    
                    # Skip navigation and non-profile links
                    if any(skip in href for skip in ['/following/', '/friends/', '/photos/', '/videos/', '/about/', '?ref=', '?sk=', '/home/', '/feed/', '/settings/', '/notifications/']):
                        continue
                    
                    # Skip navigation text
                    if any(invalid in name.lower() for invalid in ["see all", "more", "following", "follow", "unfollow", "mutual", "message", "home", "settings", "photos", "videos"]):
                        continue
                    
                    # Validate it's a real profile URL
                    if not self._is_valid_profile_url(href):
                        continue
                    
                    following_data = {
                        "name": self.utils.clean_text(name),
                        "profile_url": href,
                        "bio": ""
                    }
                    
                    # Avoid duplicates
                    if not any(f["name"] == following_data["name"] for f in following_list):
                        following_list.append(following_data)
                        
                except Exception:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error extracting following data: {e}")
        
        return following_list
    
    def _is_valid_profile_url(self, url: str) -> bool:
        """Validate if URL looks like a real Facebook profile"""
        try:
            if "facebook.com" not in url:
                return False
            
            invalid_patterns = [
                '/groups/', '/pages/', '/events/', '/photos/', '/videos/',
                '/marketplace/', '/gaming/', '/watch/', '/business/',
                '/ads/', '/help/', '/settings/', '/privacy/', '/terms/',
                '?sk=', '?ref=', '#', 'l.facebook.com', 'm.me',
                '/login/', '/signup/', '/recover/', '/security/'
            ]
            
            if any(pattern in url for pattern in invalid_patterns):
                return False
            
            parts = url.split('facebook.com/')
            if len(parts) < 2:
                return False
            
            path = parts[1].split('?')[0].split('#')[0]
            
            # Valid profile patterns
            if path.startswith('profile.php?id='):
                return True
            
            # Username-based profiles
            if len(path) > 0 and '/' not in path.strip('/'):
                return True
            
            return False
            
        except Exception:
            return False 