import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto('https://www.facebook.com/srikanth767', timeout=60000)
        await asyncio.sleep(10)  # Wait for content to load
        html = await page.content()
        with open('fb_profile_sample.html', 'w') as f:
            f.write(html)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main()) 