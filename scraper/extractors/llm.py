"""LLM-based extractor.

Strategy: VC portfolio pages link to portfolio companies via anchor tags. We
extract every link that could plausibly be a portfolio company (excluding
obvious nav, social, legal, blog, podcast, etc.) along with anchor text and a
small neighborhood of context, then ask the LLM to filter the list down to
actual portfolio companies and structure the metadata.

We deliberately do NOT exclude links to the source VC's own domain, because
many VC sites use internal company-detail pages (e.g., foundersfund.com/companies/X)
rather than direct external links.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional
from urllib.parse import urlparse

from anthropic import Anthropic
from bs4 import BeautifulSoup, Tag

from models import Company, InternHiringStatus

logger = logging.getLogger("extractors.llm")

DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

# Domains we always exclude (clearly not portfolio companies).
EXCLUDED_DOMAINS = {
    "twitter.com", "x.com", "linkedin.com", "facebook.com", "instagram.com",
    "youtube.com", "github.com", "medium.com", "substack.com",
    "spotify.com", "open.spotify.com", "podcasts.apple.com", "soundcloud.com",
    "anchor.fm", "rss.com", "buzzsprout.com", "vimeo.com",
    "wikipedia.org", "wsj.com", "nytimes.com", "bloomberg.com",
    "techcrunch.com", "forbes.com", "ft.com", "theinformation.com",
}

# URL paths that are clearly NOT portfolio companies.
EXCLUDED_PATH_PATTERNS = [
    re.compile(r"^/?$"),                                   # homepage
    re.compile(r"^/(about|about-us|team|people|partners?)(/|$)", re.I),
    re.compile(r"^/(contact|contact-us|location)(/|$)", re.I),
    re.compile(r"^/(careers?|jobs?)(/|$)", re.I),
    re.compile(r"^/(privacy|terms|legal|tos|cookies?|disclosures?)(/|$)", re.I),
    re.compile(r"^/(login|signin|signup|register|account)(/|$)", re.I),
    re.compile(r"^/(blog|news|press|insights?|articles?|stories)(/|$)", re.I),
    re.compile(r"^/(podcasts?|episodes?|videos?|events?)(/|$)", re.I),
    re.compile(r"^/(search|sitemap|rss|feed)(/|$)", re.I),
    re.compile(r"^/(thesis|values|approach|mission|vision|history)(/|$)", re.I),
    re.compile(r"\.(pdf|jpg|jpeg|png|gif|svg|webp|mp3|mp4|css|js)$", re.I),
    re.compile(r"^#"),
    re.compile(r"^/?\?"),
]

EXTRACTION_PROMPT = """You are extracting startup company entries from a VC firm's portfolio page.

I have already extracted candidate links from the page. Each entry has the link text, the URL, and a snippet of nearby context. Some are real portfolio companies; many are nav links, blog posts, partner bios, etc.

Your job: identify which candidates point to actual portfolio companies, and return structured data for each.

Return a JSON array of company objects. Each object has:
- name (string, required): the company name
- website (string, required): the URL from the candidate. If the URL is an internal page on the VC's own site (e.g., https://foundersfund.com/companies/anduril), return that URL anyway; we will resolve it later.
- sector (string, optional): one of "AI", "Fintech", "Healthcare", "Consumer", "Enterprise", "Crypto", "Climate", "Bio", "Education", "Gaming", "Other". Null if unclear.
- one_line_pitch (string, optional): short description if you can infer from the context, max 200 chars. Null if not visible.

Hard rules:
- Include EVERY portfolio company you can identify. Do not sample.
- A real portfolio company link points to either (a) the company's own domain, or (b) an internal portfolio detail page on the VC's own site.
- Exclude: blog posts, podcast episodes, news/press articles, the VC firm itself, partner/team bios, contact/about/careers/legal pages, login pages, social media, search/feed/sitemap, navigation/menu items.
- If a single company appears multiple times (different links), include it once.
- Output ONLY the raw JSON array. No prose, no markdown fences.

Source fund: {source_fund}

Candidate links ({count} total):
{candidates}

JSON array:"""


def _path_looks_like_nav(href: str) -> bool:
    """True if the URL path matches a nav/legal/blog pattern."""
    parsed = urlparse(href)
    path = parsed.path or "/"
    for pattern in EXCLUDED_PATH_PATTERNS:
        if pattern.search(path):
            return True
    return False


def _is_excluded(href: str, source_domain: str) -> bool:
    """True if the link should not be considered a portfolio candidate."""
    if not href:
        return True
    if href.startswith(("mailto:", "tel:", "javascript:", "#")):
        return True
    if not href.startswith("http"):
        return True
    host = urlparse(href).netloc.lower()
    if not host:
        return True
    host_stripped = host[4:] if host.startswith("www.") else host
    # Exclude social/news/podcast platforms.
    if host_stripped in EXCLUDED_DOMAINS:
        return True
    for excluded in EXCLUDED_DOMAINS:
        if host_stripped.endswith("." + excluded):
            return True
    # Allow source-domain links IF they look like company detail pages
    # (i.e., not nav/legal/blog/etc).
    if host_stripped == source_domain:
        return _path_looks_like_nav(href)
    # External links: always allow (LLM will filter).
    return False


def _resolve_relative(href: str, source_url: str) -> str:
    """Resolve relative or root-relative URLs against the source page."""
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        parsed = urlparse(source_url)
        return f"{parsed.scheme}://{parsed.netloc}{href}"
    if href.startswith("http"):
        return href
    return ""  # Skip oddly-formatted hrefs


def _extract_candidates(html: str, source_url: str) -> list[dict]:
    """Pull plausible portfolio company links + context. Deduplicated by URL."""
    soup = BeautifulSoup(html, "html.parser")
    source_domain = urlparse(source_url).netloc.lower()
    if source_domain.startswith("www."):
        source_domain = source_domain[4:]

    seen: dict[str, dict] = {}
    for a in soup.find_all("a", href=True):
        if not isinstance(a, Tag):
            continue
        href_raw = a.get("href", "").strip()
        href = _resolve_relative(href_raw, source_url)
        if _is_excluded(href, source_domain):
            continue

        text = a.get_text(" ", strip=True)[:200]
        parent = a.parent
        context = parent.get_text(" ", strip=True)[:300] if parent else ""

        parsed = urlparse(href)
        key = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/").lower()

        if key in seen:
            if len(text) > len(seen[key]["text"]):
                seen[key] = {"href": href, "text": text, "context": context}
            continue
        seen[key] = {"href": href, "text": text, "context": context}

    return list(seen.values())


def _format_candidates(candidates: list[dict]) -> str:
    """Format candidate links as a readable list for the LLM prompt."""
    lines = []
    for i, c in enumerate(candidates, 1):
        text = c["text"] or "(no text)"
        context = c["context"]
        if context and context != text:
            lines.append(f"{i}. text=\"{text}\" url={c['href']}\n   context=\"{context}\"")
        else:
            lines.append(f"{i}. text=\"{text}\" url={c['href']}")
    return "\n".join(lines)


def _extract_json_array(raw: str) -> Optional[list]:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        parsed = json.loads(raw[start : end + 1])
        return parsed if isinstance(parsed, list) else None
    except json.JSONDecodeError:
        return None


def extract_companies(
    html: str,
    source_fund: str,
    source_url: str = "",
    client: Optional[Anthropic] = None,
) -> list[Company]:
    """Extract companies from raw HTML using the LLM."""
    client = client or Anthropic()

    candidates = _extract_candidates(html, source_url)
    logger.info("llm_extract source=%s candidates=%d", source_fund, len(candidates))

    if not candidates:
        logger.warning("llm_extract source=%s no_candidate_links_found", source_fund)
        return []

    if len(candidates) > 600:
        logger.info("llm_extract source=%s truncating from=%d to=600", source_fund, len(candidates))
        candidates = candidates[:600]

    prompt = EXTRACTION_PROMPT.format(
        source_fund=source_fund,
        count=len(candidates),
        candidates=_format_candidates(candidates),
    )

    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text
    items = _extract_json_array(raw)
    if items is None:
        logger.error(
            "llm_extract_invalid_json source=%s response_preview=%s",
            source_fund,
            raw[:500],
        )
        return []

    companies: list[Company] = []
    seen_websites: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        website = item.get("website")
        if not name or not isinstance(name, str):
            continue
        if not website or not isinstance(website, str):
            continue
        if not website.startswith("http"):
            website = "https://" + website.lstrip("/")

        website_key = website.rstrip("/").lower()
        if website_key in seen_websites:
            continue
        seen_websites.add(website_key)

        try:
            companies.append(Company(
                name=name.strip(),
                website=website.strip(),
                sector=item.get("sector"),
                one_line_pitch=(item.get("one_line_pitch") or None),
                source_fund=source_fund,
                intern_hiring_status=InternHiringStatus.UNKNOWN,
            ))
        except (KeyError, ValueError) as e:
            logger.warning("llm_extract_skip_item error=%s item=%s", e, item)
            continue

    logger.info("llm_extract source=%s extracted=%d", source_fund, len(companies))
    return companies
