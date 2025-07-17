"""
Improved Facebook Posts Scraper
Clean, robust implementation with comprehensive error handling
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

class PostsScraper:
    """
    Improved Facebook Posts Scraper with robust error handling and modern design patterns
    """
    
    def __init__(self, page: Page, utils: ScraperUtils):
        """Initialize the PostsScraper with page and utilities"""
        self.page = page
        self.utils = utils
        
        # Configuration
        self.max_retries = 3
        self.default_timeout = 30000
        self.max_posts_per_section = 100
    
    def _clean_input(self, username: str) -> str:
        """Clean and normalize input username/URL"""
        if not username:
            raise ValueError("Username cannot be empty")
        return username.strip().rstrip('/').lstrip('@')
    
    def _detect_profile_type(self, username: str) -> Tuple[str, str]:
        """Detect if input is username or profile ID and return type and identifier"""
        username = self._clean_input(username)
        
        # Handle full Facebook URLs
        if "facebook.com" in username.lower():
            if "profile.php?id=" in username:
                match = re.search(r'profile\.php\?id=(\d+)', username)
                if match:
                    profile_id = match.group(1)
                    logger.info(f"Extracted profile ID from URL: {profile_id}")
                    return "id", profile_id
            else:
                # Extract username from URL
                try:
                    parts = username.lower().split('facebook.com/')
                    if len(parts) > 1:
                        username_part = parts[1].split('/')[0].split('?')[0].split('#')[0]
                        if username_part and not username_part.isdigit() and len(username_part) > 0:
                            logger.info(f"Extracted username from URL: {username_part}")
                            return "username", username_part
                except Exception as e:
                    logger.warning(f"Error extracting username from URL: {e}")
        
        # Handle profile.php format without domain
        if "profile.php?id=" in username:
            match = re.search(r'profile\.php\?id=(\d+)', username)
            if match:
                profile_id = match.group(1)
                logger.info(f"Detected profile.php format: {profile_id}")
                return "id", profile_id
        
        # Handle numeric ID only
        if username.isdigit():
            logger.info(f"Detected numeric profile ID: {username}")
            return "id", username
        
        # Handle username format
        logger.info(f"Detected username format: {username}")
        return "username", username
    
    def _construct_profile_url(self, username: str, section: str = "") -> str:
        """Construct the correct Facebook URL for posts sections"""
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
    
    async def get_own_posts(self, username: str, max_posts: int = None) -> List[Dict[str, Any]]:
        """
        Extract user's own posts with improved error handling and fallback
        
        Args:
            username: Username or profile URL
            max_posts: Maximum number of posts to extract
            
        Returns:
            List of post dictionaries
        """
        try:
            logger.info("Extracting own posts...")
            
            if max_posts is None:
                max_posts = self.max_posts_per_section
            
            # Navigate to posts section
            posts_url = self._construct_profile_url(username)
            logger.info(f"Navigating to profile: {posts_url}")
            
            if not await self._navigate_with_retries(posts_url):
                logger.warning("Failed to navigate to profile, trying fallback...")
                return await self._fallback_posts_extraction(username, max_posts)
            
            # Wait for page to load
            await self._wait_for_posts_to_load()
            
            # Extract posts with scrolling
            posts = await self._extract_posts_with_scrolling("own_posts", max_posts)
            
            # If no posts found, try fallback
            if not posts:
                logger.warning("No posts found with main method, trying fallback...")
                posts = await self._fallback_posts_extraction(username, max_posts)
            
            logger.info(f"Extracted {len(posts)} own posts")
            return posts
            
        except Exception as e:
            logger.error(f"Error getting own posts: {e}")
            # Try fallback as last resort
            try:
                return await self._fallback_posts_extraction(username, max_posts)
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                return []
    
    async def _fallback_posts_extraction(self, username: str, max_posts: int) -> List[Dict[str, Any]]:
        """Fallback method for posts extraction when main method fails"""
        try:
            logger.info("Using fallback posts extraction method...")
            
            # Try to navigate to profile again
            posts_url = self._construct_profile_url(username)
            await self.page.goto(posts_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)
            
            # Simple extraction without scrolling
            posts = []
            post_elements = await self.page.query_selector_all('[role="article"]')
            
            for element in post_elements[:max_posts]:
                try:
                    post_data = await self._extract_single_post(element, "own_posts")
                    if post_data:
                        posts.append(post_data)
                except Exception as e:
                    logger.warning(f"Error in fallback post extraction: {e}")
                    continue
            
            logger.info(f"Fallback extracted {len(posts)} posts")
            return posts
            
        except Exception as e:
            logger.error(f"Fallback posts extraction failed: {e}")
            return []
    
    async def get_tagged_posts(self, username: str, max_posts: int = None) -> List[Dict[str, Any]]:
        """Extract posts where user is tagged"""
        try:
            logger.info("Extracting tagged posts...")
            
            if max_posts is None:
                max_posts = self.max_posts_per_section
            
            # Navigate to tagged posts section
            tagged_url = self._construct_profile_url(username, "photos_of")
            logger.info(f"Navigating to tagged posts: {tagged_url}")
            
            if not await self._navigate_with_retries(tagged_url):
                return []
            
            await self._wait_for_posts_to_load()
            
            posts = await self._extract_posts_with_scrolling("tagged_posts", max_posts)
            
            logger.info(f"Extracted {len(posts)} tagged posts")
            return posts
            
        except Exception as e:
            logger.error(f"Error getting tagged posts: {e}")
            return []
    
    async def get_user_comments(self, username: str, max_comments: int = None) -> List[Dict[str, Any]]:
        """Extract user's comments on other posts"""
        try:
            logger.info("Extracting user comments...")
            
            if max_comments is None:
                max_comments = self.max_posts_per_section
            
            # This would require more complex navigation and searching
            # For now, returning empty list as this is a complex feature
            logger.warning("User comments extraction is not fully implemented yet")
            return []
            
        except Exception as e:
            logger.error(f"Error getting user comments: {e}")
            return []
    
    async def get_locations(self, username: str) -> List[Dict[str, Any]]:
        """Extract location data from posts"""
        try:
            logger.info("Extracting locations...")
            
            # Navigate to places/locations section
            places_url = self._construct_profile_url(username, "map")
            logger.info(f"Navigating to places: {places_url}")
            
            if not await self._navigate_with_retries(places_url):
                return []
            
            await asyncio.sleep(5)
            
            locations = await self._extract_location_data()
            
            logger.info(f"Extracted {len(locations)} locations")
            return locations
            
        except Exception as e:
            logger.error(f"Error getting locations: {e}")
            return []
    
    async def _navigate_with_retries(self, url: str, retries: int = 3) -> bool:
        """Navigate to URL with retries and crash recovery"""
        for attempt in range(retries):
            try:
                # Check if page is still responsive
                try:
                    await self.page.evaluate("() => document.readyState")
                except Exception:
                    logger.warning("Page crashed, attempting to recover...")
                    # Try to recover by going back to Facebook home
                    try:
                        await self.page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=30000)
                        await asyncio.sleep(5)
                    except Exception:
                        logger.error("Failed to recover from crash")
                        return False
                
                # Navigate to target URL
                await self.page.goto(url, wait_until="domcontentloaded", timeout=self.default_timeout)
                await asyncio.sleep(8)  # Human-like delay
                
                # Verify page loaded successfully
                try:
                    page_title = await self.page.title()
                    if "facebook" in page_title.lower() or "error" not in page_title.lower():
                        return True
                except Exception:
                    pass
                    
            except Exception as e:
                logger.warning(f"Navigation attempt {attempt + 1} failed: {e}")
                if attempt == retries - 1:
                    return False
                await asyncio.sleep(10)
        return False
    
    async def _wait_for_posts_to_load(self) -> None:
        """Wait for posts content to load"""
        post_selectors = [
            'div[data-ad-preview="message"]',
            'div[data-ad-comet-preview="message"]'
        ]
        
        content_loaded = False
        for selector in post_selectors:
            try:
                await self.page.wait_for_selector(selector, timeout=10000)
                logger.info(f"Posts loaded using selector: {selector}")
                content_loaded = True
                break
            except PlaywrightTimeoutError:
                continue
        
        if not content_loaded:
            logger.warning("No post selectors found, but continuing...")
        
        # Human-like page observation time
        await asyncio.sleep(8)
    
    async def _extract_posts_with_scrolling(self, post_type: str, max_posts: int) -> List[Dict[str, Any]]:
        """Extract posts with intelligent scrolling and timeout handling"""
        posts = []
        last_count = 0
        stable_rounds = 0
        max_stable_rounds = 5
        max_scrolls = min(30, max_posts // 5 + 10)  # Reduced from 50 to 30
        start_time = time.time()
        max_time = 180  # 3 minutes max
        
        logger.info(f"Starting posts extraction (max {max_scrolls} scrolls)")
        
        for scroll_attempt in range(max_scrolls):
            # Check timeout
            if time.time() - start_time > max_time:
                logger.warning(f"Timeout in posts extraction after {max_time} seconds")
                break
                
            try:
                # Extract current batch of posts
                current_batch = await self._extract_current_posts_batch(post_type)
                
                # Add new posts to list
                for post in current_batch:
                    if not any(p.get("id") == post.get("id") for p in posts if post.get("id")):
                        posts.append(post)
                        if len(posts) >= max_posts:
                            logger.info(f"Reached max posts limit: {max_posts}")
                            return posts
                
                current_count = len(posts)
                new_posts = current_count - last_count
                logger.info(f"Scroll {scroll_attempt + 1}: Found {current_count} total (+{new_posts} new)")
                
                # Take debug screenshot after each scroll
                if hasattr(self.utils, 'take_screenshot'):
                    try:
                        await self.utils.take_screenshot(f"posts_scroll_{scroll_attempt+1}")
                        logger.info(f"[DEBUG] Screenshot taken: posts_scroll_{scroll_attempt+1}")
                    except Exception as e:
                        logger.warning(f"[DEBUG] Could not take screenshot after scroll {scroll_attempt+1}: {e}")
                
                # Check for stability (no new posts found)
                if current_count == last_count:
                    stable_rounds += 1
                    if stable_rounds >= max_stable_rounds:
                        logger.info(f"No new posts found for {max_stable_rounds} rounds, stopping")
                        break
                else:
                    stable_rounds = 0
                
                last_count = current_count
                
                # Perform human-like scrolling
                await self._perform_post_scrolling()
                
            except Exception as e:
                logger.warning(f"Error during scroll {scroll_attempt + 1}: {e}")
                # Continue with next scroll attempt
                continue
        
        return posts
    
    async def _extract_current_posts_batch(self, post_type: str) -> List[Dict[str, Any]]:
        posts_batch = []
        try:
            post_selectors = [
                'div[data-ad-preview="message"]',
                'div[data-ad-comet-preview="message"]'
            ]
            logger.info(f"Trying to extract posts with {len(post_selectors)} selectors...")
            for selector in post_selectors:
                try:
                    post_elements = await self.page.query_selector_all(selector)
                    logger.info(f"[DEBUG] Selector: {selector} - Found {len(post_elements)} elements")
                    # Log the text content of the first 2 elements for debugging
                    for idx, elem in enumerate(post_elements[:2]):
                        try:
                            text = await elem.text_content()
                            logger.info(f"[DEBUG] Selector: {selector} - Element {idx} text: {text[:200] if text else 'None'}")
                        except Exception as e:
                            logger.warning(f"[DEBUG] Could not get text for element {idx}: {e}")
                    for i, element in enumerate(post_elements):
                        try:
                            post_data = await self._extract_single_post(element, post_type)
                            if post_data:
                                posts_batch.append(post_data)
                                logger.info(f"Successfully extracted post {i+1} with selector {selector}")
                            else:
                                logger.debug(f"Post {i+1} with selector {selector} was filtered out")
                        except Exception as e:
                            logger.warning(f"Error extracting post {i+1} with selector {selector}: {e}")
                    if posts_batch:
                        logger.info(f"Successfully extracted {len(posts_batch)} posts with selector: {selector}")
                        break
                except Exception as e:
                    logger.warning(f"Error with selector {selector}: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Error extracting posts batch: {e}")
        logger.info(f"Total posts extracted in this batch: {len(posts_batch)}")
        return posts_batch

    async def _extract_single_post(self, element, post_type: str) -> Optional[Dict[str, Any]]:
        try:
            post_data = {
                "id": "",
                "content": "",
                "timestamp": "",
                "likes": 0,
                "comments": [],
                "shares": 0,
                "media": [],
                "type": post_type
            }
            content = await self._extract_post_content(element)
            post_data["content"] = content
            timestamp = await self._extract_post_timestamp(element)
            post_data["timestamp"] = timestamp
            metrics = await self._extract_post_metrics(element)
            post_data.update(metrics)
            media = await self._extract_post_media(element)
            post_data["media"] = media
            post_data["id"] = self._generate_post_id(content, timestamp)
            # PATCH: Always include the post for debugging
            logger.info(f"[DEBUG] Including post with content length {len(content)}, timestamp: {timestamp}, likes: {metrics.get('likes', 0)}, media: {len(media)}")
            return post_data
        except Exception as e:
            logger.warning(f"Error extracting single post: {e}")
            return None

    async def _extract_post_content(self, element) -> str:
        try:
            # Click all visible 'See more' buttons inside the post element before extracting content
            see_more_selectors = [
                'span:has-text("See more")',
                'a:has-text("See more")',
                'div:has-text("See more")',
                'span[role="button"]:has-text("See more")',
                'div[role="button"]:has-text("See more")',
                '[role="button"]:has-text("See more")',
                '[aria-label="See more"]',
            ]
            for see_more_selector in see_more_selectors:
                try:
                    see_more_buttons = await element.query_selector_all(see_more_selector)
                    for btn in see_more_buttons:
                        if await btn.is_visible():
                            try:
                                await btn.click()
                                logger.info(f"[DEBUG] Clicked 'See more' button with selector: {see_more_selector}")
                                await asyncio.sleep(0.7)  # Wait for content to expand
                            except Exception as e:
                                logger.warning(f"[DEBUG] Failed to click 'See more': {e}")
                except Exception:
                    continue
            content_selectors = [
                'div[data-ad-preview="message"]',
                'div[data-ad-comet-preview="message"]',
                '[data-testid="post_message"]',
                'div[dir="auto"]',
                'span[dir="auto"]',
                'div[data-testid="post_message"]',
                'div[data-testid="post_message_container"]'
            ]
            for selector in content_selectors:
                try:
                    content_elem = await element.query_selector(selector)
                    if content_elem:
                        text = await content_elem.text_content()
                        if text and len(text.strip()) > 1:
                            return self.utils.clean_text(text.strip())
                except Exception:
                    continue
            all_text = await element.text_content()
            if all_text:
                lines = all_text.split('\n')
                content_lines = []
                for line in lines:
                    line = line.strip()
                    if len(line) > 1 and not self._is_unwanted_text(line):
                        content_lines.append(line)
                if content_lines:
                    return self.utils.clean_text('\n'.join(content_lines[:5]))
                # PATCH: Log the full text content for debugging if no content found
                logger.info(f"[DEBUG] No content found by selectors, full text: {all_text[:500]}")
            return ""
        except Exception as e:
            logger.warning(f"Error extracting post content: {e}")
            return ""
    
    def _is_unwanted_text(self, text: str) -> bool:
        """Check if text should be filtered out"""
        unwanted_patterns = [
            "like", "comment", "share", "ago", "minutes", "hours", "days",
            "see more", "see less", "view", "show", "hide", "edit", "delete",
            "report", "save", "follow", "unfollow", "tag", "check-in",
            "photo", "video", "story", "reel", "live", "event"
        ]
        
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in unwanted_patterns) or len(text) < 3  # Reduced from 10 to 3
    
    async def _extract_post_timestamp(self, element) -> str:
        """Extract timestamp from post"""
        try:
            timestamp_selectors = [
                'time',
                '[data-testid="story-subtitle"] a',
                'a[role="link"][tabindex="0"]'
            ]
            
            for selector in timestamp_selectors:
                try:
                    time_elem = await element.query_selector(selector)
                    if time_elem:
                        # Try datetime attribute first
                        datetime_attr = await time_elem.get_attribute('datetime')
                        if datetime_attr:
                            return datetime_attr
                        
                        # Try text content
                        time_text = await time_elem.text_content()
                        if time_text and ('ago' in time_text.lower() or 'at' in time_text.lower()):
                            return self.utils.clean_text(time_text.strip())
                except Exception:
                    continue
            
            return ""
            
        except Exception as e:
            logger.warning(f"Error extracting timestamp: {e}")
            return ""
    
    async def _extract_post_metrics(self, element) -> Dict[str, Any]:
        """Extract likes, comments, shares counts"""
        metrics = {"likes": 0, "comments": [], "shares": 0}
        
        try:
            # Extract likes count
            likes_selectors = [
                '[data-testid="like_def"]',
                'span[aria-label*="reaction"]',
                'span[aria-label*="like"]'
            ]
            
            for selector in likes_selectors:
                try:
                    likes_elem = await element.query_selector(selector)
                    if likes_elem:
                        likes_text = await likes_elem.text_content()
                        if likes_text:
                            metrics["likes"] = self._extract_number_from_text(likes_text)
                            break
                except Exception:
                    continue
            
            # Extract comments (simplified - just count, not content)
            comments_selectors = [
                '[data-testid="UFI2Comment/root"]',
                'div[role="article"] ul li'
            ]
            
            for selector in comments_selectors:
                try:
                    comment_elements = await element.query_selector_all(selector)
                    metrics["comments"] = [{"content": "Comment content not extracted", "author": "Unknown"} for _ in comment_elements[:5]]
                    if comment_elements:
                        break
                except Exception:
                    continue
            
            # Extract shares count
            shares_selectors = [
                '[aria-label*="share"]',
                'span[data-testid="UFI2SharesCount/root"]'
            ]
            
            for selector in shares_selectors:
                try:
                    shares_elem = await element.query_selector(selector)
                    if shares_elem:
                        shares_text = await shares_elem.text_content()
                        if shares_text:
                            metrics["shares"] = self._extract_number_from_text(shares_text)
                            break
                except Exception:
                    continue
            
        except Exception as e:
            logger.warning(f"Error extracting metrics: {e}")
        
        return metrics
    
    def _extract_number_from_text(self, text: str) -> int:
        """Extract numeric value from text like '123 likes' or '1.2K comments'"""
        try:
            text = text.lower().strip()
            
            # Handle K, M notation
            if 'k' in text:
                number_part = re.search(r'(\d+\.?\d*)', text)
                if number_part:
                    return int(float(number_part.group(1)) * 1000)
            elif 'm' in text:
                number_part = re.search(r'(\d+\.?\d*)', text)
                if number_part:
                    return int(float(number_part.group(1)) * 1000000)
            else:
                # Extract regular number
                number_part = re.search(r'(\d+)', text)
                if number_part:
                    return int(number_part.group(1))
            
            return 0
            
        except Exception:
            return 0
    
    async def _extract_post_media(self, element) -> List[Dict[str, str]]:
        """Extract media (images, videos) from post"""
        media = []
        
        try:
            # Extract images
            img_elements = await element.query_selector_all('img')
            for img in img_elements:
                try:
                    src = await img.get_attribute('src')
                    alt = await img.get_attribute('alt')
                    if src and 'profile' not in src.lower() and 'icon' not in src.lower():
                        media.append({
                            "type": "image",
                            "url": src,
                            "description": alt or ""
                        })
                except Exception:
                    continue
            
            # Extract videos
            video_elements = await element.query_selector_all('video')
            for video in video_elements:
                try:
                    src = await video.get_attribute('src')
                    if src:
                        media.append({
                            "type": "video",
                            "url": src,
                            "description": ""
                        })
                except Exception:
                    continue
            
        except Exception as e:
            logger.warning(f"Error extracting media: {e}")
        
        return media[:5]  # Limit to 5 media items per post
    
    def _generate_post_id(self, content: str, timestamp: str) -> str:
        """Generate a unique-ish ID for the post"""
        try:
            import hashlib
            content_hash = hashlib.md5(f"{content}_{timestamp}".encode()).hexdigest()[:8]
            return f"post_{content_hash}"
        except Exception:
            import time
            return f"post_{int(time.time())}"
    
    async def _perform_post_scrolling(self) -> None:
        """Perform human-like scrolling for posts"""
        try:
            # Gradual scrolling
            for i in range(2):
                await self.page.evaluate(f'window.scrollBy(0, {400 + i * 200})')
                await asyncio.sleep(2)
            
            # Scroll to bottom
            await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(5)
            
            # Explicit wait for post selector after scrolling
            try:
                await self.page.wait_for_selector('div[data-ad-preview="message"], div[data-ad-comet-preview="message"]', timeout=15000)
            except Exception as e:
                logger.warning(f"[DEBUG] No post selector found after scroll: {e}")
            
            # Try to click "See more posts" if available
            await self._click_see_more_posts()
            
        except Exception as e:
            logger.warning(f"Error during post scrolling: {e}")
    
    async def _click_see_more_posts(self) -> None:
        """Click 'See more posts' buttons if available"""
        see_more_selectors = [
            'text="See more posts"',
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
    
    async def _extract_location_data(self) -> List[Dict[str, Any]]:
        """Extract location data from places/map page"""
        locations = []
        
        try:
            # Wait for map or location content to load
            await asyncio.sleep(5)
            
            # Try to find location elements
            location_selectors = [
                'div[data-testid="place"]',
                'a[href*="/places/"]',
                'div[role="link"]'
            ]
            
            for selector in location_selectors:
                try:
                    location_elements = await self.page.query_selector_all(selector)
                    for element in location_elements:
                        try:
                            name_elem = await element.query_selector('span, div')
                            if name_elem:
                                name = await name_elem.text_content()
                                if name and len(name.strip()) > 3:
                                    location_data = {
                                        "name": self.utils.clean_text(name.strip()),
                                        "address": "",
                                        "coordinates": "",
                                        "visit_count": 1
                                    }
                                    
                                    # Avoid duplicates
                                    if not any(loc["name"] == location_data["name"] for loc in locations):
                                        locations.append(location_data)
                        except Exception:
                            continue
                    
                    if locations:
                        break  # Found locations with this selector
                        
                except Exception:
                    continue
            
            # Limit to reasonable number
            return locations[:20]
            
        except Exception as e:
            logger.warning(f"Error extracting location data: {e}")
            return [] 