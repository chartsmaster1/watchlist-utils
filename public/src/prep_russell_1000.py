"""Russell 1000 constituents with fund weights.

Base membership: Wikipedia 'List of Russell 1000 companies' via
common/wiki.py, sorted by market cap from stocks.json (existing behaviour).

Weights: iShares Russell 1000 ETF (IWB) holdings published by
companiesmarketcap.com — the same site family as the stocks.json scrape.
The page is a single server-rendered table (Weight %, Name, Ticker,
Shares Held); a plain scripted fetch returns it, no login or JS needed.

IWB rows that are not index constituents (cash, futures, rights,
collateral) are excluded by ticker shape + name keywords and reported;
genuine new constituents are added, with Sector enriched from the other
local datasets when available. Wikipedia rows absent from IWB keep
Weight null and are reported, never dropped.
"""

import io
import json
import re
import requests
import pandas as pd
import numpy as np
import logging
from pathlib import Path
from common.wiki import fetch_by_schema
from common.tickers import normalize_tickers, report_missing_market_caps

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

IWB_URL = 'https://companiesmarketcap.com/ishares-russell-1000-etf/holdings/'
UA = {'User-Agent': 'watchlist-utils/1.0 (research; contact watchlist-static-files)'}

# Plain US stock tickers: 1-5 letters, optional .class (e.g. BRK.B).
# Kills futures (ESZ6), cash balances (ETD_USD), rights (UWMC-R-W).
_TICKER_RE = re.compile(r'^[A-Z]{1,5}(\.[A-Z])?$')
# Names of non-stock fund rows: cash, futures, collateral, money-market.
_JUNK_NAME_WORDS = ('CASH', 'EMINI', 'FUTURE', 'COLLATERAL', 'TREASURY', 'SWAP')

# Local datasets that carry a Sector column, for enriching IWB-only rows.
SECTOR_SOURCES = ('spy.json', 'nasdaq.json', 'dia.json', 'schd.json', 'russell_1000.json')


def _ticker_key(ticker):
    """Join key: uppercase alphanumerics only ('BRK B' == 'BRK.B')."""
    return re.sub(r'[^A-Z0-9]', '', str(ticker).upper())


def _is_stock_row(name, ticker):
    """True for a genuine stock holding; False for cash/futures/rights rows."""
    key = _ticker_key(ticker)
    if not _TICKER_RE.match(key):
        return False
    upper_name = str(name).upper()
    return not any(word in upper_name for word in _JUNK_NAME_WORDS)


def fetch_iwb_weights():
    """Fetch the IWB holdings table; return {ticker_key: (ticker, weight)}."""
    r = requests.get(IWB_URL, headers=UA, timeout=30)
    r.raise_for_status()
    tables = pd.read_html(io.StringIO(r.text))
    if len(tables) != 1:
        raise ValueError(f'IWB page: expected 1 table, found {len(tables)}')
    df = tables[0]
    expected = ['Weight %', 'Name', 'Ticker', 'Shares Held']
    if list(df.columns) != expected:
        raise ValueError(f'IWB page: columns changed: {list(df.columns)}')
    if len(df) < 900:
        raise ValueError(f'IWB page: only {len(df)} rows, expected ~1000')
    df = df.dropna(subset=['Ticker'])
    df['Weight'] = (
        df['Weight %'].astype(str).str.rstrip('%').astype(float).round(2)
    )
    total = float(df['Weight'].sum())
    if not 95.0 <= total <= 105.0:
        raise ValueError(f'IWB weights sum to {total}, expected ~100')
    weights = {}
    for _, row in df.iterrows():
        key = _ticker_key(row['Ticker'])
        if key in weights:
            raise ValueError(f'IWB page: duplicate ticker {row["Ticker"]}')
        weights[key] = (str(row['Ticker']).strip(), float(row['Weight']),
                        str(row['Name']).strip(), float(row['Shares Held']))
    return weights


def _sector_map(data_dir):
    """Ticker key -> Sector from the other local datasets (first match wins)."""
    sectors = {}
    for filename in SECTOR_SOURCES:
        path = data_dir / filename
        if not path.exists():
            continue
        try:
            rows = json.loads(path.read_text())
        except Exception as e:
            print(f'Warning: could not read {filename} for sector lookup: {e}')
            continue
        for row in rows:
            if not isinstance(row, dict) or 'Sector' not in row:
                continue
            key = _ticker_key(row.get('Ticker', ''))
            if key and key not in sectors and row['Sector']:
                sectors[key] = row['Sector']
    return sectors


def sort_by_market_cap(df):
    """
    Sorts the DataFrame by MarketCap in descending order.
    """
    data_dir = Path(__file__).resolve().parent.parent / 'data'
    mc_df = pd.read_json(data_dir / 'stocks.json')
    mc_df['Ticker'] = normalize_tickers(mc_df['Ticker'])
    mc_df['TickerKey'] = mc_df['Ticker']

    in_df = df.copy()
    in_df.columns = ['Name', 'Ticker', 'Sector']
    in_df['TickerKey'] = normalize_tickers(in_df['Ticker'])
    in_df = in_df[in_df['TickerKey'] != '']

    in_mc_df = (
        in_df.merge(
            mc_df[['TickerKey', 'MarketCap']],
            on='TickerKey',
            how='left'
        )
        .sort_values(by='MarketCap', ascending=False)
    )
    in_mc_df = in_mc_df.drop(columns=['TickerKey'])

    return in_mc_df


def read_prep_russell():

    url = 'https://en.wikipedia.org/wiki/Russell_1000_Index'
    data_dir = Path(__file__).resolve().parent.parent / 'data'
    file_name = 'russell_1000'
    file_path = data_dir / (file_name + '.json')

    try:
        comps, _table_idx = fetch_by_schema('russell1000')
        comps_sorted = sort_by_market_cap(comps[['Company', 'Symbol', 'GICS Sector']])

        report_missing_market_caps(comps_sorted)

        # Weights from the IWB holdings page (validated before any write).
        iwb = fetch_iwb_weights()

        res_list = []
        missing_weight = []
        seen_keys = set()
        for _, row in comps_sorted[['Name', 'Ticker', 'Sector']].iterrows():
            key = _ticker_key(row['Ticker'])
            seen_keys.add(key)
            weight = iwb[key][1] if key in iwb else None
            if weight is None:
                missing_weight.append(row['Ticker'])
            res_list.append({
                'Name': row['Name'],
                'Ticker': row['Ticker'],
                'Sector': row['Sector'],
                'Weight': weight,
            })
        if missing_weight:
            print(f'Warning: {len(missing_weight)} Wikipedia constituents '
                  f'have no IWB weight (kept, Weight null): {missing_weight}')

        # Genuine IWB-only constituents (added after Wikipedia's snapshot):
        # keep real stocks, report the excluded fund rows.
        sectors = _sector_map(data_dir)
        added, excluded = [], []
        for key, (ticker, weight, name, shares) in iwb.items():
            if key in seen_keys:
                continue
            if shares <= 0 or not _is_stock_row(name, ticker):
                excluded.append(ticker)
                continue
            res_list.append({
                'Name': name,
                'Ticker': ticker,
                'Sector': sectors.get(key),
                'Weight': weight,
            })
            added.append(ticker)
        if added:
            print(f'IWB-only constituents added: {added}')
        if excluded:
            print(f'IWB-only rows excluded as non-stock: {excluded}')

        # Order by weight (largest first); unweighted rows at the end.
        res_list.sort(key=lambda r: (r['Weight'] is None, -(r['Weight'] or 0)))

        # Validate the merged list before overwriting anything.
        tickers = [r['Ticker'] for r in res_list]
        if len(res_list) < 900:
            raise ValueError(f'merged list only {len(res_list)} rows')
        if len(tickers) != len(set(tickers)):
            raise ValueError('merged list contains duplicate tickers')
        if any(not t or t == 'nan' for t in tickers):
            raise ValueError('merged list contains a blank ticker')
        total = sum(r['Weight'] for r in res_list if r['Weight'] is not None)
        if not 95.0 <= total <= 105.0:
            raise ValueError(f'merged weights sum to {total}, expected ~100')

        with open(file_path, "w") as write_file:
            json.dump(res_list, write_file)

        print('Russell 1000 data read and json write was successfull.')

        try:
            df = pd.DataFrame(res_list)
            # Weight at exactly 2 decimals in CSV; blank where unknown.
            df['Weight'] = df['Weight'].map(
                lambda v: f'{v:.2f}' if v is not None and not (isinstance(v, float) and np.isnan(v)) else ''
            )
            df.to_csv(data_dir / 'russell_1000.csv', index=False, encoding='utf-8-sig')
            print('Russell 1000 data read and csv write was successfull.')

        except Exception as e:
            logging.error(str(e))
            print('Failed to save Russell 1000 data to csv.')

    except Exception as e:
        logging.error(str(e))
        print(f'Russell 1000 data read failed. {e}')


if __name__ == '__main__':

    read_prep_russell()
