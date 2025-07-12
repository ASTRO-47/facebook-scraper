#!/usr/bin/env python3
"""
Facebook Account Recovery Helper
For accounts that are restricted despite phone verification

This script helps with advanced account recovery scenarios,
particularly for international accounts (Moroccan -> US access)
"""

import asyncio
import os
import time
from playwright.async_api import async_playwright

class FacebookAccountRecovery:
    def __init__(self):
        self.user_data_dir = os.path.expanduser("~/.facebook_recovery_session")
        os.makedirs(self.user_data_dir, exist_ok=True)

    async def advanced_recovery_flow(self):
        """Advanced recovery flow for persistent restrictions"""
        print("\n" + "🔓" * 80)
        print("FACEBOOK ADVANCED ACCOUNT RECOVERY")
        print("🔓" * 80)
        print("For accounts restricted despite phone verification")
        print("="*80)
        
        async with async_playwright() as p:
            # Launch with maximum stealth
            context = await p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=False,
                args=[
                    '--disable-web-security',
                    '--disable-blink-features=AutomationControlled',
                    '--exclude-switches=enable-automation',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-images',  # Faster loading
                    '--disable-javascript-harmony-shipping',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--no-first-run',
                    '--no-default-browser-check'
                ],
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
                locale="en-US",
                timezone_id="America/New_York"
            )
            
            page = await context.new_page()
            
            # Advanced stealth
            await page.evaluate("""
                Object.defineProperty(navigator, 'webdriver', {get: () => false});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                delete window.chrome;
            """)
            
            print("🌐 Navigating to Facebook Help Center...")
            
            # Start with help center (less suspicious)
            await page.goto("https://www.facebook.com/help/", wait_until="domcontentloaded")
            await asyncio.sleep(5)
            
            print("\n📋 STEP 1: Try Account Recovery Methods")
            print("="*50)
            print("1. Go to: https://www.facebook.com/login/identify")
            print("2. Enter your email/phone")
            print("3. Click 'No longer have access to these?'")
            print("4. Choose 'Recover your account with ID'")
            print("5. Upload REAL ID (passport/driver's license)")
            
            # Navigate to identity recovery
            await page.goto("https://www.facebook.com/login/identify", wait_until="domcontentloaded")
            await asyncio.sleep(3)
            
            print("\n📋 STEP 2: Alternative - Contact Form")
            print("="*50)
            print("If ID recovery doesn't work:")
            print("1. Go to: https://www.facebook.com/help/contact/")
            print("2. Choose 'Something Isn't Working'")
            print("3. Select 'Login and Password'")
            print("4. Fill form explaining your situation:")
            print("   - Moroccan living/working in US")
            print("   - Account is legitimate and old")
            print("   - You verified with phone but still restricted")
            print("   - Need account for legitimate business/personal use")
            
            print("\n📋 STEP 3: Wait for Manual Review")
            print("="*50)
            print("Facebook manual review typically takes:")
            print("- ID Review: 24-48 hours")
            print("- Contact Form: 3-7 days")
            print("- During this time, DON'T attempt to login repeatedly")
            
            print("\n⏳ Keeping browser open for you to complete the process...")
            print("🖱️ Complete the recovery steps above")
            print("📞 Check your phone for verification codes")
            print("📧 Monitor your email for Facebook responses")
            print("⌨️ Press Ctrl+C when done")
            
            # Wait for user to complete
            try:
                while True:
                    await asyncio.sleep(10)
                    print("⏳ Recovery session active... (Press Ctrl+C to finish)")
                    
            except KeyboardInterrupt:
                print("\n✅ Recovery session completed")
                
            await context.close()

    async def try_alternative_login_urls(self):
        """Try different Facebook login URLs that might bypass restrictions"""
        print("\n🔗 ALTERNATIVE LOGIN URLS TO TRY")
        print("="*50)
        
        alternative_urls = [
            "https://m.facebook.com/login.php",
            "https://mobile.facebook.com/login.php", 
            "https://touch.facebook.com/login.php",
            "https://ar-ar.facebook.com/login.php",
            "https://fr-fr.facebook.com/login.php",
            "https://www.facebook.com/login.php?next=https%3A%2F%2Fm.facebook.com%2F",
            "https://business.facebook.com/login",
            "https://www.facebook.com/recover/initiate"
        ]
        
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=False
            )
            
            page = await context.new_page()
            
            for i, url in enumerate(alternative_urls, 1):
                print(f"\n{i}. Trying: {url}")
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    await asyncio.sleep(3)
                    
                    # Check if login form is available
                    email_input = await page.query_selector('input[name="email"]')
                    if email_input:
                        print(f"✅ Login form found at: {url}")
                        print("🔄 Try logging in through this URL")
                        
                        # Wait for user to try
                        await asyncio.sleep(10)
                    else:
                        print(f"⚠️ No login form at: {url}")
                        
                except Exception as e:
                    print(f"❌ Failed to load: {url} - {e}")
                    
            await context.close()

async def main():
    recovery = FacebookAccountRecovery()
    
    print("🔓 Facebook Account Recovery for Persistent Restrictions")
    print("="*60)
    print("Choose an option:")
    print("1. Advanced Account Recovery (ID verification)")
    print("2. Try Alternative Login URLs")
    print("3. Both")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice in ["1", "3"]:
        await recovery.advanced_recovery_flow()
    
    if choice in ["2", "3"]:
        await recovery.try_alternative_login_urls()

if __name__ == "__main__":
    asyncio.run(main()) 