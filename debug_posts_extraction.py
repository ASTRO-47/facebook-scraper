#!/usr/bin/env python3
"""
Debug script to analyze why content extraction is failing for posts after the first one
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.session import FacebookSession

async def debug_posts_extraction():
    """Debug posts extraction to find the issue with subsequent posts"""
    
    print("🐛 Debugging Posts Content Extraction")
    
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
        
        print("📋 Analyzing Multiple Posts...")
        
        # Find posts
        posts = await page.query_selector_all('[role="article"]')
        if not posts:
            print("❌ No posts found")
            return
        
        print(f"✅ Found {len(posts)} posts, analyzing each one...")
        
        for i, post in enumerate(posts[:5]):  # Analyze first 5 posts
            print(f"\n🔍 POST {i+1} ANALYSIS:")
            print("=" * 50)
            
            # Method 1: Get all text content
            all_text = await post.text_content()
            lines = [line.strip() for line in all_text.split('\n') if line.strip()]
            print(f"📝 Total lines of text: {len(lines)}")
            
            # Show first few meaningful lines
            meaningful_lines = []
            for line in lines:
                if 10 < len(line) < 200 and not any(ui in line.lower() for ui in ['like', 'comment', 'share', 'ago']):
                    meaningful_lines.append(line)
            
            if meaningful_lines:
                print(f"📄 Meaningful content found ({len(meaningful_lines)} lines):")
                for j, line in enumerate(meaningful_lines[:3]):
                    print(f"   Line {j+1}: {line[:80]}...")
            else:
                print("❌ No meaningful content found")
            
            # Method 2: Test specific selectors
            print(f"\n🎯 Testing Content Selectors:")
            
            test_selectors = [
                ('[data-ad-preview="message"]', 'Facebook Ad Message'),
                ('[data-testid="post_message"]', 'Post Message TestID'),
                ('div[dir="auto"][style*="text-align"]', 'Text Align Divs'),
                ('span[dir="auto"]', 'Auto Direction Spans'),
                ('div[role="article"] span', 'Article Spans'),
            ]
            
            for selector, description in test_selectors:
                try:
                    elements = await post.query_selector_all(selector)
                    print(f"   {description}: {len(elements)} elements")
                    
                    for j, element in enumerate(elements[:2]):
                        text = await element.text_content()
                        if text and len(text.strip()) > 10:
                            print(f"      Element {j+1}: {text.strip()[:60]}...")
                except Exception as e:
                    print(f"   {description}: Error - {e}")
            
            # Method 3: Check for post IDs and URLs
            print(f"\n🆔 Post Identification:")
            
            # Try to find post ID
            id_attributes = ['data-testid', 'id', 'data-story-id', 'data-post-id']
            for attr in id_attributes:
                post_id = await post.get_attribute(attr)
                if post_id:
                    print(f"   {attr}: {post_id[:50]}...")
            
            # Try to find post URL
            try:
                url_links = await post.query_selector_all('a[href*="posts"], a[href*="photo"], a[href*="permalink"]')
                for j, link in enumerate(url_links[:2]):
                    href = await link.get_attribute('href')
                    if href:
                        print(f"   URL {j+1}: {href[:80]}...")
            except:
                pass
            
            # Method 4: Enhanced content extraction simulation
            print(f"\n🔧 Enhanced Content Extraction Test:")
            
            # Simulate the enhanced content extraction
            try:
                # Test Facebook 2024 selectors
                facebook_2024_selectors = [
                    '[data-ad-preview="message"]',
                    '[data-testid="post_message"]',
                    'div[dir="auto"][style*="text-align"]',
                    'span[dir="auto"]',
                    'div[role="article"] span',
                ]

                extracted_content = ""
                for selector in facebook_2024_selectors:
                    try:
                        content_elements = await post.query_selector_all(selector)
                        if content_elements:
                            contents = []
                            for el in content_elements:
                                text = await el.text_content()
                                if text and len(text.strip()) > 15:
                                    # Apply basic cleaning
                                    cleaned = text.strip()
                                    # Remove UI noise
                                    ui_patterns = ['Like', 'Comment', 'Share', 'Reply', 'ago', 'Home', 'Watch']
                                    has_ui_noise = any(ui in cleaned for ui in ui_patterns)
                                    if not has_ui_noise and len(cleaned) > 15:
                                        contents.append(cleaned)
                            
                            if contents:
                                extracted_content = ' '.join(contents)
                                print(f"✅ Content extracted with {selector}: {extracted_content[:100]}...")
                                break
                    except:
                        continue
                
                if not extracted_content:
                    print("❌ No content extracted with enhanced method")
                
            except Exception as e:
                print(f"❌ Error in enhanced extraction: {e}")
        
        input("\n⏸️ Press Enter to continue...")
        
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(debug_posts_extraction())
