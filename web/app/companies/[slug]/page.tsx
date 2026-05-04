import Link from "next/link";
import { notFound } from "next/navigation";

import { CompanyAvatar } from "@/components/CompanyAvatar";
import { HiringBadge, SectorBadge, VandyBadge } from "@/components/badges";
import { supabase } from "@/lib/supabase";
import type { CompanyWithAlumni } from "@/lib/types";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ slug: string }>;
}

async function fetchCompany(slug: string): Promise<CompanyWithAlumni | null> {
  const { data, error } = await supabase
    .from("companies_with_alumni")
    .select("*")
    .eq("slug", slug)
    .order("id")
    .limit(1);
  if (error || !data?.length) return null;
  return data[0] as CompanyWithAlumni;
}

async function fetchAlumni(companyId: number) {
  const { data, error } = await supabase
    .from("alumni")
    .select("name, role, linkedin_url, graduation_year, is_recruiter")
    .eq("current_company_id", companyId)
    .order("graduation_year", { ascending: false });
  if (error) return [];
  return data ?? [];
}

function formatRoundSize(usd: number | null): string {
  if (!usd) return "—";
  if (usd >= 1_000_000_000) return `$${(usd / 1_000_000_000).toFixed(1)}B`;
  if (usd >= 1_000_000) return `$${(usd / 1_000_000).toFixed(0)}M`;
  return `$${(usd / 1_000).toFixed(0)}K`;
}

function formatDate(d: string | null): string {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleDateString("en-US", { year: "numeric", month: "short" });
  } catch {
    return d;
  }
}

export default async function CompanyDetail({ params }: Props) {
  const { slug } = await params;
  if (!slug) notFound();

  const company = await fetchCompany(slug);
  if (!company) notFound();

  const alumni = await fetchAlumni(company.id);

  const isPlaceholderUrl = company.website.includes("no-url.placeholder");
  const isVCInternalUrl =
    !isPlaceholderUrl &&
    /(foundersfund|sequoiacap|khoslaventures|greylock|generalcatalyst|lsvp)\.com/i.test(
      company.website,
    );

  return (
    <div className="relative min-h-screen bg-slate-950 text-slate-100">
      {/* Background gradient orbs */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-48 left-1/2 h-[600px] w-[900px] -translate-x-1/2 rounded-full bg-violet-600/15 blur-[140px]" />
        <div className="absolute top-1/3 -right-32 h-[400px] w-[400px] rounded-full bg-emerald-500/8 blur-[120px]" />
        <div className="absolute bottom-0 -left-32 h-[400px] w-[400px] rounded-full bg-indigo-600/10 blur-[120px]" />
      </div>

      <header className="relative border-b border-slate-800/60 bg-slate-950/80 backdrop-blur-sm">
        <div className="mx-auto max-w-5xl px-6 py-4">
          <Link
            href="/"
            className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-slate-100 transition-colors"
          >
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
              <path
                fillRule="evenodd"
                d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z"
                clipRule="evenodd"
              />
            </svg>
            Back to all companies
          </Link>
        </div>
      </header>

      <main className="relative mx-auto max-w-5xl px-6 py-10">
        <section className="rounded-2xl border border-slate-700/40 bg-slate-900/80 backdrop-blur-sm p-8">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-start">
            <CompanyAvatar name={company.name} website={company.website} size="lg" />
            <div className="min-w-0 flex-1">
              <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
                {company.name}
              </h1>
              {company.one_line_pitch && (
                <p className="mt-2 text-lg leading-relaxed text-slate-300">
                  {company.one_line_pitch}
                </p>
              )}
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <HiringBadge status={company.intern_hiring_status} />
                {company.sector && <SectorBadge sector={company.sector} />}
                {company.vandy_alumni_count > 0 && (
                  <VandyBadge count={company.vandy_alumni_count} />
                )}
              </div>
            </div>
          </div>
        </section>

        <section className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Fact label="Stage" value={company.stage ?? "—"} />
          <Fact
            label="Last round"
            value={formatRoundSize(company.last_round_size_usd)}
            sub={company.last_round_date ? formatDate(company.last_round_date) : undefined}
          />
          <Fact label="Headcount" value={company.headcount_range ?? "—"} />
          <Fact label="Location" value={company.location ?? "Remote / unknown"} />
        </section>

        <section className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="rounded-2xl border border-slate-700/40 bg-slate-900/80 backdrop-blur-sm p-6 lg:col-span-2">
            <h2 className="text-base font-semibold text-slate-100">How to reach them</h2>
            <p className="mt-1 text-sm text-slate-400">
              Direct paths to apply or learn more.
            </p>

            <div className="mt-4 space-y-3">
              {!isPlaceholderUrl && !isVCInternalUrl && (
                <ApplyLink
                  label="Visit company website"
                  href={company.website}
                  description={new URL(company.website).hostname.replace("www.", "")}
                />
              )}

              {isVCInternalUrl && (
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-sm text-amber-300">
                  <strong>Heads up:</strong> the link below points to the VC firm&apos;s profile of this company, not the company&apos;s own site. We are working on automated link resolution.
                  <ApplyLink
                    label="View on VC firm site"
                    href={company.website}
                    description={new URL(company.website).hostname.replace("www.", "")}
                  />
                </div>
              )}

              {company.careers_page_url && (
                <ApplyLink
                  label="Open careers page"
                  href={company.careers_page_url}
                  description="Look for internship listings"
                  highlight
                />
              )}

              {company.source_fund && (
                <div className="rounded-lg border border-slate-700/40 bg-slate-800/60 p-3">
                  <div className="text-xs uppercase tracking-wider text-slate-500">Backed by</div>
                  <div className="mt-1 text-sm font-medium text-slate-200">{company.source_fund}</div>
                </div>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-700/40 bg-slate-900/80 backdrop-blur-sm p-6">
            <h2 className="text-base font-semibold text-slate-100">Vandy connections</h2>
            <p className="mt-1 text-sm text-slate-400">
              Alumni currently at this company.
            </p>

            {alumni.length === 0 ? (
              <div className="mt-4 rounded-lg border border-dashed border-slate-700 p-4 text-center">
                <p className="text-sm text-slate-400">No mapped alumni yet.</p>
                <p className="mt-1 text-xs text-slate-500">
                  Alumni mapping rolls out in Phase 2.
                </p>
              </div>
            ) : (
              <ul className="mt-4 space-y-3">
                {alumni.map((a, i) => (
                  <li key={i} className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-slate-200">{a.name}</div>
                      <div className="text-xs text-slate-400">
                        {a.role ?? "—"}
                        {a.graduation_year ? ` · '${String(a.graduation_year).slice(2)}` : ""}
                      </div>
                    </div>
                    {a.linkedin_url && (
                      <a
                        href={a.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="shrink-0 text-xs font-medium text-violet-400 hover:text-violet-300 transition-colors"
                      >
                        LinkedIn ↗
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        <section className="mt-6 rounded-2xl border border-slate-700/40 bg-slate-900/80 backdrop-blur-sm p-6">
          <h2 className="text-base font-semibold text-slate-100">Data freshness</h2>
          <p className="mt-2 text-sm text-slate-400">
            Last scraped: {company.last_scraped_at ? formatDate(company.last_scraped_at) : "Never"}.
            Source: {company.source_fund ? `${company.source_fund} portfolio page` : "manual entry"}.
          </p>
          <p className="mt-3 text-xs text-slate-500">
            Found a problem with this listing? <Link href="/" className="text-violet-400 hover:text-violet-300 underline transition-colors">Go back</Link> and let us know.
          </p>
        </section>
      </main>
    </div>
  );
}

function Fact({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-slate-700/40 bg-slate-900/80 p-4">
      <div className="text-xs uppercase tracking-wider text-slate-500">{label}</div>
      <div className="mt-1 text-base font-semibold text-slate-100">{value}</div>
      {sub && <div className="mt-0.5 text-xs text-slate-500">{sub}</div>}
    </div>
  );
}

function ApplyLink({
  label,
  href,
  description,
  highlight,
}: {
  label: string;
  href: string;
  description: string;
  highlight?: boolean;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={`flex items-center justify-between rounded-lg border p-3 transition-all ${
        highlight
          ? "border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/15"
          : "border-slate-700/40 bg-slate-800/40 hover:bg-slate-800/80"
      }`}
    >
      <div>
        <div className={`text-sm font-medium ${highlight ? "text-emerald-300" : "text-slate-200"}`}>
          {label}
        </div>
        <div className={`mt-0.5 text-xs ${highlight ? "text-emerald-400/70" : "text-slate-500"}`}>
          {description}
        </div>
      </div>
      <svg
        viewBox="0 0 20 20"
        fill="currentColor"
        className={`h-4 w-4 shrink-0 ${highlight ? "text-emerald-400" : "text-slate-500"}`}
      >
        <path
          fillRule="evenodd"
          d="M5.22 14.78a.75.75 0 001.06 0l7.22-7.22v5.69a.75.75 0 001.5 0V5.25a.75.75 0 00-.75-.75H8.31a.75.75 0 000 1.5h5.69l-7.22 7.22a.75.75 0 000 1.06z"
          clipRule="evenodd"
        />
      </svg>
    </a>
  );
}
