# source: Berkshire Hathaway Inc. (CIK 0001067983) Form 13F-HR filings
# on SEC EDGAR — Warren Buffett's reported US stock portfolio. The
# information table is aggregated by CUSIP (Berkshire reports the same
# stock through several subsidiaries), share counts/option rows are
# skipped, and Weight is each position's share of the reported total
# value. CUSIP -> ticker resolution reuses the shared OpenFIGI cache
# in common/nport.py. 13F filings are quarterly and due 45 days after
# quarter end, so the list lags the live portfolio by up to ~4 months.



import logging
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

from common import nport

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

EDGAR_CIK = '0001067983'
F13_NS = {'f': 'http://www.sec.gov/edgar/document/thirteenf/informationtable'}


def find_latest_13f():
    """Return (accession, report_date) of the newest 13F-HR filing."""
    response = requests.get(
        f'https://data.sec.gov/submissions/CIK{EDGAR_CIK}.json',
        headers=nport.EDGAR_HEADERS, timeout=30)
    response.raise_for_status()
    recent = response.json()['filings']['recent']
    for i, form in enumerate(recent['form']):
        if form == '13F-HR':
            return recent['accessionNumber'][i], recent['reportDate'][i]
    raise ValueError('No 13F-HR filing found for Berkshire Hathaway')


def fetch_information_table(accession):
    """Locate and parse the filing's information table XML."""
    folder = (f'https://www.sec.gov/Archives/edgar/data/{int(EDGAR_CIK)}/'
              f"{accession.replace('-', '')}")
    index = requests.get(f'{folder}/index.json',
                         headers=nport.EDGAR_HEADERS, timeout=30)
    index.raise_for_status()
    names = [item['name'] for item in index.json()['directory']['item']
             if item['name'].lower().endswith('.xml')
             and item['name'] != 'FilingSummary.xml']
    for name in names:
        doc = requests.get(f'{folder}/{name}',
                           headers=nport.EDGAR_HEADERS, timeout=60)
        doc.raise_for_status()
        root = ET.fromstring(doc.content)
        if root.tag.endswith('informationTable'):
            return root
    raise ValueError('No information table found in the 13F filing')


def aggregate_holdings(root):
    """Sum reported values per CUSIP over share rows (no options)."""
    def text(entry, tag):
        el = entry.find(f'f:{tag}', F13_NS)
        return el.text.strip() if el is not None and el.text else None

    by_cusip = {}
    for entry in root.findall('f:infoTable', F13_NS):
        if text(entry, 'putCall') is not None:
            continue  # option rows, not held shares
        amt_type = entry.find('f:shrsOrPrnAmt/f:sshPrnamtType', F13_NS)
        if amt_type is None or amt_type.text.strip() != 'SH':
            continue  # principal-amount (debt) rows
        cusip = text(entry, 'cusip')
        value = float(text(entry, 'value'))
        if cusip not in by_cusip:
            by_cusip[cusip] = {'Name': text(entry, 'nameOfIssuer'),
                               'CUSIP': cusip, 'ISIN': None, 'value': 0.0}
        by_cusip[cusip]['value'] += value
    total = sum(h['value'] for h in by_cusip.values())
    holdings = []
    for h in by_cusip.values():
        h['Weight'] = round(h.pop('value') / total * 100, 2)
        holdings.append(h)
    return holdings


def read_prep_berkshire():

    file_name = 'berkshire'
    data_dir = Path(__file__).resolve().parent.parent / 'data'

    accession, report_date = find_latest_13f()
    root = fetch_information_table(accession)
    holdings = aggregate_holdings(root)
    if len(holdings) < 25:
        raise ValueError(
            f'Berkshire 13F lists only {len(holdings)} stocks (expected ~30-40)')
    tickers, _ = nport.resolve_tickers(holdings, data_dir)

    stocks, sectors = nport.load_enrichment(data_dir)
    res_list, missing_caps, missing_sectors = nport.build_records(
        holdings, tickers, stocks, sectors)
    if missing_caps:
        print(f'Berkshire: no market cap in stocks.json for: {", ".join(missing_caps)}')
    if missing_sectors:
        print(f'Berkshire: no sector in the other datasets for: {", ".join(missing_sectors)}')

    nport.write_dataset(file_name, res_list, data_dir, 'Berkshire')
    print(f'Berkshire source: 13F-HR period {report_date}, filing {accession}')


if __name__ == '__main__':

    read_prep_berkshire()
