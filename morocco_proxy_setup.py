#!/usr/bin/env python3
"""
Morocco Proxy Setup for Facebook Login
This script helps configure reliable Morocco proxies for Facebook scraping
"""
import subprocess
import sys
import time
import requests

def check_current_ip():
    """Check current IP and location"""
    try:
        response = requests.get('http://ipinfo.io/json', timeout=10)
        data = response.json()
        print(f"🌍 Current IP: {data.get('ip', 'Unknown')}")
        print(f"🏴 Country: {data.get('country', 'Unknown')}")
        print(f"🏙️ City: {data.get('city', 'Unknown')}")
        print(f"📡 ISP: {data.get('org', 'Unknown')}")
        return data.get('country', '').upper()
    except Exception as e:
        print(f"❌ Could not check IP: {e}")
        return None

def setup_nordvpn():
    """Setup NordVPN for Morocco"""
    print("🔧 Setting up NordVPN...")
    
    # Check if user is in nordvpn group
    try:
        result = subprocess.run(['groups'], capture_output=True, text=True)
        if 'nordvpn' not in result.stdout:
            print("⚠️ Adding user to nordvpn group...")
            subprocess.run(['sudo', 'usermod', '-aG', 'nordvpn', 'root'])
            print("✅ User added to nordvpn group")
            print("🔄 You may need to restart your shell session")
    except Exception as e:
        print(f"❌ Error setting up nordvpn group: {e}")
    
    print("\n📋 NordVPN Setup Steps:")
    print("1. Get a NordVPN account at https://nordvpn.com")
    print("2. Run: nordvpn login")
    print("3. Run: nordvpn connect Morocco")
    print("4. If Morocco not available, try: nordvpn connect Spain")
    print("5. Check IP: curl ipinfo.io")

def setup_openvpn_morocco():
    """Setup OpenVPN with Morocco config"""
    print("\n🔧 OpenVPN Morocco Setup:")
    print("1. Get Morocco OpenVPN config from:")
    print("   - VPNGate: https://www.vpngate.net/en/")
    print("   - ProtonVPN: https://protonvpn.com/")
    print("   - Surfshark: https://surfshark.com/")
    print("2. Download .ovpn file")
    print("3. Run: sudo openvpn --config morocco.ovpn")

def setup_ssh_tunnel():
    """Setup SSH tunnel through Morocco server"""
    print("\n🔧 SSH Tunnel Setup:")
    print("1. Get a Morocco VPS from:")
    print("   - AWS EC2 (if available in Morocco)")
    print("   - Vultr")
    print("   - Linode")
    print("2. Create SSH tunnel:")
    print("   ssh -D 8080 -N user@morocco-server.com")
    print("3. Configure browser to use SOCKS proxy: 127.0.0.1:8080")

def setup_residential_proxy():
    """Setup residential proxy for Morocco"""
    print("\n🔧 Residential Proxy Setup (Most Reliable):")
    print("1. Premium services with Morocco residential IPs:")
    print("   - Bright Data: https://brightdata.com")
    print("   - Oxylabs: https://oxylabs.io")
    print("   - Smartproxy: https://smartproxy.com")
    print("   - ProxyEmpire: https://proxyempire.io")
    print("2. Cost: ~$300-500/month but very reliable")
    print("3. These work best with Facebook scraping")

def test_facebook_access():
    """Test Facebook access with current IP"""
    print("\n🧪 Testing Facebook Access...")
    try:
        response = requests.get('https://www.facebook.com', timeout=10)
        if response.status_code == 200:
            print("✅ Facebook accessible")
            if 'login' in response.text.lower():
                print("✅ Login page accessible")
            else:
                print("⚠️ May be logged in or redirected")
        else:
            print(f"❌ Facebook returned status: {response.status_code}")
    except Exception as e:
        print(f"❌ Facebook access failed: {e}")

def main():
    """Main setup function"""
    print("🇲🇦 Morocco Proxy Setup for Facebook Login")
    print("=" * 50)
    
    # Check current IP
    current_country = check_current_ip()
    
    if current_country == 'MA':
        print("✅ You're already in Morocco!")
        print("🎉 Your Facebook login should work normally")
        test_facebook_access()
        return
    
    print(f"\n📍 You're currently in: {current_country}")
    print("🎯 Need to change IP to Morocco for Facebook login")
    
    print("\n🔧 Available Solutions:")
    print("1. NordVPN (Recommended)")
    print("2. OpenVPN with Morocco config")
    print("3. SSH tunnel through Morocco server")
    print("4. Residential proxy (Most reliable)")
    print("5. Move server to Europe (Frankfurt/London)")
    
    choice = input("\nChoose option (1-5): ").strip()
    
    if choice == '1':
        setup_nordvpn()
    elif choice == '2':
        setup_openvpn_morocco()
    elif choice == '3':
        setup_ssh_tunnel()
    elif choice == '4':
        setup_residential_proxy()
    elif choice == '5':
        print("\n🌍 Server Migration:")
        print("1. Create new DigitalOcean droplet in Frankfurt")
        print("2. Transfer your scraper code")
        print("3. This puts you much closer to Morocco")
    else:
        print("❌ Invalid choice")
        return
    
    print("\n🎯 After setup:")
    print("1. Check IP: curl ipinfo.io")
    print("2. Test Facebook: python3 main.py")
    print("3. Your Moroccan account should login normally")

if __name__ == "__main__":
    main() 