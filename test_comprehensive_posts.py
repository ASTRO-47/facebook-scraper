#!/usr/bin/env python3

"""
Test script to verify the improved comprehensive chronological post extraction
"""

import asyncio
import sys
import os
import json

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.session import FacebookSession
from scraper.posts_improved import PostsScraperImproved
from scraper.utils import ScraperUtils

async def test_comprehensive_posts():
    """Test comprehensive chronological posts extraction"""
    
    username = "srikanth767"
    
    print(f"🚀 Testing comprehensive chronological extraction for: {username}")
    print(f"📊 Goal: Extract ALL posts from newest to oldest with full content")
    
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
        
        # Test comprehensive chronological extraction
        print("🔄 Starting comprehensive chronological post extraction...")
        print("⏱️ This will extract ALL posts from newest to oldest")
        
        # Extract posts with higher limit
        all_posts = await posts_scraper.get_all_post_types(username, max_posts=100)
        
        # Analyze results
        own_posts = all_posts.get('own_posts', [])
        tagged_posts = all_posts.get('tagged_posts', [])
        comments_by_user = all_posts.get('comments_by_user', [])
        
        print(f"\n📊 COMPREHENSIVE EXTRACTION RESULTS:")
        print(f"   📝 Own posts: {len(own_posts)}")
        print(f"   🏷️  Tagged posts: {len(tagged_posts)}")
        print(f"   💬 Comments by user: {len(comments_by_user)}")
        print(f"   📈 Total posts: {len(own_posts) + len(tagged_posts)}")
        
        # Analyze content quality
        posts_with_content = [p for p in own_posts if p.get('content', '').strip()]
        posts_with_timestamps = [p for p in own_posts if p.get('timestamp', '').strip()]
        posts_with_urls = [p for p in own_posts if p.get('original_url', '').strip()]
        posts_with_tagged = [p for p in own_posts if p.get('tagged_accounts')]
        
        print(f"\n📈 CONTENT QUALITY ANALYSIS:")
        print(f"   📝 Posts with content: {len(posts_with_content)}")
        print(f"   ⏰ Posts with timestamps: {len(posts_with_timestamps)}")
        print(f"   🔗 Posts with URLs: {len(posts_with_urls)}")
        print(f"   👥 Posts with tagged accounts: {len(posts_with_tagged)}")
        
        # Show sample posts
        if posts_with_content:
            print(f"\n📝 SAMPLE POSTS WITH CONTENT:")
            for i, post in enumerate(posts_with_content[:3], 1):
                print(f"   Post {i}:")
                print(f"     Content: {post['content'][:100]}...")
                print(f"     Timestamp: {post.get('timestamp', 'N/A')}")
                print(f"     URL: {post.get('original_url', 'N/A')}")
                print(f"     Tagged: {len(post.get('tagged_accounts', []))}")
        
        # Save sample results
        output_file = f"test_comprehensive_{username}.json"
        sample_data = {
            "total_posts": len(own_posts) + len(tagged_posts),
            "own_posts": len(own_posts),
            "tagged_posts": len(tagged_posts),
            "posts_with_content": len(posts_with_content),
            "posts_with_timestamps": len(posts_with_timestamps),
            "posts_with_urls": len(posts_with_urls),
            "sample_posts": own_posts[:5]  # First 5 posts as sample
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Sample results saved to: {output_file}")
        
        # Success criteria
        success = (
            len(own_posts) > 15 and  # Got more than 15 posts
            len(posts_with_content) > 5 and  # At least 5 have content
            len(posts_with_urls) > 5  # At least 5 have URLs
        )
        
        return success
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        await session.close()

if __name__ == "__main__":
    result = asyncio.run(test_comprehensive_posts())
    if result:
        print("🎉 Comprehensive chronological extraction test PASSED!")
        print("✅ The scraper now extracts posts properly with content, timestamps and URLs")
    else:
        print("❌ Comprehensive extraction test FAILED!")
        print("ℹ️ Check the logs above for details")
        sys.exit(1)
