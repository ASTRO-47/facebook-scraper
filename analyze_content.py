#!/usr/bin/env python3
"""
Facebook 2024 Content Extraction Analyzer
Analyzes the current DOM structure to find the best selectors
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.session import FacebookSession

async def analyze_content_extraction():
    """Analyze how Facebook structures content in 2024"""
    
    print("🔬 Facebook 2024 Content Analysis")
    
    session = FacebookSession(headless=False)
    
    try:
        await session.initialize()
        page = session.page
        
        # Load cookies
        cookies_file = "facebook_cookies.json"
        if os.path.exists(cookies_file):
            with open(cookies_file, 'r') as f:
                cookie_data = json.load(f)
            await session.context.add_cookies(cookie_data['cookies'])
        
        # Check login
        is_logged_in = await session.login_check()
        if not is_logged_in:
            print("❌ Not logged in")
            return
        
        # Navigate to profile
        await page.goto("https://www.facebook.com/srikanth767")
        await asyncio.sleep(5)
        
        print("📋 Analyzing Content Structure...")
        
        # Find first post
        posts = await page.query_selector_all('[role="article"]')
        if not posts:
            print("❌ No posts found")
            return
        
        first_post = posts[0]
        print(f"✅ Found {len(posts)} posts, analyzing first one...")
        
        # Method 1: Check all text content
        print("\n🔍 Method 1: Raw Text Analysis")
        all_text = await first_post.text_content()
        lines = [line.strip() for line in all_text.split('\n') if line.strip()]
        print(f"Total lines: {len(lines)}")
        
        content_candidates = []
        for i, line in enumerate(lines[:20]):
            if 10 < len(line) < 200 and not any(ui in line for ui in ['Like', 'Comment', 'Share', 'ago']):
                content_candidates.append((i, line))
                print(f"   Candidate {i}: {line[:80]}...")
        
        # Method 2: Specific selector analysis
        print(f"\n🔍 Method 2: Selector Analysis")
        
        selectors_to_test = [
            ('div[data-ad-preview="message"]', 'Facebook Ad Message'),
            ('span[dir="auto"]', 'Auto Direction Spans'),
            ('div[dir="auto"][role="presentation"]', 'Auto Direction Divs'),
            ('[data-testid="post_message"]', 'Post Message TestID'),
            ('div[style*="text-align"]', 'Text Align Divs'),
            ('.userContent', 'User Content Class'),
            ('div[class*="userContent"]', 'User Content Like Classes')
        ]
        
        for selector, description in selectors_to_test:
            try:
                elements = await first_post.query_selector_all(selector)
                print(f"   {description} ({selector}): {len(elements)} elements")
                
                for i, element in enumerate(elements[:3]):
                    text = await element.text_content()
                    if text and len(text.strip()) > 5:
                        print(f"      Element {i}: {text.strip()[:60]}...")
            except:
                print(f"   {description}: Error with selector")
        
        # Method 3: Look for content in spans with specific characteristics
        print(f"\n🔍 Method 3: Smart Span Analysis")
        
        all_spans = await first_post.query_selector_all('span')
        print(f"Total spans in post: {len(all_spans)}")
        
        content_spans = []
        for i, span in enumerate(all_spans):
            try:
                text = await span.text_content()
                if text and 15 <= len(text.strip()) <= 300:
                    # Check if it looks like content (not UI)
                    text = text.strip()
                    if not any(ui in text for ui in ['Like', 'Comment', 'Share', 'Reply', 'minutes ago', 'hours ago']):
                        content_spans.append((i, text))
            except:
                continue
        
        print(f"Found {len(content_spans)} potential content spans:")
        for i, (span_idx, text) in enumerate(content_spans[:5]):
            print(f"   Span {span_idx}: {text[:80]}...")
        
        # Method 4: Check for timestamps
        print(f"\n🔍 Method 4: Timestamp Analysis")
        
        timestamp_selectors = [
            ('a[href*="posts"]', 'Post Links'),
            ('time', 'Time Elements'), 
            ('abbr', 'Abbreviation Elements'),
            ('[data-testid*="timestamp"]', 'Timestamp TestIDs'),
            ('a[role="link"]', 'Link Role Elements')
        ]
        
        for selector, description in timestamp_selectors:
            try:
                elements = await first_post.query_selector_all(selector)
                print(f"   {description} ({selector}): {len(elements)} elements")
                
                for i, element in enumerate(elements[:3]):
                    # Check multiple attributes
                    for attr in ['title', 'aria-label', 'datetime', 'href']:
                        value = await element.get_attribute(attr)
                        if value:
                            print(f"      Element {i} {attr}: {value[:60]}...")
                    
                    text = await element.text_content()
                    if text:
                        print(f"      Element {i} text: {text.strip()[:60]}...")
            except:
                print(f"   {description}: Error with selector")
        
        input("\n⏸️ Press Enter to continue...")
        
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(analyze_content_extraction())
