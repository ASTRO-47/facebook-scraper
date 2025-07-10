#!/usr/bin/env python3

import asyncio
import os
import subprocess
import time
import json
from pathlib import Path

from playwright.async_api import async_playwright

def get_server_ip():
    """Get the server's public IP address"""
    try:
        # Try to get public IP
        result = subprocess.run(["curl", "-s", "ifconfig.me"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass
    
    # Fallback: try to get from hostname -I
    try:
        result = subprocess.run(["hostname", "-I"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            # Get first IP address
            ips = result.stdout.strip().split()
            if ips:
                return ips[0]
    except:
        pass
    
    return "localhost"

def check_vnc_dependencies():
    """Check if required VNC packages are installed"""
    required_packages = ["Xvfb", "x11vnc", "websockify"]
    missing = []
    
    for package in required_packages:
        result = subprocess.run(["which", package], 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode != 0:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing required packages: {', '.join(missing)}")
        print("\nPlease install them with:")
        print("sudo apt update")
        print("sudo apt install -y xvfb x11vnc novnc websockify")
        return False
    
    print("✅ All VNC dependencies are installed")
    return True

async def ensure_vnc_running():
    """Make sure the VNC server is running before launching browser"""
    
    # Check dependencies first
    if not check_vnc_dependencies():
        return False
    
    # Kill any existing processes to start fresh
    print("🔄 Stopping any existing VNC processes...")
    for process in ["Xvfb", "x11vnc", "websockify"]:
        subprocess.run(["pkill", process], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    time.sleep(2)  # Wait for processes to terminate
    
    # Start Xvfb (virtual display)
    print("🖥️  Starting virtual display (Xvfb)...")
    xvfb_proc = subprocess.Popen([
        "Xvfb", ":1", "-screen", "0", "1366x768x24", "-ac", "+extension", "GLX"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)  # Give Xvfb time to start
    
    # Verify Xvfb is running
    if subprocess.run(["pgrep", "Xvfb"], stdout=subprocess.PIPE).stdout:
        print("✅ Xvfb started successfully")
    else:
        print("❌ Failed to start Xvfb")
        return False
    
    # Start x11vnc server
    print("📡 Starting VNC server (x11vnc)...")
    os.makedirs("/root/.vnc", exist_ok=True)
    vnc_proc = subprocess.Popen([
        "x11vnc", "-display", ":1", "-forever", "-nopw", "-shared", 
        "-rfbport", "5901", "-bg", "-o", "/root/.vnc/x11vnc.log"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)  # Give x11vnc time to start
    
    # Verify x11vnc is running
    if subprocess.run(["pgrep", "x11vnc"], stdout=subprocess.PIPE).stdout:
        print("✅ x11vnc started successfully")
    else:
        print("❌ Failed to start x11vnc")
        return False
    
    # Start NoVNC (web interface)
    print("🌐 Starting NoVNC web interface...")
    novnc_proc = subprocess.Popen([
        "websockify", "-D", "--web=/usr/share/novnc/", "6080", "localhost:5901"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)  # Give websockify time to start
    
    # Verify websockify is running
    if subprocess.run(["pgrep", "websockify"], stdout=subprocess.PIPE).stdout:
        print("✅ NoVNC web interface started successfully")
    else:
        print("❌ Failed to start NoVNC")
        return False
    
    # Set DISPLAY environment variable
    os.environ["DISPLAY"] = ":1"
    
    # Get server IP for access instructions
    server_ip = get_server_ip()
    
    print("\n" + "="*80)
    print("🚀 VNC SERVER IS READY!")
    print("="*80)
    if server_ip != "localhost":
        print(f"🌍 Direct access: http://{server_ip}:6080/vnc.html")
    print("🔐 SSH tunnel access: http://localhost:6080/vnc.html")
    print("💡 To create SSH tunnel: ssh -L 6080:localhost:6080 user@your-server")
    print("="*80 + "\n")
    
    time.sleep(3)  # Give user time to read instructions
    return True

def save_login_session(user_data_dir):
    """Save login session info for future use"""
    session_file = Path(user_data_dir) / "session_info.json"
    session_info = {
        "last_login": time.time(),
        "user_data_dir": str(user_data_dir),
        "status": "logged_in"
    }
    q
    try:
        with open(session_file, 'w') as f:
            json.dump(session_info, f, indent=2)
        print(f"✅ Session info saved to: {session_file}")
    except Exception as e:
        print(f"⚠️  Warning: Could not save session info: {e}")

def load_login_session(user_data_dir):
    """Load previous login session info"""
    session_file = Path(user_data_dir) / "session_info.json"
    
    if session_file.exists():
        try:
            with open(session_file, 'r') as f:
                session_info = json.load(f)
            
            last_login = session_info.get("last_login", 0)
            days_since_login = (time.time() - last_login) / (24 * 3600)
            
            print(f"📁 Found existing session (last login: {days_since_login:.1f} days ago)")
            return session_info
        except Exception as e:
            print(f"⚠️  Warning: Could not load session info: {e}")
    
    return None

async def main():
    print("\n" + "🔧" * 80)
    print("FACEBOOK SCRAPER - PERSISTENT BROWSER SETUP")
    print("🔧" * 80)
    
    # Make sure VNC server is running
    if not await ensure_vnc_running():
        print("❌ Failed to start VNC server. Please check the error messages above.")
        return
    
    # Set up persistent browser directory
    user_data_dir = Path.home() / ".facebook_scraper_data"
    user_data_dir.mkdir(exist_ok=True)
    
    # Check for existing session
    session_info = load_login_session(user_data_dir)
    
    print("\n" + "="*80)
    print("🌐 FACEBOOK LOGIN - PERSISTENT BROWSER SESSION")
    print("="*80)
    print("📍 Steps to follow:")
    print("1. 🖥️  Open VNC viewer in your browser (see URL above)")
    print("2. 🔐 Log in to Facebook in the browser window")
    print("3. ✅ Complete any security checks if prompted")
    print("4. 💾 Your session will be automatically saved")
    print("5. ⌨️  Press Ctrl+C in this terminal when done")
    print("="*80 + "\n")
    
    # Launch browser with persistent context
    async with async_playwright() as p:
        # Enhanced browser settings for better compatibility
        browser_context = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            ignore_https_errors=True,
            viewport={"width": 1366, "height": 768},
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=VizDisplayCompositor",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-extensions-except=",
                "--disable-extensions",
                "--no-first-run",
                "--no-default-browser-check"
            ]
        )
        
        # Get the default page or create one
        if len(browser_context.pages) > 0:
            page = browser_context.pages[0]
        else:
            page = await browser_context.new_page()
        
        # Go to Facebook
        print("🌐 Navigating to Facebook...")
        try:
            await page.goto("https://www.facebook.com", wait_until="networkidle", timeout=30000)
            print("✅ Facebook loaded successfully!")
        except Exception as e:
            print(f"⚠️  Warning: {e}")
            print("🔄 Trying to continue anyway...")
        
        # Check if already logged in
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
            current_url = page.url
            
            if "facebook.com" in current_url and ("login" not in current_url.lower() and "checkpoint" not in current_url.lower()):
                print("✅ Appears to be already logged in!")
            else:
                print("🔐 Please log in to Facebook in the VNC viewer")
        except:
            print("🔐 Please log in to Facebook in the VNC viewer")
        
        print("\n📺 Browser is now visible in VNC viewer")
        print("🎯 Complete your login and press Ctrl+C here when done")
        
        try:
            # Keep the script running until user presses Ctrl+C
            while True:
                await asyncio.sleep(5)
                
                # Periodically check if we're still on Facebook
                try:
                    current_url = page.url
                    if "facebook.com" not in current_url.lower():
                        print(f"📍 Current page: {current_url}")
                except:
                    pass
                    
        except KeyboardInterrupt:
            print("\n🛑 Detected Ctrl+C. Saving session and closing browser...")
            
            # Save session info
            save_login_session(user_data_dir)
            
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            
        finally:
            # Close the persistent context
            try:
                await browser_context.close()
                print("✅ Browser closed successfully")
                print("💾 Your Facebook session has been saved for future use")
                print(f"📁 Session data stored in: {user_data_dir}")
            except Exception as e:
                print(f"⚠️  Warning during cleanup: {e}")

        # --- FriendsScraper integration ---
        
        from friends import FriendsScraper  # Import here to avoid circular dependency
        
        async def scrape_friends_data():
            # Create a new page for scraping friends
            friends_page = await browser_context.new_page()
            
            # Initialize the friends scraper
            friends_scraper = FriendsScraper(friends_page)
            
            # Scrape friends list
            username = "me"  # Change this to target a specific user
            friends = await friends_scraper.scrape_friends(username)
            
            # Log or process the friends data as needed
            print(f"✅ Scraped {len(friends)} friends:")
            for friend in friends:
                print(f"- {friend['name']} ({friend['profile_url']})")
            
            # Close the friends page
            await friends_page.close()
        
        # Run the friends scraper
        await scrape_friends_data()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Script terminated by user")
    except Exception as e:
        print(f"\n❌ Script failed: {e}")
        print("💡 Make sure all VNC dependencies are installed")