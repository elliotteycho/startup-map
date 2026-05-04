-- Migration 002: Development seed data
-- Six realistic-looking sample companies so the dashboard renders with data
-- before the scraper is wired up. Safe to delete (or re-run) once the scraper
-- populates real entries.

INSERT INTO companies (
  slug, name, website, sector, stage,
  last_round_date, last_round_size_usd, lead_investor,
  headcount_range, location, careers_page_url,
  intern_hiring_status, one_line_pitch, source_fund
) VALUES
  ('anthropic', 'Anthropic', 'https://anthropic.com', 'AI', 'Series E',
   '2025-08-01', 4000000000, 'Lightspeed', '500-1000', 'San Francisco, CA',
   'https://anthropic.com/careers', 'hiring',
   'AI safety company building reliable, interpretable AI systems.', 'Lightspeed'),
  ('ramp', 'Ramp', 'https://ramp.com', 'Fintech', 'Series D',
   '2024-04-01', 150000000, 'Khosla Ventures', '500-1000', 'New York, NY',
   'https://ramp.com/careers', 'hiring',
   'Corporate cards and spend management built to save companies time and money.', 'Founders Fund'),
  ('linear', 'Linear', 'https://linear.app', 'Enterprise', 'Series C',
   '2024-09-01', 80000000, 'Accel', '50-200', 'Remote',
   'https://linear.app/careers', 'open_to',
   'The issue tracking tool youll enjoy using.', 'Accel'),
  ('mercury', 'Mercury', 'https://mercury.com', 'Fintech', 'Series C',
   '2024-07-01', 120000000, 'Sequoia Capital', '500-1000', 'San Francisco, CA',
   'https://mercury.com/jobs', 'hiring',
   'Banking built for startups.', 'Andreessen Horowitz'),
  ('vercel', 'Vercel', 'https://vercel.com', 'Enterprise', 'Series E',
   '2024-05-01', 250000000, 'Accel', '500-1000', 'San Francisco, CA',
   'https://vercel.com/careers', 'hiring',
   'Frontend cloud platform for developers building modern web apps.', 'Accel'),
  ('replit', 'Replit', 'https://replit.com', 'AI', 'Series B',
   '2025-09-01', 250000000, 'Andreessen Horowitz', '200-500', 'San Francisco, CA',
   'https://replit.com/site/careers', 'hiring',
   'Build software collaboratively from anywhere using AI agents.', 'Andreessen Horowitz')
ON CONFLICT (website) DO NOTHING;

-- Seed a few Vandy alumni so the badge logic shows something
INSERT INTO alumni (school_id, name, linkedin_url, current_company_id, role, graduation_year, is_recruiter)
SELECT
  (SELECT id FROM schools WHERE slug = 'vanderbilt'),
  'Sample Alum',
  'https://linkedin.com/in/sample-alum-' || c.slug,
  c.id,
  'Software Engineer',
  2023,
  FALSE
FROM companies c
WHERE c.slug IN ('ramp', 'linear', 'mercury')
ON CONFLICT (linkedin_url) DO NOTHING;
