"""Derive the Top 100 US and Top 100 World lists from the stocks file.

No new source: both lists are slices of public/data/stocks.json, which
the companies job refreshes earlier in the same run (main.py runs this
job after 'companies'). Top 100 World is the 100 largest companies by
market cap; Top 100 US is the 100 largest with Country == 'United States'.
Sorted by MarketCap descending, nulls last. Raises on failure so
main.py records the job instead of silently shipping stale files.
"""

import json
import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')


def _write_dataset(rows, file_name, data_dir):
    """Write one ranked list as JSON + CSV twin (same rows, same order)."""
    if len(rows) != 100:
        raise ValueError(f'{file_name}: expected 100 rows, got {len(rows)}')
    tickers = [r['Ticker'] for r in rows]
    if any(not t or t == 'nan' for t in tickers):
        raise ValueError(f'{file_name}: blank ticker')
    if len(set(tickers)) != len(tickers):
        raise ValueError(f'{file_name}: duplicate tickers')
    caps = [r['MarketCap'] for r in rows]
    ordered = [c for c in caps if c is not None]
    if ordered != sorted(ordered, reverse=True):
        raise ValueError(f'{file_name}: not sorted by MarketCap desc')
    if any(c is None for c in caps) and caps[-1] is not None:
        raise ValueError(f'{file_name}: null MarketCap not last')
    file_path = data_dir / (file_name + '.json')
    with file_path.open('w') as f:
        json.dump(rows, f)
    df = pd.DataFrame(rows)
    df.to_csv(data_dir / (file_name + '.csv'), index=False, encoding='utf-8-sig')
    print(f'{file_name}: {len(rows)} rows, top {tickers[0]} '
          f'({caps[0]:,}) .. #{len(rows)} {tickers[-1]} ({caps[-1]:,})')


def _ranked(df, label):
    df = df.sort_values(by='MarketCap', ascending=False).head(100).reset_index(drop=True)
    rows = []
    for i, r in df.iterrows():
        rows.append({
            'Rank': int(i) + 1,
            'Name': r['Name'],
            'Ticker': r['Ticker'],
            'MarketCap': int(r['MarketCap']) if pd.notna(r['MarketCap']) else None,
            'Country': r['Country'],
        })
    return rows


def read_prep_top100():
    data_dir = Path(__file__).resolve().parent.parent / 'data'
    stocks_path = data_dir / 'stocks.json'
    if not stocks_path.exists():
        raise ValueError('stocks.json missing — the companies job must run first')
    stocks = pd.read_json(stocks_path)
    if stocks.empty or 'MarketCap' not in stocks.columns or 'Country' not in stocks.columns:
        raise ValueError('stocks.json has an unexpected shape')
    stocks = stocks.dropna(subset=['Ticker'])
    stocks['Ticker'] = stocks['Ticker'].astype(str).str.strip().str.upper()

    world = _ranked(stocks, 'Top 100 World')
    _write_dataset(world, 'top100_world', data_dir)

    us = stocks[stocks['Country'] == 'United States']
    if len(us) < 100:
        raise ValueError(f'stocks.json has only {len(us)} United States rows, need 100')
    us_top = _ranked(us, 'Top 100 US')
    _write_dataset(us_top, 'top100_us', data_dir)


if __name__ == '__main__':
    read_prep_top100()
