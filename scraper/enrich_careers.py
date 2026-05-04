"""
Careers page enrichment. For each company with intern_hiring_status=unknown,
visit the careers page, search for intern/internship mentions, and update Supabase.

Also discovers and sets careers_page_url for companies that don't have one.

Run from scraper/ with venv active:
    python enrich_careers.py               # all unknowns
    python enrich_careers.py --limit 50    # process at most N
    python enrich_careers.py --source "Founders Fund"  # one source fund

Will not re-process companies already set to hiring/not_hiring/open_to unless
you pass --recheck.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import time
from urllib.parse import urljoin, urlparse

from dotenv import load_dotenv
from playwright.sync_api import Page, sync_playwright
from supabase import Client, create_client

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("enrich_careers")

# Keywords that indicate an active internship listing.
INTERN_KEYWORDS = re.compile(
    r"\b(intern(?:ship)?s?|co-op|coop)\b",
    re.IGNORECASE,
)

# Common careers-page path candidates, tried in order.
CAREERS_PATHS = [
    "/careers",
    "/jobs",
    "/work-with-us",
    "/join-us",
    "/join",
    "/hiring",
    "/openings",
    "/team",
    "/about/careers",
    "/about/jobs",
    "/company/careers",
    "/company/jobs",
]

# If the page text length is shorter than this, treat it as empty/broken.
MIN_PAGE_TEXT_LEN = 200

# Pause between requests (seconds) to be polite to startup websites.
REQUEST_DELAY = 1.0

# VC portfolio page domains whose URLs are NOT the company's own website.
# When we encounter these as the stored `website`, we must resolve the real URL first.
VC_INTERNAL_DOMAINS = {
    "foundersfund.com",
    "sequoiacap.com",
    "generalcatalyst.com",
    "lsvp.com",
    "lightspeedvp.com",
    "khoslaventures.com",
    "greylock.com",
}


def get_supabase() -> Client:
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


def _page_text(page: Page) -> str:
    """Return visible text from a rendered page, stripped of noise."""
    try:
        return page.inner_text("body") or ""
    except Exception:
        return page.content()


def _origin(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def _find_careers_link_in_page(page: Page, base_url: str) -> str | None:
    """
    Scan the current page's anchor tags for a careers/jobs link.
    Returns the absolute URL of the best match, or None.
    """
    try:
        links = page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => ({href: e.href, text: e.textContent}))",
        )
    except Exception:
        return None

    careers_pattern = re.compile(
        r"(careers?|jobs?|hiring|work.with|join.us|openings?)",
        re.IGNORECASE,
    )
    origin = _origin(base_url)
    for link in links:
        href = link.get("href", "")
        text = link.get("text", "")
        if careers_pattern.search(href) or careers_pattern.search(text):
            # Prefer same-origin links.
            if href.startswith(origin) or href.startswith("/"):
                return urljoin(base_url, href)
    return None


def _try_common_paths(page: Page, website: str) -> str | None:
    """
    Try common careers paths until we get a page with real content.
    Returns the URL of the first path that loads successfully.
    """
    origin = _origin(website)
    for path in CAREERS_PATHS:
        url = origin + path
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=20_000)
            if resp and resp.ok:
                text = _page_text(page)
                if len(text) >= MIN_PAGE_TEXT_LEN:
                    return url
        except Exception:
            pass
        time.sleep(0.3)
    return None


def _is_vc_internal(url: str) -> bool:
    host = urlparse(url).netloc.lower().lstrip("www.")
    return any(host == d or host.endswith("." + d) for d in VC_INTERNAL_DOMAINS)


_SKIP_DOMAINS_RESOLVE = {
    "twitter.com", "x.com", "linkedin.com", "facebook.com", "instagram.com",
    "youtube.com", "github.com", "medium.com", "crunchbase.com",
    "wikipedia.org", "tumblr.com", "techcrunch.com", "forbes.com",
    "wsj.com", "bloomberg.com", "nytimes.com", "wired.com",
    "reuters.com", "businessinsider.com", "fortune.com",
    "podcasts.apple.com", "open.spotify.com", "spotify.com",
}
# Link text patterns that clearly point to the company website (not blog/team/etc).
_WEBSITE_LINK_RE = re.compile(r"\b(website|visit|company site|homepage|home page)\b", re.I)
# Media file extensions to skip.
_MEDIA_EXT_RE = re.compile(r"\.(jpg|jpeg|png|gif|svg|webp|mp4|mp3|pdf)(\?|$)", re.I)


def _company_slug(name: str) -> str:
    """Convert company name to a simple slug for domain matching."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def resolve_vc_website(page: Page, vc_page_url: str, company_name: str = "") -> str | None:
    """
    Visit a VC portfolio detail page and return the company's real website.
    Scores candidates by how well they match the company name and URL cleanliness.
    """
    try:
        resp = page.goto(vc_page_url, wait_until="domcontentloaded", timeout=25_000)
        time.sleep(1)
        if not resp or not resp.ok:
            return None
    except Exception as e:
        logger.debug("vc_page_failed url=%s err=%s", vc_page_url, e)
        return None

    vc_host = urlparse(vc_page_url).netloc.lower().lstrip("www.")
    skip_domains = _SKIP_DOMAINS_RESOLVE | {vc_host}

    try:
        links = page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => ({href: e.href, text: e.textContent.trim()}))",
        )
    except Exception:
        return None

    slug = _company_slug(company_name)
    best: tuple[int, str] = (-1, "")

    for link in links:
        href: str = link.get("href", "")
        text: str = link.get("text", "")
        if not href.startswith("http"):
            continue
        if _MEDIA_EXT_RE.search(href):
            continue
        parsed = urlparse(href)
        host = parsed.netloc.lower().lstrip("www.")
        if not host:
            continue
        if any(host == d or host.endswith("." + d) for d in skip_domains):
            continue

        score = 0
        # Heavily prefer domain that contains the company slug.
        if slug and slug in host.replace(".", "").replace("-", ""):
            score += 10
        # Prefer explicit "website" link text.
        if _WEBSITE_LINK_RE.search(text):
            score += 5
        # Prefer clean root-level URLs (no long paths).
        path_depth = len([p for p in parsed.path.split("/") if p])
        score -= path_depth
        # Prefer https.
        if href.startswith("https"):
            score += 1

        if score > best[0]:
            best = (score, href)

    if best[1]:
        logger.info("resolved_website vc_page=%s -> company=%s (score=%d)", vc_page_url, best[1], best[0])
        return best[1]
    return None


def fetch_careers_page(page: Page, company: dict) -> tuple[str | None, str]:
    """
    Locate and return (careers_url, page_text) for a company.
    Falls back through: existing url → link in homepage → common paths.
    Returns (None, "") if nothing usable is found.
    """
    existing_url: str | None = company.get("careers_page_url")
    website: str = company.get("website", "")

    # 1. Try existing careers URL if we have one — but skip YC company pages,
    #    which list full-time roles only and never mention internships.
    if existing_url and "ycombinator.com" not in existing_url:
        try:
            resp = page.goto(existing_url, wait_until="domcontentloaded", timeout=25_000)
            if resp and resp.ok:
                text = _page_text(page)
                if len(text) >= MIN_PAGE_TEXT_LEN:
                    return existing_url, text
        except Exception as e:
            logger.debug("existing_url_failed url=%s err=%s", existing_url, e)

    if not website:
        return None, ""

    # 2. Load homepage and look for a careers link.
    careers_url: str | None = None
    try:
        resp = page.goto(website, wait_until="domcontentloaded", timeout=25_000)
        time.sleep(1)
        if resp and resp.ok:
            careers_url = _find_careers_link_in_page(page, website)
    except Exception as e:
        logger.debug("homepage_failed url=%s err=%s", website, e)

    # 3. If not found by scanning, try common paths.
    if not careers_url:
        careers_url = _try_common_paths(page, website)

    if not careers_url:
        return None, ""

    # 4. Fetch the careers page (might already be current if _try_common_paths did it).
    try:
        if page.url != careers_url:
            resp = page.goto(careers_url, wait_until="domcontentloaded", timeout=25_000)
            time.sleep(1)
            if not resp or not resp.ok:
                return None, ""
        text = _page_text(page)
        return careers_url, text if len(text) >= MIN_PAGE_TEXT_LEN else ""
    except Exception as e:
        logger.debug("careers_fetch_failed url=%s err=%s", careers_url, e)
        return None, ""


def classify(page_text: str) -> str:
    """Return intern_hiring_status string based on page content."""
    if not page_text:
        return "unknown"
    if INTERN_KEYWORDS.search(page_text):
        return "hiring"
    # Page loaded but no intern mentions.
    return "not_hiring"


def enrich_company(page: Page, company: dict) -> dict | None:
    """
    Enrich one company. Returns a dict with fields to update, or None if nothing changed.
    If the stored website is a VC portfolio page, resolves the real company website first.
    """
    name = company.get("name", "?")
    updates: dict = {}

    # Resolve VC-internal website to real company website before enrichment.
    website = company.get("website", "")
    if _is_vc_internal(website):
        real_website = resolve_vc_website(page, website, company_name=name)
        if real_website:
            updates["website"] = real_website
            company = {**company, "website": real_website, "careers_page_url": None}
        else:
            logger.warning("resolve_failed name=%s vc_url=%s", name, website)
            updates["intern_hiring_status"] = "unknown"
            return updates

    careers_url, text = fetch_careers_page(page, company)

    updates["intern_hiring_status"] = classify(text)
    existing = company.get("careers_page_url") or ""
    if careers_url and (not existing or "ycombinator.com" in existing):
        updates["careers_page_url"] = careers_url

    logger.info(
        "enrich name=%s status=%s careers_url=%s text_len=%d",
        name, updates["intern_hiring_status"], careers_url or "none", len(text),
    )
    return updates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Max companies to process")
    parser.add_argument("--source", type=str, default=None, help="Filter by source_fund")
    parser.add_argument("--recheck", action="store_true", help="Re-process already-classified companies")
    args = parser.parse_args()

    supabase = get_supabase()

    query = supabase.table("companies").select(
        "id,name,website,careers_page_url,intern_hiring_status,source_fund"
    )
    if not args.recheck:
        query = query.eq("intern_hiring_status", "unknown")
    if args.source:
        query = query.eq("source_fund", args.source)
    if args.limit:
        query = query.limit(args.limit)

    companies = query.execute().data
    logger.info("enrich_start total=%d recheck=%s", len(companies), args.recheck)

    if not companies:
        logger.info("nothing_to_enrich")
        return

    updated = 0
    failed = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = ctx.new_page()

        for i, company in enumerate(companies, 1):
            logger.info("progress %d/%d name=%s", i, len(companies), company.get("name"))
            try:
                updates = enrich_company(page, company)
                if updates:
                    try:
                        supabase.table("companies").update(updates).eq("id", company["id"]).execute()
                        updated += 1
                    except Exception as db_err:
                        err_str = str(db_err)
                        if "duplicate key" in err_str or "23505" in err_str:
                            # Real website already exists from another source; drop this duplicate row.
                            logger.info(
                                "duplicate_website name=%s old_url=%s real_url=%s — deleting duplicate",
                                company.get("name"), company.get("website"), updates.get("website"),
                            )
                            supabase.table("companies").delete().eq("id", company["id"]).execute()
                            updated += 1
                        else:
                            raise
            except Exception as e:
                logger.exception("enrich_failed name=%s", company.get("name"))
                failed += 1

            time.sleep(REQUEST_DELAY)

        browser.close()

    print(f"\nDone. updated={updated} failed={failed} total={len(companies)}")


if __name__ == "__main__":
    main()
