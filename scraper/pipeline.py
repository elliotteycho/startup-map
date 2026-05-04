"""Scraper orchestrator. Reads a list of VC sources, scrapes each, upserts
into Supabase.

Run from the scraper/ folder with the venv active:
    python pipeline.py                # scrape all default sources
    python pipeline.py founders       # scrape one preset
    python pipeline.py founders sequoia khosla   # scrape a specific subset

The list of sources lives in SOURCES below. Add more there as you validate them.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv
from supabase import Client, create_client

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extractors.llm import extract_companies
from extractors.yc import BATCH_NAMES as YC_BATCH_NAMES, extract_yc_batch, get_algolia_key

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("pipeline")

# Add sources here as you validate them via smoke_test.py.
# Each entry: (preset_key, url, fund_name).
SOURCES: dict[str, tuple[str, str]] = {
    "founders":   ("https://foundersfund.com/portfolio/", "Founders Fund"),
    "sequoia":    ("https://www.sequoiacap.com/our-companies/", "Sequoia Capital"),
    "khosla":     ("https://www.khoslaventures.com/portfolio", "Khosla Ventures"),
    "greylock":   ("https://greylock.com/portfolio/", "Greylock"),
    "general":    ("https://www.generalcatalyst.com/portfolio/", "General Catalyst"),
    "lightspeed": ("https://lsvp.com/portfolio/", "Lightspeed Venture Partners"),
    # YC: filter to recent batches + currently hiring. These are the
    # intern-friendly companies (small teams, founders responsive).
    "yc_w25":     ("https://www.ycombinator.com/companies?batch=Winter%202025&isHiring=true", "Y Combinator W25"),
    "yc_s24":     ("https://www.ycombinator.com/companies?batch=Summer%202024&isHiring=true", "Y Combinator S24"),
    "yc_w24":     ("https://www.ycombinator.com/companies?batch=Winter%202024&isHiring=true", "Y Combinator W24"),
    # a16z deferred: heavy SPA without standard anchor tags.
}

# Sources that need extra-aggressive scrolling (infinite scroll, lazy load heavy).
HEAVY_SCROLL_SOURCES = {"yc_w25", "yc_s24", "yc_w24"}


def get_supabase() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


def fetch_html(url: str, scroll_iterations: int = 15) -> str:
    from playwright.sync_api import sync_playwright
    logger.info("fetch_start url=%s scrolls=%d", url, scroll_iterations)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ))
        # "domcontentloaded" works for sites that have constant background
        # network activity (ads, analytics) where "networkidle" never fires.
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        # Give JS a moment to render dynamic content.
        time.sleep(3)
        for _ in range(scroll_iterations):
            page.mouse.wheel(0, 5000)
            time.sleep(0.4)
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(1)
        html = page.content()
        browser.close()
        logger.info("fetch_done url=%s chars=%d", url, len(html))
        return html


def upsert_companies(supabase: Client, companies: list, source_fund: str) -> int:
    """Upsert companies into Supabase, keyed on website. Returns rows affected."""
    if not companies:
        logger.info("upsert source=%s skipped reason=no_companies", source_fund)
        return 0
    rows = [c.to_supabase_row() for c in companies]
    response = supabase.table("companies").upsert(
        rows,
        on_conflict="website",
    ).execute()
    affected = len(response.data) if response.data else 0
    logger.info("upsert source=%s affected=%d", source_fund, affected)

    # Upsert founders for any company that has them
    _upsert_founders(supabase, companies, response.data or [])

    return affected


def _upsert_founders(supabase: Client, companies: list, upserted_rows: list) -> None:
    """Upsert founders for companies that returned founder data from the extractor."""
    # Build a name → id map from the upserted rows
    name_to_id: dict[str, int] = {r["name"]: r["id"] for r in upserted_rows if "id" in r}

    founder_rows = []
    for company in companies:
        if not company.founders:
            continue
        company_id = name_to_id.get(company.name)
        if not company_id:
            continue
        for f in company.founders:
            row: dict = {"company_id": company_id, "name": f.name}
            if f.title:       row["title"]        = f.title
            if f.linkedin_url: row["linkedin_url"] = f.linkedin_url
            if f.bio:          row["bio"]          = f.bio
            founder_rows.append(row)

    if not founder_rows:
        return

    try:
        supabase.table("founders").upsert(
            founder_rows,
            on_conflict="company_id,name",
        ).execute()
        logger.info("founders_upserted count=%d", len(founder_rows))
    except Exception as e:
        logger.warning("founders_upsert_failed error=%s", e)


def run_source(supabase: Client, key: str, url: str, fund_name: str, yc_api_key: str | None = None) -> dict:
    """Scrape one source end-to-end. Returns a summary dict for the run report."""
    started = datetime.utcnow()
    summary = {
        "key": key, "fund": fund_name, "url": url,
        "extracted": 0, "upserted": 0, "error": None,
    }
    try:
        if key.startswith("yc_"):
            companies = extract_yc_batch(key, source_fund=fund_name, api_key=yc_api_key)
        else:
            scrolls = 30 if key in HEAVY_SCROLL_SOURCES else 15
            html = fetch_html(url, scroll_iterations=scrolls)
            companies = extract_companies(html, source_fund=fund_name, source_url=url)
        summary["extracted"] = len(companies)
        summary["upserted"] = upsert_companies(supabase, companies, fund_name)
    except Exception as e:
        logger.exception("source_failed source=%s", key)
        summary["error"] = str(e)
    summary["duration_sec"] = (datetime.utcnow() - started).seconds
    return summary


def main() -> None:
    requested = sys.argv[1:] if len(sys.argv) > 1 else list(SOURCES.keys())
    invalid = [k for k in requested if k not in SOURCES]
    if invalid:
        print(f"Unknown sources: {invalid}")
        print(f"Available: {list(SOURCES.keys())}")
        sys.exit(1)

    if not requested:
        print("No sources defined yet. Add entries to SOURCES in pipeline.py.")
        sys.exit(0)

    supabase = get_supabase()

    yc_api_key: str | None = None
    if any(k.startswith("yc_") for k in requested):
        logger.info("fetching_yc_algolia_key")
        yc_api_key = get_algolia_key()
        logger.info("yc_algolia_key_acquired")

    summaries = []
    for key in requested:
        url, fund_name = SOURCES[key]
        summaries.append(run_source(supabase, key, url, fund_name, yc_api_key=yc_api_key))

    print("\n" + "=" * 80)
    print("PIPELINE RUN SUMMARY")
    print("=" * 80)
    for s in summaries:
        status = "ERROR" if s["error"] else "OK"
        print(f"[{status}] {s['fund']:30} extracted={s['extracted']:4} upserted={s['upserted']:4} duration={s['duration_sec']}s")
        if s["error"]:
            print(f"        {s['error']}")
    print("=" * 80)


if __name__ == "__main__":
    main()
