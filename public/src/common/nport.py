"""Shared SEC EDGAR Form N-PORT machinery for fund-holdings datasets.

Used by the SCHD, QQQ and Russell 2000 (IWM) preparers. A fund's official
holdings are read from its N-PORT filing on EDGAR (scriptable, never
bot-blocked), keeping common-stock (assetCat EC) rows only. Filings carry
CUSIPs/ISINs, not tickers; resolution goes through OpenFIGI with a
persistent CUSIP -> ticker cache in public/data/cusip_tickers.json so
repeat runs only resolve new identifiers.

N-PORT-P filings become public ~60 days after period end, and only for
fiscal quarter-end months, so the newest *public* filing for a series can
be a few months old. The finder scans period batches newest-first until
the series is found.
"""

import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests

EDGAR_HEADERS = {'User-Agent': 'watchlist-utils/1.0 (hmohammadi6545@gmail.com)'}
NPORT_NS = {'n': 'http://www.sec.gov/edgar/nport'}
OPENFIGI_URL = 'https://api.openfigi.com/v3/mapping'
OPENFIGI_BATCH = 10  # jobs per request without an API key
CACHE_NAME = 'cusip_tickers.json'
PLAIN_TICKER_RE = re.compile(r'^[A-Z0-9]+(\.[A-Z])?$')


def _filing_series_name(cik, accession, primary_doc):
    """Stream the filing XML only until <seriesName> is found."""
    doc_name = primary_doc.split('/')[-1]
    url = (f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/'
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


def find_filing(cik, series_name, max_periods=6):
    """Return (accession, primary_doc, report_date) of the newest public
    NPORT-P filing for the given series of the given trust CIK."""
    response = requests.get(
        f'https://data.sec.gov/submissions/CIK{cik}.json',
        headers=EDGAR_HEADERS, timeout=30)
    response.raise_for_status()
    recent = response.json()['filings']['recent']
    by_period = {}
    for i, form in enumerate(recent['form']):
        if form == 'NPORT-P':
            by_period.setdefault(recent['reportDate'][i], []).append(
                (recent['accessionNumber'][i], recent['primaryDocument'][i]))
    for report_date in sorted(by_period, reverse=True)[:max_periods]:
        for accession, primary_doc in by_period[report_date]:
            time.sleep(0.12)  # SEC fair access: stay well under 10 requests/sec
            if _filing_series_name(cik, accession, primary_doc) == series_name:
                return accession, primary_doc, report_date
    raise ValueError(f'No NPORT-P filing found for series {series_name} (CIK {cik})')


def fetch_stock_holdings(cik, accession, primary_doc):
    """Parse the filing and return its common-stock holdings."""
    doc_name = primary_doc.split('/')[-1]
    url = (f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/'
           f"{accession.replace('-', '')}/{doc_name}")
    response = requests.get(url, headers=EDGAR_HEADERS, timeout=120)
    response.raise_for_status()
    root = ET.fromstring(response.content)

    def text(sec, tag):
        el = sec.find(f'n:{tag}', NPORT_NS)
        return el.text.strip() if el is not None and el.text else None

    holdings = []
    for sec in root.findall('.//n:invstOrSec', NPORT_NS):
        if text(sec, 'assetCat') != 'EC':
            continue  # stocks only: skip money-market funds (STIV) and futures (DE)
        cusip = text(sec, 'cusip')
        isin_el = sec.find('n:identifiers/n:isin', NPORT_NS)
        isin = isin_el.get('value') if isin_el is not None else None
        if not cusip and not isin:
            raise ValueError(f"Holding without CUSIP or ISIN: {text(sec, 'name')}")
        holdings.append({
            'Name': text(sec, 'name'),
            'CUSIP': cusip,
            'ISIN': isin,
            'Weight': round(float(text(sec, 'pctVal')), 2),
        })
    return holdings


def _pick_ticker(data):
    """Choose the US primary-listing ticker from OpenFIGI result entries.

    OpenFIGI also returns foreign listings and occasional marked
    tickers (e.g. 'WBD*'); prefer a plain US-listed ticker, then any
    US entry, then any plain ticker. Returns None if nothing usable.
    """
    candidates = []
    for entry in data or []:
        raw = entry.get('ticker')
        if not raw:
            continue
        ticker = raw.replace('/', '.').strip().upper().rstrip('*')
        candidates.append((ticker, entry.get('exchCode')))
    for want_us, want_plain in ((True, True), (True, False), (False, True)):
        for ticker, exch in candidates:
            if want_us and exch != 'US':
                continue
            if want_plain and not PLAIN_TICKER_RE.match(ticker):
                continue
            return ticker
    return None


def _openfigi_lookup(id_type, id_values, slow, exch_code=None):
    """One batched pass over OpenFIGI; returns {id_value: ticker or None}."""
    results = {}
    for start in range(0, len(id_values), OPENFIGI_BATCH):
        batch = id_values[start:start + OPENFIGI_BATCH]
        jobs = []
        for value in batch:
            job = {'idType': id_type, 'idValue': value}
            if exch_code:
                job['exchCode'] = exch_code
            jobs.append(job)
        response = requests.post(OPENFIGI_URL, json=jobs, timeout=30,
                                 headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        payload = response.json()
        if len(payload) != len(batch):
            raise ValueError('OpenFIGI returned an unexpected number of results')
        for value, result in zip(batch, payload):
            results[value] = _pick_ticker(result.get('data'))
        # Unauthenticated OpenFIGI allows ~25 requests/minute; pace big
        # first-time resolutions (e.g. Russell 2000) under that budget.
        time.sleep(2.5 if slow else 0.3)
    return results


def resolve_tickers(holdings, data_dir, allow_unresolved=0):
    """Resolve every holding to a ticker, aligned with the holdings order.

    Cache keys are real CUSIPs, or 'ISIN:<isin>' for holdings filed with a
    placeholder CUSIP (all zeros). Resolution passes, in order: cache,
    OpenFIGI by CUSIP, by ISIN, then both again restricted to US
    exchanges. Returns (tickers, unresolved holdings). Unresolved
    holdings raise unless the caller allows a small number (used by the
    Russell 2000: a few recent listings lag in OpenFIGI, and one bad
    identifier must not block the whole refresh).
    """
    cache_path = data_dir / CACHE_NAME
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}

    def real_cusip(holding):
        cusip = holding['CUSIP']
        return cusip if cusip and set(cusip) != {'0'} else None

    def cache_key(holding):
        cusip = real_cusip(holding)
        if cusip:
            return cusip
        return f"ISIN:{holding['ISIN']}" if holding['ISIN'] else None

    def apply_pass(missing, id_type, slow, exch_code=None):
        if id_type == 'ID_CUSIP':
            ids = sorted({real_cusip(h) for h in missing if real_cusip(h)})
            key_of = real_cusip
        else:
            ids = sorted({h['ISIN'] for h in missing if h['ISIN']})
            key_of = lambda h: h['ISIN']
        if not ids:
            return missing
        found = _openfigi_lookup(id_type, ids, slow, exch_code=exch_code)
        still = []
        for holding in missing:
            ticker = found.get(key_of(holding))
            if ticker:
                key = cache_key(holding)
                if key:
                    cache[key] = ticker
            else:
                still.append(holding)
        return still

    missing = [h for h in holdings if not cache.get(cache_key(h) or '')]
    if missing:
        slow = len(missing) > 100
        for id_type, exch_code in (('ID_CUSIP', None), ('ID_ISIN', None),
                                   ('ID_CUSIP', 'US'), ('ID_ISIN', 'US')):
            if not missing:
                break
            missing = apply_pass(missing, id_type, slow, exch_code)
        cache_path.write_text(json.dumps(cache, indent=0, sort_keys=True))

    tickers = [cache.get(cache_key(h) or '') for h in holdings]
    unresolved = [h for h, t in zip(holdings, tickers) if t is None]
    if len(unresolved) > allow_unresolved:
        names = [h['Name'] for h in unresolved]
        raise ValueError(
            f"OpenFIGI could not resolve tickers for: {', '.join(names[:10])}"
            + (f' (+{len(names) - 10} more)' if len(names) > 10 else ''))
    return tickers, unresolved


def load_enrichment(data_dir):
    """Return (stocks by ticker, sectors by ticker) from existing datasets."""
    stocks = {}
    for row in json.loads((data_dir / 'stocks.json').read_text()):
        stocks[row['Ticker']] = row
    sectors = {}
    for fname in ('s&p500.json', 'russell_1000.json', 'nasdaq.json',
                  'dow.json', 'schd.json'):
        path = data_dir / fname
        if not path.exists():
            continue
        for row in json.loads(path.read_text()):
            if row.get('Sector'):
                sectors.setdefault(row['Ticker'], row['Sector'])
    return stocks, sectors


def build_records(holdings, tickers, stocks, sectors, fixed_sector=None):
    """Assemble ranked output records; warn (never silently drop).

    If two holdings resolve to the same ticker (dual share classes that
    OpenFIGI maps to one symbol), the larger holding wins and the
    smaller is dropped with a warning — datasets must have unique
    tickers (validate_data.py enforces it).
    """
    res_list = []
    missing_caps = []
    missing_sectors = []
    seen_tickers = set()
    ranked = sorted(zip(holdings, tickers),
                    key=lambda pair: pair[0]['Weight'], reverse=True)
    for holding, ticker in ranked:
        if ticker in seen_tickers:
            print(f'Dropping duplicate ticker {ticker} ({holding["Name"]}, '
                  f'{holding["Weight"]}%) — kept the larger holding')
            continue
        seen_tickers.add(ticker)
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
        sector = fixed_sector or sectors.get(ticker)
        if sector:
            record['Sector'] = sector
        else:
            missing_sectors.append(ticker)
        record['Weight'] = holding['Weight']
        res_list.append(record)
    return res_list, missing_caps, missing_sectors


def write_dataset(file_name, res_list, data_dir, label):
    """Write <file_name>.json and the formatted companion CSV."""
    file_path = data_dir / (file_name + '.json')
    with open(file_path, 'w') as write_file:
        json.dump(res_list, write_file)
    df = pd.read_json(file_path)
    if 'MarketCap' in df.columns:
        df['MarketCap'] = df['MarketCap'].round(0).astype('Int64')
    if 'Weight' in df.columns:
        df['Weight'] = df['Weight'].map(lambda v: f'{v:.2f}')
    df.to_csv(data_dir / f'{file_name}.csv', index=False, encoding='utf-8-sig')
    print(f'{label} data read and csv write was successfull. ({len(res_list)} holdings)')
