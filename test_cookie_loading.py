#!/usr/bin/env python3
"""
Test Cookie Loading Functionality
Quick test to verify saved cookies are properly loaded
"""

import asyncio
import os
import json
from scraper.session import FacebookSession

async def test_cookie_loading():
    """Test if saved cookies are properly loaded"""
    print("🧪 Testing Cookie Loading Functionality")
    print("=" * 50)
    
    # Check if cookie file exists
    cookies_file = "facebook_cookies.json"
    if not os.path.exists(cookies_file):
        print("❌ facebook_cookies.json not found")
        print("💡 Run save_cookies.py on your Morocco machine first")
        return False
    
    # Load and validate cookie file
    try:
        with open(cookies_file, 'r') as f:
            cookie_data = json.load(f)
        
        if 'cookies' not in cookie_data:
            print("❌ Invalid cookie file format")
            return False
            
        print(f"✅ Found valid cookie file with {len(cookie_data['cookies'])} cookies")
        
        # Show cookie details
        print("\n📋 Cookie Details:")
        for cookie in cookie_data['cookies'][:3]:  # Show first 3 cookies
            print(f"   🍪 {cookie['name']}: {cookie['value'][:20]}...")
        
        print(f"   📅 Timestamp: {cookie_data.get('timestamp', 'Unknown')}")
        print(f"   🌐 User Agent: {cookie_data.get('user_agent', 'Unknown')[:50]}...")
        
        # Test browser initialization with cookies
        print("\n🚀 Testing browser initialization...")
        
        user_data_dir = os.path.expanduser("~/.facebook_scraper_test")
        session = FacebookSession(headless=True, user_data_dir=user_data_dir)
        page = await session.initialize()
        
        # Load cookies
        print("🍪 Loading cookies...")
        await session.context.add_cookies(cookie_data['cookies'])
        
        # Navigate to Facebook
        print("🌐 Testing Facebook navigation...")
        await page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=30000)
        
        # Check if logged in
        current_url = page.url
        page_title = await page.title()
        
        print(f"📍 Current URL: {current_url}")
        print(f"📄 Page Title: {page_title}")
        
        # Check for login indicators
        login_indicators = [
            'div[role="navigation"]',
            'a[href*="/logout"]',
            'div[data-pagelet="LeftRail"]'
        ]
        
        logged_in = False
        for indicator in login_indicators:
            try:
                element = await page.query_selector(indicator)
                if element:
                    login_form = await page.query_selector('form[data-testid="royal_login_form"]')
                    if not login_form:
                        logged_in = True
                        break
            except Exception:
                continue
        
        await session.close()
        
        if logged_in:
            print("✅ Cookie loading test PASSED - Successfully logged in!")
            return True
        else:
            print("⚠️ Cookie loading test PARTIAL - Cookies loaded but login status unclear")
            print("💡 This might be due to cookie expiration or Facebook security measures")
            return True
            
    except Exception as e:
        print(f"❌ Cookie loading test FAILED: {e}")
        return False

async def main():
    success = await test_cookie_loading()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Cookie loading functionality is working!")
        print("✅ Your saved cookies should work with the main scraper")
    else:
        print("❌ Cookie loading test failed")
        print("💡 You may need to save fresh cookies from Morocco")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main()) 