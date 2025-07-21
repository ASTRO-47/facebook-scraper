#!/usr/bin/env python3
"""
Direct test of the main scraper to see the full output structure
"""
import asyncio
import json
import sys
import os

# Add the project root to the Python path
sys.path.append('/root/facebook-scraper')

async def test_full_scraper(username="srikanth767"):
    """Test the full scraper pipeline"""
    try:
        # Import the scraper function from main
        from main import scrape_profile
        
        print(f"🚀 Testing full scraper for {username}...")
        
        # Run the full scraper (this includes profile + posts)
        result = await scrape_profile(username, headless=True)
        
        print("📊 Full Scraper Results:")
        print(f"Success: {result.get('success', False)}")
        print(f"Username: {result.get('username', 'N/A')}")
        
        if result.get('success'):
            data = result.get('data', {})
            
            # Profile info
            profile = data.get('profile', {})
            print(f"\n👤 Profile: {profile.get('name', 'N/A')}")
            print(f"Bio: {profile.get('bio', 'N/A')}")
            
            # Posts info
            posts = data.get('posts', {})
            print(f"\n📝 Posts:")
            print(f"  Own posts: {len(posts.get('own_posts', []))}")
            print(f"  Tagged posts: {len(posts.get('tagged_posts', []))}")
            print(f"  Comments by user: {len(posts.get('comments_by_user', []))}")
            
            # Show sample posts with content
            own_posts = posts.get('own_posts', [])
            if own_posts:
                print(f"\n📄 Sample Posts:")
                for i, post in enumerate(own_posts[:3]):
                    print(f"  Post {i+1}:")
                    print(f"    ID: {post.get('id', 'N/A')}")
                    print(f"    Content: {post.get('content', 'N/A')[:100]}...")
                    print(f"    URL: {post.get('original_url', 'N/A')}")
                    print(f"    Timestamp: {post.get('timestamp', 'N/A')}")
                    tagged = post.get('tagged_accounts', [])
                    print(f"    Tagged: {len(tagged)} accounts")
                    if tagged:
                        print(f"      - {tagged[0].get('name', 'N/A')}")
            
            # Locations
            locations = data.get('locations_visited', [])
            print(f"\n📍 Locations visited: {len(locations)}")
            
            # Save full results
            output_file = f"full_scraper_test_{username}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Full results saved to {output_file}")
        else:
            print(f"❌ Scraping failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_full_scraper())
