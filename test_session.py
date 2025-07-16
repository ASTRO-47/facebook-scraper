#!/usr/bin/env python3
"""
Test script for Facebook session persistence
This script will:
1. Initialize a Facebook session
2. Check if already logged in
3. If not, wait for manual login
4. Close the session
5. Reopen the session to verify persistence
"""
import os
import asyncio
from scraper.session import FacebookSession
import logging

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('session_test')

async def test_session_persistence():
    # Configure X11 display for remote server
    os.environ["DISPLAY"] = ":1"
    
    # Create user data directory in a location accessible by the current user
    user_data_dir = os.path.join(os.path.expanduser("~"), ".facebook_scraper_data")
    os.makedirs(user_data_dir, exist_ok=True)
    
    # Step 1: First session initialization
    logger.info("STEP 1: Initializing first session")
    session1 = FacebookSession(headless=True, user_data_dir=user_data_dir)
    page = await session1.initialize()
    
    # Step 2: Check login status
    logger.info("STEP 2: Checking login status")
    is_logged_in = await session1.login_check()
    
    if is_logged_in:
        logger.info("Already logged in. Session persistence working!")
    else:
        logger.info("Not logged in. Please login manually when prompted.")
        logger.info("Waiting for manual login to complete...")
        # The login_check method already waits for login completion
        
    # Navigate to profile page to verify access
    logger.info("Navigating to profile page...")
    await page.goto("https://www.facebook.com/me", wait_until="networkidle")
    await asyncio.sleep(3)
    
    # Step 3: Close the first session
    logger.info("STEP 3: Closing first session")
    await session1.close()
    await asyncio.sleep(2)
    
    # Step 4: Create a new session to verify persistence
    logger.info("STEP 4: Creating second session to verify persistence")
    session2 = FacebookSession(headless=True, user_data_dir=user_data_dir)
    page2 = await session2.initialize()
    
    # Step 5: Verify login persisted
    logger.info("STEP 5: Verifying login persistence")
    is_still_logged_in = await session2.login_check()
    
    if is_still_logged_in:
        logger.info("SUCCESS: Session persistence is working correctly!")
        # Navigate to profile page to verify
        await page2.goto("https://www.facebook.com/me", wait_until="networkidle")
        await asyncio.sleep(5)
    else:
        logger.error("FAILED: Session was not persisted between browser restarts")
    
    # Close the second session
    logger.info("Closing second session")
    await session2.close()

if __name__ == "__main__":
    asyncio.run(test_session_persistence())
