# Scraper Design

The scraper is the most opinionated piece of this project. Three decisions worth walking through in detail: the hybrid LLM plus CSS extraction strategy, the YC Algolia direct fetch, and the Pydantic contract pattern that ties both paths together.

## The problem

The seed sourcing data is a database of 245 venture capital firms. Each one has a portfolio page on its own website. None of them use the same layout, the same HTML structure, the same tagging, the same way of marking which companies are in the portfolio versus which are blog posts, partner bios, or footer links. Some are static HTML. Most are JavaScript heavy with lazy loaded grids. A few render through a third party CMS with proprietary class names.

The naive options are both bad.

**Option 1: Hand write a CSS selector for every site.** This works for the first 3 sites in roughly a day each, then quickly becomes unsustainable. A new VC firm or a redesign of an existing one means another day of work. With a team of 1 and ~20 hours per week, this fails at roughly site 10.

**Option 2: Pure LLM extraction.** Send the entire rendered HTML to a model and ask for a JSON array of companies. This works on quality but the math kills it. A typical VC portfolio page is 100KB to 500KB of HTML, mostly noise. At Claude Sonnet input pricing this is 1 to 5 cents per page. Weekly cron across 50 sources is $2 to $13 per week, $100 to $700 per year, on a project with a zero dollar budget.

## The hybrid

The scraper splits the problem in two. Cheap deterministic logic does what cheap deterministic logic is good at. The LLM does only the small high signal step that requires judgment.

**Step 1: Render the page with Playwright.** Most VC portfolio pages need JavaScript to load the company grid. Headless Chromium with `wait_until="domcontentloaded"`, a 3 second sleep for dynamic content, and 15 scroll iterations to trigger lazy loads. This gives a full DOM snapshot.

**Step 2: BS4 extracts anchor tag candidates.** Iterate every `<a href>` on the page. Collect the URL, the anchor text, and the parent element's text as context (up to 300 characters).

**Step 3: Hard coded filtering removes obvious noise.** A domain blocklist drops social media (Twitter, LinkedIn, Instagram, YouTube), news outlets (Bloomberg, WSJ, TechCrunch), and podcast hosts (Spotify, Apple Podcasts, Buzzsprout). A path regex set drops the source VC's own nav, legal, and editorial pages (`/about`, `/team`, `/careers`, `/privacy`, `/blog`, `/podcasts`, etc.). Same domain links are kept only if their path looks like a company detail page, not a navigation page.

The result is typically 50 to 500 candidate links from an original DOM with 500 to 2000 anchor tags. Roughly a 10x reduction with near zero false negatives.

**Step 4: Claude Haiku filters and structures.** The candidates are formatted as a numbered list with text, URL, and context, and sent to Haiku with an extraction prompt. Haiku returns a JSON array of company objects. Each object has a name, a website, an optional sector, and an optional one line pitch.

The prompt is explicit about what to include (real portfolio companies, including internal VC detail pages like `foundersfund.com/companies/anduril`) and what to exclude (blog posts, partner bios, navigation, search pages, social media). It also handles the deduplication case where the same company appears under multiple links.

**Step 5: Pydantic validates and rejects bad rows.** The JSON array is parsed and each item is passed to the `Company` Pydantic model. Items with missing required fields (name, website) or invalid types are skipped with a warning. The model normalizes the website URL (prepends https:// if missing) and computes a slug from the name.

**Step 6: Supabase upsert keyed on website.** Companies are upserted with `on_conflict="website"`, which means re running the pipeline is idempotent. A company that already exists gets its `last_scraped_at` updated; a new company is inserted.

## Cost math

A typical VC portfolio page after BS4 filtering produces a prompt of 5,000 to 30,000 input tokens (the candidate list). Haiku output is 1,000 to 4,000 tokens. At Haiku 4.5 pricing this is well under one cent per source. Weekly run across 20 sources is roughly 20 cents. Annualized: $10 to $15. Well inside the zero dollar budget envelope.

Compare to pure LLM extraction on Sonnet without the BS4 prefilter: $100 to $700 per year. The BS4 prefilter does not just save money; it makes the whole approach feasible.

## YC via Algolia, not Playwright

Y Combinator is the most valuable single source in the pipeline. The company directory at `ycombinator.com/companies` has roughly 5,000 active companies across all batches, with structured industry tags, team sizes, locations, and an "is hiring" flag. Scraping the rendered page would work but is slow (Playwright launch + scroll + parse for every batch) and fragile (the React DOM structure can change).

The shortcut: YC's company directory is powered by a public Algolia search index. The credentials sit inline in the page source as `window.AlgoliaOpts = { ... "key": "abc123..." }`. The key is read only, scoped to the `YCCompany_production` index, and intended to be exposed to the browser. There is nothing private about it.

The scraper fetches the YC page with plain httpx (no Playwright), regexes the Algolia API key out of the HTML, then sends one POST to `https://45bwzj1sgc-dsn.algolia.net/1/indexes/*/queries` with a filter like `batch:"Winter 2025" AND isHiring:true` and `hitsPerPage=1000`. Algolia returns the full set of matching companies in a single response, with all the structured fields the directory shows.

This is roughly 100x faster than rendering the page. It is also more durable: Algolia's response schema is stable in a way the YC React DOM is not. The only fragile piece is the regex that finds the Algolia key on the YC page; if YC reformats `AlgoliaOpts` the regex breaks loudly with a clear error message, not silently.

This same pattern works for any site that uses a public client side search API. Worth checking before reaching for Playwright on any data heavy company directory.

## Pydantic as the contract

Both extractors converge on one type: `Company`. The LLM extractor builds `Company` instances from JSON. The YC extractor builds `Company` instances from Algolia hits. The pipeline orchestrator does not know or care which one ran; it just calls `upsert_companies(list[Company])`.

This matters for two reasons.

First, adding a field is one change, not three. Add `funding_total_usd` to the `Company` model, the database column, and the prompt, and both extractors pick it up automatically. Without a shared type, each extractor would have its own ad hoc dict and adding a field means changing every call site.

Second, validation lives in one place. The `Company` model enforces field types, length limits, and the `intern_hiring_status` enum. Bad data from any source gets rejected at the same boundary, with the same error semantics. The LLM cannot return a sector that breaks the schema because the model rejects it before it reaches Supabase.

The `to_supabase_row()` method is on the model itself. It serializes to a dict, drops None values (so partial updates do not overwrite existing data), and adds the derived `slug` and `last_scraped_at`. The pipeline never touches dict keys directly.

## Careers page enrichment

A second script, `scraper/enrich_careers.py`, runs after the main pipeline and fills in two fields the portfolio scrapers cannot reliably capture: the company's careers page URL and the intern hiring status.

For each company with `intern_hiring_status='unknown'`, the script tries a list of common careers paths against the company's website (`/careers`, `/jobs`, `/join`, `/team`, etc.). If a page returns content, it scans the text for intern related keywords (`intern`, `internship`, `co-op`). A hit sets the status to `hiring`. A page with no hit sets it to `not_hiring`. A site with no findable careers page leaves it as `unknown`.

Companies whose stored `website` is actually a VC internal detail page (foundersfund.com/companies/X, sequoiacap.com/companies/Y) get an extra step: the script first visits the detail page and tries to extract the real company URL before checking careers. The VC internal domains are in a static list at the top of the file.

This is mid quality on purpose. Detecting active internship listings requires actually parsing job board markup, which is its own snowflake problem. The current approach gets to a "probably hiring" signal cheaply and leaves the manual override path open via Supabase.

## What this does not do yet

**No retry logic.** A source that fails on a given week contributes zero rows that week. Adding tenacity backed retries with exponential backoff is straightforward; the dependency is already in `requirements.txt`. Deliberately not wired yet.

**No diff detection.** Every weekly run re extracts every company. No tracking of which companies appeared or disappeared between runs. This is fine at v1 scale but becomes interesting at 5,000+ companies.

**No structured logging output.** Logs go to stdout. Render's log viewer is enough for v1 monitoring. A real observability story (structured JSON logs, error tracking, run metrics) is appropriate when the scraper is critical infrastructure.

**No per source concurrency.** Sources run sequentially. A single 30 second source blocks the rest of the pipeline. At 7 sources this is fine; at 50 it would matter.

Each of these is a deliberate non choice for v1. The scraper exists to populate the dashboard, not to be the product.
