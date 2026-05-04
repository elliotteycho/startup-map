"use client";

import { useState } from "react";

interface Props {
  name: string;
  website: string;
  size?: "sm" | "lg";
}

export function CompanyAvatar({ name, website, size = "sm" }: Props) {
  const [failed, setFailed] = useState(false);

  const initials = name
    .split(/\s+/)
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  let domain = "";
  try {
    domain = new URL(website).hostname;
  } catch {}

  const faviconUrl = domain
    ? `https://www.google.com/s2/favicons?domain=${domain}&sz=64`
    : "";

  const isLg = size === "lg";
  const containerCls = isLg
    ? "flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl overflow-hidden bg-slate-800 border border-slate-700/50"
    : "flex h-11 w-11 shrink-0 items-center justify-center rounded-lg overflow-hidden bg-slate-800 border border-slate-700/50";
  const imgCls = isLg ? "h-10 w-10 object-contain" : "h-6 w-6 object-contain";
  const fallbackCls = isLg
    ? "flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl bg-slate-800 text-2xl font-bold text-slate-300 border border-slate-700/50"
    : "flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-slate-800 text-sm font-semibold text-slate-300 border border-slate-700/50";

  if (failed || !faviconUrl) {
    return <div className={fallbackCls}>{initials}</div>;
  }

  return (
    <div className={containerCls}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={faviconUrl}
        alt=""
        width={isLg ? 40 : 24}
        height={isLg ? 40 : 24}
        className={imgCls}
        onError={() => setFailed(true)}
      />
    </div>
  );
}
