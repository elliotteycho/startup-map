import Link from "next/link";

import type { CompanyWithAlumni } from "@/lib/types";
import { CompanyAvatar } from "./CompanyAvatar";
import { HiringBadge, SectorBadge, VandyBadge } from "./badges";

const STATUS_ACCENT: Record<string, string> = {
  hiring:     "border-l-emerald-500",
  open_to:    "border-l-amber-400",
  not_hiring: "border-l-slate-700",
  unknown:    "border-l-slate-700",
};

export function CompanyCard({ company: c }: { company: CompanyWithAlumni }) {
  const accent = STATUS_ACCENT[c.intern_hiring_status] ?? "border-l-slate-700";

  return (
    <Link
      href={`/companies/${c.slug}`}
      aria-label={`${c.name}${c.one_line_pitch ? ` — ${c.one_line_pitch}` : ""}`}
      className={`group relative flex h-full flex-col rounded-xl border border-slate-700/40 border-l-[3px] ${accent} bg-slate-900/80 backdrop-blur-sm p-5 transition-all duration-300 hover:-translate-y-1.5 hover:border-slate-600/60 hover:bg-slate-800/90 hover:shadow-2xl hover:shadow-violet-500/10`}
    >
      {/* Header: logo + name + hiring badge (Netflix top-right pattern) */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <CompanyAvatar name={c.name} website={c.website} />
          <div className="min-w-0 pt-0.5">
            <h3 className="font-bold text-base text-white leading-snug group-hover:text-violet-100 transition-colors line-clamp-1">
              {c.name}
            </h3>
            {c.source_fund && (
              <p className="mt-0.5 text-xs text-slate-500 truncate">
                {c.source_fund}
              </p>
            )}
          </div>
        </div>
        {/* Hiring badge top-right — immediately scannable (Airbnb listing badge) */}
        <div className="shrink-0 pt-0.5">
          <HiringBadge status={c.intern_hiring_status} />
        </div>
      </div>

      {/* Pitch — Blinkist clear value prop */}
      {c.one_line_pitch && (
        <p className="mt-3.5 line-clamp-2 text-sm leading-relaxed text-slate-400 group-hover:text-slate-300 transition-colors">
          {c.one_line_pitch}
        </p>
      )}

      {/* Footer */}
      <div className="mt-auto pt-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          {c.location ? (
            <p className="flex items-center gap-1.5 text-xs text-slate-500">
              <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5 shrink-0 text-slate-600" aria-hidden="true">
                <path fillRule="evenodd" d="M9.69 18.933l.003.001C9.89 19.02 10 19 10 19s.11.02.308-.066l.002-.001.006-.003.018-.008a5.741 5.741 0 00.281-.14c.186-.096.446-.24.757-.433.62-.384 1.445-.966 2.274-1.765C15.302 15.57 17 13.216 17 10a7 7 0 10-14 0c0 3.216 1.698 5.57 3.354 7.185a13.045 13.045 0 002.274 1.765 11.169 11.169 0 00.757.433 5.737 5.737 0 00.281.14l.018.008.006.003zM10 12a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
              </svg>
              {c.location}
            </p>
          ) : <span />}
          <div className="flex flex-wrap items-center gap-1.5">
            {c.sector && <SectorBadge sector={c.sector} />}
            {c.vandy_alumni_count > 0 && <VandyBadge count={c.vandy_alumni_count} />}
          </div>
        </div>
      </div>

      {/* Linear-style subtle corner glow on hover */}
      <div className="pointer-events-none absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-br from-violet-500/5 via-transparent to-transparent" aria-hidden="true" />
    </Link>
  );
}
