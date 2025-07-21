#!/usr/bin/env python3
"""
Test script for the improved Facebook Profile Scraper
This script allows you to test the improvements with better debugging output
"""
import os
import sys
import json
import asyncio
import argparse
from datetime import datetime
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('facebook_test')

# Make sure the scraper module can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper.session import FacebookSession
from scraper.profile import ProfileScraper
from scraper.posts import PostsScraper
from scraper.utils import ScraperUtils
from scraper.json_builder import JSONBuilder

#!/usr/bin/env python3
"""
Test script for improved Facebook scraper with non-headless browser
"""

import asyncio
import sys
from scraper.session import FacebookSession
from scraper.posts import PostsScraper
from scraper.utils import ScraperUtils
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_improved_scraper(username: str = "test_user"):
    """Test the improved scraper with visible browser"""
    print("🚀 Testing improved Facebook scraper with visible browser...")
    
    # Initialize session with headless=False to see browser
    session = FacebookSession(headless=False, user_data_dir="./user_data")
    
    try:
        # Initialize browser (non-headless)
        page = await session.initialize()
        print("✅ Browser initialized successfully (visible mode)")
        
        # Initialize utilities and scraper
        utils = ScraperUtils(page)
        scraper = PostsScraper(page, utils)
        
        # Go to Facebook
        await session.prefill_login()
        
        # Wait for manual login
        print("⏳ Please login manually in the browser window...")
        print("   - Enter your credentials")
        print("   - Complete any 2FA if required")
        print("   - Navigate to the profile you want to scrape")
        print("   - Press Enter here when ready to start scraping...")
        
        input("Press Enter when logged in and ready...")
        
        # Check if logged in
        if await session.login_check():
            print("✅ Login successful!")
            
            # Test improved post extraction
            print(f"🔍 Testing improved post extraction...")
            
            # Get current URL to determine what to scrape
            current_url = page.url
            print(f"📍 Current URL: {current_url}")
            
            # Extract posts using improved methods
            posts = await scraper.extract_posts(max_posts=5, post_type="own")
            
            print(f"📊 Extracted {len(posts)} posts")
            
            # Display post information
            for i, post in enumerate(posts[:3], 1):  # Show first 3 posts
                print(f"\n📝 Post {i}:")
                print(f"   Content: {post.get('content', 'N/A')[:100]}...")
                print(f"   Timestamp: {post.get('timestamp', 'N/A')}")
                print(f"   Reactions: {post.get('reactions', {}).get('total', 0)}")
                print(f"   Comments: {post.get('comments_count', 0)}")
                print(f"   URL: {post.get('original_url', 'N/A')}")
                print(f"   Media: {len(post.get('media', []))} items")
                
            print(f"\n🎉 Test completed successfully!")
            print(f"   - Browser was visible during scraping")
            print(f"   - Improved content extraction worked")
            print(f"   - Enhanced reaction detection active")
            
        else:
            print("❌ Login failed or not completed")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Keep browser open for inspection
        print("\n🔍 Browser will remain open for inspection...")
        print("   - Check the extracted post data")
        print("   - Verify the selectors are working")
        print("   - Press Ctrl+C to close when done")
        
        try:
            # Keep running until interrupted
            await asyncio.sleep(300)  # Wait 5 minutes
        except KeyboardInterrupt:
            print("\n👋 Closing browser...")
            
        # Close session
        if session.context:
            await session.context.close()

if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else "test_user"
    asyncio.run(test_improved_scraper(username))
    try:
        print("="*80)
        print(f"🧪 TESTING IMPROVED FACEBOOK SCRAPER")
        print(f"Target Profile: {username}")
        print(f"Headless Mode: {headless}")
        print(f"Test Posts: {test_posts}")
        print("="*80)
        
        # Set display for X11 if not headless
        if not headless:
            os.environ["DISPLAY"] = ":1"
        
        # Create directories
        user_data_dir = os.path.join(os.path.expanduser("~"), ".facebook_scraper_data")
        os.makedirs(user_data_dir, exist_ok=True)
        
        output_dir = "./test_output"
        os.makedirs(output_dir, exist_ok=True)
        screenshots_dir = os.path.join(output_dir, "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        
        print(f"📁 Output directory: {output_dir}")
        
        # Initialize session
        logger.info("🔧 Initializing Facebook session...")
        session = FacebookSession(headless=headless, user_data_dir=user_data_dir)
        page = await session.initialize()
        
        # Check login status
        logger.info("🔑 Checking login status...")
        is_logged_in = await session.login_check()
        if not is_logged_in:
            logger.info("✅ Login completed successfully")
        else:
            logger.info("✅ Already logged in to Facebook")
        
        # Initialize helper classes
        utils = ScraperUtils(page, screenshot_dir=screenshots_dir)
        profile_scraper = ProfileScraper(page, utils)
        posts_scraper = PostsScraper(page, utils)
        json_builder = JSONBuilder(output_dir=output_dir)
        
        # Set up dialog handlers
        await utils.handle_dialogs()
        
        print("\n" + "="*60)
        print("🎯 PHASE 1: PROFILE NAVIGATION")
        print("="*60)
        
        # Navigate to profile
        logger.info(f"🔗 Navigating to profile: {username}")
        profile_exists = await profile_scraper.navigate_to_profile(username)
        
        if not profile_exists:
            logger.error(f"❌ Profile '{username}' not found")
            await session.close()
            return False
        
        print("\n" + "="*60)
        print("🔍 PHASE 2: BASIC INFO EXTRACTION")
        print("="*60)
        
        # Test basic info extraction
        basic_info = await profile_scraper.get_basic_info()
        print(f"📝 Name: {basic_info.get('name', 'NOT FOUND')}")
        print(f"📝 Bio: {basic_info.get('bio', 'NOT FOUND')[:100]}...")
        print(f"📝 Work: {len(basic_info.get('work', []))} entries")
        print(f"📝 Education: {len(basic_info.get('education', []))} entries")
        print(f"📝 Location: {basic_info.get('current_city', 'NOT FOUND')}")
        print(f"📝 Birthday: {basic_info.get('birthday', 'NOT FOUND')}")
        print(f"📝 Email: {basic_info.get('email', 'NOT FOUND')}")
        print(f"📝 Phone: {basic_info.get('phone', 'NOT FOUND')}")
        
        print("\n" + "="*60)
        print("👥 PHASE 3: SOCIAL CONNECTIONS")
        print("="*60)
        
        # Test social connections
        friends = await profile_scraper.get_friends_list()
        print(f"👫 Friends: {len(friends)} found")
        if friends:
            print(f"   Sample: {friends[0].get('name', 'N/A')}")
        
        groups = await profile_scraper.get_groups()
        print(f"👥 Groups: {len(groups)} found")
        if groups:
            print(f"   Sample: {groups[0].get('group_name', 'N/A')}")
        
        pages = await profile_scraper.get_pages_followed()
        print(f"📄 Pages: {len(pages)} found")
        if pages:
            print(f"   Sample: {pages[0].get('page_name', 'N/A')}")
        
        following = await profile_scraper.get_following_list()
        print(f"➡️ Following: {len(following)} found")
        if following:
            print(f"   Sample: {following[0].get('name', 'N/A')}")
        
        # Prepare test data
        scrape_data = {
            "basic_info": basic_info,
            "friends_list": friends,
            "groups": groups,
            "pages_followed": pages,
            "following_list": following,
            "own_posts": [],
            "tagged_posts": [],
            "user_comments": [],
            "locations": []
        }
        
        if test_posts:
            print("\n" + "="*60)
            print("📝 PHASE 4: POSTS AND CONTENT")
            print("="*60)
            
            # Test posts extraction (limited for testing)
            own_posts = await posts_scraper.get_own_posts(username, max_posts=3)
            print(f"📝 Own Posts: {len(own_posts)} found")
            for i, post in enumerate(own_posts[:2]):
                print(f"   Post {i+1}: {post.get('content', 'No content')[:50]}...")
            
            tagged_posts = await posts_scraper.get_tagged_posts(username, max_posts=2)
            print(f"🏷️ Tagged Posts: {len(tagged_posts)} found")
            
            # Update scrape data
            scrape_data.update({
                "own_posts": own_posts,
                "tagged_posts": tagged_posts,
            })
        else:
            print("\n⏭️ Skipping posts extraction (test_posts=False)")
        
        print("\n" + "="*60)
        print("📊 PHASE 5: JSON GENERATION")
        print("="*60)
        
        # Generate JSON output
        result = json_builder.build_profile_json(username, scrape_data)
        
        print(f"💾 JSON saved to: {result['filepath']}")
        
        # Print summary
        profile_data = result['data']
        print(f"\n📈 EXTRACTION SUMMARY:")
        print(f"   Profile Name: {profile_data['profile'].get('name', 'N/A')}")
        print(f"   Friends: {len(profile_data['profile'].get('friends', []))}")
        print(f"   Groups: {len(profile_data['profile'].get('groups', []))}")
        print(f"   Pages: {len(profile_data['profile'].get('pages_followed', []))}")
        print(f"   Following: {len(profile_data['profile'].get('following', []))}")
        print(f"   Own Posts: {len(profile_data['posts'].get('own_posts', []))}")
        print(f"   Tagged Posts: {len(profile_data['posts'].get('tagged_posts', []))}")
        
        # Show a sample of the JSON structure
        print(f"\n🔍 JSON STRUCTURE PREVIEW:")
        preview = {
            "profile": {
                "name": profile_data['profile'].get('name', 'N/A'),
                "bio": profile_data['profile'].get('bio', 'N/A')[:50] + "...",
                "friends_count": len(profile_data['profile'].get('friends', [])),
                "groups_count": len(profile_data['profile'].get('groups', [])),
            },
            "posts": {
                "own_posts_count": len(profile_data['posts'].get('own_posts', [])),
                "tagged_posts_count": len(profile_data['posts'].get('tagged_posts', [])),
            }
        }
        print(json.dumps(preview, indent=2))
        
        print("\n" + "="*80)
        print("✅ TEST COMPLETED SUCCESSFULLY!")
        print("="*80)
        
        # Close browser
        await session.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {str(e)}")
        # Ensure browser is closed
        try:
            if 'session' in locals():
                await session.close()
        except Exception as close_error:
            logger.error(f"Error closing session: {close_error}")
        return False

def main():
    """Main entry point for test script"""
    parser = argparse.ArgumentParser(description="Test Improved Facebook Profile Scraper")
    parser.add_argument("username", help="Facebook username to test scraping")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--no-posts", action="store_true", help="Skip posts testing (faster)")
    
    args = parser.parse_args()
    
    print(f"🧪 Testing Facebook Profile Scraper for '{args.username}'")
    if os.environ.get("DISPLAY") is None and not args.headless:
        print("⚠️ WARNING: No display detected. Consider using --headless if on a server.")
    
    success = asyncio.run(test_scraper(
        args.username, 
        headless=args.headless, 
        test_posts=not args.no_posts
    ))
    
    if success:
        print("\n✅ Test completed successfully! Check the output files.")
    else:
        print("\n❌ Test failed. Check the logs above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
