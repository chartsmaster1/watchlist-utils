"""Live scraper for https://companiesmarketcap.com (server-rendered, 100 rows/page).

Parses raw HTML with regex (pd.read_html mangles the Name/Ticker join).
Reads exact market cap from td[data-sort] (no $X.XT string parsing).
Polite: real User-Agent, 2s delay, stop-early once target tickers covered.
"""
import re
import time
import requests
import pandas as pd
from typing import Optional, Set

BASE = "https://companiesmarketcap.com/page/{n}/"
UA = {"User-Agent": "watchlist-utils/1.0 (research; contact watchlist-static-files)"}
DELAY = 2.0

RANK_RE = '<td class="rank-td[^"]*" data-sort="(\\d+)"[^>]*>'
NAME_RE = '<div class="company-name">(.*?)</div>'
CODE_RE = '<div class="company-code">.*?</span>(.*?)</div>'
MCAP_RE = '<td class="td-right" data-sort="(\\d+)"[^>]*>'
CTRY_RE = '<span class="responsive-hidden">(.*?)</span>'

ROW_RE = re.compile(
    RANK_RE + r".*?" + NAME_RE + CODE_RE + r".*?" + MCAP_RE + r".*?" + CTRY_RE,
    re.S,
)


def _parse_page_html(html):
    rows = []
    for rank, name, ticker, mcap, country in ROW_RE.findall(html):
        rows.append({
            "Rank": int(rank),
            "Name": name.strip(),
            "Ticker": ticker.strip(),
            "MarketCap": int(mcap),
            "Country": country.strip(),
        })
    return rows


def scrape_companies(max_pages=200, delay=DELAY, need_tickers=None):
    """Scrape up to max_pages (capped at 200), stopping at the end of the list."""
    rows = []
    sess = requests.Session()
    sess.headers.update(UA)
    max_pages = min(max_pages, 200)
    for page in range(1, max_pages + 1):
        if page == 1:
            url = "https://companiesmarketcap.com/"
        else:
            url = BASE.format(n=page)
        r = sess.get(url, timeout=30)
        if r.status_code == 404:
            if rows:
                break
            r.raise_for_status()
        r.raise_for_status()
        page_rows = _parse_page_html(r.text)
        if not page_rows:
            if rows:
                break
            raise ValueError("no company rows parsed - page layout changed")
        rows.extend(page_rows)
        if need_tickers:
            have = set(x["Ticker"] for x in rows)
            if need_tickers <= have:
                break
        if page < max_pages:
            time.sleep(delay)
    df = pd.DataFrame(rows).dropna(subset=["Ticker"]).query("MarketCap > 0")
    return df.sort_values("Rank").reset_index(drop=True)
