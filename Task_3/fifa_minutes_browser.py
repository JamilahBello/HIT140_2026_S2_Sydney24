
import asyncio
import json
from playwright.async_api import async_playwright

# FIFA (2026) is the primary data source. Playwright's documented network events allow
# Python to observe the responses loaded by a dynamic webpage (Microsoft, n.d.-b).

FIFA_URL = ("https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/statistics/player-statistics?group=gcp_top_scorer&stat=total_competition_minutes_played")

async def main():
  async with async_playwright() as p:
    # Playwright's BrowserType.launch() supports the execulable_path,
    # headless and args options used below (Microsoft, n.d.-a).
    
    # Use the Google Chrome installed in Colab,
    # and run it in HEADED mode.
    browser = await p.chromium.launch(
        executable_path="/usr/bin/google-chrome",
        headless=False,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--window-size=1440,1200"]
    )

    context = await browser.new_context(
        viewport={"width": 1440, "height": 1200},
        locale="en-AU"
    )

    page = await context.new_page()

    successful = []
    failed = []

    # Watch real GameDay responses
    # page.on('response', ...) follows Playwright's network-event approach
    # documented by Microsoft (n.d.-b).
    async def response_handler(response):
      if "gameday-prod.fifa.mangodev.co.uk" in response.url:
        print("\nGAMEDAY RESPONSE")
        print("Status:", response.status)
        print("URL:", response.url)

        if response.status == 200:
          successful.append(response.url)

          try:
            data = await response.json()

            if isinstance(data, dict):
              print("JSON keys:", list(data.keys()))

          except Exception as e:
            print("JSON read error:", e)
    
    # Check for failures
    async def failure_handler(request):
      if "gameday-prod.fifa.mangodev.co.uk" in request.url:
        failed.append(request.url)
        print("\nGAMEDAY FAILED")
        print("URL:", request.url)
        print("Reason:", request.failure)

    page.on("response", response_handler)
    page.on("requestfailed", failure_handler)

    print("Opening FIFA...")
    
    response = await page.goto(FIFA_URL, wait_until="domcontentloaded", timeout=90000)

    print("\nFIFA page status:", response.status)

    # Give FIFA's JS plenty of time
    await page.wait_for_timeout(20000)
    
    print("\nSUMMARY")
    print("Successful requests:", len(successful))
    print("Failed requests:", len(failed))

    await browser.close()

asyncio.run(main())
