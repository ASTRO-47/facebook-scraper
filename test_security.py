#!/usr/bin/env python3
"""
Test script for Facebook security checkpoint detection
"""
import os
import asyncio
from scraper.session import FacebookSession
from scraper.utils import ScraperUtils
import logging

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('security_test')

async def test_security_checkpoint(username):
    # Configure X11 display for remote server
    os.environ["DISPLAY"] = ":1"
    
    # Create user data directory
    user_data_dir = os.path.join(os.path.expanduser("~"), ".facebook_scraper_data")
    os.makedirs(user_data_dir, exist_ok=True)
    
    # Initialize session
    logger.info("Initializing Facebook session...")
    session = FacebookSession(headless=False, user_data_dir=user_data_dir)
    page = await session.initialize()
    
    # Create utility instance
    utils = ScraperUtils(page)
    
    # Check login status and handle security checkpoint
    logger.info("Checking login status...")
    is_logged_in = await session.login_check()
    
    if is_logged_in:
        logger.info("Successfully logged in")
    else:
        logger.info("Login required. Please log in manually when prompted.")
    
    # Navigate to the requested profile
    logger.info(f"Navigating to profile: {username}")
    await page.goto(f"https://www.facebook.com/{username}", wait_until="domcontentloaded")
    
    # Check for security checkpoint
    checkpoint_detected = await utils.check_for_security_checkpoint()
    
    if checkpoint_detected:
        logger.warning("Security checkpoint detected! Waiting for 2 minutes so you can solve it manually...")
        await utils.handle_security_checkpoint(wait_time=120)
        logger.info("Continuing after checkpoint...")
    else:
        logger.info("No security checkpoint detected")
    
    # Screenshot the profile page
    await utils.take_screenshot("profile_page")
    
    # Wait a bit before closing
    logger.info("Taking screenshot of the page")
    await asyncio.sleep(5)
    
    # Close the session
    await session.close()
    logger.info("Test completed")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python test_security.py <username>")
        print("Example: python test_security.py zuck")
        sys.exit(1)
    
    username = sys.argv[1]
    asyncio.run(test_security_checkpoint(username))
