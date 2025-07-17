# Facebook Profile Scraper

A tool to scrape Facebook profiles using Playwright and FastAPI with SSH X11 forwarding for secure remote browser access.

## Features

- **Profile Information**: Extract basic profile details (name, bio, work history, education, location, contact details)
- **Friends List Scraping**: Comprehensive friends list extraction with intelligent scrolling and privacy detection
- **Social Connections**: Scrape friends list, followed pages, groups, and following list
- **Content Analysis**: Extract user posts, tagged posts, comments made, and locations visited
- **Media Capture**: Take screenshots of profile elements and posts
- **Structured Output**: Generate well-structured JSON output of all scraped data
- **PDF Reports**: Generate PDF reports with key profile information and post screenshots
- **Web Interface**: Simple UI for entering usernames and viewing results
- **API Access**: FastAPI endpoints for programmatic access
- **Session Persistence**: Maintains login sessions between runs to avoid repeated logins
- **SSH X11 Forwarding**: Display browser on local machine through secure SSH connection
- **International Account Support**: Enhanced support for accounts from different countries

## Prerequisites

- Python 3.8+
- Playwright
- FastAPI
- SSH access with X11 forwarding enabled
- X11 server on local machine (Linux native, macOS with XQuartz, Windows with VcXsrv)

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
playwright install chromium
```

4. Enable X11 forwarding on your server:
```bash
sudo nano /etc/ssh/sshd_config
# Ensure: X11Forwarding yes
sudo systemctl restart sshd
```

## Usage

### Method 1: SSH X11 Forwarding (Recommended)

This method displays the browser directly on your local machine through SSH.

#### Step 1: Connect with X11 Forwarding

```bash
# Basic X11 forwarding
ssh -X user@your-server-ip

# For better performance (trusted)
ssh -Y user@your-server-ip

# With compression for slow connections
ssh -XC user@your-server-ip
```

#### Step 2: Test X11 Forwarding

```bash
# Test that X11 forwarding works
xclock
# A clock should appear on your local machine
```

#### Step 3: Manual Facebook Login

```bash
python3 login_manual.py
```

This will:
- Open Facebook in a browser **on your local machine**
- Allow you to login manually and complete security verifications
- Save your session for future automated scraping
- Press Ctrl+C when login is complete

#### Step 4: Start the Scraper

```bash
python3 main.py
```

Navigate to `http://localhost:8080` in your local browser to use the web interface.

### Method 2: Web Interface

1. Start the FastAPI server:
```bash
python main.py
```

2. Open your browser and navigate to `http://localhost:8080`

3. Enter a Facebook username to scrape

4. If this is your first time, the browser will open for manual login (via X11 forwarding)

5. View and download the scraped data in JSON format or as a PDF report

### Method 3: Command Line Interface

A command-line interface is available for direct scraping:

```bash
# Basic usage (includes friends list)
./fb_scraper_cli.py username

# With options
./fb_scraper_cli.py username --wait 120 --output ./my_results

# Run in headless mode (requires existing login session)
./fb_scraper_cli.py username --headless

# Test friends scraping only
python test_friends_scraper.py username
```

## International Account Support

The scraper includes enhanced support for international accounts (e.g., Moroccan accounts accessing from US servers):

### Features:
- **Multi-domain login attempts**: Tries different Facebook regional domains
- **Extended security timeouts**: More time for location verification
- **Language support**: Handles Arabic and French security prompts
- **Location verification guidance**: Helps with "This Was Me" prompts

### Tips for International Accounts:
- Choose "This Was Me" for location verification prompts
- Complete phone/email verification when requested
- Use real information for any ID verification
- Be patient with the verification process (can take 5-10 minutes)

## API Endpoints

- `GET /`: Web interface for the scraper
- `GET /scrape/{username}`: Scrape a Facebook profile and return JSON data (includes friends)
- `GET /api/scrape/{username}`: API version of full profile scraping
- `GET /quick-test/{username}`: Test friends list scraping only
- `GET /download/{username}/json`: Download scraped data as a JSON file
- `GET /pdf/{username}`: Generate and download a PDF report
- `GET /health`: Health check endpoint

## Project Structure

```
/facebook_scraper
├── main.py              # FastAPI app with endpoints
├── login_manual.py      # Manual login setup with X11 forwarding
├── fb_scraper_cli.py    # Command-line interface
├── scraper/
│   ├── __init__.py
│   ├── session.py       # Browser session management with X11 support
│   ├── profile.py       # Profile data extraction
│   ├── posts.py         # Posts and content extraction
│   ├── utils.py         # Utilities and human-like behavior
│   └── json_builder.py  # Output formatting
├── static/
│   ├── screenshots/     # Stored screenshots
│   └── output/          # JSON and PDF outputs
├── templates/
│   └── index.html       # Web interface
├── requirements.txt
├── README.md
└── README_SSH_X11.md    # Detailed X11 forwarding setup guide
```

## Platform-Specific Setup

### Linux
X11 should work out of the box. Just connect with `ssh -X`.

### macOS
Install XQuartz:
```bash
brew install --cask xquartz
# Log out and log back in after installation
```

### Windows
Install an X11 server like VcXsrv:
1. Download from https://sourceforge.net/projects/vcxsrv/
2. Start VcXsrv with default settings
3. Enable "Disable access control"
4. Use SSH client with X11 forwarding support

## Troubleshooting

### X11 Forwarding Issues

```bash
# Check DISPLAY variable
echo $DISPLAY
# Should show something like: localhost:10.0

# Test X11 connection
xset q

# Install X11 tools if missing
sudo apt install x11-utils xauth
```

### Browser Launch Issues

```bash
# Install Playwright browsers
playwright install chromium

# Check Playwright installation
python -c "from playwright.sync_api import sync_playwright; print('OK')"
```

### Session Persistence Issues

```bash
# Clear session data to start fresh
rm -rf ~/.facebook_scraper_data

# Check permissions
ls -la ~/.facebook_scraper_data/
```

## Privacy and Ethical Considerations

- This tool should only be used to scrape profiles of friends or those who have given permission
- Respect Facebook's terms of service and rate limits
- Do not use for mass scraping or spamming
- Be mindful of privacy concerns when handling scraped data

## Limitations

- Facebook's anti-scraping measures may affect functionality
- Changes to Facebook's HTML structure may require updates to selectors
- Some content may not be accessible depending on privacy settings
- Requires manual login to Facebook via X11 forwarding

## Session Management

The scraper includes improved session persistence to avoid repeated logins:

### Security Checkpoint Handling

The scraper automatically detects Facebook security checkpoints and provides guidance for international accounts. Security checkpoints typically appear:

1. When accessing Facebook from a new device/location
2. After suspicious activity
3. When automation is detected

### How Session Persistence Works

1. **Persistent Browser Context**: Uses Playwright's persistent context to maintain cookies and session data
2. **User Data Directory**: Session data stored in `~/.facebook_scraper_data`
3. **X11 Integration**: Browser displays on local machine for natural interaction

### Testing Session Persistence

```bash
# Test the setup
python3 test_session.py

# Test international login features
python3 test_international_login.py
```

## Performance Tips

- Use trusted X11 forwarding for better performance: `ssh -Y`
- Enable SSH compression for slow connections: `ssh -XC`
- Use screen/tmux for long-running scrapers
- Monitor resource usage during scraping

## License

[MIT License](LICENSE)

## Disclaimer

This project is for educational purposes only. The developers are not responsible for any misuse of this software or violations of Facebook's terms of service.