"""Scraper orchestrator. Reads sources, runs extractors, upserts into Supabase."""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from supabase import Client, create_client

from models import ScrapeResult

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("pipeline")


def get_supabase() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


def upsert_companies(supabase: Client, result: ScrapeResult) -> int:
    """Upsert each company keyed on website. Returns number of rows affected."""
    rows = [c.to_supabase_row() for c in result.companies]
    if not rows:
        logger.info("source=%s no_companies", result.source)
        return 0

    response = supabase.table("companies").upsert(
        rows,
        on_conflict="website",
    ).execute()
    affected = len(response.data) if response.data else 0
    logger.info("source=%s upserted=%d", result.source, affected)
    return affected


def run_source(name: str) -> ScrapeResult:
    """Dynamic import of scraper.sources.<name> and call its scrape() function."""
    import importlib

    module = importlib.import_module(f"sources.{name}")
    logger.info("source=%s starting", name)
    started = datetime.utcnow()
    companies = module.scrape()
    logger.info("source=%s extracted=%d duration=%ss", name, len(companies), (datetime.utcnow() - started).seconds)
    return ScrapeResult(source=name, fetched_at=started, companies=companies)


def main() -> None:
    """Run all sources listed in SOURCES env var (comma separated) or default to a16z."""
    sources = os.environ.get("SOURCES", "a16z").split(",")
    supabase = get_supabase()

    total_affected = 0
    for source_name in sources:
        source_name = source_name.strip()
        try:
            result = run_source(source_name)
            total_affected += upsert_companies(supabase, result)
        except Exception:
            logger.exception("source=%s failed", source_name)

    logger.info("pipeline_complete total_affected=%d sources=%d", total_affected, len(sources))


if __name__ == "__main__":
    main()
