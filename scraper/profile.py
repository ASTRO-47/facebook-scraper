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
        """Extract basic profile information with improved selectors and fallbacks"""
        try:
            print("🔍 Extracting basic profile information...")
            
            # Take screenshot of profile header
            screenshot_path = await self.utils.take_screenshot("profile_header")
            
            # Get profile name with multiple fallback selectors
            name = await self._extract_profile_name()
            print(f"📝 Profile name: {name}")
            
            # Get bio/description with multiple fallback selectors
            bio = await self._extract_profile_bio()
            print(f"📝 Profile bio: {bio[:50]}..." if bio else "📝 No bio found")
            
            # Try to navigate to About page with better error handling
            about_data = await self._extract_about_info()
            
            result = {
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
            
            print(f"✅ Basic info extracted: {len([v for v in result.values() if v])} fields found")
            return result
            
        except Exception as e:
            print(f"❌ Error in get_basic_info: {e}")
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
            'h1[data-testid="profile-name"]',  # Modern Facebook
            'h1',  # Generic h1
            '[data-testid="profile-name"]',
            'div[role="main"] h1',
            'div[data-pagelet*="Profile"] h1',
            'span[dir="auto"]',  # Another common pattern
        ]
        
        for selector in name_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    name = await element.text_content()
                    if name and len(name.strip()) > 0:
                        print(f"✅ Found name using selector: {selector}")
                        return name.strip()
            except Exception as e:
                print(f"⚠️ Name selector {selector} failed: {e}")
                continue
        
        return "Unknown"

    async def _extract_profile_bio(self) -> str:
        """Extract profile bio/description with multiple fallback selectors"""
        bio_selectors = [
            '[data-testid="profile-bio"]',
            'div[data-pagelet*="Profile"] span[dir="auto"]',
            'div[role="main"] div > div > div > span[dir="auto"]',
            'meta[name="description"]',  # Meta description as fallback
        ]
        
        for selector in bio_selectors:
            try:
                if selector.startswith('meta'):
                    element = await self.page.query_selector(selector)
                    if element:
                        bio = await element.get_attribute('content')
                        if bio and len(bio.strip()) > 0:
                            print(f"✅ Found bio using selector: {selector}")
                            return bio.strip()
                else:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        bio = await element.text_content()
                        if bio and len(bio.strip()) > 10:  # Min length to avoid false positives
                            print(f"✅ Found bio using selector: {selector}")
                            return bio.strip()
            except Exception as e:
                print(f"⚠️ Bio selector {selector} failed: {e}")
                continue
        
        return ""

    async def _extract_about_info(self) -> Dict[str, Any]:
        """Extract detailed information from About page with improved methods"""
        about_data = {}
        
        try:
            print("🔍 Attempting to navigate to About page...")
            
            # Multiple ways to find and click About link
            about_selectors = [
                'a[href*="/about"]',
                'nav a:text("About")',
                'div[role="tablist"] a:text("About")',
                '[data-testid*="about"]',
            ]
            
            about_clicked = False
            for selector in about_selectors:
                try:
                    about_link = await self.page.query_selector(selector)
                    if about_link:
                        await about_link.click()
                        await asyncio.sleep(3)
                        await self.page.wait_for_load_state("domcontentloaded", timeout=30000)
                        print(f"✅ Navigated to About using selector: {selector}")
                        about_clicked = True
                        break
                except Exception as e:
                    print(f"⚠️ About selector {selector} failed: {e}")
                    continue
            
            if not about_clicked:
                print("⚠️ Could not navigate to About page, using main profile page")
                return about_data
            
            # Extract different types of information
            about_data.update(await self._extract_work_education())
            about_data.update(await self._extract_places())
            about_data.update(await self._extract_contact_info())
            about_data.update(await self._extract_basic_details())
            
        except Exception as e:
            print(f"❌ Error extracting about info: {e}")
        
        return about_data

    async def _extract_work_education(self) -> Dict[str, Any]:
        """Extract work and education information with improved selectors"""
        result = {}
        
        try:
            # Look for work information with multiple patterns
            work_patterns = [
                'div:has-text("Works at")',
                'div:has-text("Work")',
                'div:has-text("Worked at")',
                '[data-testid*="work"]',
            ]
            
            work_list = []
            for pattern in work_patterns:
                try:
                    elements = await self.page.query_selector_all(pattern)
                    for element in elements:
                        text = await element.text_content()
                        if text and "Add a workplace" not in text and len(text.strip()) > 5:
                            work_list.append(self.utils.clean_text(text))
                except Exception:
                    continue
            
            result["work"] = list(set(work_list))  # Remove duplicates
            
            # Look for education information
            edu_patterns = [
                'div:has-text("Studied at")',
                'div:has-text("Studies at")',
                'div:has-text("Education")',
                'div:has-text("School")',
                'div:has-text("University")',
                '[data-testid*="education"]',
            ]
            
            edu_list = []
            for pattern in edu_patterns:
                try:
                    elements = await self.page.query_selector_all(pattern)
                    for element in elements:
                        text = await element.text_content()
                        if text and "Add a school" not in text and len(text.strip()) > 5:
                            edu_list.append(self.utils.clean_text(text))
                except Exception:
                    continue
            
            result["education"] = list(set(edu_list))  # Remove duplicates
            
        except Exception as e:
            print(f"❌ Error extracting work/education: {e}")
        
        return result

    async def _extract_places(self) -> Dict[str, Any]:
        """Extract location information with improved selectors"""
        result = {}
        
        try:
            # Look for location information
            location_patterns = [
                'div:has-text("Lives in")',
                'div:has-text("From")',
                'div:has-text("Current city")',
                'div:has-text("Hometown")',
                '[data-testid*="location"]',
            ]
            
            for pattern in location_patterns:
                try:
                    elements = await self.page.query_selector_all(pattern)
                    for element in elements:
                        text = await element.text_content()
                        if text:
                            text = self.utils.clean_text(text)
                            if "Lives in" in text or "Current city" in text:
                                result["current_city"] = text.replace("Lives in", "").replace("Current city", "").strip()
                            elif "From" in text or "Hometown" in text:
                                result["hometown"] = text.replace("From", "").replace("Hometown", "").strip()
                except Exception:
                    continue
            
        except Exception as e:
            print(f"❌ Error extracting places: {e}")
        
        return result

    async def _extract_contact_info(self) -> Dict[str, Any]:
        """Extract contact information with improved patterns"""
        result = {}
        
        try:
            # Get all text content and search for patterns
            page_text = await self.page.evaluate('() => document.body.innerText')
            
            # Extract email with regex
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_matches = re.findall(email_pattern, page_text)
            if email_matches:
                result["email"] = email_matches[0]
            
            # Extract phone with regex (basic patterns)
            phone_pattern = r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
            phone_matches = re.findall(phone_pattern, page_text)
            if phone_matches:
                result["phone"] = ''.join(phone_matches[0]) if isinstance(phone_matches[0], tuple) else phone_matches[0]
            
        except Exception as e:
            print(f"❌ Error extracting contact info: {e}")
        
        return result

    async def _extract_basic_details(self) -> Dict[str, Any]:
        """Extract basic details like birthday with improved patterns"""
        result = {}
        
        try:
            # Look for birthday information
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
            print(f"❌ Error extracting basic details: {e}")
        
        return result

    async def get_friends_list(self, max_scrolls: int = 5) -> List[Dict[str, str]]:
        """Extract friends list with improved selectors and error handling"""
        try:
            print("🔍 Extracting friends list...")
            
            # Check if page/browser is still available
            if not self.page or self.page.is_closed():
                print("❌ Page is closed, cannot get friends list")
                return []
                
            # Get the username - use original username if available, otherwise extract from URL
            username = self.original_username or self._extract_username_from_url(self.page.url)
            
            if not username:
                print("❌ Could not extract username from URL")
                return []
                
            # Navigate to Friends page with proper URL construction
            friends_url = f"https://www.facebook.com/{username}/friends"
            print(f"🔗 Navigating to friends page: {friends_url}")
            await self.page.goto(friends_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)  # Wait for page to stabilize
            
            # Check for privacy restrictions
            privacy_indicators = [
                'div:text-matches("This content isn\'t available|Friends list is private|No friends to show")',
                'div:has-text("Only you can see")',
                'div:has-text("private")',
            ]
            
            for indicator in privacy_indicators:
                try:
                    privacy_element = await self.page.query_selector(indicator)
                    if privacy_element:
                        print("🔒 Friends list is private or restricted")
                        return []
                except Exception:
                    continue
            
            # Scroll to load more friends
            await self.utils.scroll_to_bottom(max_scrolls)
            
            # Take screenshot of friends page
            await self.utils.take_screenshot("friends_list")
            
            # Extract friends information with multiple selector strategies
            friends_list = []
            
            # Strategy 1: Modern Facebook selectors
            friend_selectors = [
                'div[data-pagelet*="ProfileAppSection"] a[href*="/"]',
                'div[role="main"] a[href*="facebook.com/"]',
                'a[href*="/"] span[dir="auto"]',
                'div[data-testid*="friend"] a',
            ]
            
            for selector in friend_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    print(f"🔍 Found {len(elements)} elements with selector: {selector}")
                    
                    for element in elements:
                        try:
                            # Get name
                            name_element = await element.query_selector('span[dir="auto"]')
                            if not name_element:
                                name_element = element
                            
                            name = await name_element.text_content()
                            if not name or len(name.strip()) < 2:
                                continue
                            
                            # Get profile URL
                            if await element.evaluate('el => el.tagName.toLowerCase()') == 'a':
                                href = await element.get_attribute('href')
                            else:
                                link_element = await element.query_selector('a[href*="/"]')
                                href = await link_element.get_attribute('href') if link_element else ""
                            
                            # Clean and validate
                            name = self.utils.clean_text(name)
                            if name and "Add Friend" not in name and len(name) > 1:
                                friend_data = {
                                    "name": name,
                                    "profile_url": href if href else "",
                                    "bio": ""  # Could be extracted if available
                                }
                                
                                # Avoid duplicates
                                if not any(f["name"] == name for f in friends_list):
                                    friends_list.append(friend_data)
                                    
                        except Exception as e:
                            print(f"⚠️ Error extracting individual friend: {e}")
                            continue
                    
                    if friends_list:  # If we found friends with this selector, use them
                        break
                        
                except Exception as e:
                    print(f"⚠️ Friend selector {selector} failed: {e}")
                    continue
            
            print(f"✅ Extracted {len(friends_list)} friends")
            return friends_list[:50]  # Limit to prevent excessive data
            
        except Exception as e:
            print(f"❌ Error getting friends list: {e}")
            return []

    async def get_groups(self) -> List[Dict[str, str]]:
        """Extract groups the user is a member of with improved selectors"""
        try:
            print("🔍 Extracting groups list...")
            
            # Check if page/browser is still available
            if not self.page or self.page.is_closed():
                print("❌ Page is closed, cannot get groups")
                return []
                
            # Get the username - use original username if available, otherwise extract from URL
            username = self.original_username or self._extract_username_from_url(self.page.url)
            
            if not username:
                print("❌ Could not extract username from URL")
                return []
                
            # Navigate to Groups page with proper URL construction
            groups_url = f"https://www.facebook.com/{username}/groups"
            print(f"🔗 Navigating to groups page: {groups_url}")
            await self.page.goto(groups_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)  # Wait for page to stabilize
            
            # Check if groups page exists or is private
            privacy_indicators = [
                'div:text-matches("This content isn\'t available|No groups to show|Groups are private")',
                'div:has-text("Only you can see")',
            ]
            
            for indicator in privacy_indicators:
                try:
                    privacy_element = await self.page.query_selector(indicator)
                    if privacy_element:
                        print("🔒 Groups list is private or empty")
                        return []
                except Exception:
                    continue
                
            # Scroll to load more groups
            await self.utils.scroll_to_bottom(3)
            
            # Take screenshot
            await self.utils.take_screenshot("groups_list")
            
            # Extract groups information with multiple strategies
            groups_list = []
            
            group_selectors = [
                'a[href*="/groups/"]',
                'div[data-testid*="group"] a',
                'div[role="main"] a[href*="facebook.com/groups/"]',
            ]
            
            for selector in group_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    print(f"🔍 Found {len(elements)} group elements with selector: {selector}")
                    
                    for element in elements:
                        try:
                            # Get group name
                            name = await element.text_content()
                            
                            # Get group URL
                            href = await element.get_attribute('href')
                            
                            if name and href and name.strip() and "/groups/" in href:
                                group_data = {
                                    "group_name": self.utils.clean_text(name.strip()),
                                    "group_url": href,
                                    "bio": ""  # Could be extracted if available
                                }
                                
                                # Avoid duplicates
                                if not any(g["group_name"] == group_data["group_name"] for g in groups_list):
                                    groups_list.append(group_data)
                                    
                        except Exception as e:
                            print(f"⚠️ Error extracting individual group: {e}")
                            continue
                    
                    if groups_list:  # If we found groups with this selector, use them
                        break
                        
                except Exception as e:
                    print(f"⚠️ Group selector {selector} failed: {e}")
                    continue
            
            print(f"✅ Extracted {len(groups_list)} groups")
            return groups_list
            
        except Exception as e:
            print(f"❌ Error getting groups: {e}")
            return []

    async def get_pages_followed(self) -> List[Dict[str, str]]:
        """Extract pages the user follows with improved selectors"""
        try:
            print("🔍 Extracting pages followed...")
            
            # Check if page/browser is still available
            if not self.page or self.page.is_closed():
                print("❌ Page is closed, cannot get pages followed")
                return []
                
            # Get the username - use original username if available, otherwise extract from URL
            username = self.original_username or self._extract_username_from_url(self.page.url)
            
            if not username:
                print("❌ Could not extract username from URL")
                return []
                
            # Navigate to Likes page with proper URL construction
            likes_url = f"https://www.facebook.com/{username}/likes"
            print(f"🔗 Navigating to likes page: {likes_url}")
            await self.page.goto(likes_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)  # Wait for page to stabilize
            
            # Check if likes page exists or is private
            privacy_indicators = [
                'div:text-matches("This content isn\'t available|No pages to show|Likes are private")',
                'div:has-text("Only you can see")',
            ]
            
            for indicator in privacy_indicators:
                try:
                    privacy_element = await self.page.query_selector(indicator)
                    if privacy_element:
                        print("🔒 Pages list is private or empty")
                        return []
                except Exception:
                    continue
                
            # Scroll to load more pages
            await self.utils.scroll_to_bottom(3)
            
            # Take screenshot of liked pages
            await self.utils.take_screenshot("pages_followed")
            
            # Extract pages information with multiple strategies
            pages_list = []
            
            page_selectors = [
                'div[role="main"] a[href*="facebook.com/"][href*="/"]',
                'a[href*="facebook.com/"] span[dir="auto"]',
                'div[data-testid*="page"] a',
            ]
            
            for selector in page_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    print(f"🔍 Found {len(elements)} page elements with selector: {selector}")
                    
                    for element in elements:
                        try:
                            # Get page name
                            name_element = await element.query_selector('span[dir="auto"]')
                            if not name_element:
                                name_element = element
                            
                            name = await name_element.text_content()
                            
                            # Get page URL
                            if await element.evaluate('el => el.tagName.toLowerCase()') == 'a':
                                href = await element.get_attribute('href')
                            else:
                                link_element = await element.query_selector('a[href*="facebook.com"]')
                                href = await link_element.get_attribute('href') if link_element else ""
                            
                            if name and href and name.strip():
                                # Filter out navigation links and duplicates
                                if not ("/likes" in href or "?ref=" in href or "/friends" in href):
                                    page_data = {
                                        "page_name": self.utils.clean_text(name.strip()),
                                        "page_url": href,
                                        "bio": ""  # Could be extracted if available
                                    }
                                    
                                    # Avoid duplicates
                                    if not any(p["page_name"] == page_data["page_name"] for p in pages_list):
                                        pages_list.append(page_data)
                                        
                        except Exception as e:
                            print(f"⚠️ Error extracting individual page: {e}")
                            continue
                    
                    if pages_list:  # If we found pages with this selector, use them
                        break
                        
                except Exception as e:
                    print(f"⚠️ Page selector {selector} failed: {e}")
                    continue
            
            print(f"✅ Extracted {len(pages_list)} pages")
            return pages_list
            
        except Exception as e:
            print(f"❌ Error getting pages: {e}")
            return []

    async def get_following_list(self) -> List[Dict[str, str]]:
        """Extract list of profiles the user is following with improved selectors"""
        try:
            print("🔍 Extracting following list...")
            
            # Check if page/browser is still available
            if not self.page or self.page.is_closed():
                print("❌ Page is closed, cannot get following list")
                return []
                
            # Get the username - use original username if available, otherwise extract from URL
            username = self.original_username or self._extract_username_from_url(self.page.url)
            
            if not username:
                print("❌ Could not extract username from URL")
                return []
                
            # Navigate to Following page with proper URL construction
            following_url = f"https://www.facebook.com/{username}/following"
            print(f"🔗 Navigating to following page: {following_url}")
            await self.page.goto(following_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)  # Wait for page to stabilize
            
            # Check if following page exists or is private
            privacy_indicators = [
                'div:text-matches("This content isn\'t available|No following to show|Following is private")',
                'div:has-text("Only you can see")',
            ]
            
            for indicator in privacy_indicators:
                try:
                    privacy_element = await self.page.query_selector(indicator)
                    if privacy_element:
                        print("🔒 Following list is private or empty")
                        return []
                except Exception:
                    continue
                
            # Scroll to load more following
            await self.utils.scroll_to_bottom(3)
            
            # Take screenshot of following page
            await self.utils.take_screenshot("following_list")
            
            # Extract following information with multiple strategies
            following_list = []
            
            following_selectors = [
                'div[role="main"] a[href*="facebook.com/"][href*="/"]',
                'a[href*="/"] span[dir="auto"]',
                'div[data-testid*="following"] a',
            ]
            
            for selector in following_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    print(f"🔍 Found {len(elements)} following elements with selector: {selector}")
                    
                    for element in elements:
                        try:
                            # Get profile name
                            name_element = await element.query_selector('span[dir="auto"]')
                            if not name_element:
                                name_element = element
                            
                            name = await name_element.text_content()
                            
                            # Get profile URL
                            if await element.evaluate('el => el.tagName.toLowerCase()') == 'a':
                                href = await element.get_attribute('href')
                            else:
                                link_element = await element.query_selector('a[href*="facebook.com"]')
                                href = await link_element.get_attribute('href') if link_element else ""
                            
                            if name and href and name.strip():
                                # Filter out navigation links and duplicates
                                if not ("/following" in href or "?ref=" in href or "/friends" in href):
                                    following_data = {
                                        "name": self.utils.clean_text(name.strip()),
                                        "profile_url": href,
                                        "bio": ""  # Could be extracted if available
                                    }
                                    
                                    # Avoid duplicates
                                    if not any(f["name"] == following_data["name"] for f in following_list):
                                        following_list.append(following_data)
                                        
                        except Exception as e:
                            print(f"⚠️ Error extracting individual following: {e}")
                            continue
                    
                    if following_list:  # If we found following with this selector, use them
                        break
                        
                except Exception as e:
                    print(f"⚠️ Following selector {selector} failed: {e}")
                    continue
            
            print(f"✅ Extracted {len(following_list)} following")
            return following_list
            
        except Exception as e:
            print(f"❌ Error getting following list: {e}")
            return []