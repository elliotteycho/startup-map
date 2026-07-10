import Link from "next/link";
import { notFound } from "next/navigation";

import { supabase } from "@/lib/supabase";
import type {
  Alumni,
  CompanyWithAlumni,
  Founder,
  InternHiringStatus,
} from "@/lib/types";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ slug: string }>;
}

const FETCH_BUDGET_MS = 2500;

function raceWithFallback<T, F>(p: PromiseLike<T>, fallback: F): Promise<T | F> {
  return new Promise<T | F>((resolve) => {
    const t = setTimeout(() => resolve(fallback), FETCH_BUDGET_MS);
    Promise.resolve(p).then(
      (v) => {
        clearTimeout(t);
        resolve(v);
      },
      () => {
        clearTimeout(t);
        resolve(fallback);
      },
    );
  });
}

async function fetchCompany(slug: string): Promise<CompanyWithAlumni | null> {
  const res = await raceWithFallback(
    supabase.from("companies_with_alumni").select("*").eq("slug", slug).maybeSingle(),
    null,
  );
  if (!res) return null;
  return (res.data as CompanyWithAlumni | null) ?? null;
}

async function fetchAlumni(companyId: number): Promise<Alumni[]> {
  const res = await raceWithFallback(
    supabase
      .from("alumni")
      .select("id, name, role, linkedin_url, graduation_year, is_recruiter")
      .eq("current_company_id", companyId)
      .order("graduation_year", { ascending: false }),
    null,
  );
  if (!res) return [];
  return ((res.data as Alumni[] | null) ?? []) as Alumni[];
}

async function fetchFounders(companyId: number): Promise<Founder[]> {
  const res = await raceWithFallback(
    supabase
      .from("founders")
      .select("id, name, title, linkedin_url, bio")
      .eq("company_id", companyId)
      .order("id"),
    null,
  );
  if (!res) return [];
  return ((res.data as Founder[] | null) ?? []) as Founder[];
}

function formatRoundSize(usd: number | null | undefined): string {
  if (!usd || usd <= 0) return "Undisclosed";
  if (usd >= 1_000_000_000) return `$${(usd / 1_000_000_000).toFixed(1)}B`;
  if (usd >= 1_000_000) return `$${(usd / 1_000_000).toFixed(0)}M`;
  return `$${Math.round(usd / 1_000)}K`;
}

function formatMonthYear(iso: string | null): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

const STATUS_LABEL: Record<InternHiringStatus, string> = {
  hiring: "Hiring interns",
  open_to: "Open to interns",
  not_hiring: "Not hiring",
  unknown: "Status unknown",
};

const STATUS_DOT: Record<InternHiringStatus, string> = {
  hiring: "bg-emerald-400",
  open_to: "bg-amber-300",
  not_hiring: "bg-zinc-600",
  unknown: "bg-zinc-700",
};

const STATUS_TEXT: Record<InternHiringStatus, string> = {
  hiring: "text-emerald-300",
  open_to: "text-amber-300",
  not_hiring: "text-zinc-400",
  unknown: "text-zinc-500",
};

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
    /(foundersfund|sequoiacap|khoslaventures|greylock|generalcatalyst|lsvp)\.com/i.test(
      company.website,
    );
  const hasUsableWebsite = !isPlaceholderUrl && !isVCInternalUrl;

  let websiteHostname = "";
  try {
    websiteHostname = new URL(company.website).hostname.replace(/^www\./, "");
  } catch {}

  const initials = company.name
    .split(/\s+/)
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  const status = company.intern_hiring_status;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-amber-300/30 selection:text-amber-50">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-amber-300 focus:px-3 focus:py-2 focus:text-sm focus:font-medium focus:text-zinc-950"
      >
        Skip to content
      </a>

      <nav className="border-b border-zinc-900/80">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-6">
          <Link
            href="/"
            className="flex items-center gap-2 text-[13px] font-medium tracking-tight"
          >
            <span className="grid h-5 w-5 place-items-center rounded-sm bg-amber-300 font-bold text-[10px] text-zinc-950">
              SM
            </span>
            <span className="text-zinc-100">Startup Map</span>
            <span className="ml-1 font-mono text-[10px] uppercase tracking-[0.18em] text-zinc-500">
              v0.4 · beta
            </span>
          </Link>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.18em] text-zinc-400 transition hover:text-amber-300"
          >
            <svg
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              className="h-3.5 w-3.5"
              aria-hidden
            >
              <path
                d="M10 3L5 8l5 5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            All companies
          </Link>
        </div>
      </nav>

      <main id="main">
        {/* ── Hero ───────────────────────────────────────────────── */}
        <section
          aria-label="Company overview"
          className="mx-auto max-w-5xl px-6 pt-16 pb-20 sm:pt-20"
        >
          <div className="grid gap-12 lg:grid-cols-12 lg:gap-16">
            <div className="lg:col-span-8">
              <div className="flex items-center gap-3 font-mono text-[11px] uppercase tracking-[0.18em] text-zinc-500">
                <span className="grid h-9 w-9 place-items-center rounded-md border border-zinc-800/80 bg-zinc-900/60 font-sans text-[13px] font-semibold tracking-tight text-zinc-300">
                  {initials}
                </span>
                <span className="flex items-center gap-2">
                  <span className={`h-1.5 w-1.5 rounded-full ${STATUS_DOT[status]}`} />
                  <span className={STATUS_TEXT[status]}>{STATUS_LABEL[status]}</span>
                </span>
                {company.sector && (
                  <>
                    <span className="text-zinc-700">/</span>
                    <span>{company.sector}</span>
                  </>
                )}
              </div>

              <h1 className="mt-8 text-[44px] font-medium leading-[1.04] tracking-[-0.02em] text-zinc-50 sm:text-[56px] lg:text-[64px]">
                {company.name}
              </h1>

              {company.one_line_pitch && (
                <p className="mt-7 max-w-[55ch] text-[20px] leading-snug tracking-tight text-zinc-300">
                  {company.one_line_pitch}
                </p>
              )}

              {company.long_description &&
                company.long_description !== company.one_line_pitch && (
                  <p className="mt-6 max-w-[62ch] text-[16px] leading-relaxed text-zinc-400">
                    {company.long_description}
                  </p>
                )}

              <div className="mt-9 flex flex-wrap items-center gap-3">
                {company.careers_page_url && (
                  <a
                    href={company.careers_page_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 rounded-md bg-zinc-100 px-4 py-2.5 text-sm font-medium text-zinc-950 transition hover:bg-amber-300"
                  >
                    See open roles
                    <svg
                      viewBox="0 0 16 16"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      className="h-4 w-4"
                      aria-hidden
                    >
                      <path
                        d="M6 3l5 5-5 5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </a>
                )}
                {hasUsableWebsite && (
                  <a
                    href={company.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-2 py-2.5 text-sm font-medium text-zinc-400 transition hover:text-zinc-100"
                  >
                    {websiteHostname}
                    <svg
                      viewBox="0 0 16 16"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      className="h-3.5 w-3.5"
                      aria-hidden
                    >
                      <path
                        d="M5 11l6-6M11 5H5.5M11 5v5.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </a>
                )}
              </div>
            </div>

            {/* Right rail — typographic meta sheet, no card */}
            <aside
              aria-label="Company facts"
              className="lg:col-span-4 lg:border-l lg:border-zinc-900/80 lg:pl-10"
            >
              <dl className="divide-y divide-zinc-900/80">
                <MetaRow label="Stage" value={company.stage} />
                <MetaRow
                  label="Last round"
                  value={
                    company.last_round_size_usd
                      ? formatRoundSize(company.last_round_size_usd)
                      : null
                  }
                  sub={
                    company.last_round_date
                      ? formatMonthYear(company.last_round_date)
                      : null
                  }
                />
                <MetaRow label="Lead investor" value={company.lead_investor} />
                <MetaRow label="Team" value={company.headcount_range} />
                <MetaRow
                  label="Founded"
                  value={
                    company.founded_year ? String(company.founded_year) : null
                  }
                />
                <MetaRow label="HQ" value={company.location} />
                <MetaRow label="Source fund" value={company.source_fund} />
                {company.vandy_alumni_count > 0 && (
                  <MetaRow
                    label="Vandy alumni"
                    value={
                      <span className="text-amber-300">
                        {company.vandy_alumni_count}
                        <span className="ml-1 text-[12px] font-normal text-zinc-500">
                          inside
                        </span>
                      </span>
                    }
                  />
                )}
              </dl>
            </aside>
          </div>
        </section>

        {/* ── Founders ───────────────────────────────────────────── */}
        {founders.length > 0 && (
          <section
            aria-label="Founders"
            className="border-t border-zinc-900/80"
          >
            <div className="mx-auto max-w-5xl px-6 py-20">
              <div className="grid gap-12 lg:grid-cols-12">
                <header className="lg:col-span-4">
                  <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-amber-300">
                    {founders.length === 1 ? "Founder" : "Founders"}
                  </p>
                  <h2 className="mt-3 text-2xl font-medium tracking-tight text-zinc-50 sm:text-3xl">
                    The people running it.
                  </h2>
                  <p className="mt-4 max-w-[40ch] text-[14px] leading-relaxed text-zinc-500">
                    Early-stage means founders are the recruiters. A short, specific
                    message goes further than a polished resume.
                  </p>
                </header>

                <ul className="divide-y divide-zinc-900/80 lg:col-span-8">
                  {founders.map((f) => {
                    const firstName = f.name.split(/\s+/)[0];
                    return (
                      <li key={f.id} className="py-8 first:pt-0 last:pb-0">
                        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                          <h3 className="text-[18px] font-medium tracking-tight text-zinc-100">
                            {f.name}
                          </h3>
                          {f.title && (
                            <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-zinc-500">
                              {f.title}
                            </span>
                          )}
                        </div>
                        {f.bio && (
                          <p className="mt-3 max-w-[62ch] text-[14.5px] leading-relaxed text-zinc-400">
                            {f.bio}
                          </p>
                        )}
                        {f.linkedin_url && (
                          <a
                            href={f.linkedin_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label={`Message ${f.name} on LinkedIn`}
                            className="mt-4 inline-flex items-center gap-1.5 text-[13.5px] font-medium text-zinc-100 transition hover:text-amber-300"
                          >
                            Ask {firstName} for coffee
                            <svg
                              viewBox="0 0 16 16"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="1.5"
                              className="h-3.5 w-3.5"
                              aria-hidden
                            >
                              <path
                                d="M6 3l5 5-5 5"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                              />
                            </svg>
                          </a>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </div>
            </div>
          </section>
        )}

        {/* ── Vandy alumni ───────────────────────────────────────── */}
        <section
          aria-label="Vanderbilt alumni at this company"
          className="border-t border-zinc-900/80"
        >
          <div className="mx-auto max-w-5xl px-6 py-20">
            <div className="grid gap-12 lg:grid-cols-12">
              <header className="lg:col-span-4">
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-amber-300">
                  Vandy on the inside
                </p>
                <h2 className="mt-3 text-2xl font-medium tracking-tight text-zinc-50 sm:text-3xl">
                  Alumni you can actually reach.
                </h2>
                <p className="mt-4 max-w-[40ch] text-[14px] leading-relaxed text-zinc-500">
                  A warm intro through someone who walked your campus is worth ten
                  cold applications.
                </p>
              </header>

              <div className="lg:col-span-8">
                {alumni.length === 0 ? (
                  <p className="max-w-[50ch] text-[14px] leading-relaxed text-zinc-500">
                    No Vanderbilt alumni mapped here yet. If you know someone, the
                    next refresh on Sunday at 2am may catch them.
                  </p>
                ) : (
                  <ul className="divide-y divide-zinc-900/80">
                    {alumni.map((a) => {
                      const firstName = a.name.split(/\s+/)[0];
                      return (
                        <li
                          key={a.id}
                          className="grid grid-cols-12 items-baseline gap-x-4 gap-y-2 py-5 first:pt-0"
                        >
                          <div className="col-span-12 sm:col-span-6">
                            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                              <span className="text-[15px] font-medium tracking-tight text-zinc-100">
                                {a.name}
                              </span>
                              {a.is_recruiter && (
                                <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-amber-300">
                                  Recruiter
                                </span>
                              )}
                            </div>
                            {a.role && (
                              <div className="mt-1 text-[13.5px] text-zinc-400">
                                {a.role}
                              </div>
                            )}
                          </div>
                          <div className="col-span-6 sm:col-span-3">
                            <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-zinc-500 tabular-nums">
                              {a.graduation_year
                                ? `Class of '${String(a.graduation_year).slice(2)}`
                                : "Class unknown"}
                            </span>
                          </div>
                          <div className="col-span-6 flex justify-end sm:col-span-3">
                            {a.linkedin_url ? (
                              <a
                                href={a.linkedin_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                aria-label={`Reach out to ${a.name} on LinkedIn`}
                                className="inline-flex items-center gap-1.5 text-[13px] font-medium text-zinc-100 transition hover:text-amber-300"
                              >
                                Ask {firstName} for coffee
                                <svg
                                  viewBox="0 0 16 16"
                                  fill="none"
                                  stroke="currentColor"
                                  strokeWidth="1.5"
                                  className="h-3.5 w-3.5"
                                  aria-hidden
                                >
                                  <path
                                    d="M6 3l5 5-5 5"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                  />
                                </svg>
                              </a>
                            ) : (
                              <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-zinc-600">
                                No contact
                              </span>
                            )}
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* ── How to apply ───────────────────────────────────────── */}
        <section
          aria-label="How to apply"
          className="border-y border-zinc-900/80 bg-zinc-950"
        >
          <div className="mx-auto max-w-5xl px-6 py-20">
            <div className="grid gap-12 lg:grid-cols-12">
              <header className="lg:col-span-4">
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-amber-300">
                  Get in
                </p>
                <h2 className="mt-3 text-2xl font-medium tracking-tight text-zinc-50 sm:text-3xl">
                  Three ways to land an intro.
                </h2>
                <p className="mt-4 max-w-[40ch] text-[14px] leading-relaxed text-zinc-500">
                  Start with the warmest path. Open roles for clarity, founders for
                  signal, alumni for trust.
                </p>
              </header>

              <ol className="lg:col-span-8">
                {company.careers_page_url && (
                  <ApplyStep
                    n={1}
                    label="Apply directly"
                    detail="See the open roles they're actively recruiting for."
                    href={company.careers_page_url}
                    hrefLabel="Open careers page"
                    highlight
                  />
                )}
                {founders.filter((f) => f.linkedin_url).length > 0 && (
                  <ApplyStep
                    n={company.careers_page_url ? 2 : 1}
                    label="Message a founder"
                    detail={`Short, specific, two lines. Mention you saw their last round and what you'd actually build.`}
                    href={founders.find((f) => f.linkedin_url)!.linkedin_url!}
                    hrefLabel={`DM ${founders.find((f) => f.linkedin_url)!.name.split(/\s+/)[0]}`}
                  />
                )}
                {hasUsableWebsite && (
                  <ApplyStep
                    n={
                      [company.careers_page_url, founders.find((f) => f.linkedin_url)]
                        .filter(Boolean).length + 1
                    }
                    label="Read everything on the site"
                    detail="Then write better than the people who didn't."
                    href={company.website}
                    hrefLabel={websiteHostname || "Visit website"}
                  />
                )}
              </ol>
            </div>

            {isVCInternalUrl && (
              <p className="mt-10 max-w-[60ch] border-l-0 font-mono text-[11px] uppercase tracking-[0.18em] text-amber-300">
                Note · Website points to the VC firm profile. Resolving this on the
                next refresh.
              </p>
            )}
          </div>
        </section>
      </main>

      <footer className="border-t border-zinc-900/80">
        <div className="mx-auto flex max-w-5xl flex-col items-start justify-between gap-3 px-6 py-10 font-mono text-[11px] uppercase tracking-[0.16em] text-zinc-600 sm:flex-row sm:items-center">
          <Link href="/" className="transition hover:text-zinc-300">
            Back to all companies
          </Link>
          <span className="flex items-center gap-5">
            <span>Data refreshed weekly</span>
            <span className="text-zinc-700">v0.4 · beta</span>
          </span>
        </div>
      </footer>
    </div>
  );
}

function MetaRow({
  label,
  value,
  sub,
}: {
  label: string;
  value: React.ReactNode;
  sub?: string | null;
}) {
  const display = value === null || value === undefined || value === "" ? null : value;
  return (
    <div className="flex items-baseline justify-between gap-4 py-3 first:pt-0 last:pb-0">
      <dt className="font-mono text-[11px] uppercase tracking-[0.18em] text-zinc-500">
        {label}
      </dt>
      <dd className="text-right">
        {display === null ? (
          <span className="text-[14px] text-zinc-600">—</span>
        ) : (
          <>
            <span className="text-[14px] font-medium tracking-tight text-zinc-100 tabular-nums">
              {display}
            </span>
            {sub && (
              <span className="ml-2 font-mono text-[11px] uppercase tracking-[0.18em] text-zinc-500 tabular-nums">
                {sub}
              </span>
            )}
          </>
        )}
      </dd>
    </div>
  );
}

function ApplyStep({
  n,
  label,
  detail,
  href,
  hrefLabel,
  highlight,
}: {
  n: number;
  label: string;
  detail: string;
  href: string;
  hrefLabel: string;
  highlight?: boolean;
}) {
  return (
    <li className="grid grid-cols-12 gap-4 border-t border-zinc-900/80 py-8 first:border-t-0 first:pt-0">
      <div className="col-span-2 sm:col-span-1">
        <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-amber-300 tabular-nums">
          {String(n).padStart(2, "0")}
        </span>
      </div>
      <div className="col-span-10 sm:col-span-11">
        <h3 className="text-[17px] font-medium tracking-tight text-zinc-100">
          {label}
        </h3>
        <p className="mt-2 max-w-[58ch] text-[14.5px] leading-relaxed text-zinc-400">
          {detail}
        </p>
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className={`mt-4 inline-flex items-center gap-1.5 text-[13.5px] font-medium transition ${
            highlight
              ? "text-amber-300 hover:text-amber-200"
              : "text-zinc-100 hover:text-amber-300"
          }`}
        >
          {hrefLabel}
          <svg
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            className="h-3.5 w-3.5"
            aria-hidden
          >
            <path d="M5 11l6-6M11 5H5.5M11 5v5.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </a>
      </div>
    </li>
  );
}
