/**
 * Home page: the dashboard. Server-rendered list of all companies, fetched
 * directly from Supabase at request time.
 *
 * This is intentionally minimal in v1. Filters and per-company detail pages
 * come in Tasks #12 and #13.
 */

import { supabase } from "@/lib/supabase";
import type { CompanyWithAlumni } from "@/lib/types";

export const revalidate = 300; // Cache for 5 minutes; scraper runs weekly anyway.

async function fetchCompanies(): Promise<CompanyWithAlumni[]> {
  const { data, error } = await supabase
    .from("companies_with_alumni")
    .select("*")
    .order("name", { ascending: true });

  if (error) {
    // eslint-disable-next-line no-console
    console.error("fetchCompanies failed", error);
    return [];
  }
  return (data ?? []) as CompanyWithAlumni[];
}

function formatRoundSize(usd: number | null): string {
  if (!usd) return "—";
  if (usd >= 1_000_000_000) return `$${(usd / 1_000_000_000).toFixed(1)}B`;
  if (usd >= 1_000_000) return `$${(usd / 1_000_000).toFixed(0)}M`;
  return `$${(usd / 1_000).toFixed(0)}K`;
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    hiring: "bg-emerald-100 text-emerald-800 border-emerald-200",
    open_to: "bg-amber-100 text-amber-800 border-amber-200",
    not_hiring: "bg-zinc-100 text-zinc-600 border-zinc-200",
    unknown: "bg-zinc-50 text-zinc-500 border-zinc-200",
  };
  const label: Record<string, string> = {
    hiring: "Hiring interns",
    open_to: "Open to interns",
    not_hiring: "Not hiring",
    unknown: "Status unknown",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${styles[status] ?? styles.unknown}`}
    >
      {label[status] ?? "Unknown"}
    </span>
  );
}

export default async function Home() {
  const companies = await fetchCompanies();

  return (
    <div className="min-h-screen bg-zinc-50">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto max-w-6xl px-6 py-8">
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">
            Startup Dashboard
          </h1>
          <p className="mt-1 text-sm text-zinc-600">
            Vetted early stage startups for Vanderbilt undergrads. Filter by sector and intern hiring status.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-4 flex items-center justify-between">
          <p className="text-sm text-zinc-600">
            {companies.length} {companies.length === 1 ? "company" : "companies"}
          </p>
        </div>

        {companies.length === 0 ? (
          <div className="rounded-lg border border-dashed border-zinc-300 bg-white p-12 text-center">
            <p className="text-zinc-700">No companies in the database yet.</p>
            <p className="mt-2 text-sm text-zinc-500">
              Run the scraper or insert seed data to populate the dashboard.
            </p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-zinc-200">
              <thead className="bg-zinc-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-zinc-600">
                    Company
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-zinc-600">
                    Sector
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-zinc-600">
                    Stage
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-zinc-600">
                    Last Round
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-zinc-600">
                    Location
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-zinc-600">
                    Hiring
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-zinc-600">
                    Vandy
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 bg-white">
                {companies.map((c) => (
                  <tr key={c.id} className="hover:bg-zinc-50">
                    <td className="px-4 py-4">
                      <div>
                        <a
                          href={c.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-medium text-zinc-900 hover:text-blue-600"
                        >
                          {c.name}
                        </a>
                        {c.one_line_pitch && (
                          <p className="mt-0.5 max-w-md text-sm text-zinc-500">
                            {c.one_line_pitch}
                          </p>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-4 text-sm text-zinc-700">
                      {c.sector ?? "—"}
                    </td>
                    <td className="px-4 py-4 text-sm text-zinc-700">
                      {c.stage ?? "—"}
                    </td>
                    <td className="px-4 py-4 text-sm text-zinc-700">
                      {formatRoundSize(c.last_round_size_usd)}
                    </td>
                    <td className="px-4 py-4 text-sm text-zinc-700">
                      {c.location ?? "—"}
                    </td>
                    <td className="px-4 py-4">
                      <StatusBadge status={c.intern_hiring_status} />
                    </td>
                    <td className="px-4 py-4 text-sm text-zinc-700">
                      {c.vandy_alumni_count > 0 ? (
                        <span className="inline-flex items-center rounded-full bg-yellow-50 px-2.5 py-0.5 text-xs font-medium text-yellow-800 ring-1 ring-yellow-200">
                          {c.vandy_alumni_count} alum{c.vandy_alumni_count === 1 ? "" : "ni"}
                        </span>
                      ) : (
                        <span className="text-zinc-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      <footer className="mx-auto max-w-6xl px-6 py-8 text-center text-xs text-zinc-500">
        v1 in development · built by a Vandy student, for Vandy students
      </footer>
    </div>
  );
}
