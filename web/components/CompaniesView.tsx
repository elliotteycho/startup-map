/**
 * Client-side filter + grid for the home page. Server component fetches the
 * full list and passes it down; this component handles search, sector and
 * hiring filters in the browser.
 */

"use client";

import { useMemo, useState } from "react";

import type { CompanyWithAlumni } from "@/lib/types";
import { CompanyCard } from "./CompanyCard";

const SECTORS = [
  "AI", "Fintech", "Healthcare", "Consumer", "Enterprise",
  "Crypto", "Climate", "Bio", "Education", "Gaming", "Other",
];

const STATUS_OPTIONS = [
  { value: "all", label: "All companies" },
  { value: "hiring", label: "Hiring interns" },
  { value: "open_to", label: "Open to interns" },
];

interface Props {
  companies: CompanyWithAlumni[];
}

export function CompaniesView({ companies }: Props) {
  const [search, setSearch] = useState("");
  const [hiringFilter, setHiringFilter] = useState<string>("all");
  const [sectorFilter, setSectorFilter] = useState<string>("all");
  const [vandyOnly, setVandyOnly] = useState(false);

  const sectorsPresent = useMemo(() => {
    const set = new Set<string>();
    companies.forEach((c) => {
      if (c.sector) set.add(c.sector);
    });
    return SECTORS.filter((s) => set.has(s));
  }, [companies]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return companies.filter((c) => {
      if (hiringFilter !== "all" && c.intern_hiring_status !== hiringFilter) {
        return false;
      }
      if (sectorFilter !== "all" && c.sector !== sectorFilter) {
        return false;
      }
      if (vandyOnly && c.vandy_alumni_count <= 0) {
        return false;
      }
      if (q) {
        const haystack = `${c.name} ${c.one_line_pitch ?? ""} ${c.source_fund ?? ""}`.toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });
  }, [companies, search, hiringFilter, sectorFilter, vandyOnly]);

  const hiringCount = companies.filter((c) => c.intern_hiring_status === "hiring").length;

  return (
    <>
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Companies" value={companies.length} />
        <Stat label="Hiring interns" value={hiringCount} highlight />
        <Stat label="Sectors" value={sectorsPresent.length} />
        <Stat
          label="Vandy connections"
          value={companies.filter((c) => c.vandy_alumni_count > 0).length}
        />
      </div>

      <div className="mb-6 rounded-xl border border-zinc-200 bg-white p-4 space-y-3">
        {/* Row 1: search + hiring dropdown + vandy toggle */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <svg
              viewBox="0 0 20 20"
              fill="currentColor"
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400"
            >
              <path
                fillRule="evenodd"
                d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.45 4.39l3.08 3.08a.75.75 0 11-1.06 1.06l-3.08-3.08A7 7 0 012 9z"
                clipRule="evenodd"
              />
            </svg>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name, pitch, or VC firm..."
              className="w-full rounded-lg border border-zinc-200 bg-white py-2 pl-9 pr-3 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none focus:ring-1 focus:ring-zinc-300"
            />
          </div>

          <select
            value={hiringFilter}
            onChange={(e) => setHiringFilter(e.target.value)}
            className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 focus:border-zinc-400 focus:outline-none focus:ring-1 focus:ring-zinc-300"
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>

          <label className="flex shrink-0 items-center gap-2 text-sm text-zinc-700">
            <input
              type="checkbox"
              checked={vandyOnly}
              onChange={(e) => setVandyOnly(e.target.checked)}
              className="h-4 w-4 rounded border-zinc-300 text-zinc-900 focus:ring-zinc-300"
            />
            Vandy connections only
          </label>
        </div>

        {/* Row 2: sector pills */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSectorFilter("all")}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              sectorFilter === "all"
                ? "bg-zinc-900 text-white"
                : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
            }`}
          >
            All
          </button>
          {sectorsPresent.map((s) => (
            <button
              key={s}
              onClick={() => setSectorFilter(s)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                sectorFilter === s
                  ? "bg-zinc-900 text-white"
                  : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-3 text-sm text-zinc-600">
        Showing {filtered.length} of {companies.length}
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-zinc-300 bg-white p-12 text-center">
          <p className="text-zinc-700">No companies match these filters.</p>
          <p className="mt-2 text-sm text-zinc-500">Try widening your search.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((c) => (
            <CompanyCard key={c.id} company={c} />
          ))}
        </div>
      )}
    </>
  );
}

function Stat({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div
      className={`rounded-xl border p-4 ${
        highlight
          ? "border-emerald-200 bg-emerald-50"
          : "border-zinc-200 bg-white"
      }`}
    >
      <div className={`text-2xl font-semibold ${highlight ? "text-emerald-900" : "text-zinc-900"}`}>
        {value.toLocaleString()}
      </div>
      <div className={`mt-1 text-xs uppercase tracking-wider ${highlight ? "text-emerald-700" : "text-zinc-500"}`}>
        {label}
      </div>
    </div>
  );
}
