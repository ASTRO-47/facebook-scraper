#!/usr/bin/env python3
"""
Test script for friends list scraping functionality
"""
import asyncio
import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper.session import FacebookSession
from scraper.profile import ProfileScraper
from scraper.utils import ScraperUtils
from scraper.json_builder import JSONBuilder

async def test_friends_scraping(username: str, headless: bool = True):
    """Test the friends list scraping functionality"""
    print(f"🧪 Testing friends list scraping for: {username}")
    
    try:
        # Initialize session
        print("🔧 Initializing Facebook session...")
        session = FacebookSession(headless=headless)
        page = await session.initialize()
        
        # Check login status
        is_logged_in = await session.login_check()
        if not is_logged_in:
            print("❌ Not logged in. Please login manually first.")
            await session.close()
            return False
        
        print("✅ Logged in successfully!")
        
        # Initialize scraper components
        utils = ScraperUtils(page)
        profile_scraper = ProfileScraper(page, utils)
        
        # Navigate to profile
        print(f"🎯 Navigating to profile: {username}")
        profile_exists = await profile_scraper.navigate_to_profile(username)
        
        if not profile_exists:
            print(f"❌ Failed to navigate to profile: {username}")
            await session.close()
            return False
        
        print("✅ Profile loaded successfully!")
        
        # Test friends list scraping
        print("👥 Testing friends list scraping...")
        friends = await profile_scraper.get_friends_list(max_scrolls=5)  # Limit scrolls for testing
        
        print(f"📊 Friends scraping results:")
        print(f"   Total friends found: {len(friends)}")
        
        if friends:
            print("   Sample friends:")
            for i, friend in enumerate(friends[:5]):  # Show first 5 friends
                print(f"     {i+1}. {friend.get('name', 'N/A')} - {friend.get('profile_url', 'N/A')}")
        
        # Test JSON building with friends
        print("📝 Testing JSON building with friends...")
        json_builder = JSONBuilder()
        
        # Create sample data structure
        sample_data = {
            "basic_info": {"name": "Test User"},
            "friends_list": friends,
            "groups": [],
            "pages_followed": [],
            "following_list": [],
            "own_posts": [],
            "tagged_posts": [],
            "user_comments": [],
            "locations": []
        }
        
        result = json_builder.build_profile_json(username, sample_data)
        
        print(f"✅ JSON built successfully!")
        print(f"   Friends in JSON: {len(result['data']['profile']['friends'])}")
        
        # Close session
        await session.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        try:
            if 'session' in locals():
                await session.close()
        except:
            pass
        return False

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python test_friends_scraper.py <username> [--no-headless]")
        sys.exit(1)
    
    username = sys.argv[1]
    headless = "--no-headless" not in sys.argv
    
    print(f"🚀 Starting friends scraping test for: {username}")
    print(f"🤖 Headless mode: {headless}")
    
    success = asyncio.run(test_friends_scraping(username, headless))
    
    if success:
        print("✅ Friends scraping test completed successfully!")
    else:
        print("❌ Friends scraping test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 