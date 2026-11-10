# source: SEC EDGAR Form N-PORT filings of Invesco QQQ Trust, Series 1
# (CIK 0001067839) — the QQQ fund itself. Invesco's website holdings
# download is behind a JavaScript app, so the fund's official quarterly
# N-PORT filing on EDGAR is the durable scriptable source.
# Shared EDGAR/OpenFIGI machinery lives in common/nport.py; N-PORT-P
# filings become public ~60 days after period end and this trust files
# quarterly, so the list lags the live fund by a few months. QQQ tracks
# the Nasdaq-100, whose constituents change only a few times a year.



import logging
from pathlib import Path

from common import nport

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

EDGAR_CIK = '0001067839'
SERIES_NAME = 'Invesco QQQ Trust, Series 1'


def read_prep_qqq():

    file_name = 'qqq'
    data_dir = Path(__file__).resolve().parent.parent / 'data'

    accession, primary_doc, report_date = nport.find_filing(EDGAR_CIK, SERIES_NAME)
    holdings = nport.fetch_stock_holdings(EDGAR_CIK, accession, primary_doc)
    if len(holdings) < 95:
        raise ValueError(f'QQQ N-PORT lists only {len(holdings)} stocks (expected ~100)')
    tickers = nport.resolve_tickers(holdings, data_dir)

    stocks, sectors = nport.load_enrichment(data_dir)
    res_list, missing_caps, missing_sectors = nport.build_records(
        holdings, tickers, stocks, sectors)
    if missing_caps:
        print(f'QQQ: no market cap in stocks.json for: {", ".join(missing_caps)}')
    if missing_sectors:
        print(f'QQQ: no sector in the other datasets for: {", ".join(missing_sectors)}')

    nport.write_dataset(file_name, res_list, data_dir, 'QQQ')
    print(f'QQQ source: N-PORT period {report_date}, filing {accession}')


if __name__ == '__main__':

    read_prep_qqq()
