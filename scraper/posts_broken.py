"""
Functions for scraping Facebook posts and comments
"""
import asyncio
import re
from typing import Dict, List, Any, Optional
from playwright.async_api import Page

from .utils import ScraperUtils

class PostsScraper:
    def __init__(self, page: Page, utils: ScraperUtils):
        self.page = page
        self.utils = utils
    
    def _detect_profile_type(self, username: str) -> tuple[str, str]:
        """Detect if input is username or profile ID and return appropriate URL format"""
        try:
            # Clean input first - remove whitespace, trailing slashes, and @ symbols
            username = username.strip().rstrip('/').lstrip('@')
            
            # Handle full Facebook URLs with more robust extraction
            if "facebook.com" in username.lower():
            if "profile.php?id=" in username:
                    # Extract profile ID from full URL - improved regex to handle various formats
                import re
                match = re.search(r'profile\.php\?id=(\d+)', username)
                if match:
                    profile_id = match.group(1)
                        print(f"🔗 Extracted profile ID from full URL: {profile_id}")
                        return "id", profile_id
                else:
                    # Extract username from full URL - more robust extraction
                    try:
                        # Split by facebook.com/ and get the next part
                        parts = username.lower().split('facebook.com/')
                        if len(parts) > 1:
                            username_part = parts[1].split('/')[0].split('?')[0].split('#')[0]
                            if username_part and not username_part.isdigit() and len(username_part) > 0:
                                print(f"🔗 Extracted username from full URL: {username_part}")
                                return "username", username_part
                    except Exception as e:
                        print(f"⚠️ Error extracting username from URL: {e}")
            
            # Handle profile.php format without domain
            if "profile.php?id=" in username:
                import re
                match = re.search(r'profile\.php\?id=(\d+)', username)
                if match:
                    profile_id = match.group(1)
                    print(f"🔢 Detected profile.php format: {profile_id}")
                    return "id", profile_id
            
            # Handle numeric ID only
            if username.isdigit():
                # Validate profile ID format (Facebook profile IDs are typically 15-17 digits)
                if len(username) < 5 or len(username) > 20:
                    print(f"⚠️ Profile ID {username} has unusual length ({len(username)} digits)")
                print(f"🔢 Detected numeric profile ID: {username}")
                return "id", username
            
            # Handle username format (anything else)
            print(f"👤 Detected username format: {username}")
            return "username", username
            
        except Exception as e:
            print(f"⚠️ Error detecting profile type: {e}")
            # Default to username format
            return "username", username
    
    def _construct_profile_url(self, username: str, section: str = "") -> str:
        """Construct the correct Facebook URL for both username and profile ID formats"""
        try:
            profile_type, profile_identifier = self._detect_profile_type(username)
            
            # Ensure we're working with clean identifiers
            if profile_type == "id":
                # For profile IDs, use the profile.php format
                base_url = f"https://www.facebook.com/profile.php?id={profile_identifier}"
                if section:
                    # For profile IDs, sections are added as parameters
                    return f"{base_url}&sk={section}"
                return base_url
            else:
                # For usernames, use the standard format
                base_url = f"https://www.facebook.com/{profile_identifier}"
                if section:
                    # For usernames, sections are added as paths
                    return f"{base_url}/{section}"
                return base_url
                
        except Exception as e:
            print(f"⚠️ Error constructing URL: {e}")
            # Fallback: extract clean username/id from input
            clean_input = username
            if "facebook.com/" in username:
                clean_input = username.split("facebook.com/")[-1].split("/")[0].split("?")[0]
            return f"https://www.facebook.com/{clean_input}{f'/{section}' if section else ''}"

    async def get_own_posts(self, username: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """Scrape user's own posts with improved selectors and error handling"""
        try:
            print("🔍 Extracting own posts...")
            
            # Check if page/browser is still available
            if not self.page or self.page.is_closed():
                print("❌ Page is closed, cannot get own posts")
                return []
                
            # Construct appropriate profile URL using helper function
            profile_url = self._construct_profile_url(username)
            print(f"🔗 Navigating to profile for posts: {profile_url}")
            await self.page.goto(profile_url, wait_until="domcontentloaded", timeout=90000)
            await asyncio.sleep(5)  # Wait for page to stabilize
            
            # Check for privacy restrictions
            privacy_indicators = [
                'div:text-matches("This content isn\'t available|Posts are private|No posts to show")',
                'div:has-text("Only you can see")',
            ]
            
            for indicator in privacy_indicators:
                try:
                    privacy_element = await self.page.query_selector(indicator)
                    if privacy_element:
                        print("🔒 Posts are private or restricted")
                        return []
                except Exception:
                    continue
            
            # Try to navigate to posts section if available
            posts_tab_selectors = [
                'a[href*="/posts"]',
                'nav a:text("Posts")',
                'div[role="tablist"] a:text("Posts")',
            ]
            
            for selector in posts_tab_selectors:
                try:
                    posts_tab = await self.page.query_selector(selector)
                    if posts_tab:
                        print("🔗 Navigating to posts tab...")
                        await posts_tab.click()
                        await asyncio.sleep(3)
                        break
                except Exception:
                    continue
            
            # Scroll to load more posts with better scrolling
            print("📜 Scrolling to load more posts...")
            await self._advanced_scroll_for_posts(10)
            
            # Expand all comments if possible
            await self.utils.click_see_more_buttons()
            
            # Extract posts with improved detection
            return await self._extract_posts_improved(max_posts, "own")
            
        except Exception as e:
            print(f"❌ Error getting own posts: {e}")
            return []

    async def get_tagged_posts(self, username: str, max_posts: int = 20) -> List[Dict[str, Any]]:
        """Scrape posts where the user is tagged with improved selectors"""
        try:
            print("🔍 Extracting tagged posts...")
            
            # Check if page/browser is still available
            if not self.page or self.page.is_closed():
                print("❌ Page is closed, cannot get tagged posts")
                return []
                
            # Navigate to tagged posts with better timeout handling
            # Construct appropriate tagged photos URL using helper function
            tagged_url = self._construct_profile_url(username, "photos_of")
            print(f"🔗 Navigating to tagged posts: {tagged_url}")
            await self.page.goto(tagged_url, wait_until="domcontentloaded", timeout=90000)
            await asyncio.sleep(5)  # Wait for page to stabilize
            
            # Check if there are any tagged posts
            privacy_indicators = [
                'div:text-matches("No photos to show|This content isn\'t available|Tagged posts are private")',
                'div:has-text("Only you can see")',
            ]
            
            for indicator in privacy_indicators:
                try:
                    privacy_element = await self.page.query_selector(indicator)
                    if privacy_element:
                        print("🔒 Tagged posts are private or empty")
                        return []
                except Exception:
                    continue
            
            # Scroll to load more posts
            await self._advanced_scroll_for_posts(5)
            
            # Extract posts
            return await self._extract_posts_improved(max_posts, "tagged")
            
        except Exception as e:
            print(f"❌ Error getting tagged posts: {e}")
            return []

    async def _advanced_scroll_for_posts(self, max_attempts: int = 10) -> None:
        """Advanced scrolling specifically for loading posts"""
        print("🔄 Advanced scrolling to load posts...")
        
        last_post_count = 0
        stable_count = 0
        max_stable_attempts = 3
        
        for attempt in range(max_attempts):
            print(f"📜 Scroll attempt {attempt + 1}/{max_attempts}")
            
            # Count current posts
            current_posts = await self.page.query_selector_all('div[role="article"], div[data-pagelet*="FeedUnit"]')
            current_count = len(current_posts)
            
            print(f"   Current posts found: {current_count}")
            
            # Check if we're making progress
            if current_count == last_post_count:
                stable_count += 1
                print(f"   No new posts loaded (stable count: {stable_count})")
                if stable_count >= max_stable_attempts:
                    print("   ✅ Reached stable state, stopping scroll")
                    break
            else:
                stable_count = 0
                print(f"   📈 Found {current_count - last_post_count} new posts")
            
            last_post_count = current_count
            
            # Perform scrolling
            try:
                # Scroll to bottom
                await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(2)
                
                # Scroll in chunks
                for i in range(3):
                    await self.page.evaluate(f'window.scrollBy(0, {300 + i * 100})')
                    await asyncio.sleep(0.5)
                
                # Wait for content to load
                await asyncio.sleep(3)
                
            except Exception as e:
                print(f"   ⚠️ Error during scroll attempt {attempt + 1}: {e}")
                continue

    async def _extract_posts_improved(self, max_posts: int, post_type: str) -> List[Dict[str, Any]]:
        """Improved post extraction with better selectors and validation"""
        posts_list = []
        
        print(f"🔍 Looking for {post_type} posts with improved detection...")
        
        # Comprehensive post selectors
        post_selectors = [
            'div[role="article"]',
            'div[data-pagelet*="FeedUnit"]',
            'div[data-testid*="post"]',
            'div[data-ad-preview="message"]',
            'div[data-testid="story-subtitle"]',
            'div[aria-label*="Story"]',
            'div[data-pagelet*="ProfileTimeline"]',
        ]
        
        post_elements = []
        for selector in post_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                print(f"🔍 Found {len(elements)} elements with selector: {selector}")
                if elements:
                    post_elements.extend(elements)
            except Exception as e:
                print(f"⚠️ Post selector {selector} failed: {e}")
                continue
        
        # Remove duplicates while preserving order
        seen = set()
        unique_elements = []
        for element in post_elements:
            element_id = id(element)
            if element_id not in seen:
                seen.add(element_id)
                unique_elements.append(element)
        
        post_elements = unique_elements
        print(f"📊 Total unique post elements found: {len(post_elements)}")
        
        if not post_elements:
            print("❌ No post elements found with any selector")
            return []
        
        count = 0
        for i, element in enumerate(post_elements):
            if count >= max_posts:
                break
                
            try:
                print(f"🔍 Processing post element {i+1}/{len(post_elements)}...")
                
                # Enhanced post validation
                if not await self._is_valid_post(element):
                    print(f"⚠️ Skipping element {i+1} - not a valid post")
                    continue
                
                # Extract post data with improved methods
                post_data = await self._extract_post_data(element, post_type, count)
                
                if post_data and (post_data.get("content") or post_data.get("media")):
                    posts_list.append(post_data)
                    count += 1
                    content_preview = post_data.get("content", "")[:50] + "..." if post_data.get("content") else "media only"
                    print(f"✅ Extracted post {count}: {content_preview}")
                else:
                    print(f"⚠️ Skipping empty post {i+1}")
                    
            except Exception as e:
                print(f"⚠️ Error extracting post {i+1}: {e}")
                continue
        
        print(f"✅ Extracted {len(posts_list)} {post_type} posts")
        return posts_list

    async def _is_valid_post(self, element) -> bool:
        """Enhanced post validation with multiple indicators"""
        try:
            # Check for post indicators
            post_indicators = [
                'div:has-text("ago")',  # Timestamp
                'a[href*="/posts/"]',   # Post link
                'a[href*="/permalink/"]',  # Permalink
                'div[data-ad-preview="message"]',  # Post content
                'span[dir="auto"]',     # Text content
                'div[role="button"]:has-text("Like")',  # Like button
                'div[role="button"]:has-text("Comment")',  # Comment button
                'div[role="button"]:has-text("Share")',  # Share button
                'img[src*="scontent"]',  # Facebook CDN images
                'video',  # Video content
            ]
            
            indicator_count = 0
            for indicator in post_indicators:
                try:
                    indicator_elem = await element.query_selector(indicator)
                    if indicator_elem:
                        indicator_count += 1
                except Exception:
                    continue
            
            # Need at least 2 indicators for a valid post
            if indicator_count >= 2:
                print(f"✅ Valid post found with {indicator_count} indicators")
                return True
            
            # Additional check for text content
            text_content = await element.text_content()
            if text_content and len(text_content.strip()) > 20:
                # Check if it's not just navigation text
                nav_patterns = [
                    "add friend", "message", "follow", "see all", "more options",
                    "photos", "videos", "about", "friends", "timeline"
                ]
                
                is_nav = any(pattern in text_content.lower() for pattern in nav_patterns)
                if not is_nav:
                    print(f"✅ Valid post found with text content")
                    return True
            
            return False
            
        except Exception as e:
            print(f"⚠️ Error validating post: {e}")
            return False

    async def _extract_post_data(self, element, post_type: str, count: int) -> Dict[str, Any]:
        """Extract comprehensive post data"""
        try:
            # Extract post ID
            post_id = await self._extract_post_id_improved(element)
            
            # Extract timestamp
            timestamp = await self._extract_timestamp_improved(element)
            
            # Extract content
            content = await self._extract_content_improved(element)
            
            # Extract author (for tagged posts)
            author = await self._extract_author_improved(element) if post_type == "tagged" else ""
            
            # Extract comments
            comments = await self._extract_comments_improved(element)
            
            # Extract reactions
            reactions_count = await self._extract_reactions_improved(element)
            
            # Extract media
            media_links = await self._extract_media_improved(element)
            
            # Take screenshot (commented out)
            screenshot_path = ""
            # try:
            #     screenshot_path = await self.utils.take_screenshot(
            #         f"{post_type}_post_{count}_{post_id}" if post_id else f"{post_type}_post_{count}"
            #     )
            # except Exception as e:
            #     print(f"⚠️ Could not take screenshot: {e}")
            
            post_data = {
                "id": post_id,
                "timestamp": self.utils.clean_text(timestamp),
                "content": self.utils.clean_text(content),
                "caption": "",
                "media_screenshot_url": screenshot_path,
                "original_url": f"https://facebook.com/posts/{post_id}" if post_id else "",
                "tagged_accounts": [],
                "location_tagged": "",
                "comments": comments,
                "reactions_count": reactions_count,
                "media": media_links
            }
            
            if author:
                post_data["author"] = author
            
            return post_data
            
        except Exception as e:
            print(f"⚠️ Error extracting post data: {e}")
            return {}

    async def _extract_post_id_improved(self, element) -> str:
        """Extract post ID with improved strategies"""
        post_id_selectors = [
            'a[href*="/posts/"]',
            'a[href*="/permalink/"]',
            'a[href*="/story"]',
            'a[href*="story_fbid"]',
            'a[href*="fbid"]',
        ]
        
        for selector in post_id_selectors:
            try:
                post_link = await element.query_selector(selector)
                if post_link:
                    href = await post_link.get_attribute('href')
                    if href:
                        # Extract ID from different URL patterns
                        patterns = [
                            r'/posts/(\d+)',
                            r'/permalink/(\d+)',
                            r'story_fbid=(\d+)',
                            r'fbid=(\d+)',
                            r'/story/(\d+)',
                        ]
                        
                        for pattern in patterns:
                            match = re.search(pattern, href)
                            if match:
                                return match.group(1)
            except Exception:
                continue
        
        return ""

    async def _extract_timestamp_improved(self, element) -> str:
        """Extract timestamp with improved strategies"""
        timestamp_selectors = [
            'a[href*="/posts/"] span',
            'a[href*="/permalink/"] span',
            'span:has-text("ago")',
            'span[aria-label*="ago"]',
            'time',
            'a[role="link"]:has-text("ago")',
            'div:has-text("ago")',
        ]
        
        for selector in timestamp_selectors:
            try:
                time_element = await element.query_selector(selector)
                if time_element:
                    timestamp = await time_element.text_content()
                    if timestamp and ("ago" in timestamp or "at" in timestamp or "·" in timestamp):
                        # Clean up timestamp
                        timestamp = timestamp.strip()
                        if "·" in timestamp:
                            # Handle format like "John Doe · 2 hours ago"
                            timestamp = timestamp.split("·")[-1].strip()
                        return timestamp
            except Exception:
                continue
        
        return ""

    async def _extract_content_improved(self, element) -> str:
        """Extract post content with improved strategies and better text filtering"""
        content_selectors = [
            'div[data-ad-comet-preview="message"]',
            'div[data-ad-preview="message"]',
            'div[data-testid="post_message"]',
            'div[data-testid="post_message"] span',
            'div[dir="auto"]',
            'span[dir="auto"]',
            'div[data-testid="story-subtitle"]',
            'div[role="button"] span[dir="auto"]',
        ]
        
        for selector in content_selectors:
            try:
                content_elements = await element.query_selector_all(selector)
                for content_element in content_elements:
                    content = await content_element.text_content()
                    if content and len(content.strip()) > 10:
                        # Filter out common non-content text
                        invalid_content_patterns = [
                            "like", "comment", "share", "react", "see more", "see less",
                            "follow", "following", "friend", "message", "more",
                            "photos", "videos", "posts", "about", "timeline",
                            "suggested for you", "sponsored", "ad", "promoted",
                            "add friend", "mutual friends", "view profile"
                        ]
                        
                        # Check if content is meaningful
                        content_lower = content.lower().strip()
                        
                        # Skip if content is just a single word that matches invalid patterns
                        if content_lower in invalid_content_patterns:
                            continue
                        
                        # Skip if content is mostly invalid patterns
                        invalid_count = sum(1 for pattern in invalid_content_patterns if pattern in content_lower)
                        if invalid_count > 2:  # Allow some common words
                            continue
                        
                        # Must have some alphabetic content
                        if not any(char.isalpha() for char in content):
                            continue
                        
                        return content.strip()
            except Exception:
                continue
        
        return ""

    async def _extract_author_improved(self, element) -> str:
        """Extract post author with improved strategies"""
        author_selectors = [
            'h3 a span',
            'h3 span[dir="auto"]',
            'strong a',
            'div[role="button"] span[dir="auto"]',
            'a[role="link"] span[dir="auto"]',
            'span[dir="auto"]:first-child',
        ]
        
        for selector in author_selectors:
            try:
                author_element = await element.query_selector(selector)
                if author_element:
                    author = await author_element.text_content()
                    if author and len(author.strip()) > 1:
                        # Filter out non-author text
                        if not any(x in author.lower() for x in [
                            "ago", "like", "comment", "share", "follow", "friend"
                        ]):
                            return author.strip()
            except Exception:
                continue
        
        return ""

    async def _extract_reactions_improved(self, element) -> int:
        """Extract reactions count with improved strategies"""
        reactions_selectors = [
            'div[aria-label*="reactions"]',
            'span[aria-label*="reactions"]',
            'div:has-text("Like")',
            'span:has-text("Like")',
            'div[role="button"]:has-text("Like")',
            'span[aria-label*="people reacted"]',
        ]
        
        for selector in reactions_selectors:
            try:
                reactions_element = await element.query_selector(selector)
                if reactions_element:
                    reactions_text = await reactions_element.text_content()
                    if reactions_text:
                        # Extract numbers from text
                        numbers = re.findall(r'\d+', reactions_text)
                        if numbers:
                            return int(numbers[0])
                    
                    # Check aria-label for reaction count
                    aria_label = await reactions_element.get_attribute('aria-label')
                    if aria_label:
                        numbers = re.findall(r'\d+', aria_label)
                        if numbers:
                            return int(numbers[0])
            except Exception:
                continue
        
        return 0

    async def _extract_media_improved(self, element) -> List[str]:
        """Extract media links with improved strategies"""
        media_links = []
        
        media_selectors = [
            'a[href*="/photos/"] img',
            'img[src*="scontent"]',
            'img[src*="fbcdn"]',
            'video',
            'video source',
        ]
        
        for selector in media_selectors:
            try:
                media_elements = await element.query_selector_all(selector)
                for media_elem in media_elements:
                    if 'img' in selector:
                        src = await media_elem.get_attribute('src')
                        if src and ('scontent' in src or 'fbcdn' in src):
                            media_links.append(src)
                    elif 'video' in selector:
                        src = await media_elem.get_attribute('src')
                        if src:
                            media_links.append(src)
            except Exception:
                continue
        
        # Remove duplicates
        return list(set(media_links))

    async def _extract_comments_improved(self, post_element) -> List[Dict[str, Any]]:
        """Extract comments with improved selectors and validation"""
        comments_list = []
        
        try:
            print("🔍 Extracting comments with improved detection...")
            
            # Comprehensive comment selectors
            comment_selectors = [
                'div[role="article"] ul > li',
                'div[data-testid*="comment"]',
                'div[aria-label*="Comment"]',
                'ul[role="list"] > li',
                'div[data-testid="UFI2Comment/root"]',
                'div[data-testid="comment_text"]',
            ]
            
            comments_elements = []
            for selector in comment_selectors:
                try:
                    elements = await post_element.query_selector_all(selector)
                    if elements:
                        comments_elements.extend(elements)
                        print(f"✅ Found {len(elements)} comment elements with selector: {selector}")
                except Exception as e:
                    print(f"⚠️ Comment selector {selector} failed: {e}")
                    continue
            
            # Remove duplicates
            seen = set()
            unique_comments = []
            for element in comments_elements:
                element_id = id(element)
                if element_id not in seen:
                    seen.add(element_id)
                    unique_comments.append(element)
            
            comments_elements = unique_comments
            print(f"📊 Total unique comment elements: {len(comments_elements)}")
            
            if not comments_elements:
                print("⚠️ No comment elements found")
                return []
            
            for i, comment_elem in enumerate(comments_elements):
                if len(comments_list) >= 10:  # Limit comments
                    break
                    
                try:
                    # Extract comment data
                    comment_data = await self._extract_comment_data(comment_elem)
                    
                    if comment_data and comment_data.get("author") and comment_data.get("text"):
                        comments_list.append(comment_data)
                        print(f"✅ Extracted comment {len(comments_list)}: {comment_data['author']} - {comment_data['text'][:30]}...")
                    else:
                        print(f"⚠️ Skipping comment {i+1} - insufficient data")
                        
                except Exception as e:
                    print(f"⚠️ Error extracting comment {i+1}: {e}")
                    continue
            
            print(f"✅ Extracted {len(comments_list)} comments total")
            return comments_list
            
        except Exception as e:
            print(f"❌ Error in comment extraction: {e}")
            return []

    async def _extract_comment_data(self, comment_elem) -> Dict[str, Any]:
        """Extract individual comment data"""
        try:
            # Get commenter name
            name = ""
            name_selectors = [
                'a[role="link"] span',
                'strong a',
                'h4 a span',
                'a span[dir="auto"]',
                'span[dir="auto"]:first-child',
            ]
            
            for name_selector in name_selectors:
                try:
                    name_element = await comment_elem.query_selector(name_selector)
                    if name_element:
                        name = await name_element.text_content()
                        if name and len(name.strip()) > 1:
                            break
                except Exception:
                    continue
            
            # Get comment text
            text = ""
            text_selectors = [
                'div[dir="auto"]',
                'span[dir="auto"]',
                'div[data-testid*="comment_text"]',
                'div[data-testid="UFI2Comment/body"]',
            ]
            
            for text_selector in text_selectors:
                try:
                    text_elements = await comment_elem.query_selector_all(text_selector)
                    for text_element in text_elements:
                        potential_text = await text_element.text_content()
                        if potential_text and len(potential_text.strip()) > 3:
                            # Skip if it's just the name repeated
                            if name.lower() not in potential_text.lower() or len(potential_text) > len(name) * 2:
                                text = potential_text.strip()
                                break
                    if text:
                        break
                except Exception:
                    continue
            
            # Get timestamp
            timestamp = ""
            time_selectors = [
                'span[role="link"] > span',
                'a[role="link"]:has-text("ago")',
                'span:has-text("ago")',
                'time',
            ]
            
            for time_selector in time_selectors:
                try:
                    time_element = await comment_elem.query_selector(time_selector)
                    if time_element:
                        timestamp = await time_element.text_content()
                        if timestamp and ("ago" in timestamp or "at" in timestamp):
                            break
                except Exception:
                    continue
            
            return {
                "author": self.utils.clean_text(name),
                "text": self.utils.clean_text(text),
                "timestamp": self.utils.clean_text(timestamp)
            }
            
        except Exception as e:
            print(f"⚠️ Error extracting comment data: {e}")
            return {}

    async def get_user_comments(self, username: str, max_comments: int = 20) -> List[Dict[str, Any]]:
        """Attempt to find comments made by the user on other posts"""
        # This is challenging as Facebook doesn't have a dedicated section for this
        # We'll try to check recent activity for comments
        try:
            # Check if page/browser is still available
            if not self.page or self.page.is_closed():
                print("Page is closed, cannot get user comments")
                return []
                
            print(f"Accessing user comments for {username}")
            # Navigate to profile using helper function
            profile_url = self._construct_profile_url(username)
            await self.page.goto(profile_url, wait_until="domcontentloaded", timeout=90000)
            await asyncio.sleep(3)  # Wait for page to stabilize
            
            # Check if we can access the activity log
            activity_link = await self.page.query_selector('a[href*="/allactivity"]')
            if not activity_link:
                print("Activity log not accessible")
                return []
                
            await activity_link.click()
            await asyncio.sleep(3)
            await self.page.wait_for_load_state("domcontentloaded", timeout=30000)
            
            # Look for comments filter if available
            comments_filter = await self.page.query_selector('span:text("Comments")')
            if comments_filter:
                await comments_filter.click()
                await asyncio.sleep(3)
            
            # Take screenshot of activity
            # await self.utils.take_screenshot("user_comments")
            
            # Extract comment data
            comments_list = []
            comment_elements = await self.page.query_selector_all('div[role="article"]')
            
            count = 0
            for element in comment_elements:
                if count >= max_comments:
                    break
                    
                try:
                    # Check if this is a comment activity
                    header = await element.query_selector('div:has-text("commented on")')
                    if not header:
                        continue
                    
                    # Extract comment content
                    content_element = await element.query_selector('div[dir="auto"]')
                    if not content_element:
                        continue
                        
                    content = await content_element.text_content()
                    
                    # Extract post info
                    post_info_element = await element.query_selector('a[href*="/posts/"]')
                    post_info = ""
                    post_url = ""
                    
                    if post_info_element:
                        post_info = await post_info_element.text_content()
                        post_url = await post_info_element.get_attribute('href')
                    
                    # Extract timestamp
                    time_element = await element.query_selector('a[href*="?log_filter="] > span')
                    timestamp = await time_element.text_content() if time_element else ""
                    
                    comments_list.append({
                        "content": self.utils.clean_text(content),
                        "post_info": self.utils.clean_text(post_info),
                        "post_url": post_url,
                        "timestamp": self.utils.clean_text(timestamp)
                    })
                    count += 1
                except Exception as e:
                    print(f"Error extracting user comment: {e}")
                    continue
            
            print(f"Extracted {len(comments_list)} user comments")
            return comments_list
            
        except Exception as e:
            print(f"Error accessing user comments: {e}")
            return []
    
    async def get_locations(self, username: str) -> List[Dict[str, Any]]:
        """Scrape locations where the user has been tagged or checked in"""
        try:
            # Check if page/browser is still available
            if not self.page or self.page.is_closed():
                print("Page is closed, cannot get locations")
                return []
                
            # Navigate to map/locations if available with better timeout handling
            # Construct appropriate locations URL using helper function
            locations_url = self._construct_profile_url(username, "map")
            print(f"Navigating to locations: {locations_url}")
            await self.page.goto(locations_url, wait_until="domcontentloaded", timeout=90000)
            await asyncio.sleep(5)  # Wait for page to stabilize
            
            # Check if map page exists
            no_content = await self.page.query_selector('div:text-matches("This content isn\'t available|No locations to show")')
            if no_content:
                print("No locations content available")
                return []
                
            # Take screenshot of map view
            # await self.utils.take_screenshot("locations_map")
            
            # Extract locations with better filtering
            locations_list = []
            location_elements = await self.page.query_selector_all('div[role="main"] > div > div > div > div')
            
            for element in location_elements:
                try:
                    name_element = await element.query_selector('span[dir="auto"]')
                    if not name_element:
                        continue
                    
                    name = await name_element.text_content()
                    
                    if not name or len(name.strip()) < 3:
                        continue
                    
                    name = name.strip()
                    
                    # Filter out navigation elements and invalid location names
                    invalid_locations = [
                        "more", "check-ins", "map", "places", "locations",
                        "see all", "show", "hide", "view", "edit", "delete",
                        "add", "remove", "settings", "privacy", "help",
                        "about", "home", "profile", "photos", "videos",
                        username.lower() if username else ""
                    ]
                    
                    # Skip obvious navigation text
                    if any(invalid in name.lower() for invalid in invalid_locations):
                        continue
                    
                    # Skip if it's just numbers or symbols
                    if name.isdigit() or all(not char.isalpha() for char in name):
                        continue
                    
                    # Skip if it's all uppercase and long (likely navigation)
                    if name.isupper() and len(name) > 10:
                        continue
                    
                    # Try to extract additional information
                    details_element = await element.query_selector('div > div > span')
                    details = await details_element.text_content() if details_element else ""
                    
                    # Clean and validate details too
                    if details:
                        details = details.strip()
                        if any(invalid in details.lower() for invalid in invalid_locations):
                            details = ""
                    
                    # Only add if name looks like a real location
                    if name and any(char.isalpha() for char in name):
                        location_data = {
                            "place": self.utils.clean_text(name),
                            "timestamp": self.utils.clean_text(details) if details else ""
                        }
                        
                        # Avoid duplicates
                        if not any(loc["place"] == location_data["place"] for loc in locations_list):
                            locations_list.append(location_data)
                            
                except Exception as e:
                    print(f"Error extracting location info: {e}")
                    continue
            
            print(f"Extracted {len(locations_list)} locations")
            return locations_list
            
        except Exception as e:
            print(f"Error getting locations: {e}")
            return []