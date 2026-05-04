"""Pydantic models matching the Supabase schema. Single source of truth for field shapes."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class InternHiringStatus(str, Enum):
    HIRING = "hiring"
    OPEN_TO = "open_to"
    NOT_HIRING = "not_hiring"
    UNKNOWN = "unknown"


class Company(BaseModel):
    """Mirrors the companies table in Supabase."""

    name: str = Field(..., min_length=1, max_length=200)
    website: str = Field(..., min_length=1)
    sector: Optional[str] = None
    stage: Optional[str] = None
    last_round_date: Optional[date] = None
    last_round_size_usd: Optional[int] = Field(None, ge=0)
    lead_investor: Optional[str] = None
    headcount_range: Optional[str] = None
    location: Optional[str] = None
    careers_page_url: Optional[str] = None
    intern_hiring_status: InternHiringStatus = InternHiringStatus.UNKNOWN
    one_line_pitch: Optional[str] = Field(None, max_length=300)
    source_fund: Optional[str] = None

    def to_supabase_row(self) -> dict:
        """Serialize for Supabase upsert. Drops None values to preserve existing data."""
        from re import sub
        from urllib.parse import urlparse

        slug = sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-")
        row = self.model_dump(mode="json", exclude_none=True)
        row["slug"] = slug
        row["last_scraped_at"] = datetime.utcnow().isoformat()

        # Normalize website to root domain so the same company scraped from
        # multiple VC portfolios always upserts to the same row.
        try:
            parsed = urlparse(str(self.website))
            netloc = parsed.netloc.lower().lstrip("www.")
            row["website"] = f"https://{netloc}"
        except Exception:
            pass

        return row


class ScrapeResult(BaseModel):
    """Output of a single source scrape."""

    source: str
    fetched_at: datetime
    companies: list[Company]
    errors: list[str] = Field(default_factory=list)
