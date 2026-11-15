"""S&P 500 Dividend Aristocrats (the ProShares NOBL index) from the
Wikipedia constituents table, enriched with MarketCap from stocks.json
(same pattern as prep_nasdaq.py / prep_russell_1000.py). The list is the
companies that raised dividends for 25+ straight years — about 60-70
names. Sorted by MarketCap descending, nulls last. Raises on failure
so main.py records the job.

Source verified live 2026-11-15: the page's constituents table has
columns Ticker symbol / Company / Sector.
"""

import json
import logging
from pathlib import Path

import pandas as pd

from common.tickers import normalize_tickers, report_missing_market_caps
from common.wiki import fetch_by_schema

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')


def read_prep_dividend_aristocrats():
    data_dir = Path(__file__).resolve().parent.parent / 'data'
    file_name = 'divaristocrats'
    file_path = data_dir / (file_name + '.json')

    comps, _table_idx = fetch_by_schema('divaristocrats')
    if len(comps) < 50:
        raise ValueError(
            f'Dividend Aristocrats table has only {len(comps)} rows (expected ~60-70)')

    stocks_path = data_dir / 'stocks.json'
    if not stocks_path.exists():
        raise ValueError('stocks.json missing — the companies job must run first')
    mc_df = pd.read_json(stocks_path)
    mc_df['Ticker'] = normalize_tickers(mc_df['Ticker'])
    mc_df['TickerKey'] = mc_df['Ticker']

    in_df = comps[['Company', 'Ticker symbol', 'Sector']].copy()
    in_df.columns = ['Name', 'Ticker', 'Sector']
    in_df['TickerKey'] = normalize_tickers(in_df['Ticker'])
    in_df = in_df[in_df['TickerKey'] != '']
    in_df = (
        in_df.merge(mc_df[['TickerKey', 'MarketCap']], on='TickerKey', how='left')
        .sort_values(by='MarketCap', ascending=False, na_position='last')
        .reset_index(drop=True)
    )
    in_df = in_df.drop(columns=['TickerKey'])
    report_missing_market_caps(in_df)

    res_list = []
    for i, row in in_df.iterrows():
        res_list.append({
            'Rank': int(i) + 1,
            'Name': row['Name'],
            'Ticker': row['Ticker'],
            'Sector': row['Sector'],
            'MarketCap': int(row['MarketCap']) if pd.notna(row['MarketCap']) else None,
        })
    if len(res_list) < 50:
        raise ValueError(f'Dividend Aristocrats produced only {len(res_list)} rows')

    with file_path.open('w') as f:
        json.dump(res_list, f)
    df = pd.DataFrame(res_list)
    df.to_csv(data_dir / (file_name + '.csv'), index=False, encoding='utf-8-sig')
    print(f'Dividend Aristocrats: {len(res_list)} rows, top {res_list[0]["Ticker"]}')


if __name__ == '__main__':
    read_prep_dividend_aristocrats()
