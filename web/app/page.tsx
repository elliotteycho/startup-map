import { DashboardShell } from "@/components/DashboardShell";
import { supabase } from "@/lib/supabase";
import type { CompanyWithAlumni } from "@/lib/types";

export const dynamic = "force-dynamic";

async function fetchCompanies(): Promise<{ companies: CompanyWithAlumni[]; loadError: boolean }> {
  const { data, error } = await supabase
    .from("companies_with_alumni")
    .select("id, slug, name, website, sector, one_line_pitch, intern_hiring_status, location, source_fund, vandy_alumni_count")
    .order("vandy_alumni_count", { ascending: false })
    .order("name", { ascending: true });

  if (error) {
    console.error("fetchCompanies failed", error);
    return { companies: [], loadError: true };
  }
  return { companies: (data ?? []) as CompanyWithAlumni[], loadError: false };
}

export default async function Home() {
  const { companies, loadError } = await fetchCompanies();

  return (
    <div className="relative min-h-screen bg-slate-950 text-slate-100">
      {/* Persistent full-page gradient orbs */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden="true">
        <div className="absolute -top-48 left-1/2 h-[700px] w-[1100px] -translate-x-1/2 rounded-full bg-violet-600/20 blur-[150px]" />
        <div className="absolute top-1/4 -right-32 h-[500px] w-[500px] rounded-full bg-emerald-500/10 blur-[120px]" />
        <div className="absolute top-1/2 -left-32 h-[450px] w-[450px] rounded-full bg-indigo-600/12 blur-[120px]" />
        <div className="absolute bottom-0 left-1/2 h-[400px] w-[700px] -translate-x-1/2 rounded-full bg-violet-700/10 blur-[120px]" />
      </div>

      {/* Skip to content — GOV.UK accessibility pattern */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-violet-600 focus:px-4 focus:py-2 focus:text-white focus:text-sm focus:font-medium"
      >
        Skip to content
      </a>

      {/* ── Hero ───────────────────────────────────────────────── */}
      <header className="relative">
        <div className="relative mx-auto max-w-7xl px-6 pt-16 pb-12">
          {/* Brand mark */}
          <div className="flex items-center gap-2.5">
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4 text-yellow-400" aria-hidden="true">
              <path fillRule="evenodd" d="M9.69 18.933l.003.001C9.89 19.02 10 19 10 19s.11.02.308-.066l.002-.001.006-.003.018-.008a5.741 5.741 0 00.281-.14c.186-.096.446-.24.757-.433.62-.384 1.445-.966 2.274-1.765C15.302 15.57 17 13.216 17 10a7 7 0 10-14 0c0 3.216 1.698 5.57 3.354 7.185a13.045 13.045 0 002.274 1.765 11.169 11.169 0 00.757.433 5.737 5.737 0 00.281.14l.018.008.006.003zM10 12a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
            </svg>
            <span className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">
              Startup Map
            </span>
            <span className="inline-flex items-center rounded-full bg-yellow-400/10 px-2.5 py-0.5 text-xs font-semibold text-yellow-400 ring-1 ring-inset ring-yellow-400/20">
              Beta
            </span>
          </div>

          {/* Headline — Zara editorial scale */}
          <h1 className="mt-6 max-w-3xl text-5xl font-bold tracking-tight sm:text-6xl lg:text-7xl xl:text-8xl">
            <span className="bg-gradient-to-br from-white via-violet-200 to-violet-500 bg-clip-text text-transparent leading-[1.08]">
              Find your first
              <br />
              startup.
            </span>
          </h1>

          {/* Divider — Blinkist structural clarity */}
          <div className="mt-8 h-px w-16 bg-gradient-to-r from-violet-500 to-transparent" aria-hidden="true" />

          <p className="mt-6 max-w-lg text-base text-slate-400 sm:text-lg leading-relaxed">
            Curated early stage companies from top VC portfolios and YC,
            filtered for Vanderbilt students looking for internships.
          </p>
        </div>
      </header>

      {/* ── Dashboard ──────────────────────────────────────────── */}
      <main id="main-content">
        {loadError ? (
          <div className="mx-auto max-w-7xl px-6 pb-12">
            <div
              className="rounded-2xl border border-amber-400/20 bg-amber-400/[0.04] p-12 text-center"
              role="alert"
            >
              <p className="font-medium text-amber-200">
                We couldn&apos;t load companies right now.
              </p>
              <p className="mt-2 text-sm text-slate-400">
                This is a temporary issue on our end, not an empty list. Please
                refresh in a moment.
              </p>
            </div>
          </div>
        ) : (
          <DashboardShell companies={companies} />
        )}
      </main>

      <footer className="relative mx-auto max-w-7xl border-t border-slate-800/60 px-6 py-8">
        <div className="flex flex-col items-center justify-between gap-3 text-xs text-slate-600 sm:flex-row">
          <span className="flex items-center gap-1.5">
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5 text-yellow-400" aria-hidden="true">
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
