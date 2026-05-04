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

from models import Company, InternHiringStatus

logger = logging.getLogger("extractors.yc")

_ALGOLIA_APP_ID = "45BWZJ1SGC"
_ALGOLIA_INDEX = "YCCompany_production"
_YC_PAGE = "https://www.ycombinator.com/companies"

# Map our pipeline source keys to the batch strings Algolia uses.
BATCH_NAMES: dict[str, str] = {
    "yc_w25": "Winter 2025",
    "yc_s24": "Summer 2024",
    "yc_w24": "Winter 2024",
    "yc_s23": "Summer 2023",
    "yc_w23": "Winter 2023",
    "yc_w22": "Winter 2022",
    "yc_s22": "Summer 2022",
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


def get_algolia_key() -> str:
    """Fetch the public Algolia API key from the YC page via plain HTTP (no Playwright)."""
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
        if team_size < threshold:
            return label
    return "100+"


def extract_yc_batch(
    batch_key: str,
    source_fund: str,
    api_key: Optional[str] = None,
) -> list[Company]:
    """Return hiring companies for one YC batch, pulled from Algolia."""
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

        one_liner = hit.get("one_liner") or hit.get("long_description")
        if one_liner:
            one_liner = one_liner.strip()[:300]

        slug = hit.get("slug", "")
        careers_url = f"https://www.ycombinator.com/companies/{slug}#jobs" if slug else None

        locations: list[str] = hit.get("all_locations") or []
        location = locations[0] if locations else None

        try:
            companies.append(Company(
                name=name,
                website=website,
                sector=_sector(hit.get("industries") or []),
                stage=hit.get("stage"),
                headcount_range=_headcount(hit.get("team_size")),
                location=location,
                careers_page_url=careers_url,
                intern_hiring_status=InternHiringStatus.HIRING,
                one_line_pitch=one_liner,
                source_fund=source_fund,
            ))
        except Exception as e:
            logger.warning("yc_algolia skip name=%s error=%s", name, e)

    logger.info("yc_algolia batch=%s companies=%d", batch_name, len(companies))
    return companies
