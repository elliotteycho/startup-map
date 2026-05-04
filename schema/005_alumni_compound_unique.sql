-- Migration 005: Add compound unique constraint to alumni for GitHub upserts
-- Without this, PostgREST rejects on_conflict=school_id,name,current_company_id with HTTP 400.
-- Safe to re-run (IF NOT EXISTS guard on the index).

CREATE UNIQUE INDEX IF NOT EXISTS alumni_school_name_company_uniq
ON alumni(school_id, name, current_company_id);
