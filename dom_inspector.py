#!/usr/bin/env python3
"""
Quick DOM inspector to see Facebook's current post structure
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.session import FacebookSession

async def inspect_facebook_dom():
    """Inspect Facebook's current DOM structure"""
    
    print("🔍 Facebook DOM Inspector - Finding Current Post Selectors")
    
    session = FacebookSession(headless=False)
    
    try:
        await session.initialize()
        page = session.page
        
        # Load cookies and login
        cookies_file = "facebook_cookies.json"
        if os.path.exists(cookies_file):
            with open(cookies_file, 'r') as f:
                cookie_data = json.load(f)
            await session.context.add_cookies(cookie_data['cookies'])
        
        is_logged_in = await session.login_check()
        if not is_logged_in:
            print("❌ Not logged in")
            return
        
        # Navigate to profile
        await page.goto("https://www.facebook.com/srikanth767")
        await asyncio.sleep(5)
        
        # Get all possible post containers
        print("\n🏷️ Finding Post Containers...")
        
        post_container_selectors = [
            '[data-pagelet^="FeedUnit"]',
            '[data-testid="story"]',
            '[role="article"]',
            'div[class*="userContentWrapper"]',
            'div[data-testid*="post"]'
        ]
        
        for selector in post_container_selectors:
            elements = await page.query_selector_all(selector)
            print(f"   {selector}: {len(elements)} elements")
            
        # Inspect the first post
        first_post = await page.query_selector('[data-pagelet^="FeedUnit"]')
        if first_post:
            print(f"\n📝 Analyzing First Post Structure...")
            
            # Get all spans and divs within the post
            spans = await first_post.query_selector_all('span')
            divs = await first_post.query_selector_all('div')
            
            print(f"   Found {len(spans)} spans, {len(divs)} divs")
            
            # Look for content patterns
            print("\n📋 Text Content Analysis:")
            for i, span in enumerate(spans[:10]):  # First 10 spans
                text = await span.text_content()
                if text and len(text.strip()) > 5:
                    print(f"   Span {i}: {text.strip()[:100]}...")
            
            # Look for selectors with data attributes
            print(f"\n🏷️ Data Attributes Analysis:")
            data_elements = await first_post.query_selector_all('[data-testid]')
            print(f"   Elements with data-testid: {len(data_elements)}")
            
            for element in data_elements[:5]:
                testid = await element.get_attribute('data-testid')
                text = await element.text_content()
                if text and len(text.strip()) > 5:
                    print(f"   data-testid='{testid}': {text.strip()[:50]}...")
        
        input("\n⏸️ Press Enter to continue...")
        
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(inspect_facebook_dom())
