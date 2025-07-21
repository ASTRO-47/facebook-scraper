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
    
    async def get_all_post_types(self, username: str, max_posts: int = 20) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract all types of posts (own, tagged, shared) in a single run.
        This is more efficient as it avoids multiple page navigations.
        """
        all_posts = {
            "own_posts": [],
            "tagged_posts": [],
            "shared_posts": []
        }
        
        try:
            logger.info(f"🚀 Starting comprehensive post extraction for {username}")
            
            # Navigate to the main profile page
            profile_url = self._construct_profile_url(username)
            if not await self._navigate_with_retries(profile_url):
                logger.error(f"❌ Failed to navigate to profile {profile_url}")
                return all_posts
            
            await self._wait_for_posts_to_load()
            
            # Save the initial HTML of the posts page for debugging
            clean_username = self._detect_profile_type(username)[1]
            await self.utils.save_page_html(f"{clean_username}_posts_page_debug.html")

            # Extract all posts from the main feed
            logger.info("🔍 Extracting all visible posts from the main feed...")
            extracted_posts = await self._extract_posts_with_scrolling("all_posts", max_posts)
            
            # Categorize posts
            for post in extracted_posts:
                if post.get("shared"):
                    all_posts["shared_posts"].append(post)
                elif post.get("is_tagged"):
                    all_posts["tagged_posts"].append(post)
                else:
                    all_posts["own_posts"].append(post)
            
            logger.info(f"📊 Categorization complete:")
            logger.info(f"   - Own posts: {len(all_posts['own_posts'])}")
            logger.info(f"   - Tagged posts: {len(all_posts['tagged_posts'])}")
            logger.info(f"   - Shared posts: {len(all_posts['shared_posts'])}")
            
            return all_posts
            
        except Exception as e:
            logger.error(f"❌ Error in get_all_post_types: {e}", exc_info=True)
            return all_posts

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
            'div[role="article"]',
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
        max_time = 300  # 5 minutes max
        
        logger.info(f"Starting posts extraction (max {max_scrolls} scrolls, {max_time/60:.1f} min timeout)")
        
        # More robust post container selector
        post_container_selector = 'div[role="main"]'

        for scroll_attempt in range(max_scrolls):
            # Check timeout
            if time.time() - start_time > max_time:
                logger.warning(f"Timeout reached in posts extraction after {max_time/60:.1f} minutes. Returning {len(posts)} posts found so far.")
                break
                
            try:
                # Extract current batch of posts
                current_batch = await self._extract_current_posts_batch(post_type, post_container_selector)
                
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
                
                # # Take debug screenshot after each scroll
                # if hasattr(self.utils, 'take_screenshot'):
                #     try:
                #         await self.utils.take_screenshot(f"posts_scroll_{scroll_attempt+1}")
                #         logger.info(f"[DEBUG] Screenshot taken: posts_scroll_{scroll_attempt+1}")
                #     except Exception as e:
                #         logger.warning(f"[DEBUG] Could not take screenshot after scroll {scroll_attempt+1}: {e}")
                
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
    
    async def _extract_current_posts_batch(self, post_type: str, container_selector: str) -> List[Dict[str, Any]]:
        posts_batch = []
        try:
            # Find the main container
            container = await self.page.query_selector(container_selector)
            if not container:
                logger.warning(f"Could not find post container with selector: {container_selector}. Falling back to page-wide search.")
                # If main container isn't found, search the whole page for articles
                post_elements = await self.page.query_selector_all('div[role="article"]')
            else:
                logger.info(f"Found post container with selector: {container_selector}. Searching for articles within.")
                # Search for articles only within the main container
                post_elements = await container.query_selector_all('div[role="article"]')

            logger.info(f"[DEBUG] Found {len(post_elements)} potential post elements.")

            for i, element in enumerate(post_elements):
                try:
                    post_data = await self._extract_single_post(element, post_type)
                    # Check for post_data and that the ID is not None before checking for duplicates
                    if post_data and post_data.get("id") and not any(p.get("id") == post_data.get("id") for p in posts_batch):
                        posts_batch.append(post_data)
                        logger.info(f"Successfully extracted and added new post {i+1}")
                    else:
                        logger.debug(f"Post {i+1} was a duplicate, empty, or filtered out")
                except Exception as e:
                    logger.warning(f"Error processing single post element {i+1}: {e}", exc_info=True)

        except Exception as e:
            logger.warning(f"Error in _extract_current_posts_batch: {e}", exc_info=True)
            
        logger.info(f"Total new posts extracted in this batch: {len(posts_batch)}")
        return posts_batch

    async def _extract_single_post(self, element, post_type: str) -> Optional[Dict[str, Any]]:
        post_id = ""
        try:
            # Generate a unique ID for the post
            timestamp_for_id = await self._extract_post_timestamp(element)
            content_for_id = await self._extract_post_content(element)
            post_id = self._generate_post_id(content_for_id, timestamp_for_id)
            logger.info(f"Processing post with generated ID: {post_id}")

            # Basic post data
            content = content_for_id
            timestamp = timestamp_for_id
            original_url = await self._extract_post_url(element)
            
            # Metrics
            reactions = await self._extract_post_reactions(element)
            metrics = await self._extract_post_metrics(element)
            
            # Media
            media = await self._extract_post_media(element)
            
            # Comments
            comments = await self._extract_post_comments(element)

            # Categorization
            is_shared, shared_content, original_poster = await self._detect_shared_post(element)
            is_tagged = await self._detect_tagged_post(element, content)

            post_data = {
                "id": post_id,
                "timestamp": timestamp,
                "content": content,
                "caption": content, # Simplified for now
                "media_screenshot_url": "", # Disabled for performance
                "original_url": original_url,
                "shared": is_shared,
                "shared_content": shared_content,
                "original_poster": original_poster,
                "is_tagged": is_tagged,
                "tagged_accounts": [], # To be implemented
                "location_tagged": "", # To be implemented
                "comments": comments,
                "reactions": reactions,
                "comments_count": metrics.get("comments", len(comments)),
                "shares_count": metrics.get("shares", 0),
                "media": media
            }
            
            logger.info(f"Successfully extracted post data for ID: {post_id}")
            return post_data

        except Exception as e:
            logger.error(f"❌ Critical error in _extract_single_post for post_id {post_id}: {e}", exc_info=True)
            clean_username = self._detect_profile_type(self.page.url)[1]
            await self.utils.save_page_html(f"{clean_username}_post_extraction_error_{post_id}.html")
            return None

    async def _perform_post_scrolling(self):
        """Performs a more human-like and robust scroll action"""
        try:
            logger.info("📜 Scrolling down the page...")
            # Scroll a bit less than a full viewport to keep context
            await self.page.evaluate("window.scrollBy(0, window.innerHeight * 0.8);")
            await self.utils.human_like_delay(3, 6)
        except Exception as e:
            logger.warning(f"Could not perform scroll: {e}")
            # Fallback to simple scroll
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            await asyncio.sleep(5)

    async def _extract_post_content(self, element) -> str:
        """Extracts the main text content of a post with improved selectors."""
        try:
            content_text = ""
            
            # First, expand any "See more" buttons to get full content
            try:
                see_more_buttons = await element.query_selector_all('div[role="button"], span[role="button"]')
                for button in see_more_buttons:
                    try:
                        button_text = await button.text_content()
                        if button_text and any(x in button_text.lower() for x in ["see more", "show more", "view more", "more"]):
                            await button.click()
                            await asyncio.sleep(2)  # Wait for expansion
                            logger.debug("Expanded 'See more' content")
                    except Exception as e:
                        logger.debug(f"Error clicking see more: {e}")
                        continue
            except Exception as e:
                logger.debug(f"Error handling see more buttons: {e}")
            
            # Enhanced content selectors with more modern Facebook classes
            content_selectors = [
                # New Facebook content containers (2024)
                'div[data-ad-comet-preview="message"]',
                'div[data-ad-preview="message"]',
                'div[data-testid="post_message"]',
                'div[class*="userContent"]',
                
                # Main post text areas
                'div.x1iorvi4.x1pi30zi.x1l90r2v.x1swvt13',
                'div.xdj266r.x11i5rnm.xat24cr.x1mh8g0r',
                'div.x1cy8zhl.x78zum5.x1q0g3np.xz9dl7a',
                
                # Text content with direction attributes
                'div[dir="auto"]:not([role="button"]):not([role="tab"]):not([role="menuitem"])',
                'span[dir="auto"]:not([role="button"]):not([role="tab"]):not([role="menuitem"])',
                
                # Specific text containers
                'div.x193iq5w.xeuugli.x13faqbe.x1vvkbs.x1xmvt09.x1lliihq.x1s928wv.xhkezso.x1gmr53x.x1cpjm7i.x1fgarty.x1943h6x.x4zkp8e.x676frb.x1nxh6w3.x1sibtaa.xo1l8bm.xi81zsa',
                'div.x1cy8zhl.x1q0g3np.x78zum5.x2lwn1j.xeuugli.x1qhmfi1',
                
                # Shared post content
                'div.x1i10hfl.xjbqb8w > div[dir="auto"]',  # Shared post text
                
                # Fallback content areas
                'div.xvijz8h',  # General content container
                'div[style*="text-align"][dir="auto"]'  # Styled text content
            ]
            
            # Try each selector in order with enhanced filtering
            for selector in content_selectors:
                try:
                    elements = await element.query_selector_all(selector)
                    for el in elements:
                        try:
                            # Skip elements that are clearly not content
                            role = await el.get_attribute('role')
                            if role in ['button', 'menuitem', 'tab', 'navigation', 'banner']:
                                continue
                                
                            # Skip elements with specific classes that indicate UI elements
                            class_attr = await el.get_attribute('class')
                            if class_attr and any(skip_class in class_attr for skip_class in [
                                'navigation', 'menu', 'toolbar', 'header', 'footer', 'sidebar'
                            ]):
                                continue
                                
                            # Get text content
                            text = await el.text_content()
                            if text and len(text.strip()) > 5:  # Minimum length for meaningful content
                                clean_text = text.strip()
                                # Skip if it's metadata, reactions, or UI text
                                if not self._is_metadata(clean_text) and not self._is_ui_text(clean_text):
                                    content_text = clean_text
                                    break
                        except:
                            continue
                    if content_text:
                        break
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue

            # Enhanced fallback: Look for substantial text in any div
            if not content_text:
                try:
                    all_text_elements = await element.query_selector_all('div, span, p')
                    text_candidates = []
                    
                    for div in all_text_elements:
                        try:
                            # Skip interactive elements
                            role = await div.get_attribute('role')
                            if role in ['button', 'menuitem', 'tab', 'navigation']:
                                continue
                                
                            text = await div.text_content()
                            if text and len(text.strip()) > 15:  # Longer text more likely to be content
                                clean_text = text.strip()
                                if not self._is_metadata(clean_text) and not self._is_ui_text(clean_text):
                                    text_candidates.append(clean_text)
                        except:
                            continue
                    
                    # Select the longest meaningful text as content
                    if text_candidates:
                        content_text = max(text_candidates, key=len)
                        
                except Exception as e:
                    logger.debug(f"Error in fallback content extraction: {e}")

            return content_text or ""
        except Exception as e:
            logger.error(f"Error extracting post content: {e}")
            return ""

    async def _extract_post_timestamp(self, element) -> str:
        """Extracts the timestamp of a post."""
        try:
            # Timestamp selectors in order of reliability
            timestamp_selectors = [
                # Primary timestamp selectors
                'a[role="link"][aria-label*="hour"], a[role="link"][aria-label*="minute"]',  # Recent posts
                'a[role="link"][aria-label*="at"]',  # Posts with specific time
                'a.x1i10hfl.xjbqb8w:has(span[title])',  # Links with timestamp tooltips
                
                # Secondary timestamp containers
                'span.x4k7w5x.x1h91t0o.x1h9r5lt.x1jfb8zj',  # Modern timestamp format
                'span.x1xmf6yo',  # Alternative timestamp format
                'a[href*="permalink"][role="link"]',  # Permalink timestamps
                
                # Timestamp indicators
                'a[href*="/posts/"][role="link"]',  # Post links
                'a[href*="story_fbid="][role="link"]',  # Story links
                'a[href*="/photos/"][role="link"]',  # Photo timestamps
                'a[href*="/videos/"][role="link"]'  # Video timestamps
            ]
            
            for selector in timestamp_selectors:
                elements = await element.query_selector_all(selector)
                for el in elements:
                    try:
                        # Check multiple sources for timestamp
                        timestamp = None
                        
                        # 1. Check aria-label (most reliable)
                        aria_label = await el.get_attribute('aria-label')
                        if aria_label:
                            # Look for full date pattern
                            date_pattern = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+,?\s+(?:20\d{2}|19\d{2})(?:\s+at\s+\d+:\d+(?:\s*[AaPp][Mm])?)?'
                            match = re.search(date_pattern, aria_label)
                            if match:
                                timestamp = match.group(0)
                            else:
                                # Look for relative time
                                time_pattern = r'\b(?:\d+\s+(?:second|minute|hour|day|week|month|year)s?\s+ago|yesterday|just now)\b'
                                match = re.search(time_pattern, aria_label, re.IGNORECASE)
                                if match:
                                    timestamp = match.group(0)
                                    
                        # 2. Check title attribute
                        if not timestamp:
                            title = await el.get_attribute('title')
                            if title:
                                timestamp = title.strip()
                                
                        # 3. Check text content as fallback
                        if not timestamp:
                            text = await el.text_content()
                            if text and text.strip() and not text.strip().isdigit():
                                timestamp = text.strip()
                    
                        # Return first valid timestamp found
                        if timestamp:
                            return timestamp
                            
                    except Exception as e:
                        logger.debug(f"Error processing timestamp element: {e}")
                        continue
            
            # If no timestamp found, return empty string
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting timestamp: {e}")
            return ""
                    
    async def _extract_post_url(self, element) -> str:
        """Extracts the permalink URL of a post."""
        try:
            # Using the same robust selector as the timestamp
            timestamp_selector = 'a[aria-label][href*="/posts/"], a[aria-label][href*="/videos/"], a[aria-label][href*="?story_fbid="]'
            link_element = await element.query_selector(timestamp_selector)
            if link_element:
                href = await link_element.get_attribute('href')
                if href:
                    # Ensure it's a full URL
                    if href.startswith('/'):
                        return f"https://www.facebook.com{href}"
                    return href
        except Exception as e:
            logger.debug(f"Error extracting post URL: {e}")
        return ""

    async def _extract_post_metrics(self, element) -> Dict[str, int]:
        """Extracts comment and share counts."""
        metrics = {"comments": 0, "shares": 0}
        try:
            # The metrics are usually in a container below the like/comment/share buttons.
            # This selector targets that container.
            metrics_container_selector = 'div[class="x1i10hfl x1jx91rp x1sg6plg x1swvt13 x1pi30zi x1y1aw1k xwib8y2 x1y332i5"]'
            metrics_container = await element.query_selector(metrics_container_selector)
            if metrics_container:
                metrics_text = await metrics_container.text_content()
                
                comments_match = re.search(r'([\d,]+\.?\d*K?)\s+comment', metrics_text, re.IGNORECASE)
                if comments_match:
                    metrics["comments"] = self.utils.parse_count(comments_match.group(1))

                shares_match = re.search(r'([\d,]+\.?\d*K?)\s+share', metrics_text, re.IGNORECASE)
                if shares_match:
                    metrics["shares"] = self.utils.parse_count(shares_match.group(1))
        except Exception as e:
            logger.debug(f"Could not extract post metrics: {e}")
        return metrics

    async def _extract_post_media(self, element) -> List[Dict[str, str]]:
        """Extracts media (images, videos) from post"""
        media_list = []
        try:
            # Image selectors targeting actual post images, not icons/emojis
            image_selectors = [
                'div[data-visualcompletion="media-vc-image"] img',
                'img.x1ey2m1c.xds687c.x5yr21d.x10l6tqk',
                'img[data-visualcompletion="media-vc-image"]',
                'img.x1b0d499.xuo83w3',
                'div[role="article"] img[src*="scontent"]', # Facebook CDN images
                'a[role="link"] img[alt]:not([alt=""])', # Linked images with alt text
            ]
            
            for selector in image_selectors:
                image_elements = await element.query_selector_all(selector)
                for img in image_elements:
                    src = await img.get_attribute('src')
                    alt = await img.get_attribute('alt')
                    if src and not any(x in src.lower() for x in ['emoji', 'profile', 'data:', 'static']):
                        # Get high quality image URL
                        src = src.replace('&amp;', '&') # Fix encoded URLs
                        src = re.sub(r'[\?&]_nc_cat=\d+', '', src) # Remove cache buster
                        src = re.sub(r'&_nc_[a-z]+=[^&]+', '', src) # Remove FB parameters
                        # Get largest size by removing size parameters
                        src = re.sub(r'[?&](?:oh|oe|w|h)=\d+', '', src)
                        media_list.append({"type": "image", "url": src, "alt": alt or ""})

            # Video selectors
            video_selectors = [
                'video',
                'div[data-video-id]',
                'div[data-video-url]',
                'div[data-visualcompletion="media-vc-video"]',
                'div[aria-label*="video"]',
            ]
            
            for selector in video_selectors:
                video_elements = await element.query_selector_all(selector)
                for video in video_elements:
                    # Try multiple attributes that might contain the video URL
                    for attr in ['src', 'data-video-url', 'href', 'data-url']:
                        url = await video.get_attribute(attr)
                        if url and 'video' in url.lower():
                            # Clean up video URL similarly to images
                            url = url.replace('&amp;', '&')
                            url = re.sub(r'[\?&]_nc_cat=\d+', '', url)
                            url = re.sub(r'&_nc_[a-z]+=[^&]+', '', url)
                            media_list.append({"type": "video", "url": url})
                            break # Found valid URL, move to next element
        except Exception as e:
            logger.debug(f"Could not extract post media: {e}")
        return media_list

    def _generate_post_id(self, content: str, timestamp: str) -> str:
        """Generates a unique ID for a post based on its content and timestamp."""
        import hashlib
        if not content and not timestamp:
            return hashlib.md5(str(time.time()).encode()).hexdigest()
        
        return hashlib.md5((content[:50] + timestamp).encode()).hexdigest()

    async def _extract_post_reactions(self, element) -> Dict[str, Any]:
        """Extracts detailed reaction counts (likes, loves, etc.)"""
        reactions = {"total": 0, "types": {}}
        try:
            # Get all interactive elements that might contain reaction info
            all_divs = await element.query_selector_all('div')
            
            for div in all_divs:
                try:
                    # Check aria-label for reaction information
                    aria_label = await div.get_attribute('aria-label')
                    if not aria_label:
                        continue
                        
                    # Look for reaction patterns
                    if "reactions" in aria_label.lower():
                        # Get total reactions
                        total_match = re.search(r'([\d,]+)\s*(?:reaction|person|people)', aria_label, re.IGNORECASE)
                        if total_match:
                            reactions["total"] = self.utils.parse_count(total_match.group(1))
                            
                        # Extract individual reaction types
                        reaction_matches = re.findall(r'(\d+)\s+(like|love|care|haha|wow|sad|angry)', aria_label, re.IGNORECASE)
                        for count, reaction_type in reaction_matches:
                            reactions["types"][reaction_type.lower()] = self.utils.parse_count(count)
                            
                        if reactions["total"] > 0:
                            break
                            
                    # Handle single reaction type (e.g. "Like")
                    elif any(word in aria_label.lower() for word in ['like', 'love', 'care', 'haha', 'wow', 'sad', 'angry']):
                        reactions["total"] = 1
                        reaction_type = re.search(r'(like|love|care|haha|wow|sad|angry)', aria_label, re.IGNORECASE)
                        if reaction_type:
                            reactions["types"][reaction_type.group(1).lower()] = 1
                except Exception as e:
                    continue
                    
            # If still no reactions found, try span elements
            if reactions["total"] == 0:
                spans = await element.query_selector_all('span')
                for span in spans:
                    try:
                        text = await span.text_content()
                        if not text:
                            continue
                            
                        # Look for reaction counts
                        count_match = re.search(r'([\d,]+(?:\.\d+)?[KMB]?)\s*(?:like|reaction)', text, re.IGNORECASE)
                        if count_match:
                            reactions["total"] = self.utils.parse_count(count_match.group(1))
                            reactions["types"]["like"] = reactions["total"]
                            break
                    except:
                        continue
        except Exception as e:
            logger.debug(f"Could not extract post reactions: {e}")
        return reactions

    def _is_metadata(self, text: str) -> bool:
        """Check if text is metadata like timestamps, likes, comments, etc."""
        metadata_patterns = [
            r'^\d+$',  # Just numbers
            r'^\d+[KMB]$',  # Numbers with K,M,B
            r'\b\d+\s*(?:like|share|comment)s?\b',  # Engagement counts
            r'\b(?:just now|now|yesterday)\b',  # Recent time indicators
            r'\b\d+\s*(?:second|minute|hour|day|week|month|year)s?\s*ago\b',  # Time ago
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+\b',  # Month dates
            r'\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b',  # Days
            r'^\s*(?:Like|Comment|Share|Reply)\s*$',  # Action buttons
            r'(?:Public|Friends|Only me)',  # Privacy settings
            r'Edited',  # Edit indicator
        ]
        text = text.strip()
        if not text:
            return True
        
        # Check if text matches any metadata pattern
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in metadata_patterns)

    def _is_ui_text(self, text: str) -> bool:
        """Check if text is likely UI element text rather than post content"""
        ui_indicators = [
            'like', 'comment', 'share', 'react', 'follow', 'friend', 'add friend',
            'message', 'more options', 'see more', 'hide', 'report', 'block',
            'activity', 'notification', 'settings', 'privacy', 'help',
            'marketplace', 'groups', 'pages', 'events', 'photos', 'videos',
            'create post', 'what\'s on your mind', 'add to story',
            'sponsored', 'suggested for you', 'people you may know'
        ]
        
        text_lower = text.lower()
        # Check if text is very short or matches UI patterns
        if len(text) < 3 or any(indicator in text_lower for indicator in ui_indicators):
            return True
            
        # Check if text is just numbers, reactions, or single words
        if text.isdigit() or len(text.split()) == 1 and len(text) < 10:
            return True
            
        return False

    async def _extract_post_comments(self, element) -> List[Dict[str, Any]]:
        """Extracts comments from a post."""
        comments = []
        try:
            # Click "View more comments" or similar button to load more comments
            view_comments_selectors = [
                'div[role="button"]:has-text("View more comments")',
                'div[role="button"]:has-text("View all comments")',
                'div[role="button"]:has-text("previous comments")'
            ]
            for selector in view_comments_selectors:
                button = await element.query_selector(selector)
                if button:
                    try:
                        await button.click(timeout=2000)
                        await self.page.wait_for_timeout(2000) # Wait for comments to load
                        logger.info("Clicked to expand comments.")
                    except Exception as e:
                        logger.debug(f"Could not click view comments button: {e}")
                    break

            # More specific selector for individual comment blocks
            comment_elements = await element.query_selector_all('div[aria-label*="Comment by"], div.x168nmei.x13lgxp2.x30kzoy.x9jhf4c.x1emribx')
            for i, comment_elem in enumerate(comment_elements[:10]): # Limit comments for performance
                try:
                    # Find author and content within the comment block
                    author_elem = await comment_elem.query_selector('a[role="link"]:not([aria-label])')
                    content_elem = await comment_elem.query_selector('div[dir="auto"]')
                    
                    if author_elem and content_elem:
                        author = await author_elem.text_content()
                        author_url = await author_elem.get_attribute('href')
                        content = await content_elem.text_content()
                        
                        if author and content and not self._is_comment_metadata(content):
                            comments.append({
                                "author": self.utils.clean_text(author),
                                "author_url": author_url,
                                "content": self.utils.clean_text(content)
                            })
                except Exception as e:
                    logger.debug(f"Could not extract comment {i+1}: {e}")
        except Exception as e:
            logger.debug(f"Could not extract post comments: {e}")
        return comments

    async def _detect_shared_post(self, element) -> Tuple[bool, str, str]:
        """Detects if a post is a share and extracts original poster info."""
        try:
            # A shared post often has a header indicating who shared it, and a nested block with the original post.
            # This selector looks for the nested block which is a common pattern for shared content.
            shared_post_block_selector = 'div[style*="border-left"]'
            nested_article = await element.query_selector(shared_post_block_selector)
            
            if nested_article:
                # If we found the block, it's a share. Now get the details.
                original_poster_elem = await nested_article.query_selector('a[href*="/groups/"] strong, a[href*="/pages/"] strong, strong a')
                shared_content_elem = await nested_article.query_selector('div[data-ad-preview="message"], div[dir="auto"]')
                
                original_poster = await original_poster_elem.text_content() if original_poster_elem else ""
                shared_content = await shared_content_elem.text_content() if shared_content_elem else ""
                
                return True, self.utils.clean_text(shared_content), self.utils.clean_text(original_poster)
        except Exception as e:
            logger.debug(f"Error detecting shared post: {e}")
        return False, "", ""

    async def _detect_tagged_post(self, element, content: str) -> bool:
        """Detects if the post is a tagged post."""
        try:
            # Look for "is with" text in the post header, avoiding the main content
            header_text_element = await element.query_selector('h3, h4')
            if header_text_element:
                header_text = await header_text_element.text_content()
                if "is with" in header_text and header_text not in content:
                    return True
        except Exception as e:
            logger.debug(f"Error detecting tagged post: {e}")
        return False

    async def _extract_location_tagged(self, element) -> str:
        """Extracts the tagged location from a post."""
        # This is a placeholder for future implementation
        return ""