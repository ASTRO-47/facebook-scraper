"""
Facebook Profile Scraper - FastAPI Application
"""
import os
import json
import asyncio
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

# Initialize FastAPI app
app = FastAPI(
    title="Facebook Profile Scraper",
    description="API for scraping Facebook profiles using Playwright",
    version="1.0.0"
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

@app.get("/scrape/{username}")
async def scrape_profile(username: str):
    """API endpoint to scrape a Facebook profile"""
    if not username or len(username) < 3:
        raise HTTPException(status_code=400, detail="Invalid username")
    
    try:
        # Initialize Facebook session with visible browser using X11 display
        os.environ["DISPLAY"] = ":1"
        
        # Create user data directory in a location accessible by the current user
        user_data_dir = os.path.join(os.path.expanduser("~"), ".facebook_scraper_data")
        os.makedirs(user_data_dir, exist_ok=True)
        
        # Initialize session with persistent storage
        session = FacebookSession(headless=False, user_data_dir=user_data_dir)
        page = await session.initialize()
        
        # Check if logged in with improved login detection
        is_logged_in = await session.login_check()
        if not is_logged_in:
            # The login_check method already waits for login completion
            # Add extra wait time to ensure page is fully loaded after login
            await asyncio.sleep(5)
            print("Successfully logged in and session saved!")
        
        # Initialize helper classes
        utils = ScraperUtils(page, screenshot_dir="static/screenshots")
        profile_scraper = ProfileScraper(page, utils)
        posts_scraper = PostsScraper(page, utils)
        json_builder = JSONBuilder(output_dir="static/output")
        
        # Setup dialog handlers
        await utils.handle_dialogs()
        
        # Navigate to profile and handle security checkpoint if needed
        print(f"Navigating to profile {username}. If a security puzzle appears, you'll have 2 minutes to solve it...")
        profile_exists = await profile_scraper.navigate_to_profile(username)
        if not profile_exists:
            await session.close()
            raise HTTPException(status_code=404, detail=f"Profile '{username}' not found")
        
        # Check for security checkpoint one more time after navigating to profile
        print("Checking for security checkpoints...")
        checkpoint_detected = await utils.check_for_security_checkpoint()
        if checkpoint_detected:
            print("Security checkpoint detected! Please solve it manually.")
            # Take a screenshot of the security checkpoint
            checkpoint_screenshot = await utils.take_screenshot("security_checkpoint")
            print(f"Security checkpoint screenshot saved to {checkpoint_screenshot}")
            print("Waiting for 2 minutes to allow manual solving of the security puzzle...")
            
            # Wait for the user to solve the challenge
            await utils.handle_security_checkpoint(wait_time=120)
            print("Security checkpoint wait time completed. Continuing with scraping...")
        
        # Scrape all data
        scrape_data = {}
        
        # Basic profile info
        print(f"Scraping basic info for {username}...")
        scrape_data["basic_info"] = await profile_scraper.get_basic_info()
        
        # Friends list
        print("Scraping friends list...")
        scrape_data["friends_list"] = await profile_scraper.get_friends_list()
        
        # Groups
        print("Scraping groups...")
        scrape_data["groups"] = await profile_scraper.get_groups()
        
        # Pages followed
        print("Scraping pages followed...")
        scrape_data["pages_followed"] = await profile_scraper.get_pages_followed()
        
        # Following list
        print("Scraping following list...")
        scrape_data["following_list"] = await profile_scraper.get_following_list()
        
        # Own posts
        print("Scraping own posts...")
        scrape_data["own_posts"] = await posts_scraper.get_own_posts(username)
        
        # Tagged posts
        print("Scraping tagged posts...")
        scrape_data["tagged_posts"] = await posts_scraper.get_tagged_posts(username)
        
        # User comments on other posts
        print("Scraping user comments...")
        scrape_data["user_comments"] = await posts_scraper.get_user_comments(username)
        
        # Locations
        print("Scraping locations...")
        scrape_data["locations"] = await posts_scraper.get_locations(username)
        
        # Build JSON
        print("Building final JSON output...")
        result = json_builder.build_profile_json(username, scrape_data)
        
        # Cache the result
        scrape_results_cache[username] = result
        
        # Close browser session
        await session.close()
        
        return result["data"]
    
    except Exception as e:
        print(f"Error scraping profile: {str(e)}")
        # Ensure browser is closed in case of error
        try:
            await session.close()
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Error scraping profile: {str(e)}")

@app.get("/download/{username}/json")
async def download_json(username: str):
    """Download the scraped data as a JSON file"""
    # Check if we have cached results or find the latest file
    if username in scrape_results_cache:
        filepath = scrape_results_cache[username]["filepath"]
    else:
        # Try to find the latest file for this username
        pattern = f"{username}_profile_*.json"
        files = list(Path("static/output").glob(pattern))
        if not files:
            raise HTTPException(status_code=404, detail=f"No data found for {username}")
        
        # Sort by creation time (newest first)
        filepath = str(sorted(files, key=lambda x: x.stat().st_ctime, reverse=True)[0])
    
    return FileResponse(
        filepath,
        media_type="application/json",
        filename=f"{username}_facebook_data.json"
    )

@app.get("/pdf/{username}")
async def generate_pdf(username: str):
    """Generate a PDF report of the profile data"""
    try:
        # Check if we have cached results
        if username not in scrape_results_cache:
            # Try to find the latest file for this username
            pattern = f"{username}_profile_*.json"
            files = list(Path("static/output").glob(pattern))
            if not files:
                raise HTTPException(status_code=404, detail=f"No data found for {username}")
            
            # Load the JSON data
            json_file = sorted(files, key=lambda x: x.stat().st_ctime, reverse=True)[0]
            async with aiofiles.open(json_file, "r") as f:
                content = await f.read()
                data = json.loads(content)
        else:
            data = scrape_results_cache[username]["data"]
        
        # Create PDF
        pdf_path = f"static/output/{username}_profile_report.pdf"
        
        # Generate the PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Set title
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, f"Facebook Profile Report: {data['profile']['basic_info']['name']}", ln=True, align="C")
        
        # Basic information
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Basic Information", ln=True)
        pdf.set_font("Arial", "", 12)
        
        basic_info = data["profile"]["basic_info"]
        pdf.cell(0, 10, f"Name: {basic_info['name']}", ln=True)
        if basic_info["bio"]:
            pdf.multi_cell(0, 10, f"Bio: {basic_info['bio']}")
        if basic_info["current_city"]:
            pdf.cell(0, 10, f"Location: {basic_info['current_city']}", ln=True)
        if basic_info["birthday"]:
            pdf.cell(0, 10, f"Birthday: {basic_info['birthday']}", ln=True)
        
        # Work and Education
        if basic_info["work"] or basic_info["education"]:
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Work and Education", ln=True)
            pdf.set_font("Arial", "", 12)
            
            if basic_info["work"]:
                pdf.cell(0, 10, "Work Experience:", ln=True)
                for work in basic_info["work"]:
                    pdf.multi_cell(0, 10, f"- {work}")
            
            if basic_info["education"]:
                pdf.cell(0, 10, "Education:", ln=True)
                for edu in basic_info["education"]:
                    pdf.multi_cell(0, 10, f"- {edu}")
        
        # Stats summary
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Profile Statistics", ln=True)
        pdf.set_font("Arial", "", 12)
        
        friends_count = len(data["profile"]["connections"]["friends"])
        groups_count = len(data["profile"]["connections"]["groups"])
        pages_count = len(data["profile"]["connections"]["pages_followed"])
        posts_count = len(data["profile"]["content"]["own_posts"])
        
        pdf.cell(0, 10, f"Friends: {friends_count}", ln=True)
        pdf.cell(0, 10, f"Groups: {groups_count}", ln=True)
        pdf.cell(0, 10, f"Pages Followed: {pages_count}", ln=True)
        pdf.cell(0, 10, f"Posts: {posts_count}", ln=True)
        
        # Posts summary
        if data["profile"]["content"]["own_posts"]:
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Recent Posts", ln=True)
            
            for i, post in enumerate(data["profile"]["content"]["own_posts"][:5]):  # Limit to 5 posts
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, f"Post {i+1}", ln=True)
                pdf.set_font("Arial", "", 12)
                
                if post["timestamp"]:
                    pdf.cell(0, 10, f"Date: {post['timestamp']}", ln=True)
                
                if post["content"]:
                    pdf.multi_cell(0, 10, f"Content: {post['content'][:200]}...")
                
                if post["comments"]:
                    pdf.cell(0, 10, f"Comments: {len(post['comments'])}", ln=True)
                
                # Add screenshot if available
                if post["screenshot"] and post["screenshot"].startswith("/static"):
                    screenshot_path = post["screenshot"].lstrip("/")
                    if os.path.exists(screenshot_path):
                        try:
                            pdf.image(screenshot_path, x=10, y=None, w=180)
                        except Exception as e:
                            print(f"Error adding image to PDF: {e}")
                
                pdf.cell(0, 10, "", ln=True)  # Add space between posts
        
        # Save the PDF
        pdf.output(pdf_path)
        
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"{username}_facebook_report.pdf"
        )
    
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

# Run the app with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)