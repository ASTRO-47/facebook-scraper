#!/usr/bin/env python3
"""
Debug Facebook posts extraction issue
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_facebook_posts(username="srikanth767"):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Navigate to the profile
            url = f"https://www.facebook.com/{username}"
            print(f"🌐 Navigating to: {url}")
            
            await page.goto(url, wait_until="networkidle")
            await asyncio.sleep(5)
            
            # Check if login is required
            login_form = await page.query_selector('form[data-testid="royal_login_form"]')
            if login_form:
                print("❌ Login required - Facebook is not logged in")
                return
            
            # Check if profile exists
            title = await page.title()
            print(f"📄 Page title: {title}")
            
            # Look for posts container
            posts_selectors = [
                '[role="main"] [data-pagelet="ProfileTimeline"]',
                '[role="main"] div[data-testid="royalSlide"]',
                '[role="feed"]',
                '[data-testid="story-wrap"]',
                'div[data-testid*="post"]',
                'div[role="article"]',
                'div[data-pagelet*="FeedUnit"]'
            ]
            
            posts_found = False
            for selector in posts_selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"✅ Found {len(elements)} elements with selector: {selector}")
                    posts_found = True
                    break
                else:
                    print(f"❌ No elements found with selector: {selector}")
            
            if not posts_found:
                print("❌ No posts container found")
                # Save page content for debugging
                content = await page.content()
                with open("debug_facebook_page.html", "w", encoding="utf-8") as f:
                    f.write(content)
                print("📁 Saved page content to debug_facebook_page.html")
            
            # Check for specific Facebook elements
            profile_elements = [
                'h1',  # Profile name
                '[data-testid="cover"]',  # Cover photo
                'div[data-overviewsection="about"]',  # About section
                'a[aria-label*="Friends"]',  # Friends link
                'div[role="tablist"]'  # Navigation tabs
            ]
            
            print("\n🔍 Checking for Facebook profile elements:")
            for selector in profile_elements:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content() if element else ""
                    print(f"✅ Found: {selector} - Text: {text[:50]}...")
                else:
                    print(f"❌ Not found: {selector}")
            
            await asyncio.sleep(10)  # Keep browser open for inspection
            
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_facebook_posts())
