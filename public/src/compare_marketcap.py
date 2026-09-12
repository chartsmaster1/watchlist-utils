"""Compare checked-in stocks.json (from manual CompaniesMarketCap.csv)
vs live scrape of companiesmarketcap.com. Read-only — writes nothing.

Usage: python3 compare_marketcap.py [--pages 3] [--delay 2]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common.marketcap_live import scrape_companies

DATA = Path(__file__).resolve().parent.parent / "data"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=3)
    ap.add_argument("--delay", type=float, default=2.0)
    args = ap.parse_args()

    checked = {r["Ticker"]: r for r in json.load(open(DATA / "stocks.json"))}
    print(f"checked-in stocks.json: {len(checked)} tickers")

    live = scrape_companies(max_pages=args.pages, delay=args.delay)
    live_map = {r["Ticker"]: r for _, r in live.to_dict(orient="index").items()}
    print(f"live scrape ({args.pages} pages): {len(live_map)} rows, "
          f"ranks {live['Rank'].min()}-{live['Rank'].max()}")

    only_checked = sorted(set(checked) - set(live_map))
    only_live = sorted(set(live_map) - set(checked))
    both = set(checked) & set(live_map)
    print(f"\nchecked-only (not in top live pages): {len(only_checked)} e.g. {only_checked[:10]}")
    print(f"live-only (new tickers): {len(only_live)} e.g. {only_live[:10]}")

    # market-cap drift on overlap
    drifts = []
    for t in both:
        old, new = checked[t]["MarketCap"], live_map[t]["MarketCap"]
        if old and new:
            drifts.append((t, (new - old) / old))
    drifts.sort(key=lambda x: abs(x[1]), reverse=True)
    print(f"\noverlap: {len(both)} tickers; top 15 movers (live vs checked-in):")
    for t, d in drifts[:15]:
        print(f"  {t:<12} {d:+.1%}  checked={checked[t]['MarketCap']:,} live={live_map[t]['MarketCap']:,}")

    # coverage check: do live top-N cover all index constituents?
    idx_tickers = set()
    for fn in ["s&p500.json", "dow.json", "nasdaq.json", "russell_1000.json"]:
        p = DATA / fn
        if p.exists():
            idx_tickers |= {r["Ticker"] for r in json.load(open(p))}
    missing = sorted(idx_tickers - set(live_map))
    print(f"\nindex constituents total: {len(idx_tickers)}; "
          f"missing from live top-{args.pages * 100}: {len(missing)} e.g. {missing[:15]}")
    if not missing:
        print("OK: live scrape covers all index tickers — sufficient as stocks.json source.")
    else:
        print("TIP: raise --pages until missing=0 (small-caps need deeper pages).")


if __name__ == "__main__":
    main()
