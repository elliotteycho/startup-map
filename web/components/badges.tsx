/**
 * Reusable badge components for hiring status and sector.
 * Server components: pure rendering, no client-side state.
 */

const SECTOR_STYLES: Record<string, string> = {
  AI:         "bg-violet-100 text-violet-800 ring-violet-200",
  Fintech:    "bg-emerald-100 text-emerald-800 ring-emerald-200",
  Healthcare: "bg-rose-100 text-rose-800 ring-rose-200",
  Consumer:   "bg-pink-100 text-pink-800 ring-pink-200",
  Enterprise: "bg-sky-100 text-sky-800 ring-sky-200",
  Crypto:     "bg-orange-100 text-orange-800 ring-orange-200",
  Climate:    "bg-teal-100 text-teal-800 ring-teal-200",
  Bio:        "bg-lime-100 text-lime-800 ring-lime-200",
  Education:  "bg-yellow-100 text-yellow-800 ring-yellow-200",
  Gaming:     "bg-indigo-100 text-indigo-800 ring-indigo-200",
  Other:      "bg-zinc-100 text-zinc-700 ring-zinc-200",
};

export function SectorBadge({ sector }: { sector: string | null }) {
  if (!sector) return null;
  const style = SECTOR_STYLES[sector] ?? SECTOR_STYLES.Other;
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${style}`}
    >
      {sector}
    </span>
  );
}

const STATUS_STYLES: Record<string, string> = {
  hiring:     "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  open_to:    "bg-amber-50 text-amber-700 ring-amber-600/20",
  not_hiring: "bg-zinc-50 text-zinc-600 ring-zinc-500/10",
  unknown:    "bg-zinc-50 text-zinc-500 ring-zinc-500/10",
};

const STATUS_LABELS: Record<string, string> = {
  hiring:     "Hiring interns",
  open_to:    "Open to interns",
  not_hiring: "Not hiring",
  unknown:    "Status unknown",
};

const STATUS_DOTS: Record<string, string> = {
  hiring:     "bg-emerald-500",
  open_to:    "bg-amber-500",
  not_hiring: "bg-zinc-400",
  unknown:    "bg-zinc-300",
};

export function HiringBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.unknown;
  const label = STATUS_LABELS[status] ?? "Unknown";
  const dot = STATUS_DOTS[status] ?? STATUS_DOTS.unknown;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${style}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  );
}

export function VandyBadge({ count }: { count: number }) {
  if (count <= 0) return null;
  return (
    <span className="inline-flex items-center gap-1 rounded-md bg-yellow-50 px-2 py-0.5 text-xs font-medium text-yellow-800 ring-1 ring-inset ring-yellow-600/20">
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-3 w-3">
        <path
          fillRule="evenodd"
          d="M10 1l2.39 5.84L18.5 7.5l-4.5 4.05L15.4 18 10 14.85 4.6 18l1.4-6.45L1.5 7.5l6.11-.66L10 1z"
          clipRule="evenodd"
        />
      </svg>
      {count} Vandy alum{count === 1 ? "" : "ni"}
    </span>
  );
}
