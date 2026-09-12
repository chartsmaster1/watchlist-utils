"""Shared Wikipedia fetch helper: schema-based table selection, not hard index."""
import pandas as pd
import requests
from io import StringIO

USER_AGENT = "watchlist-utils/1.0 (contact: watchlist-static-files; python-requests)"

WIKI = {
    # key: (url, required-columns)
    # NOTE: Nasdaq/Dow/Russell component tables moved off the overview pages
    # onto dedicated "List_of_..." pages — the old overview URLs no longer
    # contain a constituents table at all (this is exactly what broke [4]/[2]/[3]).
    "sp500": (
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        {"Symbol", "Security", "GICS Sector"},
    ),
    "nasdaq100": (
        "https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies",
        {"Company", "Ticker"},
    ),
    "dow": (
        "https://en.wikipedia.org/wiki/List_of_Dow_Jones_Industrial_Average_companies",
        {"Company", "Symbol"},
    ),
    "russell1000": (
        "https://en.wikipedia.org/wiki/List_of_Russell_1000_companies",
        {"Company", "Symbol"},
    ),
}

# Old hard indexes used by prep_*.py (for comparison / regression check)
# + old (now-stale) overview URLs the legacy code hit.
LEGACY = {
    "sp500": ("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", 0),
    "nasdaq100": ("https://en.wikipedia.org/wiki/Nasdaq-100", 4),
    "dow": ("https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average", 2),
    "russell1000": ("https://en.wikipedia.org/wiki/Russell_1000_Index", 3),
}


def _download(url: str) -> str:
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    r.raise_for_status()
    return r.text


def fetch_tables(key: str) -> list:
    url, _ = WIKI[key]
    html = _download(url)
    return pd.read_html(StringIO(html), flavor="lxml")


def fetch_by_schema(key: str):
    """Return (table, matched_index) selecting by required columns."""
    _, required = WIKI[key]
    tables = fetch_tables(key)
    normed = []
    for t in tables:
        t = t.copy()
        t.columns = [str(c).strip() for c in t.columns]
        normed.append(t)
    for i, t in enumerate(normed):
        if required <= set(t.columns):
            return t, i
    raise ValueError(
        f"[wiki:{key}] layout changed. Need {sorted(required)}, "
        f"got {[list(t.columns)[:10] for t in normed]}"
    )


def fetch_legacy(key: str):
    """Old behaviour: old URL + blind index select (with UA added so the
    request itself isn't 403-blocked) — for before/after comparison."""
    url, idx = LEGACY[key]
    html = _download(url)
    tables = pd.read_html(StringIO(html), flavor="lxml")
    t = tables[idx].copy()
    t.columns = [str(c).strip() for c in t.columns]
    return t, idx
