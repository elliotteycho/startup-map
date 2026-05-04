const SECTOR_STYLES: Record<string, string> = {
  AI:         "bg-violet-500/15 text-violet-300 ring-violet-500/25",
  Fintech:    "bg-emerald-500/15 text-emerald-300 ring-emerald-500/25",
  Healthcare: "bg-rose-500/15 text-rose-300 ring-rose-500/25",
  Consumer:   "bg-pink-500/15 text-pink-300 ring-pink-500/25",
  Enterprise: "bg-sky-500/15 text-sky-300 ring-sky-500/25",
  Crypto:     "bg-orange-500/15 text-orange-300 ring-orange-500/25",
  Climate:    "bg-teal-500/15 text-teal-300 ring-teal-500/25",
  Bio:        "bg-lime-500/15 text-lime-300 ring-lime-500/25",
  Education:  "bg-yellow-500/15 text-yellow-300 ring-yellow-500/25",
  Gaming:     "bg-indigo-500/15 text-indigo-300 ring-indigo-500/25",
  Other:      "bg-slate-700/50 text-slate-400 ring-slate-600/20",
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
  hiring:     "bg-emerald-500/15 text-emerald-300 ring-emerald-500/25",
  open_to:    "bg-amber-500/15 text-amber-300 ring-amber-500/25",
  not_hiring: "bg-slate-700/50 text-slate-400 ring-slate-600/20",
  unknown:    "bg-slate-700/50 text-slate-500 ring-slate-600/20",
};

const STATUS_LABELS: Record<string, string> = {
  hiring:     "Hiring interns",
  open_to:    "Open to interns",
  not_hiring: "Not hiring",
  unknown:    "Status unknown",
};

const STATUS_DOTS: Record<string, string> = {
  hiring:     "bg-emerald-400",
  open_to:    "bg-amber-400",
  not_hiring: "bg-slate-500",
  unknown:    "bg-slate-600",
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
    <span className="inline-flex items-center gap-1 rounded-md bg-yellow-400/10 px-2 py-0.5 text-xs font-medium text-yellow-300 ring-1 ring-inset ring-yellow-400/25">
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
