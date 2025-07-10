"""
Functions for scraping Facebook profile data
"""
import asyncio
import re
from typing import Dict, List, Any, Optional
from playwright.async_api import Page

from .utils import ScraperUtils

class ProfileScraper:
    def __init__(self, page: Page, utils: ScraperUtils):
        self.page = page
        self.utils = utils
        self.original_username = None  # Store the original username

    def _extract_username_from_url(self, url: str) -> Optional[str]:
        """Extract username from Facebook URL"""
        try:
            if "/profile.php" in url:
                # Handle numeric profile IDs
                import re
                match = re.search(r'profile\.php\?id=(\d+)', url)
                if match:
                    return f"profile.php?id={match.group(1)}"
            else:
                # Handle username-based profiles
                return url.split('facebook.com/')[-1].split('/')[0].split('?')[0]
        except Exception:
            return None
        return None

    async def navigate_to_profile(self, username):
        """Navigate to a user's profile page"""
        try:
            # Store the original username for later use
            self.original_username = username
            
            # Navigate to the profile with better timeout handling
            profile_url = f"https://www.facebook.com/{username}"
            print(f"Navigating to {profile_url}")
            
            # Use domcontentloaded with longer timeout for better reliability
            await self.page.goto(profile_url, wait_until="domcontentloaded", timeout=120000)
            print("Page loaded, waiting for content to settle...")
            await asyncio.sleep(10)  # Wait for dynamic content and potential redirects
            
            # Wait for main content to load with multiple fallback selectors and longer timeout
            content_loaded = False
            selectors_to_try = [
                "div[role='main']",
                "[data-pagelet='ProfileTilesFeed']",
                "[data-pagelet='ProfileTimeline']", 
                "div[data-pagelet='ProfileActions']",
                "h1"  # fallback for any h1 on the page
            ]
            
            for selector in selectors_to_try:
                try:
                    await self.page.wait_for_selector(selector, timeout=15000)
                    print(f"Found content using selector: {selector}")
                    content_loaded = True
                    break
                except:
                    print(f"Selector {selector} not found, trying next...")
                    continue
            
            if not content_loaded:
                print("⚠️ No expected selectors found, but continuing anyway...")
            
            # Check if we landed on an error page or got redirected
            current_url = self.page.url
            if "facebook.com" not in current_url or "error" in current_url.lower():
                print(f"⚠️ Unexpected redirect to: {current_url}")
                return False
            
            # Check for security checkpoint before proceeding
            checkpoint_detected = await self.utils.check_for_security_checkpoint()
            if checkpoint_detected:
                print("🔒 Security checkpoint detected during navigation!")
                await self.utils.handle_security_checkpoint(wait_time=120)
                # Wait extra time after checkpoint resolution
                await asyncio.sleep(5)
        
            # Take a screenshot of the profile for debugging
            screenshot_path = await self.utils.take_screenshot(f"profile_{username}")
            print(f"📸 Profile screenshot saved: {screenshot_path}")
            
            print(f"✅ Successfully navigated to profile: {username}")
            return True
            
        except Exception as e:
            print(f"❌ Error navigating to profile: {str(e)}")
            # Take a screenshot of the error for debugging
            try:
                await self.utils.take_screenshot(f"error_profile_{username}")
            except:
                pass
            return False

    async def get_basic_info(self) -> Dict[str, Any]:
        """Extract basic profile information"""
        try:
            # Take screenshot of profile header
            screenshot_path = await self.utils.take_screenshot("profile_header", "div[role='main']")
            
            # Get profile name with better error handling
            name_element = await self.page.query_selector('h1')
            name = await name_element.text_content() if name_element else "Unknown"
            
            # Get bio if available
            bio_element = await self.page.query_selector('div[role="main"] > div > div > div > div > div > div > span')
            bio = await bio_element.text_content() if bio_element else ""
            
            # Try to navigate to About page with better error handling
            try:
                about_link = await self.page.query_selector('a[href*="/about"]')
                if about_link:
                    await about_link.click()
                    await asyncio.sleep(3)
                    # Wait for about page to load
                    await self.page.wait_for_load_state("domcontentloaded", timeout=30000)
                else:
                    print("About link not found, using basic profile info only")
            except Exception as e:
                print(f"Could not navigate to about page: {e}")
                
            # Extract detailed information with fallbacks
            about_data = {}
            
            try:
                # Work and Education
                work_education = await self._extract_section_data("Work and Education")
                about_data.update(work_education)
            except Exception as e:
                print(f"Error extracting work/education: {e}")
                
            try:
                # Places Lived
                places = await self._extract_section_data("Places Lived") 
                about_data.update(places)
            except Exception as e:
                print(f"Error extracting places: {e}")
                
            try:
                # Contact Info
                contact = await self._extract_section_data("Contact Info")
                about_data.update(contact)
            except Exception as e:
                print(f"Error extracting contact info: {e}")
                
            try:
                # Basic Info (including birthday)
                basic = await self._extract_section_data("Basic Info")
                about_data.update(basic)
            except Exception as e:
                print(f"Error extracting basic info: {e}")
                
            return {
                "name": self.utils.clean_text(name),
                "bio": self.utils.clean_text(bio),
                "profile_picture": screenshot_path,
                "work": about_data.get("work", []),
                "education": about_data.get("education", []),
                "current_city": about_data.get("current_city", ""),
                "hometown": about_data.get("hometown", ""),
                "email": about_data.get("email", ""),
                "phone": about_data.get("phone", ""),
                "birthday": about_data.get("birthday", ""),
            }
            
        except Exception as e:
            print(f"Error in get_basic_info: {e}")
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
    
    async def _extract_section_data(self, section_name: str) -> Dict[str, Any]:
        """Helper method to extract data from about page sections"""
        result = {}
        
        # Click on section if not already active
        section_links = await self.page.query_selector_all(f'div[role="navigation"] a:text("{section_name}")')
        if section_links:
            await section_links[0].click()
            await asyncio.sleep(2)
        
        if section_name == "Work and Education":
            # Extract work information
            work_elements = await self.page.query_selector_all('div[role="main"] div:has(> div:text-matches("(Work|Worked)"))')
            work_list = []
            
            for element in work_elements:
                text = await element.text_content()
                if text and "Add a workplace" not in text:
                    work_list.append(self.utils.clean_text(text))
            
            result["work"] = work_list
            
            # Extract education information
            edu_elements = await self.page.query_selector_all('div[role="main"] div:has(> div:text-matches("(College|School|University|Education|Studied)"))')
            edu_list = []
            
            for element in edu_elements:
                text = await element.text_content()
                if text and "Add a school" not in text:
                    edu_list.append(self.utils.clean_text(text))
            
            result["education"] = edu_list
            
        elif section_name == "Places Lived":
            # Extract current city
            city_element = await self.page.query_selector('div[role="main"] div:has(> div:text("Current city"))')
            if city_element:
                result["current_city"] = self.utils.clean_text(await city_element.text_content())
            
            # Extract hometown
            hometown_element = await self.page.query_selector('div[role="main"] div:has(> div:text("Hometown"))')
            if hometown_element:
                result["hometown"] = self.utils.clean_text(await hometown_element.text_content())
                
        elif section_name == "Contact Info":
            # Extract email
            email_element = await self.page.query_selector('div[role="main"] div:has(> div:text("Email"))') 
            if email_element:
                text = await email_element.text_content()
                email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
                if email_match:
                    result["email"] = email_match.group(0)
            
            # Extract phone
            phone_element = await self.page.query_selector('div[role="main"] div:has(> div:text("Mobile"))') 
            if phone_element:
                text = await phone_element.text_content()
                phone_match = re.search(r'(\+\d{1,3})?[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', text)
                if phone_match:
                    result["phone"] = phone_match.group(0)
                    
        elif section_name == "Basic Info":
            # Extract birthday
            birthday_element = await self.page.query_selector('div[role="main"] div:has(> div:text("Birthday"))') 
            if birthday_element:
                text = await birthday_element.text_content()
                result["birthday"] = self.utils.clean_text(text.replace("Birthday", ""))
                
        return result

    async def get_friends_list(self, max_scrolls: int = 5) -> List[Dict[str, str]]:
        """Extract friends list"""
        try:
            # Check if page/browser is still available
            if not self.page or self.page.is_closed():
                print("Page is closed, cannot get friends list")
                return []
                
            # Get the username - use original username if available, otherwise extract from URL
            username = self.original_username or self._extract_username_from_url(self.page.url)
            
            if not username:
                print("Could not extract username from URL")
                return []
                
            # Navigate to Friends page with proper URL construction
            friends_url = f"https://www.facebook.com/{username}/friends"
            print(f"Navigating to friends page: {friends_url}")
            await self.page.goto(friends_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)  # Wait for page to stabilize
            
            # Scroll to load more friends
            await self.utils.scroll_to_bottom(max_scrolls)
            
            # Take screenshot of friends page
            await self.utils.take_screenshot("friends_list")
            
            # Extract friends information
            friends_list = []
            friend_elements = await self.page.query_selector_all('div[data-pagelet="ProfileAppSection_0"] > div > div > div > div')
            
            for element in friend_elements:
                try:
                    name_element = await element.query_selector('span[dir="auto"]')
                    if not name_element:
                        continue
                    
                    name = await name_element.text_content()
                    
                    # Try to get profile link
                    link_element = await element.query_selector('a[href*="/"]')
                    profile_url = ""
                    if link_element:
                        href = await link_element.get_attribute('href')
                        if href:
                            profile_url = href
                    
                    if name and "Add Friend" not in name:
                        friends_list.append({
                            "name": self.utils.clean_text(name),
                            "profile_url": profile_url
                        })
                except Exception as e:
                    print(f"Error extracting friend info: {e}")
                    continue
            
            print(f"Extracted {len(friends_list)} friends")
            return friends_list
            
        except Exception as e:
            print(f"Error getting friends list: {e}")
            return []

    async def get_groups(self) -> List[Dict[str, str]]:
        """Extract groups the user is a member of"""
        try:
            # Check if page/browser is still available
            if not self.page or self.page.is_closed():
                print("Page is closed, cannot get groups")
                return []
                
            # Get the username - use original username if available, otherwise extract from URL
            username = self.original_username or self._extract_username_from_url(self.page.url)
            
            if not username:
                print("Could not extract username from URL")
                return []
                
            # Navigate to Groups page with proper URL construction
            groups_url = f"https://www.facebook.com/{username}/groups"
            print(f"Navigating to groups page: {groups_url}")
            await self.page.goto(groups_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)  # Wait for page to stabilize
            
            # Check if groups page exists
            no_content = await self.page.query_selector('div:text-matches("This content isn\'t available|No groups to show")')
            if no_content:
                return []
                
            # Scroll to load more groups
            await self.utils.scroll_to_bottom(3)
            
            # Take screenshot
            await self.utils.take_screenshot("groups_list")
            
            # Extract groups information
            groups_list = []
            group_elements = await self.page.query_selector_all('div[data-pagelet*="Group"] a[href*="/groups/"]')
            
            for element in group_elements:
                try:
                    # Get group name
                    name = await element.text_content()
                    
                    # Get group URL
                    href = await element.get_attribute('href')
                    
                    if name and href and name.strip():
                        groups_list.append({
                            "name": self.utils.clean_text(name.strip()),
                            "url": href
                        })
                except Exception as e:
                    print(f"Error extracting group info: {e}")
                    continue
            
            print(f"Extracted {len(groups_list)} groups")
            return groups_list
            
        except Exception as e:
            print(f"Error getting groups: {e}")
            return []

    async def get_pages_followed(self) -> List[Dict[str, str]]:
        """Extract pages the user follows"""
        try:
            # Check if page/browser is still available
            if not self.page or self.page.is_closed():
                print("Page is closed, cannot get pages followed")
                return []
                
            # Get the username - use original username if available, otherwise extract from URL
            username = self.original_username or self._extract_username_from_url(self.page.url)
            
            if not username:
                print("Could not extract username from URL")
                return []
                
            # Navigate to Likes page with proper URL construction
            likes_url = f"https://www.facebook.com/{username}/likes"
            print(f"Navigating to likes page: {likes_url}")
            await self.page.goto(likes_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)  # Wait for page to stabilize
            
            # Check if likes page exists
            no_content = await self.page.query_selector('div:text-matches("This content isn\'t available|No pages to show")')
            if no_content:
                return []
                
            # Scroll to load more pages
            await self.utils.scroll_to_bottom(3)
            
            # Take screenshot of liked pages
            await self.utils.take_screenshot("pages_followed")
            
            # Extract pages information
            pages_list = []
            page_elements = await self.page.query_selector_all('div[role="main"] > div > div > div > div')
            
            for element in page_elements:
                try:
                    name_element = await element.query_selector('span[dir="auto"]')
                    if not name_element:
                        continue
                    
                    name = await name_element.text_content()
                    
                    # Try to get page link
                    link_element = await element.query_selector('a[href*="facebook.com"]')
                    page_url = ""
                    if link_element:
                        href = await link_element.get_attribute('href')
                        if href and not ("/likes" in href or "?ref=" in href):
                            page_url = href
                    
                    if name and page_url:
                        pages_list.append({
                            "name": self.utils.clean_text(name),
                            "url": page_url
                        })
                except Exception as e:
                    print(f"Error extracting page info: {e}")
                    continue
            
            print(f"Extracted {len(pages_list)} pages")
            return pages_list
            
        except Exception as e:
            print(f"Error getting pages: {e}")
            return []

    async def get_following_list(self) -> List[Dict[str, str]]:
        """Extract list of profiles the user is following"""
        try:
            # Check if page/browser is still available
            if not self.page or self.page.is_closed():
                print("Page is closed, cannot get following list")
                return []
                
            # Get the username - use original username if available, otherwise extract from URL
            username = self.original_username or self._extract_username_from_url(self.page.url)
            
            if not username:
                print("Could not extract username from URL")
                return []
                
            # Navigate to Following page with proper URL construction
            following_url = f"https://www.facebook.com/{username}/following"
            print(f"Navigating to following page: {following_url}")
            await self.page.goto(following_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)  # Wait for page to stabilize
            
            # Check if following page exists
            no_content = await self.page.query_selector('div:text-matches("This content isn\'t available|No pages to show")')
            if no_content:
                return []
                
            # Scroll to load more followed profiles
            await self.utils.scroll_to_bottom(3)
            
            # Take screenshot of following list
            await self.utils.take_screenshot("following_list")
            
            # Extract following information
            following_list = []
            follow_elements = await self.page.query_selector_all('div[role="main"] > div > div > div > div')
            
            for element in follow_elements:
                try:
                    name_element = await element.query_selector('span[dir="auto"]')
                    if not name_element:
                        continue
                    
                    name = await name_element.text_content()
                    
                    # Try to get profile link
                    link_element = await element.query_selector('a[href*="facebook.com"]')
                    profile_url = ""
                    if link_element:
                        href = await link_element.get_attribute('href')
                        if href and not ("/following" in href or "?ref=" in href):
                            profile_url = href
                    
                    if name and profile_url:
                        following_list.append({
                            "name": self.utils.clean_text(name),
                            "url": profile_url
                        })
                except Exception as e:
                    print(f"Error extracting following info: {e}")
                    continue
            
            print(f"Extracted {len(following_list)} following")
            return following_list
            
        except Exception as e:
            print(f"Error getting following list: {e}")
            return []