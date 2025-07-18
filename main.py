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
from scraper.proxy_manager import ProxyManager

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

# Initialize proxy manager
proxy_manager = ProxyManager()

async def load_saved_cookies(session, page):
    """Load saved cookies from facebook_cookies.json if available"""
    cookies_file = "facebook_cookies.json"
    
    try:
        if not os.path.exists(cookies_file):
            print("ℹ️ No saved cookies found - will proceed with fresh login")
            return False
        
        print(f"🍪 Loading saved cookies from {cookies_file}...")
        
        # Load cookie data
        with open(cookies_file, 'r') as f:
            cookie_data = json.load(f)
        
        if 'cookies' not in cookie_data:
            print("❌ Invalid cookie file format")
            return False
        
        # Add cookies to browser context
        await session.context.add_cookies(cookie_data['cookies'])
        print(f"✅ Loaded {len(cookie_data['cookies'])} cookies from Morocco session")
        
        # Set user agent to match the saved session
        if 'user_agent' in cookie_data:
            print(f"🔧 Using saved user agent: {cookie_data['user_agent'][:50]}...")
        
        # Load localStorage if available
        if 'local_storage' in cookie_data and cookie_data['local_storage']:
            try:
                await page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=30000)
                await page.evaluate("""
                    (storage) => {
                        for (const [key, value] of Object.entries(storage)) {
                            try {
                                localStorage.setItem(key, value);
                            } catch (e) {
                                console.log('Could not set localStorage item:', key, e);
                            }
                        }
                    }
                """, cookie_data['local_storage'])
                print(f"✅ Loaded {len(cookie_data['local_storage'])} localStorage items")
            except Exception as e:
                print(f"⚠️ localStorage loading warning: {e}")
        
        print("🎉 Cookie loading completed - should be logged in from Morocco session!")
        return True
        
    except Exception as e:
        print(f"❌ Error loading cookies: {e}")
        return False

@app.get("/")
async def root():
    """Return API documentation"""
    # Get server IP for examples
    try:
        result = subprocess.run("curl -s ifconfig.me", shell=True, capture_output=True, text=True)
        server_ip = result.stdout.strip()
    except:
        server_ip = "YOUR_SERVER_IP"
    
    return {
        "endpoints": {
            "/": "This documentation",
            "/api/scrape/{username}": {
                "description": "Scrape a Facebook profile",
                "parameters": {
                    "username": "string - Facebook username to scrape",
                    "headless": "boolean - Run in headless mode (default: true)"
                },
                "example": {
                    "basic": f"curl 'http://{server_ip}:8080/api/scrape/username' -o profile_data.json",
                },
                "returns": "Profile data in JSON format"
            },
            "/api/status": {
                "description": "Get server status",
                "parameters": {},
                "example": f"curl 'http://{server_ip}:8080/api/status'",
                "returns": "Server status information"
            }
        }
    }

@app.get("/web")
async def web_interface(request: Request):
    """Serve the web interface for interactive scraping"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/scrape/{username:path}")
async def web_scrape_profile(username: str):
    """Web interface endpoint for profile scraping"""
    try:
        # Call the main scraping function
        result = await scrape_profile(
            username=username, 
            use_vnc=False,
            headless=True
        )
        
        # Cache the result for downloads
        scrape_results_cache[username] = result
        
        response_data = {
            "success": True,
            "username": username,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "data": result
        }
        
        return response_data
        
    except Exception as e:
        error_response = {
            "success": False,
            "error": str(e),
            "username": username,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        }
        return error_response

@app.get("/api/scrape/{username:path}")
async def api_scrape_profile(username: str, headless: bool = True):
    """
    Clean API endpoint for external clients - optimized for curl usage
    Returns pure JSON data that can be directly saved to file
    
    Usage: curl http://your-server-ip:8080/api/scrape/username -o output.json
    """
    try:
        # Call the main scraping function with API-optimized settings
        result = await scrape_profile(
            username=username, 
            use_vnc=False,  # Never use VNC for API calls
            headless=headless
        )
        
        # Return clean JSON data structure
        return {
            "success": True,
            "username": username,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "data": result
        }
        
    except HTTPException as he:
        return {
            "success": False,
            "error": {
                "code": he.status_code,
                "message": he.detail
            },
            "username": username,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": 500,
                "message": str(e)
            },
            "username": username,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        }

@app.get("/api/quick/{username:path}")
async def api_quick_scrape(username: str):
    """
    DEPRECATED - Quick API endpoint removed 
    Use /api/scrape/{username} for full profile scraping
    """
    return {
        "success": False,
        "error": {
            "code": 410,
            "message": "Quick friends-only scraping has been removed. Use /api/scrape/{username} for complete profile data."
        },
        "username": username,
        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    }

@app.get("/api/docs")
async def api_documentation():
    """API endpoint documentation for client testing"""
    # Get server IP for examples
    try:
        result = subprocess.run("curl -s ifconfig.me", shell=True, capture_output=True, text=True)
        server_ip = result.stdout.strip()
    except:
        server_ip = "YOUR_SERVER_IP"
    
    return {
        "facebook_scraper_api": {
            "version": "2.0.0",
            "description": "Facebook Profile Scraper API with optimized performance",
            "base_url": f"http://{server_ip}:8080",
            "authentication": "Uses saved Morocco cookies automatically",
            "curl_examples": {
                "full_scrape": f"curl http://{server_ip}:8080/api/scrape/username -o profile_data.json",
                "health_check": f"curl http://{server_ip}:8080/health",
                "with_proxy": f"curl 'http://{server_ip}:8080/api/scrape/username?use_morocco_proxy=true' -o profile_data.json"
            },
            "endpoints": {
                "api_scrape": {
                    "url": "/api/scrape/{username}",
                    "method": "GET", 
                    "description": "Complete profile scraping - optimized for curl",
                    "parameters": {
                        "username": "Facebook username or profile URL",
                        "headless": "boolean - Run headless (default: true)", 
                        "use_morocco_proxy": "boolean - Use Morocco proxy (default: false)"
                    },
                    "estimated_time": "10-15 minutes",
                    "response": "Clean JSON with success flag and scraped data"
                },
                "api_quick": {
                    "url": "/api/quick/{username}",
                    "method": "GET",
                    "description": "DEPRECATED - Quick scrape functionality removed",
                    "estimated_time": "N/A",
                    "response": "Error message indicating deprecation"
                },
                "health_check": {
                    "url": "/health",
                    "method": "GET",
                    "description": "Check server status and available features",
                    "response": "Server status, cookies availability, proxy status"
                }
            },
            "response_format": {
                "success_response": {
                    "success": True,
                    "username": "string",
                    "scraped_at": "timestamp",
                    "data": {
                        "profile": {"name": "...", "bio": "..."},
                        "groups": [],
                        "posts": {}
                    }
                },
                "error_response": {
                    "success": False,
                    "error": {"code": 404, "message": "Profile not found"},
                    "username": "string",
                    "scraped_at": "timestamp"
                }
            },
            "client_workflow": [
                "1. Check server health: curl http://ip:8080/health",
                "2. Full scrape: curl http://ip:8080/api/scrape/username -o profile.json",
                "3. Check output: cat profile.json | jq '.success'"
            ],
            "notes": {
                "authentication": "facebook_cookies.json must be present on server",
                "rate_limiting": "Built-in delays to prevent Facebook detection", 
                "concurrent_requests": "Only one scraping operation at a time recommended",
                "output_format": "All responses are valid JSON suitable for direct file saving"
            }
        }
    }

@app.get("/scrape/{username:path}")
async def scrape_profile(username: str, use_vnc: bool = False, headless: bool = True):
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
        
        # Initialize without proxy
        proxy_url = None
        
        # Create username-specific output directory using clean identifier
        username_output_dir = os.path.join("static/output", clean_username)
        os.makedirs(username_output_dir, exist_ok=True)
        username_screenshots_dir = os.path.join(username_output_dir, "screenshots")
        os.makedirs(username_screenshots_dir, exist_ok=True)
        
        # Initialize session with appropriate display settings
        session = FacebookSession(headless=headless, user_data_dir=user_data_dir, proxy=proxy_url)
        page = await session.initialize()
        
        # Load saved cookies if available
        cookies_loaded = await load_saved_cookies(session, page)
        if cookies_loaded:
            print("🍪 Cookies loaded from Morocco session - should be logged in!")
        else:
            print("ℹ️ No saved cookies found - will need to login manually")
        
        # Check if logged in with improved login detection
        is_logged_in = await session.login_check()
        if not is_logged_in:
            # The login_check method handles the login process
            print("✅ Login process completed!")
        else:
            if cookies_loaded:
                print("✅ Successfully logged in using saved Morocco cookies!")
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
        
        # Quick wait after successful navigation
        print("✅ Profile loaded successfully, waiting for page to stabilize...")
        await utils.human_like_delay(5, 8)  # Reduced from 15-25 seconds
        
        # Quick checkpoint check
        print("🔍 Enhanced security checkpoint check for international accounts...")
        checkpoint_detected = await utils.facebook_security_check()
        if checkpoint_detected:
            print("🔒 Security checkpoint detected after profile navigation!")
            print("⏳ This is normal for international accounts (Moroccan account in US)")
            
            await utils.handle_security_checkpoint(wait_time=60)  # Reduced from 2 minutes to 1 minute
            print("✅ Checkpoint handling completed, continuing with scraping...")
            await utils.human_like_delay(2, 4)  # Reduced delay
        
        # Scrape all data with comprehensive error handling and delays
        scrape_data = {}
        
        print("🚀 Starting profile data collection...")
        print("⏱️ This process should take 5-10 minutes with optimized timing")
        print("🤖 Using minimal delays for faster extraction")
        
        # Helper function for safe scraping with minimal delays
        async def safe_scrape(func, name, *args, **kwargs):
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    print(f"📊 [{name}] (attempt {attempt + 1}/{max_retries + 1})...")
                    
                    # Minimal delays to speed up process
                    await utils.human_like_delay(2, 4)  # Short pre-operation delay
                    
                    # The timeout is now handled inside the scraper functions themselves
                    # to allow for partial data return.
                    result = await func(*args, **kwargs)
                    
                    print(f"✅ [{name}] completed successfully")
                    # Minimal wait between operations
                    await utils.human_like_delay(3, 6)  # 3-6 seconds between operations
                    return result
                    
                except Exception as e:
                    print(f"⚠️ Error in [{name}]: {str(e)}")
                    if attempt < max_retries:
                        print(f"🔄 Retrying [{name}] in 10 seconds...")
                        await asyncio.sleep(10)  # Reduced retry delay
                    else:
                        print(f"❌ Failed [{name}] after {max_retries + 1} attempts")
                        return {}
        
        # All post types
        scrape_data["posts"] = await safe_scrape(
            posts_scraper.get_all_post_types,
            "All Posts",
            username
        )

        # # User comments on other posts
        # scrape_data["user_comments"] = await safe_scrape(
        #     posts_scraper.get_user_comments, 
        #     "User comments",
        #     username  # Keep original username for navigation
        # )
        
        # # Locations
        # scrape_data["locations"] = await safe_scrape(
        #     posts_scraper.get_locations, 
        #     "Locations",
        #     username  # Keep original username for navigation
        # )
        
        print("🎉 All scraping operations completed!")
        
        # Build JSON
        print("📝 Building final JSON output...")
        result = json_builder.build_profile_json(clean_username, scrape_data)
        
        # Print extraction statistics
        print("📊 Extraction Statistics:")
        # print(f"   👤 Profile name: {scrape_data.get('basic_info', {}).get('name', 'Unknown')}")
        # print(f"   👥 Friends: {len(scrape_data.get('friends_list', []))}")
        # print(f"   🏢 Groups: {len(scrape_data.get('groups', []))}")
        # print(f"   📄 Pages followed: {len(scrape_data.get('pages_followed', []))}")
        # print(f"   👥 Following: {len(scrape_data.get('following_list', []))}")
        posts_data = scrape_data.get("posts", {})
        print(f"   📝 Own posts: {len(posts_data.get('own_posts', []))}")
        print(f"   🏷️  Tagged posts: {len(posts_data.get('tagged_posts', []))}")
        print(f"   🔗 Shared posts: {len(posts_data.get('shared_posts', []))}")
        # print(f"   💬 User comments: {len(scrape_data.get('user_comments', []))}")
        # print(f"   📍 Locations: {len(scrape_data.get('locations', []))}")
        
        # Cache the result  
        scrape_results_cache[clean_username] = result
        
        print("✅ Scraping completed successfully!")
        print(f"💾 Results saved to: {result['filepath']}")
        # print(f"📸 Screenshots saved to: {username_screenshots_dir}")
        
        if use_vnc:
            print("⏳ Keeping browser open for 3 seconds for final review...")
            await asyncio.sleep(3)  # Minimal VNC review time
        else:
            print("🕐 Keeping browser open for 2 seconds to ensure all data is processed...")
            await asyncio.sleep(2)  # Minimal processing time
        
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
        posts_count = len(data.get("posts", {}).get("own_posts", []));
        
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
    
    # Check cookies status
    cookies_available = os.path.exists("facebook_cookies.json")
    
    # Get server IP for client examples
    try:
        result = subprocess.run("curl -s ifconfig.me", shell=True, capture_output=True, text=True)
        server_ip = result.stdout.strip()
    except:
        server_ip = "YOUR_SERVER_IP"
    
    return {
        "status": "ok", 
        "mode": "VNC + X11 forwarding support", 
        "vnc_active": len(vnc_processes) > 0,
        "cookies_available": cookies_available,
        "proxy_status": proxy_status,
        "server_ip": server_ip,
        "api_endpoints": {
            "curl_ready": {
                "full_scrape": f"curl http://{server_ip}:8080/api/scrape/username -o profile.json",
                "health_check": f"curl http://{server_ip}:8080/health"
            },
            "web_interface": {
                "scrape_full": "/scrape/{username}",
                "test_scraper": "/test/{username}",  
                "quick_test": "/quick-test/{username}",
                "download_json": "/download/{username}/json",
                "download_pdf": "/pdf/{username}"
            }
        },
        "documentation": f"http://{server_ip}:8080/api/docs"
    }

@app.get("/status")
async def get_status():
    """Get server status for web interface"""
    return {
        "status": "running",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "version": "2.0.0"
    }

@app.get("/download/{username}/json")
async def download_json(username: str):
    """Download scraped data as JSON file"""
    try:
        if username in scrape_results_cache:
            filename = f"{username}_profile_data.json"
            # Create a temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(scrape_results_cache[username], f, indent=2, ensure_ascii=False)
                temp_path = f.name
            
            return FileResponse(
                temp_path,
                filename=filename,
                media_type='application/json'
            )
        else:
            raise HTTPException(status_code=404, detail="Data not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pdf/{username}")
async def download_pdf(username: str):
    """Download scraped data as PDF file"""
    try:
        if username in scrape_results_cache:
            from scraper.json_builder import FacebookDataProcessor
            processor = FacebookDataProcessor()
            
            # Generate PDF
            pdf_path = await processor.generate_pdf(scrape_results_cache[username], username)
            
            return FileResponse(
                pdf_path,
                filename=f"{username}_profile.pdf",
                media_type='application/pdf'
            )
        else:
            raise HTTPException(status_code=404, detail="Data not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

@app.get("/test/{username:path}")
async def test_scraper(username: str):
    """DEPRECATED - Test scraper endpoint removed"""
    return {
        "status": "deprecated",
        "username": username,
        "message": "Test scraper functionality has been removed. Use /api/scrape/{username} for profile scraping.",
        "error": "Endpoint deprecated and disabled"
    }

@app.get("/quick-test/{username:path}")
async def quick_test_friends_only(username: str):
    """Test friends list scraping only"""
    try:
        # URL decode the username
        import urllib.parse
        username = urllib.parse.unquote(username).strip().rstrip('/').lstrip('@')
        
        if not username or len(username) < 3:
            raise HTTPException(status_code=400, detail="Invalid username")
        
        print(f"🧪 Quick friends test for: {username}")
        
        # Create user data directory
        user_data_dir = os.path.join(os.path.expanduser("~"), ".facebook_scraper_data")
        os.makedirs(user_data_dir, exist_ok=True)
        
        # Initialize session
        session = FacebookSession(headless=True, user_data_dir=user_data_dir)
        page = await session.initialize()
        
        # Load saved cookies
        cookies_loaded = await load_saved_cookies(session, page)
        
        # Check login
        is_logged_in = await session.login_check()
        if not is_logged_in:
            await session.close()
            raise HTTPException(status_code=401, detail="Not logged in to Facebook")
        
        # Initialize scraper
        utils = ScraperUtils(page)
        profile_scraper = ProfileScraper(page, utils)
        
        # Navigate to profile
        profile_exists = await profile_scraper.navigate_to_profile(username)
        if not profile_exists:
            await session.close()
            raise HTTPException(status_code=404, detail=f"Profile '{username}' not found")
        
        # Scrape friends only
        print("👥 Scraping friends list...")
        friends = await profile_scraper.get_friends_list(max_scrolls=10)
        
        await session.close()
        
        return {
            "status": "success",
            "username": username,
            "friends_count": len(friends),
            "friends": friends[:10],  # Return first 10 friends as sample
            "message": "Friends list scraped successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in friends test: {str(e)}")
        try:
            if 'session' in locals():
                await session.close()
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Error testing friends scraping: {str(e)}")

# Run the app with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)