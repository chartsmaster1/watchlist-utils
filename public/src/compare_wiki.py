"""Before/after comparison for Wikipedia table selection (read-only, writes nothing).

Original behaviour: pd.read_html(OVERVIEW_URL)[HARD_INDEX] with no User-Agent.
New behaviour:     common.wiki.fetch_by_schema(key) — dedicated List_of_... URL,
                   table picked by required columns.

Also compares the resulting ticker set vs the checked-in public/data/*.json.
"""
import json
import sys
from io import StringIO
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common.wiki import LEGACY, WIKI, _download

DATA = Path(__file__).resolve().parent.parent / "data"
CHECKED_IN = {"sp500": "s&p500.json", "nasdaq100": "nasdaq.json",
              "dow": "dow.json", "russell1000": "russell_1000.json"}
# ticker column per legacy prep script (Symbol vs Ticker differs per page)
TICK_COL = {"sp500": "Symbol", "nasdaq100": "Ticker",
            "dow": "Symbol", "russell1000": "Symbol"}


def tickers_of(df: pd.DataFrame, col: str) -> set:
    if col not in df.columns:
        return set()
    return {str(x).strip() for x in df[col].dropna().tolist() if str(x).strip()}


def main():
    print(f"{'index':<10} {'method':<8} {'idx':<4} {'cols-ok':<8} {'n_sym':<7} notes")
    print("-" * 100)
    for key in WIKI:
        new_url, required = WIKI[key]
        leg_url, leg_idx = LEGACY[key]

        # --- legacy: old URL + blind index (+UA only so download works) ---
        try:
            leg_tables = pd.read_html(StringIO(_download(leg_url)), flavor="lxml")
            for t in leg_tables:
                t.columns = [str(c).strip() for c in t.columns]
            leg_t = leg_tables[leg_idx]
            col = TICK_COL[key]
            leg_ok = col in leg_t.columns
            leg_syms = tickers_of(leg_t, col)
            leg_note = f"url=.../{leg_url.rsplit('/', 1)[-1]} cols={list(leg_t.columns)[:6]}"
        except Exception as e:
            leg_ok, leg_syms, leg_note = False, set(), f"FAILED: {repr(e)[:160]}"

        # --- new: List_of_... URL + schema match ---
        try:
            new_tables = pd.read_html(StringIO(_download(new_url)), flavor="lxml")
            for t in new_tables:
                t.columns = [str(c).strip() for c in t.columns]
            new_idx, new_syms = -1, set()
            for i, t in enumerate(new_tables):
                if required <= set(t.columns):
                    new_idx, new_syms = i, tickers_of(t, TICK_COL[key])
                    break
            new_ok = new_idx >= 0
            new_note = f"url=.../{new_url.rsplit('/', 1)[-1]} required={sorted(required)}"
        except Exception as e:
            new_idx, new_ok, new_syms, new_note = -1, False, set(), f"FAILED: {repr(e)[:160]}"

        print(f"{key:<10} {'legacy':<8} {leg_idx:<4} {str(leg_ok):<8} {len(leg_syms):<7} {leg_note}")
        print(f"{key:<10} {'schema':<8} {new_idx:<4} {str(new_ok):<8} {len(new_syms):<7} {new_note}")
        print(f"  -> symbol diff legacy-vs-schema: legacy-only={len(leg_syms - new_syms)} "
              f"schema-only={len(new_syms - leg_syms)}")

        p = DATA / CHECKED_IN[key]
        if p.exists():
            checked = {r["Ticker"] for r in json.load(open(p))}
            print(f"  -> vs checked-in {CHECKED_IN[key]} ({len(checked)}): "
                  f"legacy Δ={len(checked ^ leg_syms)} | schema Δ={len(checked ^ new_syms)} "
                  f"(missing={len(checked - new_syms)}, extra={len(new_syms - checked)})")
            if checked - new_syms:
                print(f"     dropped from live wiki: {sorted(checked - new_syms)[:15]}")
            if new_syms - checked:
                print(f"     added on live wiki: {sorted(new_syms - checked)[:15]}")
    print("-" * 100)
    print("Verdict: schema select tracks the table if Wikipedia inserts/reorders tables; "
          "legacy hard index silently reads the wrong table.")


if __name__ == "__main__":
    main()
