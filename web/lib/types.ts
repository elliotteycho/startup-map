/**
 * TypeScript types mirroring the Supabase schema. Hand-written for v1.
 * If the schema grows beyond ~10 tables, generate these via `supabase gen types typescript`.
 */

export type InternHiringStatus =
  | "hiring"
  | "open_to"
  | "not_hiring"
  | "unknown";

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
  source_fund: string | null;
  created_at: string;
  updated_at: string;
  last_scraped_at: string | null;
}

export interface CompanyWithAlumni extends Company {
  vandy_alumni_count: number;
}

export interface Database {
  public: {
    Tables: {
      companies: {
        Row: Company;
        Insert: Omit<Company, "id" | "created_at" | "updated_at">;
        Update: Partial<Omit<Company, "id" | "created_at">>;
      };
    };
    Views: {
      companies_with_alumni: {
        Row: CompanyWithAlumni;
      };
    };
  };
}
