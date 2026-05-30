"""READ-ONLY live evaluation against production Supabase (user-authorized).
Loads companies + events (SELECT only, no writes), reports volume, and if there
is enough click signal, trains + evaluates the ranker on the real data."""
import os
from collections import Counter
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(Path(__file__).resolve().parent.parent / "scraper" / ".env")
url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
client = create_client(url, key)

def fetch_all(table):
    rows, start, step = [], 0, 1000
    while True:
        chunk = client.table(table).select("*").range(start, start + step - 1).execute().data
        rows.extend(chunk)
        if len(chunk) < step:
            break
        start += step
    return pd.DataFrame(rows)

companies = fetch_all("companies")
events = fetch_all("events")
print(f"LIVE companies={len(companies)}  events={len(events)}")
if not events.empty:
    print("event_type distribution:", dict(Counter(events.get("event_type", []))))
    print("distinct sessions:", events["session_id"].nunique() if "session_id" in events else "n/a")

click_types = {"company_click", "click", "apply_click", "save"}
n_click = int(events["event_type"].isin(click_types).sum()) if not events.empty else 0
n_sessions = events["session_id"].nunique() if ("session_id" in events and not events.empty) else 0
print(f"click events={n_click}  sessions={n_sessions}")

if n_click >= 30 and n_sessions >= 20:
    print("\nEnough signal -- training on LIVE data:\n")
    from ranker.features import engineer, build_preprocessor
    from ranker.metrics import evaluate
    from sklearn.model_selection import GroupShuffleSplit
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    frame = engineer(companies, events)
    gss = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=0)
    tr, te = next(gss.split(frame, frame["y"], groups=frame["session_id"]))
    feat = [c for c in frame.columns if c not in ("session_id", "company_id", "y")]
    pipe = Pipeline([("p", build_preprocessor()), ("c", LogisticRegression(max_iter=1000, class_weight="balanced"))])
    pipe.fit(frame.iloc[tr][feat], frame.iloc[tr]["y"])
    s = pipe.predict_proba(frame.iloc[te][feat])[:, 1]
    print("LIVE metrics:", evaluate(frame.iloc[te], s, k=5))
else:
    print("\nNot enough live click signal yet for stable ranking metrics.")
    print("The pipeline is wired and correct; rerun once the events table has more clicks.")
