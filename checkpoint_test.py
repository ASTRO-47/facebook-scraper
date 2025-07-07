#!/usr/bin/env python3
"""
Test script for Facebook security checkpoint with a 2-minute wait
This script will:
1. Initialize a Facebook session
2. Navigate to a Facebook profile
3. If a security checkpoint is detected, wait for 2 minutes
4. Print a success message
"""
import os
import sys
import asyncio
import logging
from scraper.session import FacebookSession
from scraper.utils import ScraperUtils

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('checkpoint_test')

async def test_checkpoint(username):
    # Configure X11 display for remote server
    os.environ["DISPLAY"] = ":1"
    
    # Initialize session
    logger.info(f"Testing security checkpoint detection with 2-minute wait")
    logger.info(f"Target profile: {username}")
    
    # Create user data directory
    user_data_dir = os.path.join(os.path.expanduser("~"), ".facebook_scraper_data")
    os.makedirs(user_data_dir, exist_ok=True)
    
    # Initialize browser
    session = FacebookSession(headless=False, user_data_dir=user_data_dir)
    page = await session.initialize()
    
    try:
        # Initialize utilities
        utils = ScraperUtils(page, screenshot_dir="static/screenshots")
        
        # Check login status first
        logger.info("Checking login status...")
        is_logged_in = await session.login_check()
        
        if is_logged_in:
            logger.info("Login successful. Proceeding to profile...")
        else:
            logger.info("Please complete the login process...")
            await asyncio.sleep(3)
        
        # Navigate to profile
        profile_url = f"https://www.facebook.com/{username}"
        logger.info(f"Navigating to: {profile_url}")
        await page.goto(profile_url, wait_until="domcontentloaded")
        
        # Check for security checkpoint
        logger.info("Checking for security checkpoint...")
        checkpoint_detected = await utils.check_for_security_checkpoint()
        
        if checkpoint_detected:
            logger.warning("SECURITY CHECKPOINT DETECTED!")
            logger.warning("You have 2 minutes to solve the security puzzle...")
            
            # Take a screenshot
            await utils.take_screenshot("security_checkpoint_test")
            
            # Wait for 2 minutes
            await utils.handle_security_checkpoint(wait_time=120)
            
            logger.info("Wait time completed. Checking if we can access the profile...")
            # Check if we can now access the profile
            await page.reload()
            await asyncio.sleep(3)
            
            # Check again for checkpoint
            still_checkpoint = await utils.check_for_security_checkpoint()
            if still_checkpoint:
                logger.error("Still at security checkpoint. You may need more time to solve it.")
            else:
                logger.info("Security checkpoint passed! Profile now accessible.")
        else:
            logger.info("No security checkpoint detected. Profile is accessible.")
        
        # Take a screenshot of the current page
        await utils.take_screenshot(f"{username}_profile_test")
        logger.info(f"Screenshot saved to static/screenshots/{username}_profile_test.png")
        
        # Wait a bit before closing
        await asyncio.sleep(5)
    
    finally:
        # Close browser
        await session.close()
        logger.info("Test completed")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python checkpoint_test.py <username>")
        print("Example: python checkpoint_test.py zuck")
        sys.exit(1)
        
    username = sys.argv[1]
    asyncio.run(test_checkpoint(username))
