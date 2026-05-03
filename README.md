# Startup Dashboard

A free, public web dashboard helping Vanderbilt undergrads discover and research vetted early stage startups for internships. Built on a Python scraper that pulls from VC firm portfolio pages, a Supabase Postgres database, and a Next.js frontend on Vercel. Architected to expand to other top schools after Vanderbilt validation.

## Project Structure

```
startup-dashboard/
├── web/                    Next.js 14 app (TypeScript, Tailwind, shadcn/ui)
├── scraper/                Python pipeline (Playwright, BeautifulSoup, Anthropic SDK)
├── schema/                 SQL migrations applied via Supabase
└── docs/                   Spec, architectural decisions, retrospectives
```

## Getting Started

### Prerequisites
- Node.js 18+ (`brew install node`)
- Python 3.11+ (`brew install python@3.11`)
- A Supabase account (free tier)
- An Anthropic API key

### Frontend (web/)
```bash
cd web
cp .env.local.example .env.local
# Fill in NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY
npm install
npm run dev
```
Open http://localhost:3000

### Scraper (scraper/)
```bash
cd scraper
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, ANTHROPIC_API_KEY
python pipeline.py
```

### Database (schema/)
Apply migrations in order via the Supabase SQL editor. Each migration is numbered and idempotent where possible.

## Documentation
- [Specification](docs/spec.md) - locked v1 requirements, scope, success metrics
- [Architectural Decisions](docs/decisions.md) - why each major choice was made

## Status
v1 in development, May 2026.
