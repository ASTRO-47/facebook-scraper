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
            
            # Extract all posts from the main feed
            logger.info("🔍 Extracting all visible posts from the main feed...")
            extracted_posts = await self._extract_posts_with_scrolling("all_posts", max_posts)
            
            # Categorize posts
            for post in extracted_posts:
                if post.get("shared"):
                    all_posts["shared_posts"].append(post)
                # A post can be both tagged and own, so we check both
                if post.get("is_tagged"):
                    all_posts["tagged_posts"].append(post)
                # If not shared and not tagged, assume it's an own post
                if not post.get("shared") and not post.get("is_tagged"):
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
        try:
            # Detect if this is a shared post
            is_shared = False
            shared_content = ""
            original_poster = ""
            try:
                # A more reliable way to detect shared posts is to see if there's a nested article
                nested_article = await element.query_selector('div[role="article"] div[role="article"]')
                if nested_article:
                    is_shared = True
                    # The content of the outer article is the "share" message
                    # The content of the inner article is the original post
                    
                    # Extract original poster info
                    poster_element = await nested_article.query_selector('h3, a[role="link"]')
                    if poster_element:
                        original_poster = await poster_element.text_content()
                        original_poster = self.utils.clean_text(original_poster)

                    # Extract shared content from the nested article
                    shared_content_element = await nested_article.query_selector('[data-ad-preview="message"], [data-ad-comet-preview="message"], div[dir="auto"]')
                    if shared_content_element:
                        shared_content = await shared_content_element.text_content()
                        shared_content = self.utils.clean_text(shared_content)

            except Exception as e:
                logger.warning(f"[DEBUG] Error detecting shared post: {e}")

            # Detect if the user is tagged in the post
            is_tagged = False
            try:
                # Look for "is with" text or tags within the post header
                header_text = await element.text_content()
                if "is with" in header_text or "tagged" in header_text:
                    is_tagged = True
            except Exception:
                pass

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
            # try:
            #     if hasattr(self.utils, 'take_screenshot'):
            #         # Try to screenshot the main post content area
            #         screenshot_selector = 'div[data-ad-preview="message"]' or 'div[role="article"]'
            #         screenshot_path = await self.utils.take_screenshot(f"post_{post_id}", screenshot_selector)
            #         if screenshot_path:
            #             # Convert local path to URL path
            #             media_screenshot_url = screenshot_path.replace("static/", "/static/").replace("../static/", "/static/")
            # except Exception as e:
            #     logger.warning(f"Failed to take post screenshot: {e}")

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
                    link_elem = await element.query_selector(selector)
                    if link_elem:
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
                "timestamp": timestamp if timestamp else await self._extract_post_timestamp(element),
                "content": content if content else await self._extract_post_content(element),
                "caption": caption if caption else content,
                "media_screenshot_url": media_screenshot_url,
                "original_url": original_url,
                "tagged_accounts": tagged_accounts if tagged_accounts else [],
                "location_tagged": location_tagged if location_tagged else await self._extract_location_tagged(element),
                "comments": comments if comments else await self._extract_post_comments(element),
                "reactions": reactions if reactions else await self._extract_post_reactions(element),
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

    async def _perform_post_scrolling(self):
        """Performs a more human-like and robust scroll action"""
        try:
            scroll_height = await self.page.evaluate("document.body.scrollHeight")
            
            # Try different scroll methods
            scroll_options = [
                lambda: self.page.evaluate(f"window.scrollTo(0, {scroll_height});"),
                lambda: self.page.mouse.wheel(0, 1500),
                lambda: self.page.keyboard.press("PageDown"),
            ]
            
            # Choose a random scroll method
            import random
            scroll_method = random.choice(scroll_options)
            await scroll_method()
            
            logger.info("Scrolled down the page.")
            
            # Wait for new content to load
            await asyncio.sleep(random.uniform(3, 6))
            
        except Exception as e:
            logger.warning(f"Could not perform scroll: {e}")
            # Fallback to simple scroll
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            await asyncio.sleep(5)

    async def _extract_post_content(self, element) -> str:
        """Extracts the main text content of a post."""
        content = ""
        content_selectors = [
            'div[data-ad-preview="message"]',
            'div[data-ad-comet-preview="message"]',
            '[data-testid="post_message"]',
            'div[dir="auto"]'
        ]
        for selector in content_selectors:
            try:
                content_element = await element.query_selector(selector)
                if content_element:
                    text = await content_element.text_content()
                    if text:
                        content = self.utils.clean_text(text.strip())
                        if len(content) > 10: # Heuristic to avoid short, irrelevant text
                            logger.debug(f"Extracted content with selector: {selector}")
                            return content
            except Exception:
                continue
        logger.debug("Failed to extract post content with primary selectors.")
        return content

    async def _extract_post_timestamp(self, element) -> str:
        """Extracts the timestamp of a post."""
        timestamp = ""
        timestamp_selectors = [
            'a[href*="/posts/"] > span',
            'a[href*="/permalink/"] > span',
            'span[id] a[role="link"]',
            'a[aria-label*="ago"]',
            'a:has-text("ago")'
        ]
        for selector in timestamp_selectors:
            try:
                time_element = await element.query_selector(selector)
                if time_element:
                    text = await time_element.text_content()
                    timestamp = self.utils.clean_text(text.strip())
                    if timestamp:
                        logger.debug(f"Extracted timestamp with selector: {selector}")
                        return timestamp
            except Exception:
                continue
        logger.debug("Failed to extract post timestamp.")
        return ""

    async def _extract_post_metrics(self, element) -> Dict[str, int]:
        """Extracts comment and share counts."""
        metrics = {"comments": 0, "shares": 0}
        try:
            # Combined selector for all metrics
            metrics_text_element = await element.query_selector('div[role="toolbar"] + div > div')
            if metrics_text_element:
                metrics_text = await metrics_text_element.text_content()
                metrics_text = metrics_text.lower()

                # Extract comments
                comment_match = re.search(r'(\d+k?)\s+comment', metrics_text)
                if comment_match:
                    metrics["comments"] = self.utils.parse_count(comment_match.group(1))

                # Extract shares
                share_match = re.search(r'(\d+k?)\s+share', metrics_text)
                if share_match:
                    metrics["shares"] = self.utils.parse_count(share_match.group(1))
                
                logger.debug(f"Extracted metrics: {metrics}")
        except Exception as e:
            logger.debug(f"Could not extract post metrics: {e}")
        return metrics

    async def _extract_post_media(self, element) -> List[Dict[str, str]]:
        """Extracts media (images, videos) from post"""
        media_list = []
        try:
            # Images
            image_elements = await element.query_selector_all('img[alt]')
            for img in image_elements:
                src = await img.get_attribute('src')
                alt = await img.get_attribute('alt')
                if src and "emoji" not in src and "profile" not in src:
                    media_list.append({"type": "image", "url": src, "alt": alt})

            # Videos
            video_elements = await element.query_selector_all('video')
            for video in video_elements:
                src = await video.get_attribute('src')
                if src:
                    media_list.append({"type": "video", "url": src})
            
            logger.debug(f"Extracted {len(media_list)} media items.")
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
            reaction_button = await element.query_selector('span[role="button"] span[aria-label]')
            if reaction_button:
                aria_label = await reaction_button.get_attribute('aria-label')
                if aria_label:
                    # Example: "Like: 1.2K" or "Reactions: 1.2K"
                    total_match = re.search(r'(\d+\.?\d*k?)', aria_label)
                    if total_match:
                        reactions["total"] = self.utils.parse_count(total_match.group(1))
                    
                    # Try to get detailed reaction types by hovering
                    await reaction_button.hover()
                    await asyncio.sleep(0.5)
                    
                    tooltip = await self.page.query_selector('div[role="tooltip"]')
                    if tooltip:
                        reaction_types_text = await tooltip.text_content()
                        # Example: "1K Likes, 200 Loves, ..."
                        types = re.findall(r'(\d+k?)\s+(\w+)', reaction_types_text)
                        for count, type_name in types:
                            reactions["types"][type_name.lower()] = self.utils.parse_count(count)
            
            logger.debug(f"Extracted reactions: {reactions}")
        except Exception as e:
            logger.debug(f"Could not extract post reactions: {e}")
        return reactions

    async def _extract_post_comments(self, element) -> List[Dict[str, Any]]:
        """Extracts comments from a post."""
        comments = []
        try:
            # Click to show comments if not visible
            comment_button_selectors = [
                'div[role="button"]:has-text("Comment")',
                'div[role="button"]:has-text("View all comments")'
            ]
            for selector in comment_button_selectors:
                comment_button = await element.query_selector(selector)
                if comment_button:
                    await comment_button.click()
                    await asyncio.sleep(2) # Wait for comments to load
                    logger.info("Clicked to expand comments.")
                    break

            comment_elements = await element.query_selector_all('div[aria-label*="Comment by"]')
            for i, comment_elem in enumerate(comment_elements[:5]): # Limit to 5 comments for performance
                try:
                    author_elem = await comment_elem.query_selector('a[role="link"]')
                    content_elem = await comment_elem.query_selector('div[dir="auto"]')
                    
                    if author_elem and content_elem:
                        author = await author_elem.text_content()
                        content = await content_elem.text_content()
                        comments.append({
                            "author": self.utils.clean_text(author),
                            "content": self.utils.clean_text(content)
                        })
                except Exception as e:
                    logger.debug(f"Could not extract comment {i+1}: {e}")
            
            logger.debug(f"Extracted {len(comments)} comments.")
        except Exception as e:
            logger.debug(f"Could not extract post comments: {e}")
        return comments

    async def _extract_location_tagged(self, element) -> str:
        """Extracts the tagged location from a post."""
        location = ""
        try:
            # Look for a link with a location icon or "at" text
            location_link = await element.query_selector('a[href*="/places/"]')
            if location_link:
                location = await location_link.text_content()
                location = self.utils.clean_text(location)
                logger.debug(f"Extracted location: {location}")
        except Exception as e:
            logger.debug(f"Could not extract tagged location: {e}")
        return location