# Facebook Scraper API - Curl Usage Guide

## Quick Start

Your server is running at: `http://137.184.150.197:8080`

## API Endpoints for External Clients

### 1. Health Check
```bash
curl http://137.184.150.197:8080/health
```

### 2. Quick Scrape (Friends Only - 2-3 minutes)
```bash
curl http://137.184.150.197:8080/api/quick/imad.zaghba.5 -o friends_data.json
```

### 3. Full Profile Scrape (Complete Data - 10-15 minutes)
```bash
curl http://137.184.150.197:8080/api/scrape/imad.zaghba.5 -o profile_data.json
```

### 4. Full Scrape with Morocco Proxy
```bash
curl 'http://137.184.150.197:8080/api/scrape/imad.zaghba.5?use_morocco_proxy=true' -o profile_data.json
```

## Response Format

### Success Response
```json
{
  "success": true,
  "username": "imad.zaghba.5",
  "scraped_at": "2024-01-15 10:30:45 UTC",
  "data": {
    "profile": {
      "name": "Imad Ezz",
      "bio": "...",
      "work": [],
      "education": []
    },
    "friends": [
      {
        "name": "Friend Name",
        "profile_url": "https://facebook.com/friend",
        "bio": ""
      }
    ],
    "groups": [],
    "posts": {}
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": 404,
    "message": "Profile not found"
  },
  "username": "username",
  "scraped_at": "2024-01-15 10:30:45 UTC"
}
```

## Usage Examples

### Check Server Status
```bash
curl http://137.184.150.197:8080/health
```

### Test with Username
```bash
curl http://137.184.150.197:8080/api/quick/john.doe -o test.json
```

### Test with Profile ID
```bash
curl http://137.184.150.197:8080/api/scrape/profile.php?id=123456789 -o profile.json
```

### Check Results
```bash
# Check if scraping was successful
grep '"success":' profile.json

# View friends count
grep -o '"friends":\[.*\]' profile.json | wc -c
```

## Important Notes

1. **Authentication**: The server uses saved `facebook_cookies.json` from Morocco
2. **Rate Limiting**: Built-in delays prevent Facebook detection
3. **One Request at a Time**: Only run one scraping operation simultaneously
4. **Output Format**: All responses are valid JSON suitable for direct file saving
5. **Headless Mode**: API endpoints run in headless mode by default for speed

## Client Integration Example

```bash
#!/bin/bash
SERVER_IP="137.184.150.197:8080"
USERNAME="$1"

if [ -z "$USERNAME" ]; then
    echo "Usage: $0 <facebook_username>"
    exit 1
fi

echo "🔍 Scraping Facebook profile: $USERNAME"
echo "⏱️ This will take 10-15 minutes..."

curl "http://$SERVER_IP/api/scrape/$USERNAME" \
     -o "${USERNAME}_profile.json" \
     --progress-bar

if grep -q '"success":true' "${USERNAME}_profile.json"; then
    echo "✅ Profile scraped successfully!"
    echo "📄 Data saved to: ${USERNAME}_profile.json"
else
    echo "❌ Scraping failed. Check ${USERNAME}_profile.json for error details"
fi
```

## API Documentation

For complete API documentation:
```bash
curl http://137.184.150.197:8080/api/docs
``` 