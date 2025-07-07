# Facebook Profile Scraper

A tool to scrape Facebook profiles using Playwright and FastAPI. This scraper extracts structured data from Facebook profiles including personal information, posts, friends, groups, and more.

## Features

- **Profile Information**: Extract basic profile details (name, bio, work history, education, location, contact details)
- **Social Connections**: Scrape friends list, followed pages, groups, and following list
- **Content Analysis**: Extract user posts, tagged posts, comments made, and locations visited
- **Media Capture**: Take screenshots of profile elements and posts
- **Structured Output**: Generate well-structured JSON output of all scraped data
- **PDF Reports**: Generate PDF reports with key profile information and post screenshots
- **Web Interface**: Simple UI for entering usernames and viewing results
- **API Access**: FastAPI endpoints for programmatic access
- **Session Persistence**: Maintains login sessions between runs to avoid repeated logins

## Prerequisites

- Python 3.8+
- Playwright
- FastAPI
- Other dependencies as listed in requirements.txt

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd facebook_scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
playwright install
```

## Usage

### Web Interface

1. Start the FastAPI server:
```bash
python main.py
```

2. Open your browser and navigate to `http://localhost:8080`

3. Enter a Facebook username to scrape

4. The first time you run the scraper, it will open a browser window where you need to manually log in to Facebook. The login session will be saved for future use.

5. View and download the scraped data in JSON format or as a PDF report

### Command Line Interface

A command-line interface is available for direct scraping without starting the web server:

```bash
# Basic usage
./fb_scraper_cli.py zuck

# With options
./fb_scraper_cli.py zuck --wait 120 --output ./my_results

# Run in headless mode (no visible browser)
./fb_scraper_cli.py zuck --headless
```

Command-line options:
- `--headless`: Run without showing the browser window
- `--wait`: Time to wait (in seconds) if a security checkpoint is detected
- `--output`: Directory to save results

## API Endpoints

- `GET /`: Web interface for the scraper
- `GET /scrape/{username}`: Scrape a Facebook profile and return JSON data
- `GET /download/{username}/json`: Download scraped data as a JSON file
- `GET /pdf/{username}`: Generate and download a PDF report
- `GET /health`: Health check endpoint

## Project Structure

```
/facebook_scraper
├── main.py              # FastAPI app with endpoints
├── scraper/
│   ├── __init__.py
│   ├── session.py       # Loads and saves Playwright session
│   ├── profile.py       # Functions to scrape bio, about, etc.
│   ├── posts.py         # Functions to scrape own/tagged posts
│   ├── utils.py         # Screenshot, scroll, helpers
│   └── json_builder.py  # Formats final output JSON
├── static/
│   ├── screenshots/     # Stored screenshots
│   └── output/          # JSON and PDF outputs
├── templates/
│   └── index.html       # Minimal UI for input + preview
├── requirements.txt
└── README.md
```

## Privacy and Ethical Considerations

- This tool should only be used to scrape profiles of friends or those who have given permission.
- Respect Facebook's terms of service and rate limits.
- Do not use for mass scraping or spamming.
- Be mindful of privacy concerns when handling scraped data.

## Limitations

- Facebook's anti-scraping measures may affect functionality.
- Changes to Facebook's HTML structure may require updates to selectors.
- Some content may not be accessible depending on privacy settings.
- Requires manual login to Facebook.

## Running on a Headless Server (like Digital Ocean)

If you're running on a server without a display:

### Option 1: Use Headless Mode (Default)
The application now runs in headless mode by default, so it should work on any server.

### Option 2: Use xvfb (for visible browser debugging)
If you need to see the browser for debugging purposes:

1. Install xvfb:
```bash
apt-get update && apt-get install -y xvfb
```

2. Install PyVirtualDisplay:
```bash
pip install PyVirtualDisplay
```

3. Run the application with xvfb:
```bash
xvfb-run python3 main.py
```

## Session Management

The scraper now includes improved session persistence to avoid repeated logins. Here's how it works:

### Security Checkpoint Handling

The scraper automatically detects Facebook security checkpoints and CAPTCHAs and pauses for 2 minutes to allow you to solve them manually. Security checkpoints typically appear:

1. When accessing Facebook from a new device/location
2. After suspicious activity
3. When automation is detected

Once you solve a checkpoint manually, Facebook usually remembers your browser for future sessions, and you won't need to solve it again.

#### Adjusting Checkpoint Wait Time

After you've successfully solved a security checkpoint once, Facebook typically won't show it again. You can adjust or disable the wait time using the provided script:

```bash
# To reduce wait time to 30 seconds
python adjust_wait_time.py 30

# To disable wait time completely (once you're confident checkpoints won't appear)
python adjust_wait_time.py 0
```

#### Testing Security Checkpoint Detection

You can test the security checkpoint detection feature using the test script:

```bash
python test_security.py <username>
# Example: python test_security.py zuck
```

This will:
1. Open Facebook in a browser
2. Navigate to the specified profile
3. Check for security checkpoints
4. If a checkpoint is found, wait for you to solve it manually
5. Take a screenshot of the profile page

### How Session Persistence Works

1. **Persistent Browser Context**: The scraper uses Playwright's persistent context feature to maintain cookies, local storage, and other session data between runs.

2. **User Data Directory**: Session data is stored in a dedicated directory (`~/.facebook_scraper_data` by default) that persists between application runs.

3. **Improved Login Detection**: The scraper uses multiple methods to detect whether a user is logged in or not, making the login process more reliable.

### Testing Session Persistence

To test that session persistence is working correctly, you can run the test script:

```bash
python test_session.py
```

This script will:
1. Initialize a browser session
2. Check if you're already logged in
3. If not, prompt for manual login
4. Close the browser
5. Open a new browser session to verify that the login persisted

### Troubleshooting Session Issues

If you experience issues with session persistence:

1. **Clear Session Data**: Remove the user data directory to start fresh
   ```bash
   rm -rf ~/.facebook_scraper_data
   ```

2. **Verify Permissions**: Ensure the application has write permissions to the user data directory

3. **Check for Facebook Security Challenges**: Sometimes Facebook may require additional verification, which can interrupt automated sessions

## License

[MIT License](LICENSE)

## Disclaimer

This project is for educational purposes only. The developers are not responsible for any misuse of this software or violations of Facebook's terms of service.