# source: SEC EDGAR Form N-PORT filings of iShares Trust
# (CIK 0001100663), series "iShares Russell 2000 ETF" (IWM) — the
# Russell 2000 list. iShares' website holdings download no longer
# serves files to scripts, so the fund's official N-PORT filing on
# EDGAR is the durable scriptable source. The newest *public* filing
# can be a few months old (only fiscal quarter-end months are public);
# the Russell 2000 reconstitutes once a year (June), and the June
# period filing captures it right after the rebuild.
# Shared EDGAR/OpenFIGI machinery lives in common/nport.py. The first
# run resolves ~2,000 CUSIPs through OpenFIGI (slow, under the free
# rate limit); the shared cache in public/data/cusip_tickers.json
# makes later runs resolve only new identifiers.



import logging
from pathlib import Path

from common import nport

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

EDGAR_CIK = '0001100663'
SERIES_NAME = 'iShares Russell 2000 ETF'


def read_prep_russell_2000():

    file_name = 'russell_2000'
    data_dir = Path(__file__).resolve().parent.parent / 'data'

    accession, primary_doc, report_date = nport.find_filing(EDGAR_CIK, SERIES_NAME)
    holdings = nport.fetch_stock_holdings(EDGAR_CIK, accession, primary_doc)
    if len(holdings) < 1500:
        raise ValueError(
            f'Russell 2000 N-PORT lists only {len(holdings)} stocks (expected ~2000)')
    tickers = nport.resolve_tickers(holdings, data_dir)

    stocks, sectors = nport.load_enrichment(data_dir)
    res_list, missing_caps, missing_sectors = nport.build_records(
        holdings, tickers, stocks, sectors)
    print(f'Russell 2000: {len(missing_caps)} holdings without a market cap, '
          f'{len(missing_sectors)} without a sector in the other datasets')

    nport.write_dataset(file_name, res_list, data_dir, 'Russell 2000')
    print(f'Russell 2000 source: N-PORT period {report_date}, filing {accession}')


if __name__ == '__main__':

    read_prep_russell_2000()
