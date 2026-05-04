/**
 * Home page: server-renders the company list, hands off to CompaniesView for
 * client-side filtering and rendering.
 */

import { CompaniesView } from "@/components/CompaniesView";
import { supabase } from "@/lib/supabase";
import type { CompanyWithAlumni } from "@/lib/types";

export const dynamic = "force-dynamic";

async function fetchCompanies(): Promise<CompanyWithAlumni[]> {
  const { data, error } = await supabase
    .from("companies_with_alumni")
    .select("*")
    .order("vandy_alumni_count", { ascending: false })
    .order("name", { ascending: true });

  if (error) {
    // eslint-disable-next-line no-console
    console.error("fetchCompanies failed", error);
    return [];
  }
  return (data ?? []) as CompanyWithAlumni[];
}

export default async function Home() {
  const companies = await fetchCompanies();

  return (
    <div className="min-h-screen bg-zinc-50">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto max-w-7xl px-6 py-10">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center rounded-full bg-yellow-50 px-2.5 py-0.5 text-xs font-semibold text-yellow-800 ring-1 ring-inset ring-yellow-200">
              Beta · for Vanderbilt students
            </span>
          </div>
          <h1 className="mt-3 text-4xl font-bold tracking-tight text-zinc-900 sm:text-5xl">
            The startup map for Vandy.
          </h1>
          <p className="mt-3 max-w-2xl text-base text-zinc-600 sm:text-lg">
            Curated early stage startups vetted for student internships. Filter by sector, hiring status, and Vandy alumni connections. Updated weekly from major VC portfolios.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        <CompaniesView companies={companies} />
      </main>

      <footer className="mx-auto max-w-7xl border-t border-zinc-200 px-6 py-8">
        <div className="flex flex-col items-center justify-between gap-3 text-xs text-zinc-500 sm:flex-row">
          <span>v1 in development · built by a Vandy student, for Vandy students</span>
          <span>Last refreshed: every page load</span>
        </div>
      </footer>
    </div>
  );
}
