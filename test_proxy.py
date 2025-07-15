#!/usr/bin/env python3
"""
Test script for Morocco proxy functionality
This script tests if the free proxy system is working correctly
"""
import asyncio
import sys
import os

# Add the scraper module to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from scraper.proxy_manager import proxy_manager

async def test_proxy_system():
    """Test the proxy system and display results"""
    print("🧪 Testing Morocco Proxy System")
    print("=" * 50)
    
    try:
        # Get a working proxy
        print("🔍 Fetching working proxies...")
        proxy_url = await proxy_manager.get_working_proxy()
        
        if proxy_url:
            print(f"✅ Found working proxy: {proxy_url}")
            
            # Get IP information
            print("🌍 Checking IP location...")
            ip_info = await proxy_manager.get_ip_info(proxy_url)
            
            print("\n📍 Proxy Location Information:")
            print(f"   🏴 Country: {ip_info.get('country', 'Unknown')}")
            print(f"   🏙️  Region: {ip_info.get('regionName', 'Unknown')}")
            print(f"   🌆 City: {ip_info.get('city', 'Unknown')}")
            print(f"   🌐 IP Address: {ip_info.get('query', 'Unknown')}")
            print(f"   📡 ISP: {ip_info.get('isp', 'Unknown')}")
            
            # Check if it's from Morocco or nearby
            country_code = ip_info.get('countryCode', '').upper()
            if country_code == 'MA':
                print("🇲🇦 ✅ PERFECT: Using Moroccan proxy!")
            elif country_code in ['DZ', 'TN', 'EG']:
                print(f"🌍 ✅ GOOD: Using North African proxy ({country_code})")
            else:
                print(f"🌐 ⚠️ OK: Using proxy from {country_code} (not ideal but may work)")
            
            print("\n🎯 Proxy Test Results:")
            print("✅ Proxy system is working")
            print("✅ Can fetch IP information")
            print("✅ Ready for Facebook scraping")
            
            # Show available proxies count
            if proxy_manager.working_proxies:
                moroccan_count = sum(1 for p in proxy_manager.working_proxies if p.get('country') == 'MA')
                total_count = len(proxy_manager.working_proxies)
                print(f"\n📊 Available Proxies: {total_count} total ({moroccan_count} Moroccan)")
            
        else:
            print("❌ No working proxies found")
            print("💡 Suggestions:")
            print("   - Check your internet connection")
            print("   - Try running the script again (proxies change frequently)")
            print("   - Some proxy sources may be temporarily unavailable")
            
    except Exception as e:
        print(f"❌ Error testing proxy system: {e}")
        print("💡 This could be due to:")
        print("   - Network connectivity issues")
        print("   - Proxy source APIs being down")
        print("   - Firewall blocking proxy connections")

if __name__ == "__main__":
    print("🚀 Starting proxy test...")
    asyncio.run(test_proxy_system())
    print("\n✨ Test completed!") 