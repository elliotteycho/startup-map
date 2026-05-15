# Deferred sources

Scrapers that were started but not finished, kept for reference rather than deleted. Each one teaches something about the failure mode that drove a different approach in the main pipeline.

## a16z.py

a16z's portfolio page at `a16z.com/portfolio` is a heavy single page app. Standard anchor tag extraction with BeautifulSoup returns mostly nothing usable because the company links are rendered behind React routing rather than as static `<a>` elements with `href` attributes pointing to company sites.

The deferral signaled that the right pattern for SPA heavy directories is not to fight the rendered DOM with Playwright, but to find the underlying API the SPA itself hits. This is exactly the approach that worked for Y Combinator via Algolia (see `scraper/extractors/yc.py` and `docs/scraper-design.md`).

Reviving the a16z source means finding the API endpoint a16z's frontend uses to populate the portfolio grid, then hitting it directly with httpx the way the YC extractor does.
