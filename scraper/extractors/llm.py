"""LLM-based extractor. Fallback when CSS selectors are too fragile.

Pass cleaned HTML or text plus the Company schema; receive a list of structured
Company objects. Uses Claude Haiku for cost.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from anthropic import Anthropic
from bs4 import BeautifulSoup

from models import Company, InternHiringStatus

logger = logging.getLogger("extractors.llm")

DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
MAX_TEXT_CHARS = 30_000  # ~7.5k tokens, keeps cost predictable

EXTRACTION_PROMPT = """You are extracting startup company entries from a VC portfolio page.

Return a JSON array of company objects. Each object has these fields:
- name (string, required): the company name
- website (string, required): full URL starting with https://
- sector (string, optional): one of "AI", "Fintech", "Healthcare", "Consumer", "Enterprise", "Crypto", "Climate", "Bio", or null
- one_line_pitch (string, optional): a single sentence describing what they do, max 200 chars

Rules:
- Only include real companies. Skip the VC firm itself, news posts, navigation links.
- If a field is uncertain, set it to null. Never guess.
- Output ONLY the JSON array. No prose, no markdown fences.

Source fund: {source_fund}

Page content:
{content}
"""


def _clean_html(html: str) -> str:
    """Strip script/style/nav, return readable text."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return text[:MAX_TEXT_CHARS]


def extract_companies(
    html: str,
    source_fund: str,
    client: Optional[Anthropic] = None,
) -> list[Company]:
    """Extract companies from raw HTML using the LLM."""
    client = client or Anthropic()
    content = _clean_html(html)

    prompt = EXTRACTION_PROMPT.format(source_fund=source_fund, content=content)

    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    # Handle case where model wraps output in markdown despite instruction.
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("llm_extract_invalid_json error=%s raw=%s", e, raw[:200])
        return []

    companies: list[Company] = []
    for item in items:
        try:
            companies.append(Company(
                name=item["name"],
                website=item["website"],
                sector=item.get("sector"),
                one_line_pitch=item.get("one_line_pitch"),
                source_fund=source_fund,
                intern_hiring_status=InternHiringStatus.UNKNOWN,
            ))
        except (KeyError, ValueError) as e:
            logger.warning("llm_extract_skip_item error=%s item=%s", e, item)
            continue

    logger.info("llm_extract source=%s extracted=%d", source_fund, len(companies))
    return companies
