"use client";

import { useMemo, useState } from "react";

import type { CompanyWithAlumni } from "@/lib/types";
import { CompanyCard } from "./CompanyCard";

const SECTORS = [
  "AI", "Fintech", "Healthcare", "Consumer", "Enterprise",
  "Crypto", "Climate", "Bio", "Education", "Gaming", "Other",
];

const STATUS_PILLS = [
  { value: "all",        label: "All" },
  { value: "hiring",     label: "Hiring interns" },
  { value: "open_to",    label: "Open to interns" },
  { value: "not_hiring", label: "Not hiring" },
];

type HiringFilter = "all" | "hiring" | "open_to" | "not_hiring";

interface Props {
  companies: CompanyWithAlumni[];
}

export function DashboardShell({ companies }: Props) {
  const [search,       setSearch]       = useState("");
  const [hiringFilter, setHiringFilter] = useState<HiringFilter>("all");
  const [sectorFilter, setSectorFilter] = useState("all");
  const [vandyOnly,    setVandyOnly]    = useState(false);

  // ── Derived stats ───────────────────────────────────────────────
  const hiringCount  = useMemo(() => companies.filter(c => c.intern_hiring_status === "hiring").length, [companies]);
  const sectorsCount = useMemo(() => new Set(companies.map(c => c.sector).filter(Boolean)).size, [companies]);
  const vandyCount   = useMemo(() => companies.filter(c => c.vandy_alumni_count > 0).length, [companies]);

  const sectorsPresent = useMemo(() => {
    const set = new Set<string>();
    companies.forEach(c => { if (c.sector) set.add(c.sector); });
    return SECTORS.filter(s => set.has(s));
  }, [companies]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return companies.filter(c => {
      if (hiringFilter !== "all" && c.intern_hiring_status !== hiringFilter) return false;
      if (sectorFilter !== "all" && c.sector !== sectorFilter) return false;
      if (vandyOnly && c.vandy_alumni_count <= 0) return false;
      if (q) {
        const hay = `${c.name} ${c.one_line_pitch ?? ""} ${c.source_fund ?? ""}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [companies, search, hiringFilter, sectorFilter, vandyOnly]);

  const activeFilterCount = [
    hiringFilter !== "all",
    sectorFilter !== "all",
    vandyOnly,
    search.trim().length > 0,
  ].filter(Boolean).length;

  function clearAll() {
    setSearch(""); setHiringFilter("all"); setSectorFilter("all"); setVandyOnly(false);
  }

  // ── Stat cell active state ──────────────────────────────────────
  const allActive    = hiringFilter === "all" && sectorFilter === "all" && !vandyOnly && !search;
  const hiringActive = hiringFilter === "hiring";
  const vandyActive  = vandyOnly && hiringFilter === "all";

  return (
    <div className="relative mx-auto max-w-7xl px-6 pb-8">

      {/* ── Stats grid ─────────────────────────────────────────── */}
      <div className="grid grid-cols-2 divide-x divide-y divide-white/[0.06] overflow-hidden rounded-t-2xl border border-b-0 border-white/[0.08] bg-white/[0.02] sm:grid-cols-4 sm:divide-y-0">
        <StatCell
          label="Companies"
          value={companies.length}
          active={allActive}
          onClick={clearAll}
        />
        <StatCell
          label="Hiring interns"
          value={hiringCount}
          highlight
          active={hiringActive}
          onClick={() => { clearAll(); setHiringFilter("hiring"); }}
        />
        <StatCell
          label="Sectors"
          value={sectorsCount}
          active={false}
          onClick={clearAll}
        />
        <StatCell
          label="Vandy connections"
          value={vandyCount}
          gold
          active={vandyActive}
          onClick={() => { clearAll(); setVandyOnly(true); }}
        />
      </div>

      {/* ── Filter panel ───────────────────────────────────────── */}
      <div className="rounded-b-2xl rounded-t-none border border-white/[0.08] bg-slate-900/60 backdrop-blur-xl px-5 py-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <svg viewBox="0 0 20 20" fill="currentColor" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500">
              <path fillRule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.45 4.39l3.08 3.08a.75.75 0 11-1.06 1.06l-3.08-3.08A7 7 0 012 9z" clipRule="evenodd" />
            </svg>
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search by name, pitch, or VC firm..."
              className="w-full rounded-lg border border-slate-700/60 bg-slate-800/60 py-2 pl-9 pr-3 text-sm text-slate-100 placeholder:text-slate-500 focus:border-violet-500/60 focus:bg-slate-800 focus:outline-none focus:ring-1 focus:ring-violet-500/30 transition-colors"
            />
          </div>

          <label className="flex shrink-0 cursor-pointer items-center gap-2 rounded-lg border border-slate-700/60 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800/60 transition-colors select-none">
            <input
              type="checkbox"
              checked={vandyOnly}
              onChange={e => setVandyOnly(e.target.checked)}
              className="h-4 w-4 rounded border-slate-600 accent-violet-500"
            />
            <span className="hidden sm:inline">Vandy connections</span>
            <span className="sm:hidden">Vandy</span>
          </label>

          {activeFilterCount > 0 && (
            <button
              onClick={clearAll}
              className="shrink-0 rounded-lg border border-slate-700/60 px-3 py-2 text-xs text-slate-400 hover:border-slate-600 hover:text-slate-200 transition-colors"
            >
              Clear {activeFilterCount}
            </button>
          )}
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {STATUS_PILLS.map(p => (
            <button
              key={p.value}
              onClick={() => setHiringFilter(p.value as HiringFilter)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                hiringFilter === p.value
                  ? "bg-violet-600 text-white"
                  : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className="mt-2 flex flex-wrap gap-2">
          <button
            onClick={() => setSectorFilter("all")}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              sectorFilter === "all"
                ? "bg-violet-600 text-white"
                : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200"
            }`}
          >
            All sectors
          </button>
          {sectorsPresent.map(s => (
            <button
              key={s}
              onClick={() => setSectorFilter(s)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                sectorFilter === s
                  ? "bg-violet-600 text-white"
                  : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Result count */}
      <div className="mb-4">
        <p className="text-sm text-slate-500">
          <span className="font-medium text-slate-200">{filtered.length}</span>
          {" "}of {companies.length} companies
        </p>
      </div>

      {/* Grid */}
      {filtered.length === 0 ? (
        <div className="rounded-2xl border border-slate-700/40 bg-slate-900/60 p-16 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-slate-800">
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-6 w-6 text-slate-500">
              <path fillRule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.45 4.39l3.08 3.08a.75.75 0 11-1.06 1.06l-3.08-3.08A7 7 0 012 9z" clipRule="evenodd" />
            </svg>
          </div>
          <p className="font-medium text-slate-300">No companies match these filters.</p>
          <p className="mt-1 text-sm text-slate-500">Try widening your search or clearing a filter.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map(c => <CompanyCard key={c.id} company={c} />)}
        </div>
      )}
    </div>
  );
}

// ── Stat cell ─────────────────────────────────────────────────────

function StatCell({
  label, value, highlight, gold, active, onClick,
}: {
  label: string;
  value: number;
  highlight?: boolean;
  gold?: boolean;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`group w-full cursor-pointer px-6 py-5 text-left transition-colors duration-150 ${
        highlight
          ? active ? "bg-emerald-500/20" : "bg-emerald-500/10 hover:bg-emerald-500/15"
          : gold
          ? active ? "bg-yellow-400/15" : "bg-yellow-400/5 hover:bg-yellow-400/10"
          : active ? "bg-violet-500/15" : "bg-transparent hover:bg-white/[0.04]"
      }`}
    >
      <div
        className={`text-3xl font-bold tabular-nums transition-transform duration-150 ${
          active ? "scale-105" : "group-hover:scale-105"
        } ${
          highlight
            ? "bg-gradient-to-br from-emerald-300 to-emerald-500 bg-clip-text text-transparent"
            : gold
            ? "bg-gradient-to-br from-yellow-300 to-yellow-500 bg-clip-text text-transparent"
            : active
            ? "bg-gradient-to-br from-white to-violet-300 bg-clip-text text-transparent"
            : "bg-gradient-to-br from-white to-slate-400 bg-clip-text text-transparent"
        }`}
      >
        {value.toLocaleString()}
      </div>
      <div
        className={`mt-1 text-xs uppercase tracking-wider ${
          highlight ? "text-emerald-500/60"
          : gold ? "text-yellow-500/60"
          : active ? "text-violet-400/60"
          : "text-slate-600"
        }`}
      >
        {label}
        {active && <span className="ml-1.5 text-slate-600">·</span>}
        {active && <span className="ml-1 normal-case tracking-normal text-slate-500">active</span>}
      </div>
    </button>
  );
}
