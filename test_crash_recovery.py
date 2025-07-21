#!/usr/bin/env python3

"""
Test script to verify crash recovery functionality in posts scraper
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.session import FacebookSession
from scraper.posts_improved import PostsScraperImproved
from scraper.utils import ScraperUtils

async def test_crash_recovery():
    """Test crash recovery functionality"""
    
    username = "srikanth767"
    
    print(f"🧪 Testing crash recovery for: {username}")
    
    # Create user data directory
    user_data_dir = os.path.join(os.path.expanduser("~"), ".facebook_scraper_data")
    os.makedirs(user_data_dir, exist_ok=True)
    
    # Initialize session
    session = FacebookSession(headless=True, user_data_dir=user_data_dir)
    page = await session.initialize()
    
    try:
        # Load saved cookies
        cookies_file = "facebook_cookies.json"
        if os.path.exists(cookies_file):
            print("🍪 Loading saved cookies...")
            import json
            with open(cookies_file, 'r') as f:
                cookie_data = json.load(f)
            await session.context.add_cookies(cookie_data['cookies'])
            print("✅ Cookies loaded successfully")
        
        # Check login
        is_logged_in = await session.login_check()
        if not is_logged_in:
            print("❌ Not logged in - cannot test")
            return False
        
        print("✅ Logged in successfully")
        
        # Initialize scraper
        utils = ScraperUtils(page)
        posts_scraper = PostsScraperImproved(page, utils)
        
        # Test page health check
        print("🔍 Testing page health check...")
        health_ok = await posts_scraper._check_page_health()
        print(f"   Health check result: {'✅ OK' if health_ok else '❌ Failed'}")
        
        if not health_ok:
            print("🔄 Testing crash recovery...")
            recovery_ok = await posts_scraper._recover_from_crash()
            print(f"   Recovery result: {'✅ OK' if recovery_ok else '❌ Failed'}")
            
            if recovery_ok:
                # Test again after recovery
                health_ok2 = await posts_scraper._check_page_health()
                print(f"   Health after recovery: {'✅ OK' if health_ok2 else '❌ Still failed'}")
        
        # Test navigation with retries
        print("🌐 Testing navigation with crash recovery...")
        profile_url = posts_scraper._construct_profile_url(username)
        nav_ok = await posts_scraper._navigate_with_retries(profile_url)
        print(f"   Navigation result: {'✅ OK' if nav_ok else '❌ Failed'}")
        
        if nav_ok:
            print("✅ Navigation successful - testing basic post detection...")
            
            # Wait for posts to load
            await posts_scraper._wait_for_posts_to_load()
            
            # Try to extract just a few posts to verify functionality
            try:
                posts = await posts_scraper._extract_current_posts_with_details('[role="main"]')
                print(f"   Posts extracted: {len(posts)}")
                
                if posts:
                    print("📝 Sample post data:")
                    sample_post = posts[0]
                    print(f"   Content: {sample_post.get('content', 'N/A')[:100]}...")
                    print(f"   URL: {sample_post.get('post_url', 'N/A')}")
                    print(f"   Tagged accounts: {len(sample_post.get('tagged_accounts', []))}")
            except Exception as e:
                print(f"❌ Post extraction test failed: {e}")
        
        return nav_ok
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        await session.close()

if __name__ == "__main__":
    result = asyncio.run(test_crash_recovery())
    if result:
        print("🎉 Crash recovery test PASSED!")
    else:
        print("❌ Crash recovery test FAILED!")
        sys.exit(1)
