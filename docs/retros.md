# Retrospectives

Weekly retro, written each Friday. Each entry records what shipped, what slipped, and what to change next week. Append new entries at the top; do not edit past ones (write a follow up instead).

---

### Week of May 15, 2026

**Shipped**
- Documentation revamp across the repo: portfolio first README with architecture diagram, new `architecture.md`, new `scraper-design.md`, new `build-log.md`
- LICENSE file added (MIT)
- Fixed duplicated content bug in `docs/spec.md`
- Corrected version drift across all docs: Next 14 references updated to Next 16, React 19, Tailwind 4; removed stale shadcn/ui claim
- Removed dead code: `web/components/CompaniesView.tsx` (replaced by `DashboardShell`)
- Moved deferred a16z scraper to `scraper/_deferred/` with deprecation header
- Fixed emdash in live hero copy

**Slipped or blocked**
- Scraper has not been run end to end in three weeks; live production database is empty. Need to verify the YC Algolia regex still matches and rerun `pipeline.py` against all sources.
- Render cron deployment still not wired

**Change next week**
- First task: run `smoke_test.py founders` to confirm the scraper still works against current VC sites. The YC Algolia regex is the most fragile piece; verify before broader run.
- Add three more VC portfolio sources after verification (target: 10 total before pushing to Render)

---

## Template

### Week of [date]

**Shipped**
- 

**Slipped or blocked**
- 

**Change next week**
- 
