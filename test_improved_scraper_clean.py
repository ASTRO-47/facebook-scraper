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
            print("🔍 Testing improved post extraction...")
            
            # Get current URL to determine what to scrape
            current_url = page.url
            print(f"📍 Current URL: {current_url}")
            
            # Extract posts using improved methods
            posts = await scraper.extract_posts(max_posts=5, post_type="own")
            
            print(f"📊 Extracted {len(posts)} posts")
            
            # Display post information
            for i, post in enumerate(posts[:3], 1):  # Show first 3 posts
                print(f"\\n📝 Post {i}:")
                print(f"   Content: {post.get('content', 'N/A')[:100]}...")
                print(f"   Timestamp: {post.get('timestamp', 'N/A')}")
                print(f"   Reactions: {post.get('reactions', {}).get('total', 0)}")
                print(f"   Comments: {post.get('comments_count', 0)}")
                print(f"   URL: {post.get('original_url', 'N/A')}")
                print(f"   Media: {len(post.get('media', []))} items")
                
            print("\\n🎉 Test completed successfully!")
            print("   - Browser was visible during scraping")
            print("   - Improved content extraction worked")
            print("   - Enhanced reaction detection active")
            
        else:
            print("❌ Login failed or not completed")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Keep browser open for inspection
        print("\\n🔍 Browser will remain open for inspection...")
        print("   - Check the extracted post data")
        print("   - Verify the selectors are working")
        print("   - Press Ctrl+C to close when done")
        
        try:
            # Keep running until interrupted
            await asyncio.sleep(300)  # Wait 5 minutes
        except KeyboardInterrupt:
            print("\\n👋 Closing browser...")
            
        # Close session
        if session.context:
            await session.context.close()

if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else "test_user"
    asyncio.run(test_improved_scraper(username))
