"""
Functions for scraping Facebook profile data
"""
import asyncio
import re
import time
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
                    # Handle cases like https://www.facebook.com/john.doe or facebook.com/john.doe
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

    async def navigate_to_profile(self, username):
        """Navigate to a user's profile page - handles both username and profile ID formats"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
        try:
            # Store the original username for later use
            self.original_username = username
            
                # Construct the appropriate URL using the helper function
                profile_url = self._construct_profile_url(username)
                print(f"🔗 Attempt {attempt + 1}/{max_attempts}: Navigating to {profile_url}")
                
                # If this is a retry, try alternative approaches
                if attempt > 0:
                    print(f"🧹 Attempt {attempt + 1}: Clearing cookies to avoid redirect loops...")
                    await self.page.context.clear_cookies()
                    await asyncio.sleep(10)  # Realistic retry delay
                    
                    # For profile IDs, try alternative URL formats on retries
            profile_type, profile_identifier = self._detect_profile_type(username)
                    if profile_type == "id" and attempt == 1:
                        # Try alternative URL format for profile IDs
                        profile_url = f"https://m.facebook.com/profile.php?id={profile_identifier}"
                        print(f"🔄 Trying mobile Facebook URL: {profile_url}")
                    elif profile_type == "id" and attempt == 2:
                        # Try yet another approach
                        profile_url = f"https://www.facebook.com/people/{profile_identifier}"
                        print(f"🔄 Trying people URL format: {profile_url}")
            else:
                        profile_url = self._construct_profile_url(username)
            
            # Use domcontentloaded with longer timeout for better reliability
                await self.page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)
            print("Page loaded, waiting for content to settle...")
                await asyncio.sleep(12)  # Human page observation time
            
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
                        await self.page.wait_for_selector(selector, timeout=10000)  # Reduced timeout
                    print(f"Found content using selector: {selector}")
                    content_loaded = True
                    break
                except:
                    print(f"Selector {selector} not found, trying next...")
                    continue
            
            if not content_loaded:
                print("⚠️ No expected selectors found, but continuing anyway...")
            
                # Check if we landed on an error page or got redirected to wrong profile
            current_url = self.page.url
                try:
                    page_title = await self.page.title()
                    print(f"🔍 Current URL after navigation: {current_url}")
                    print(f"🔍 Page title: {page_title}")
                except:
                    print(f"🔍 Current URL after navigation: {current_url}")
                    print(f"🔍 Could not get page title")
                
            if "facebook.com" not in current_url or "error" in current_url.lower():
                print(f"⚠️ Unexpected redirect to: {current_url}")
                    if attempt < max_attempts - 1:
                        continue
                return False
            
                # IMPORTANT: Check if we were redirected to the logged-in account instead of target profile
                profile_type, profile_identifier = self._detect_profile_type(username)
                
                redirect_detected = False
                if profile_type == "id":
                    # For profile IDs, check if the current URL contains the target ID
                    if f"id={profile_identifier}" not in current_url:
                        redirect_detected = True
                        print(f"❌ REDIRECT DETECTED: Requested profile ID {profile_identifier} but landed on {current_url}")
                else:
                    # For usernames, check if the current URL contains the target username
                    if profile_identifier not in current_url and f"/{profile_identifier}" not in current_url:
                        redirect_detected = True
                        print(f"❌ REDIRECT DETECTED: Requested username {profile_identifier} but landed on {current_url}")
                
                # Additional check: See if we landed on Facebook home/feed instead of profile
                if any(pattern in current_url.lower() for pattern in ['/home', '/feed', '/?sk=', 'facebook.com/?']):
                    print(f"❌ FACEBOOK HOME/FEED DETECTED: Landed on {current_url}")
                    redirect_detected = True
                
                if redirect_detected:
                    if attempt < max_attempts - 1:
                        print(f"🔄 Redirect detected on attempt {attempt + 1}, will retry...")
                        await asyncio.sleep(3)  # Reduced delay
                        continue  # Try again
                    else:
                        print(f"❌ Failed after {max_attempts} attempts. This usually means:")
                        print(f"   - The profile doesn't exist")
                        print(f"   - The profile is private/restricted") 
                        print(f"   - Facebook is blocking access to this profile")
                        print(f"   - The profile ID {profile_identifier} may be invalid")
                        print(f"   - Facebook redirected to home page/feed instead")
                        return False
                
                print(f"✅ Successfully landed on target profile: {profile_identifier}")
                
            # Check for security checkpoint before proceeding
            checkpoint_detected = await self.utils.check_for_security_checkpoint()
            if checkpoint_detected:
                print("🔒 Security checkpoint detected during navigation!")
                    await self.utils.handle_security_checkpoint(wait_time=60)  # Reduced time
                # Wait extra time after checkpoint resolution
                    await asyncio.sleep(3)  # Reduced delay
            
            print(f"✅ Successfully navigated to profile: {username}")
            return True
            
        except Exception as e:
                print(f"❌ Error navigating to profile on attempt {attempt + 1}: {str(e)}")
                if attempt < max_attempts - 1:
                    print(f"🔄 Will retry in 5 seconds...")
                    await asyncio.sleep(5)  # Reduced delay
                    continue
                else:
            return False
        
        return False  # If all attempts failed

    async def get_basic_info(self) -> Dict[str, Any]:
        """Extract basic profile information with improved selectors and fallbacks"""
        try:
            print("🔍 Extracting basic profile information...")
            
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
                "profile_picture": "",
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
        """Extract profile name with multiple fallback selectors - FIXED"""
        name_selectors = [
            'h1',  # Most common
            'span[dir="auto"]',  # Common pattern, but we need to filter out friend counts
            '[data-testid="profile-name"]',
            'div[role="main"] h1',
            'div[data-pagelet*="Profile"] h1',
        ]
        
        for selector in name_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                for element in elements:
                    full_name = await element.text_content()
                    if full_name and len(full_name.strip()) > 0:
                        name = full_name.strip()
                        
                        # Skip obvious non-name content
                        if any(skip in name.lower() for skip in [
                            "notification", "friend", "mutual", "•", "see all", "photos", 
                            "about", "more", "home", "settings", "search"
                        ]):
                            continue
                        
                        # Extract just the name part (before parentheses if any)
                        if '(' in name:
                            name = name.split('(')[0].strip()
                        
                        # Skip if it looks like a count or navigation
                        if name.isdigit() or len(name) < 2:
                            continue
                            
                        print(f"✅ Found name using selector: {selector}")
                        return name
            except Exception as e:
                print(f"⚠️ Name selector {selector} failed: {e}")
                continue
        
        return "Unknown"

    async def _extract_profile_bio(self) -> str:
        """Extract profile bio/description with multiple fallback selectors - FIXED"""
        # First, try to find actual bio content, not friend counts
        bio_selectors = [
            '[data-testid="profile-bio"]',
            'div[data-pagelet*="Profile"] div[dir="auto"]',
            'div[role="main"] div[dir="auto"]',
        ]
        
        for selector in bio_selectors:
            try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        bio_text = await element.text_content()
                    if bio_text and len(bio_text.strip()) > 5:
                        bio = bio_text.strip()
                        
                        # Skip friend counts, navigation, and other non-bio content
                        if any(skip in bio.lower() for skip in [
                            "friend", "mutual", "•", "notification", "see all", "photos", 
                            "about", "more", "home", "settings", "likes", "followers"
                        ]):
                            continue
                        
                        # Must be meaningful bio content
                        if len(bio) > 10 and not bio.isdigit():
                                        print(f"✅ Found bio using selector: {selector}")
                                        return bio
            except Exception as e:
                print(f"⚠️ Bio selector {selector} failed: {e}")
                continue
        
        return ""

    async def _extract_about_info(self) -> Dict[str, Any]:
        """Extract detailed information from About page with faster execution"""
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
                        await asyncio.sleep(6)  # Human click processing time
                        await self.page.wait_for_load_state("domcontentloaded", timeout=30000)  # Increased timeout
                        print(f"✅ Navigated to About using selector: {selector}")
                        about_clicked = True
                        break
                except Exception as e:
                    print(f"⚠️ About selector {selector} failed: {e}")
                    continue
            
            if not about_clicked:
                print("⚠️ Could not navigate to About page, using main profile page")
                return about_data
            
            # Extract different types of information with improved parsing
            about_data.update(await self._extract_work_education_improved())
            about_data.update(await self._extract_places_improved())
            about_data.update(await self._extract_contact_info())
            about_data.update(await self._extract_basic_details())
            
        except Exception as e:
            print(f"❌ Error extracting about info: {e}")
        
        return about_data

    async def get_friends_list(self, max_scrolls: int = 50) -> List[Dict[str, str]]:
        """Extract friends list with FIXED CSS selectors and proper validation"""
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
                
            # Construct appropriate friends URL using helper function
            friends_url = self._construct_profile_url(username, "friends")
            print(f"🔗 Navigating to friends page: {friends_url}")
            
            # Navigate with retries and realistic human delays
            for attempt in range(3):
                try:
                    await self.page.goto(friends_url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(8)  # Human page loading observation time
                    break
                except Exception as e:
                    print(f"⚠️ Navigation attempt {attempt + 1} failed: {e}")
                    if attempt == 2:
                        return []
                    await asyncio.sleep(10)  # Longer retry delay
            
            # Check for privacy restrictions
            privacy_texts = [
                "This content isn't available",
                "Friends list is private", 
                "No friends to show",
                "Only you can see",
                "Content not available"
            ]
            
            page_content = await self.page.content()
            if any(text in page_content for text in privacy_texts):
                print("🔒 Friends list is private or restricted")
                return []
            
            # SCALABLE scrolling for large friend lists (up to 10K+)
            friends_list = []
            last_count = 0
            stable_rounds = 0
            max_stable_rounds = 5
            
            print(f"🔄 Starting infinite scroll for up to {max_scrolls} attempts...")
            
            for scroll_attempt in range(max_scrolls):
                # FIXED: Use proper CSS selectors without syntax errors
                friend_elements = await self.page.query_selector_all('a[href*="facebook.com/"]')
                
                # Filter and extract friends from found elements
                current_batch = []
                for element in friend_elements:
                    try:
                        href = await element.get_attribute('href')
                        if not href:
                            continue
                        
                        # Skip navigation links with comprehensive patterns
                        skip_patterns = [
                            '/friends/', '/photos/', '/videos/', '/about/', '/posts/',
                            '/likes/', '/groups/', '/events/', '/reviews/', '/places/',
                            '?sk=', '?ref=', '/home/', '/feed/', '/search/', '/browse/',
                            'mutual', 'message', '/settings/', '/notifications/',
                            '/stories/', '/reels/', '/watch/', '/marketplace/',
                            '/gaming/', '/pages/', '/ads/', '/help/'
                        ]
                        
                        if any(pattern in href for pattern in skip_patterns):
                            continue
                        
                        # Skip if it's the user's own profile
                        if username and (f"/{username}" in href or href.endswith(username)):
                            continue
                        
                        # Get name - try multiple approaches
                        name = ""
                        
                        # Method 1: Direct text content
                        direct_text = await element.text_content()
                        if direct_text and len(direct_text.strip()) > 1:
                            name = direct_text.strip()
                        
                        # Method 2: Look for name in child elements
                        if not name:
                            name_elements = await element.query_selector_all('span, div')
                            for name_elem in name_elements:
                                text = await name_elem.text_content()
                                if text and len(text.strip()) > 1:
                                    name = text.strip()
                                    break
                        
                        if not name or len(name) < 2:
                            continue
                        
                        # Comprehensive filtering of navigation text and invalid content
                        invalid_names = [
                            "see all", "more", "photos", "videos", "about", "friends",
                            "mutual", "message", "follow", "add friend", "home", "settings",
                            "notifications", "stories", "reels", "watch", "marketplace",
                            "gaming", "pages", "ads", "help", "search", "browse",
                            "like", "comment", "share", "save", "edit", "delete",
                            "report", "block", "unfriend", "unfollow", "hide",
                            "ago", "min", "hour", "day", "week", "month", "year",
                            "•", "·", "...", "view", "show", "hide", "close"
                        ]
                        
                        # Skip names that are clearly navigation or invalid
                        if any(invalid in name.lower() for invalid in invalid_names):
                            continue
                        
                        # Skip names that are just numbers or too short
                        if name.isdigit() or len(name) < 2:
                            continue
                        
                        # Skip names with common notification patterns
                        if any(pattern in name.lower() for pattern in [
                            "accepted your", "friend request", "notification",
                            "tagged you", "commented on", "liked your", "shared your"
                        ]):
                            continue
                        
                        # Additional validation: must look like a real name
                        # Skip if it's all uppercase (likely navigation)
                        if name.isupper() and len(name) > 5:
                            continue
                        
                        # Check for duplicates in current batch and overall list
                        if any(f["name"] == name for f in friends_list + current_batch):
                            continue
                        
                        # Validate the href looks like a real profile URL
                        if not self._is_valid_profile_url(href):
                            continue
                        
                        friend_data = {
                            "name": self.utils.clean_text(name),
                            "profile_url": href,
                            "bio": ""  # Bio extraction can be added if needed
                        }
                        
                        current_batch.append(friend_data)
                        
                    except Exception:
                        continue
                
                # Add new friends to list
                for friend in current_batch:
                    if not any(f["name"] == friend["name"] for f in friends_list):
                        friends_list.append(friend)
                
                current_count = len(friends_list)
                new_friends = current_count - last_count
                print(f"📜 Scroll {scroll_attempt + 1}/{max_scrolls}: Found {current_count} total friends (+{new_friends} new)")
                
                # Check for stability (no new friends found)
                if current_count == last_count:
                    stable_rounds += 1
                    if stable_rounds >= max_stable_rounds:
                        print(f"✅ No new friends found for {max_stable_rounds} rounds, stopping")
                        break
                else:
                    stable_rounds = 0
                
                last_count = current_count
                
                # Human-like scrolling behavior to avoid detection
                try:
                    # Gradual scrolling like a human reading
                    for i in range(3):
                        await self.page.evaluate(f'window.scrollBy(0, {300 + i * 100})')
                        await asyncio.sleep(1.5)  # Pause between scroll increments
                    
                    # Final scroll to bottom
                    await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await asyncio.sleep(5)  # Human reading/processing time
                    
                    # Try to click "See more" buttons with human-like delays
                    see_more_selectors = [
                        'text="See more"',
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
                                        # Human-like button clicking with random delay
                                        await asyncio.sleep(2 + (scroll_attempt * 0.5))  # Increasing delay per scroll
                                        await button.click()
                                        await asyncio.sleep(4)  # Wait for content to load
                                except:
                                    continue
                        except:
                            continue
                    
                except Exception:
                    continue
            
            print(f"✅ Extracted {len(friends_list)} friends total")
            return friends_list
            
        except Exception as e:
            print(f"❌ Error getting friends list: {e}")
            return []

    def _is_valid_profile_url(self, url: str) -> bool:
        """Validate if URL looks like a real Facebook profile"""
        try:
            # Must contain facebook.com
            if "facebook.com" not in url:
                return False
            
            # Skip obvious non-profile URLs
            invalid_patterns = [
                '/groups/', '/pages/', '/events/', '/photos/', '/videos/',
                '/marketplace/', '/gaming/', '/watch/', '/business/',
                '/ads/', '/help/', '/settings/', '/privacy/', '/terms/',
                '?sk=', '?ref=', '#', 'l.facebook.com', 'm.me',
                '/login/', '/signup/', '/recover/', '/security/'
            ]
            
            if any(pattern in url for pattern in invalid_patterns):
                return False
            
            # Must have a meaningful path after facebook.com
            parts = url.split('facebook.com/')
            if len(parts) < 2:
                return False
            
            path = parts[1].split('?')[0].split('#')[0]
            
            # Valid profile patterns
            if path.startswith('profile.php?id='):
                return True
            
            # Username-based profiles
            if len(path) > 0 and '/' not in path.strip('/'):
                return True
            
            return False
            
        except Exception:
            return False

    async def _extract_work_education_improved(self) -> Dict[str, Any]:
        """Extract work and education with MUCH better filtering to avoid notifications"""
        result = {"work": [], "education": []}
        
        try:
            await asyncio.sleep(2)
            
            # Get page content and filter out notifications
            page_content = await self.page.content()
            
            # Skip if we detect notification patterns in the content
            notification_patterns = [
                "accepted your friend request",
                "sent you a friend request", 
                "tagged you in",
                "commented on your",
                "liked your",
                "shared your",
                "notification",
                "ago",
                "minutes ago",
                "hours ago",
                "days ago"
            ]
            
            # Look for structured work/education sections specifically
            work_selectors = [
                '[data-overviewsection="work"] div[role="button"]',
                '[aria-label*="Work"] div',
                'div:has-text("Works at") + div',
                'div:has-text("Worked at") + div'
            ]
            
            for selector in work_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        text = await element.text_content()
                        if text and len(text.strip()) > 3:
                            clean_text = self.utils.clean_text(text)
                            
                            # Skip if it contains notification patterns
                            if any(pattern in clean_text.lower() for pattern in notification_patterns):
                                continue
                            
                            # Skip common non-work text
                            if any(skip in clean_text.lower() for skip in [
                                "add a workplace", "work and education", "overview", 
                                "see all", "more", "edit", "delete", "hide"
                            ]):
                    continue
            
                            # Must look like actual work info
                            if len(clean_text) > 5 and not clean_text.isdigit():
                                result["work"].append(clean_text)
                                
                except Exception:
                    continue
            
            # Similar approach for education
            edu_selectors = [
                '[data-overviewsection="education"] div[role="button"]',
                '[aria-label*="Education"] div',
                'div:has-text("Studies at") + div',
                'div:has-text("Studied at") + div'
            ]
            
            for selector in edu_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        text = await element.text_content()
                        if text and len(text.strip()) > 3:
                            clean_text = self.utils.clean_text(text)
                            
                            # Skip if it contains notification patterns
                            if any(pattern in clean_text.lower() for pattern in notification_patterns):
                                continue
                            
                            # Skip common non-education text
                            if any(skip in clean_text.lower() for skip in [
                                "add a school", "education", "overview",
                                "see all", "more", "edit", "delete", "hide"
                            ]):
                    continue
            
                            # Must look like actual education info
                            if len(clean_text) > 5 and not clean_text.isdigit():
                                result["education"].append(clean_text)
                                
                except Exception:
                    continue
            
            # Remove duplicates and clean up
            result["work"] = list(set([w for w in result["work"] if w and len(w.strip()) > 3]))
            result["education"] = list(set([e for e in result["education"] if e and len(e.strip()) > 3]))
            
            # If we still got notification-like content, clear it
            result["work"] = [w for w in result["work"] if not any(pattern in w.lower() for pattern in notification_patterns)]
            result["education"] = [e for e in result["education"] if not any(pattern in e.lower() for pattern in notification_patterns)]
            
        except Exception as e:
            print(f"❌ Error extracting work/education: {e}")
        
        return result

    async def _extract_places_improved(self) -> Dict[str, Any]:
        """Extract location information with improved parsing"""
        result = {}
        
        try:
            # Look for location information in structured format
            location_selectors = [
                'div[data-overviewsection="places"]',
                'div:has-text("Places lived")',
                'div:has-text("Lives in")',
                'div:has-text("From")',
            ]
            
            for selector in location_selectors:
                try:
                    location_section = await self.page.query_selector(selector)
                    if location_section:
                        # Extract individual location entries
                        location_entries = await location_section.query_selector_all('div[role="button"], a[role="link"]')
                        for entry in location_entries:
                            location_text = await entry.text_content()
                            if location_text and len(location_text.strip()) > 3:
                                clean_location = self.utils.clean_text(location_text)
                                if "lives in" in clean_location.lower():
                                    result["current_city"] = clean_location.replace("Lives in", "").strip()
                                elif "from" in clean_location.lower():
                                    result["hometown"] = clean_location.replace("From", "").strip()
                        if result:
                            break
                except Exception as e:
                    print(f"⚠️ Location selector {selector} failed: {e}")
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

    async def get_groups(self) -> List[Dict[str, str]]:
        """Extract groups the user is a member of with improved selectors"""
        try:
            print("🔍 Extracting groups list...")
            
            # Check if page/browser is still available
            if not self.page or self.page.is_closed():
                print("❌ Page is closed, cannot get groups")
                return []
                
            # Get the username
            username = self.original_username or self._extract_username_from_url(self.page.url)
            
            if not username:
                print("❌ Could not extract username from URL")
                return []
                
            # Construct appropriate groups URL
            groups_url = self._construct_profile_url(username, "groups")
            print(f"🔗 Navigating to groups page: {groups_url}")
            await self.page.goto(groups_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(8)  # Human page observation time
            
            # Check if groups page exists or is private
            if await self.page.query_selector('text="This content isn\'t available"'):
                        print("🔒 Groups list is private or empty")
                        return []
                
            # Scroll to load more groups with human-like behavior
            await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(6)  # Human reading and processing time
            
            # Extract groups information
            groups_list = []
            
            # Simple, working selector for groups
            group_links = await self.page.query_selector_all('a[href*="/groups/"]')
                    
            for link in group_links:
                        try:
                            # Get group name
                    name = await link.text_content()
                            
                            # Get group URL
                    href = await link.get_attribute('href')
                            
                            if name and href and name.strip() and "/groups/" in href:
                        # Skip navigation elements
                        if any(skip in name.lower() for skip in [
                            "see all", "more", "groups", "discover", "create"
                        ]):
                            continue
                        
                                group_data = {
                                    "group_name": self.utils.clean_text(name.strip()),
                                    "group_url": href,
                            "bio": ""
                                }
                                
                                # Avoid duplicates
                                if not any(g["group_name"] == group_data["group_name"] for g in groups_list):
                                    groups_list.append(group_data)
                                    
                except Exception:
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
                
            # Get the username
            username = self.original_username or self._extract_username_from_url(self.page.url)
            
            if not username:
                print("❌ Could not extract username from URL")
                return []
                
            # Construct appropriate likes URL
            likes_url = self._construct_profile_url(username, "likes")
            print(f"🔗 Navigating to likes page: {likes_url}")
            await self.page.goto(likes_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(8)  # Human page observation time
            
            # Check if likes page exists or is private
            if await self.page.query_selector('text="This content isn\'t available"'):
                        print("🔒 Pages list is private or empty")
                        return []
                
            # Scroll to load more pages with human-like behavior
            await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(6)  # Human reading and processing time
            
            # Extract pages information with FIXED logic
            pages_list = []
            
            # Get all Facebook links and filter for pages
            all_links = await self.page.query_selector_all('a[href*="facebook.com/"]')
                    
            for link in all_links:
                try:
                    href = await link.get_attribute('href')
                    name = await link.text_content()
                    
                    if not href or not name or not name.strip():
                                        continue
                                    
                    name = name.strip()
                    
                    # Skip navigation and user profile links
                    if any(skip in href for skip in [
                        '/likes', '/friends', '/photos', '/videos', '/about',
                        '?ref=', '?sk=', '/home', '/feed'
                    ]):
                        continue
                    
                    # Skip navigation text
                    if any(invalid in name.lower() for invalid in [
                        "see all", "more", "likes", "following", "pages",
                        "mutual", "message", "home", "settings"
                                                            ]):
                        continue
                    
                    # Skip if this is the user's own profile
                    if username and username in href:
                        continue
                                    
                                    page_data = {
                        "page_name": self.utils.clean_text(name),
                                        "page_url": href,
                        "bio": ""
                                    }
                                    
                                    # Avoid duplicates
                                    if not any(p["page_name"] == page_data["page_name"] for p in pages_list):
                                        pages_list.append(page_data)
                        
                except Exception:
                    continue
            
            print(f"✅ Extracted {len(pages_list)} pages")
            return pages_list
            
        except Exception as e:
            print(f"❌ Error getting pages: {e}")
            return []

    async def get_following_list(self) -> List[Dict[str, str]]:
        """Extract following list with MUCH better filtering to avoid user's own profile"""
        try:
            print("🔍 Extracting following list...")
            
            # Check if page/browser is still available
            if not self.page or self.page.is_closed():
                print("❌ Page is closed, cannot get following list")
                return []
                
            # Get the username
            username = self.original_username or self._extract_username_from_url(self.page.url)
            
            if not username:
                print("❌ Could not extract username from URL")
                return []
                
            # Construct appropriate following URL
            following_url = self._construct_profile_url(username, "following")
            print(f"🔗 Navigating to following page: {following_url}")
            await self.page.goto(following_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(8)  # Human page observation time
            
            # Check if following page exists or is private
            page_content = await self.page.content()
            if "This content isn't available" in page_content:
                        print("🔒 Following list is private or empty")
                        return []
                
            # Scroll to load more following with human-like behavior
            await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(6)  # Human reading and processing time
            
            # Extract following information with FIXED filtering
            following_list = []
            
            # Get all Facebook links and filter properly
            all_links = await self.page.query_selector_all('a[href*="facebook.com/"]')
                    
            for link in all_links:
                        try:
                    href = await link.get_attribute('href')
                    name = await link.text_content()
                    
                    if not href or not name or not name.strip():
                        continue
                    
                    name = name.strip()
                    
                    # Skip the user's own profile (CRITICAL FIX)
                    if username and (f"/{username}" in href or href.endswith(username) or username in href):
                        continue
                    
                    # Skip navigation and non-profile links
                    if any(skip in href for skip in [
                        '/following/', '/friends/', '/photos/', '/videos/', '/about/',
                        '?ref=', '?sk=', '/home/', '/feed/', '/settings/', '/notifications/'
                    ]):
                        continue
                    
                    # Skip navigation text
                    if any(invalid in name.lower() for invalid in [
                        "see all", "more", "following", "follow", "unfollow",
                        "mutual", "message", "home", "settings", "photos", "videos"
                    ]):
                        continue
                    
                    # Validate it's a real profile URL
                    if not self._is_valid_profile_url(href):
                        continue
                                    
                                    following_data = {
                        "name": self.utils.clean_text(name),
                                        "profile_url": href,
                        "bio": ""
                                    }
                                    
                                    # Avoid duplicates
                                    if not any(f["name"] == following_data["name"] for f in following_list):
                                        following_list.append(following_data)
                        
                except Exception:
                    continue
            
            print(f"✅ Extracted {len(following_list)} following")
            return following_list
            
        except Exception as e:
            print(f"❌ Error getting following list: {e}")
            return []