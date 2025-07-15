#!/usr/bin/env python3
"""
Utility script to clear Facebook session data
This can be useful if you're experiencing login issues
"""
import os
import shutil
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('clear_session')

def clear_session_data(force=False):
    """Clear the Facebook session data directory to reset detection flags"""
    # Default user data directory path
    user_data_dir = os.path.join(os.path.expanduser("~"), ".facebook_scraper_data")
    
    if not os.path.exists(user_data_dir):
        logger.info(f"No session data found at {user_data_dir}")
        return
    
    if not force:
        confirm = input(f"This will delete all session data at {user_data_dir}. Continue? (y/n): ")
        if confirm.lower() != 'y':
            logger.info("Operation cancelled.")
            return
    
    try:
        shutil.rmtree(user_data_dir)
        logger.info(f"Successfully cleared session data from {user_data_dir}")
        logger.info("🔄 Session cleared! This may help if Facebook restricted access.")
        logger.info("💡 Wait 10-15 minutes before trying to scrape again.")
        logger.info("🚨 Consider using VPN or different network if restrictions persist.")
    except Exception as e:
        logger.error(f"Error clearing session data: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clear Facebook scraper session data")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()
    
    clear_session_data(force=args.force)
