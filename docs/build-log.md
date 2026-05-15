# Build Log

A phase by phase narrative of what shipped when, written for someone reading the project as a story. The raw history is in `git log`. This is the curated version.

## Phase 0: Spec, May 2026

Locked the v1 specification before writing any code. The driving question was not "what should this dashboard show" but "why does this product exist and what is the smallest thing that proves it." The spec answers both.

Five buckets of competitors, three layer competitive edge, 90 day kill criteria. The strategic move is curation discipline: 100 to 200 companies, not 5,000. The day this becomes a Wellfound clone is the day the differentiation dies. Full reasoning in [`spec.md`](spec.md).

The architecture decisions that followed (Supabase over Firebase, Python plus Anthropic over LangChain, multi school from day 1, RLS from day 1) are each captured as ADRs in [`decisions.md`](decisions.md) with alternatives explicitly considered.

**Shipped.** Spec, ADRs 001 to 005, repo structure, initial Supabase project, first SQL migration.

## Phase 1: Scaffold and proof of concept

Set up the three pieces in parallel: a Next.js app with a Supabase client, a Python virtualenv with Playwright and the Anthropic SDK, and a SQL schema with `schools`, `companies`, `alumni`, and `events` tables plus a `companies_with_alumni` view.

First scraper target was a16z's portfolio page, picked because it is well known and a useful difficulty test. It turned out to be a hard test: a16z is a JavaScript heavy single page app with React routing, and standard anchor tag extraction returns mostly nothing usable. The a16z source got deferred and the proof of concept moved to Founders Fund, which renders portfolio links as static anchor tags.

The first end to end pipeline run extracted 87 companies from Founders Fund and upserted them into Supabase. The dashboard, which already had seed data in migration 002, switched over to the real data. The thesis was alive.

**Shipped.** End to end pipeline (Founders Fund through to dashboard render), three database migrations, basic data table page, seed data fallback.

## Phase 2: Generalize the scraper

The Founders Fund pipeline worked but only for Founders Fund. The path to 20+ sources was either hand writing extractors per site (slow) or finding a generic strategy.

The generic strategy that emerged was the hybrid LLM plus CSS approach now documented in [`scraper-design.md`](scraper-design.md). BS4 extracts every plausible anchor candidate. A domain blocklist and a path regex set drop obvious noise. Claude Haiku filters and structures the survivors.

The first sites added under this strategy were Sequoia, Khosla, Greylock, General Catalyst, and Lightspeed. Each took roughly 10 minutes to validate via the smoke test rather than a day to write a custom extractor.

**Shipped.** LLM based generic extractor, smoke test harness, six VC portfolio sources working through one pipeline.

## Phase 3: YC integration and careers enrichment

YC is the highest value single source. It also turned out to be the easiest to scrape, but not in the obvious way.

The first attempt was Playwright plus BS4 over the rendered YC company page. It worked but was slow and the React DOM was clearly fragile. The shortcut became obvious after viewing the page source: YC powers the directory through Algolia, the public read only API key sits inline in `window.AlgoliaOpts`. One httpx GET to fetch the key, one POST to Algolia, and the entire batch of hiring companies comes back as structured JSON. No browser needed.

Added three YC batches: Winter 2025, Summer 2024, Winter 2024. These are the batches where companies are small enough to have responsive founders and recent enough to still be active.

Separately, built `enrich_careers.py` to discover careers page URLs and set `intern_hiring_status` for companies where the portfolio scrapers could not capture it. The script tries a list of common paths (`/careers`, `/jobs`, `/join`), parses the resulting page for intern keywords, and updates Supabase accordingly. Handles the edge case of VC internal detail pages by following the link to the real company website first.

**Shipped.** YC Algolia direct fetch, careers page enrichment script, three YC batches in production.

## Phase 4: Dashboard polish

The first dashboard was a data table. Functional, ugly. Phase 4 was the visual rebuild: card based grid, sector pills as filters, intern hiring status pills, company favicons, search across name and pitch and source fund, per company detail pages at `/companies/[slug]`.

The biggest UX call was making the stat cells (Companies, Hiring interns, Sectors, Vandy connections) interactive. Clicking a stat applies its filter. Clicking Companies clears everything. This collapses two UI rows into one and surfaces the most useful filters without a dedicated filter panel.

Rebranded from "Startup Dashboard" to "Startup Map." Redesigned the hero with a dark gradient and a yellow Beta pill.

**Shipped.** Card UI, interactive stat cells, sector pills, detail pages, redesigned hero, "Startup Map" branding.

## Phase 5: Documentation revamp, May 2026

The repo had a strong spec doc, real ADRs, and 11 thoughtful commits, but nothing pulled the story together for someone landing on the GitHub page cold. The top level README was a generic Getting Started. The competitive thesis, the scraper design, and the architecture reasoning were buried.

This phase rewrote the README as a portfolio piece, added `architecture.md` for end to end data flow with Mermaid sequence diagrams, added `scraper-design.md` for the hybrid LLM strategy and YC Algolia trick, added this build log, and added a `LICENSE` file. Fixed a duplication bug in the spec doc, corrected version drift across docs (Next 14 had become Next 16, React 19, Tailwind 4), removed a dead component (`web/components/CompaniesView.tsx`) and moved the deferred a16z scraper to `scraper/_deferred/` with a header explaining why.

**Shipped.** Portfolio first README with architecture diagram and honest status block, three new engineering docs, LICENSE, hygiene fixes across the repo.

## What's next

The remaining v1 work is operational rather than design.

**Expand the scraper to 20+ sources.** The hybrid strategy generalizes; each new source is roughly 10 minutes of smoke testing plus an entry in `SOURCES` in `pipeline.py`. Target list is in the spec under Section 7 (Constraints).

**Deploy the scraper to Render with weekly cron.** The pipeline runs cleanly from a local venv. Render Cron Jobs need a Procfile or a Render service definition. Estimated 2 hours of setup and validation.

**Populate the Vanderbilt alumni table.** Currently sparse (5 to 10 rows, manually seeded). Phase 2 work involves a LinkedIn data approach, which is the Phase 3 differentiator. Likely the highest leverage single piece of work to do next.

**Soft launch.** Once the data is populated and the alumni layer is on, share with 10 to 20 Vanderbilt friends via the channels in Layer 1 of the competitive edge thesis. Track the 90 day success metrics in Section 4 of the spec.
