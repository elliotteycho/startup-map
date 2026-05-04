-- Migration 004: Add depth columns to companies + founders table
-- These columns were added to production during the enrichment phase but were
-- missing from the migration history. Apply via Supabase SQL Editor.
-- Idempotent: safe to re-run.

-- ── Companies: enrichment fields ─────────────────────────────────────────────

ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS long_description TEXT,
  ADD COLUMN IF NOT EXISTS founded_year     INT,
  ADD COLUMN IF NOT EXISTS twitter_url      TEXT,
  ADD COLUMN IF NOT EXISTS linkedin_url     TEXT,
  ADD COLUMN IF NOT EXISTS tags             TEXT[];

-- ── Founders table ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS founders (
  id          BIGSERIAL PRIMARY KEY,
  company_id  BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  title       TEXT,
  linkedin_url TEXT,
  bio         TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (company_id, name)
);

CREATE INDEX IF NOT EXISTS idx_founders_company ON founders(company_id);

-- Allow public read of founders
ALTER TABLE founders ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public read founders" ON founders;
CREATE POLICY "public read founders" ON founders FOR SELECT USING (true);

-- ── Update companies_with_alumni view (use literal school_id, not subquery) ──

CREATE OR REPLACE VIEW companies_with_alumni AS
SELECT
  c.*,
  COALESCE(a.alumni_count, 0) AS vandy_alumni_count
FROM companies c
LEFT JOIN (
  SELECT current_company_id, COUNT(*) AS alumni_count
  FROM alumni
  WHERE school_id = 1  -- Vanderbilt; avoids subquery on every row evaluation
  GROUP BY current_company_id
) a ON a.current_company_id = c.id;
