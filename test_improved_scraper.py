#!/usr/bin/env python3
"""
Quick test script for the improved Facebook scraper
"""
import asyncio
import os
import sys

# Add the scraper module to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.session import FacebookSession
from scraper.profile import ProfileScraper
from scraper.utils import ScraperUtils

async def test_scraper(username="imad.zaghba.5"):
    """Test the improved scraper with better timeout handling"""
    try:
        # Set display for VNC
        os.environ["DISPLAY"] = ":1"
        
        # Create user data directory
        user_data_dir = os.path.join(os.path.expanduser("~"), ".facebook_scraper_data")
        os.makedirs(user_data_dir, exist_ok=True)
        
        print(f"🚀 Testing improved Facebook scraper for: {username}")
        print("="*60)
        
        # Initialize session
        print("1. Initializing browser session...")
        session = FacebookSession(headless=False, user_data_dir=user_data_dir)
        page = await session.initialize()
        
        # Check login
        print("2. Checking login status...")
        is_logged_in = await session.login_check()
        if is_logged_in:
            print("✅ Already logged in!")
        else:
            print("❌ Login required")
            return
        
        # Initialize utils and profile scraper
        utils = ScraperUtils(page, screenshot_dir="./test_screenshots")
        profile_scraper = ProfileScraper(page, utils)
        
        # Test navigation
        print(f"3. Testing navigation to {username}...")
        success = await profile_scraper.navigate_to_profile(username)
        
        if success:
            print("✅ Navigation successful!")
            
            # Test basic info scraping
            print("4. Testing basic info extraction...")
            try:
                basic_info = await profile_scraper.get_basic_info()
                print(f"✅ Basic info extracted: {basic_info}")
            except Exception as e:
                print(f"⚠️ Basic info extraction failed: {e}")
            
            # Keep browser open for observation
            print("5. Keeping browser open for 30 seconds for observation...")
            await asyncio.sleep(30)
        else:
            print("❌ Navigation failed")
        
        # Close session
        print("6. Closing browser session...")
        await session.close()
        print("✅ Test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        username = sys.argv[1]
        asyncio.run(test_scraper(username))
    else:
        print("Usage: python3 test_improved_scraper.py <username>")
        print("Example: python3 test_improved_scraper.py imad.zaghba.5")
