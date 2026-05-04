import Link from "next/link";
import { notFound } from "next/navigation";

import { CompanyAvatar } from "@/components/CompanyAvatar";
import { HiringBadge, SectorBadge, VandyBadge } from "@/components/badges";
import { supabase } from "@/lib/supabase";
import type { CompanyWithAlumni, Founder } from "@/lib/types";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ slug: string }>;
}

async function fetchCompany(slug: string): Promise<CompanyWithAlumni | null> {
  const { data } = await supabase
    .from("companies_with_alumni")
    .select("*")
    .eq("slug", slug)
    .maybeSingle();
  return (data as CompanyWithAlumni) ?? null;
}

async function fetchAlumni(companyId: number) {
  const { data } = await supabase
    .from("alumni")
    .select("id, name, role, linkedin_url, graduation_year, is_recruiter")
    .eq("current_company_id", companyId)
    .order("graduation_year", { ascending: false });
  return data ?? [];
}

async function fetchFounders(companyId: number): Promise<Founder[]> {
  const { data } = await supabase
    .from("founders")
    .select("id, name, title, linkedin_url, bio")
    .eq("company_id", companyId)
    .order("id");
  return (data ?? []) as Founder[];
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

  const [alumni, founders] = await Promise.all([
    fetchAlumni(company.id),
    fetchFounders(company.id),
  ]);

  const isPlaceholderUrl = company.website.includes("no-url.placeholder");
  const isVCInternalUrl =
    !isPlaceholderUrl &&
    /(foundersfund|sequoiacap|khoslaventures|greylock|generalcatalyst|lsvp)\.com/i.test(company.website);

  let websiteHostname = "";
  try { websiteHostname = new URL(company.website).hostname.replace("www.", ""); } catch {}

  const hasStats = company.stage || company.last_round_size_usd || company.headcount_range || company.founded_year;
  const tags = (company.tags ?? []).slice(0, 6);

  return (
    <div className="relative min-h-screen bg-slate-950 text-slate-100">
      {/* Background gradient orbs */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden="true">
        <div className="absolute -top-48 left-1/2 h-[600px] w-[900px] -translate-x-1/2 rounded-full bg-violet-600/15 blur-[140px]" />
        <div className="absolute top-1/3 -right-32 h-[400px] w-[400px] rounded-full bg-emerald-500/8 blur-[120px]" />
        <div className="absolute bottom-0 -left-32 h-[400px] w-[400px] rounded-full bg-indigo-600/10 blur-[120px]" />
      </div>

      <header className="relative border-b border-slate-800/60 bg-slate-950/80 backdrop-blur-sm">
        <div className="mx-auto max-w-5xl px-6 py-4">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-100 transition-colors"
          >
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
              <path fillRule="evenodd" d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z" clipRule="evenodd" />
            </svg>
            All companies
          </Link>
        </div>
      </header>

      <main className="relative mx-auto max-w-5xl px-6 py-10 space-y-5">

        {/* ── Hero ──────────────────────────────────────────────── */}
        <section className="rounded-2xl border border-slate-700/40 bg-slate-900/80 backdrop-blur-sm p-8">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-start">
            <CompanyAvatar name={company.name} website={company.website} size="lg" />
            <div className="min-w-0 flex-1">

              {/* Name row + hiring badge */}
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
                    {company.name}
                  </h1>
                  <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-slate-400">
                    {company.founded_year && <span>Founded {company.founded_year}</span>}
                    {company.founded_year && company.location && <span className="text-slate-600">·</span>}
                    {company.location && <span>{company.location}</span>}
                    {(company.founded_year || company.location) && company.source_fund && (
                      <span className="text-slate-600">·</span>
                    )}
                    {company.source_fund && <span>{company.source_fund}</span>}
                  </div>
                </div>
                <HiringBadge status={company.intern_hiring_status} />
              </div>

              {/* One-liner (short pitch) */}
              {company.one_line_pitch && (
                <p className="mt-3 text-lg font-medium text-slate-200 leading-snug">
                  {company.one_line_pitch}
                </p>
              )}

              {/* Long description */}
              {company.long_description && company.long_description !== company.one_line_pitch && (
                <p className="mt-2 text-sm leading-relaxed text-slate-400">
                  {company.long_description}
                </p>
              )}

              {/* Badges + social row */}
              <div className="mt-4 flex flex-wrap items-center gap-2">
                {company.sector && <SectorBadge sector={company.sector} />}
                {company.vandy_alumni_count > 0 && <VandyBadge count={company.vandy_alumni_count} />}
                {tags.map(tag => (
                  <span key={tag} className="rounded-full border border-slate-700/50 bg-slate-800/60 px-2.5 py-0.5 text-xs text-slate-400">
                    {tag}
                  </span>
                ))}
              </div>

              {/* Social links */}
              {(company.twitter_url || company.linkedin_url || (!isPlaceholderUrl && !isVCInternalUrl)) && (
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  {!isPlaceholderUrl && !isVCInternalUrl && (
                    <SocialLink href={company.website} label="Website">
                      <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5"><path fillRule="evenodd" d="M4.083 9h1.946c.089-1.546.383-2.97.837-4.118A6.004 6.004 0 004.083 9zM10 2a8 8 0 100 16A8 8 0 0010 2zm0 2c-.076 0-.232.032-.465.262-.238.234-.497.623-.737 1.182-.389.907-.673 2.142-.766 3.556h3.936c-.093-1.414-.377-2.649-.766-3.556-.24-.56-.5-.948-.737-1.182C10.232 4.032 10.076 4 10 4zm3.971 5c-.089-1.546-.383-2.97-.837-4.118A6.004 6.004 0 0115.917 9h-1.946zm-2.003 2H8.032c.093 1.414.377 2.649.766 3.556.24.56.5.948.737 1.182.233.23.389.262.465.262.076 0 .232-.032.465-.262.238-.234.498-.623.737-1.182.389-.907.673-2.142.766-3.556zm1.166 4.118c.454-1.147.748-2.572.837-4.118h1.946a6.004 6.004 0 01-2.783 4.118zm-6.268 0C6.412 13.97 6.118 12.546 6.03 11H4.083a6.004 6.004 0 002.783 4.118z" clipRule="evenodd" /></svg>
                      {websiteHostname}
                    </SocialLink>
                  )}
                  {company.twitter_url && (
                    <SocialLink href={company.twitter_url} label="Twitter/X">
                      <svg viewBox="0 0 24 24" fill="currentColor" className="h-3.5 w-3.5"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                      Twitter
                    </SocialLink>
                  )}
                  {company.linkedin_url && (
                    <SocialLink href={company.linkedin_url} label="LinkedIn">
                      <svg viewBox="0 0 24 24" fill="currentColor" className="h-3.5 w-3.5"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                      LinkedIn
                    </SocialLink>
                  )}
                  {company.careers_page_url && (
                    <SocialLink href={company.careers_page_url} label="Careers" highlight>
                      <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5"><path fillRule="evenodd" d="M6 6V5a3 3 0 013-3h2a3 3 0 013 3v1h2a2 2 0 012 2v3.57A22.952 22.952 0 0110 13a22.95 22.95 0 01-8-1.43V8a2 2 0 012-2h2zm2-1a1 1 0 011-1h2a1 1 0 011 1v1H8V5zm1 5a1 1 0 011-1h.01a1 1 0 110 2H10a1 1 0 01-1-1z" clipRule="evenodd" /><path d="M2 13.692V16a2 2 0 002 2h12a2 2 0 002-2v-2.308A24.974 24.974 0 0110 15c-2.796 0-5.487-.46-8-1.308z" /></svg>
                      Open roles
                    </SocialLink>
                  )}
                </div>
              )}
            </div>
          </div>
        </section>

        {/* ── Stats row (only if we have data) ──────────────────── */}
        {hasStats && (
          <section className="grid grid-cols-2 gap-3 sm:grid-cols-4" aria-label="Company stats">
            <Fact label="Stage"     value={company.stage ?? "—"} />
            <Fact
              label="Last round"
              value={formatRoundSize(company.last_round_size_usd)}
              sub={company.last_round_date ? formatDate(company.last_round_date) : undefined}
            />
            <Fact label="Team size" value={company.headcount_range ?? "—"} />
            <Fact label="Founded"   value={company.founded_year ? String(company.founded_year) : "—"} />
          </section>
        )}

        {/* ── Founders ──────────────────────────────────────────── */}
        {founders.length > 0 && (
          <section className="rounded-2xl border border-slate-700/40 bg-slate-900/80 backdrop-blur-sm p-6">
            <h2 className="text-base font-semibold text-slate-100">
              {founders.length === 1 ? "Founder" : "Founders"}
            </h2>
            <ul className="mt-4 divide-y divide-slate-800/60">
              {founders.map((f) => (
                <li key={f.id} className="py-5 first:pt-0 last:pb-0">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-white">{f.name}</span>
                        {f.title && (
                          <span className="text-xs text-slate-400 bg-slate-800 px-2 py-0.5 rounded-md">
                            {f.title}
                          </span>
                        )}
                      </div>
                      {f.bio && (
                        <p className="mt-2 text-sm leading-relaxed text-slate-400 max-w-2xl">{f.bio}</p>
                      )}
                    </div>
                    {f.linkedin_url && (
                      <a
                        href={f.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        aria-label={`${f.name} on LinkedIn`}
                        className="shrink-0 flex items-center gap-1.5 rounded-lg border border-slate-700/60 px-3 py-1.5 text-xs font-medium text-slate-300 hover:border-violet-500/40 hover:text-violet-300 hover:bg-violet-500/10 transition-all"
                      >
                        <svg viewBox="0 0 24 24" fill="currentColor" className="h-3.5 w-3.5" aria-hidden="true">
                          <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                        </svg>
                        LinkedIn
                      </a>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* ── Bottom row: reach out + vandy ─────────────────────── */}
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">

          {/* How to reach them */}
          <section className="rounded-2xl border border-slate-700/40 bg-slate-900/80 backdrop-blur-sm p-6 lg:col-span-2">
            <h2 className="text-base font-semibold text-slate-100">How to reach them</h2>
            <p className="mt-1 text-sm text-slate-500">Best paths to get on their radar.</p>

            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {company.careers_page_url && (
                <ApplyLink
                  label="Browse open roles"
                  href={company.careers_page_url}
                  description="See what they're hiring for"
                  highlight
                />
              )}

              {founders.filter(f => f.linkedin_url).map(f => (
                <ApplyLink
                  key={f.id}
                  label={`Message ${f.name.split(" ")[0]}`}
                  href={f.linkedin_url!}
                  description={f.title ?? "Founder · LinkedIn DM"}
                />
              ))}

              {company.twitter_url && (
                <ApplyLink
                  label="Follow on Twitter"
                  href={company.twitter_url}
                  description="See what they're building in public"
                />
              )}

              {!isPlaceholderUrl && !isVCInternalUrl && (
                <ApplyLink
                  label="Company website"
                  href={company.website}
                  description={websiteHostname}
                />
              )}
            </div>

            {isVCInternalUrl && (
              <p className="mt-3 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-sm text-amber-300">
                Website points to the VC firm profile, not the company — working on resolving this.
              </p>
            )}
          </section>

          {/* Vandy connections */}
          <section className="rounded-2xl border border-slate-700/40 bg-slate-900/80 backdrop-blur-sm p-6">
            <h2 className="text-base font-semibold text-slate-100">Vandy connections</h2>
            <p className="mt-1 text-sm text-slate-500">Alumni currently at this company.</p>

            {alumni.length === 0 ? (
              <div className="mt-4 rounded-lg border border-dashed border-slate-700/60 p-4 text-center">
                <p className="text-sm text-slate-500">No Vanderbilt alumni found here yet.</p>
              </div>
            ) : (
              <ul className="mt-4 space-y-3">
                {alumni.map((a) => (
                  <li key={a.id} className="flex items-start justify-between gap-3">
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
          </section>
        </div>

      </main>
    </div>
  );
}

function Fact({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-slate-700/40 bg-slate-900/80 p-4">
      <div className="text-xs uppercase tracking-wider text-slate-500">{label}</div>
      <div className="mt-1 text-lg font-semibold text-slate-100">{value}</div>
      {sub && <div className="mt-0.5 text-xs text-slate-500">{sub}</div>}
    </div>
  );
}

function SocialLink({
  href, label, children, highlight,
}: {
  href: string;
  label: string;
  children: React.ReactNode;
  highlight?: boolean;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={label}
      className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-all ${
        highlight
          ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20"
          : "border-slate-700/50 bg-slate-800/50 text-slate-300 hover:border-slate-600 hover:text-slate-100"
      }`}
    >
      {children}
    </a>
  );
}

function ApplyLink({
  label, href, description, highlight,
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
      className={`flex items-center justify-between rounded-xl border p-4 transition-all ${
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
      <svg viewBox="0 0 20 20" fill="currentColor" className={`h-4 w-4 shrink-0 ${highlight ? "text-emerald-400" : "text-slate-500"}`} aria-hidden="true">
        <path fillRule="evenodd" d="M5.22 14.78a.75.75 0 001.06 0l7.22-7.22v5.69a.75.75 0 001.5 0V5.25a.75.75 0 00-.75-.75H8.31a.75.75 0 000 1.5h5.69l-7.22 7.22a.75.75 0 000 1.06z" clipRule="evenodd" />
      </svg>
    </a>
  );
}
