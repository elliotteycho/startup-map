import Link from "next/link";

import type { CompanyWithAlumni } from "@/lib/types";
import { CompanyAvatar } from "./CompanyAvatar";
import { HiringBadge, SectorBadge, VandyBadge } from "./badges";

const STATUS_ACCENT: Record<string, string> = {
  hiring:     "border-l-emerald-500",
  open_to:    "border-l-amber-400",
  not_hiring: "border-l-zinc-200",
  unknown:    "border-l-zinc-200",
};

export function CompanyCard({ company: c }: { company: CompanyWithAlumni }) {
  const accent = STATUS_ACCENT[c.intern_hiring_status] ?? "border-l-zinc-200";

  return (
    <Link
      href={`/companies/${c.slug}`}
      className={`group flex h-full flex-col rounded-xl border border-zinc-200 border-l-[3px] ${accent} bg-white p-5 transition-all duration-200 hover:-translate-y-1 hover:shadow-lg hover:shadow-zinc-200/80`}
    >
      {/* Header row */}
      <div className="flex items-start gap-3">
        <CompanyAvatar name={c.name} website={c.website} />
        <div className="min-w-0 flex-1">
          <h3 className="truncate font-semibold text-zinc-900 group-hover:text-zinc-700 transition-colors">
            {c.name}
          </h3>
          {c.source_fund && (
            <p className="mt-0.5 truncate text-xs text-zinc-400">
              {c.source_fund}
            </p>
          )}
        </div>
      </div>

      {/* Pitch */}
      {c.one_line_pitch && (
        <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-zinc-600">
          {c.one_line_pitch}
        </p>
      )}

      {/* Footer */}
      <div className="mt-auto pt-4 space-y-2.5">
        {c.location && (
          <p className="flex items-center gap-1.5 text-xs text-zinc-400">
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5 shrink-0 text-zinc-300">
              <path fillRule="evenodd" d="M9.69 18.933l.003.001C9.89 19.02 10 19 10 19s.11.02.308-.066l.002-.001.006-.003.018-.008a5.741 5.741 0 00.281-.14c.186-.096.446-.24.757-.433.62-.384 1.445-.966 2.274-1.765C15.302 15.57 17 13.216 17 10a7 7 0 10-14 0c0 3.216 1.698 5.57 3.354 7.185a13.045 13.045 0 002.274 1.765 11.169 11.169 0 00.757.433 5.737 5.737 0 00.281.14l.018.008.006.003zM10 12a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
            </svg>
            {c.location}
          </p>
        )}
        <div className="flex flex-wrap items-center gap-1.5">
          <HiringBadge status={c.intern_hiring_status} />
          {c.sector && <SectorBadge sector={c.sector} />}
          {c.vandy_alumni_count > 0 && <VandyBadge count={c.vandy_alumni_count} />}
        </div>
      </div>
    </Link>
  );
}
