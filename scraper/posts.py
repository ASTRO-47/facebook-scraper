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
            # Detect if this is a shared post
            is_shared = False
            shared_content = ""
            try:
                shared_marker_selectors = [
                    'span:has-text("shared")',
                    'span:has-text("shared a post")',
                    'span:has-text("shared a memory")',
                    'span:has-text("shared a link")',
                    'span:has-text("shared a photo")',
                    'span:has-text("shared a video")',
                    'span[role="button"]:has-text("shared")',
                ]
                for selector in shared_marker_selectors:
                    marker = await element.query_selector(selector)
                    if marker:
                        is_shared = True
                        break
                if is_shared:
                    shared_content_selectors = [
                        'div[role="article"]',
                        'div[data-ad-preview="message"]',
                        'div[data-ad-comet-preview="message"]',
                        '[data-testid="post_message"]',
                        'div[dir="auto"]',
                        'span[dir="auto"]',
                    ]
                    for sc_selector in shared_content_selectors:
                        try:
                            shared_elem = await element.query_selector(sc_selector)
                            if shared_elem:
                                shared_content = await shared_elem.text_content()
                                if shared_content and len(shared_content.strip()) > 1:
                                    shared_content = self.utils.clean_text(shared_content.strip())
                                    break
                        except Exception:
                            continue
            except Exception as e:
                logger.warning(f"[DEBUG] Error detecting shared post: {e}")

            # Extract main content
            content = await self._extract_post_content(element)
            timestamp = await self._extract_post_timestamp(element)
            metrics = await self._extract_post_metrics(element)
            media = await self._extract_post_media(element)
            post_id = self._generate_post_id(content, timestamp)

            # Extract caption (try to find a subtitle or secondary text)
            caption = ""
            try:
                caption_selectors = [
                    'div[data-ad-comet-preview="message"] span',
                    'div[data-ad-preview="message"] span',
                    'span[dir="auto"]',
                    'div[dir="auto"] span',
                ]
                for selector in caption_selectors:
                    cap_elem = await element.query_selector(selector)
                    if cap_elem:
                        cap_text = await cap_elem.text_content()
                        if cap_text and cap_text.strip() != content:
                            caption = self.utils.clean_text(cap_text.strip())
                            break
            except Exception:
                pass

            # Media screenshot URL (improved with error handling)
            media_screenshot_url = ""
            try:
                if hasattr(self.utils, 'take_screenshot'):
                    # Try to screenshot the main post content area
                    screenshot_selector = 'div[data-ad-preview="message"]' or 'div[role="article"]'
                    screenshot_path = await self.utils.take_screenshot(f"post_{post_id}", screenshot_selector)
                    if screenshot_path:
                        # Convert local path to URL path
                        media_screenshot_url = screenshot_path.replace("static/", "/static/").replace("../static/", "/static/")
            except Exception as e:
                logger.warning(f"Failed to take post screenshot: {e}")

            # Extract reaction counts (likes, loves, etc.)
            reactions = await self._extract_post_reactions(element)
            
            # Extract additional metrics
            metrics = await self._extract_post_metrics(element)
            shares_count = metrics.get("shares", 0)
            
            # Initialize comments list (moved from below to fix variable reference error)
            comments = []
            
            # This will be updated after comments are extracted
            comments_count = metrics.get("comments", 0)

            # Original URL (improved extraction for permalinks)
            original_url = ""
            try:
                link_selectors = [
                    'a[href*="/posts/"]',
                    'a[href*="/permalink/"]',
                    'a[href*="/story_fbid="]',
                    'a[href*="/photo.php"]',
                    'a[href*="/video.php"]',
                    'a[aria-label*="permalink"]',
                    'time[datetime] parent::a',
                    'a[role="link"][href*="facebook.com"]',
                ]
                
                for selector in link_selectors:
                    link_elems = await element.query_selector_all(selector)
                    for link_elem in link_elems:
                        href = await link_elem.get_attribute('href')
                        if href and "facebook.com" in href:
                            # Clean the URL - remove tracking parameters
                            if "?" in href and any(param in href for param in ["/posts/", "/permalink/", "story_fbid="]):
                                # Keep the essential part of the URL
                                original_url = href.split("?")[0] if "/posts/" in href else href
                                break
                            elif any(path in href for path in ["/posts/", "/permalink/", "story_fbid=", "/photo.php", "/video.php"]):
                                original_url = href
                                break
            except Exception:
                pass

            # Tagged accounts (improved extraction for tagged people/pages)
            tagged_accounts = []
            try:
                # Enhanced selectors for tagged accounts
                tagged_selectors = [
                    'a[role="link"][href*="facebook.com"]',
                    'a[aria-label*="Tagged"]',
                    'a[href*="/profile.php?id="]',
                    'a[href*="/pages/"]',
                    'a[href*="/people/"]',
                    'a[data-testid*="tagged"]',
                    'span[data-testid*="tagged"] a',
                    'div[aria-label*="tagged"] a',
                    'a[href*="/groups/"][role="link"]',
                ]
                
                seen_profiles = set()  # Avoid duplicates
                
                for selector in tagged_selectors:
                    tag_elems = await element.query_selector_all(selector)
                    for tag_elem in tag_elems:
                        try:
                            name = await tag_elem.text_content()
                            profile_url = await tag_elem.get_attribute('href')
                            
                            if name and profile_url and "facebook.com" in profile_url:
                                name = self.utils.clean_text(name.strip())
                                
                                # Clean the profile URL
                                if "?" in profile_url and not "profile.php" in profile_url:
                                    profile_url = profile_url.split("?")[0]
                                
                                # Skip if we've already seen this profile
                                if profile_url in seen_profiles or len(name) < 2:
                                    continue
                                    
                                seen_profiles.add(profile_url)
                                
                                # Try to extract bio from aria-label or title
                                bio = ""
                                try:
                                    aria_label = await tag_elem.get_attribute('aria-label')
                                    title = await tag_elem.get_attribute('title')
                                    if aria_label and len(aria_label) > len(name):
                                        bio = aria_label.replace(name, "").strip()
                                    elif title and len(title) > len(name):
                                        bio = title.replace(name, "").strip()
                                except Exception:
                                    pass
                                
                                tagged_accounts.append({
                                    "name": name,
                                    "profile_url": profile_url,
                                    "bio": bio
                                })
                                
                        except Exception:
                            continue
            except Exception:
                pass

            # Location tagged (improved extraction for location info)
            location_tagged = ""
            try:
                location_selectors = [
                    'a[href*="/places/"]',
                    'a[href*="/maps/place/"]',
                    'span[aria-label*="Location"]',
                    'div[aria-label*="Location"]',
                    'a[aria-label*="location"]',
                    'div[data-testid*="location"]',
                    'span[data-testid*="location"]',
                    'a[href*="maps.google.com"]',
                    'a[href*="/checkin/"]',
                ]
                
                for selector in location_selectors:
                    loc_elem = await element.query_selector(selector)
                    if loc_elem:
                        loc_text = await loc_elem.text_content()
                        if loc_text and len(loc_text.strip()) > 2:
                            location_tagged = self.utils.clean_text(loc_text.strip())
                            break
                        
                        # Also try aria-label for location info
                        aria_label = await loc_elem.get_attribute('aria-label')
                        if aria_label and "location" in aria_label.lower():
                            location_tagged = self.utils.clean_text(aria_label.strip())
                            break
            except Exception:
                pass

            # Comments (improved extraction with better parsing)
            try:
                # Enhanced comment selectors
                comment_selectors = [
                    'div[role="article"] ul > li',
                    'div[data-testid*="comment"]',
                    'div[aria-label*="Comment"]',
                    'ul[role="list"] > li',
                    'div[data-testid="UFI2Comment/root"]',
                    'div[data-testid="comment_text"]',
                    'div[data-testid="UFI2CommentsList/root"] > div',
                    'div[aria-label*="commented"]',
                ]
                
                seen_comments = set()  # Avoid duplicates
                
                for selector in comment_selectors:
                    comment_elems = await element.query_selector_all(selector)
                    for comment_elem in comment_elems:
                        try:
                            # Extract commenter info with better selectors
                            commenter_name = ""
                            commenter_url = ""
                            commenter_bio = ""
                            
                            # Try multiple selectors for commenter
                            commenter_selectors = [
                                'a[role="link"][href*="facebook.com"]',
                                'span[dir="auto"] a',
                                'h3 a',
                                'strong a',
                            ]
                            
                            for comm_selector in commenter_selectors:
                                commenter_elem = await comment_elem.query_selector(comm_selector)
                                if commenter_elem:
                                    commenter_name = await commenter_elem.text_content()
                                    commenter_url = await commenter_elem.get_attribute('href')
                                    
                                    # Try to get bio from aria-label
                                    aria_label = await commenter_elem.get_attribute('aria-label')
                                    if aria_label and len(aria_label) > len(commenter_name or ""):
                                        commenter_bio = aria_label.replace(commenter_name or "", "").strip()
                                    
                                    if commenter_name:
                                        break
                            
                            # Extract comment text with better filtering
                            comment_text = ""
                            full_text = await comment_elem.text_content()
                            
                            if full_text:
                                # Clean comment text by removing commenter name and timestamps
                                lines = full_text.split('\n')
                                text_lines = []
                                
                                for line in lines:
                                    line = line.strip()
                                    # Skip lines that are just navigation text, timestamps, or names
                                    if (len(line) > 2 and 
                                        not self._is_comment_metadata(line) and
                                        line != commenter_name):
                                        text_lines.append(line)
                                
                                comment_text = ' '.join(text_lines).strip()
                            
                            # Extract timestamp with improved selectors
                            comment_timestamp = ""
                            timestamp_selectors = [
                                'time',
                                'a[aria-label*="ago"]',
                                'span[aria-label*="ago"]',
                                'a[href*="comment_id"]',
                            ]
                            
                            for ts_selector in timestamp_selectors:
                                timestamp_elem = await comment_elem.query_selector(ts_selector)
                                if timestamp_elem:
                                    datetime_attr = await timestamp_elem.get_attribute('datetime')
                                    if datetime_attr:
                                        comment_timestamp = datetime_attr
                                        break
                                    
                                    time_text = await timestamp_elem.text_content()
                                    if time_text and 'ago' in time_text.lower():
                                        comment_timestamp = self.utils.clean_text(time_text.strip())
                                        break
                            
                            # Only add if we have meaningful content and haven't seen it before
                            if (comment_text and len(comment_text) > 3 and 
                                comment_text not in seen_comments):
                                
                                seen_comments.add(comment_text)
                                
                                comments.append({
                                    "commenter": {
                                        "name": self.utils.clean_text(commenter_name.strip()) if commenter_name else "",
                                        "profile_url": commenter_url or "",
                                        "bio": commenter_bio
                                    },
                                    "comment_text": self.utils.clean_text(comment_text),
                                    "timestamp": comment_timestamp or ""
                                })
                                
                        except Exception:
                            continue
            except Exception:
                pass

            # Update comments count after extraction
            comments_count = len(comments) if comments else metrics.get("comments", 0)

            post_data = {
                "id": post_id,
                "timestamp": timestamp,
                "content": content,
                "caption": caption,
                "media_screenshot_url": media_screenshot_url,
                "original_url": original_url,
                "tagged_accounts": tagged_accounts,
                "location_tagged": location_tagged,
                "comments": comments,
                "reactions": reactions,
                "reactions_count": reactions.get("total", metrics.get("likes", 0)),
                "shares_count": shares_count,
                "comments_count": comments_count,
                "media_urls": [m["url"] for m in media if "url" in m],
                "shared": is_shared,
                "shared_content": shared_content,
                "type": post_type
            }
            
            logger.info(f"[DEBUG] Extracted post: ID={post_id}, content_len={len(content)}, "
                       f"timestamp={timestamp}, reactions={reactions.get('total', 0)}, "
                       f"comments={len(comments)}, tagged={len(tagged_accounts)}, "
                       f"location={location_tagged}, shared={is_shared}")
            return post_data
        except Exception as e:
            logger.warning(f"Error extracting single post: {e}")
            return None

    async def _extract_post_reactions(self, element) -> Dict[str, Any]:
        """Extract detailed reaction counts (likes, loves, etc.)"""
        reactions = {"total": 0, "like": 0, "love": 0, "haha": 0, "wow": 0, "sad": 0, "angry": 0}
        
        try:
            # Try to find reaction elements
            reaction_selectors = [
                'span[aria-label*="reactions"]',
                'div[aria-label*="reactions"]',
                'span[aria-label*="people reacted"]',
                'div[data-testid*="reaction"]',
                'a[aria-label*="See who reacted"]',
            ]
            
            for selector in reaction_selectors:
                reaction_elem = await element.query_selector(selector)
                if reaction_elem:
                    aria_label = await reaction_elem.get_attribute('aria-label')
                    text_content = await reaction_elem.text_content()
                    
                    # Parse reaction counts from aria-label or text
                    if aria_label:
                        reactions["total"] = self._parse_reaction_count(aria_label)
                        break
                    elif text_content and any(char.isdigit() for char in text_content):
                        reactions["total"] = self._parse_reaction_count(text_content)
                        break
            
            # Try to find specific reaction types
            reaction_icons = await element.query_selector_all('img[alt*="Like"], img[alt*="Love"], img[alt*="Haha"], img[alt*="Wow"], img[alt*="Sad"], img[alt*="Angry"]')
            for icon in reaction_icons:
                alt_text = await icon.get_attribute('alt')
                if alt_text:
                    reaction_type = alt_text.lower()
                    if reaction_type in reactions:
                        reactions[reaction_type] = 1  # At least one of this type exists
                        
        except Exception as e:
            logger.warning(f"Error extracting reactions: {e}")
            
        return reactions
    
    def _parse_reaction_count(self, text: str) -> int:
        """Parse reaction count from text"""
        try:
            # Look for numbers in the text
            numbers = re.findall(r'\d+(?:,\d+)*(?:\.\d+)?[KkMm]?', text)
            if numbers:
                count_str = numbers[0].replace(',', '')
                
                # Handle K/M suffixes
                if count_str.endswith(('K', 'k')):
                    return int(float(count_str[:-1]) * 1000)
                elif count_str.endswith(('M', 'm')):
                    return int(float(count_str[:-1]) * 1000000)
                else:
                    return int(float(count_str))
        except Exception:
            pass
        return 0

    async def _extract_post_content(self, element) -> str:
        try:
            # Enhanced "See more" button clicking with multiple selectors
            see_more_selectors = [
                'span:has-text("See more")',
                'a:has-text("See more")',
                'div:has-text("See more")',
                'span[role="button"]:has-text("See more")',
                'div[role="button"]:has-text("See more")',
                '[role="button"]:has-text("See more")',
                '[aria-label="See more"]',
                'span:has-text("Show more")',
                'div:has-text("Show more")',
                '[aria-expanded="false"]:has-text("more")',
            ]
            
            # Click all "See more" buttons found
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
            
            # Enhanced content extraction with better selectors
            content_selectors = [
                'div[data-ad-preview="message"]',
                'div[data-ad-comet-preview="message"]',
                '[data-testid="post_message"]',
                'div[data-testid="post_message_container"]',
                'span[data-testid="post_message"] span',
                'div[dir="auto"][role="main"]',
                'div[dir="auto"]:not([aria-hidden="true"])',
                'span[dir="auto"]:not([aria-hidden="true"])',
            ]
            
            for selector in content_selectors:
                try:
                    content_elem = await element.query_selector(selector)
                    if content_elem:
                        text = await content_elem.text_content()
                        if text and len(text.strip()) > 1:
                            cleaned_text = self.utils.clean_text(text.strip())
                            # Ensure we got meaningful content, not just metadata
                            if len(cleaned_text) > 10 and not self._is_unwanted_text(cleaned_text):
                                return cleaned_text
                except Exception:
                    continue
            
            # Fallback: extract all text and filter intelligently
            all_text = await element.text_content()
            if all_text:
                lines = all_text.split('\n')
                content_lines = []
                
                for line in lines:
                    line = line.strip()
                    # More intelligent filtering
                    if (len(line) > 1 and 
                        not self._is_unwanted_text(line) and
                        not self._is_comment_metadata(line)):
                        content_lines.append(line)
                
                if content_lines:
                    # Join the most relevant lines
                    content = '\n'.join(content_lines[:10])  # Take up to 10 meaningful lines
                    return self.utils.clean_text(content)
                
                # Last resort: log for debugging
                logger.info(f"[DEBUG] No content found by selectors, full text preview: {all_text[:500]}")
            
            return ""
        except Exception as e:
            logger.warning(f"Error extracting post content: {e}")
            return ""
    
    def _is_comment_metadata(self, text: str) -> bool:
        """Check if text is comment metadata (timestamps, actions, etc.)"""
        metadata_patterns = [
            "like", "reply", "react", "ago", "minutes", "hours", "days",
            "weeks", "months", "years", "edited", "translate", "see translation",
            "view", "show", "hide", "more replies", "view more comments",
            "see more", "see less", "report", "delete", "share"
        ]
        
        text_lower = text.lower().strip()
        return (any(pattern in text_lower for pattern in metadata_patterns) or 
                len(text) < 3 or
                text.isdigit() or
                re.match(r'^\d+[smhdwmy]$', text_lower))  # Match patterns like "5m", "2h", "1d"
    
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
        """Extract timestamp from post with improved selectors"""
        try:
            timestamp_selectors = [
                'time[datetime]',
                'a[href*="story_fbid"] time',
                'a[href*="posts"] time',
                'a[aria-label*="ago"]',
                'span[aria-label*="ago"]',
                '[data-testid="story-subtitle"] a',
                '[data-testid="story-subtitle"] time',
                'a[role="link"][tabindex="0"]:has(time)',
                'a[href*="permalink"]',
            ]
            
            for selector in timestamp_selectors:
                try:
                    time_elem = await element.query_selector(selector)
                    if time_elem:
                        # First try datetime attribute (most reliable)
                        datetime_attr = await time_elem.get_attribute('datetime')
                        if datetime_attr:
                            return datetime_attr
                        
                        # Try aria-label for relative time
                        aria_label = await time_elem.get_attribute('aria-label')
                        if aria_label and ('ago' in aria_label.lower() or 'at' in aria_label.lower()):
                            return self.utils.clean_text(aria_label.strip())
                        
                        # Try text content
                        time_text = await time_elem.text_content()
                        if time_text and ('ago' in time_text.lower() or 'at' in time_text.lower() or self._is_valid_timestamp(time_text)):
                            return self.utils.clean_text(time_text.strip())
                except Exception:
                    continue
            
            return ""
        except Exception as e:
            logger.warning(f"Error extracting timestamp: {e}")
            return ""
    
    def _is_valid_timestamp(self, text: str) -> bool:
        """Check if text looks like a valid timestamp"""
        timestamp_patterns = [
            r'\d+[smhdwmy]',  # 5m, 2h, 1d, etc.
            r'\d{1,2}:\d{2}',  # 14:32
            r'\d{4}-\d{2}-\d{2}',  # 2025-07-01
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)',  # Month names
            r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)',  # Day names
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in timestamp_patterns)
    
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