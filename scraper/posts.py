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
        """Scrape user's own posts"""
        try:
            # Check if page/browser is still available
            if not self.page or self.page.is_closed():
                print("Page is closed, cannot get own posts")
                return []
                
            # Navigate to profile with better timeout handling
            print(f"Navigating to profile for posts: https://www.facebook.com/{username}")
            await self.page.goto(f"https://www.facebook.com/{username}", wait_until="domcontentloaded", timeout=90000)
            await asyncio.sleep(5)  # Wait for page to stabilize
            
            # Scroll to load more posts
            await self.utils.scroll_to_bottom(5)
            
            # Expand all comments if possible
            await self.utils.click_see_more_buttons()
            
            # Extract posts
            return await self._extract_posts(max_posts, "own")
            
        except Exception as e:
            print(f"Error getting own posts: {e}")
            return []

    async def get_tagged_posts(self, username: str, max_posts: int = 10) -> List[Dict[str, Any]]:
        """Scrape posts where the user is tagged"""
        try:
            # Check if page/browser is still available
            if not self.page or self.page.is_closed():
                print("Page is closed, cannot get tagged posts")
                return []
                
            # Navigate to tagged posts with better timeout handling
            tagged_url = f"https://www.facebook.com/{username}/photos_of"
            print(f"Navigating to tagged posts: {tagged_url}")
            await self.page.goto(tagged_url, wait_until="domcontentloaded", timeout=90000)
            await asyncio.sleep(5)  # Wait for page to stabilize
            
            # Check if there are any tagged posts
            no_content = await self.page.query_selector('div:text-matches("No photos to show|This content isn\'t available")')
            if no_content:
                return []
            
            # Scroll to load more posts
            await self.utils.scroll_to_bottom(3)
            
            # Extract posts
            return await self._extract_posts(max_posts, "tagged")
            
        except Exception as e:
            print(f"Error getting tagged posts: {e}")
            return []

    async def _extract_posts(self, max_posts: int, post_type: str) -> List[Dict[str, Any]]:
        """Helper method to extract post information"""
        posts_list = []
        # Find post containers based on common Facebook post structure
        post_elements = await self.page.query_selector_all('div[role="article"]')
        
        count = 0
        for element in post_elements:
            if count >= max_posts:
                break
                
            try:
                # Check if this is a proper post (some articles are for ads)
                header = await element.query_selector('div:has(> h3, > h4, > div > h3, > div > h4, > div > div > h3, > div > div > h4)')
                if not header:
                    continue
                
                # Extract post ID for unique identification
                post_id = ""
                post_link = await element.query_selector('a[href*="/posts/"]')
                if post_link:
                    href = await post_link.get_attribute('href')
                    match = re.search(r'/posts/(\d+)', href)
                    if match:
                        post_id = match.group(1)
                
                # Extract timestamp
                timestamp = ""
                time_element = await element.query_selector('a[href*="/posts/"] > span')
                if time_element:
                    timestamp = await time_element.text_content()
                
                # Extract post content
                content = ""
                content_element = await element.query_selector('div[data-ad-comet-preview="message"]')
                if not content_element:
                    content_element = await element.query_selector('div[data-ad-preview="message"]')
                if not content_element:
                    # Try another selector pattern
                    content_element = await element.query_selector('div > div > div > div > div > div > span')
                
                if content_element:
                    content = await content_element.text_content()
                
                # Take screenshot of the post
                screenshot_path = await self.utils.take_screenshot(
                    f"{post_type}_post_{count}_{post_id}" if post_id else f"{post_type}_post_{count}",
                    element
                )
                
                # Extract comments
                comments = await self._extract_comments(element)
                
                # Extract reactions count (likes, etc.)
                reactions_count = 0
                reactions_element = await element.query_selector('div[aria-label*="reactions"]')
                if reactions_element:
                    reactions_text = await reactions_element.text_content()
                    numbers = re.findall(r'\d+', reactions_text)
                    if numbers:
                        reactions_count = int(numbers[0])
                
                # Collect media links if present
                media_links = []
                media_elements = await element.query_selector_all('a[href*="/photos/"] img')
                for img in media_elements:
                    src = await img.get_attribute('src')
                    if src:
                        media_links.append(src)
                
                # Skip empty posts or promotional content
                if (content or media_links) and "Suggested for you" not in timestamp:
                    posts_list.append({
                        "id": post_id,
                        "timestamp": self.utils.clean_text(timestamp),
                        "content": self.utils.clean_text(content),
                        "screenshot": screenshot_path,
                        "reactions_count": reactions_count,
                        "comments": comments,
                        "media": media_links
                    })
                    count += 1
            except Exception as e:
                print(f"Error extracting post: {e}")
                continue
        
        return posts_list
    
    async def _extract_comments(self, post_element) -> List[Dict[str, Any]]:
        """Extract comments from a post"""
        comments_list = []
        
        # Try to find the comments section
        comments_elements = await post_element.query_selector_all('div[role="article"] ul > li > div')
        
        for comment_elem in comments_elements:
            try:
                # Get commenter name
                name_element = await comment_elem.query_selector('a[role="link"] > span')
                if not name_element:
                    continue
                
                name = await name_element.text_content()
                
                # Get comment text
                text_element = await comment_elem.query_selector('div[dir="auto"]')
                text = await text_element.text_content() if text_element else ""
                
                # Get timestamp
                time_element = await comment_elem.query_selector('span[role="link"] > span')
                timestamp = await time_element.text_content() if time_element else ""
                
                comments_list.append({
                    "author": self.utils.clean_text(name),
                    "text": self.utils.clean_text(text),
                    "timestamp": self.utils.clean_text(timestamp)
                })
            except Exception as e:
                print(f"Error extracting comment: {e}")
                continue
        
        return comments_list
    
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