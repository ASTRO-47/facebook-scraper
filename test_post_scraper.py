#!/usr/bin/env python3
"""
Test script for the improved post extraction functionality
"""
import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright

# Make sure the scraper module can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.join(__file__, '..'))))

from scraper.session import FacebookSession
from scraper.posts import PostsScraper
from scraper.utils import ScraperUtils

async def test_post_extraction(username: str):
    """Test the improved post extraction on a sample Facebook profile"""
    
    print(f"🧪 Testing improved post extraction for user: {username}...")
    
    session = FacebookSession(headless=True)
    await session.initialize()

    is_logged_in = await session.login_check()
    if not is_logged_in:
        print("❌ Not logged in. Please run login_manual.py first.")
        await session.close()
        return

    print("✅ Logged in successfully.")

    posts_scraper = PostsScraper(session.page, ScraperUtils(session.page))
    
    try:
        print(f"🔗 Navigating to profile: {username}")
        await posts_scraper.navigate_to_profile(username)
        
        print("🚀 Starting post extraction...")
        # Focus only on posts
        posts = await posts_scraper.get_all_post_types(username, max_posts=50)
        
        own_posts = posts.get("own_posts", [])
        shared_posts = posts.get("shared_posts", [])
        tagged_posts = posts.get("tagged_posts", [])

        print(f"\n✅ Extraction Complete!")
        print(f"   - Own Posts: {len(own_posts)}")
        print(f"   - Shared Posts: {len(shared_posts)}")
        print(f"   - Tagged Posts: {len(tagged_posts)}")

        # Save sample post data
        output_dir = "test_output"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{username}_posts_test.json")
        with open(output_path, "w", encoding='utf-8') as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)
        print(f"💾 Test results saved to: {output_path}")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        
    finally:
        await session.close()
        
    print("\n🏁 Test completed!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_to_scrape = sys.argv[1]
        asyncio.run(test_post_extraction(user_to_scrape))
    else:
        print("Please provide a Facebook username to test.")
        print("Usage: python test_post_scraper.py <username>")
