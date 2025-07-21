#!/usr/bin/env python3
"""
Direct test of the scraper without FastAPI to debug the content extraction
"""

import asyncio
import json
import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.session import FacebookSession
from scraper.posts_improved import PostsScraperImproved
from scraper.utils import ScraperUtils

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

async def direct_scraper_test():
    """Direct test of the scraper"""
    
    print("🧪 Direct Scraper Test (Headless)")
    
    session = FacebookSession(headless=True)  # Force headless for server
    
    try:
        await session.initialize()
        page = session.page
        utils = ScraperUtils(page)
        
        # Load cookies
        cookies_file = "facebook_cookies.json"
        if os.path.exists(cookies_file):
            with open(cookies_file, 'r') as f:
                cookie_data = json.load(f)
            await session.context.add_cookies(cookie_data['cookies'])
        
        # Check login
        is_logged_in = await session.login_check()
        if not is_logged_in:
            print("❌ Not logged in")
            return
        
        print("✅ Logged in successfully")
        
        # Create scraper
        scraper = PostsScraperImproved(page, utils)
        
        print("🔍 Starting extraction...")
        
        # Use the main extraction method
        result = await scraper.get_all_post_types("srikanth767", max_posts=5)
        
        print("📊 Extraction Results:")
        print(f"   Own posts: {len(result.get('own_posts', []))}")
        print(f"   Tagged posts: {len(result.get('tagged_posts', []))}")
        print(f"   Comments: {len(result.get('comments_by_user', []))}")
        
        # Show details of first few posts
        own_posts = result.get('own_posts', [])
        for i, post in enumerate(own_posts[:3]):
            print(f"\nPost {i+1}:")
            print(f"  ID: {post.get('id', 'MISSING')}")
            print(f"  Content: {post.get('content', 'MISSING')[:80]}...")
            print(f"  Timestamp: {post.get('timestamp', 'MISSING')}")
            print(f"  URL: {post.get('original_url', 'MISSING')[:60]}...")
        
        # Save full result
        with open('test_output/improved_extraction_test.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n💾 Full result saved to test_output/improved_extraction_test.json")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await session.close()
        print("🔒 Session closed")

if __name__ == "__main__":
    asyncio.run(direct_scraper_test())
