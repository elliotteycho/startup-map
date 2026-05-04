/**
 * Single startup card used in the home grid. Click navigates to the detail page.
 */

import Link from "next/link";

import type { CompanyWithAlumni } from "@/lib/types";
import { HiringBadge, SectorBadge, VandyBadge } from "./badges";

export function CompanyCard({ company: c }: { company: CompanyWithAlumni }) {
  const initials = c.name
    .split(/\s+/)
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <Link
      href={`/companies/${c.id}`}
      className="group flex h-full flex-col rounded-xl border border-zinc-200 bg-white p-5 transition-all hover:border-zinc-300 hover:shadow-md"
    >
      <div className="flex items-start gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-zinc-900 text-sm font-semibold text-white">
          {initials}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-base font-semibold text-zinc-900 group-hover:text-zinc-700">
            {c.name}
          </h3>
          {c.source_fund && (
            <p className="mt-0.5 truncate text-xs text-zinc-500">
              via {c.source_fund}
            </p>
          )}
        </div>
      </div>

      {c.one_line_pitch && (
        <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-zinc-600">
          {c.one_line_pitch}
        </p>
      )}

      <div className="mt-auto pt-4">
        <div className="flex flex-wrap items-center gap-1.5">
          <HiringBadge status={c.intern_hiring_status} />
          {c.sector && <SectorBadge sector={c.sector} />}
          {c.vandy_alumni_count > 0 && (
            <VandyBadge count={c.vandy_alumni_count} />
          )}
        </div>
      </div>
    </Link>
  );
}
