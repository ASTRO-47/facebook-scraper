#!/usr/bin/env python3
"""
Facebook Security Checkpoint Status Tool

This script checks if security checkpoint handling is properly configured
and provides a quick way to test and configure it.
"""

import os
import sys
import re
import argparse
import asyncio
from scraper.utils import ScraperUtils
from scraper.session import FacebookSession
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('checkpoint_status')

def get_current_wait_time():
    """Get the current security checkpoint wait time from utils.py"""
    utils_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "scraper", "utils.py")
    
    if not os.path.exists(utils_file):
        return None
    
    with open(utils_file, 'r') as f:
        content = f.read()
    
    # Find the wait_time parameter in handle_security_checkpoint method
    pattern = r'async def handle_security_checkpoint\(self, wait_time: int = (\d+)\):'
    match = re.search(pattern, content)
    
    if match:
        return int(match.group(1))
    return None

async def test_checkpoint_detection(url="https://www.facebook.com/checkpoint/"):
    """Test if the security checkpoint detection works by navigating directly to the checkpoint URL"""
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
    
    # Check login status
    logger.info("Checking login status...")
    is_logged_in = await session.login_check()
    
    if is_logged_in:
        logger.info("Successfully logged in")
    else:
        logger.info("Login required. Please log in manually when prompted.")
    
    # Navigate to the specified URL
    logger.info(f"Navigating to URL: {url}")
    await page.goto(url, wait_until="domcontentloaded")
    
    # Wait a moment for page to load
    await asyncio.sleep(2)
    
    # Check for security checkpoint
    logger.info("Checking for security checkpoint indicators...")
    checkpoint_detected = await utils.check_for_security_checkpoint()
    
    # Take a screenshot
    await utils.take_screenshot("checkpoint_test")
    
    if checkpoint_detected:
        logger.info("✅ SECURITY CHECKPOINT DETECTION IS WORKING!")
        logger.info("Security checkpoint detected on the page")
    else:
        logger.info("❌ No security checkpoint detected")
        logger.info("This might mean either:")
        logger.info("1. The detection is not working properly")
        logger.info("2. Facebook is not showing a checkpoint at this URL anymore")
        logger.info("3. You've already solved all checkpoints and Facebook remembers you")
    
    # Wait a moment before closing
    await asyncio.sleep(3)
    
    # Close the session
    await session.close()
    logger.info("Test completed")

def main():
    parser = argparse.ArgumentParser(description="Facebook Security Checkpoint Status Tool")
    parser.add_argument("--test", action="store_true", help="Test checkpoint detection")
    parser.add_argument("--wait", type=int, help="Set new wait time in seconds")
    args = parser.parse_args()
    
    # Get current wait time
    current_wait = get_current_wait_time()
    if current_wait is not None:
        print(f"Current security checkpoint wait time: {current_wait} seconds")
    else:
        print("Could not determine current wait time.")
    
    # Update wait time if requested
    if args.wait is not None:
        from adjust_wait_time import update_wait_time
        update_wait_time(args.wait)
    
    # Run test if requested
    if args.test:
        print("\nRunning security checkpoint detection test...")
        asyncio.run(test_checkpoint_detection())
    
    # If no arguments provided, show help
    if not args.test and args.wait is None:
        parser.print_help()

if __name__ == "__main__":
    main()
