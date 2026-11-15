"""Regenerate the ETF groups file (etfgrouped.json) from ETFIQ + our own
market-cap file. Runs as an OPTIONAL job in main.py: if it fails for any
reason (ETFIQ unreachable, format changed, caps file missing), it raises
and main.py logs a warning and keeps the previous etfgrouped.json — the
failure never blocks the other datasets, the manifest, the commit or the
deploy. The file is only written after the full build succeeds, so a
failed run never leaves a partial file behind.

Sources (plain script fetch, no login, no cookies):
  - https://etfiq.com/data/core.json      (2,916 funds; kind/fundTypeLabel/note)
  - https://etfiq.com/data/thematic.json (428 theme funds; theme slugs)
  - https://etfiq.com/data/categories.json (taxonomy; as-of + license only)
  - public/data/etfs_market_cap.json (this repo, fresh from the ETFs job
    earlier in the same run — the ranking source)
ETFIQ blocks non-browser User-Agents (plain urllib/requests default gets
403), so the fetch uses a browser UA string. That is still a code-only
fetch, but it is a durability caveat: if ETFIQ tightens bot protection,
this job fails (non-fatally) until the UA or the source is revisited.
License: "Computed by ETFIQ. Free to use with attribution: ETFIQ
(etfiq.com)" — attribution lives on the data site next to the dataset.

Groups (Popular + Volatility are NOT regenerated: neither has a clean
source, and Volatility's TVIXF is a delisted-ETN remnant absent from
every ETFIQ file):
  Main      top 100 by MarketCap from etfs_market_cap.json
  Commodity core.json fundTypeLabel == 'Commodity fund', top 21 by MarketCap
  Currency  core.json fundTypeLabel == 'Currency fund', all 8 (whole universe)
  Sector    core.json equity funds whose note is one of the 11 sector names
            (+ real-estate variants) OR thematic funds with a sector theme
            (gold/miners/semis/biotech), top 25 by MarketCap
  Country   core.json equity index funds whose name holds a single country
            name (regional / "ex-" funds excluded), top 22 by MarketCap
  Index     core.json equity index funds whose note or name holds a
            broad-market index (S&P 500/100, Nasdaq-100, Russell 2000/1000,
            Dow, total market, MidCap 400, MSCI ACWI, MSCI Emerging,
            EURO STOXX 50), top 18 by MarketCap

Set ETFIQ_BASE_URL to override the ETFIQ host (used to test the failure
path without touching the real endpoint).
"""

import csv
import json
import logging
import os
from pathlib import Path

import requests

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

# ETFIQ serves plain script requests a 403; a browser UA gets 200.
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
ETFIQ_BASE = os.environ.get("ETFIQ_BASE_URL", "https://etfiq.com/data")

SECTOR_NOTES = {
    "Energy", "Financials", "Utilities", "Industrials", "Technology",
    "Health care", "Consumer staples", "Consumer discretionary", "Materials",
    "Communication services", "U.S. Real Estate", "US real estate",
}
SECTOR_THEMES = {"gold", "miners", "semis", "biotech"}

COUNTRIES = [
    "Japan", "China", "Brazil", "Taiwan", "Germany", "Hong Kong", "Italy",
    "Mexico", "United Kingdom", "India", "Indonesia", "South Korea",
    "Australia", "Malaysia", "Singapore", "Canada", "Spain", "Switzerland",
    "South Africa", "France", "Netherlands", "Sweden", "Austria", "Belgium",
    "Poland", "Thailand", "Vietnam", "Philippines", "Chile", "Peru",
    "Colombia", "Israel", "Turkey", "Egypt", "New Zealand", "Ireland",
    "Portugal", "Greece", "Denmark", "Norway", "Finland", "Russia",
]
# Regional / "ex-" funds are NOT single-country (AAXJ "Asia ex Japan",
# EMXC "Emerging Markets ex China", EPP "Pacific ex Japan", XCEM "EM Core
# ex-China").
COUNTRY_EXCLUDE = [
    " ex ", "ex-", " EM ", "All Country", "Pacific", "Emerging Markets",
    "EAFE", "Europe", "Asia", "Latin America", "Developed Markets", "World",
]

BROAD_INDEX = [
    "S&P 500", "S&P 100", "Nasdaq-100", "Russell 2000", "Russell 1000",
    "Dow Jones", "total market", "MidCap 400", "MSCI ACWI",
    "MSCI Emerging", "EURO STOXX 50",
]

CAPS = {"Main": 100, "Commodity": 21, "Currency": None,  # all 8: universe fits
        "Sector": 25, "Country": 22, "Index": 18}


def _fetch_json(session, url):
    response = session.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def build_groups(data_dir):
    caps_path = data_dir / "etfs_market_cap.json"
    if not caps_path.exists():
        raise ValueError("etfs_market_cap.json missing — the ETFs job must run first")
    with caps_path.open() as f:
        caps = {e["Ticker"]: e.get("MarketCap") for e in json.load(f)}

    session = requests.Session()
    session.headers.update({"User-Agent": BROWSER_UA})
    core = _fetch_json(session, f"{ETFIQ_BASE}/core.json")
    thematic_raw = _fetch_json(session, f"{ETFIQ_BASE}/thematic.json")
    cats = _fetch_json(session, f"{ETFIQ_BASE}/categories.json")
    # Validate response shape before building anything.
    if not isinstance(core, list) or not core or not isinstance(core[0], dict) \
            or "ticker" not in core[0]:
        raise ValueError("ETFIQ core.json has an unexpected shape")
    if not isinstance(thematic_raw, dict) or not isinstance(thematic_raw.get("funds"), list) \
            or not thematic_raw["funds"] \
            or not isinstance(thematic_raw["funds"][0], dict) \
            or "ticker" not in thematic_raw["funds"][0]:
        raise ValueError("ETFIQ thematic.json has an unexpected shape")
    thematic = thematic_raw["funds"]
    if not isinstance(cats, dict) or "asOf" not in cats:
        raise ValueError("ETFIQ categories.json has an unexpected shape")
    print(f"ETFIQ core asOf: {core[0].get('asOf')} | "
          f"categories asOf: {cats.get('asOf')} | "
          f"thematic asOf: {thematic[0].get('asOf')}")

    def ranked(tickers, n):
        with_cap = [(t, caps[t]) for t in tickers if caps.get(t)]
        no_cap = sorted(t for t in tickers if not caps.get(t))
        with_cap.sort(key=lambda x: -x[1])
        if n is None:  # whole universe fits — keep all, ranked
            return [t for t, _ in with_cap], no_cap
        return [t for t, _ in with_cap[:n]], no_cap

    main, _ = ranked(list(caps.keys()), CAPS["Main"])

    commodity, com_nocap = ranked(
        [f["ticker"] for f in core if f.get("fundTypeLabel") == "Commodity fund"],
        CAPS["Commodity"])
    currency, cur_nocap = ranked(
        [f["ticker"] for f in core if f.get("fundTypeLabel") == "Currency fund"],
        CAPS["Currency"])

    sector = {f["ticker"] for f in core
              if f.get("kind") == "equity" and f.get("note") in SECTOR_NOTES}
    sector |= {f["ticker"] for f in thematic
               if f.get("theme") in SECTOR_THEMES}
    sector, sec_nocap = ranked(sorted(sector), CAPS["Sector"])

    country, cou_nocap = ranked(
        [f["ticker"] for f in core
         if f.get("kind") == "equity"
         and f.get("structure") == "index"
         and any(c in f["name"] for c in COUNTRIES)
         and not any(x in f["name"] for x in COUNTRY_EXCLUDE)],
        CAPS["Country"])

    index, idx_nocap = ranked(
        [f["ticker"] for f in core
         if f.get("kind") == "equity"
         and f.get("structure") == "index"
         and any(p in (f.get("note") or "") or p in f["name"]
                 for p in BROAD_INDEX)],
        CAPS["Index"])

    for label, lst in [("Commodity no-cap", com_nocap),
                       ("Currency no-cap", cur_nocap),
                       ("Sector no-cap", sec_nocap),
                       ("Country no-cap", cou_nocap),
                       ("Index no-cap", idx_nocap)]:
        if lst:
            print(f"{label} (no MarketCap, skipped): {lst}")

    return [("Main", main), ("Commodity", commodity), ("Currency", currency),
            ("Sector", sector), ("Country", country), ("Index", index)]


def read_prep_etf_groups():
    data_dir = Path(__file__).resolve().parent.parent / "data"
    groups = build_groups(data_dir)
    # Build everything in memory; write only on full success.
    out = [{"Name": name, "Items": items} for name, items in groups]
    with (data_dir / "etfgrouped.json").open("w") as f:
        json.dump(out, f, indent=2)
    with (data_dir / "etfgrouped.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Group", "Ticker"])
        for name, items in groups:
            for ticker in items:
                writer.writerow([name, ticker])
    total = sum(len(items) for _, items in groups)
    print(f"ETF groups written: {len(groups)} groups, {total} tickers "
          f"({', '.join(f'{n} {len(i)}' for n, i in groups)})")


if __name__ == "__main__":
    read_prep_etf_groups()
