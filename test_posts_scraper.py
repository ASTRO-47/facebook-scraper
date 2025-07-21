#!/usr/bin/env python3
"""
Quick test of the updated posts scraper to see if it extracts content
"""
import asyncio
from playwright.async_api import async_playwright
import json
import sys
import os

# Add the project root to the Python path
sys.path.append('/root/facebook-scraper')

from scraper.posts_improved import PostsScraperImproved
from scraper.utils import ScraperUtils

async def test_posts_scraper(username="srikanth767"):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        context = await browser.new_context()
        
        # Load cookies
        cookies_file = "/root/facebook-scraper/data/facebook_cookies.json"
        if os.path.exists(cookies_file):
            print("🍪 Loading cookies...")
            with open(cookies_file, 'r') as f:
                cookie_data = json.load(f)
            await context.add_cookies(cookie_data['cookies'])
        
        page = await context.new_page()
        
        try:
            # Initialize scraper
            utils = ScraperUtils(page, screenshot_dir="test_output")
            scraper = PostsScraperImproved(page, utils)
            
            print(f"🔍 Testing posts extraction for {username}...")
            
            # Test the extraction
            posts_data = await scraper.get_all_post_types(username, max_posts=5)
            
            print("\n📊 Results:")
            print(f"Own posts: {len(posts_data.get('own_posts', []))}")
            print(f"Tagged posts: {len(posts_data.get('tagged_posts', []))}")
            print(f"Comments by user: {len(posts_data.get('comments_by_user', []))}")
            
            # Show sample data
            for section, posts in posts_data.items():
                if posts:
                    print(f"\n📝 Sample from {section}:")
                    sample_post = posts[0]
                    print(f"  ID: {sample_post.get('id', 'N/A')}")
                    print(f"  Content: {sample_post.get('content', 'N/A')[:100]}...")
                    print(f"  Timestamp: {sample_post.get('timestamp', 'N/A')}")
                    break
            
            # Save results
            output_file = f"test_posts_output_{username}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(posts_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Full results saved to {output_file}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_posts_scraper())
