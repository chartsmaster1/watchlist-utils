"""ARK active-ETF holdings (ARKW, ARKG, ARKF, ARKX, ARKQ) from the
official ARK daily CSVs on assets.ark-funds.com — the same source and
output schema as prep_arkk.py (ARKK), one job per fund so a single bad
file never blocks the others. Each job writes <fund>.json (Rank/Name/
Ticker/Weight, weight order) + <fund>.csv and keeps the raw daily file
as <fund>_holdings.csv. Raises on failure so main.py records the job.

Verified live 2026-11-21 (HTTP 200 + 11/20/2026 holdings date).
ARK renamed three files in Nov 2026 — the old URLs still return
HTTP 200 with stale files (ARKF/ARKX 01/02/2026, ARKW 10/06/2026),
so the exact verified URLs are pinned below. ARKQ's file is
abbreviated ARK_AUTONOMOUS_TECH._&_ROBOTICS_ETF (not TECHNOLOGY) —
the full name 404s.
"""

import json
import logging
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

BASE = 'https://assets.ark-funds.com/fund-documents/funds-etf-csv'
REQUIRED_COLUMNS = {'company', 'ticker', 'weight (%)'}

FUNDS = {
    'arkw': ('ARK Next Generation Technology ETF',
             f'{BASE}/ARK_NEXT_GENERATION_TECHNOLOGY_ETF_ARKW_HOLDINGS.csv'),
    'arkg': ('ARK Genomic Revolution ETF',
             f'{BASE}/ARK_GENOMIC_REVOLUTION_ETF_ARKG_HOLDINGS.csv'),
    'arkf': ('ARK Blockchain & Fintech Innovation ETF',
             f'{BASE}/ARK_BLOCKCHAIN_%26_FINTECH_INNOVATION_ETF_ARKF_HOLDINGS.csv'),
    'arkx': ('ARK Space & Defense Innovation ETF',
             f'{BASE}/ARK_SPACE_%26_DEFENSE_INNOVATION_ETF_ARKX_HOLDINGS.csv'),
    'arkq': ('ARK Autonomous Tech. & Robotics ETF',
             f'{BASE}/ARK_AUTONOMOUS_TECH._%26_ROBOTICS_ETF_ARKQ_HOLDINGS.csv'),
}


def _prep_ark(fund):
    label, source_url = FUNDS[fund]
    data_dir = Path(__file__).resolve().parent.parent / 'data'
    file_path = data_dir / (fund + '.json')
    holdings_path = data_dir / (fund + '_holdings.csv')

    response = requests.get(
        source_url,
        headers={'User-Agent': 'watchlist-utils/1.0'},
        timeout=30,
    )
    response.raise_for_status()
    df_raw = pd.read_csv(StringIO(response.text))
    missing_columns = REQUIRED_COLUMNS - set(df_raw.columns)
    if missing_columns:
        raise ValueError(f'{fund.upper()} source missing columns: {sorted(missing_columns)}')
    if df_raw['ticker'].notna().sum() == 0:
        raise ValueError(f'{fund.upper()} source contains no holdings')
    temporary_path = holdings_path.with_suffix('.csv.tmp')
    normalized_csv = response.text.replace('\r\n', '\n').replace('\r', '\n')
    temporary_path.write_text(normalized_csv)
    temporary_path.replace(holdings_path)

    df_raw = df_raw.dropna(subset=['ticker']).reset_index(drop=True)
    df_raw['ticker'] = df_raw['ticker'].str.strip().str.upper()
    df_raw['ticker'] = df_raw['ticker'].apply(lambda x: x.split(' ')[0] if ' ' in x else x)

    res_list = []
    for idx, row in df_raw.iterrows():
        weight = float(str(row['weight (%)']).replace('%', '').strip())
        res_list.append({
            'Rank': int(idx) + 1,
            'Name': row['company'],
            'Ticker': row['ticker'],
            'Weight': round(weight, 2),
        })
    if not res_list:
        raise ValueError(f'{fund.upper()} produced no holdings')

    with file_path.open('w') as f:
        json.dump(res_list, f)
    df = pd.read_json(file_path)
    df['Weight'] = df['Weight'].map(lambda v: f'{v:.2f}')
    df.to_csv(data_dir / f'{fund}.csv', index=False, encoding='utf-8-sig')
    print(f'{fund.upper()} ({label}): {len(res_list)} holdings')


def read_prep_arkw():
    _prep_ark('arkw')


def read_prep_arkg():
    _prep_ark('arkg')


def read_prep_arkf():
    _prep_ark('arkf')


def read_prep_arkx():
    _prep_ark('arkx')


def read_prep_arkq():
    _prep_ark('arkq')


if __name__ == '__main__':
    for fund in FUNDS:
        _prep_ark(fund)
