# Architectural Decision Records

Each entry: what was decided, when, why, and what alternatives were considered. Append new entries; do not edit old ones (use a follow up entry to revise).

---

## ADR 001: Stack choice (May 2026)
**Decision:** Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui on Vercel; Supabase Postgres; Python scraper on Render cron.

**Why:** Fastest path from empty folder to production for a solo developer. Vercel deploys Next.js with one git push. Supabase replaces three services (database, REST API, auth) with one. Python is the only serious choice for scraping plus LLM extraction. All four are free tier compatible.

**Alternatives considered:** Django (worse frontend story), MongoDB (relational data is wrong shape for it), Firebase (vendor lock in), Cursor as IDE (no benefit over VS Code + Claude Code).

---

## ADR 002: Multi-school architecture from day 1 (May 2026)
**Decision:** `schools` table exists from the first migration with Vanderbilt as row 1. School is a parameter, not a hardcoded constant. URL routing supports `/vanderbilt/companies` even though Vanderbilt is the only valid path in v1.

**Why:** Phase 3 explicitly expands to other top 30 schools. Hardcoding "Vanderbilt" everywhere would force a major refactor in month 4. The 30 minute upfront cost is negligible.

**Alternatives considered:** Hardcode Vanderbilt for v1 and refactor later. Rejected because the refactor cost is high and the upfront cost is trivial.

---

## ADR 003: LLM as fallback extractor (May 2026)
**Decision:** Use CSS/XPath selectors per source where structure is clean. Fall back to Claude Haiku for HTML extraction where structure is irregular, with a strict Pydantic schema for the output.

**Why:** VC portfolio pages are snowflakes. Hand writing 245 extractors does not scale. Pure LLM extraction is too expensive (1 to 5 cents per page) for daily runs across all sources. Hybrid gets the best of both: cheap fast extraction where possible, LLM coverage where needed.

**Alternatives considered:** All CSS selectors (does not scale), all LLM (cost prohibitive), third party services like ScrapingBee (recurring cost).

---

## ADR 004: Row Level Security from day 1 on Supabase (May 2026)
**Decision:** Every table has RLS enabled. Public read policies for client safe data. Writes only via service role key (used by scraper, never exposed to frontend).

**Why:** Supabase tables are accessible via API by default. Forgetting to enable RLS is the most common Supabase security failure. Enabling from day 1 prevents the failure mode entirely.

**Alternatives considered:** Disable RLS in v1 for speed, enable later. Rejected because "later" never comes and the security debt compounds.

---

## ADR 005: Click tracking from day 1 (May 2026)
**Decision:** Capture every meaningful user interaction in a Supabase `events` table from launch. No PII, no auth required, anonymous session IDs only.

**Why:** The data moat in Phase 3 (response verification) requires months of accumulated event data. Adding tracking later means starting from zero engagement data when we need it most.

**Alternatives considered:** Add tracking after launch. Rejected because the data we need cannot be backfilled.
