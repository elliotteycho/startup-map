-- Migration 003: Drop UNIQUE constraint on slug
--
-- Why: the same company name (e.g. "Ramp") can legitimately appear across
-- multiple VC portfolios with different source URLs. The canonical key is
-- the website, not the slug. The slug is only a URL-friendly identifier.
--
-- Safe to re-run; uses IF EXISTS guards.

ALTER TABLE companies DROP CONSTRAINT IF EXISTS companies_slug_key;

-- Replace the UNIQUE constraint with a plain index for query performance.
CREATE INDEX IF NOT EXISTS idx_companies_slug ON companies(slug);
