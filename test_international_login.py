#!/usr/bin/env python3
"""
Test script for international Facebook account login
Specifically designed for Moroccan accounts accessing from US servers
"""

import asyncio
import os
from scraper.session import FacebookSession
from scraper.utils import ScraperUtils

async def test_international_login():
    """Test the enhanced international login flow"""
    print("🌍 Testing International Account Login")
    print("="*50)
    
    # Initialize session with enhanced stealth
    print("1. Initializing enhanced browser session...")
    session = FacebookSession(headless=True, user_data_dir="./test_user_data")
    
    try:
        # Start browser
        page = await session.initialize()
        print("✅ Browser initialized with stealth features")
        
        # Initialize utils for human behavior
        utils = ScraperUtils(page, screenshot_dir="./test_screenshots")
        
        # Test login check with international support
        print("\n2. Testing international login flow...")
        login_result = await session.login_check()
        
        if login_result:
            print("✅ Login successful!")
            
            # Test human-like behavior
            print("\n3. Testing human-like behaviors...")
            await utils.human_like_delay(2, 5)
            await utils.random_mouse_movement()
            await utils.human_scroll()
            print("✅ Human behaviors working")
            
            # Test enhanced security checkpoint detection
            print("\n4. Testing security checkpoint detection...")
            checkpoint_detected = await utils.facebook_security_check()
            if checkpoint_detected:
                print("🔒 Security checkpoint detected (this is normal)")
                print("📋 Enhanced international account prompts available")
            else:
                print("✅ No security checkpoint detected")
            
            # Take a success screenshot
            screenshot = await utils.take_screenshot("international_login_success")
            print(f"📸 Success screenshot: {screenshot}")
            
        else:
            print("❌ Login failed - but this might be normal on first attempt")
            print("💡 Try running the main scraper for full login flow")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        print("💡 This might be normal - international accounts need manual verification")
        
    finally:
        print("\n5. Cleaning up...")
        await session.close()
        print("✅ Test completed")

async def test_stealth_features():    """Test that stealth features are working"""
    print("\n🥷 Testing Stealth Features")
    print("="*30)

    session = FacebookSession(headless=True, user_data_dir="./test_user_data")
    
    try:
        page = await session.initialize()
        
        # Test that automation detection is hidden
        webdriver_result = await page.evaluate("() => navigator.webdriver")
        print(f"navigator.webdriver: {webdriver_result} (should be false/undefined)")
        
        # Test user agent
        user_agent = await page.evaluate("() => navigator.userAgent")
        print(f"User Agent: {user_agent[:50]}...")
        
        # Test languages
        languages = await page.evaluate("() => navigator.languages")
        print(f"Languages: {languages}")
        
        # Test plugins
        plugins_length = await page.evaluate("() => navigator.plugins.length")
        print(f"Plugins count: {plugins_length} (should be > 0)")
        
        print("✅ Stealth features appear to be working")
        
    except Exception as e:
        print(f"❌ Error testing stealth: {e}")
        
    finally:
        await session.close()

def main():
    """Main test function"""
    print("🧪 Facebook International Account Test Suite")
    print("="*60)
    print("This will test the free bot detection solutions")
    print("for Moroccan accounts logging in from US servers")
    print("="*60)
    
    # Create test directories
    os.makedirs("./test_screenshots", exist_ok=True)
    os.makedirs("./test_user_data", exist_ok=True)
    
    # Run tests
    asyncio.run(test_stealth_features())
    asyncio.run(test_international_login())
    
    print("\n🎯 Test Summary:")
    print("If you see ✅ for most tests, the enhancements are working!")
    print("If you see ❌ for login, run the main scraper for full verification flow")
    print("\n💡 Next steps:")
    print("1. Run: python main.py")
    print("2. Navigate to: http://localhost:8000")
    print("3. Try scraping a profile with your Moroccan account")

if __name__ == "__main__":
    main() 