# source: State Street (SSGA) official daily holdings spreadsheets for
# the SPDR ETFs: SPY, DIA and the 11 Select Sector SPDRs. Each fund's
# XLSX downloads with a plain request from ssga.com:
#   https://www.ssga.com/us/en/intermediary/etfs/library-content/
#   products/fund-data/etfs/us/holdings-daily-us-en-<ticker>.xlsx
# The files carry cash rows (ticker '-') and futures rows (contract
# tickers with digits); only plain US stock tickers with a positive
# weight are kept. The file's own Sector column is unpopulated ('-'),
# so Sector comes from the other datasets — or, for the sector funds,
# from the fund's own GICS sector. MarketCap joins from stocks.json,
# matching the other index datasets (see common/nport.py helpers).
# Downloads run through curl: SSGA's CDN stalls Python's TLS
# fingerprint, curl passes (see download_ssga_file).



import logging
import re
import subprocess
from io import BytesIO
from pathlib import Path

import pandas as pd

from common import nport

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

URL_TEMPLATE = ('https://www.ssga.com/us/en/intermediary/etfs/library-content/'
                'products/fund-data/etfs/us/holdings-daily-us-en-{slug}.xlsx')
TICKER_RE = re.compile(r'^[A-Z]+(\.[A-Z])?$')

# slug, output file, display label, the fund's own GICS sector (or None
# to join sectors per stock), minimum expected holdings
FUNDS = [
    ('spy', 'spy', 'SPY', None, 480),
    ('dia', 'dia', 'DIA', None, 30),
    ('xlk', 'xlk', 'XLK', 'Information Technology', 10),
    ('xlf', 'xlf', 'XLF', 'Financials', 10),
    ('xlv', 'xlv', 'XLV', 'Health Care', 10),
    ('xle', 'xle', 'XLE', 'Energy', 10),
    ('xly', 'xly', 'XLY', 'Consumer Discretionary', 10),
    ('xlp', 'xlp', 'XLP', 'Consumer Staples', 10),
    ('xli', 'xli', 'XLI', 'Industrials', 10),
    ('xlb', 'xlb', 'XLB', 'Materials', 10),
    ('xlre', 'xlre', 'XLRE', 'Real Estate', 10),
    ('xlu', 'xlu', 'XLU', 'Utilities', 10),
    ('xlc', 'xlc', 'XLC', 'Communication Services', 10),
]


def download_ssga_file(slug):
    """Download one holdings file with curl.

    SSGA's CDN (Akamai) stalls Python's TLS fingerprint indefinitely,
    while curl passes; the file itself is a public download link. The
    code still fetches everything itself — curl is just the transport.
    """
    url = URL_TEMPLATE.format(slug=slug)
    result = subprocess.run(
        ['curl', '-fSL', '--retry', '2', '--max-time', '120',
         '-A', 'watchlist-utils/1.0', url],
        capture_output=True, timeout=300)
    if result.returncode != 0:
        raise ValueError(
            f'curl failed for {slug}: {result.stderr.decode(errors="replace")[:200]}')
    return result.stdout


def fetch_fund_holdings(slug):
    """Download one SSGA holdings file; return stock holdings only."""
    content = download_ssga_file(slug)
    raw = pd.read_excel(BytesIO(content), header=None)
    header_rows = raw.index[(raw[0] == 'Name') & (raw[1] == 'Ticker')].tolist()
    if not header_rows:
        raise ValueError(f'SSGA file for {slug} has no holdings header row')
    df = raw.iloc[header_rows[0] + 1:].copy()
    df.columns = ['Name', 'Ticker', 'Identifier', 'SEDOL', 'Weight',
                  'Sector', 'Shares', 'Currency'][:len(df.columns)]
    holdings = []
    for _, row in df.iterrows():
        if pd.isna(row['Ticker']) or pd.isna(row['Weight']):
            continue  # blank and footer/disclaimer rows
        ticker = str(row['Ticker']).strip().upper()
        weight = round(float(row['Weight']), 2)
        if not TICKER_RE.match(ticker) or weight <= 0:
            continue  # cash ('-'), futures (IXTZ6) and contra rows
        holdings.append({
            'Name': str(row['Name']).strip(),
            'Ticker': ticker,
            'Weight': weight,
        })
    return holdings


def read_prep_spdr():

    data_dir = Path(__file__).resolve().parent.parent / 'data'
    stocks, sectors = nport.load_enrichment(data_dir)

    failures = []
    for slug, file_name, label, fixed_sector, minimum in FUNDS:
        try:
            holdings = fetch_fund_holdings(slug)
            if len(holdings) < minimum:
                raise ValueError(
                    f'{label} file lists only {len(holdings)} stocks (expected {minimum}+)')
            tickers = [h['Ticker'] for h in holdings]
            if len(set(tickers)) != len(tickers):
                raise ValueError(f'{label} file contains duplicate tickers')
            res_list, missing_caps, missing_sectors = nport.build_records(
                holdings, tickers, stocks, sectors, fixed_sector=fixed_sector)
            if missing_caps:
                print(f'{label}: no market cap in stocks.json for: {", ".join(missing_caps)}')
            if missing_sectors:
                print(f'{label}: no sector in the other datasets for: {", ".join(missing_sectors)}')
            nport.write_dataset(file_name, res_list, data_dir, label)
        except Exception as e:
            print(f'{label} failed: {e}')
            failures.append(label)

    if failures:
        raise RuntimeError(f'SPDR refresh failed for: {", ".join(failures)}')


if __name__ == '__main__':

    read_prep_spdr()
