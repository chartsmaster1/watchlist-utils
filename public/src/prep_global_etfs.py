"""Global index ETFs from SEC EDGAR Form N-PORT filings of iShares
Trust (CIK 0001100663) — the same shared machinery as prep_russell_2000.py:
  - MSCI ACWI (all-world, ~2,300 holdings)
  - MSCI EAFE (developed markets ex-US/Canada, ~800 holdings)
  - MSCI Emerging Markets (~1,300 holdings)
One job per fund so a single bad filing never blocks the others.
N-PORT becomes public ~60 days after period end, so the lists lag the
live funds by a few months, like QQQ and Russell 2000. Raises on
failure so main.py records the job.
"""

import logging
from pathlib import Path

from common import nport

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

EDGAR_CIK = '0001100663'
# EEM is a series of iShares, Inc. (CIK 0000930667), NOT iShares Trust —
# verified 2026-11-15: no EEM N-PORT exists under the Trust in the last
# four quarter-ends (only the Quality/Value Factor variants), while
# iShares, Inc. holds the plain EEM series (period 2026-08-31).
EEM_CIK = '0000930667'

FUNDS = {
    'acwi': (EDGAR_CIK, 'iShares MSCI ACWI ETF', 'MSCI ACWI', 1800),
    'efa': (EDGAR_CIK, 'iShares MSCI EAFE ETF', 'MSCI EAFE', 500),
    'eem': (EEM_CIK, 'iShares MSCI Emerging Markets ETF', 'MSCI Emerging Markets', 800),
}


def _prep_global_etf(fund):
    cik, series_name, label, minimum = FUNDS[fund]
    data_dir = Path(__file__).resolve().parent.parent / 'data'

    accession, primary_doc, report_date = nport.find_filing(cik, series_name)
    holdings = nport.fetch_stock_holdings(cik, accession, primary_doc)
    if len(holdings) < minimum:
        raise ValueError(
            f'{label} N-PORT lists only {len(holdings)} stocks (expected >={minimum})')
    # A few recent listings lag in OpenFIGI; dropping up to 25 (with a
    # loud warning) beats blocking the whole refresh on them. They
    # re-enter automatically once OpenFIGI maps their identifiers.
    tickers, unresolved = nport.resolve_tickers(holdings, data_dir,
                                                allow_unresolved=25)
    if unresolved:
        dropped = {id(h) for h in unresolved}
        names = ', '.join(f"{h['Name']} ({h['Weight']}%)" for h in unresolved)
        print(f'{label} WARNING: dropping {len(unresolved)} holdings '
              f'OpenFIGI cannot map yet: {names}')
        pairs = [(h, t) for h, t in zip(holdings, tickers) if id(h) not in dropped]
        holdings = [h for h, _ in pairs]
        tickers = [t for _, t in pairs]

    stocks, sectors = nport.load_enrichment(data_dir)
    res_list, missing_caps, missing_sectors = nport.build_records(
        holdings, tickers, stocks, sectors)
    print(f'{label}: {len(missing_caps)} holdings without a market cap, '
          f'{len(missing_sectors)} without a sector in the other datasets')

    nport.write_dataset(fund, res_list, data_dir, label)
    print(f'{label} source: N-PORT period {report_date}, filing {accession}')


def read_prep_acwi():
    _prep_global_etf('acwi')


def read_prep_efa():
    _prep_global_etf('efa')


def read_prep_eem():
    _prep_global_etf('eem')


if __name__ == '__main__':
    for fund in FUNDS:
        _prep_global_etf(fund)
