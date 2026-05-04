/**
 * TypeScript types mirroring the Supabase schema. Hand-written for v1.
 * Used for query result type assertions; not wired into the Supabase client
 * itself (the client is untyped in v1 for simplicity).
 *
 * When the schema stabilizes, regenerate via:
 *   npx supabase gen types typescript --project-id <id> > lib/database.ts
 */

export type InternHiringStatus =
  | "hiring"
  | "open_to"
  | "not_hiring"
  | "unknown";

export interface School {
  id: number;
  slug: string;
  name: string;
  domain: string | null;
  active: boolean;
  created_at: string;
}

export interface Company {
  id: number;
  slug: string;
  name: string;
  website: string;
  sector: string | null;
  stage: string | null;
  last_round_date: string | null;
  last_round_size_usd: number | null;
  lead_investor: string | null;
  headcount_range: string | null;
  location: string | null;
  careers_page_url: string | null;
  intern_hiring_status: InternHiringStatus;
  one_line_pitch: string | null;
  long_description: string | null;
  source_fund: string | null;
  founded_year: number | null;
  twitter_url: string | null;
  linkedin_url: string | null;
  tags: string[] | null;
  created_at: string;
  updated_at: string;
  last_scraped_at: string | null;
}

export interface Founder {
  id: number;
  company_id: number;
  name: string;
  title: string | null;
  linkedin_url: string | null;
  bio: string | null;
  created_at: string;
}

export interface CompanyWithAlumni extends Company {
  vandy_alumni_count: number;
}

export interface Alumni {
  id: number;
  school_id: number;
  name: string;
  linkedin_url: string | null;
  current_company_id: number | null;
  role: string | null;
  graduation_year: number | null;
  is_recruiter: boolean;
  created_at: string;
  last_verified_at: string | null;
}

export interface AppEvent {
  id: number;
  session_id: string;
  school_slug: string;
  event_type: string;
  company_id: number | null;
  payload: Record<string, unknown> | null;
  created_at: string;
}
