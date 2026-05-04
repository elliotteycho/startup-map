"""
YC company extractor using YC's public Algolia search API.

The credentials live in window.AlgoliaOpts on the YC page — a public, read-only
key that restricts queries to YCCompany_production. Fetching it via regex from
the raw HTML avoids a Playwright launch just for this step.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from typing import Optional

import httpx

from models import Company, Founder, InternHiringStatus

logger = logging.getLogger("extractors.yc")

_ALGOLIA_APP_ID = "45BWZJ1SGC"
_ALGOLIA_INDEX = "YCCompany_production"
_YC_PAGE = "https://www.ycombinator.com/companies"

BATCH_NAMES: dict[str, str] = {
    "yc_w25": "Winter 2025",
    "yc_s24": "Summer 2024",
    "yc_w24": "Winter 2024",
    "yc_s23": "Summer 2023",
    "yc_w23": "Winter 2023",
    "yc_w22": "Winter 2022",
    "yc_s22": "Summer 2022",
}

# Approximate founding year from YC batch (companies usually founded 6-12 months before batch)
# KEEP IN SYNC with BATCHES dict in fetch_yc_founders.py
_BATCH_YEAR: dict[str, int] = {
    "Winter 2025": 2024, "Summer 2024": 2024, "Winter 2024": 2023,
    "Summer 2023": 2023, "Winter 2023": 2022, "Winter 2022": 2021, "Summer 2022": 2022,
}

_SECTOR_MAP = {
    "artificial intelligence": "AI",
    "machine learning": "AI",
    "fintech": "Fintech",
    "financial technology": "Fintech",
    "healthcare": "Healthcare",
    "consumer": "Consumer",
    "enterprise": "Enterprise",
    "b2b": "Enterprise",
    "saas": "Enterprise",
    "crypto": "Crypto",
    "web3": "Crypto",
    "climate": "Climate",
    "biotech": "Bio",
    "education": "Education",
    "gaming": "Gaming",
}

_HEADCOUNT_RANGES = [
    (10, "1-10"),
    (25, "11-25"),
    (50, "26-50"),
    (100, "51-100"),
]


def parse_location(raw: object) -> Optional[str]:
    """Return the first location string from all_locations.

    Algolia returns all_locations as either a list of strings or a bare string.
    Treating a string as a list produces locations[0] == first character, e.g.
    'San Francisco, CA'[0] == 'S'. Guard against that here.
    """
    if not raw:
        return None
    if isinstance(raw, str):
        return raw or None
    locs = list(raw)
    return locs[0] if locs else None


def parse_founded_year(raw_year, batch_fallback: Optional[int] = None) -> Optional[int]:
    """Convert a raw YC API year value to an int year.

    Handles three formats:
      - Unix timestamp (int > 1_000_000_000) — e.g. launched_at from Algolia
      - Plain year int (1980-2030)
      - ISO date string "YYYY-MM-DD" — takes first 4 chars
    Falls back to batch_fallback if raw_year is None or unrecognized.
    """
    import datetime
    if raw_year is None:
        return batch_fallback
    try:
        v = int(raw_year)
        if v > 1_000_000_000:
            return datetime.datetime.fromtimestamp(v, tz=datetime.timezone.utc).year
        if 1980 <= v <= 2030:
            return v
        return batch_fallback
    except (ValueError, TypeError):
        try:
            return int(str(raw_year)[:4])
        except (ValueError, TypeError):
            return batch_fallback


# get_algolia_key logic is duplicated in fetch_yc_founders.py (stdlib-only version).
# KEEP IN SYNC if the YC page markup changes.
def get_algolia_key() -> str:
    resp = httpx.get(
        _YC_PAGE,
        headers={"User-Agent": "Mozilla/5.0"},
        follow_redirects=True,
        timeout=30,
    )
    resp.raise_for_status()
    m = re.search(r'AlgoliaOpts\s*=\s*\{[^}]*"key"\s*:\s*"([^"]+)"', resp.text)
    if not m:
        raise RuntimeError("AlgoliaOpts key not found on YC page — their markup may have changed")
    return m.group(1)


def _sector(industries: list[str]) -> Optional[str]:
    for ind in industries:
        low = ind.lower()
        for keyword, sector in _SECTOR_MAP.items():
            if keyword in low:
                return sector
    return "Other" if industries else None


def _headcount(team_size: Optional[int]) -> Optional[str]:
    if not team_size:
        return None
    for threshold, label in _HEADCOUNT_RANGES:
        if team_size <= threshold:
            return label
    return "100+"


def _parse_founders(raw: list[dict]) -> list[Founder]:
    founders = []
    for f in raw or []:
        name = (f.get("full_name") or "").strip()
        if not name:
            first = (f.get("first_name") or "").strip()
            last = (f.get("last_name") or "").strip()
            name = f"{first} {last}".strip()
        if not name:
            continue
        linkedin = f.get("linkedin_url") or f.get("linkedinUrl") or None
        if linkedin:
            linkedin = linkedin.strip() or None
        title = (f.get("title") or f.get("role") or "").strip() or None
        bio = (f.get("founder_bio") or f.get("bio") or "").strip() or None
        founders.append(Founder(name=name, title=title, linkedin_url=linkedin, bio=bio))
    return founders


def extract_yc_batch(
    batch_key: str,
    source_fund: str,
    api_key: Optional[str] = None,
) -> list[Company]:
    batch_name = BATCH_NAMES.get(batch_key)
    if not batch_name:
        raise ValueError(f"Unknown batch key '{batch_key}'. Add to BATCH_NAMES in extractors/yc.py.")

    if api_key is None:
        api_key = get_algolia_key()

    algolia_url = f"https://{_ALGOLIA_APP_ID.lower()}-dsn.algolia.net/1/indexes/*/queries"
    headers = {
        "X-Algolia-Application-Id": _ALGOLIA_APP_ID,
        "X-Algolia-API-Key": api_key,
        "Content-Type": "application/json",
    }
    filters = urllib.parse.quote(f'batch:"{batch_name}" AND isHiring:true')
    payload = {
        "requests": [{
            "indexName": _ALGOLIA_INDEX,
            "params": f"filters={filters}&hitsPerPage=1000",
        }]
    }

    resp = httpx.post(algolia_url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    hits: list[dict] = data["results"][0]["hits"]
    nb_hits: int = data["results"][0].get("nbHits", 0)
    logger.info("yc_algolia batch=%s total=%d fetched=%d", batch_name, nb_hits, len(hits))

    founded_year = _BATCH_YEAR.get(batch_name)

    companies: list[Company] = []
    for hit in hits:
        website = (hit.get("website") or "").strip()
        if not website:
            continue
        if not website.startswith("http"):
            website = "https://" + website

        name = (hit.get("name") or "").strip()
        if not name:
            continue

        one_liner = (hit.get("one_liner") or "").strip()[:300] or None
        long_desc = (hit.get("long_description") or hit.get("description") or "").strip() or None

        slug = hit.get("slug", "")
        careers_url = f"https://www.ycombinator.com/companies/{slug}#jobs" if slug else None

        location = parse_location(hit.get("all_locations"))

        raw_year = hit.get("founded_date") or hit.get("launched_at") or hit.get("year_founded")
        company_year = parse_founded_year(raw_year, batch_fallback=founded_year)

        founders = _parse_founders(hit.get("founders") or hit.get("team") or [])

        try:
            c = Company(
                name=name,
                website=website,
                sector=_sector(hit.get("industries") or []),
                stage=hit.get("stage"),
                headcount_range=_headcount(hit.get("team_size")),
                location=location,
                careers_page_url=careers_url,
                intern_hiring_status=InternHiringStatus.HIRING,
                one_line_pitch=one_liner or long_desc,
                long_description=long_desc,
                source_fund=source_fund,
                founded_year=company_year,
            )
            c.founders = founders
            companies.append(c)
        except Exception as e:
            logger.warning("yc_algolia skip name=%s error=%s", name, e)

    logger.info("yc_algolia batch=%s companies=%d", batch_name, len(companies))
    return companies
