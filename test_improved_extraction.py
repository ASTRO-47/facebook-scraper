#!/usr/bin/env python3
"""
Quick test to see if the improved content extraction is working for all posts
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.session import FacebookSession
from scraper.posts_improved import PostsScraperImproved
from scraper.utils import ScraperUtils

async def test_improved_extraction():
    """Test improved content extraction"""
    
    print("🧪 Testing Improved Content Extraction")
    
    session = FacebookSession(headless=False)
    
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
        
        # Create scraper
        scraper = PostsScraperImproved(page, utils)
        
        # Navigate to profile
        await page.goto("https://www.facebook.com/srikanth767")
        await asyncio.sleep(5)
        
        print("📊 Testing extraction of first 3 posts...")
        
        # Get posts
        posts = await page.query_selector_all('[role="article"]')
        if not posts:
            print("❌ No posts found")
            return
        
        print(f"✅ Found {len(posts)} posts")
        
        # Test extraction on first 3 posts
        for i, post_element in enumerate(posts[:3]):
            print(f"\n🔍 TESTING POST {i+1}:")
            print("=" * 50)
            
            try:
                # Use the improved comprehensive extraction
                post_data = await scraper._extract_comprehensive_post_data(post_element)
                
                print(f"📋 Extracted Data:")
                print(f"   ID: {post_data.get('id', 'MISSING')}")
                print(f"   Timestamp: {post_data.get('timestamp', 'MISSING')}")
                print(f"   Content: {post_data.get('content', 'MISSING')[:100]}...")
                print(f"   URL: {post_data.get('original_url', 'MISSING')[:60]}...")
                print(f"   Tagged: {len(post_data.get('tagged_accounts', []))} accounts")
                print(f"   Valid: {scraper._is_valid_comprehensive_post(post_data)}")
                
                # Show formatted version
                formatted = scraper._format_own_post(post_data)
                print(f"\n📄 Formatted JSON snippet:")
                print(json.dumps({
                    "id": formatted["id"],
                    "timestamp": formatted["timestamp"],
                    "content": formatted["content"][:100] + "..." if len(formatted["content"]) > 100 else formatted["content"],
                    "original_url": formatted["original_url"]
                }, indent=2))
                
            except Exception as e:
                print(f"❌ Error extracting post {i+1}: {e}")
        
        input("\n⏸️ Press Enter to continue...")
        
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(test_improved_extraction())
