"""
Facebook Profile Scraper - FastAPI Application with VNC Support
"""
import os
import json
import asyncio
import uuid
import subprocess
import time
import signal
from pathlib import Path
from typing import Dict, Any, Optional, List
import aiofiles
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fpdf import FPDF

from scraper.session import FacebookSession
from scraper.profile import ProfileScraper
from scraper.posts import PostsScraper
from scraper.utils import ScraperUtils
from scraper.json_builder import JSONBuilder
from scraper.proxy_manager import proxy_manager

# Global variables for VNC cleanup
vnc_processes = []
display_num = None

def cleanup_vnc():
    """Clean up VNC processes on exit"""
    global vnc_processes, display_num
    
    print("🧹 Cleaning up VNC processes...")
    
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

def setup_vnc_server():
    """Set up VNC server for remote browser access"""
    global vnc_processes, display_num
    
    print("🖥️  Setting up VNC server for remote browser access...")
    
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
        print("❌ No available display found")
        return False
    
    print(f"📺 Using display :{display_num}")
    
    try:
        # Start Xvfb
        print("🔧 Starting Xvfb virtual display...")
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
        print("🪟 Starting Fluxbox window manager...")
        fluxbox_proc = subprocess.Popen([
            "fluxbox"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        vnc_processes.append(fluxbox_proc)
        time.sleep(2)
        
        # Start x11vnc
        vnc_port = 5900 + display_num
        print(f"🔗 Starting x11vnc server on port {vnc_port}...")
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
            print("🌐 Starting NoVNC web interface on port 6080...")
            websockify_proc = subprocess.Popen([
                "websockify", "-D", "6080", f"localhost:{vnc_port}"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            vnc_processes.append(websockify_proc)
            time.sleep(2)
            
            # Get server IP
            try:
                result = subprocess.run("curl -s ifconfig.me", shell=True, capture_output=True, text=True)
                server_ip = result.stdout.strip()
                print(f"🌐 VNC Web Access: http://{server_ip}:6080/vnc.html")
            except:
                print("🌐 VNC Web Access: http://YOUR_SERVER_IP:6080/vnc.html")
        
        print(f"✅ VNC Server ready on port {vnc_port}")
        print(f"📱 You can connect with a VNC client or web browser")
        print("🔗 The browser will be visible in the VNC session")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to set up VNC server: {e}")
        cleanup_vnc()
        return False

# Initialize FastAPI app
app = FastAPI(
    title="Facebook Profile Scraper with VNC Support",
    description="API for scraping Facebook profiles with VNC remote access support",
    version="2.0.0"
)

# Setup static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Create required directories
os.makedirs("static/screenshots", exist_ok=True)
os.makedirs("static/output", exist_ok=True)

# Cache for scraping results
scrape_results_cache = {}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Render the main page with scraping interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/scrape/{username:path}")
async def scrape_profile(username: str, use_vnc: bool = False, headless: bool = False, use_morocco_proxy: bool = True):
    """API endpoint to scrape a Facebook profile with optional VNC support"""
    
    # URL decode the username in case it's a full URL that was encoded
    import urllib.parse
    username = urllib.parse.unquote(username)
    
    # Clean up the username - remove any trailing slashes, @ symbols, or extra characters
    username = username.strip().rstrip('/').lstrip('@')
    
    print(f"🔍 Received username/URL: {username}")
    
    # Validate that we have a meaningful input
    if not username or len(username) < 3:
        raise HTTPException(status_code=400, detail="Invalid username or URL")
    
    # Additional validation for Facebook URLs
    if "facebook.com" in username and not any(x in username for x in ["profile.php?id=", "/", "."]):
        raise HTTPException(status_code=400, detail="Invalid Facebook URL format")
    
    try:
        print(f"🎯 Starting scrape for input: {username}")
        
        # Debug: Show URL detection results (imports already available at top)
        
        # Create temporary mock objects to test URL detection
        class MockPage:
            pass
        class MockUtils:
            pass
        
        temp_scraper = ProfileScraper(MockPage(), MockUtils())
        profile_type, profile_identifier = temp_scraper._detect_profile_type(username)
        constructed_url = temp_scraper._construct_profile_url(username)
        
        print(f"🔍 Detected type: {profile_type}")
        print(f"🔍 Profile identifier: {profile_identifier}")
        print(f"🔍 Will navigate to: {constructed_url}")
        
        # Use the clean profile identifier for directory names instead of full URL
        clean_username = profile_identifier
        
        # Set up VNC server if requested
        if use_vnc and not headless:
            if not setup_vnc_server():
                print("❌ Failed to set up VNC server, continuing without VNC...")
                use_vnc = False
        
        if use_vnc:
            print("📺 Browser will be visible in VNC session")
        elif not headless:
            print("📺 Browser will open using X11 forwarding")
        else:
            print("🤖 Running in headless mode")
        
        # Create user data directory - use persistent directory to maintain login
        user_data_dir = os.path.join(os.path.expanduser("~"), ".facebook_scraper_data")
        os.makedirs(user_data_dir, exist_ok=True)
        
        # Get Morocco proxy if requested
        proxy_url = None
        if use_morocco_proxy:
            print("🌍 Fetching working Morocco proxy...")
            try:
                proxy_url = await proxy_manager.get_working_proxy()
                if proxy_url:
                    # Verify proxy location
                    ip_info = await proxy_manager.get_ip_info(proxy_url)
                    print(f"🇲🇦 Using proxy from: {ip_info.get('country', 'Unknown')}, {ip_info.get('city', 'Unknown')}")
                    print(f"📍 Proxy IP: {proxy_url}")
                else:
                    print("⚠️ No working Morocco proxies found, continuing without proxy")
                    print("💡 This may trigger more security checkpoints from Facebook")
            except Exception as e:
                print(f"❌ Proxy setup failed: {e}")
                print("📄 Continuing without proxy...")
                proxy_url = None
        
        # Create username-specific output directory using clean identifier
        username_output_dir = os.path.join("static/output", clean_username)
        os.makedirs(username_output_dir, exist_ok=True)
        username_screenshots_dir = os.path.join(username_output_dir, "screenshots")
        os.makedirs(username_screenshots_dir, exist_ok=True)
        
        # Initialize session with appropriate display settings
        session = FacebookSession(headless=headless, user_data_dir=user_data_dir, proxy=proxy_url)
        page = await session.initialize()
        
        # Check if logged in with improved login detection
        is_logged_in = await session.login_check()
        if not is_logged_in:
            # The login_check method handles the login process
            print("✅ Login process completed!")
        else:
            print("✅ Already logged in!")
        
        # Initialize helper classes with username-specific directories
        utils = ScraperUtils(page, screenshot_dir=username_screenshots_dir)
        profile_scraper = ProfileScraper(page, utils)
        posts_scraper = PostsScraper(page, utils)
        json_builder = JSONBuilder(output_dir=username_output_dir)
        
        # Setup dialog handlers
        await utils.handle_dialogs()
        
        # Navigate to profile and handle security checkpoint if needed
        print(f"🎯 Navigating to profile {username}...")
        print("⏱️ This may take up to 5 minutes depending on Facebook's response time")
        if use_vnc:
            print("📺 You can watch the progress in your VNC viewer")
        print("🌍 Using international account-friendly navigation...")
        
        # Add human behavior before navigation
        await utils.random_mouse_movement()
        await utils.human_like_delay(3, 8)
        
        profile_exists = await profile_scraper.navigate_to_profile(username)
        if not profile_exists:
            print(f"❌ Failed to navigate to profile: {username}")
            await session.close()
            raise HTTPException(status_code=404, detail=f"Profile '{username}' not found or navigation failed")
        
        # Extra wait after successful navigation to ensure page is fully loaded
        print("✅ Profile loaded successfully, waiting for page to stabilize...")
        await utils.human_like_delay(15, 25)  # Realistic human page reading time
        
        # Additional checkpoint check after navigation using enhanced detection
        print("🔍 Enhanced security checkpoint check for international accounts...")
        checkpoint_detected = await utils.facebook_security_check()
        if checkpoint_detected:
            print("🔒 Security checkpoint detected after profile navigation!")
            print("⏳ This is normal for international accounts (Moroccan account in US)")
            
            await utils.handle_security_checkpoint(wait_time=120)  # 2 minutes
            print("✅ Checkpoint handling completed, continuing with scraping...")
            await utils.human_like_delay(3, 6)  # Faster stabilization time
        
        # Scrape all data with comprehensive error handling and delays
        scrape_data = {}
        
        print("🚀 Starting comprehensive profile data collection...")
        print("⏱️ This process may take 15-25 minutes with human-like delays to avoid detection")
        print("🤖 Using realistic human behavior patterns to prevent Facebook restrictions")
        
        # Helper function for safe scraping with realistic human behavior delays
        async def safe_scrape(func, name, *args, **kwargs):
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    print(f"📊 [{name}] (attempt {attempt + 1}/{max_retries + 1})...")
                    
                    # Realistic human behavior simulation to avoid detection
                    await utils.random_mouse_movement()
                    await utils.human_like_delay(8, 15)  # Longer pre-operation thinking time
                    await utils.human_scroll()  # Random scrolling like a human
                    
                    # Add timeout context for each scraping operation
                    result = await asyncio.wait_for(
                        func(*args, **kwargs), 
                        timeout=300.0  # 5 minutes per operation to accommodate delays
                    )
                    
                    print(f"✅ [{name}] completed successfully")
                    # Realistic wait between operations (human reading/processing time)
                    await utils.human_like_delay(20, 35)  # 20-35 seconds between operations
                    return result
                    
                except asyncio.TimeoutError:
                    print(f"⚠️ Timeout in [{name}] after 5 minutes")
                    if attempt < max_retries:
                        print(f"🔄 Retrying [{name}] in 30 seconds...")
                        await asyncio.sleep(30)  # Longer retry delay
                    else:
                        print(f"❌ Failed [{name}] after {max_retries + 1} attempts (timeout)")
                        return {}
                        
                except Exception as e:
                    print(f"⚠️ Error in [{name}]: {str(e)}")
                    if attempt < max_retries:
                        print(f"🔄 Retrying [{name}] in 30 seconds...")
                        await asyncio.sleep(30)
                    else:
                        print(f"❌ Failed [{name}] after {max_retries + 1} attempts")
                        return {}
        
        # Basic profile info
        scrape_data["basic_info"] = await safe_scrape(
            profile_scraper.get_basic_info, 
            "Basic profile info"
        )
        
        # Friends list
        scrape_data["friends_list"] = await safe_scrape(
            profile_scraper.get_friends_list, 
            "Friends list"
        )
        
        # Groups
        scrape_data["groups"] = await safe_scrape(
            profile_scraper.get_groups, 
            "Groups"
        )
        
        # Pages followed
        scrape_data["pages_followed"] = await safe_scrape(
            profile_scraper.get_pages_followed, 
            "Pages followed"
        )
        
        # Following list
        scrape_data["following_list"] = await safe_scrape(
            profile_scraper.get_following_list, 
            "Following list"
        )
        
        # Own posts
        scrape_data["own_posts"] = await safe_scrape(
            posts_scraper.get_own_posts, 
            "Own posts",
            username  # Keep original username for navigation
        )
        
        # Tagged posts
        scrape_data["tagged_posts"] = await safe_scrape(
            posts_scraper.get_tagged_posts, 
            "Tagged posts",
            username  # Keep original username for navigation
        )
        
        # User comments on other posts
        scrape_data["user_comments"] = await safe_scrape(
            posts_scraper.get_user_comments, 
            "User comments",
            username  # Keep original username for navigation
        )
        
        # Locations
        scrape_data["locations"] = await safe_scrape(
            posts_scraper.get_locations, 
            "Locations",
            username  # Keep original username for navigation
        )
        
        print("🎉 All scraping operations completed!")
        
        # Build JSON
        print("📝 Building final JSON output...")
        result = json_builder.build_profile_json(clean_username, scrape_data)
        
        # Print extraction statistics
        print("📊 Extraction Statistics:")
        print(f"   👤 Profile name: {scrape_data.get('basic_info', {}).get('name', 'Unknown')}")
        print(f"   👥 Friends: {len(scrape_data.get('friends_list', []))}")
        print(f"   📄 Pages followed: {len(scrape_data.get('pages_followed', []))}")
        print(f"   👥 Following: {len(scrape_data.get('following_list', []))}")
        print(f"   🏢 Groups: {len(scrape_data.get('groups', []))}")
        print(f"   📝 Own posts: {len(scrape_data.get('own_posts', []))}")
        print(f"   🏷️  Tagged posts: {len(scrape_data.get('tagged_posts', []))}")
        print(f"   💬 User comments: {len(scrape_data.get('user_comments', []))}")
        print(f"   📍 Locations: {len(scrape_data.get('locations', []))}")
        
        # Cache the result  
        scrape_results_cache[clean_username] = result
        
        print("✅ Scraping completed successfully!")
        print(f"💾 Results saved to: {result['filepath']}")
        # print(f"📸 Screenshots saved to: {username_screenshots_dir}")
        
        if use_vnc:
            print("⏳ Keeping browser open for 10 seconds for final review...")
            await asyncio.sleep(10)  # Reduced VNC review time
        else:
            print("🕐 Keeping browser open for 5 seconds to ensure all data is processed...")
            await asyncio.sleep(5)  # Reduced processing time
        
        # Close browser session
        await session.close()
        
        return result["data"]
    
    except Exception as e:
        print(f"❌ Error scraping profile: {str(e)}")
        # Ensure browser is closed in case of error
        try:
            if 'session' in locals():
                await session.close()
        except Exception as close_error:
            print(f"Error closing session: {close_error}")
        raise HTTPException(status_code=500, detail=f"Error scraping profile: {str(e)}")

@app.get("/download/{username:path}/json")
async def download_json(username: str):
    """Download the scraped data as a JSON file"""
    import urllib.parse
    username = urllib.parse.unquote(username).strip().rstrip('/').lstrip('@')
    
    # Extract clean identifier for file lookup
    temp_scraper = ProfileScraper(type('MockPage', (), {})(), type('MockUtils', (), {})())
    profile_type, clean_identifier = temp_scraper._detect_profile_type(username)
    
    # Check if we have cached results or find the latest file
    if clean_identifier in scrape_results_cache:
        filepath = scrape_results_cache[clean_identifier]["filepath"]
    else:
        # Try to find the latest file for this username
        username_dir = Path("static/output") / clean_identifier
        pattern = f"{clean_identifier}_profile_*.json"
        files = list(username_dir.glob(pattern))
        
        if not files:
            # Fallback to old location
            files = list(Path("static/output").glob(pattern))
        
        if not files:
            raise HTTPException(status_code=404, detail=f"No data found for {clean_identifier}")
        
        # Sort by creation time (newest first)
        filepath = str(sorted(files, key=lambda x: x.stat().st_ctime, reverse=True)[0])
    
    return FileResponse(
        filepath,
        media_type="application/json",
        filename=f"{clean_identifier}_facebook_data.json"
    )

@app.get("/pdf/{username:path}")
async def generate_pdf(username: str):
    """Generate a PDF report of the profile data"""
    try:
        import urllib.parse
        username = urllib.parse.unquote(username).strip().rstrip('/').lstrip('@')
        
        # Extract clean identifier for file lookup
        temp_scraper = ProfileScraper(type('MockPage', (), {})(), type('MockUtils', (), {})())
        profile_type, clean_identifier = temp_scraper._detect_profile_type(username)
        
        # Check if we have cached results
        if clean_identifier not in scrape_results_cache:
            # Try to find the latest file for this username
            username_dir = Path("static/output") / clean_identifier
            pattern = f"{clean_identifier}_profile_*.json"
            files = list(username_dir.glob(pattern))
            
            if not files:
                # Fallback to old location
                files = list(Path("static/output").glob(pattern))
            
            if not files:
                raise HTTPException(status_code=404, detail=f"No data found for {clean_identifier}")
            
            # Load the JSON data
            json_file = sorted(files, key=lambda x: x.stat().st_ctime, reverse=True)[0]
            async with aiofiles.open(json_file, "r") as f:
                content = await f.read()
                data = json.loads(content)
        else:
            data = scrape_results_cache[clean_identifier]["data"]
        
        # Create PDF in username directory
        username_dir = Path("static/output") / clean_identifier
        username_dir.mkdir(exist_ok=True)
        pdf_path = username_dir / f"{clean_identifier}_profile_report.pdf"
        
        # Generate the PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, f"Facebook Profile Report: {clean_identifier}", ln=True)
        pdf.ln(10)
        
        # Basic info
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Basic Information", ln=True)
        pdf.set_font("Arial", "", 12)
        
        profile_info = data.get("profile", {})
        pdf.cell(0, 10, f"Name: {profile_info.get('name', 'N/A')}", ln=True)
        
        if profile_info.get("bio"):
            pdf.multi_cell(0, 10, f"Bio: {profile_info['bio']}")
        
        about_info = profile_info.get("about", {})
        if about_info.get("location"):
            pdf.cell(0, 10, f"Location: {about_info['location']}", ln=True)
        if about_info.get("birthday"):
            pdf.cell(0, 10, f"Birthday: {about_info['birthday']}", ln=True)
        if about_info.get("work"):
            pdf.cell(0, 10, f"Work: {about_info['work']}", ln=True)
        if about_info.get("education"):
            pdf.cell(0, 10, f"Education: {about_info['education']}", ln=True)
        
        # Stats summary
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Profile Statistics", ln=True)
        pdf.set_font("Arial", "", 12)
        
        friends_count = len(profile_info.get("friends", []))
        groups_count = len(profile_info.get("groups", []))
        pages_count = len(profile_info.get("pages_followed", []))
        posts_count = len(data.get("posts", {}).get("own_posts", []))
        
        pdf.cell(0, 10, f"Friends: {friends_count}", ln=True)
        pdf.cell(0, 10, f"Groups: {groups_count}", ln=True)
        pdf.cell(0, 10, f"Pages Followed: {pages_count}", ln=True)
        pdf.cell(0, 10, f"Posts: {posts_count}", ln=True)
        
        # Posts summary
        own_posts = data.get("posts", {}).get("own_posts", [])
        if own_posts:
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Recent Posts", ln=True)
            
            for i, post in enumerate(own_posts[:5]):  # Limit to 5 posts
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, f"Post {i+1}", ln=True)
                pdf.set_font("Arial", "", 12)
                
                if post.get("timestamp"):
                    pdf.cell(0, 10, f"Date: {post['timestamp']}", ln=True)
                
                if post.get("content"):
                    pdf.multi_cell(0, 10, f"Content: {post['content'][:200]}...")
                
                if post.get("comments"):
                    pdf.cell(0, 10, f"Comments: {len(post['comments'])}", ln=True)
                
                pdf.cell(0, 10, "", ln=True)  # Add space between posts
        
        # Save the PDF
        pdf.output(str(pdf_path))
        
        return FileResponse(
            str(pdf_path),
            media_type="application/pdf",
            filename=f"{clean_identifier}_facebook_report.pdf"
        )
    
    except Exception as e:
        print(f"❌ Error generating PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Check proxy status
    proxy_status = {
        "available_proxies": len(proxy_manager.working_proxies),
        "moroccan_proxies": len([p for p in proxy_manager.working_proxies if p.get('country') == 'MA']),
        "last_refresh": proxy_manager.last_fetch_time
    }
    
    return {
        "status": "ok", 
        "mode": "VNC + X11 forwarding support", 
        "vnc_active": len(vnc_processes) > 0,
        "proxy_status": proxy_status
    }

@app.get("/vnc/status")
async def vnc_status():
    """Check VNC server status"""
    return {
        "vnc_active": len(vnc_processes) > 0,
        "display": display_num,
        "processes": len(vnc_processes)
    }

@app.post("/vnc/start")
async def start_vnc():
    """Start VNC server"""
    if len(vnc_processes) > 0:
        return {"message": "VNC server already running", "display": display_num}
    
    success = setup_vnc_server()
    if success:
        return {"message": "VNC server started successfully", "display": display_num}
    else:
        raise HTTPException(status_code=500, detail="Failed to start VNC server")

@app.post("/vnc/stop")
async def stop_vnc():
    """Stop VNC server"""
    cleanup_vnc()
    return {"message": "VNC server stopped"}

@app.get("/proxy/status")
async def proxy_status():
    """Get detailed proxy status"""
    moroccan_proxies = [p for p in proxy_manager.working_proxies if p.get('country') == 'MA']
    other_proxies = [p for p in proxy_manager.working_proxies if p.get('country') != 'MA']
    
    return {
        "total_proxies": len(proxy_manager.working_proxies),
        "moroccan_proxies": len(moroccan_proxies),
        "other_proxies": len(other_proxies),
        "last_refresh": proxy_manager.last_fetch_time,
        "next_refresh": proxy_manager.last_fetch_time + proxy_manager.fetch_interval,
        "proxy_details": {
            "moroccan": [f"{p['ip']}:{p['port']}" for p in moroccan_proxies[:5]],
            "others": [f"{p['ip']}:{p['port']} ({p.get('country', 'Unknown')})" for p in other_proxies[:5]]
        }
    }

@app.post("/proxy/refresh")
async def refresh_proxies():
    """Manually refresh proxy list"""
    try:
        await proxy_manager.refresh_proxies()
        return {
            "message": "Proxies refreshed successfully",
            "total_proxies": len(proxy_manager.working_proxies),
            "moroccan_proxies": len([p for p in proxy_manager.working_proxies if p.get('country') == 'MA'])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh proxies: {str(e)}")

@app.get("/proxy/test")
async def test_proxy_endpoint():
    """Test proxy functionality"""
    try:
        proxy_url = await proxy_manager.get_working_proxy()
        if proxy_url:
            ip_info = await proxy_manager.get_ip_info(proxy_url)
            return {
                "status": "success",
                "proxy_url": proxy_url,
                "location": {
                    "country": ip_info.get('country', 'Unknown'),
                    "region": ip_info.get('regionName', 'Unknown'),
                    "city": ip_info.get('city', 'Unknown'),
                    "ip": ip_info.get('query', 'Unknown')
                }
            }
        else:
            return {"status": "no_proxies", "message": "No working proxies available"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy test failed: {str(e)}")

@app.post("/proxy/local/setup")
async def setup_local_proxy(
    local_user: str,
    local_host: str,
    tunnel_port: int = 9999,
    local_port: int = 8888,
    ssh_key_path: str = None
):
    """Set up SSH tunnel to local proxy"""
    try:
        success = proxy_manager.setup_ssh_tunnel(
            local_user=local_user,
            local_host=local_host,
            tunnel_port=tunnel_port,
            local_port=local_port,
            ssh_key_path=ssh_key_path
        )
        
        if success:
            return {
                "status": "success",
                "message": "SSH tunnel established successfully",
                "proxy_url": proxy_manager.local_proxy_url
            }
        else:
            return {
                "status": "failed",
                "message": "Failed to establish SSH tunnel"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Local proxy setup failed: {str(e)}")

@app.post("/proxy/local/enable")
async def enable_local_proxy(tunnel_port: int = 9999):
    """Enable local proxy (assuming tunnel is already established)"""
    try:
        proxy_manager.enable_local_proxy(tunnel_port)
        is_working = proxy_manager.test_local_proxy()
        
        return {
            "status": "enabled",
            "proxy_url": proxy_manager.local_proxy_url,
            "working": is_working
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enable local proxy: {str(e)}")

@app.post("/proxy/local/disable")
async def disable_local_proxy():
    """Disable local proxy and cleanup SSH tunnel"""
    try:
        proxy_manager.disable_local_proxy()
        return {"status": "disabled", "message": "Local proxy disabled successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disable local proxy: {str(e)}")

@app.get("/proxy/current")
async def get_current_proxy():
    """Get information about currently active proxy"""
    try:
        proxy_info = proxy_manager.get_current_proxy_info()
        return proxy_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get proxy info: {str(e)}")

# Run the app with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)