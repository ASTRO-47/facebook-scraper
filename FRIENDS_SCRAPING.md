# Friends List Scraping Feature

## Overview

The Facebook Profile Scraper now includes comprehensive friends list scraping functionality. This feature allows you to extract the complete list of friends from any Facebook profile that has a public friends list.

## Features

### 🔍 **Smart Friends Detection**
- Automatically detects if friends list is public or private
- Handles different Facebook URL formats (username, profile ID, full URLs)
- Intelligent scrolling to load more friends dynamically

### 📊 **Comprehensive Data Extraction**
- Friend names and profile URLs
- Bio information when available
- Efficient deduplication to avoid duplicates
- Configurable scroll limits to prevent infinite scrolling

### 🛡️ **Privacy & Safety Features**
- Respects Facebook's privacy settings
- Stops scraping if friends list is private
- Human-like scrolling behavior to avoid detection
- Configurable timeouts and retry logic

## Usage

### Web API

#### Full Profile Scraping (includes friends)
```bash
# Scrape complete profile including friends
curl "http://localhost:8080/scrape/username"

# API endpoint
curl "http://localhost:8080/api/scrape/username"
```

#### Friends-Only Testing
```bash
# Quick test of friends scraping only
curl "http://localhost:8080/quick-test/username"
```

### CLI Usage

```bash
# Full profile scraping with friends
python fb_scraper_cli.py username

# With VNC for visual monitoring
python fb_scraper_cli.py username --vnc

# Non-headless mode
python fb_scraper_cli.py username --no-headless
```

### Test Script

```bash
# Test friends scraping functionality
python test_friends_scraper.py username

# Non-headless testing
python test_friends_scraper.py username --no-headless
```

## Output Format

### JSON Structure
```json
{
  "profile": {
    "name": "User Name",
    "bio": "User bio",
    "friends": [
      {
        "name": "Friend Name",
        "profile_url": "https://www.facebook.com/friend.username",
        "bio": "Friend's bio if available"
      }
    ],
    "groups": [...],
    "pages_followed": [...],
    "following": [...]
  },
  "posts": {...},
  "locations_visited": [...]
}
```

### API Response (Friends-Only Test)
```json
{
  "status": "success",
  "username": "testuser",
  "friends_count": 150,
  "friends": [
    {
      "name": "John Doe",
      "profile_url": "https://www.facebook.com/john.doe",
      "bio": "Software Engineer"
    }
  ],
  "message": "Friends list scraped successfully"
}
```

## Configuration

### Scrolling Parameters

The friends scraping can be configured with these parameters:

```python
# In the ProfileScraper.get_friends_list() method
friends = await profile_scraper.get_friends_list(max_scrolls=20)
```

- `max_scrolls`: Maximum number of scroll operations (default: 20)
- `stable_rounds`: Number of rounds without new friends before stopping (default: 2)
- `max_friends`: Maximum friends to collect before stopping (default: 500)

### Performance Settings

```python
# Timeout settings
navigation_timeout = 60000  # 60 seconds for page navigation
default_timeout = 30000     # 30 seconds for operations
scroll_delay = 1.5         # 1.5 seconds between scrolls
```

## Technical Details

### How It Works

1. **Navigation**: Constructs the friends page URL using the profile identifier
2. **Privacy Check**: Verifies if the friends list is accessible
3. **Scrolling**: Intelligently scrolls to load more friends
4. **Extraction**: Extracts friend data from the current page state
5. **Deduplication**: Removes duplicate friends based on name matching
6. **Stability Check**: Stops when no new friends are found for multiple rounds

### Error Handling

- **Private Friends List**: Returns empty list with warning
- **Navigation Failures**: Retries with alternative URL formats
- **Timeout Errors**: Graceful fallback with partial results
- **Network Issues**: Automatic retry with exponential backoff

### Privacy Considerations

- Only scrapes publicly accessible friends lists
- Respects Facebook's privacy settings
- Stops immediately if access is restricted
- Uses human-like behavior to avoid detection

## Troubleshooting

### Common Issues

1. **No Friends Found**
   - Check if the profile's friends list is public
   - Verify the username/profile ID is correct
   - Try with a different account

2. **Partial Results**
   - Increase `max_scrolls` parameter
   - Check for network connectivity issues
   - Verify login status

3. **Timeout Errors**
   - Reduce `max_scrolls` for faster completion
   - Check internet connection speed
   - Try during off-peak hours

### Debug Mode

Enable detailed logging by setting the log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/scrape/{username}` | GET | Full profile scraping (includes friends) |
| `/api/scrape/{username}` | GET | API version of full scraping |
| `/quick-test/{username}` | GET | Friends-only scraping test |
| `/download/{username}/json` | GET | Download scraped data as JSON |
| `/pdf/{username}` | GET | Generate PDF report |

## Examples

### Basic Usage
```bash
# Scrape a profile including friends
curl "http://localhost:8080/scrape/zuck"

# Test friends scraping only
curl "http://localhost:8080/quick-test/zuck"
```

### Advanced Usage
```python
from scraper.session import FacebookSession
from scraper.profile import ProfileScraper
from scraper.utils import ScraperUtils

# Initialize session
session = FacebookSession(headless=True)
page = await session.initialize()

# Initialize scraper
utils = ScraperUtils(page)
profile_scraper = ProfileScraper(page, utils)

# Navigate and scrape friends
await profile_scraper.navigate_to_profile("username")
friends = await profile_scraper.get_friends_list(max_scrolls=30)

print(f"Found {len(friends)} friends")
```

## Performance Tips

1. **Use Headless Mode**: Faster execution without UI rendering
2. **Limit Scrolls**: Set appropriate `max_scrolls` for your needs
3. **Monitor Progress**: Use VNC mode to watch scraping progress
4. **Batch Processing**: Process multiple profiles sequentially
5. **Caching**: Results are cached for quick re-access

## Security Notes

- Always respect Facebook's Terms of Service
- Use responsibly and ethically
- Don't overload Facebook's servers
- Consider rate limiting for large-scale operations
- Monitor for any changes in Facebook's structure

## Updates

This feature is actively maintained and updated to handle:
- Facebook UI changes
- New privacy settings
- Improved detection algorithms
- Performance optimizations

For the latest updates, check the main README.md file. 