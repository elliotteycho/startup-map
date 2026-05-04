"""
Find Vanderbilt-affiliated people at startups in the DB.

Two strategies:
  1. founder-scan  — scrapes LinkedIn profiles of founders we already have
                     and checks for Vanderbilt education (no API key needed)
  2. apollo        — uses Apollo.io people-search API with school filter
                     (free API key at apollo.io — 50 exports/month free)

Usage:
    python3 find_vandy_alumni.py founder-scan          # check all founder profiles
    python3 find_vandy_alumni.py founder-scan --limit 100
    python3 find_vandy_alumni.py apollo                # needs APOLLO_API_KEY in .env
    python3 find_vandy_alumni.py apollo --school "Vanderbilt University"
"""

from __future__ import annotations

import argparse
import html as html_module
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ── Env ───────────────────────────────────────────────────────────

def load_env(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

load_env()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
SB_HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}

SCHOOL_NAME    = "Vanderbilt"          # used as a substring match
SCHOOL_DB_ID   = 1                     # schools.id for Vanderbilt in Supabase

# ── Supabase helpers ──────────────────────────────────────────────

def sb_get(table: str, params: dict) -> list:
    qs = urllib.parse.urlencode(params)
    url = f"{SUPABASE_URL}/rest/v1/{table}?{qs}"
    return json.loads(urllib.request.urlopen(
        urllib.request.Request(url, headers=SB_HEADERS), timeout=20
    ).read())

def sb_upsert(table: str, rows: list, on_conflict: str) -> None:
    if not rows:
        return
    url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={urllib.parse.quote(on_conflict)}"
    data = json.dumps(rows).encode()
    req = urllib.request.Request(url, data=data, headers={
        **SB_HEADERS,
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    })
    urllib.request.urlopen(req, timeout=20)

# ── LinkedIn profile scraper ──────────────────────────────────────

_LI_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def _extract_education(html: str) -> list[str]:
    """Return list of institution names found in the education section."""
    unescaped = html_module.unescape(html)
    # Education section lives in structured data or visible HTML
    schools = []

    # Structured JSON-LD
    for m in re.finditer(r'"alumniOf"\s*:\s*(\[.*?\]|\{.*?\})', unescaped, re.DOTALL):
        try:
            val = json.loads(m.group(1))
            items = val if isinstance(val, list) else [val]
            for item in items:
                name = item.get("name", "")
                if name:
                    schools.append(name)
        except Exception:
            pass

    # Visible education cards (LinkedIn SEO HTML)
    for m in re.finditer(
        r'<span[^>]*>\s*([^<]{5,80}(?:University|College|Institute|School)[^<]{0,40})\s*</span>',
        unescaped, re.IGNORECASE
    ):
        schools.append(m.group(1).strip())

    # Broader keyword search in the full page
    for m in re.finditer(r'((?:University|College) of [A-Z][a-zA-Z ]{2,30}|[A-Z][a-zA-Z ]+ (?:University|College|Institute))', unescaped):
        schools.append(m.group(1))

    return list(dict.fromkeys(schools))  # deduplicate, preserve order


def _grad_year(html: str) -> int | None:
    """Try to extract a graduation year near a Vanderbilt mention."""
    unescaped = html_module.unescape(html)
    idx = unescaped.lower().find(SCHOOL_NAME.lower())
    if idx < 0:
        return None
    window = unescaped[max(0, idx - 200): idx + 400]
    years = re.findall(r'\b(20\d{2}|19\d{2})\b', window)
    if years:
        return int(years[-1])  # take latest year (graduation rather than start)
    return None


def scrape_linkedin_education(linkedin_url: str) -> dict:
    """
    Returns {"has_vanderbilt": bool, "schools": [...], "grad_year": int|None}
    """
    try:
        raw = urllib.request.urlopen(
            urllib.request.Request(linkedin_url.rstrip("/"), headers=_LI_HEADERS),
            timeout=15,
        ).read().decode("utf-8", errors="replace")
    except Exception:
        return {"has_vanderbilt": False, "schools": [], "grad_year": None}

    schools = _extract_education(raw)
    has_vandy = any(SCHOOL_NAME.lower() in s.lower() for s in schools) or \
                SCHOOL_NAME.lower() in raw.lower()
    grad_year = _grad_year(raw) if has_vandy else None
    return {"has_vanderbilt": has_vandy, "schools": schools, "grad_year": grad_year}

# ── Strategy 1: founder scan ──────────────────────────────────────

def run_founder_scan(limit: int = 2000) -> None:
    print(f"Loading founders with LinkedIn URLs...", flush=True)
    founders = sb_get("founders", {
        "select": "id,name,company_id,linkedin_url",
        "linkedin_url": "not.is.null",
        "limit": str(limit),
    })
    print(f"  {len(founders)} founders to check", flush=True)

    # Load company map
    companies = sb_get("companies", {"select": "id,name", "limit": "2000"})
    id_to_name = {c["id"]: c["name"] for c in companies}

    alumni_rows: list[dict] = []
    checked = 0

    def check_one(f):
        result = scrape_linkedin_education(f["linkedin_url"])
        time.sleep(0.4)  # polite rate limit
        return f, result

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(check_one, f): f for f in founders}
        for future in as_completed(futures):
            checked += 1
            if checked % 50 == 0:
                print(f"  ... {checked}/{len(founders)} profiles checked, {len(alumni_rows)} Vandy matches", flush=True)
            try:
                f, result = future.result()
            except Exception:
                continue
            if not result["has_vanderbilt"]:
                continue

            company_name = id_to_name.get(f["company_id"], "")
            print(f"  ✓ {f['name']} ({company_name}) — grad year: {result['grad_year']}", flush=True)
            alumni_rows.append({
                "school_id":          SCHOOL_DB_ID,
                "name":               f["name"],
                "linkedin_url":       f["linkedin_url"],
                "current_company_id": f["company_id"],
                "role":               "Founder",
                "graduation_year":    result["grad_year"],
                "is_recruiter":       False,
            })

    print(f"\nFound {len(alumni_rows)} Vanderbilt founders.", flush=True)
    if alumni_rows:
        sb_upsert("alumni", alumni_rows, "school_id,linkedin_url")
        print(f"Saved {len(alumni_rows)} rows to alumni table.", flush=True)

# ── Strategy 2: Apollo.io ────────────────────────────────────────

def run_apollo(school: str = "Vanderbilt University", limit: int = 500) -> None:
    api_key = os.environ.get("APOLLO_API_KEY")
    if not api_key:
        print("ERROR: Set APOLLO_API_KEY in .env — get a free key at apollo.io")
        return

    print(f"Loading companies from Supabase...", flush=True)
    companies = sb_get("companies", {"select": "id,name,website", "limit": "2000"})
    print(f"  {len(companies)} companies", flush=True)

    alumni_rows: list[dict] = []

    for i, company in enumerate(companies):
        if i % 20 == 0:
            print(f"  [{i}/{len(companies)}] checking {company['name']}...", flush=True)

        body = json.dumps({
            "api_key": api_key,
            "q_organization_name": company["name"],
            "education_school_name": school,
            "per_page": 25,
            "page": 1,
        }).encode()

        try:
            resp = urllib.request.urlopen(
                urllib.request.Request(
                    "https://api.apollo.io/v1/people/search",
                    data=body,
                    headers={"Content-Type": "application/json"},
                ),
                timeout=15,
            )
            data = json.loads(resp.read())
        except Exception as e:
            continue

        for person in data.get("people", []):
            edu = person.get("education", []) or []
            grad_year = None
            for e in edu:
                if school.split()[0].lower() in (e.get("school_name") or "").lower():
                    if e.get("end_date"):
                        try:
                            grad_year = int(str(e["end_date"])[:4])
                        except Exception:
                            pass
                    break

            linkedin = person.get("linkedin_url") or None

            alumni_rows.append({
                "school_id":          SCHOOL_DB_ID,
                "name":               person.get("name", "Unknown"),
                "linkedin_url":       linkedin,
                "current_company_id": company["id"],
                "role":               (person.get("title") or "").strip() or None,
                "graduation_year":    grad_year,
                "is_recruiter":       False,
            })

        time.sleep(0.5)  # Apollo rate limit

        if len(alumni_rows) >= limit:
            break

    print(f"\nFound {len(alumni_rows)} Vanderbilt alumni via Apollo.", flush=True)
    if alumni_rows:
        sb_upsert("alumni", alumni_rows, "school_id,linkedin_url")
        print(f"Saved {len(alumni_rows)} rows to alumni table.", flush=True)


# ── CLI ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("strategy", choices=["founder-scan", "apollo"], help="Which strategy to use")
    parser.add_argument("--limit", type=int, default=2000)
    parser.add_argument("--school", type=str, default="Vanderbilt University")
    args = parser.parse_args()

    if args.strategy == "founder-scan":
        run_founder_scan(limit=args.limit)
    elif args.strategy == "apollo":
        run_apollo(school=args.school, limit=args.limit)


if __name__ == "__main__":
    main()
