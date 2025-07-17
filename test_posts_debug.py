#!/usr/bin/env python3
"""
Debug script for posts extraction
"""
import asyncio
import json
import sys
from playwright.async_api import async_playwright
from scraper.posts import PostsScraper
from scraper.utils import ScraperUtils

async def debug_posts_extraction(username: str):
    """Debug posts extraction for a given username"""
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        
        # Create context
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Create page
        page = await context.new_page()
        
        # Initialize scraper
        utils = ScraperUtils(page)
        posts_scraper = PostsScraper(page, utils)
        
        try:
            print(f"🔍 Testing posts extraction for: {username}")
            
            # Try to extract posts
            posts = await posts_scraper.get_own_posts(username, max_posts=10)
            
            print(f"📊 Results:")
            print(f"   - Total posts found: {len(posts)}")
            
            if posts:
                print(f"   - First post content: {posts[0].get('content', '')[:100]}...")
                print(f"   - First post timestamp: {posts[0].get('timestamp', '')}")
                print(f"   - First post likes: {posts[0].get('likes', 0)}")
            else:
                print("   - No posts found")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_posts_debug.py <username>")
        sys.exit(1)
    
    username = sys.argv[1]
    asyncio.run(debug_posts_extraction(username)) 