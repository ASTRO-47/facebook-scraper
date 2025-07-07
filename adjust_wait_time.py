#!/usr/bin/env python3
"""
Utility script to adjust security checkpoint wait time

This script updates the default wait time for security checkpoints in utils.py.
Once you've successfully solved a Facebook security checkpoint once, you can 
reduce or disable the wait time since Facebook usually remembers your browser.
"""
import os
import re
import argparse

def update_wait_time(new_wait_time):
    utils_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                             "scraper", "utils.py")
    
    if not os.path.exists(utils_file):
        print(f"Error: Could not find utils.py at {utils_file}")
        return False
    
    with open(utils_file, 'r') as f:
        content = f.read()
    
    # Find and replace the wait_time parameter in handle_security_checkpoint method
    pattern = r'(async def handle_security_checkpoint\(self, wait_time: int = )(\d+)(\):)'
    match = re.search(pattern, content)
    
    if not match:
        print("Could not find the wait_time parameter in handle_security_checkpoint method.")
        return False
    
    current_wait_time = int(match.group(2))
    replacement = f'\\1{new_wait_time}\\3'
    
    new_content = re.sub(pattern, replacement, content)
    
    with open(utils_file, 'w') as f:
        f.write(new_content)
    
    print(f"✅ Security checkpoint wait time updated")
    print(f"   - Previous setting: {current_wait_time} seconds")
    print(f"   - New setting: {new_wait_time} seconds")
    
    if new_wait_time == 0:
        print("\n⚠️ Security checkpoint waiting is now DISABLED.")
        print("   If Facebook shows a security puzzle, you'll need to solve it quickly")
        print("   before the scraper continues.")
    elif new_wait_time < 30:
        print(f"\n⚠️ Warning: Wait time of {new_wait_time} seconds may not be enough")
        print("   to solve complex security puzzles.")
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adjust security checkpoint wait time")
    parser.add_argument("wait_time", type=int, help="New wait time in seconds (0 to disable waiting)")
    args = parser.parse_args()
    
    if args.wait_time < 0:
        print("Error: Wait time cannot be negative.")
        exit(1)
    
    if args.wait_time == 0:
        print("\n⚠️ You are about to DISABLE security checkpoint waiting.")
        confirm = input("Are you sure you want to continue? (y/n): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            exit(0)
    
    update_wait_time(args.wait_time)
