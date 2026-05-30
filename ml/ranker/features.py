"""Feature engineering for the internship ranker.

Turns raw `companies` rows (joined with light session context) into a model
matrix. Demonstrates real feature work: categorical encoding, log-scaling of
funding, recency decay, recruiter/alumni signals, and a session-personalization
interaction (does this company match the session's preferred sector).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

CATEGORICAL = ["sector", "stage", "headcount_range", "location", "intern_hiring_status"]
NUMERIC = [
    "log_last_round",
    "recency_decay",
    "company_age",
    "vandy_alumni_count",
    "has_careers_page",
    "sector_match",
]


def _col(df: pd.DataFrame, name: str, default) -> pd.Series:
    """df[name] if present, else a Series of `default` aligned to df.index.

    Guards the live path: the production `companies` table does not carry
    `founded_year`, `vandy_alumni_count`, or `has_careers_page`, so a plain
    df.get(name, default) would return a scalar and break .fillna()/.astype().
    """
    if name in df.columns:
        return df[name]
    return pd.Series([default] * len(df), index=df.index)


def engineer(companies: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Join events to company features and build the per-(session, company) frame.

    Label `y` = 1 if the company was clicked in that session, else 0.
    Returns a frame with: session_id, company_id, group key, engineered features, y.
    Robust to either the synthetic schema or the live Supabase `companies`/`events`.
    """
    comp = companies.copy()

    # --- company-level engineered features -----------------------------------
    comp["log_last_round"] = np.log1p(_col(comp, "last_round_size_usd", 0).fillna(0).astype(float))

    # recency: prefer days_since_round; else derive from last_round_date.
    if "days_since_round" not in comp.columns:
        if "last_round_date" in comp.columns:
            d = pd.to_datetime(comp["last_round_date"], errors="coerce")
            comp["days_since_round"] = (pd.Timestamp.now().normalize() - d).dt.days
        else:
            comp["days_since_round"] = 365
    comp["days_since_round"] = pd.to_numeric(comp["days_since_round"], errors="coerce").fillna(365).clip(lower=0)
    comp["recency_decay"] = np.exp(-comp["days_since_round"] / 365.0)  # 1.0 = fresh

    cur_year = pd.Timestamp.now().year
    comp["company_age"] = (cur_year - _col(comp, "founded_year", cur_year).fillna(cur_year).astype(float)).clip(lower=0)
    comp["vandy_alumni_count"] = _col(comp, "vandy_alumni_count", 0).fillna(0).astype(float)

    # has_careers_page: explicit flag if present, else derive from careers_page_url.
    if "has_careers_page" in comp.columns:
        comp["has_careers_page"] = comp["has_careers_page"].fillna(False).astype(float)
    elif "careers_page_url" in comp.columns:
        comp["has_careers_page"] = comp["careers_page_url"].notna().astype(float)
    else:
        comp["has_careers_page"] = 0.0

    for col in CATEGORICAL:
        if col not in comp.columns:
            comp[col] = "unknown"
        comp[col] = comp[col].fillna("unknown").astype(str)

    # --- join clicks ----------------------------------------------------------
    ev = events.copy()
    click_types = {"company_click", "click", "apply_click", "save"}
    ev["clicked"] = ev["event_type"].isin(click_types).astype(int)
    # Collapse to one row per (session, company): clicked if any click event.
    agg = {"clicked": ("clicked", "max")}
    if "fav_sector" in ev.columns:
        agg["fav_sector"] = ("fav_sector", "first")
    pair = ev.groupby(["session_id", "company_id"], as_index=False).agg(**agg)

    frame = pair.merge(comp, left_on="company_id", right_on="id", how="inner")

    # session personalization interaction (only when a preferred sector exists)
    if "fav_sector" in frame.columns:
        frame["sector_match"] = (frame["sector"] == frame["fav_sector"]).astype(float)
    else:
        frame["sector_match"] = 0.0

    frame = frame.rename(columns={"clicked": "y"})
    keep = ["session_id", "company_id", "y"] + CATEGORICAL + NUMERIC
    return frame[keep].reset_index(drop=True)


def build_preprocessor() -> ColumnTransformer:
    """sklearn transformer: one-hot the categoricals, scale the numerics."""
    return ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
            ("num", StandardScaler(), NUMERIC),
        ],
        remainder="drop",
    )
