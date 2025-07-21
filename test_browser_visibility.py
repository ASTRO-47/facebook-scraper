#!/usr/bin/env python3
"""
Test script to verify browser visibility
"""

import asyncio
from scraper.session import FacebookSession

async def test_browser_visibility():
    """Test that browser opens in visible mode by default"""
    print("🚀 Testing browser visibility...")
    print("📋 This test will:")
    print("   1. Initialize a Facebook session with default settings")
    print("   2. Open a browser window (should be visible)")
    print("   3. Navigate to Facebook")
    print("   4. Wait 10 seconds for you to see the browser")
    print("   5. Close the browser")
    
    # Initialize session with defaults (should be headless=False now)
    session = FacebookSession()
    
    print(f"🔧 Headless mode: {session.headless}")
    print("🌐 Opening browser...")
    
    try:
        # Initialize browser
        page = await session.initialize()
        print("✅ Browser opened successfully!")
        
        if not session.headless:
            print("👁️  Browser should be visible on your screen!")
        else:
            print("🤖 Browser is running in headless mode")
        
        # Navigate to Facebook
        print("🌐 Navigating to Facebook...")
        await page.goto("https://www.facebook.com")
        
        print("⏳ Keeping browser open for 10 seconds...")
        print("   You should see the Facebook login page!")
        await asyncio.sleep(10)
        
    finally:
        print("🔄 Closing browser...")
        if session.context:
            await session.context.close()
        print("✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_browser_visibility())
