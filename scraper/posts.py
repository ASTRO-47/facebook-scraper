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

    async def get_own_posts(self, username: str, max_posts: int = 10) -> List[Dict[str, Any]]:
        """Scrape user's own posts with improved selectors and error handling"""
        try:
            print("🔍 Extracting own posts...")
            
            # Check if page/browser is still available
            if not self.page or self.page.is_closed():
                print("❌ Page is closed, cannot get own posts")
                return []
                
            # Navigate to profile with better timeout handling
            profile_url = f"https://www.facebook.com/{username}"
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
            
            # Scroll to load more posts
            print("📜 Scrolling to load more posts...")
            await self.utils.scroll_to_bottom(5)
            
            # Expand all comments if possible
            await self.utils.click_see_more_buttons()
            
            # Extract posts
            return await self._extract_posts(max_posts, "own")
            
        except Exception as e:
            print(f"❌ Error getting own posts: {e}")
            return []

    async def get_tagged_posts(self, username: str, max_posts: int = 10) -> List[Dict[str, Any]]:
        """Scrape posts where the user is tagged with improved selectors"""
        try:
            print("🔍 Extracting tagged posts...")
            
            # Check if page/browser is still available
            if not self.page or self.page.is_closed():
                print("❌ Page is closed, cannot get tagged posts")
                return []
                
            # Navigate to tagged posts with better timeout handling
            tagged_url = f"https://www.facebook.com/{username}/photos_of"
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
            await self.utils.scroll_to_bottom(3)
            
            # Extract posts
            return await self._extract_posts(max_posts, "tagged")
            
        except Exception as e:
            print(f"❌ Error getting tagged posts: {e}")
            return []

    async def _extract_posts(self, max_posts: int, post_type: str) -> List[Dict[str, Any]]:
        """Helper method to extract post information with improved selectors"""
        posts_list = []
        
        print(f"🔍 Looking for {post_type} posts...")
        
        # Multiple strategies for finding posts
        post_selectors = [
            'div[role="article"]',
            'div[data-pagelet*="FeedUnit"]',
            'div[data-testid*="post"]',
            'div[data-ad-preview="message"]',  # Fallback for post content
        ]
        
        post_elements = []
        for selector in post_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                print(f"🔍 Found {len(elements)} elements with selector: {selector}")
                if elements:
                    post_elements = elements
                    break
            except Exception as e:
                print(f"⚠️ Post selector {selector} failed: {e}")
                continue
        
        if not post_elements:
            print("❌ No post elements found with any selector")
            return []
        
        count = 0
        for i, element in enumerate(post_elements):
            if count >= max_posts:
                break
                
            try:
                print(f"🔍 Processing post element {i+1}/{len(post_elements)}...")
                
                # Check if this is a proper post (some articles are for ads)
                # Use multiple patterns to identify valid posts
                valid_post = False
                
                post_indicators = [
                    'div:has-text("ago")',  # Timestamp indicator
                    'a[href*="/posts/"]',   # Post link
                    'div[data-ad-preview="message"]',  # Post content
                    'span[dir="auto"]',     # Text content
                ]
                
                for indicator in post_indicators:
                    try:
                        indicator_elem = await element.query_selector(indicator)
                        if indicator_elem:
                            valid_post = True
                            print(f"✅ Valid post found with indicator: {indicator}")
                            break
                    except Exception:
                        continue
                
                if not valid_post:
                    print(f"⚠️ Skipping element {i+1} - not a valid post")
                    continue
                
                # Extract post ID for unique identification
                post_id = await self._extract_post_id(element)
                
                # Extract timestamp
                timestamp = await self._extract_timestamp(element)
                
                # Extract post content
                content = await self._extract_content(element)
                
                # Extract post author (for tagged posts)
                author = await self._extract_author(element) if post_type == "tagged" else ""
                
                # Take screenshot of the post
                screenshot_path = await self.utils.take_screenshot(
                    f"{post_type}_post_{count}_{post_id}" if post_id else f"{post_type}_post_{count}",
                    element
                )
                
                # Extract comments
                comments = await self._extract_comments(element)
                
                # Extract reactions count (likes, etc.)
                reactions_count = await self._extract_reactions(element)
                
                # Collect media links if present
                media_links = await self._extract_media(element)
                
                # Skip empty posts or promotional content
                if (content or media_links) and "Suggested for you" not in timestamp:
                    post_data = {
                        "id": post_id,
                        "timestamp": self.utils.clean_text(timestamp),
                        "content": self.utils.clean_text(content),
                        "caption": "",  # Could be extracted separately if needed
                        "media_screenshot_url": screenshot_path,
                        "original_url": f"https://facebook.com/posts/{post_id}" if post_id else "",
                        "tagged_accounts": [],  # Could be extracted if needed
                        "location_tagged": "",  # Could be extracted if needed
                        "comments": comments,
                        "reactions_count": reactions_count,
                        "media": media_links
                    }
                    
                    if author:
                        post_data["author"] = author
                    
                    posts_list.append(post_data)
                    count += 1
                    print(f"✅ Extracted post {count}: {content[:50]}..." if content else f"✅ Extracted post {count} (media only)")
                else:
                    print(f"⚠️ Skipping empty or promotional post")
                    
            except Exception as e:
                print(f"⚠️ Error extracting post {i+1}: {e}")
                continue
        
        print(f"✅ Extracted {len(posts_list)} {post_type} posts")
        return posts_list

    async def _extract_post_id(self, element) -> str:
        """Extract post ID with multiple strategies"""
        post_id_selectors = [
            'a[href*="/posts/"]',
            'a[href*="/permalink/"]',
            'a[href*="/story"]',
        ]
        
        for selector in post_id_selectors:
            try:
                post_link = await element.query_selector(selector)
                if post_link:
                    href = await post_link.get_attribute('href')
                    if href:
                        # Extract ID from different URL patterns
                        match = re.search(r'/posts/(\d+)', href)
                        if match:
                            return match.group(1)
                        match = re.search(r'/permalink/(\d+)', href)
                        if match:
                            return match.group(1)
                        match = re.search(r'story_fbid=(\d+)', href)
                        if match:
                            return match.group(1)
            except Exception:
                continue
        
        return ""

    async def _extract_timestamp(self, element) -> str:
        """Extract timestamp with multiple strategies"""
        timestamp_selectors = [
            'a[href*="/posts/"] span',
            'a[href*="/permalink/"] span',
            'span:has-text("ago")',
            'span[aria-label*="ago"]',
            'time',
        ]
        
        for selector in timestamp_selectors:
            try:
                time_element = await element.query_selector(selector)
                if time_element:
                    timestamp = await time_element.text_content()
                    if timestamp and ("ago" in timestamp or "at" in timestamp):
                        return timestamp
            except Exception:
                continue
        
        return ""

    async def _extract_content(self, element) -> str:
        """Extract post content with multiple strategies"""
        content_selectors = [
            'div[data-ad-comet-preview="message"]',
            'div[data-ad-preview="message"]',
            'div[data-testid="post_message"]',
            'span[dir="auto"]',  # Generic text content
            'div[dir="auto"]',
        ]
        
        for selector in content_selectors:
            try:
                content_elements = await element.query_selector_all(selector)
                for content_element in content_elements:
                    content = await content_element.text_content()
                    if content and len(content.strip()) > 10:  # Min length to avoid false positives
                        return content
            except Exception:
                continue
        
        return ""

    async def _extract_author(self, element) -> str:
        """Extract post author for tagged posts"""
        author_selectors = [
            'h3 a span',
            'strong a',
            'div[role="button"] span[dir="auto"]',
        ]
        
        for selector in author_selectors:
            try:
                author_element = await element.query_selector(selector)
                if author_element:
                    author = await author_element.text_content()
                    if author and len(author.strip()) > 1:
                        return author
            except Exception:
                continue
        
        return ""

    async def _extract_reactions(self, element) -> int:
        """Extract reactions count with multiple strategies"""
        reactions_selectors = [
            'div[aria-label*="reactions"]',
            'span[aria-label*="reactions"]',
            'div:has-text("Like")',
            'span:has-text("Like")',
        ]
        
        for selector in reactions_selectors:
            try:
                reactions_element = await element.query_selector(selector)
                if reactions_element:
                    reactions_text = await reactions_element.text_content()
                    numbers = re.findall(r'\d+', reactions_text)
                    if numbers:
                        return int(numbers[0])
            except Exception:
                continue
        
        return 0

    async def _extract_media(self, element) -> List[str]:
        """Extract media links with multiple strategies"""
        media_links = []
        
        media_selectors = [
            'a[href*="/photos/"] img',
            'img[src*="scontent"]',  # Facebook CDN images
            'video',
        ]
        
        for selector in media_selectors:
            try:
                media_elements = await element.query_selector_all(selector)
                for media_elem in media_elements:
                    if selector.endswith('img'):
                        src = await media_elem.get_attribute('src')
                        if src and 'scontent' in src:  # Facebook CDN
                            media_links.append(src)
                    elif selector == 'video':
                        src = await media_elem.get_attribute('src')
                        if src:
                            media_links.append(src)
            except Exception:
                continue
        
        return media_links
    
    async def _extract_comments(self, post_element) -> List[Dict[str, Any]]:
        """Extract comments from a post with improved selectors"""
        comments_list = []
        
        print("🔍 Extracting comments...")
        
        # Multiple strategies for finding comments
        comment_selectors = [
            'div[role="article"] ul > li',  # Standard comment structure
            'div[data-testid*="comment"]',  # Comment test IDs
            'div[aria-label*="Comment"]',   # Comments with aria labels
            'ul[role="list"] > li',         # List of comments
        ]
        
        comments_elements = []
        for selector in comment_selectors:
            try:
                elements = await post_element.query_selector_all(selector)
                if elements:
                    comments_elements = elements
                    print(f"✅ Found {len(elements)} comment elements with selector: {selector}")
                    break
            except Exception as e:
                print(f"⚠️ Comment selector {selector} failed: {e}")
                continue
        
        if not comments_elements:
            print("⚠️ No comment elements found")
            return []
        
        for i, comment_elem in enumerate(comments_elements):
            try:
                # Get commenter name with multiple strategies
                name = ""
                name_selectors = [
                    'a[role="link"] span',
                    'strong a',
                    'h4 a span',
                    'a span[dir="auto"]',
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
                
                if not name:
                    print(f"⚠️ Skipping comment {i+1} - no name found")
                    continue
                
                # Get comment text with multiple strategies
                text = ""
                text_selectors = [
                    'div[dir="auto"]',
                    'span[dir="auto"]',
                    'div[data-testid*="comment_text"]',
                ]
                
                for text_selector in text_selectors:
                    try:
                        text_elements = await comment_elem.query_selector_all(text_selector)
                        for text_element in text_elements:
                            potential_text = await text_element.text_content()
                            if potential_text and len(potential_text.strip()) > 3:
                                # Skip if it's just the name repeated
                                if name.lower() not in potential_text.lower() or len(potential_text) > len(name) * 2:
                                    text = potential_text
                                    break
                        if text:
                            break
                    except Exception:
                        continue
                
                # Get timestamp with multiple strategies
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
                
                # Only add comment if we have meaningful content
                if name and (text or timestamp):
                    comment_data = {
                        "author": self.utils.clean_text(name),
                        "text": self.utils.clean_text(text),
                        "timestamp": self.utils.clean_text(timestamp)
                    }
                    comments_list.append(comment_data)
                    print(f"✅ Extracted comment {len(comments_list)}: {name} - {text[:30]}...")
                else:
                    print(f"⚠️ Skipping comment {i+1} - insufficient data")
                    
            except Exception as e:
                print(f"⚠️ Error extracting comment {i+1}: {e}")
                continue
        
        print(f"✅ Extracted {len(comments_list)} comments total")
        return comments_list[:10]  # Limit to prevent excessive data
    
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
            await self.page.goto(f"https://www.facebook.com/{username}", wait_until="domcontentloaded", timeout=90000)
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
            await self.utils.take_screenshot("user_comments")
            
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
            locations_url = f"https://www.facebook.com/{username}/map"
            print(f"Navigating to locations: {locations_url}")
            await self.page.goto(locations_url, wait_until="domcontentloaded", timeout=90000)
            await asyncio.sleep(5)  # Wait for page to stabilize
            
            # Check if map page exists
            no_content = await self.page.query_selector('div:text-matches("This content isn\'t available|No locations to show")')
            if no_content:
                print("No locations content available")
                return []
                
            # Take screenshot of map view
            await self.utils.take_screenshot("locations_map")
            
            # Extract locations
            locations_list = []
            location_elements = await self.page.query_selector_all('div[role="main"] > div > div > div > div')
            
            for element in location_elements:
                try:
                    name_element = await element.query_selector('span[dir="auto"]')
                    if not name_element:
                        continue
                    
                    name = await name_element.text_content()
                    
                    # Try to extract additional information
                    details_element = await element.query_selector('div > div > span')
                    details = await details_element.text_content() if details_element else ""
                    
                    if name:
                        locations_list.append({
                            "name": self.utils.clean_text(name),
                            "details": self.utils.clean_text(details)
                        })
                except Exception as e:
                    print(f"Error extracting location info: {e}")
                    continue
            
            print(f"Extracted {len(locations_list)} locations")
            return locations_list
            
        except Exception as e:
            print(f"Error getting locations: {e}")
            return []