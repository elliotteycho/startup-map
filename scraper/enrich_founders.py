"""
Enrich founder data by scraping each company's own team/about page.

For each company without any founders in the DB, fetches their website,
tries common team page paths, and uses Claude Haiku to extract founder info.

Usage:
    python enrich_founders.py                  # all companies missing founders
    python enrich_founders.py --limit 50       # process at most 50
    python enrich_founders.py --source "Sequoia Capital"  # one fund only
    python enrich_founders.py --recheck        # redo companies already attempted
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from typing import Optional

import httpx
from anthropic import Anthropic
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("enrich_founders")

TEAM_PATHS = ["/team", "/about", "/about-us", "/company", "/people", "/founders", "/our-team", "/leadership"]
TIMEOUT = 12
MAX_HTML_CHARS = 40_000  # trim before sending to LLM


def get_supabase():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])


def fetch_page(url: str) -> Optional[str]:
    """Return visible text from a URL, or None on failure."""
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; StartupMap/1.0)"},
            follow_redirects=True,
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "head"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # Keep only lines with actual content
        lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 3]
        return "\n".join(lines)[:MAX_HTML_CHARS]
    except Exception as e:
        logger.debug("fetch_failed url=%s error=%s", url, e)
        return None


def find_team_page(base_url: str) -> Optional[tuple[str, str]]:
    """Try common team page paths. Returns (url, text) for the first that works."""
    base = base_url.rstrip("/")
    for path in TEAM_PATHS:
        url = base + path
        text = fetch_page(url)
        if text and len(text) > 200:
            logger.info("team_page_found url=%s", url)
            return url, text
    # Fall back to homepage
    text = fetch_page(base_url)
    if text and len(text) > 200:
        return base_url, text
    return None


def extract_founders_llm(company_name: str, page_text: str, client: Anthropic) -> list[dict]:
    """Ask Claude Haiku to extract founder info from the page text."""
    prompt = f"""You are extracting founder information for a startup called "{company_name}" from their website.

Here is text scraped from their team/about page:

<page_text>
{page_text[:MAX_HTML_CHARS]}
</page_text>

Extract the FOUNDERS only (not all employees — just co-founders / founding team members).
For each founder return a JSON object with these fields (use null if not found):
- name (string, required)
- title (string, e.g. "CEO & Co-founder")
- linkedin_url (string, full URL if present on the page)
- bio (string, 1-3 sentence bio if present)

Return a JSON array. If no founders are identifiable, return [].
Return ONLY the JSON array, no other text."""

    try:
        msg = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        founders = json.loads(raw)
        return [f for f in founders if isinstance(f, dict) and f.get("name")]
    except Exception as e:
        logger.warning("llm_extract_failed company=%s error=%s", company_name, e)
        return []


def upsert_founders(sb, company_id: int, founders: list[dict]) -> int:
    if not founders:
        return 0
    rows = []
    for f in founders:
        rows.append({
            "company_id":  company_id,
            "name":        str(f["name"])[:200],
            "title":       str(f["title"])[:200] if f.get("title") else None,
            "linkedin_url": str(f["linkedin_url"])[:500] if f.get("linkedin_url") else None,
            "bio":         str(f["bio"])[:2000] if f.get("bio") else None,
        })
    try:
        sb.table("founders").upsert(rows, on_conflict="company_id,name").execute()
        return len(rows)
    except Exception as e:
        logger.warning("upsert_failed company_id=%d error=%s", company_id, e)
        return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",           type=int, default=200)
    parser.add_argument("--source",          type=str, default=None)
    parser.add_argument("--recheck",         action="store_true")
    parser.add_argument("--missing-linkedin", action="store_true",
                        help="Only process companies where ≥1 founder is missing a LinkedIn URL")
    args = parser.parse_args()

    sb = get_supabase()
    ai = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Fetch companies to process
    query = sb.table("companies").select("id,name,website,source_fund")
    if args.source:
        query = query.eq("source_fund", args.source)
    query = query.order("id")
    companies = query.execute().data or []

    if args.missing_linkedin:
        # Companies where at least one founder has no LinkedIn URL
        no_li = sb.table("founders").select("company_id").is_("linkedin_url", "null").execute().data or []
        target_ids = {r["company_id"] for r in no_li}
        companies = [c for c in companies if c["id"] in target_ids]
    elif not args.recheck:
        existing_ids = {
            r["company_id"]
            for r in (sb.table("founders").select("company_id").execute().data or [])
        }
        companies = [c for c in companies if c["id"] not in existing_ids]

    companies = companies[: args.limit]
    logger.info("processing count=%d", len(companies))

    stats = {"ok": 0, "no_page": 0, "no_founders": 0, "error": 0}

    for i, company in enumerate(companies):
        logger.info("[%d/%d] %s", i + 1, len(companies), company["name"])
        try:
            result = find_team_page(company["website"])
            if not result:
                logger.info("no_team_page company=%s", company["name"])
                stats["no_page"] += 1
                continue

            _, page_text = result
            founders = extract_founders_llm(company["name"], page_text, ai)

            if not founders:
                logger.info("no_founders_found company=%s", company["name"])
                stats["no_founders"] += 1
                continue

            inserted = upsert_founders(sb, company["id"], founders)
            logger.info("founders_saved company=%s count=%d", company["name"], inserted)
            stats["ok"] += 1

        except Exception as e:
            logger.warning("company_failed company=%s error=%s", company["name"], e)
            stats["error"] += 1

        time.sleep(0.5)  # polite rate limiting

    print("\n" + "=" * 60)
    print(f"  Enriched:      {stats['ok']}")
    print(f"  No team page:  {stats['no_page']}")
    print(f"  No founders:   {stats['no_founders']}")
    print(f"  Errors:        {stats['error']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
