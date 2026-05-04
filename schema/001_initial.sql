-- Migration 001: Initial schema
-- Apply via Supabase SQL Editor
-- Idempotent: safe to re-run

-- ============================================================================
-- Schools table (multi-school capable from day 1)
-- ============================================================================
CREATE TABLE IF NOT EXISTS schools (
  id          BIGSERIAL PRIMARY KEY,
  slug        TEXT NOT NULL UNIQUE,
  name        TEXT NOT NULL,
  domain      TEXT,
  active      BOOLEAN NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO schools (slug, name, domain, active)
VALUES ('vanderbilt', 'Vanderbilt University', 'vanderbilt.edu', TRUE)
ON CONFLICT (slug) DO NOTHING;

-- ============================================================================
-- Companies table (12 fields plus metadata)
-- ============================================================================
CREATE TABLE IF NOT EXISTS companies (
  id                    BIGSERIAL PRIMARY KEY,
  slug                  TEXT NOT NULL UNIQUE,
  name                  TEXT NOT NULL,
  website               TEXT NOT NULL UNIQUE,
  sector                TEXT,
  stage                 TEXT,
  last_round_date       DATE,
  last_round_size_usd   BIGINT,
  lead_investor         TEXT,
  headcount_range       TEXT,
  location              TEXT,
  careers_page_url      TEXT,
  intern_hiring_status  TEXT CHECK (intern_hiring_status IN ('hiring', 'open_to', 'not_hiring', 'unknown')),
  one_line_pitch        TEXT,
  source_fund           TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_scraped_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_companies_sector ON companies(sector);
CREATE INDEX IF NOT EXISTS idx_companies_stage ON companies(stage);
CREATE INDEX IF NOT EXISTS idx_companies_intern_hiring ON companies(intern_hiring_status);

-- ============================================================================
-- Alumni table (sparse in v1, populated in Phase 2)
-- ============================================================================
CREATE TABLE IF NOT EXISTS alumni (
  id                BIGSERIAL PRIMARY KEY,
  school_id         BIGINT NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  name              TEXT NOT NULL,
  linkedin_url      TEXT UNIQUE,
  current_company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL,
  role              TEXT,
  graduation_year   INT,
  is_recruiter      BOOLEAN NOT NULL DEFAULT FALSE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_verified_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_alumni_school ON alumni(school_id);
CREATE INDEX IF NOT EXISTS idx_alumni_company ON alumni(current_company_id);

-- ============================================================================
-- Events table (click tracking from day 1)
-- ============================================================================
CREATE TABLE IF NOT EXISTS events (
  id           BIGSERIAL PRIMARY KEY,
  session_id   TEXT NOT NULL,
  school_slug  TEXT NOT NULL,
  event_type   TEXT NOT NULL,
  company_id   BIGINT REFERENCES companies(id) ON DELETE SET NULL,
  payload      JSONB,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_company ON events(company_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at DESC);

-- ============================================================================
-- Convenience view: company + alumni count for dashboard rendering
-- ============================================================================
DROP VIEW IF EXISTS companies_with_alumni;
CREATE VIEW companies_with_alumni AS
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

-- ============================================================================
-- Row Level Security
-- ============================================================================
ALTER TABLE schools  ENABLE ROW LEVEL SECURITY;
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE alumni    ENABLE ROW LEVEL SECURITY;
ALTER TABLE events    ENABLE ROW LEVEL SECURITY;

-- Public read policies
DROP POLICY IF EXISTS "public read schools" ON schools;
CREATE POLICY "public read schools" ON schools FOR SELECT USING (true);

DROP POLICY IF EXISTS "public read companies" ON companies;
CREATE POLICY "public read companies" ON companies FOR SELECT USING (true);

DROP POLICY IF EXISTS "public read alumni" ON alumni;
CREATE POLICY "public read alumni" ON alumni FOR SELECT USING (true);

-- Events: public can insert (for tracking), no public read
DROP POLICY IF EXISTS "public insert events" ON events;
CREATE POLICY "public insert events" ON events FOR INSERT WITH CHECK (true);

-- Service role bypasses RLS automatically; no policies needed for writes from scraper.
