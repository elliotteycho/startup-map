"""
Standalone YC founder fetcher — zero third-party dependencies.
Uses only Python stdlib (urllib, json, re, concurrent.futures). Run with system python3.

Usage:
    python3 fetch_yc_founders.py
"""
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

# ── Load .env manually (no dotenv needed) ────────────────────────
def load_env(path: str = ".env"):
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
ALGOLIA_APP  = "45BWZJ1SGC"
ALGOLIA_IDX  = "YCCompany_production"

# KEEP IN SYNC with _BATCH_YEAR in extractors/yc.py
BATCHES = {
    "Winter 2025": 2024,
    "Summer 2024": 2024,
    "Winter 2024": 2023,
    "Summer 2023": 2023,
    "Winter 2023": 2022,
    "Winter 2022": 2021,
    "Summer 2022": 2022,
}

# ── HTTP helpers ──────────────────────────────────────────────────

def http_get(url: str, headers: dict = None) -> bytes:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def http_post(url: str, body: dict, headers: dict = None) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        **(headers or {}),
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def http_post_raw(url: str, body, headers: dict = None) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        **(headers or {}),
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read()
        raise RuntimeError(f"HTTP {e.code}: {body[:300]}") from e

# ── Supabase helpers ──────────────────────────────────────────────

SB_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}

def sb_get(table: str, params: dict = None) -> list:
    qs = urllib.parse.urlencode(params or {})
    url = f"{SUPABASE_URL}/rest/v1/{table}{'?' + qs if qs else ''}"
    data = http_get(url, headers=SB_HEADERS)
    return json.loads(data)

def sb_upsert(table: str, rows: list, on_conflict: str) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={urllib.parse.quote(on_conflict)}"
    return http_post_raw(url, rows, headers={
        **SB_HEADERS,
        "Prefer": "resolution=merge-duplicates,return=representation",
    })

# ── YC Algolia helpers ────────────────────────────────────────────

def get_algolia_key() -> str:
    raw = http_get("https://www.ycombinator.com/companies",
                   headers={"User-Agent": "Mozilla/5.0"}).decode("utf-8", errors="replace")
    m = re.search(r'AlgoliaOpts\s*=\s*\{[^}]*"key"\s*:\s*"([^"]+)"', raw)
    if not m:
        raise RuntimeError("AlgoliaOpts key not found on YC page")
    return m.group(1)

def fetch_batch(batch_name: str, api_key: str) -> list:
    filters = urllib.parse.quote(f'batch:"{batch_name}" AND isHiring:true')
    result = http_post(
        f"https://{ALGOLIA_APP.lower()}-dsn.algolia.net/1/indexes/*/queries",
        {"requests": [{"indexName": ALGOLIA_IDX, "params": f"filters={filters}&hitsPerPage=1000"}]},
        headers={"X-Algolia-Application-Id": ALGOLIA_APP, "X-Algolia-API-Key": api_key},
    )
    return result["results"][0]["hits"]

# ── YC page founder scraping ──────────────────────────────────────

def scrape_yc_page(yc_slug: str) -> dict:
    """Fetch a YC company page and extract founders, social links, and tags."""
    url = f"https://www.ycombinator.com/companies/{yc_slug}"
    try:
        raw = http_get(url, headers={"User-Agent": "Mozilla/5.0"}).decode("utf-8", errors="replace")
    except Exception:
        return {"founders": [], "twitter_url": None, "linkedin_url": None, "tags": []}

    unescaped = html_module.unescape(raw)

    # ── Founders ──────────────────────────────────────────────────
    founders = []
    m = re.search(r'"founders"\s*:\s*(\[.*?\])\s*[,}]', unescaped, re.DOTALL)
    if m:
        try:
            for f in json.loads(m.group(1)):
                name = (f.get("full_name") or "").strip()
                if name:
                    founders.append({
                        "name": name,
                        "title":        (f.get("title") or "").strip() or None,
                        "linkedin_url": (f.get("linkedin_url") or "").strip() or None,
                        "bio":          (f.get("founder_bio") or "").strip() or None,
                    })
        except Exception:
            pass

    # ── Social links ──────────────────────────────────────────────
    def extract_field(key: str) -> str | None:
        fm = re.search(rf'"{re.escape(key)}"\s*:\s*"([^"]+)"', unescaped)
        return fm.group(1).strip() or None if fm else None

    twitter_url  = extract_field("twitter_url")
    linkedin_url = extract_field("linkedin_url")

    # ── Tags ──────────────────────────────────────────────────────
    tags = []
    mt = re.search(r'"tags"\s*:\s*(\[.*?\])\s*[,}]', unescaped, re.DOTALL)
    if mt:
        try:
            tags = [t for t in json.loads(mt.group(1)) if isinstance(t, str)]
        except Exception:
            pass

    return {"founders": founders, "twitter_url": twitter_url, "linkedin_url": linkedin_url, "tags": tags}

# ── Data helpers ──────────────────────────────────────────────────

def normalize_website(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return f"https://{netloc}"

def make_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

# ── Main ──────────────────────────────────────────────────────────

def main():
    print("Fetching Algolia key...", flush=True)
    api_key = get_algolia_key()
    print("Got key.", flush=True)

    print("Loading company index from Supabase...", flush=True)
    all_companies = sb_get("companies", {"select": "id,name,website,slug", "limit": "2000"})
    website_to_id = {normalize_website(c["website"]): c["id"] for c in all_companies}
    print(f"Loaded {len(all_companies)} companies.", flush=True)

    total_companies = 0
    total_founders  = 0

    # Collect (yc_slug, website) pairs for founder scraping after all upserts
    slug_website_pairs: list[tuple[str, str]] = []

    for batch_name, founded_year in BATCHES.items():
        print(f"\nBatch: {batch_name} ...", flush=True)
        hits = fetch_batch(batch_name, api_key)
        print(f"  {len(hits)} hits from Algolia", flush=True)

        company_rows = []

        for hit in hits:
            raw_site = (hit.get("website") or "").strip()
            if not raw_site:
                continue
            if not raw_site.startswith("http"):
                raw_site = "https://" + raw_site
            website = normalize_website(raw_site)

            name = (hit.get("name") or "").strip()
            if not name:
                continue

            yc_slug   = hit.get("slug", "")
            one_liner = (hit.get("one_liner") or "").strip()[:300] or None
            long_desc = (hit.get("long_description") or hit.get("description") or "").strip() or None
            careers   = f"https://www.ycombinator.com/companies/{yc_slug}#jobs" if yc_slug else None
            locations = hit.get("all_locations") or []
            location  = locations[0] if locations else None

            company_year = founded_year
            for field in ("founded_date", "launched_at", "year_founded"):
                raw_year = hit.get(field)
                if raw_year:
                    try:
                        company_year = int(str(raw_year)[:4])
                        break
                    except (ValueError, TypeError):
                        pass

            company_rows.append({
                "name": name,
                "website": website,
                "slug": make_slug(name),
                "one_line_pitch": one_liner or long_desc,
                "long_description": long_desc,
                "founded_year": company_year,
                "careers_page_url": careers,
                "location": location,
                "intern_hiring_status": "hiring",
                "source_fund": f"Y Combinator {batch_name}",
            })

            if yc_slug:
                slug_website_pairs.append((yc_slug, website))

        # Upsert companies
        if company_rows:
            result = sb_upsert("companies", company_rows, "website")
            upserted = result if isinstance(result, list) else []
            for r in upserted:
                website_to_id[normalize_website(r["website"])] = r["id"]
            total_companies += len(upserted)
            print(f"  Upserted {len(upserted)} companies", flush=True)

    # ── Scrape YC pages concurrently (founders + social + tags) ───
    print(f"\nScraping {len(slug_website_pairs)} YC company pages...", flush=True)

    def fetch_one(pair):
        yc_slug, website = pair
        return yc_slug, website, scrape_yc_page(yc_slug)

    founder_rows  = []
    company_patches: list[tuple[str, dict]] = []  # (website, patch_data)
    done = 0

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_one, p): p for p in slug_website_pairs}
        for future in as_completed(futures):
            done += 1
            if done % 50 == 0:
                print(f"  ... {done}/{len(slug_website_pairs)} pages scraped", flush=True)
            try:
                yc_slug, website, data = future.result()
            except Exception:
                continue

            company_id = website_to_id.get(website)
            if not company_id:
                continue

            # Founders
            for f in data["founders"]:
                founder_rows.append({
                    "company_id":   company_id,
                    "name":         f["name"],
                    "title":        f.get("title"),
                    "linkedin_url": f.get("linkedin_url"),
                    "bio":          f.get("bio"),
                })

            # Social + tags patch
            patch: dict = {}
            if data.get("twitter_url"):  patch["twitter_url"]  = data["twitter_url"]
            if data.get("linkedin_url"): patch["linkedin_url"] = data["linkedin_url"]
            if data.get("tags"):         patch["tags"]         = data["tags"]
            if patch:
                company_patches.append((website, patch))

    print(f"  {len(founder_rows)} founder records, {len(company_patches)} companies with social/tags.", flush=True)

    # Upsert founders in batches of 200
    if founder_rows:
        batch_size = 200
        for i in range(0, len(founder_rows), batch_size):
            batch = founder_rows[i:i + batch_size]
            sb_upsert("founders", batch, "company_id,name")
            total_founders += len(batch)
        print(f"  Saved {total_founders} founders.", flush=True)

    # Patch companies with social links + tags
    if company_patches:
        patched = 0
        for website, patch in company_patches:
            try:
                qs = urllib.parse.urlencode({"website": f"eq.{website}"})
                url = f"{SUPABASE_URL}/rest/v1/companies?{qs}"
                data_bytes = json.dumps(patch).encode()
                req = urllib.request.Request(url, data=data_bytes, method="PATCH", headers={
                    **SB_HEADERS,
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                })
                urllib.request.urlopen(req, timeout=15)
                patched += 1
            except Exception:
                pass
        print(f"  Patched {patched} companies with social/tags.", flush=True)

    print(f"\n{'='*50}")
    print(f"  Companies upserted : {total_companies}")
    print(f"  Founders saved     : {total_founders}")
    print(f"{'='*50}", flush=True)

if __name__ == "__main__":
    main()
