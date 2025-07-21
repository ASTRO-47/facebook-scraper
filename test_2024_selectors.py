#!/usr/bin/env python3
"""
Test Facebook 2024 DOM selectors - headless mode
"""
import asyncio
from scraper.session import FacebookSession
from scraper.posts_improved import PostsScraperImproved
from scraper.utils import ScraperUtils

async def test_2024_selectors():
    """Test the updated Facebook 2024 selectors in headless mode"""
    
    print("🚀 Testing Facebook 2024 DOM selectors (headless mode)...")
    
    try:
        # Initialize Facebook session in headless mode
        session = FacebookSession(
            headless=True,  # Headless mode
            user_data_dir="./user_data"
        )
        
        print("🔄 Initializing browser session...")
        page = await session.initialize()
        
        print("🔑 Loading saved cookies...")
        await session.load_session_cookies()
        
        print("🌐 Navigating to Facebook...")
        await page.goto("https://www.facebook.com", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)
        
        # Initialize scraper and utils
        utils = ScraperUtils(page, session)
        scraper = PostsScraperImproved(page, utils)
        
        print("📊 Testing updated selectors on a sample profile...")
        
        # Navigate to a test profile
        profile_url = scraper._construct_profile_url("srikanth767")
        print(f"🌐 Navigating to: {profile_url}")
        
        await page.goto(profile_url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(5)  # Wait for page to fully load
        
        # Test the new post detection selectors
        print("🔍 Testing new post detection selectors...")
        
        post_selectors = [
            'div.x1rg5ohu.x1iyjqo2.x6ikm8r.x10wlt62.xv54qhq',  # Main post containers
            'div.xqcrz7y.x1c9tyrk.xeusxvb.x1pahc9y.x1ertn4p.x1lliihq.xbelrpt.xr9ek0c.x1n2onr6',  # Comment containers
            'div[role="article"]',  # Fallback
        ]
        
        total_elements_found = 0
        best_selector = None
        
        for i, selector in enumerate(post_selectors):
            try:
                elements = await page.query_selector_all(selector)
                count = len(elements)
                total_elements_found += count
                print(f"   Selector {i+1}: '{selector}' -> {count} elements")
                
                if count > 0 and not best_selector:
                    best_selector = selector
                    
            except Exception as e:
                print(f"   Selector {i+1}: Failed - {e}")
        
        print(f"\n🎯 Total elements found: {total_elements_found}")
        print(f"🏆 Best working selector: {best_selector}")
        
        # Test content extraction on first element if found
        if best_selector:
            print(f"\n🧪 Testing content extraction with best selector...")
            elements = await page.query_selector_all(best_selector)
            
            if elements:
                test_element = elements[0]
                
                # Test timestamp extraction
                print("🕒 Testing timestamp extraction...")
                timestamp = await scraper._extract_enhanced_timestamp(test_element)
                print(f"   Extracted timestamp: '{timestamp}'")
                
                # Test content extraction  
                print("📝 Testing content extraction...")
                content = await scraper._extract_enhanced_post_content(test_element)
                print(f"   Extracted content: '{content[:100]}{'...' if len(content) > 100 else ''}'")
                
                # Test content quality scoring
                if content:
                    score = scraper._score_content_quality(content)
                    print(f"   Content quality score: {score:.2f}")
                    
                    is_valid = scraper._is_actual_post_content(content)
                    print(f"   Is valid content: {is_valid}")
        
        print("\n✅ Facebook 2024 selector test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        
    finally:
        try:
            await session.close()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_2024_selectors())
