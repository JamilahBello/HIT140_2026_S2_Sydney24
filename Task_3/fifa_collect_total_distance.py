
import asyncio
import json
from playwright.async_api import async_playwright
from pathlib import Path

# FIFA (2026) is the primary data source. The collection method uses Playwright's documented
# page.evaluate() and network capabilities (Microsoft, n.d.-b).

FIFA_URL = ("https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/statistics/player-statistics")

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

    print("Opening FIFA...")
    
    response = await page.goto(FIFA_URL, wait_until="domcontentloaded", timeout=90000)

    print("\nFIFA page status:", response.status)

    # Give FIFA's JS plenty of time
    await page.wait_for_timeout(12000)

    # Get token using FIFA's own token endpoint
    # page.evaluate() runs JS in the webpage context and returns its result to Python (Microsoft, n.d.-a).
    token = await page.evaluate("""
    async () => {
      const response = await fetch("https://cxm-api.fifa.com/fifaplusweb/api/external/gameDay/token");
      const data = await response.json();
      return data.token;
    }
    """)

    print("Token obtained")

    # Manual inspection of the FIFA passing table showed 25 pages at the time of collection.
    # The page number also appeared within the request query (FIFA, 2026; Microsoft, n.d.-c).
    # EncodedURIComponent() was applied because the query contains spaces, colons, 
    # backticks and other characters that must be safely included in a URL (Mozilla, n.d.-a),
    all_pages = []
    for page_number in range (1, 26):
      print(f"Collecting passing page {page_number}...")
      result = await page.evaluate(
        """
        async ({token, pageNumber}) => {
          const query =
            "(and resourceStatus==`urn:gd:resourceStatus:active` " +
            "_externalId~`urn:gd:story:classification:" +
            "gcp_physical:" +
            "competitionId:285023:" +
            "total_distance:" +
            "rank_asc:" +
            "page:" + pageNumber + "$`)";

          const url =
            "https://gameday-prod.fifa.mangodev.co.uk/1-0/stories" +
            "?query=" + encodeURIComponent(query) +
            "&skip=0" +
            "&limit=1" +
            "&sort=" +
            encodeURIComponent(
                "tags.name==urn:gd:tag:story:fifa:column_number:asc"
            );

          const response = await fetch(
              url,
              {
                headers: {
                  "Authorization": "Bearer " + token,
                  "Accept": "application/json, text/plain, */*"
                }
              }
            );

            const text = await response.text();

            return {
                status: response.status,
                url: url,
                text: text
            };
        }
        """,
        {"token": token, "pageNumber": page_number}
      )
      
      print("Status:", result["status"])

      if result["status"] != 200:
        print("Stopped because page", page_number, "returned", result["status"])
        print(result["text"][:500])
        break
        
      data = json.loads(result["text"])

      all_pages.append({"page_number": page_number, "url": result["url"], "data": data})

      # Although manual inspection found 25 pages,
      # Stop early if FIFA returns a page containing no player records
      items = data.get("items", [])
      if not items:
        print("No items returned")
        break
      
  # Save FIFA JSON
  Path("fifa_total_distance_raw.json").write_text(
      json.dumps(all_pages, indent=2, ensure_ascii=False), encoding="utf-8"
  )

  print("\nCOLLECTION COMPLETE")
  print("Pages captured:", len(all_pages))
  print("Saved: fifa_total_distance_raw.json")

  await browser.close()

asyncio.run(main())
