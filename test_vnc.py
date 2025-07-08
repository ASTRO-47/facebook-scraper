#!/usr/bin/env python3

import subprocess
import time
import os

def test_vnc_setup():
    """Test if VNC is properly set up and working"""
    
    print("🧪 Testing VNC setup...")
    print("=" * 50)
    
    # Test 1: Check if required packages are installed
    required_packages = ["Xvfb", "x11vnc", "websockify"]
    print("\n1️⃣  Checking required packages...")
    
    for package in required_packages:
        result = subprocess.run(["which", package], 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            print(f"   ✅ {package} - installed")
        else:
            print(f"   ❌ {package} - missing")
            print(f"      Install with: sudo apt install {package.lower()}")
    
    # Test 2: Check if NoVNC is available
    print("\n2️⃣  Checking NoVNC...")
    if os.path.exists("/usr/share/novnc/"):
        print("   ✅ NoVNC web interface - found")
    else:
        print("   ❌ NoVNC web interface - missing")
        print("      Install with: sudo apt install novnc")
    
    # Test 3: Try to start a quick VNC session
    print("\n3️⃣  Testing VNC startup...")
    
    # Kill any existing processes
    for process in ["Xvfb", "x11vnc", "websockify"]:
        subprocess.run(["pkill", process], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    time.sleep(1)
    
    try:
        # Start Xvfb
        print("   🖥️  Starting test Xvfb...")
        xvfb_proc = subprocess.Popen([
            "Xvfb", ":99", "-screen", "0", "1024x768x24", "-ac"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        time.sleep(2)
        
        # Check if Xvfb is running
        if subprocess.run(["pgrep", "Xvfb"], stdout=subprocess.PIPE).stdout:
            print("   ✅ Xvfb test - success")
            
            # Try to start x11vnc
            print("   📡 Starting test x11vnc...")
            vnc_proc = subprocess.Popen([
                "x11vnc", "-display", ":99", "-nopw", "-rfbport", "5999", "-bg"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            time.sleep(2)
            
            if subprocess.run(["pgrep", "x11vnc"], stdout=subprocess.PIPE).stdout:
                print("   ✅ x11vnc test - success")
            else:
                print("   ❌ x11vnc test - failed")
            
        else:
            print("   ❌ Xvfb test - failed")
        
    except Exception as e:
        print(f"   ❌ VNC test failed: {e}")
    
    finally:
        # Clean up test processes
        for process in ["Xvfb", "x11vnc"]:
            subprocess.run(["pkill", process], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Test 4: Check network configuration
    print("\n4️⃣  Checking network configuration...")
    
    try:
        # Get public IP
        result = subprocess.run(["curl", "-s", "ifconfig.me"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            public_ip = result.stdout.strip()
            print(f"   🌍 Public IP: {public_ip}")
            print(f"   🔗 Direct VNC access: http://{public_ip}:6080/vnc.html")
        else:
            print("   ⚠️  Could not determine public IP")
    except:
        print("   ⚠️  Could not check public IP")
    
    print("\n🏁 VNC test complete!")
    print("\n💡 Next steps:")
    print("   1. Run: python3 /root/facebook_scraper/simple_browser.py")
    print("   2. Open VNC URL in your browser")
    print("   3. Or create SSH tunnel: ssh -L 6080:localhost:6080 user@server")

if __name__ == "__main__":
    test_vnc_setup()
