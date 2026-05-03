# Startup Dashboard — v1 Specification

**Status:** Locked, May 2026
**Owner:** Elliott Cho
**Sprint length:** 2 to 3 weeks at 20+ hours per week

## 1. North Star

A free, public web dashboard where Vanderbilt undergrads can discover and research vetted early stage startups for internships, with response data and alumni connections that Wellfound cannot offer.

## 2. Target User

A 2nd or 3rd year Vanderbilt undergraduate in CS, HOD, or Business, looking for a summer internship at an early stage startup, who has tried Wellfound and found it overwhelming, and who does not yet have a strong founder network.

## 3. Core Problem and Current Alternatives

The problem is signal to noise in the early stage startup market. The competitive set is broad and serious, not just Wellfound.

### Five buckets of competitors

**Structural giants** (Crunchbase, PitchBook, LinkedIn, Wellfound). Orders of magnitude more data. Cannot be beaten on their own terms.

**Curated startup specific players** (YC's Work at a Startup, Built In, Welcome to the Jungle, Underdog Fund job board). Already proved the curation thesis works. YC is the most dangerous: 5000 active companies, free, high response rate.

**Student specific platforms** (Handshake, RippleMatch, Forage, WayUp). Direct school integration. Corporate dominated by design. Handshake is literally Vandy's career office portal.

**AI assisted newcomers** (Simplify, Sonara, Massive). Move fast, well funded, target the same user.

**Unstructured but dominant channels** (Twitter/X, founder Slacks, On Deck, Hacker News "Who's Hiring," warm intros). Where most early stage hires actually happen. No platform competes effectively.

### Honest assessment of what each does well

Crunchbase wins on breadth. PitchBook on data depth. LinkedIn on people graph. Wellfound on liquidity. YC on credibility. Built In on local SEO. Handshake on school integration. None of them are bad products.

## 3b. Competitive Edge (3 layers)

### Layer 1, distribution edge (works week 1)
Authentic reach into Vanderbilt student channels no platform competitor can replicate: dorm chats, club Slacks, Greek life GroupMe, CS Discord, Wond'ry, Owen, Vandy startups Slack. Walk in as a peer. This is the launch advantage.

### Layer 2, curation and presentation edge (works months 1 to 3)
"100 vetted startups for Vandy students this semester" is a fundamentally different product from "12,000 jobs, search to refine." A student can read the entire database in 30 minutes and feel they have surveyed the field. Discipline: the day this becomes 5,000 companies, the edge dies.

### Layer 3, data moat (compounds months 4 to 12)
The only durable defensibility. Two specific data assets:

**Vandy alumni map.** Every company tagged with which Vanderbilt alumni currently work there. Publicly inferrable from LinkedIn but nobody compiled it for any specific school. Hard to replicate at depth.

**Response verification data.** Track which companies students actually apply to and which reply within 14 days. After 6 months, you have empirical response rate data on early stage startups segmented by who is applying. Wellfound, Crunchbase, and LinkedIn do not have this at any price.

### Strategic narrative
Not "another startup database." This is the Facebook playbook for early career startup discovery. Win Vanderbilt completely (high penetration, high engagement), then expand to peer schools using the same template. Network effects compound within and across schools. The TAM is small at Vanderbilt alone but real across the top 30 undergrad campuses.

## 4. Success Metrics (90-day thresholds)

100 unique Vanderbilt student visitors. 40 percent return rate within 14 days. 10 students who applied to a startup found through the platform. 3 students who got an interview as a result.

If these are not hit, the product is not working and the response is to change the product, not push harder on the same approach.

## 5. Scope

### In scope for v1
A public web dashboard listing 100 to 200 vetted startups, filterable by sector and intern hiring status, with a detail page per company showing 12 data fields, a Vanderbilt alumni connection badge where applicable, and a link to the company careers page. A Python scraper pipeline that populates and refreshes the database weekly. Basic traffic analytics. Multi school capable architecture from day 1.

### Explicitly out of scope for v1
User accounts, saved companies, email alerts, application tracking, in platform applications, founder side tools, payment, mobile app, AI chat over the dashboard, social features, comments or reviews, custom domain.

## 6. Phases

**Phase 1, weeks 1 to 3:** MVP. Scraper plus dashboard plus 100 to 200 companies. Deployed publicly. Soft launched to 10 to 20 friends.

**Phase 2, weeks 4 to 12:** Validation. Add the alumni connection layer. Expand to 300+ companies. Public launch to broader Vanderbilt. Hit 90 day success metrics or pivot.

**Phase 3, months 4 to 6:** Differentiation. Add response verification (which startups actually reply). Add warm intros via the VC network. Expand to a second school.

## 7. Constraints

Sophomore in classes, ~20 hours per week available for the next 4 weeks. Zero budget; constrained to free tiers (Vercel, Supabase, Render). Existing VC Fund Network database (245 funds, 107 portfolio companies) as seed sourcing data. Claude Code in VS Code as the build accelerator.

The driving constraint is time. Anything that takes more than 2 hours and does not move toward Phase 1 launch is cut.

## 8. Technical Architecture

**Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui. Deployed on Vercel.

**Database and auto generated REST API:** Supabase (managed Postgres). Row Level Security enabled from day 1.

**Scraper:** Python 3.11+. Playwright for JavaScript heavy pages, BeautifulSoup for static HTML, Anthropic SDK for LLM extraction (Claude Haiku for cost). Pydantic for data validation. Deployed as a Render Cron Job, scheduled weekly.

**Version control:** GitHub, private repo to start.

**Multi school architecture:** `schools` table from day 1 with Vanderbilt as row 1. School is a parameter, never a hardcoded constant. URL routing supports `/vanderbilt/companies` even if Vanderbilt is the only valid path in v1.

## 9. Data Model (12 fields per company)

`name`, `website` (unique), `sector`, `stage`, `last_round_date`, `last_round_size`, `lead_investor`, `headcount_range`, `location`, `careers_page_url`, `intern_hiring_status`, `one_line_pitch`. Plus `created_at`, `updated_at`, `last_scraped_at`.

## 10. Repo Structure

```
startup-dashboard/
├── README.md
├── .gitignore
├── web/                    Next.js app, deployed to Vercel
├── scraper/                Python pipeline, deployed to Render
├── schema/                 SQL migrations (001_initial.sql, etc.)
└── docs/
    ├── spec.md             this document
    └── decisions.md        architectural decision records
```

## 11. Operating Principles

Deploy on day 1 (Hello World to Vercel before any features). Commit early and often with messages explaining why, not what. Never commit secrets; use `.env.local` and `.gitignore`. Type safety end to end (TypeScript on frontend, Pydantic on backend). Database changes go in numbered SQL migrations. Log every meaningful step in the scraper. Update the README every time setup changes. Self review every PR even when working alone. Weekly retro on Friday in `docs/retros.md`.

## 12. Sprint Tasks (v1)

1. Lock spec document and commit to repo
2. Initialize GitHub repo and folder structure
3. Provision Supabase project and capture credentials
4. Define and apply initial database schema
5. Scaffold Next.js web app with TypeScript and Tailwind
6. Scaffold Python scraper environment
7. Build first VC portfolio scraper as proof of concept (a16z)
8. Build LLM-based generic extractor
9. Wire scraper output into Supabase
10. Build minimal data table page in Next.js
11. Style the dashboard with Tailwind and shadcn/ui
12. Implement sector and intern hiring filters
13. Build per-company detail page
14. Expand scraper to 20+ VC portfolio sources
15. Deploy frontend to Vercel
16. Deploy scraper to Render with weekly cron
17. Add Vercel Analytics and basic error tracking
18. Write README and decisions log
19. Soft launch to 10 to 20 Vandy friends
