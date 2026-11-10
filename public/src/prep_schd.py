# source: SEC EDGAR Form N-PORT filings of Schwab Strategic Trust
# (CIK 0001454889), series "Schwab U.S. Dividend Equity ETF" (SCHD).
# Schwab's own holdings page blocks automated downloads, so the fund's
# official monthly N-PORT filing on EDGAR is the durable source.
# N-PORT holdings carry CUSIPs, not tickers; CUSIP -> ticker resolution
# uses the OpenFIGI mapping API (US composite listing). A holding filed
# with a placeholder CUSIP (000000000 — Schwab does this for Accenture)
# falls back to its ISIN, which N-PORT also reports.
# Note: N-PORT-P filings become public ~60 days after period end, so
# this list lags the live fund. SCHD reconstitutes annually (March)
# and reweights quarterly, so constituents are stable between refreshes.



import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

EDGAR_CIK = '0001454889'
SERIES_NAME = 'Schwab U.S. Dividend Equity ETF'
EDGAR_HEADERS = {'User-Agent': 'watchlist-utils/1.0 (hmohammadi6545@gmail.com)'}
NPORT_NS = {'n': 'http://www.sec.gov/edgar/nport'}
OPENFIGI_URL = 'https://api.openfigi.com/v3/mapping'
OPENFIGI_BATCH = 10  # jobs per request without an API key


def _filing_series_name(accession, primary_doc):
    """Stream the filing XML only until <seriesName> is found."""
    doc_name = primary_doc.split('/')[-1]
    url = (f'https://www.sec.gov/Archives/edgar/data/{int(EDGAR_CIK)}/'
           f"{accession.replace('-', '')}/{doc_name}")
    buffer = b''
    with requests.get(url, headers=EDGAR_HEADERS, timeout=30, stream=True) as response:
        response.raise_for_status()
        for chunk in response.iter_content(4096):
            buffer += chunk
            match = re.search(rb'<seriesName>([^<]+)</seriesName>', buffer)
            if match:
                return match.group(1).decode('utf-8').strip()
            if len(buffer) > 65536:
                return None
    return None


def find_schd_filing():
    """Return (accession, primary_doc, report_date) of the newest SCHD NPORT-P."""
    response = requests.get(
        f'https://data.sec.gov/submissions/CIK{EDGAR_CIK}.json',
        headers=EDGAR_HEADERS, timeout=30)
    response.raise_for_status()
    recent = response.json()['filings']['recent']
    by_period = {}
    for i, form in enumerate(recent['form']):
        if form == 'NPORT-P':
            by_period.setdefault(recent['reportDate'][i], []).append(
                (recent['accessionNumber'][i], recent['primaryDocument'][i]))
    for report_date in sorted(by_period, reverse=True)[:3]:
        for accession, primary_doc in by_period[report_date]:
            time.sleep(0.15)  # SEC fair access: stay well under 10 requests/sec
            if _filing_series_name(accession, primary_doc) == SERIES_NAME:
                return accession, primary_doc, report_date
    raise ValueError(f'No NPORT-P filing found for series {SERIES_NAME}')


def fetch_holdings(accession, primary_doc):
    """Parse the filing and return its common-stock holdings."""
    doc_name = primary_doc.split('/')[-1]
    url = (f'https://www.sec.gov/Archives/edgar/data/{int(EDGAR_CIK)}/'
           f"{accession.replace('-', '')}/{doc_name}")
    response = requests.get(url, headers=EDGAR_HEADERS, timeout=60)
    response.raise_for_status()
    root = ET.fromstring(response.content)

    def text(sec, tag):
        el = sec.find(f'n:{tag}', NPORT_NS)
        return el.text.strip() if el is not None and el.text else None

    holdings = []
    for sec in root.findall('.//n:invstOrSec', NPORT_NS):
        if text(sec, 'assetCat') != 'EC':
            continue  # stocks only: skip the money-market fund (STIV) and futures (DE)
        cusip = text(sec, 'cusip')
        isin_el = sec.find('n:identifiers/n:isin', NPORT_NS)
        isin = isin_el.get('value') if isin_el is not None else None
        if not cusip and not isin:
            raise ValueError(f"SCHD holding without CUSIP or ISIN: {text(sec, 'name')}")
        holdings.append({
            'Name': text(sec, 'name'),
            'CUSIP': cusip,
            'ISIN': isin,
            'Weight': round(float(text(sec, 'pctVal')), 2),
        })
    if len(holdings) < 90:
        raise ValueError(f'SCHD N-PORT lists only {len(holdings)} stocks (expected ~100)')
    return holdings


def _openfigi_lookup(id_type, id_values):
    """One batched pass over OpenFIGI; returns {id_value: ticker or None}."""
    results = {}
    for start in range(0, len(id_values), OPENFIGI_BATCH):
        batch = id_values[start:start + OPENFIGI_BATCH]
        jobs = [{'idType': id_type, 'idValue': value} for value in batch]
        response = requests.post(OPENFIGI_URL, json=jobs, timeout=30,
                                 headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        payload = response.json()
        if len(payload) != len(batch):
            raise ValueError('OpenFIGI returned an unexpected number of results')
        for value, result in zip(batch, payload):
            data = [d for d in (result.get('data') or []) if d.get('ticker')]
            chosen = next((d for d in data if d.get('exchCode') == 'US'), None)
            if chosen is None and data:
                chosen = data[0]
            results[value] = (chosen['ticker'].replace('/', '.').strip().upper()
                              if chosen is not None else None)
        time.sleep(0.3)
    return results


def resolve_tickers(holdings):
    """Resolve every holding to a ticker, aligned with the holdings order.

    Primary key is the CUSIP. Holdings whose CUSIP is a placeholder
    (all zeros, as Schwab files Accenture) or unresolvable fall back to
    their ISIN. Any holding that resolves neither way fails the refresh
    rather than being silently dropped.
    """
    by_cusip = _openfigi_lookup(
        'ID_CUSIP',
        sorted({h['CUSIP'] for h in holdings
                if h['CUSIP'] and set(h['CUSIP']) != {'0'}}))
    tickers = [by_cusip.get(h['CUSIP']) for h in holdings]

    missing = [h for h, t in zip(holdings, tickers) if t is None]
    if missing:
        by_isin = _openfigi_lookup(
            'ID_ISIN', sorted({h['ISIN'] for h in missing if h['ISIN']}))
        tickers = [t or by_isin.get(h['ISIN'])
                   for h, t in zip(holdings, tickers)]

    unresolved = [h['Name'] for h, t in zip(holdings, tickers) if t is None]
    if unresolved:
        raise ValueError(f"OpenFIGI could not resolve tickers for: {', '.join(unresolved)}")
    return tickers


def read_prep_schd():

    file_name = 'schd'
    data_dir = Path(__file__).resolve().parent.parent / 'data'
    file_path = data_dir / (file_name + '.json')

    accession, primary_doc, report_date = find_schd_filing()
    holdings = fetch_holdings(accession, primary_doc)
    tickers = resolve_tickers(holdings)

    stocks = {}
    for row in json.loads((data_dir / 'stocks.json').read_text()):
        stocks[row['Ticker']] = row
    sectors = {}
    for fname in ('s&p500.json', 'russell_1000.json'):
        for row in json.loads((data_dir / fname).read_text()):
            if row.get('Sector'):
                sectors.setdefault(row['Ticker'], row['Sector'])

    res_list = []
    missing_caps = []
    missing_sectors = []
    ranked = sorted(zip(holdings, tickers), key=lambda pair: pair[0]['Weight'], reverse=True)
    for holding, ticker in ranked:
        record = {
            'Rank': len(res_list) + 1,
            'Name': holding['Name'],
            'Ticker': ticker,
        }
        stock = stocks.get(ticker)
        if stock and stock.get('MarketCap'):
            record['MarketCap'] = stock['MarketCap']
        if 'MarketCap' not in record:
            missing_caps.append(ticker)
        sector = sectors.get(ticker)
        if sector:
            record['Sector'] = sector
        else:
            missing_sectors.append(ticker)
        record['Weight'] = holding['Weight']
        res_list.append(record)

    if missing_caps:
        print(f'SCHD: no market cap in stocks.json for: {", ".join(missing_caps)}')
    if missing_sectors:
        print(f'SCHD: no sector in s&p500/russell_1000 for: {", ".join(missing_sectors)}')

    with open(file_path, 'w') as write_file:
        json.dump(res_list, write_file)

    # Save to CSV
    try:
        df = pd.read_json(file_path)
        df['MarketCap'] = df['MarketCap'].round(0).astype('Int64')
        df['Weight'] = df['Weight'].map(lambda v: f'{v:.2f}')
        df.to_csv(data_dir / f'{file_name}.csv', index=False, encoding='utf-8-sig')
        print(f'SCHD data read and csv write was successfull. '
              f'({len(res_list)} holdings, N-PORT period {report_date}, filing {accession})')

    except Exception as e:
        logging.error(str(e))
        print('Failed to save SCHD data to csv.')


if __name__ == '__main__':

    read_prep_schd()
