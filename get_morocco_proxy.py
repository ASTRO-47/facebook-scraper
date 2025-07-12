#!/usr/bin/env python3
"""
Get free Morocco proxy for Facebook scraping
"""
import requests
import time
import random
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json

class MoroccoProxyFinder:
    def __init__(self):
        self.working_proxies = []
        
    def get_free_proxy_sources(self):
        """Get multiple sources of free proxies"""
        sources = [
            # Free proxy APIs
            "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=MA&format=json",
            "https://api.proxyscrape.com/v2/?request=get&protocol=socks5&timeout=10000&country=MA&format=json", 
            "https://www.proxy-list.download/api/v1/get?type=http&country=MA",
            "https://www.proxy-list.download/api/v1/get?type=socks5&country=MA",
        ]
        
        # Also try some manual Morocco proxies (these change frequently)
        manual_proxies = [
            "41.230.216.70:8080",
            "41.230.216.71:8080", 
            "196.12.163.66:8080",
            "196.12.163.67:8080",
            "41.92.208.178:8080",
            "41.92.208.179:8080",
            "41.251.84.229:8080",
            "105.235.200.18:8080",
            "105.235.200.19:8080",
            "196.12.142.166:8080",
        ]
        
        return sources, manual_proxies
    
    def test_proxy(self, proxy):
        """Test if a proxy works"""
        try:
            proxy_dict = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            
            # Test with a simple request
            response = requests.get(
                'http://httpbin.org/ip', 
                proxies=proxy_dict, 
                timeout=10
            )
            
            if response.status_code == 200:
                ip_info = response.json()
                print(f"✅ Working proxy: {proxy} -> IP: {ip_info.get('origin', 'Unknown')}")
                return proxy
            else:
                print(f"❌ Proxy failed: {proxy} (Status: {response.status_code})")
                return None
                
        except Exception as e:
            print(f"❌ Proxy failed: {proxy} (Error: {str(e)[:50]})")
            return None
    
    def get_proxies_from_api(self, url):
        """Get proxies from API"""
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                if 'json' in url:
                    data = response.json()
                    if isinstance(data, dict) and 'proxies' in data:
                        return [f"{p['ip']}:{p['port']}" for p in data['proxies']]
                    elif isinstance(data, list):
                        return [f"{p['ip']}:{p['port']}" for p in data]
                else:
                    # Plain text format
                    return [line.strip() for line in response.text.split('\n') if line.strip()]
        except Exception as e:
            print(f"❌ Failed to get proxies from {url}: {e}")
        return []
    
    def find_working_proxies(self):
        """Find working Morocco proxies"""
        print("🔍 Searching for free Morocco proxies...")
        
        sources, manual_proxies = self.get_free_proxy_sources()
        all_proxies = list(manual_proxies)  # Start with manual list
        
        # Get proxies from APIs
        for source in sources:
            print(f"📡 Checking source: {source}")
            proxies = self.get_proxies_from_api(source)
            all_proxies.extend(proxies)
            time.sleep(1)  # Be nice to APIs
        
        # Remove duplicates
        unique_proxies = list(set(all_proxies))
        print(f"📋 Found {len(unique_proxies)} unique proxies to test")
        
        # Test proxies in parallel
        print("🧪 Testing proxies...")
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(self.test_proxy, unique_proxies))
        
        # Filter working proxies
        self.working_proxies = [p for p in results if p is not None]
        
        if self.working_proxies:
            print(f"✅ Found {len(self.working_proxies)} working proxies!")
            return self.working_proxies
        else:
            print("❌ No working proxies found")
            return []
    
    def get_random_proxy(self):
        """Get a random working proxy"""
        if self.working_proxies:
            return random.choice(self.working_proxies)
        return None
    
    def save_proxies(self, filename="morocco_proxies.json"):
        """Save working proxies to file"""
        if self.working_proxies:
            data = {
                "proxies": self.working_proxies,
                "last_updated": time.time()
            }
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"💾 Saved {len(self.working_proxies)} proxies to {filename}")
    
    def load_proxies(self, filename="morocco_proxies.json"):
        """Load proxies from file"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            # Check if proxies are less than 1 hour old
            if time.time() - data.get('last_updated', 0) < 3600:
                self.working_proxies = data.get('proxies', [])
                print(f"📂 Loaded {len(self.working_proxies)} cached proxies")
                return self.working_proxies
            else:
                print("⏰ Cached proxies are too old, will fetch new ones")
                
        except FileNotFoundError:
            print("📂 No cached proxies found, will fetch new ones")
        except Exception as e:
            print(f"❌ Error loading cached proxies: {e}")
        
        return []

def get_morocco_proxy():
    """Main function to get a working Morocco proxy"""
    finder = MoroccoProxyFinder()
    
    # Try to load cached proxies first
    cached_proxies = finder.load_proxies()
    if cached_proxies:
        return finder.get_random_proxy()
    
    # If no cached proxies, find new ones
    working_proxies = finder.find_working_proxies()
    if working_proxies:
        finder.save_proxies()
        return finder.get_random_proxy()
    
    return None

if __name__ == "__main__":
    print("🇲🇦 Morocco Proxy Finder")
    print("="*50)
    
    proxy = get_morocco_proxy()
    if proxy:
        print(f"\n🎉 SUCCESS! Use this proxy: {proxy}")
        print(f"\n💡 To use in your scraper:")
        print(f"   python main.py --proxy {proxy}")
    else:
        print("\n😞 No working Morocco proxies found.")
        print("💡 Try running this script again in a few minutes.")
        print("📝 You can also manually add Morocco proxies to the manual_proxies list.") 