#!/usr/bin/env python3
"""
Test script for the improved post extraction functionality
"""
import asyncio
import json
from playwright.async_api import async_playwright
from scraper.posts import PostsScraper
from scraper.utils import ScraperUtils

async def test_post_extraction():
    """Test the improved post extraction on a sample Facebook profile"""
    
    print("🧪 Testing improved post extraction...")
    
    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        # Initialize utilities and scraper
        utils = ScraperUtils(page)
        posts_scraper = PostsScraper(page, utils)
        
        try:
            # Navigate to a public Facebook page for testing
            print("📱 Navigating to Facebook...")
            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
            await asyncio.sleep(3)
            
            # Test the post extraction improvements on any visible posts
            print("🔍 Looking for post elements...")
            post_elements = await page.query_selector_all('div[role="article"]')
            
            if post_elements:
                print(f"✅ Found {len(post_elements)} post elements")
                
                # Test extraction on first few posts
                for i, post_element in enumerate(post_elements[:3]):
                    print(f"\n📝 Testing post {i+1}...")
                    
                    try:
                        post_data = await posts_scraper._extract_single_post(post_element, "test_posts")
                        
                        if post_data:
                            print(f"   ✅ Successfully extracted post:")
                            print(f"      - ID: {post_data.get('id', 'N/A')}")
                            print(f"      - Content length: {len(post_data.get('content', ''))}")
                            print(f"      - Timestamp: {post_data.get('timestamp', 'N/A')}")
                            print(f"      - Tagged accounts: {len(post_data.get('tagged_accounts', []))}")
                            print(f"      - Comments: {len(post_data.get('comments', []))}")
                            print(f"      - Location: {post_data.get('location_tagged', 'N/A')}")
                            print(f"      - Reactions: {post_data.get('reactions', {}).get('total', 0)}")
                            print(f"      - Shared: {post_data.get('shared', False)}")
                            
                            # Save sample post data
                            with open(f"/root/facebook-scraper/static/sample_post_{i+1}.json", "w") as f:
                                json.dump(post_data, f, indent=2, ensure_ascii=False)
                                
                        else:
                            print(f"   ❌ Failed to extract post {i+1}")
                            
                    except Exception as e:
                        print(f"   ❌ Error extracting post {i+1}: {e}")
            else:
                print("❌ No post elements found")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            
        finally:
            await browser.close()
            
    print("\n🏁 Test completed!")

if __name__ == "__main__":
    asyncio.run(test_post_extraction())
