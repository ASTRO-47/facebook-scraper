#!/usr/bin/env python3
"""
Example usage of Facebook scraper with Morocco proxy functionality
"""
import asyncio
import sys
import os

# Add the scraper module to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from scraper import FacebookSession, ProfileScraper, ScraperUtils, proxy_manager

async def example_scrape_with_morocco_proxy():
    """Example of scraping with Morocco proxy"""
    print("🇲🇦 Facebook Scraper with Morocco Proxy - Example Usage")
    print("=" * 60)
    
    try:
        # Step 1: Get a working Morocco proxy
        print("🌍 Getting Morocco proxy...")
        proxy_url = await proxy_manager.get_working_proxy()
        
        if proxy_url:
            print(f"✅ Using proxy: {proxy_url}")
            
            # Verify proxy location
            ip_info = await proxy_manager.get_ip_info(proxy_url)
            print(f"📍 Proxy location: {ip_info.get('country', 'Unknown')}, {ip_info.get('city', 'Unknown')}")
        else:
            print("⚠️ No proxy available, continuing without proxy")
            proxy_url = None
        
        # Step 2: Initialize session with proxy
        print("\n🚀 Starting browser session...")
        session = FacebookSession(
            headless=True,  # Set to False to see browser
            proxy=proxy_url  # This makes Facebook think you're in Morocco!
        )
        
        page = await session.initialize()
        print("✅ Browser initialized")
        
        # Step 3: Check login status (you'll need to login manually if needed)
        print("\n🔑 Checking login status...")
        is_logged_in = await session.login_check()
        
        if is_logged_in:
            print("✅ Already logged in!")
            
            # Step 4: Initialize scraper components
            utils = ScraperUtils(page)
            profile_scraper = ProfileScraper(page, utils)
            
            # Step 5: Example scraping (replace with actual username)
            username = "example.username"  # Replace with target username
            print(f"\n🎯 Example: Scraping profile {username}")
            print("(This is just a demo - replace with actual username)")
            
            # Simulate navigation (commented out to avoid actual requests in example)
            # profile_exists = await profile_scraper.navigate_to_profile(username)
            # if profile_exists:
            #     basic_info = await profile_scraper.get_basic_info()
            #     print(f"📝 Profile name: {basic_info.get('name', 'Unknown')}")
            
            print("✅ Example completed successfully!")
            
        else:
            print("🔑 Please complete login manually and try again")
        
        # Step 6: Cleanup
        print("\n🧹 Cleaning up...")
        await session.close()
        print("✅ Session closed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

async def quick_proxy_test():
    """Quick test to see if proxies are working"""
    print("🧪 Quick Proxy Test")
    print("-" * 30)
    
    # Test proxy system
    proxy_url = await proxy_manager.get_working_proxy()
    
    if proxy_url:
        ip_info = await proxy_manager.get_ip_info(proxy_url)
        print(f"✅ Proxy working: {proxy_url}")
        print(f"📍 Location: {ip_info.get('country', 'Unknown')}")
        return True
    else:
        print("❌ No working proxies found")
        return False

if __name__ == "__main__":
    print("🔹 Choose an option:")
    print("1. Quick proxy test")
    print("2. Full scraper example with proxy")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        print("\n" + "="*50)
        asyncio.run(quick_proxy_test())
    elif choice == "2":
        print("\n" + "="*50)
        asyncio.run(example_scrape_with_morocco_proxy())
    else:
        print("Invalid choice. Run the script again.")
    
    print("\n✨ Done!") 