#!/usr/bin/env python3
"""
Command-line interface for the Facebook Profile Scraper
This script allows you to run the scraper directly from the command line
with VNC server support for remote access.
"""
import os
import sys
import json
import asyncio
import argparse
import subprocess
import time
import signal
from datetime import datetime
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('facebook_cli')

# Make sure the scraper module can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper.session import FacebookSession
from scraper.profile import ProfileScraper
from scraper.posts import PostsScraper
from scraper.utils import ScraperUtils
from scraper.json_builder import JSONBuilder

# Global variables for VNC cleanup
vnc_processes = []
display_num = None

def cleanup_vnc():
    """Clean up VNC processes on exit"""
    global vnc_processes, display_num
    
    logger.info("Cleaning up VNC processes...")
    
    # Kill our spawned processes
    for proc in vnc_processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except:
            try:
                proc.kill()
            except:
                pass
    
    # Clean up display processes
    if display_num:
        try:
            subprocess.run(f"pkill -f 'Xvfb :{display_num}'", shell=True, check=False)
            subprocess.run(f"pkill -f 'x11vnc.*:{display_num}'", shell=True, check=False)
            subprocess.run(f"pkill -f 'fluxbox.*DISPLAY=:{display_num}'", shell=True, check=False)
        except:
            pass

def signal_handler(signum, frame):
    """Handle interrupt signals"""
    logger.info("Received interrupt signal, cleaning up...")
    cleanup_vnc()
    sys.exit(0)

def setup_vnc_server():
    """Set up VNC server for remote browser access"""
    global vnc_processes, display_num
    
    logger.info("Setting up VNC server for remote browser access...")
    
    # Find available display
    for display in range(1, 6):
        try:
            # Check if display is available
            result = subprocess.run(f"xdpyinfo -display :{display}", 
                                  shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                display_num = display
                break
        except:
            continue
    
    if not display_num:
        logger.error("No available display found")
        return False
    
    logger.info(f"Using display :{display_num}")
    
    try:
        # Start Xvfb
        logger.info("Starting Xvfb virtual display...")
        xvfb_proc = subprocess.Popen([
            "Xvfb", f":{display_num}", 
            "-screen", "0", "1920x1080x24",
            "-ac", "+extension", "GLX", "+render", "-noreset"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        vnc_processes.append(xvfb_proc)
        time.sleep(2)
        
        # Set display environment
        os.environ["DISPLAY"] = f":{display_num}"
        
        # Start window manager
        logger.info("Starting Fluxbox window manager...")
        fluxbox_proc = subprocess.Popen([
            "fluxbox"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        vnc_processes.append(fluxbox_proc)
        time.sleep(2)
        
        # Start x11vnc
        vnc_port = 5900 + display_num
        logger.info(f"Starting x11vnc server on port {vnc_port}...")
        x11vnc_proc = subprocess.Popen([
            "x11vnc", "-display", f":{display_num}",
            "-nopw", "-listen", "0.0.0.0", "-xkb",
            "-rfbport", str(vnc_port), "-forever", "-shared"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        vnc_processes.append(x11vnc_proc)
        time.sleep(2)
        
        # Start NoVNC if available
        novnc_path = "/usr/share/novnc"
        if os.path.exists(novnc_path):
            logger.info("Starting NoVNC web interface on port 6080...")
            websockify_proc = subprocess.Popen([
                "websockify", "-D", "6080", f"localhost:{vnc_port}"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            vnc_processes.append(websockify_proc)
            time.sleep(2)
            
            # Get server IP
            try:
                result = subprocess.run("curl -s ifconfig.me", shell=True, capture_output=True, text=True)
                server_ip = result.stdout.strip()
                logger.info(f"🌐 VNC Web Access: http://{server_ip}:6080/vnc.html")
            except:
                logger.info("🌐 VNC Web Access: http://YOUR_SERVER_IP:6080/vnc.html")
        
        logger.info(f"🖥️  VNC Server ready on port {vnc_port}")
        logger.info(f"📱 You can connect with a VNC client or web browser")
        logger.info("🔗 The browser will be visible in the VNC session")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to set up VNC server: {e}")
        cleanup_vnc()
        return False

async def scrape_profile(username, headless=True, checkpoint_wait=60, output_dir="./output", use_vnc=False):
    """
    Scrape a Facebook profile using the command line
    
    Args:
        username: Facebook username to scrape
        headless: Run in headless mode (no visible browser)
        checkpoint_wait: Time to wait (in seconds) if security checkpoint detected
        output_dir: Directory to save output files
        use_vnc: Set up VNC server for remote access
    """
    try:
        # Set up VNC server if requested
        if use_vnc and not headless:
            if not setup_vnc_server():
                logger.error("Failed to set up VNC server")
                return False
        elif not headless:
            # Set display for X11 if not headless and not using VNC
            if not os.environ.get("DISPLAY"):
            os.environ["DISPLAY"] = ":1"
        
        # Create user data directory
        user_data_dir = os.path.join(os.path.expanduser("~"), ".facebook_scraper_data")
        os.makedirs(user_data_dir, exist_ok=True)
        
        # Create output directory structure
        os.makedirs(output_dir, exist_ok=True)
        screenshots_dir = os.path.join(output_dir, "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        
        # Create username-specific directory
        username_dir = os.path.join(output_dir, username)
        os.makedirs(username_dir, exist_ok=True)
        username_screenshots = os.path.join(username_dir, "screenshots")
        os.makedirs(username_screenshots, exist_ok=True)
        
        logger.info(f"🚀 Initializing Facebook session (headless={headless})...")
        session = FacebookSession(headless=headless, user_data_dir=user_data_dir)
        page = await session.initialize()
        
        # Check login status
        logger.info("🔐 Checking login status...")
        is_logged_in = await session.login_check()
        if not is_logged_in:
            logger.info("✅ Login completed successfully")
        else:
            logger.info("✅ Already logged in to Facebook")
        
        # Initialize helper classes
        utils = ScraperUtils(page, screenshot_dir=username_screenshots)
        profile_scraper = ProfileScraper(page, utils)
        posts_scraper = PostsScraper(page, utils)
        json_builder = JSONBuilder(output_dir=username_dir)
        
        # Set up dialog handlers
        await utils.handle_dialogs()
        
        # Navigate to profile
        logger.info(f"🎯 Navigating to profile: {username}")
        if use_vnc:
            logger.info("📺 You can watch the progress in your VNC viewer")
        if checkpoint_wait > 0:
            logger.info(f"⏰ Security checkpoint wait time: {checkpoint_wait} seconds")
        
        profile_exists = await profile_scraper.navigate_to_profile(username)
        
        if not profile_exists:
            logger.error(f"❌ Profile '{username}' not found")
            await session.close()
            return False
        
        # Check for security checkpoint after profile navigation
        checkpoint_detected = await utils.check_for_security_checkpoint()
        if checkpoint_detected:
            logger.warning("🔒 Security checkpoint detected! Please solve it manually.")
            await utils.handle_security_checkpoint(wait_time=checkpoint_wait)
        
        # Scrape data with progress tracking
        logger.info("📊 Starting comprehensive profile data collection...")
        scrape_data = {}
        
        # Helper function for progress tracking
        def log_progress(step, total, description):
            logger.info(f"📈 [{step}/{total}] {description}")
        
        # Basic profile info
        log_progress(1, 9, "Scraping basic profile info...")
        scrape_data["basic_info"] = await profile_scraper.get_basic_info()
        
        # Friends list
        log_progress(2, 9, "Scraping friends list...")
        scrape_data["friends_list"] = await profile_scraper.get_friends_list()
        
        # Groups
        log_progress(3, 9, "Scraping groups...")
        scrape_data["groups"] = await profile_scraper.get_groups()
        
        # Pages followed
        log_progress(4, 9, "Scraping pages followed...")
        scrape_data["pages_followed"] = await profile_scraper.get_pages_followed()
        
        # Following list
        log_progress(5, 9, "Scraping following list...")
        scrape_data["following_list"] = await profile_scraper.get_following_list()
        
        # Own posts
        log_progress(6, 9, "Scraping own posts...")
        scrape_data["own_posts"] = await posts_scraper.get_own_posts(username)
        
        # Tagged posts
        log_progress(7, 9, "Scraping tagged posts...")
        scrape_data["tagged_posts"] = await posts_scraper.get_tagged_posts(username)
        
        # User comments on other posts
        log_progress(8, 9, "Scraping user comments...")
        scrape_data["user_comments"] = await posts_scraper.get_user_comments(username)
        
        # Locations
        log_progress(9, 9, "Scraping locations...")
        scrape_data["locations"] = await posts_scraper.get_locations(username)
        
        # Build final JSON
        logger.info("📝 Building final JSON output...")
        result = json_builder.build_profile_json(username, scrape_data)
        
        # Print statistics
        logger.info("📊 Extraction Statistics:")
        logger.info(f"   👤 Profile name: {scrape_data['basic_info'].get('name', 'Unknown')}")
        logger.info(f"   👥 Friends: {len(scrape_data['friends_list'])}")
        logger.info(f"   📄 Pages followed: {len(scrape_data['pages_followed'])}")
        logger.info(f"   👥 Following: {len(scrape_data['following_list'])}")
        logger.info(f"   🏢 Groups: {len(scrape_data['groups'])}")
        logger.info(f"   📝 Own posts: {len(scrape_data['own_posts'])}")
        logger.info(f"   🏷️  Tagged posts: {len(scrape_data['tagged_posts'])}")
        logger.info(f"   💬 User comments: {len(scrape_data['user_comments'])}")
        logger.info(f"   📍 Locations: {len(scrape_data['locations'])}")
        
        # Save timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        logger.info(f"✅ Scraping completed at {timestamp}")
        logger.info(f"💾 Results saved to: {result['filepath']}")
        logger.info(f"📸 Screenshots saved to: {username_screenshots}")
        
        # Keep browser open for a few seconds if using VNC
        if use_vnc and not headless:
            logger.info("⏳ Keeping browser open for 30 seconds for final review...")
            await asyncio.sleep(30)
        
        # Close browser
        await session.close()
        
        # Clean up VNC if we set it up
        if use_vnc:
            logger.info("🧹 VNC server will remain running for remote access")
            logger.info("   Use Ctrl+C to stop the VNC server")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error scraping profile: {str(e)}")
        # Ensure browser is closed
        try:
            if 'session' in locals():
            await session.close()
        except:
            pass
        return False

def main():
    """Main entry point for CLI"""
    parser = argparse.ArgumentParser(description="Facebook Profile Scraper CLI with VNC Support")
    parser.add_argument("username", help="Facebook username to scrape")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (no browser UI)")
    parser.add_argument("--vnc", action="store_true", help="Set up VNC server for remote browser access")
    parser.add_argument("--wait", type=int, default=60, help="Time to wait for security checkpoints (seconds)")
    parser.add_argument("--output", type=str, default="./output", help="Output directory for results")
    
    args = parser.parse_args()
    
    # Set up signal handlers for clean VNC shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the scraper
    print(f"🚀 Starting Facebook Profile Scraper for '{args.username}'")
    
    if args.vnc:
        print("📺 VNC mode enabled - browser will be accessible remotely")
    elif not args.headless and os.environ.get("DISPLAY") is None:
        print("⚠️  WARNING: No display detected. Consider using --vnc or --headless")
    
    try:
        success = asyncio.run(scrape_profile(args.username, 
                               headless=args.headless, 
                               checkpoint_wait=args.wait,
                                           output_dir=args.output,
                                           use_vnc=args.vnc))
        
        if success:
            print("✅ Scraping completed successfully!")
            if args.vnc:
                print("📺 VNC server is still running. Press Ctrl+C to stop.")
                try:
                    # Keep VNC running until user stops it
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n🛑 Stopping VNC server...")
                    cleanup_vnc()
        else:
            print("❌ Scraping failed!")
            cleanup_vnc()
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        cleanup_vnc()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        cleanup_vnc()
        sys.exit(1)

if __name__ == "__main__":
    main()
