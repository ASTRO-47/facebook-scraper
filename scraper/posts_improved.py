"""
Improved Facebook Posts Scraper - Enhanced to match target JSON structure
"""
import asyncio
import re
import time
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
import logging

from .utils import ScraperUtils

# Configure logging - REDUCED for cleaner output
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class PostsScraperImproved:
    """
    Enhanced Facebook Posts Scraper that extracts detailed post information
    matching the target JSON structure with full user profiles, locations, etc.
    """
    
    def __init__(self, page: Page, utils: ScraperUtils):
        """Initialize the PostsScraper with page and utilities"""
        self.page = page
        self.utils = utils
        
        # Configuration
        self.max_retries = 3
        self.default_timeout = 30000
        self.max_posts_per_section = 50
    
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
    
    async def _check_page_health(self) -> bool:
        """Check if the page is still responsive and not crashed"""
        try:
            # Try a simple evaluation to check if page is responsive
            await self.page.evaluate("document.title")
            return True
        except Exception as e:
            logger.warning(f"Page health check failed: {e}")
            return False
    
    async def _recover_from_crash(self) -> bool:
        """Attempt to recover from page crash by creating a new page"""
        try:
            logger.info("🔄 Attempting to recover from page crash...")
            
            # Check if we have access to the browser context
            if hasattr(self.page, 'context') and self.page.context:
                # Create a new page in the same context
                new_page = await self.page.context.new_page()
                
                # Copy cookies from the old page if possible
                try:
                    cookies = await self.page.context.cookies()
                    if cookies:
                        await new_page.context.add_cookies(cookies)
                        logger.info(f"✅ Transferred {len(cookies)} cookies to new page")
                except Exception as e:
                    logger.warning(f"Could not transfer cookies: {e}")
                
                # Replace the old page with the new one
                old_page = self.page
                self.page = new_page
                self.utils.page = new_page  # Update utils reference
                
                # Close the old crashed page
                try:
                    await old_page.close()
                except Exception as e:
                    logger.warning(f"Could not close old page: {e}")
                
                logger.info("✅ Successfully recovered from page crash")
                return True
            else:
                logger.error("❌ Cannot recover - no browser context available")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to recover from crash: {e}")
            return False

    async def get_all_post_types(self, username: str, max_posts: int = 200) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract ALL posts chronologically (newest to oldest) with enhanced detail matching target JSON structure
        """
        all_posts = {
            "own_posts": [],
            "tagged_posts": [],
            "comments_by_user": []
        }
        
        try:
            logger.info(f"🚀 Starting COMPLETE chronological post extraction for {username}")
            logger.info(f"📊 Target: Extract ALL posts from newest to oldest (max {max_posts})")
            
            # Check page health before starting
            if not await self._check_page_health():
                logger.warning("Page appears crashed, attempting recovery...")
                if not await self._recover_from_crash():
                    logger.error("❌ Could not recover from page crash")
                    return all_posts
            
            # Navigate to the main profile page
            profile_url = self._construct_profile_url(username)
            if not await self._navigate_with_retries(profile_url):
                logger.error(f"❌ Failed to navigate to profile {profile_url}")
                return all_posts
            
            await self._wait_for_posts_to_load()
            
            # Save the initial HTML for debugging
            clean_username = self._detect_profile_type(username)[1]
            await self.utils.save_page_html(f"{clean_username}_posts_page_debug.html")

            # Extract ALL posts chronologically with enhanced details
            logger.info("🔍 Extracting ALL posts chronologically (newest to oldest)...")
            extracted_posts = await self._extract_all_posts_chronologically(max_posts)
            
            # Categorize posts with enhanced structure
            for post in extracted_posts:
                if post.get("is_tagged_post"):
                    all_posts["tagged_posts"].append(self._format_tagged_post(post))
                else:
                    all_posts["own_posts"].append(self._format_own_post(post))
            
            # Extract comments by user on other posts
            logger.info("💬 Extracting user comments on other posts...")
            all_posts["comments_by_user"] = await self._extract_user_comments_on_other_posts(username, max_posts // 4)
            
            logger.info(f"📊 Enhanced extraction complete:")
            logger.info(f"   - Own posts: {len(all_posts['own_posts'])}")
            logger.info(f"   - Tagged posts: {len(all_posts['tagged_posts'])}")
            logger.info(f"   - Comments by user: {len(all_posts['comments_by_user'])}")
            
            return all_posts
            
        except Exception as e:
            logger.error(f"❌ Error in enhanced post extraction: {e}", exc_info=True)
            return all_posts

    async def _extract_all_posts_chronologically(self, max_posts: int) -> List[Dict[str, Any]]:
        """Extract ALL posts from the timeline in chronological order (newest to oldest)"""
        all_posts = []
        seen_post_ids = set()
        last_height = 0
        no_new_content_rounds = 0
        max_no_new_rounds = 8
        start_time = time.time()
        max_time = 900  # 15 minutes max for complete extraction
        
        logger.info(f"🔄 Starting complete chronological extraction (max {max_posts} posts)")
        
        while len(all_posts) < max_posts and no_new_content_rounds < max_no_new_rounds:
            # Check timeout
            if time.time() - start_time > max_time:
                logger.warning(f"⏰ Time limit reached. Extracted {len(all_posts)} posts.")
                break
            
            try:
                # Get current page height
                current_height = await self.page.evaluate("document.body.scrollHeight")
                
                # Extract current batch of posts
                current_posts = await self._extract_current_posts_with_enhanced_content()
                
                # Add new unique posts
                new_posts_added = 0
                for post in current_posts:
                    post_id = post.get("id")
                    if post_id and post_id not in seen_post_ids:
                        seen_post_ids.add(post_id)
                        all_posts.append(post)
                        new_posts_added += 1
                        
                        # Log progress every 10 posts
                        if len(all_posts) % 10 == 0:
                            logger.info(f"📝 Extracted {len(all_posts)} posts so far...")
                
                logger.info(f"🔄 Round {len(all_posts)//5 + 1}: +{new_posts_added} new posts (total: {len(all_posts)})")
                
                # Check if we're getting new content
                if new_posts_added == 0:
                    no_new_content_rounds += 1
                    logger.info(f"⏳ No new posts found ({no_new_content_rounds}/{max_no_new_rounds})")
                else:
                    no_new_content_rounds = 0
                
                # Check if we reached target
                if len(all_posts) >= max_posts:
                    logger.info(f"🎯 Target reached: {len(all_posts)} posts extracted!")
                    break
                
                # Smart scrolling - scroll to load more content
                await self._smart_scroll_for_more_posts()
                
                # Wait for new content to load
                await asyncio.sleep(2)
                
                # Check if page height changed (indicates new content)
                new_height = await self.page.evaluate("document.body.scrollHeight")
                if new_height == current_height and new_posts_added == 0:
                    no_new_content_rounds += 1
                
                last_height = new_height
                
            except Exception as e:
                logger.error(f"⚠️ Error during extraction round: {e}")
                # Try to continue after errors
                await asyncio.sleep(3)
                continue
        
        logger.info(f"✅ Chronological extraction complete: {len(all_posts)} posts")
        return all_posts

    async def _extract_current_posts_with_enhanced_content(self) -> List[Dict[str, Any]]:
        """Extract current visible posts with enhanced content extraction"""
        posts_batch = []
        
        try:
            # Use UPDATED 2024 Facebook selectors based on real DOM analysis
            post_selectors = [
                # Primary selectors from actual Facebook 2024 DOM structure
                'div.x1rg5ohu.x1iyjqo2.x6ikm8r.x10wlt62.xv54qhq',  # Main post containers
                'div.xqcrz7y.x1c9tyrk.xeusxvb.x1pahc9y.x1ertn4p.x1lliihq.xbelrpt.xr9ek0c.x1n2onr6',  # Comment containers
                'div.x1r8uery.x1iyjqo2.x6ikm8r.x10wlt62.xv54qhq',  # Alternative post containers
                'div.x6s0dn4.x3nfvp2',  # Action containers with content
                
                # Secondary selectors (more specific)
                'div[role="article"]',                    # Post articles
                'div[data-pagelet*="FeedUnit"]',         # Feed units  
                'div[data-testid*="post"]',              # Test ID posts
                'div[aria-posinset]',                    # Positioned posts
                
                # Tertiary selectors (backup)
                '[data-testid="story-root-element"]',    # Story elements
                'div[data-testid="story-subtitle"]',     # Story subtitles
                'div[class*="userContentWrapper"]',      # User content wrappers
                
                # Final fallback selectors
                'div[data-ft]',                          # Facebook tracking elements
                'div[id*="mall_post"]',                  # Mall posts
                'div[id*="photos_timeline"]',            # Timeline photos
            ]
            
            post_elements = []
            best_selector = None
            max_elements = 0
            
            # Test each selector and use the one that finds the most elements
            for selector in post_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements and len(elements) > max_elements:
                        max_elements = len(elements)
                        post_elements = elements
                        best_selector = selector
                        logger.debug(f"✅ Selector '{selector}' found {len(elements)} elements")
                except Exception as e:
                    logger.debug(f"❌ Selector '{selector}' failed: {e}")
                    continue
            
            print(f"🎯 Using best selector: '{best_selector}' with {max_elements} elements")
            logger.info(f"🔍 Processing {len(post_elements)} potential post elements")
            
            print(f"🔧 DEBUG: Found {len(post_elements)} post elements to analyze")

            for i, element in enumerate(post_elements):
                try:
                    # DEBUG: Log what we're processing
                    element_info = await element.inner_text()
                    print(f"🔍 Post {i+1}: Processing element with text length {len(element_info)} characters")
                    
                    # Extract comprehensive post data
                    post_data = await self._extract_comprehensive_post_data(element)
                    
                    # DEBUG: Show what we extracted
                    print(f"📊 Post {i+1} extracted data:")
                    print(f"   - ID: {post_data.get('id', 'None')}")
                    print(f"   - Content: {post_data.get('content', 'None')[:50]}...")
                    print(f"   - Timestamp: {post_data.get('timestamp', 'None')}")
                    print(f"   - Tagged accounts: {len(post_data.get('tagged_accounts', []))}")
                    
                    # Validation with enhanced logging
                    if self._is_valid_comprehensive_post(post_data):
                        posts_batch.append(post_data)
                        print(f"✅ Post {i+1} ACCEPTED - Content: {post_data.get('content', 'No content')[:40]}...")
                    else:
                        print(f"❌ Post {i+1} REJECTED - Failed validation")
                    
                except Exception as e:
                    print(f"❌ Failed to extract post {i+1}: {e}")
                    continue

            logger.info(f"📊 Successfully extracted {len(posts_batch)} valid posts from this batch")
            return posts_batch
            
        except Exception as e:
            logger.error(f"❌ Error extracting current posts: {e}")
            return []

    async def _smart_scroll_for_more_posts(self):
        """Intelligent scrolling to load more posts"""
        try:
            # Scroll down in steps to trigger loading
            for _ in range(3):
                await self.page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
                await asyncio.sleep(0.5)
            
            # Scroll to bottom to trigger infinite scroll
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
            
            # Small scroll up and down to trigger loading
            await self.page.evaluate("window.scrollBy(0, -100)")
            await asyncio.sleep(0.5)
            await self.page.evaluate("window.scrollBy(0, 200)")
            
        except Exception as e:
            logger.warning(f"⚠️ Error during smart scrolling: {e}")

    async def _extract_comprehensive_post_data(self, element) -> Dict[str, Any]:
        """Extract comprehensive post data with improved content detection"""
        post_data = {
            "id": await self._generate_enhanced_post_id(element),
            "timestamp": await self._extract_enhanced_timestamp(element),
            "content": await self._extract_enhanced_post_content(element),
            "caption": "",
            "media_screenshot_url": "",
            "original_url": await self._extract_enhanced_post_url(element),
            "shared": False,
            "shared_content": "",
            "original_poster": "",
            "is_tagged": await self._detect_if_tagged_post(element),
            "tagged_accounts": await self._extract_enhanced_tagged_accounts(element),
            "location_tagged": await self._extract_location_from_post(element),
            "comments": await self._extract_post_comments(element),
            "reactions": await self._extract_reactions_enhanced(element),
            "comments_count": await self._extract_comments_count(element),
            "shares_count": await self._extract_shares_count(element),
            "media": await self._extract_media_info(element)
        }
        
        # Set caption same as content if not empty
        if post_data["content"]:
            post_data["caption"] = post_data["content"]
            
        return post_data

    def _is_valid_comprehensive_post(self, post_data: Dict[str, Any]) -> bool:
        """STRICT validation for comprehensive posts - only accept posts with meaningful content"""
        # Must have an ID
        if not post_data.get("id"):
            return False
        
        # Get the content and clean it
        content = post_data.get("content", "").strip()
        timestamp = post_data.get("timestamp", "").strip()
        tagged_accounts = post_data.get("tagged_accounts", [])
        
        # Primary validation: Must have actual content
        if content and len(content) > 15:
            # Make sure it's not just UI noise
            if self._is_actual_post_content(content):
                return True
        
        # Secondary validation: Tagged posts with meaningful data
        if tagged_accounts and len(tagged_accounts) > 0:
            # Must also have either content or timestamp
            if content or timestamp:
                return True
        
        # Tertiary validation: Posts with good timestamps and some indicators
        if timestamp and len(timestamp) > 5:
            # Must have some other data (URL, tags, etc)
            if (post_data.get("original_url") or 
                tagged_accounts or 
                post_data.get("location_tagged") or
                post_data.get("media")):
                return True
        
        # Reject posts with no meaningful content
        return False

    async def _extract_posts_with_enhanced_details(self, post_type: str, max_posts: int) -> List[Dict[str, Any]]:
        """Extract posts with enhanced details including user profiles, locations, etc."""
        posts = []
        last_count = 0
        stable_rounds = 0
        max_stable_rounds = 5
        max_scrolls = min(20, max_posts // 3 + 5)
        start_time = time.time()
        max_time = 300  # 5 minutes max
        
        logger.info(f"Starting enhanced posts extraction (max {max_scrolls} scrolls)")
        
        post_container_selector = 'div[role="main"]'

        for scroll_attempt in range(max_scrolls):
            # Check timeout
            if time.time() - start_time > max_time:
                logger.warning(f"Timeout reached. Returning {len(posts)} posts found so far.")
                break
                
            try:
                # Extract current batch with enhanced details
                current_batch = await self._extract_current_posts_with_details(post_container_selector)
                
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
                
                # Check for stability
                if current_count == last_count:
                    stable_rounds += 1
                    if stable_rounds >= max_stable_rounds:
                        logger.info(f"No new posts found for {max_stable_rounds} rounds, stopping")
                        break
                else:
                    stable_rounds = 0
                
                last_count = current_count
                
                # Perform scrolling
                await self._perform_post_scrolling()
                
            except Exception as e:
                logger.warning(f"Error during scroll {scroll_attempt + 1}: {e}")
                continue
        
        return posts

    async def _extract_current_posts_with_details(self, container_selector: str) -> List[Dict[str, Any]]:
        """Extract current batch of posts with enhanced details using updated selectors"""
        posts_batch = []
        try:
            # Try multiple selectors to find posts - Facebook structure varies
            post_selectors = [
                'div[role="article"]',  # Standard post articles
                'div[aria-posinset]',  # Individual posts
                'div[data-testid*="post"]',  # Posts with testid
                '[role="main"] > div > div > div',  # General content divs
                'div[data-pagelet*="FeedUnit"]'  # Feed units
            ]
            
            post_elements = []
            for selector in post_selectors:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    logger.info(f"[ENHANCED] Found {len(elements)} potential posts with selector: {selector}")
                    post_elements = elements
                    break
            
            if not post_elements:
                # Fallback: get all divs in main content and filter
                logger.warning("No standard post elements found, trying fallback approach...")
                all_divs = await self.page.query_selector_all('[role="main"] div')
                
                # Filter divs that might contain posts (have substantial text content)
                for div in all_divs[:50]:  # Limit to first 50 to avoid processing too many
                    try:
                        text_content = await div.text_content()
                        if text_content and len(text_content.strip()) > 20:  # Has meaningful content
                            post_elements.append(div)
                    except:
                        continue
                
                logger.info(f"[FALLBACK] Found {len(post_elements)} potential content divs")

            logger.info(f"[ENHANCED] Processing {len(post_elements)} potential post elements.")

            for i, element in enumerate(post_elements):
                try:
                    post_data = await self._extract_single_post_enhanced(element)
                    if post_data and post_data.get("id"):
                        if not any(p.get("id") == post_data.get("id") for p in posts_batch):
                            posts_batch.append(post_data)
                            logger.info(f"Successfully extracted enhanced post {i+1}")
                        else:
                            logger.debug(f"Post {i+1} was a duplicate")
                    else:
                        logger.debug(f"Post {i+1} was empty or filtered out")
                except Exception as e:
                    logger.warning(f"Error processing enhanced post element {i+1}: {e}")

        except Exception as e:
            logger.warning(f"Error in _extract_current_posts_with_details: {e}")
            
        logger.info(f"Total enhanced posts extracted in this batch: {len(posts_batch)}")
        return posts_batch

    async def _extract_single_post_enhanced(self, element) -> Optional[Dict[str, Any]]:
        """Extract a single post with enhanced details matching target JSON structure"""
        try:
            # Generate unique ID
            timestamp = await self._extract_post_timestamp_enhanced(element)
            content = await self._extract_post_content_enhanced(element)
            post_id = self._generate_post_id(content, timestamp)
            
            logger.info(f"Processing enhanced post with ID: {post_id}")

            # Enhanced post data extraction
            post_data = {
                "id": post_id,
                "timestamp": timestamp,
                "content": content,
                "caption": content,  # In Facebook, content often serves as caption
                "media_screenshot_url": "",  # Can be implemented if needed
                "original_url": await self._extract_post_url_enhanced(element),
                "tagged_accounts": await self._extract_tagged_accounts(element),
                "location_tagged": await self._extract_location_tagged(element),
                "comments": await self._extract_comments_enhanced(element),
                "is_tagged_post": await self._detect_if_tagged_post(element),
                "reactions": await self._extract_post_reactions_enhanced(element),
                "shares_count": await self._extract_shares_count(element)
            }
            
            logger.info(f"Successfully extracted enhanced post data for ID: {post_id}")
            return post_data

        except Exception as e:
            logger.error(f"❌ Error in enhanced post extraction: {e}")
            return None

    async def _extract_post_timestamp_enhanced(self, element) -> str:
        """Enhanced timestamp extraction"""
        try:
            timestamp_selectors = [
                'a[role="link"] span[title]',  # Hover titles often have full timestamps
                'a[aria-label*="hour"], a[aria-label*="minute"], a[aria-label*="day"]',
                'a[href*="permalink"] span',
                'time',
                'span[data-testid="timestamp"]'
            ]
            
            for selector in timestamp_selectors:
                elements = await element.query_selector_all(selector)
                for el in elements:
                    try:
                        # Check title attribute first
                        title = await el.get_attribute('title')
                        if title:
                            return title.strip()
                            
                        # Check aria-label
                        aria_label = await el.get_attribute('aria-label')
                        if aria_label and any(word in aria_label.lower() for word in ['ago', 'at', 'on']):
                            return aria_label.strip()
                            
                        # Check text content
                        text = await el.text_content()
                        if text and text.strip():
                            return text.strip()
                    except:
                        continue
                        
            return ""
        except Exception as e:
            logger.debug(f"Error extracting enhanced timestamp: {e}")
            return ""

    async def _extract_post_content_enhanced(self, element) -> str:
        """Enhanced content extraction with better text cleaning and language support"""
        try:
            # Enhanced content selectors that work with current Facebook structure
            content_selectors = [
                # Standard post content
                'div[data-ad-comet-preview="message"]',
                'div[data-ad-preview="message"]',
                'div[data-testid="post_message"]',
                'div[class*="userContent"]',
                # Text containers with dir attribute (handles RTL languages)
                'div[dir="auto"]:not([role="button"]):not([aria-hidden="true"])',
                'div[dir="ltr"]:not([role="button"]):not([aria-hidden="true"])',
                'div[dir="rtl"]:not([role="button"]):not([aria-hidden="true"])',
                # Span elements with text
                'span[dir="auto"]',
                # General text containers
                'div:not([role="button"]):not([aria-hidden="true"])',
            ]
            
            # Try each selector and collect text
            content_parts = []
            for selector in content_selectors:
                try:
                    content_elements = await element.query_selector_all(selector)
                    for content_elem in content_elements[:5]:  # Limit to prevent too much data
                        text = await content_elem.text_content()
                        if text and len(text.strip()) > 10:  # Only meaningful text
                            cleaned_text = self.utils.clean_text(text)
                            # Filter out UI elements and navigation
                            if self._is_valid_post_content(cleaned_text):
                                if cleaned_text not in content_parts:
                                    content_parts.append(cleaned_text)
                except:
                    continue
            
            # If we got multiple parts, find the best post content
            if content_parts:
                # Sort by length and filter further
                content_parts = sorted([c for c in content_parts if len(c) > 20], key=len, reverse=True)
                
                for content in content_parts:
                    # Skip if it contains too many UI indicators
                    ui_indicators = ['Like', 'Comment', 'Share', 'Reply', 'hours', 'days', 'minutes', 'ago']
                    ui_count = sum(1 for indicator in ui_indicators if indicator in content)
                    
                    # If less than 30% UI indicators, it's likely real content
                    if len(content.split()) > 0 and ui_count / len(content.split()) < 0.3 and len(content) > 30:
                        return content[:500]  # Return substantial content
                
                # Fallback: return the longest content, cleaned of UI elements
                if content_parts:
                    content = content_parts[0]
                    # Clean common UI elements from the content
                    ui_patterns = ['Like', 'Comment', 'Share', 'Reply', 'hours ago', 'days ago', 'minutes ago']
                    for pattern in ui_patterns:
                        content = content.replace(pattern, '').strip()
                    return content[:500] if len(content) > 20 else ""
            
            return ""
            
        except Exception as e:
            logger.debug(f"Error extracting enhanced content: {e}")
            return ""

    async def _extract_enhanced_post_content(self, element) -> str:
        """ULTRA-ENHANCED content extraction - finds actual post text with aggressive filtering"""
        try:
            # Method 1: Target Facebook 2024 post content structure - most specific first
            post_content_candidates = []
            
            # Strategy A: Look for the main post text container (updated with real Facebook 2024 selectors)
            main_content_selectors = [
                # Real Facebook 2024 selectors based on actual DOM structure
                'span.x193iq5w.xeuugli.x13faqbe.x1vvkbs.x1xmvt09.x1lliihq.x1s928wv.xhkezso.x1gmr53x.x1cpjm7i.x1fgarty.x1943h6x.xudqn12.x3x7a5m.x6prxxf.xvq8zen.xo1l8bm.xzsf02u[dir="auto"]',
                'div.xdj266r.x14z9mp.xat24cr.x1lziwak.xvv2xg div[dir="auto"][style*="text-align:start"]',
                'div[dir="auto"][style*="text-align:start"]',
                'span.x193iq5w.xeuugli.x13faqbe.x1vvkbs[dir="auto"]',
                'div.x1lliihq.xjkvuk6.x1iorvi4 span[dir="auto"]',
                
                # Fallback selectors - broader patterns
                'div[data-ad-preview="message"]',  # Sponsored post content
                'div[data-testid="post_message"]',  # Direct post message
                'div[class*="userContent"]',       # User content wrapper
                'span[class*="userContent"]',      # User content text
                'div[dir="auto"] span',            # Auto-direction spans in divs
                'span[dir="auto"]',                # Auto-direction spans
                'div[role="button"] + div span',   # Content after action buttons
            ]
            
            for selector in main_content_selectors:
                try:
                    elements = await element.query_selector_all(selector)
                    for el in elements:
                        text = await el.text_content()
                        if text and len(text.strip()) > 15:
                            cleaned = self._clean_facebook_content(text.strip())
                            if len(cleaned) > 15 and self._is_actual_post_content(cleaned):
                                post_content_candidates.append((cleaned, self._score_content_quality(cleaned)))
                except:
                    continue
            
            # Strategy B: Look for largest meaningful text blocks in the post
            try:
                all_spans = await element.query_selector_all('span')
                for span in all_spans:
                    text = await span.text_content()
                    if text and len(text.strip()) > 20:
                        cleaned = self._clean_facebook_content(text.strip())
                        if len(cleaned) > 20 and self._is_actual_post_content(cleaned):
                            post_content_candidates.append((cleaned, self._score_content_quality(cleaned)))
            except:
                pass
            
            # Strategy C: Extract and analyze all text, then find the best content
            try:
                full_element_text = await element.text_content()
                if full_element_text:
                    # Split into lines and analyze each
                    lines = [line.strip() for line in full_element_text.split('\n') if line.strip()]
                    for line in lines:
                        if (len(line) > 25 and 
                            self._is_actual_post_content(line) and
                            not self._is_ui_text(line)):
                            cleaned = self._clean_facebook_content(line)
                            if len(cleaned) > 20:
                                post_content_candidates.append((cleaned, self._score_content_quality(cleaned)))
            except:
                pass
            
            # Find the best content from all candidates
            if post_content_candidates:
                # Sort by score (highest first)
                post_content_candidates.sort(key=lambda x: x[1], reverse=True)
                best_content = post_content_candidates[0][0]
                
                # Additional cleaning and validation
                final_content = self._final_content_cleanup(best_content)
                if len(final_content) > 15:
                    return final_content[:400]  # Reasonable length limit
            
            # Fallback: Look for hashtags if no content found
            try:
                import re
                full_text = await element.text_content()
                if full_text:
                    hashtags = re.findall(r'#\w+', full_text)
                    if hashtags:
                        return ' '.join(hashtags[:5])  # Max 5 hashtags
            except:
                pass
            
            return ""
            
        except Exception as e:
            logger.debug(f"Content extraction error: {e}")
            return ""

    def _is_actual_post_content(self, text: str) -> bool:
        """Enhanced check if text is actual post content (not UI noise)"""
        if not text or len(text.strip()) < 10:
            return False
        
        text_lower = text.lower().strip()
        
        # Immediate disqualifiers (UI elements)
        ui_noise = [
            'like', 'comment', 'share', 'reply', 'follow', 'message',
            'see more', 'see less', 'show more', 'show less',
            'ago', 'hours', 'minutes', 'yesterday', 'just now',
            'mobile uploads', 'shared with', 'tagged', 'photo',
            'add friend', 'send message', 'view profile',
            'home', 'watch', 'marketplace', 'groups', 'gaming',
            'what\'s on your mind', 'write a comment', 'add a comment'
        ]
        
        # Don't accept text that's purely UI
        if any(ui in text_lower for ui in ui_noise) and len(text) < 50:
            return False
        
        # Must have sentence structure or meaningful content
        has_sentence_structure = ('.' in text or '!' in text or '?' in text or 
                                ',' in text or ':' in text)
        has_hashtags = '#' in text
        has_meaningful_length = len(text) > 15
        
        # Good indicators of actual content
        content_indicators = ['happy', 'birthday', 'love', 'great', 'awesome', 
                            'thanks', 'congratulations', 'beautiful', 'amazing']
        has_content_words = any(word in text_lower for word in content_indicators)
        
        return (has_sentence_structure or has_hashtags or has_content_words) and has_meaningful_length

    def _score_content_quality(self, text: str) -> float:
        """Score content quality to identify real post content vs UI noise"""
        if not text or len(text) < 10:
            return 0.0
        
        score = 0.0
        
        # Length bonus (but not too long)
        if 20 <= len(text) <= 200:
            score += 0.3
        elif len(text) > 200:
            score += 0.1
        
        # Content indicators
        if '.' in text or '!' in text or '?' in text:
            score += 0.3
        if '#' in text:  # Hashtags are good content
            score += 0.2
        if any(word in text.lower() for word in ['happy', 'birthday', 'love', 'great', 'awesome', 'thanks']):
            score += 0.2
        
        # Penalties for UI text
        if 'facebook' in text.lower() and text.lower().count('facebook') > 3:
            score -= 0.8  # Heavy penalty for repetitive Facebook
        if any(ui in text.lower() for ui in ['like', 'comment', 'share', 'see more', 'mobile uploads']):
            score -= 0.3
        if len(text.split()) < 3:  # Too short
            score -= 0.2
        if text.isupper() and len(text) > 10:  # All caps likely UI
            score -= 0.4
        if any(char.isdigit() for char in text) and len([c for c in text if c.isdigit()]) > len(text) * 0.3:
            score -= 0.3  # Too many numbers
        
        return max(0.0, score)

    def _final_content_cleanup(self, text: str) -> str:
        """Final cleanup of extracted content"""
        if not text:
            return ""
        
        import re
        
        # Remove common Facebook artifacts
        text = re.sub(r'\bFacebook\b{2,}', 'Facebook', text, flags=re.IGNORECASE)
        text = re.sub(r'(\bFacebook\b\s*){3,}', '', text, flags=re.IGNORECASE)
        
        # Remove UI fragments that might have slipped through
        ui_fragments = [
            r'\bLike\b|\bComment\b|\bShare\b',
            r'\b\d+\s*likes?\b',
            r'\b\d+\s*comments?\b',  
            r'\b\d+\s*shares?\b',
            r'\bmobile uploads\b',
            r'\bsee more\b|\bsee less\b',
            r'\bhours ago\b|\bminutes ago\b|\bdays ago\b'
        ]
        
        for pattern in ui_fragments:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Remove very short words and fragments
        words = text.split()
        cleaned_words = []
        for word in words:
            if len(word) > 2 or word.lower() in ['i', 'a', 'is', 'to', 'in', 'on', 'at']:
                cleaned_words.append(word)
        
        result = ' '.join(cleaned_words).strip()
        return result if len(result) > 10 else ""
        """Score content quality to identify real post content vs UI noise"""
        if not text or len(text) < 10:
            return 0.0
        
        score = 0.0
        
        # Length bonus (but not too long)
        if 20 <= len(text) <= 200:
            score += 0.3
        elif len(text) > 200:
            score += 0.1
        
        # Content indicators
        if '.' in text or '!' in text or '?' in text:
            score += 0.3
        if '#' in text:  # Hashtags are good content
            score += 0.2
        if any(word in text.lower() for word in ['happy', 'birthday', 'love', 'great', 'awesome', 'thanks']):
            score += 0.2
        
        # Penalties for UI text
        if 'facebook' in text.lower() and text.lower().count('facebook') > 3:
            score -= 0.8  # Heavy penalty for repetitive Facebook
        if any(ui in text.lower() for ui in ['like', 'comment', 'share', 'see more', 'mobile uploads']):
            score -= 0.3
        if len(text.split()) < 3:  # Too short
            score -= 0.2
        if text.isupper() and len(text) > 10:  # All caps likely UI
            score -= 0.4
        if any(char.isdigit() for char in text) and len([c for c in text if c.isdigit()]) > len(text) * 0.3:
            score -= 0.3  # Too many numbers
        
        return max(0.0, score)

    def _is_ui_text(self, text: str) -> bool:
        """Check if text is UI element rather than content"""
        ui_indicators = [
            'like', 'comment', 'share', 'reply', 'follow', 'message',
            'see more', 'show more', 'mobile uploads', 'shared with',
            'minutes ago', 'hours ago', 'days ago'
        ]
        
        text_lower = text.lower().strip()
        return any(ui in text_lower for ui in ui_indicators)

    def _is_content_line(self, text: str) -> bool:
        """Simple check if a line contains actual content (not UI)"""
        if not text or len(text) < 8:
            return False
        
        # Common UI elements to exclude
        ui_elements = [
            'Like', 'Comment', 'Share', 'Reply', 'Follow', 'Message',
            'ago', 'just now', 'yesterday', 'See more', 'Show more',
            'Home', 'Watch', 'Marketplace', 'Groups', 'Gaming',
            'What\'s on your mind?', 'Write a comment...',
            'Add a comment...', 'Sponsored', 'Suggested for you'
        ]
        
        # Exact matches (case insensitive)
        text_lower = text.lower().strip()
        if any(ui.lower() == text_lower for ui in ui_elements):
            return False
        
        # Partial matches for obvious UI
        ui_partials = ['hours ago', 'minutes ago', 'days ago', 'weeks ago', 'months ago', 'years ago']
        if any(ui in text_lower for ui in ui_partials):
            return False
        
        # Must have some substantial content
        if len(text) < 15:
            return False
            
        # Should not be ALL caps (likely UI)
        if text.isupper() and len(text) > 5:
            return False
        
        return True

    def _clean_facebook_content(self, text: str) -> str:
        """Clean Facebook-specific noise from content - IMPROVED VERSION"""
        if not text:
            return ""
        
        import re
        
        # Remove repetitive "Facebook" text (major issue in your results)
        # Fix the regex pattern - the issue was with {2,} on word boundaries
        text = re.sub(r'Facebook\s*Facebook\s*Facebook', 'Facebook', text, flags=re.IGNORECASE)
        text = re.sub(r'(Facebook\s*){2,}', 'Facebook ', text, flags=re.IGNORECASE)
        
        # Remove common Facebook UI elements
        ui_patterns = [
            r'\b(Like|Comment|Share|Reply)\b',
            r'\b\d+\s+(minutes?|hours?|days?|weeks?|months?|years?)\s+ago\b',
            r'\bSee more\b|\bSee less\b',
            r'\bFollow\b|\bFollowing\b',
            r'\bAdd friend\b|\bMessage\b',
            r'\bHome\b|\bWatch\b|\bMarketplace\b|\bGroups\b|\bGaming\b',
            r'\bShared with.*?friends\b',
            r'\bmobile uploads\b',
            r'\b[A-Za-z0-9]{20,}\b',  # Remove long random strings
            r'\b\w+\.\w+\.com\b'  # Remove domain-like strings
        ]
        
        for pattern in ui_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Clean multiple spaces and newlines
        text = re.sub(r'\s+', ' ', text)
        
        # Remove very short fragments
        words = text.split()
        meaningful_words = [word for word in words if len(word) > 2 or word in ['I', 'a', 'is', 'to']]
        
        return ' '.join(meaningful_words).strip()
    
    def _is_likely_post_content(self, text: str) -> bool:
        """Determine if text is likely actual post content"""
        if not text or len(text) < 20:
            return False
        
        # Check for content indicators
        content_indicators = [
            '.',  # Sentences usually end with periods
            '!',  # Exclamation marks
            '?',  # Questions
            '#',  # Hashtags
            '@',  # Mentions
        ]
        
        # Check for UI noise
        ui_noise = ['Like', 'Comment', 'Share', 'Home', 'Watch', 'Marketplace', 'Groups']
        ui_count = sum(1 for noise in ui_noise if noise in text)
        
        # More content indicators = better
        indicator_count = sum(1 for indicator in content_indicators if indicator in text)
        
        # Should have content indicators and minimal UI noise
        return indicator_count > 0 and ui_count < len(text.split()) * 0.3

    def _clean_repetitive_text(self, text: str) -> str:
        """Clean text with excessive repetition"""
        if not text:
            return ""
        
        words = text.split()
        if len(words) < 10:
            return text
        
        # Remove excessive repetition of the word "Facebook"
        if words.count("Facebook") > 10:
            # Keep first few and last few occurrences
            cleaned_words = []
            facebook_count = 0
            for word in words:
                if word == "Facebook":
                    facebook_count += 1
                    if facebook_count <= 3:  # Keep first 3
                        cleaned_words.append(word)
                else:
                    cleaned_words.append(word)
            text = ' '.join(cleaned_words)
        
        return text

    async def _extract_enhanced_timestamp(self, element) -> str:
        """ULTRA-ENHANCED timestamp extraction with Facebook 2024 selectors"""
        try:
            timestamp_candidates = []
            
            # Strategy 1: Facebook 2024 timestamp selectors (updated with real selectors)
            timestamp_selectors = [
                # Real Facebook 2024 selectors based on actual DOM structure
                'li.html-li.xdj266r.xat24cr.xexx8yu.xyri2b.x18d9i69.x1c1uobl.x1rg5ohu.x1xegmmw.x13fj5qh a',  # Real timestamp links in lists
                'span.html-span.xdj266r.x14z9mp.xat24cr.x1lziwak.xexx8yu.xyri2b.x18d9i69.x1c1uobl.x1hl2dhg.x16tdsg8.x1vvkbs.x4k7w5x.x1h91t0o.x1h9r5lt.x1jfb8zj.xv2umb2.x1beo9mf.xaigb6o.x12ejxvf.x3igimt.xarpa2k.xedcshv.x1lytzrv.x1t2pt76.x7ja8zs.x1qrby5j a',
                'div.html-div.xdj266r.x14z9mp.xat24cr.x1lziwak.xexx8yu.xyri2b.x18d9i69.x1c1uobl a',
                'a[role="link"][tabindex="0"]',       # Focusable links
                
                # Fallback selectors
                'a[aria-label*="ago"]',              # Links with "ago" in aria-label
                'a[href*="/posts/"]',                # Post links
                'a[href*="/photos/"]',               # Photo links  
                'a[role="link"][aria-label]',        # Links with aria labels
                'span[id*="jsc"][title]',            # Facebook's JS component spans
                'abbr[title]',                       # HTML5 abbreviation with title
                'time',                              # HTML5 time elements
                'a[title*="20"]',                    # Links with year in title
                'span[title*="20"]'                  # Spans with year in title
            ]
            
            for selector in timestamp_selectors:
                try:
                    elements = await element.query_selector_all(selector)
                    for el in elements:
                        # Check aria-label first (most reliable)
                        aria_label = await el.get_attribute('aria-label')
                        if aria_label and self._is_timestamp_text(aria_label):
                            timestamp_candidates.append((aria_label.strip(), 3))
                        
                        # Check title attribute
                        title = await el.get_attribute('title')
                        if title and self._is_timestamp_text(title):
                            timestamp_candidates.append((title.strip(), 2))
                        
                        # Check text content
                        text = await el.text_content()
                        if text and self._is_timestamp_text(text.strip()):
                            timestamp_candidates.append((text.strip(), 1))
                except:
                    continue
            
            # Strategy 2: Search all text for timestamp patterns
            try:
                full_text = await element.text_content()
                if full_text:
                    import re
                    
                    # Pattern 1: "X ago" format (most common)
                    ago_patterns = [
                        r'(\d+\s+(?:second|minute|hour|day|week|month|year)s?\s+ago)',
                        r'(just now|a moment ago|an? (?:second|minute|hour|day|week|month|year) ago)',
                        r'(yesterday|today|this morning|this afternoon|this evening)'
                    ]
                    
                    for pattern in ago_patterns:
                        matches = re.findall(pattern, full_text, re.IGNORECASE)
                        for match in matches:
                            timestamp_candidates.append((match, 2))
                    
                    # Pattern 2: Specific dates and times
                    date_patterns = [
                        r'(\w+ \d{1,2}, 20\d{2})',           # "January 15, 2023"
                        r'(\d{1,2}/\d{1,2}/20\d{2})',        # "01/15/2023"
                        r'(\d{1,2}:\d{2}\s*(?:AM|PM)?)',     # "2:30 PM"
                        r'(\w+ at \d{1,2}:\d{2}\s*(?:AM|PM)?)'  # "Yesterday at 2:30 PM"
                    ]
                    
                    for pattern in date_patterns:
                        matches = re.findall(pattern, full_text, re.IGNORECASE)
                        for match in matches:
                            timestamp_candidates.append((match, 1))
            except:
                pass
            
            # Strategy 3: Look for time-related attributes in any element
            try:
                all_elements = await element.query_selector_all('*')
                for el in all_elements[:20]:  # Limit search to avoid performance issues
                    try:
                        # Check datetime attribute (HTML5)
                        datetime_attr = await el.get_attribute('datetime')
                        if datetime_attr:
                            timestamp_candidates.append((datetime_attr, 2))
                        
                        # Check data-time or similar attributes
                        for attr_name in ['data-time', 'data-timestamp', 'data-date']:
                            attr_value = await el.get_attribute(attr_name)
                            if attr_value and self._is_timestamp_text(attr_value):
                                timestamp_candidates.append((attr_value, 1))
                    except:
                        continue
            except:
                pass
            
            # Find the best timestamp candidate
            if timestamp_candidates:
                # Sort by priority (higher number = better)
                timestamp_candidates.sort(key=lambda x: x[1], reverse=True)
                best_timestamp = timestamp_candidates[0][0]
                
                # Clean and validate
                cleaned_timestamp = self._clean_timestamp_text(best_timestamp)
                if cleaned_timestamp:
                    return cleaned_timestamp
            
            return ""
            
        except Exception as e:
            logger.debug(f"Error extracting enhanced timestamp: {e}")
            return ""

    def _is_timestamp_text(self, text: str) -> bool:
        """Enhanced check if text looks like a timestamp (updated for Facebook 2024)"""
        if not text or len(text.strip()) < 1:
            return False
        
        text_lower = text.lower().strip()
        
        # Facebook 2024 short format: "5y", "2h", "3m", "1d", "6w", "now"
        import re
        if re.match(r'^\d+[smhdwy]$', text_lower):  # seconds, minutes, hours, days, weeks, years
            return True
        
        if text_lower in ['now', 'just now']:
            return True
        
        # Time indicators
        time_words = ['ago', 'yesterday', 'today', 'just now', 'moment ago', 
                     'morning', 'afternoon', 'evening', 'night']
        time_units = ['second', 'minute', 'hour', 'day', 'week', 'month', 'year']
        
        # Direct time indicators
        if any(word in text_lower for word in time_words):
            return True
        
        # Unit + ago patterns
        if any(unit in text_lower for unit in time_units) and 'ago' in text_lower:
            return True
        
        # Time formats
        time_patterns = [
            r'\d{1,2}:\d{2}',           # 12:30
            r'\d{1,2}/\d{1,2}/20\d{2}', # 01/15/2023
            r'20\d{2}',                 # 2023
            r'\w+ \d{1,2}',            # January 15
        ]
        
        for pattern in time_patterns:
            if re.search(pattern, text):
                return True
        
        return False

    def _clean_timestamp_text(self, text: str) -> str:
        """Clean timestamp text and return best format"""
        if not text:
            return ""
        
        text = text.strip()
        
        # Remove common prefixes/suffixes
        prefixes_to_remove = ['posted ', 'shared ', 'updated ', 'created ']
        for prefix in prefixes_to_remove:
            if text.lower().startswith(prefix):
                text = text[len(prefix):]
        
        # Capitalize first letter for consistency
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
        
        return text

    def _looks_like_timestamp(self, text: str) -> bool:
        """Check if text looks like a timestamp"""
        if not text:
            return False
        
        text = text.lower()
        time_indicators = ['ago', ':', '202', '20', 'am', 'pm', 'minute', 'hour', 'day', 'week', 'month', 'year']
        return any(indicator in text for indicator in time_indicators)

    def _parse_facebook_timestamp(self, timestamp_str: str) -> str:
        """Parse Facebook timestamp into readable format"""
        try:
            # Handle various Facebook timestamp formats
            timestamp_str = timestamp_str.strip()
            
            # Direct readable formats
            if any(month in timestamp_str.lower() for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                                                                 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
                return timestamp_str
            
            # Relative time formats
            if 'ago' in timestamp_str.lower():
                return timestamp_str
                
            # ISO format
            if 'T' in timestamp_str and 'Z' in timestamp_str:
                from datetime import datetime
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d %H:%M:%S')
                
            return timestamp_str if timestamp_str else ""
        except Exception:
            return timestamp_str if timestamp_str else ""

    async def _extract_enhanced_post_url(self, element) -> str:
        """Enhanced post URL extraction"""
        try:
            # Enhanced URL selectors
            url_selectors = [
                'a[href*="/posts/"]',
                'a[href*="/photo/"]',
                'a[href*="permalink"]',
                'a[href*="story_fbid"]',
                'a[href*="pfbid"]',
                'span[id*="timestamp"] a',
                '[data-testid*="story-subtitle"] a',
                'time[datetime] a',
                'a[role="link"][aria-label*="ago"]'
            ]
            
            for selector in url_selectors:
                try:
                    url_elements = await element.query_selector_all(selector)
                    for url_el in url_elements:
                        href = await url_el.get_attribute('href')
                        if href and self._is_valid_facebook_post_url(href):
                            # Convert relative to absolute URL
                            if href.startswith('/'):
                                href = f'https://www.facebook.com{href}'
                            return href
                except Exception:
                    continue
                    
            return ""
        except Exception as e:
            logger.debug(f"Error extracting enhanced post URL: {e}")
            return ""

    def _is_valid_facebook_post_url(self, url: str) -> bool:
        """Check if URL is a valid Facebook post URL"""
        if not url:
            return False
        
        valid_patterns = [
            '/posts/', '/photo/', 'story_fbid', 'pfbid', 'permalink'
        ]
        
        return any(pattern in url for pattern in valid_patterns)

    async def _generate_enhanced_post_id(self, element) -> str:
        """Generate enhanced post ID with better uniqueness"""
        try:
            # Try to find existing post ID attributes
            id_attributes = ['data-testid', 'id', 'data-story-id', 'data-post-id']
            
            for attr in id_attributes:
                post_id = await element.get_attribute(attr)
                if post_id:
                    # Clean and shorten the ID
                    clean_id = re.sub(r'[^a-zA-Z0-9]', '', post_id)
                    if len(clean_id) > 8:
                        return clean_id[:12]  # Take first 12 chars
            
            # Fallback: generate ID from content hash
            content = await element.text_content() or ""
            if content:
                import hashlib
                content_hash = hashlib.md5(content[:200].encode()).hexdigest()
                return content_hash[:12]
            
            # Last resort: timestamp-based ID
            import time
            return f"post_{int(time.time() * 1000) % 1000000000000}"
            
        except Exception as e:
            logger.debug(f"Error generating enhanced post ID: {e}")
            import time
            return f"post_{int(time.time() * 1000) % 1000000000000}"

    async def _extract_enhanced_tagged_accounts(self, element) -> List[Dict[str, Any]]:
        """Enhanced extraction of tagged accounts"""
        try:
            tagged_accounts = []
            
            # Enhanced selectors for tagged accounts
            tag_selectors = [
                'a[href*="facebook.com/"]:not([href*="/posts/"]):not([href*="/photo/"])',
                'a[data-hovercard-prefer-more-content-show]',
                'span[data-testid="event_permalink_user_name"] a',
                'a[role="link"][href*="profile.php"]',
                'a[href*="facebook.com/"][aria-label]'
            ]
            
            for selector in tag_selectors:
                try:
                    tag_elements = await element.query_selector_all(selector)
                    for tag_el in tag_elements:
                        href = await tag_el.get_attribute('href')
                        name = await tag_el.text_content()
                        aria_label = await tag_el.get_attribute('aria-label')
                        
                        if href and name and self._is_valid_profile_url(href):
                            # Clean up the name
                            clean_name = name.strip()
                            if clean_name and len(clean_name) > 1 and len(clean_name) < 100:
                                account = {
                                    "name": clean_name,
                                    "profile_url": href if href.startswith('http') else f'https://www.facebook.com{href}',
                                    "bio": aria_label or "Facebook User"
                                }
                                
                                # Avoid duplicates
                                if not any(acc['name'] == account['name'] for acc in tagged_accounts):
                                    tagged_accounts.append(account)
                                    
                except Exception:
                    continue
            
            return tagged_accounts[:5]  # Limit to 5 tagged accounts per post
            
        except Exception as e:
            logger.debug(f"Error extracting enhanced tagged accounts: {e}")
            return []

    def _is_valid_profile_url(self, url: str) -> bool:
        """Check if URL is a valid Facebook profile URL"""
        if not url:
            return False
        
        # Valid profile patterns
        profile_patterns = [
            'facebook.com/profile.php?id=',
            'facebook.com/people/',
            'facebook.com/public/'
        ]
        
        # Or direct username (facebook.com/username but not posts/photos/etc)
        if 'facebook.com/' in url and not any(invalid in url for invalid in ['/posts/', '/photos/', '/videos/', '/about/']):
            return True
            
        return any(pattern in url for pattern in profile_patterns)

    async def _extract_location_from_post(self, element) -> str:
        """Extract location information from post"""
        try:
            location_selectors = [
                'a[href*="places/"]',
                'a[href*="location/"]',
                'span[data-testid="location-subtitle"]',
                'a[role="link"][href*="map"]'
            ]
            
            for selector in location_selectors:
                try:
                    loc_elements = await element.query_selector_all(selector)
                    for loc_el in loc_elements:
                        location_text = await loc_el.text_content()
                        if location_text and len(location_text.strip()) > 2:
                            return location_text.strip()
                except Exception:
                    continue
                    
            return ""
        except Exception as e:
            logger.debug(f"Error extracting location: {e}")
            return ""

    async def _extract_post_comments(self, element) -> List[Dict[str, Any]]:
        """Extract comments from post (limited extraction for performance)"""
        try:
            comments = []
            # Light comment extraction to avoid performance issues
            comment_selectors = [
                'div[data-testid="UFI2Comment/body"]',
                'div[role="article"] div[dir="auto"]'
            ]
            
            for selector in comment_selectors:
                try:
                    comment_elements = await element.query_selector_all(selector)
                    for i, comment_el in enumerate(comment_elements[:3]):  # Limit to 3 comments
                        comment_text = await comment_el.text_content()
                        if comment_text and len(comment_text.strip()) > 10:
                            comments.append({
                                "text": comment_text.strip()[:200],
                                "author": "Unknown"
                            })
                except Exception:
                    continue
                    
            return comments
        except Exception as e:
            logger.debug(f"Error extracting comments: {e}")
            return []

    async def _extract_reactions_enhanced(self, element) -> Dict[str, int]:
        """Extract reaction counts"""
        try:
            reactions = {"total": 0}
            
            # Look for reaction elements
            reaction_selectors = [
                'span[aria-label*="reaction"]',
                'div[data-testid="UFI2ReactionsCount/sentenceWithSocialContext"]',
                'a[aria-label*="reaction"]'
            ]
            
            for selector in reaction_selectors:
                try:
                    reaction_elements = await element.query_selector_all(selector)
                    for reaction_el in reaction_elements:
                        aria_label = await reaction_el.get_attribute('aria-label')
                        if aria_label:
                            # Extract number from reaction text
                            numbers = re.findall(r'[\d,]+', aria_label)
                            if numbers:
                                count = int(numbers[0].replace(',', ''))
                                reactions["total"] = max(reactions["total"], count)
                                break
                except Exception:
                    continue
                    
            return reactions
        except Exception as e:
            logger.debug(f"Error extracting reactions: {e}")
            return {"total": 0}

    async def _extract_comments_count(self, element) -> int:
        """Extract comment count"""
        try:
            comment_selectors = [
                'a[aria-label*="comment"]',
                'span[aria-label*="comment"]',
                'div[data-testid*="comment"] span'
            ]
            
            for selector in comment_selectors:
                try:
                    comment_elements = await element.query_selector_all(selector)
                    for comment_el in comment_elements:
                        aria_label = await comment_el.get_attribute('aria-label')
                        text_content = await comment_el.text_content()
                        
                        for text in [aria_label, text_content]:
                            if text and 'comment' in text.lower():
                                numbers = re.findall(r'(\d+)', text)
                                if numbers:
                                    return int(numbers[0])
                except Exception:
                    continue
                    
            return 0
        except Exception as e:
            logger.debug(f"Error extracting comment count: {e}")
            return 0

    async def _extract_media_info(self, element) -> List[Dict[str, Any]]:
        """Extract media information from post"""
        try:
            media_info = []
            
            # Look for images
            img_elements = await element.query_selector_all('img')
            for img in img_elements[:3]:  # Limit to 3 images
                src = await img.get_attribute('src')
                alt = await img.get_attribute('alt')
                if src and 'facebook.com' in src and not 'static' in src:
                    media_info.append({
                        "type": "image",
                        "url": src,
                        "description": alt or ""
                    })
            
            # Look for videos
            video_elements = await element.query_selector_all('video')
            for video in video_elements[:2]:  # Limit to 2 videos
                src = await video.get_attribute('src')
                if src:
                    media_info.append({
                        "type": "video",
                        "url": src,
                        "description": ""
                    })
                    
            return media_info
        except Exception as e:
            logger.debug(f"Error extracting media info: {e}")
            return []

    def _is_valid_post_content(self, text: str) -> bool:
        """Check if text content is likely to be actual post content vs UI elements"""
        if not text or len(text.strip()) < 20:
            return False
        
        # Common UI/navigation words that indicate non-content
        ui_keywords = [
            'home', 'notifications', 'messages', 'marketplace', 'watch', 'groups',
            'gaming', 'pages', 'more', 'create', 'privacy', 'terms', 'help',
            'settings', 'log out', 'menu', 'search', 'filter', 'sort', 'view',
            'friends list', 'timeline', 'about', 'photos', 'videos', 'check-in',
            'feeling', 'life event', 'أصدقاء', 'صور', 'فيديو', 'المزيد'  # Arabic UI terms
        ]
        
        text_lower = text.lower()
        
        # If text is mostly UI keywords, it's not content
        ui_word_count = sum(1 for keyword in ui_keywords if keyword in text_lower)
        total_words = len(text.split())
        
        if total_words > 0 and ui_word_count / total_words > 0.5:
            return False
        
        # If text is very short and contains common UI actions
        if len(text) < 50 and any(action in text_lower for action in ['like', 'comment', 'share', 'reply']):
            return False
        
        # If text is all uppercase (likely UI labels)
        if text.isupper() and len(text) < 100:
            return False
            
        return True

    async def _extract_tagged_accounts(self, element) -> List[Dict[str, Any]]:
        """Extract tagged accounts with profile URLs and bios"""
        tagged_accounts = []
        try:
            # Look for tagged users in post content and header
            tag_selectors = [
                'a[role="link"][href*="/"][data-hovercard]',  # Profile links with hovercards
                'a[href*="facebook.com/"]:not([href*="/hashtag/"]):not([href*="/posts/"])',  # Profile links
                'span[data-hovercard] a[role="link"]'  # Links within hovercard spans
            ]
            
            for selector in tag_selectors:
                tag_elements = await element.query_selector_all(selector)
                for tag_el in tag_elements[:5]:  # Limit to prevent too many requests
                    try:
                        name = await tag_el.text_content()
                        profile_url = await tag_el.get_attribute('href')
                        
                        if name and profile_url and name.strip():
                            # Clean up profile URL
                            if profile_url.startswith('/'):
                                profile_url = f"https://facebook.com{profile_url}"
                            
                            # Extract bio from hovercard if available
                            bio = await self._extract_bio_from_hovercard(tag_el)
                            
                            tagged_account = {
                                "name": self.utils.clean_text(name),
                                "profile_url": profile_url,
                                "bio": bio or "Facebook User"
                            }
                            
                            # Avoid duplicates
                            if not any(acc["name"] == tagged_account["name"] for acc in tagged_accounts):
                                tagged_accounts.append(tagged_account)
                                
                    except Exception as e:
                        logger.debug(f"Error extracting tagged account: {e}")
                        continue
            
        except Exception as e:
            logger.debug(f"Error extracting tagged accounts: {e}")
        
        return tagged_accounts

    async def _extract_bio_from_hovercard(self, element) -> str:
        """Extract bio information from profile hovercard"""
        try:
            # Try to hover to trigger hovercard
            await element.hover()
            await asyncio.sleep(1)
            
            # Look for hovercard content
            hovercard_selectors = [
                '[role="tooltip"] div[dir="auto"]',
                '[data-testid="profile_hovercard"] div',
                '.profileHovercard div[dir="auto"]'
            ]
            
            for selector in hovercard_selectors:
                bio_elements = await self.page.query_selector_all(selector)
                for bio_el in bio_elements:
                    try:
                        bio_text = await bio_el.text_content()
                        if bio_text and len(bio_text.strip()) > 5:
                            return self.utils.clean_text(bio_text)
                    except:
                        continue
                        
            return ""
        except:
            return ""

    async def _extract_location_tagged(self, element) -> str:
        """Extract location information from posts"""
        try:
            # Look for location indicators
            location_selectors = [
                'a[href*="/places/"]:not([aria-hidden="true"])',
                'a[data-hovercard*="location"]',
                'span[data-testid="location"] a',
                'div[data-testid="location_tag"]'
            ]
            
            for selector in location_selectors:
                location_elements = await element.query_selector_all(selector)
                for loc_el in location_elements:
                    try:
                        location_text = await loc_el.text_content()
                        if location_text and location_text.strip():
                            return self.utils.clean_text(location_text)
                    except:
                        continue
                        
            return ""
        except Exception as e:
            logger.debug(f"Error extracting location: {e}")
            return ""

    async def _extract_comments_enhanced(self, element) -> List[Dict[str, Any]]:
        """Extract comments with enhanced commenter profile information"""
        comments = []
        try:
            # Try to expand comments first
            view_comments_buttons = await element.query_selector_all('div[role="button"]:has-text("View"), div[role="button"]:has-text("comments")')
            for button in view_comments_buttons[:1]:  # Only click first button
                try:
                    await button.click()
                    await asyncio.sleep(2)
                    break
                except:
                    pass

            # Enhanced comment selectors
            comment_selectors = [
                'div[aria-label*="Comment by"]',
                'div[data-testid="comment_container"]',
                'div[role="article"] div[role="article"]',  # Nested articles are often comments
                'li[data-testid="comment"]'
            ]
            
            for selector in comment_selectors:
                comment_elements = await element.query_selector_all(selector)
                for comment_el in comment_elements[:5]:  # Limit comments for performance
                    try:
                        comment_data = await self._extract_single_comment_enhanced(comment_el)
                        if comment_data and comment_data.get("comment_text"):
                            comments.append(comment_data)
                    except Exception as e:
                        logger.debug(f"Error extracting comment: {e}")
                        continue
                        
                if comments:  # If we found comments with this selector, break
                    break
            
        except Exception as e:
            logger.debug(f"Error extracting enhanced comments: {e}")
        
        return comments

    async def _extract_single_comment_enhanced(self, comment_element) -> Optional[Dict[str, Any]]:
        """Extract a single comment with enhanced commenter profile information"""
        try:
            # Extract commenter profile
            commenter_link = await comment_element.query_selector('a[role="link"]:not([aria-label])')
            if not commenter_link:
                return None
                
            commenter_name = await commenter_link.text_content()
            commenter_url = await commenter_link.get_attribute('href')
            
            if not commenter_name or not commenter_url:
                return None
            
            # Clean up commenter URL
            if commenter_url.startswith('/'):
                commenter_url = f"https://facebook.com{commenter_url}"
            
            # Extract commenter bio
            commenter_bio = await self._extract_bio_from_hovercard(commenter_link)
            
            # Extract comment text
            comment_text_elements = await comment_element.query_selector_all('div[dir="auto"]')
            comment_text = ""
            for text_el in comment_text_elements:
                try:
                    text = await text_el.text_content()
                    if text and len(text.strip()) > 2 and text.strip() != commenter_name.strip():
                        if not self._is_metadata_or_ui_text(text):
                            comment_text = self.utils.clean_text(text)
                            break
                except:
                    continue
            
            if not comment_text:
                return None
            
            # Extract comment timestamp
            timestamp_elements = await comment_element.query_selector_all('a[role="link"] span')
            comment_timestamp = ""
            for ts_el in timestamp_elements:
                try:
                    ts_text = await ts_el.text_content()
                    if ts_text and any(word in ts_text.lower() for word in ['ago', 'h', 'm', 'd', 'w']):
                        comment_timestamp = ts_text.strip()
                        break
                except:
                    continue
            
            return {
                "commenter": {
                    "name": self.utils.clean_text(commenter_name),
                    "profile_url": commenter_url,
                    "bio": commenter_bio or "Facebook User"
                },
                "comment_text": comment_text,
                "timestamp": comment_timestamp
            }
            
        except Exception as e:
            logger.debug(f"Error extracting single enhanced comment: {e}")
            return None

    async def _extract_user_comments_on_other_posts(self, username: str, max_comments: int = 10) -> List[Dict[str, Any]]:
        """Extract comments made by the user on other people's posts"""
        user_comments = []
        try:
            # This would require navigating to activity/comments section
            # For now, implementing a placeholder structure
            logger.info("User comments on other posts feature - placeholder implementation")
            
            # TODO: Navigate to user's activity/comments section
            # This would involve:
            # 1. Going to profile/activity
            # 2. Finding comments section
            # 3. Extracting comments with original post context
            
            return user_comments
            
        except Exception as e:
            logger.debug(f"Error extracting user comments on other posts: {e}")
            return user_comments

    def _format_own_post(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format post data for own_posts section with all required fields"""
        return {
            "id": post_data.get("id", ""),
            "timestamp": post_data.get("timestamp", ""),
            "content": post_data.get("content", ""),
            "caption": post_data.get("caption", post_data.get("content", "")),  # Use content as caption fallback
            "media_screenshot_url": post_data.get("media_screenshot_url", ""),
            "original_url": post_data.get("original_url", ""),
            "shared": post_data.get("shared", False),
            "shared_content": post_data.get("shared_content", ""),
            "original_poster": post_data.get("original_poster", ""),
            "is_tagged": post_data.get("is_tagged", False),
            "tagged_accounts": post_data.get("tagged_accounts", []),
            "location_tagged": post_data.get("location_tagged", ""),
            "comments": post_data.get("comments", []),
            "reactions": post_data.get("reactions", {}),
            "comments_count": post_data.get("comments_count", 0),
            "shares_count": post_data.get("shares_count", 0),
            "media": post_data.get("media", [])
        }

    def _format_tagged_post(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format post data for tagged_posts section"""
        return self._format_own_post(post_data)  # Same structure for now

    def _generate_post_id(self, content: str, timestamp: str) -> str:
        """Generate unique post ID"""
        import hashlib
        if not content and not timestamp:
            return hashlib.md5(str(time.time()).encode()).hexdigest()[:12]
        
        return hashlib.md5((content[:50] + timestamp).encode()).hexdigest()[:12]

    def _is_metadata_or_ui_text(self, text: str) -> bool:
        """Enhanced check for metadata or UI text"""
        ui_indicators = [
            'like', 'comment', 'share', 'react', 'follow', 'friend',
            'see more', 'show more', 'hide', 'report', 'block',
            'sponsored', 'suggested', 'promoted', 'ad',
            'just now', 'ago', 'yesterday', 'edited'
        ]
        
        text_lower = text.lower().strip()
        
        # Very short text is likely UI
        if len(text) < 5:
            return True
            
        # Check for UI indicators
        if any(indicator in text_lower for indicator in ui_indicators):
            return True
            
        # Check for pure numbers or engagement metrics
        if re.match(r'^\d+[KMB]?$', text.strip()) or re.match(r'^\d+\s*(like|comment|share)s?$', text_lower):
            return True
            
        return False

    # Additional helper methods
    async def _navigate_with_retries(self, url: str, retries: int = 3) -> bool:
        """Navigate with retries and crash recovery"""
        for attempt in range(retries):
            try:
                # Check page health before navigation
                if not await self._check_page_health():
                    logger.warning(f"Page crashed before navigation attempt {attempt + 1}, recovering...")
                    if not await self._recover_from_crash():
                        logger.error(f"Could not recover from crash on attempt {attempt + 1}")
                        continue
                
                logger.info(f"Navigation attempt {attempt + 1} to: {url}")
                await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Verify navigation was successful
                current_url = self.page.url
                if current_url:
                    logger.info(f"Successfully navigated to: {current_url}")
                    await asyncio.sleep(3)  # Reduced wait time
                    return True
                else:
                    logger.warning(f"Navigation attempt {attempt + 1}: No URL returned")
                    
            except Exception as e:
                logger.warning(f"Navigation attempt {attempt + 1} failed: {e}")
                
                # If this looks like a page crash, try to recover
                if "page crashed" in str(e).lower() or "target closed" in str(e).lower():
                    logger.warning("Detected page crash during navigation, attempting recovery...")
                    if await self._recover_from_crash():
                        logger.info("Recovery successful, continuing...")
                    else:
                        logger.error("Recovery failed")
                
                if attempt == retries - 1:
                    logger.error(f"All {retries} navigation attempts failed")
                    return False
                    
                await asyncio.sleep(3)  # Wait between attempts
        return False

    async def _wait_for_posts_to_load(self) -> None:
        """Wait for posts to load with enhanced detection and login verification"""
        try:
            # First check if we're actually logged in
            logged_in = await self._check_login_status()
            if not logged_in:
                logger.warning("⚠️ Not logged in - posts may not be accessible")
            
            # Wait for profile to load first
            await self.page.wait_for_selector('h1', timeout=self.default_timeout)
            
            # Look for posts with improved selectors based on actual Facebook structure
            post_selectors = [
                'div[role="article"]',
                'div[data-testid*="post"]', 
                'div[aria-posinset]',  # Individual post containers
                '[role="main"] > div > div > div',  # General content containers
                'div[data-pagelet*="FeedUnit"]'
            ]
            
            posts_found = False
            for selector in post_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        logger.info(f"✅ Found {len(elements)} potential posts with selector: {selector}")
                        posts_found = True
                        break
                except:
                    logger.debug(f"❌ Selector not found: {selector}")
                    continue
            
            if not posts_found:
                logger.warning("⚠️ No posts found with standard selectors")
                # Save debug page for inspection
                await self.utils.save_page_html("debug_no_posts_found.html")
            
            await asyncio.sleep(3)
            
        except Exception as e:
            logger.warning(f"Posts might not have loaded completely: {e}")

    async def _check_login_status(self) -> bool:
        """Check if user is logged in"""
        try:
            # Check for login form (means not logged in)
            login_form = await self.page.query_selector('form[data-testid="royal_login_form"]')
            if login_form:
                logger.warning("❌ Login form detected - user is not logged in")
                return False
            
            # Check for user navigation elements (means logged in)
            nav_elements = [
                '[aria-label*="profile" i]',
                '[aria-label="Home"]', 
                'div[role="banner"] a[href="/"]'  # Facebook home link in header
            ]
            
            for selector in nav_elements:
                element = await self.page.query_selector(selector)
                if element:
                    logger.info("✅ Login status verified - user appears to be logged in")
                    return True
                    
            logger.warning("⚠️ Login status unclear - may affect post extraction")
            return False
            
        except Exception as e:
            logger.debug(f"Error checking login status: {e}")
            return False

    async def _perform_post_scrolling(self):
        """Scroll down the page"""
        try:
            await self.page.evaluate("window.scrollBy(0, window.innerHeight * 0.8);")
            await asyncio.sleep(2)
        except:
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            await asyncio.sleep(3)

    async def _extract_post_url_enhanced(self, element) -> str:
        """Extract post permalink URL with improved selectors"""
        try:
            # Enhanced link selectors for different types of posts
            link_selectors = [
                # Post permalinks
                'a[aria-label][href*="/posts/"]',
                'a[aria-label][href*="/videos/"]',
                'a[aria-label][href*="story_fbid="]',
                # General post links
                'a[href*="fbid="]',
                'a[href*="/permalink/"]',
                # Time-based links (often contain post URLs)
                'a[href*="?comment_id"]:has(time)',
                'a[aria-label*="hours"], a[aria-label*="minutes"], a[aria-label*="days"]',
                # Timestamp links
                'a[role="link"] span[title]',
                # Generic post links
                'a[href*="facebook.com"][href*="posts"]'
            ]
            
            for selector in link_selectors:
                link_elements = await element.query_selector_all(selector)
                for link_element in link_elements:
                    try:
                        href = await link_element.get_attribute('href')
                        if href:
                            # Clean and format the URL
                            if href.startswith('/'):
                                href = f"https://facebook.com{href}"
                            
                            # Filter for valid post URLs
                            if any(indicator in href for indicator in ['/posts/', 'fbid=', 'story_fbid=', '/permalink/']):
                                # Remove tracking parameters
                                clean_url = href.split('&__cft__')[0].split('&__tn__')[0]
                                return clean_url
                    except:
                        continue
                        
        except Exception as e:
            logger.debug(f"Error extracting post URL: {e}")
            
        return ""

    async def _extract_post_reactions_enhanced(self, element) -> Dict[str, Any]:
        """Extract reaction information"""
        try:
            # Look for reaction indicators
            reaction_elements = await element.query_selector_all('div[aria-label*="reaction"], span[aria-label*="like"]')
            for el in reaction_elements:
                aria_label = await el.get_attribute('aria-label')
                if aria_label and 'reaction' in aria_label.lower():
                    # Parse reaction count
                    count_match = re.search(r'([\d,]+)', aria_label)
                    if count_match:
                        return {"total": self.utils.parse_count(count_match.group(1))}
                        
            return {"total": 0}
        except:
            return {"total": 0}

    async def _extract_shares_count(self, element) -> int:
        """Extract share count"""
        try:
            share_elements = await element.query_selector_all('div[aria-label*="share"], span[aria-label*="share"]')
            for el in share_elements:
                aria_label = await el.get_attribute('aria-label')
                if aria_label and 'share' in aria_label.lower():
                    count_match = re.search(r'([\d,]+)', aria_label)
                    if count_match:
                        return self.utils.parse_count(count_match.group(1))
            return 0
        except:
            return 0

    async def _detect_if_tagged_post(self, element) -> bool:
        """Detect if this is a tagged post"""
        try:
            # Look for "is with" or tagging indicators in post header
            header_elements = await element.query_selector_all('h3, h4, div[data-testid="post_subtitle"]')
            for header_el in header_elements:
                header_text = await header_el.text_content()
                if header_text and any(indicator in header_text.lower() for indicator in ["is with", "was tagged", "at"]):
                    return True
            return False
        except:
            return False

    async def get_locations_visited(self, username: str) -> List[Dict[str, Any]]:
        """Extract locations visited (check-ins and tagged locations)"""
        locations = []
        try:
            # Navigate to places/locations section
            places_url = self._construct_profile_url(username, "map")
            logger.info(f"Navigating to places: {places_url}")
            
            if await self._navigate_with_retries(places_url):
                await asyncio.sleep(5)
                
                # Extract location data
                location_elements = await self.page.query_selector_all('[data-testid="place"], .place-item, a[href*="/places/"]')
                
                for loc_el in location_elements[:20]:  # Limit locations
                    try:
                        place_name = await loc_el.text_content()
                        if place_name and len(place_name.strip()) > 2:
                            # Try to extract timestamp if available
                            timestamp_el = await loc_el.query_selector('time, span[title]')
                            timestamp = ""
                            if timestamp_el:
                                timestamp = await timestamp_el.get_attribute('title') or await timestamp_el.text_content()
                            
                            locations.append({
                                "place": self.utils.clean_text(place_name),
                                "timestamp": timestamp or "Unknown"
                            })
                    except:
                        continue
            
        except Exception as e:
            logger.error(f"Error extracting locations: {e}")
        
        return locations
