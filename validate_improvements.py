#!/usr/bin/env python3
"""
Validation script to check if all improvements are properly applied
"""

def validate_improvements():
    """Check if all the improvements from the previous prompt are applied correctly"""
    
    improvements_status = {}
    
    # 1. Check if logging level is reduced
    with open('scraper/posts_improved.py', 'r') as f:
        content = f.read()
        
    if 'logging.basicConfig(level=logging.WARNING)' in content:
        improvements_status['reduced_logging'] = True
        print("✅ Reduced logging level - APPLIED")
    else:
        improvements_status['reduced_logging'] = False
        print("❌ Reduced logging level - NOT APPLIED")
    
    # 2. Check if improved content cleaning exists
    if 'Remove repetitive "Facebook" text' in content:
        improvements_status['improved_cleaning'] = True
        print("✅ Improved Facebook content cleaning - APPLIED")
    else:
        improvements_status['improved_cleaning'] = False
        print("❌ Improved Facebook content cleaning - NOT APPLIED")
    
    # 3. Check if smart content extraction exists
    if 'SMART content extraction' in content:
        improvements_status['smart_extraction'] = True
        print("✅ Smart content extraction - APPLIED")
    else:
        improvements_status['smart_extraction'] = False
        print("❌ Smart content extraction - NOT APPLIED")
    
    # 4. Check if simplified timestamp extraction exists
    if 'SIMPLE and reliable timestamp extraction' in content:
        improvements_status['simple_timestamp'] = True
        print("✅ Simple timestamp extraction - APPLIED")
    else:
        improvements_status['simple_timestamp'] = False
        print("❌ Simple timestamp extraction - NOT APPLIED")
    
    # 5. Check if content quality scoring exists
    if '_score_content_quality' in content and 'Score content quality to identify real post content' in content:
        improvements_status['content_scoring'] = True
        print("✅ Content quality scoring - APPLIED")
    else:
        improvements_status['content_scoring'] = False
        print("❌ Content quality scoring - NOT APPLIED")
    
    # 6. Check if validation is simplified
    if 'Enhanced validation for comprehensive posts' in content and 'logger.debug' not in content.split('_is_valid_comprehensive_post')[1].split('def ')[0]:
        improvements_status['simplified_validation'] = True
        print("✅ Simplified validation - APPLIED")
    else:
        improvements_status['simplified_validation'] = False
        print("❌ Simplified validation - NOT APPLIED")
    
    # 7. Check if profile extraction is enabled in main.py
    with open('main.py', 'r') as f:
        main_content = f.read()
    
    if 'scrape_data["profile"] = await safe_scrape(' in main_content and '# scrape_data["profile"]' not in main_content:
        improvements_status['profile_enabled'] = True
        print("✅ Profile extraction enabled - APPLIED")
    else:
        improvements_status['profile_enabled'] = False
        print("❌ Profile extraction enabled - NOT APPLIED")
    
    # 8. Check if headless mode is enabled in main.py
    if 'session = FacebookSession(headless=True' in main_content:
        improvements_status['headless_mode'] = True
        print("✅ Headless mode for performance - APPLIED")
    else:
        improvements_status['headless_mode'] = False
        print("❌ Headless mode for performance - NOT APPLIED")
    
    # 9. Check if post limit is set
    if 'username,\n            20  # Limit to 20 posts for better quality' in main_content:
        improvements_status['post_limit'] = True
        print("✅ Post limit for quality - APPLIED")
    else:
        improvements_status['post_limit'] = False
        print("❌ Post limit for quality - NOT APPLIED")
    
    # Summary
    applied_count = sum(improvements_status.values())
    total_count = len(improvements_status)
    
    print(f"\n📊 SUMMARY: {applied_count}/{total_count} improvements applied")
    
    if applied_count == total_count:
        print("🎉 ALL IMPROVEMENTS SUCCESSFULLY APPLIED!")
        return True
    else:
        print("⚠️  Some improvements are missing or incomplete")
        return False

if __name__ == "__main__":
    validate_improvements()
