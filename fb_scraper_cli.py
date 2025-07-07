#!/usr/bin/env python3
"""
Command-line interface for the Facebook Profile Scraper
This script allows you to run the scraper directly from the command line
without needing to start the web server.
"""
import os
import sys
import json
import asyncio
import argparse
from datetime import datetime
import logging

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

async def scrape_profile(username, headless=False, checkpoint_wait=60, output_dir="./output"):
    """
    Scrape a Facebook profile using the command line
    
    Args:
        username: Facebook username to scrape
        headless: Run in headless mode (no visible browser)
        checkpoint_wait: Time to wait (in seconds) if security checkpoint detected
        output_dir: Directory to save output files
    """
    try:
        # Set display for X11 if not headless
        if not headless:
            os.environ["DISPLAY"] = ":1"
        
        # Create user data directory
        user_data_dir = os.path.join(os.path.expanduser("~"), ".facebook_scraper_data")
        os.makedirs(user_data_dir, exist_ok=True)
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        screenshots_dir = os.path.join(output_dir, "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        
        logger.info(f"Initializing Facebook session (headless={headless})...")
        session = FacebookSession(headless=headless, user_data_dir=user_data_dir)
        page = await session.initialize()
        
        # Check login status
        logger.info("Checking login status...")
        is_logged_in = await session.login_check()
        if not is_logged_in:
            logger.info("Login completed successfully")
        else:
            logger.info("Already logged in to Facebook")
        
        # Initialize helper classes
        utils = ScraperUtils(page, screenshot_dir=screenshots_dir)
        profile_scraper = ProfileScraper(page, utils)
        posts_scraper = PostsScraper(page, utils)
        json_builder = JSONBuilder(output_dir=output_dir)
        
        # Set up dialog handlers
        await utils.handle_dialogs()
        
        # Navigate to profile
        logger.info(f"Navigating to profile: {username}")
        logger.info(f"If a security checkpoint appears, you'll have {checkpoint_wait} seconds to solve it")
        profile_exists = await profile_scraper.navigate_to_profile(username)
        
        if not profile_exists:
            logger.error(f"Profile '{username}' not found")
            await session.close()
            return False
        
        # Check for security checkpoint after profile navigation
        checkpoint_detected = await utils.check_for_security_checkpoint()
        if checkpoint_detected:
            logger.warning("Security checkpoint detected! Please solve it manually.")
            await utils.handle_security_checkpoint(wait_time=checkpoint_wait)
        
        # Scrape data
        logger.info("Starting profile data collection...")
        scrape_data = {}
        
        # Basic profile info
        logger.info("Scraping basic info...")
        scrape_data["basic_info"] = await profile_scraper.get_basic_info()
        
        # Friends list
        logger.info("Scraping friends list...")
        scrape_data["friends_list"] = await profile_scraper.get_friends_list()
        
        # Groups
        logger.info("Scraping groups...")
        scrape_data["groups"] = await profile_scraper.get_groups()
        
        # Pages followed
        logger.info("Scraping pages followed...")
        scrape_data["pages_followed"] = await profile_scraper.get_pages_followed()
        
        # Following list
        logger.info("Scraping following list...")
        scrape_data["following_list"] = await profile_scraper.get_following_list()
        
        # Own posts
        logger.info("Scraping own posts...")
        scrape_data["own_posts"] = await posts_scraper.get_own_posts(username)
        
        # Tagged posts
        logger.info("Scraping tagged posts...")
        scrape_data["tagged_posts"] = await posts_scraper.get_tagged_posts(username)
        
        # User comments on other posts
        logger.info("Scraping user comments...")
        scrape_data["user_comments"] = await posts_scraper.get_user_comments(username)
        
        # Locations
        logger.info("Scraping locations...")
        scrape_data["locations"] = await posts_scraper.get_locations(username)
        
        # Build final JSON
        logger.info("Building final JSON output...")
        result = json_builder.build_profile_json(username, scrape_data)
        
        # Save timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        logger.info(f"Scraping completed at {timestamp}")
        logger.info(f"Results saved to: {result['filepath']}")
        
        # Close browser
        await session.close()
        return True
        
    except Exception as e:
        logger.error(f"Error scraping profile: {str(e)}")
        # Ensure browser is closed
        try:
            await session.close()
        except:
            pass
        return False

def main():
    """Main entry point for CLI"""
    parser = argparse.ArgumentParser(description="Facebook Profile Scraper CLI")
    parser.add_argument("username", help="Facebook username to scrape")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (no browser UI)")
    parser.add_argument("--wait", type=int, default=60, help="Time to wait for security checkpoints (seconds)")
    parser.add_argument("--output", type=str, default="./output", help="Output directory for results")
    
    args = parser.parse_args()
    
    # Run the scraper
    print(f"Starting Facebook Profile Scraper for '{args.username}'")
    if os.environ.get("DISPLAY") is None and not args.headless:
        print("WARNING: No display detected. If running on a server, use --headless or set up X11.")
    
    asyncio.run(scrape_profile(args.username, 
                               headless=args.headless, 
                               checkpoint_wait=args.wait,
                               output_dir=args.output))

if __name__ == "__main__":
    main()
