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

    async def navigate_to_profile(self, username):
        """Navigate to a user's profile page"""
        try:
            # Navigate to the profile
            profile_url = f"https://www.facebook.com/{username}"
            print(f"Navigating to {profile_url}")
            await self.page.goto(profile_url, wait_until="networkidle")
            await asyncio.sleep(2)  # Wait for any redirects or overlays
            
            # Check for security checkpoint
            if await self.utils.check_for_security_checkpoint():
                print("Security checkpoint detected!")
                # Use None for indefinite wait
                await self.utils.handle_security_checkpoint(wait_time=None)
        
            # Take a screenshot of the profile
            await self.utils.take_screenshot(f"profile_{username}")
            return True
        except Exception as e:
            print(f"Error navigating to profile: {str(e)}")
            return False

    async def get_basic_info(self) -> Dict[str, Any]:
        """Extract basic profile information"""
        # Take screenshot of profile header
        screenshot_path = await self.utils.take_screenshot("profile_header", "div[role='main']")
        
        # Get profile name
        name_element = await self.page.query_selector('h1')
        name = await name_element.text_content() if name_element else "Unknown"
        
        # Get bio if available
        bio_element = await self.page.query_selector('div[role="main"] > div > div > div > div > div > div > span')
        bio = await bio_element.text_content() if bio_element else ""
        
        # Navigate to About page
        await self.page.click('a[href*="/about"]')
        await self.page.wait_for_load_state("networkidle")
        
        # Extract detailed information
        about_data = {}
        
        # Work and Education
        work_education = await self._extract_section_data("Work and Education")
        
        # Places Lived
        places = await self._extract_section_data("Places Lived")
        
        # Contact Info
        contact = await self._extract_section_data("Contact Info")
        
        # Basic Info (including birthday)
        basic = await self._extract_section_data("Basic Info")
        
        return {
            "name": self.utils.clean_text(name),
            "bio": self.utils.clean_text(bio),
            "profile_picture": screenshot_path,
            "work": work_education.get("work", []),
            "education": work_education.get("education", []),
            "location": places.get("current_city", ""),
            "hometown": places.get("hometown", ""),
            "email": contact.get("email", ""),
            "phone": contact.get("phone", ""),
            "birthday": basic.get("birthday", ""),
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
        # Navigate to Friends page
        await self.page.goto(self.page.url.split('?')[0].rstrip('/') + '/friends', wait_until="networkidle")
        
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
                link_element = await element.query_selector('a[href*="/friends/"]')
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
        
        return friends_list

    async def get_groups(self) -> List[Dict[str, str]]:
        """Extract groups the user is a member of"""
        # Navigate to Groups page
        try:
            await self.page.goto(self.page.url.split('?')[0].rstrip('/') + '/groups', wait_until="networkidle")
            
            # Check if groups page exists
            no_content = await self.page.query_selector('div:text-matches("This content isn\'t available|No groups to show")')
            if no_content:
                return []
                
            # Scroll to load more groups
            await self.utils.scroll_to_bottom(3)
            
            # Take screenshot of groups page
            await self.utils.take_screenshot("groups_list")
            
            # Extract groups information
            groups_list = []
            group_elements = await self.page.query_selector_all('div[role="main"] > div > div > div > div')
            
            for element in group_elements:
                try:
                    name_element = await element.query_selector('span[dir="auto"]')
                    if not name_element:
                        continue
                    
                    name = await name_element.text_content()
                    
                    # Try to get group link
                    link_element = await element.query_selector('a[href*="/groups/"]')
                    group_url = ""
                    if link_element:
                        href = await link_element.get_attribute('href')
                        if href:
                            group_url = href
                    
                    if name and group_url:
                        groups_list.append({
                            "name": self.utils.clean_text(name),
                            "url": group_url
                        })
                except Exception as e:
                    print(f"Error extracting group info: {e}")
                    continue
            
            return groups_list
        except Exception as e:
            print(f"Error getting groups: {e}")
            return []

    async def get_pages_followed(self) -> List[Dict[str, str]]:
        """Extract pages the user follows"""
        # Navigate to Likes page
        try:
            await self.page.goto(self.page.url.split('?')[0].rstrip('/') + '/likes', wait_until="networkidle")
            
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
            
            return pages_list
        except Exception as e:
            print(f"Error getting pages: {e}")
            return []

    async def get_following_list(self) -> List[Dict[str, str]]:
        """Extract list of profiles the user is following"""
        # Navigate to Following page
        try:
            await self.page.goto(self.page.url.split('?')[0].rstrip('/') + '/following', wait_until="networkidle")
            
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
            
            return following_list
        except Exception as e:
            print(f"Error getting following list: {e}")
            return []