"""Andreessen Horowitz portfolio scraper.

a16z.com/portfolio is JS heavy and uses dynamic loading. We use Playwright to render
the page, scroll to trigger lazy loads, then parse the resulting DOM with BeautifulSoup.

This is the proof of concept source. If this works end to end, the architecture is sound.
"""

from __future__ import annotations

import logging
import time

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from models import Company, InternHiringStatus

logger = logging.getLogger("sources.a16z")

PORTFOLIO_URL = "https://a16z.com/portfolio/"


def _fetch_rendered_html() -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ))
        page.goto(PORTFOLIO_URL, wait_until="networkidle", timeout=60_000)

        # Scroll to trigger any lazy loads.
        for _ in range(8):
            page.mouse.wheel(0, 4000)
            time.sleep(0.5)

        html = page.content()
        browser.close()
        return html


def _parse(html: str) -> list[Company]:
    """Extract company entries. Selectors below are a starting point; verify against
    the live page and update as the site changes."""
    soup = BeautifulSoup(html, "html.parser")
    companies: list[Company] = []

    # a16z portfolio cards typically wrap in <article> or <div class="portfolio-item">.
    # Inspect the live page and adjust as needed.
    for card in soup.select("article, div.portfolio-item, li.portfolio-company"):
        name_el = card.select_one("h2, h3, .company-name, .portfolio-name")
        link_el = card.select_one("a[href]")

        if not name_el or not link_el:
            continue

        name = name_el.get_text(strip=True)
        website = link_el["href"]

        if not name or not website.startswith("http"):
            continue

        companies.append(Company(
            name=name,
            website=website,
            source_fund="Andreessen Horowitz",
            intern_hiring_status=InternHiringStatus.UNKNOWN,
        ))

    logger.info("a16z parsed=%d", len(companies))
    return companies


def scrape() -> list[Company]:
    html = _fetch_rendered_html()
    return _parse(html)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = scrape()
    for c in results[:10]:
        print(f"{c.name}\t{c.website}")
    print(f"\nTotal: {len(results)} companies")
