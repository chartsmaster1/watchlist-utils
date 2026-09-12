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
    if not rows:
        raise ValueError("no company rows parsed - page layout changed")
    return rows


def scrape_companies(max_pages=20, delay=DELAY, need_tickers=None):
    """Scrape top max_pages (100 rows each). Early-stop when need_tickers covered."""
    rows = []
    sess = requests.Session()
    sess.headers.update(UA)
    for page in range(1, max_pages + 1):
        if page == 1:
            url = "https://companiesmarketcap.com/"
        else:
            url = BASE.format(n=page)
        r = sess.get(url, timeout=30)
        r.raise_for_status()
        rows.extend(_parse_page_html(r.text))
        if need_tickers:
            have = set(x["Ticker"] for x in rows)
            if need_tickers <= have:
                break
        time.sleep(delay)
    df = pd.DataFrame(rows).dropna(subset=["Ticker"]).query("MarketCap > 0")
    return df.sort_values("Rank").reset_index(drop=True)
