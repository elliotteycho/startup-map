# Agent conventions for `web/`

Rules for Claude Code working in this folder. Same content as `AGENTS.md` (Claude Code reads `CLAUDE.md` preferentially, other agents read `AGENTS.md`).

## Framework versions, pinned

This project uses **Next.js 16.2.4** with the App Router, **React 19.2.4**, and **Tailwind CSS 4**. These are not the versions most training data is calibrated to.

- Next 16 uses **async route params**. Dynamic segment params must be awaited: `const { slug } = await params;`. Next 14 style sync params will break the build.
- React 19 has different rules around `use()` for promises, async server components, and the new Activity API. Check current docs before reaching for legacy patterns.
- Tailwind 4 has a different config (`@theme` directive, CSS variable based) compared to v3. PostCSS config uses `@tailwindcss/postcss`, not the old plugin.
- shadcn/ui is **not** in this project. Components are raw Tailwind. Do not introduce shadcn without an ADR.

Always check `package.json` before assuming a version.

## Data access pattern

The frontend reads from Supabase using the **public anon key only**. Service role keys never appear in `web/`. Writes from the frontend go to the `events` table only (insert allowed by RLS policy; reads forbidden).

For company data, read from the `companies_with_alumni` view, not `companies` directly. The view pre joins the alumni count so the client never has to compute it.

Order companies by `vandy_alumni_count DESC, name ASC` to surface Vanderbilt connections first.

## Component conventions

`app/page.tsx` is a server component. Use `export const dynamic = "force-dynamic"` to disable static caching since the company list refreshes weekly.

`DashboardShell.tsx` is the main client component. It owns filter state (search, hiring status, sector, Vandy connections toggle). Filtering happens in `useMemo` over the in memory company array. Do not move filtering to the server unless the company count exceeds 1,000.

Per company detail pages live at `app/companies/[slug]/page.tsx`. They are server components that fetch one row by slug. Do not add static generation; routes stay dynamic.

## Tracking

Use `lib/track.ts` for any user interaction worth recording. Events go to the `events` table with an anonymous session ID. Do not capture PII, including email addresses, IPs, or user agent strings. The session ID is generated client side and stored in localStorage.

## Build verification

Always run `npm run build` (not just `npm run dev`) before declaring work done. Dev mode hides type errors that the build catches.

If introducing a new dependency, justify it. The dependency count is intentionally small.
