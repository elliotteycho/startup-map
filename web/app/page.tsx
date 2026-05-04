import { DashboardShell } from "@/components/DashboardShell";
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
    console.error("fetchCompanies failed", error);
    return [];
  }
  return (data ?? []) as CompanyWithAlumni[];
}

export default async function Home() {
  const companies = await fetchCompanies();

  return (
    <div className="min-h-screen bg-zinc-50">
      {/* ── Hero ───────────────────────────────────────────────── */}
      <header className="relative overflow-hidden bg-zinc-950">
        {/* Glow layers */}
        <div className="pointer-events-none absolute -top-32 left-1/2 h-[500px] w-[900px] -translate-x-1/2 rounded-full bg-violet-600/25 blur-[120px]" />
        <div className="pointer-events-none absolute top-0 right-0 h-72 w-72 bg-emerald-500/10 blur-[90px]" />
        <div className="pointer-events-none absolute bottom-0 left-0 h-48 w-48 bg-yellow-500/8 blur-[80px]" />

        <div className="relative mx-auto max-w-7xl px-6 pt-10">
          {/* Brand mark */}
          <div className="flex items-center gap-2">
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4 text-yellow-400">
              <path fillRule="evenodd" d="M9.69 18.933l.003.001C9.89 19.02 10 19 10 19s.11.02.308-.066l.002-.001.006-.003.018-.008a5.741 5.741 0 00.281-.14c.186-.096.446-.24.757-.433.62-.384 1.445-.966 2.274-1.765C15.302 15.57 17 13.216 17 10a7 7 0 10-14 0c0 3.216 1.698 5.57 3.354 7.185a13.045 13.045 0 002.274 1.765 11.169 11.169 0 00.757.433 5.737 5.737 0 00.281.14l.018.008.006.003zM10 12a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
            </svg>
            <span className="text-xs font-bold uppercase tracking-[0.18em] text-zinc-500">
              Startup Map
            </span>
            <span className="ml-1 inline-flex items-center rounded-full bg-yellow-400/10 px-2.5 py-0.5 text-xs font-semibold text-yellow-400 ring-1 ring-inset ring-yellow-400/20">
              Beta
            </span>
          </div>

          <h1 className="mt-5 text-5xl font-bold tracking-tight sm:text-6xl lg:text-7xl">
            <span className="bg-gradient-to-br from-white via-zinc-100 to-zinc-500 bg-clip-text text-transparent">
              Find your first
              <br />
              startup.
            </span>
          </h1>

          <p className="mt-5 max-w-xl text-base text-zinc-400 sm:text-lg">
            Curated early-stage companies from top VC portfolios and YC —
            filtered for Vanderbilt students looking for internships.
          </p>
        </div>
      </header>

      {/* ── Stats + filters + grid (client, shares state) ──────── */}
      <DashboardShell companies={companies} />

      <footer className="mx-auto max-w-7xl border-t border-zinc-200 px-6 py-8">
        <div className="flex flex-col items-center justify-between gap-3 text-xs text-zinc-400 sm:flex-row">
          <span className="flex items-center gap-1.5">
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5 text-yellow-400">
              <path fillRule="evenodd" d="M9.69 18.933l.003.001C9.89 19.02 10 19 10 19s.11.02.308-.066l.002-.001.006-.003.018-.008a5.741 5.741 0 00.281-.14c.186-.096.446-.24.757-.433.62-.384 1.445-.966 2.274-1.765C15.302 15.57 17 13.216 17 10a7 7 0 10-14 0c0 3.216 1.698 5.57 3.354 7.185a13.045 13.045 0 002.274 1.765 11.169 11.169 0 00.757.433 5.737 5.737 0 00.281.14l.018.008.006.003zM10 12a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
            </svg>
            Startup Map · built by a Vandy student, for Vandy students
          </span>
          <span>Data refreshed weekly · v1 beta</span>
        </div>
      </footer>
    </div>
  );
}
