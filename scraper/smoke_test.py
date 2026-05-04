"""End-to-end smoke test for the scraper pipeline.

Usage:
    python smoke_test.py                       # default: Founders Fund
    python smoke_test.py sequoia               # preset target
    python smoke_test.py "https://example.com/portfolio" "Example VC"

Saves rendered HTML to /tmp/<slug>_portfolio.html for inspection.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from urllib.parse import urlparse

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extractors.llm import extract_companies

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("smoke_test")

# Pre-canned targets known to be relatively scrape-friendly.
PRESETS = {
    "founders": ("https://foundersfund.com/portfolio/", "Founders Fund"),
    "sequoia": ("https://www.sequoiacap.com/our-companies/", "Sequoia Capital"),
    "khosla": ("https://www.khoslaventures.com/portfolio", "Khosla Ventures"),
    "greylock": ("https://greylock.com/portfolio/", "Greylock"),
    "lightspeed": ("https://lsvp.com/portfolio/", "Lightspeed Venture Partners"),
    "general": ("https://www.generalcatalyst.com/portfolio/", "General Catalyst"),
    "a16z": ("https://a16z.com/portfolio/", "Andreessen Horowitz"),
}


def parse_args() -> tuple[str, str]:
    """Decide which URL and source fund label to use."""
    if len(sys.argv) == 1:
        return PRESETS["founders"]
    arg = sys.argv[1]
    if arg in PRESETS:
        return PRESETS[arg]
    if arg.startswith("http"):
        label = sys.argv[2] if len(sys.argv) > 2 else urlparse(arg).netloc
        return arg, label
    print(f"Unknown preset: {arg}")
    print("Available presets:", ", ".join(PRESETS.keys()))
    print("Or pass a full URL: python smoke_test.py https://example.com/portfolio 'Example VC'")
    sys.exit(1)


def fetch_html(url: str) -> str:
    """Render the page with Chromium, scroll for lazy loads, return HTML."""
    logger.info("Fetching %s", url)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ))
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)

        for _ in range(15):
            page.mouse.wheel(0, 5000)
            time.sleep(0.4)

        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(1)

        html = page.content()
        browser.close()
        logger.info("Fetched %d chars of HTML", len(html))
        return html


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY is empty in .env")
        sys.exit(1)
    if not os.environ.get("SUPABASE_URL"):
        logger.error("SUPABASE_URL is empty in .env")
        sys.exit(1)

    url, label = parse_args()
    slug = urlparse(url).netloc.replace(".", "_")
    debug_path = f"/tmp/{slug}_portfolio.html"

    logger.info("target=%s fund=%s", url, label)
    html = fetch_html(url)

    with open(debug_path, "w") as f:
        f.write(html)
    logger.info("Saved rendered HTML to %s", debug_path)

    companies = extract_companies(html, source_fund=label, source_url=url)

    if not companies:
        logger.warning("No companies extracted.")
        logger.warning("Inspect %s to see what Playwright actually rendered.", debug_path)
        sys.exit(2)

    print(f"\nExtracted {len(companies)} companies from {label}.")
    print("\nFirst 15:")
    print("-" * 80)
    for i, c in enumerate(companies[:15], 1):
        sector = c.sector or "—"
        pitch = c.one_line_pitch or "—"
        print(f"{i:2}. {c.name:30} {sector:15} {c.website}")
        if pitch != "—":
            print(f"    {pitch[:100]}")
    print("-" * 80)
    print(f"\nIf this looks right, the scraper pipeline works end-to-end.")


if __name__ == "__main__":
    main()
