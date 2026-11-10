# source: SEC EDGAR Form N-PORT filings of Schwab Strategic Trust
# (CIK 0001454889), series "Schwab U.S. Dividend Equity ETF" (SCHD).
# Schwab's own holdings page blocks automated downloads, so the fund's
# official monthly N-PORT filing on EDGAR is the durable source.
# Shared EDGAR/OpenFIGI machinery lives in common/nport.py; N-PORT-P
# filings become public ~60 days after period end, so this list lags
# the live fund. SCHD reconstitutes annually (March) and reweights
# quarterly, so constituents are stable between refreshes.



import logging
from pathlib import Path

from common import nport

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

EDGAR_CIK = '0001454889'
SERIES_NAME = 'Schwab U.S. Dividend Equity ETF'


def read_prep_schd():

    file_name = 'schd'
    data_dir = Path(__file__).resolve().parent.parent / 'data'

    accession, primary_doc, report_date = nport.find_filing(EDGAR_CIK, SERIES_NAME)
    holdings = nport.fetch_stock_holdings(EDGAR_CIK, accession, primary_doc)
    if len(holdings) < 90:
        raise ValueError(f'SCHD N-PORT lists only {len(holdings)} stocks (expected ~100)')
    tickers, _ = nport.resolve_tickers(holdings, data_dir)

    stocks, sectors = nport.load_enrichment(data_dir)
    res_list, missing_caps, missing_sectors = nport.build_records(
        holdings, tickers, stocks, sectors)
    if missing_caps:
        print(f'SCHD: no market cap in stocks.json for: {", ".join(missing_caps)}')
    if missing_sectors:
        print(f'SCHD: no sector in the other datasets for: {", ".join(missing_sectors)}')

    nport.write_dataset(file_name, res_list, data_dir, 'SCHD')
    print(f'SCHD source: N-PORT period {report_date}, filing {accession}')


if __name__ == '__main__':

    read_prep_schd()
