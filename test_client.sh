#!/bin/bash

# Facebook Scraper API Client Test Script
# Usage: ./test_client.sh [username]

SERVER_IP="137.184.150.197"
PORT="8080"
USERNAME="${1:-imad.zaghba.5}"  # Default to test username if not provided

echo "🔧 Facebook Scraper API Client Test"
echo "=================================="
echo "Server: http://$SERVER_IP:$PORT"
echo "Username: $USERNAME"
echo ""

# Test 1: Health Check
echo "1️⃣ Testing Health Check..."
echo "Command: curl http://$SERVER_IP:$PORT/health"
echo ""
curl -s "http://$SERVER_IP:$PORT/health" > health_check.json
if [ $? -eq 0 ]; then
    echo "✅ Health check successful"
    echo "📄 Response saved to: health_check.json"
    
    # Extract key info
    if command -v python3 &> /dev/null; then
        echo "📊 Status: $(python3 -c "import json; print(json.load(open('health_check.json'))['status'])")"
        echo "🍪 Cookies available: $(python3 -c "import json; print(json.load(open('health_check.json'))['cookies_available'])")"
    fi
else
    echo "❌ Health check failed"
    exit 1
fi
echo ""

# Test 2: Quick Scrape (Friends Only)
echo "2️⃣ Testing Quick Scrape (Friends Only)..."
echo "Command: curl http://$SERVER_IP:$PORT/api/quick/$USERNAME -o quick_test.json"
echo "⏱️ This will take 2-3 minutes..."
echo ""

curl "http://$SERVER_IP:$PORT/api/quick/$USERNAME" \
     -o "quick_test.json" \
     --progress-bar

if [ $? -eq 0 ]; then
    if grep -q '"success":true' quick_test.json; then
        echo "✅ Quick scrape successful"
        echo "📄 Response saved to: quick_test.json"
        
        # Extract key info
        if command -v python3 &> /dev/null; then
            echo "👥 Friends found: $(python3 -c "import json; data=json.load(open('quick_test.json')); print(data['data']['friends_count'])")"
            echo "📋 Sample friends: $(python3 -c "import json; data=json.load(open('quick_test.json')); print(len(data['data']['sample_friends']))")"
        fi
    else
        echo "❌ Quick scrape failed"
        echo "📄 Check quick_test.json for error details"
    fi
else
    echo "❌ Quick scrape request failed"
fi
echo ""

# Test 3: Optional Full Scrape (commented out by default)
echo "3️⃣ Full Scrape Test (Optional)"
echo "To test full scrape (10-15 minutes), run:"
echo "curl http://$SERVER_IP:$PORT/api/scrape/$USERNAME -o full_profile.json"
echo ""

# Test 4: Show Usage Examples
echo "4️⃣ Usage Examples for Your Clients"
echo "=================================="
echo ""
echo "Health Check:"
echo "curl http://$SERVER_IP:$PORT/health"
echo ""
echo "Quick Scrape (Friends Only):"
echo "curl http://$SERVER_IP:$PORT/api/quick/username -o friends.json"
echo ""
echo "Full Profile Scrape:"
echo "curl http://$SERVER_IP:$PORT/api/scrape/username -o profile.json"
echo ""
echo "With Morocco Proxy:"
echo "curl 'http://$SERVER_IP:$PORT/api/scrape/username?use_morocco_proxy=true' -o profile.json"
echo ""

# Test 5: Show File Outputs
echo "5️⃣ Generated Files"
echo "=================="
echo "📄 health_check.json - Server health status"
echo "📄 quick_test.json - Quick scrape results (friends only)"
echo ""
echo "To view results:"
echo "cat quick_test.json | grep '\"success\"'"
echo "cat quick_test.json | grep '\"friends_count\"'"
echo ""

echo "🎉 API Client Test Complete!"
echo ""
echo "📚 For complete documentation:"
echo "curl http://$SERVER_IP:$PORT/api/docs" 