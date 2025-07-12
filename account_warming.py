#!/usr/bin/env python3
"""
Facebook Account Warming Script
For accounts that have been restricted but phone verified

This script helps gradually warm up your account to establish trust
with Facebook's security system over time.
"""

import asyncio
import random
import time
from playwright.async_api import async_playwright

class FacebookAccountWarming:
    def __init__(self):
        self.user_data_dir = "~/.facebook_warming_session"
        
    async def gradual_activity_simulation(self):
        """Simulate gradual, human-like Facebook activity"""
        print("\n" + "🌡️" * 80)
        print("FACEBOOK ACCOUNT WARMING PROTOCOL")
        print("🌡️" * 80)
        print("For accounts restricted after phone verification")
        print("="*80)
        
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=False,
                args=[
                    '--disable-automation',
                    '--disable-blink-features=AutomationControlled',
                    '--exclude-switches=enable-automation',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ],
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            
            # Add realistic human behavior
            await page.evaluate("""
                Object.defineProperty(navigator, 'webdriver', {get: () => false});
                delete window.chrome;
            """)
            
            print("🌍 Phase 1: Light Activity (First 3 days)")
            print("="*50)
            print("✅ What to do:")
            print("- Login once per day maximum")
            print("- View your own profile only")
            print("- Maybe edit profile picture/bio")
            print("- Check notifications (don't interact)")
            print("- Stay logged in for 5-10 minutes max")
            print("- DON'T search for people")
            print("- DON'T visit other profiles")
            print("- DON'T send friend requests")
            
            print("\n🌍 Phase 2: Gradual Expansion (Days 4-7)")
            print("="*50)
            print("✅ What to do:")
            print("- Login once per day")
            print("- Browse news feed VERY lightly")
            print("- View 2-3 posts maximum")
            print("- Maybe like 1 post")
            print("- Check marketplace (browse only)")
            print("- Stay logged in for 10-15 minutes")
            print("- Still NO profile visits or friend requests")
            
            print("\n🌍 Phase 3: Normal Activity (After 1 week)")
            print("="*50)
            print("✅ What to do:")
            print("- Login normally")
            print("- Browse friends' profiles")
            print("- Send friend requests (1-2 per day MAX)")
            print("- Like/comment on posts")
            print("- Use search function")
            print("- Normal Facebook usage")
            
            # Open Facebook for immediate light activity
            print("\n🚀 Starting with light activity now...")
            await page.goto("https://www.facebook.com", wait_until="domcontentloaded")
            await asyncio.sleep(5)
            
            print("\n📋 INSTRUCTIONS FOR TODAY:")
            print("1. Login to your account")
            print("2. Go to your profile")
            print("3. Maybe update your profile picture or bio")
            print("4. Check notifications (don't click on profiles)")
            print("5. Stay for 5-10 minutes MAXIMUM")
            print("6. Log out cleanly")
            print("7. WAIT 24 hours before next login")
            
            print("\n⏳ Browser is open - follow the instructions above")
            print("⌨️ Press Ctrl+C when you've completed today's activity")
            
            try:
                while True:
                    await asyncio.sleep(30)
                    print("⏳ Warming session active... (Complete activity then press Ctrl+C)")
            except KeyboardInterrupt:
                print("\n✅ Warming session completed for today")
                print("⏰ REMEMBER: Wait 24 hours before next login!")
                
            await context.close()

    async def emergency_wait_strategy(self):
        """For severely restricted accounts - emergency waiting strategy"""
        print("\n" + "🚨" * 80)
        print("EMERGENCY WAIT STRATEGY")
        print("🚨" * 80)
        print("For accounts with severe restrictions")
        print("="*80)
        
        print("📅 MANDATORY WAITING PERIODS:")
        print("="*40)
        print("🔴 CRITICAL: If you see these messages:")
        print("- 'Your account is temporarily locked'")
        print("- 'We've limited some features'") 
        print("- 'Account restricted for suspicious activity'")
        print("- 'Complete identity verification'")
        print()
        print("⏰ YOU MUST WAIT:")
        print("- Minimum 48-72 hours")
        print("- NO login attempts during this time")
        print("- NO password reset attempts")
        print("- NO creating new accounts")
        
        print("\n✅ WHAT TO DO DURING WAIT:")
        print("="*40)
        print("1. 📱 Check your phone for Facebook SMS")
        print("2. 📧 Check email for Facebook messages")
        print("3. 🆔 Prepare ID documents (passport/license)")
        print("4. 📝 Prepare explanation for Facebook:")
        print("   - You're Moroccan living/working in US")
        print("   - Account is legitimate and years old")
        print("   - You need it for work/family contact")
        
        print("\n🔄 AFTER WAITING PERIOD:")
        print("="*40)
        print("1. Try mobile.facebook.com first")
        print("2. Use different browser/device if possible")
        print("3. Login during US business hours")
        print("4. Be ready for ID verification")
        print("5. Upload REAL documents only")
        
        print("\n⚠️ WHAT NOT TO DO:")
        print("="*40)
        print("❌ Don't use VPN")
        print("❌ Don't create new accounts")
        print("❌ Don't try to login repeatedly")
        print("❌ Don't use fake information")
        print("❌ Don't contact Facebook multiple times")

if __name__ == "__main__":
    warming = FacebookAccountWarming()
    
    print("🌡️ Facebook Account Recovery & Warming")
    print("="*50)
    print("Your situation: Old account, phone verified but still restricted")
    print()
    print("Choose strategy:")
    print("1. Start gradual warming protocol")
    print("2. Emergency wait strategy (for severe restrictions)")
    
    choice = input("\nEnter choice (1-2): ").strip()
    
    if choice == "1":
        asyncio.run(warming.gradual_activity_simulation())
    elif choice == "2":
        asyncio.run(warming.emergency_wait_strategy())
    else:
        print("Invalid choice") 