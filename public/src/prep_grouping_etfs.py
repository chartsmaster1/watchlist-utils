"""Industry grouping ETFs from SEC EDGAR Form N-PORT filings — the same
shared machinery as prep_global_etfs.py / prep_russell_2000.py:
  - Semiconductors: SMH (VanEck, 25 holdings), SOXX (iShares, 30)
  - Real estate: IYR (iShares, 61)
  - Gold miners: GDX (VanEck, 61)
  - Biotech: XBI (SPDR, 152)
  - Regional banks: KRE (SPDR, 161)
  - Clean energy: ICLN (iShares, 101)
One job per fund so a single bad filing never blocks the others.
N-PORT becomes public ~60 days after period end, so the lists lag the
live funds by a few months, like QQQ and Russell 2000. Raises on
failure so main.py records the job.

Series-name notes (verified 2026-11-15):
  - SOXX is filed as "iShares Semiconductor ETF" — PHLX is the index
    name, not the series name.
  - SPDR series names contain "State Street(R) SPDR(R) S&P(R) ..." and
    need the html.unescape fix in nport._filing_series_name, otherwise
    the "&amp;" in the XML never matches.
"""

import logging
from pathlib import Path

from common import nport

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

ISHARES_CIK = '0001100663'
VANECK_CIK = '0001137360'
SPDR_CIK = '0001064642'

# fund: (cik, series_name, label, minimum_holdings, allow_unresolved)
FUNDS = {
    'smh': (VANECK_CIK, 'VanEck Semiconductor ETF', 'SMH Semiconductors', 20, 10),
    'soxx': (ISHARES_CIK, 'iShares Semiconductor ETF', 'SOXX Semiconductors', 20, 10),
    'iyr': (ISHARES_CIK, 'iShares U.S. Real Estate ETF', 'IYR Real Estate', 50, 25),
    'gdx': (VANECK_CIK, 'VanEck Gold Miners ETF', 'GDX Gold Miners', 40, 25),
    'xbi': (SPDR_CIK, 'State Street(R) SPDR(R) S&P(R) Biotech ETF', 'XBI Biotech', 100, 25),
    'kre': (SPDR_CIK, 'State Street(R) SPDR(R) S&P(R) Regional Banking ETF', 'KRE Regional Banks', 100, 25),
    'icln': (ISHARES_CIK, 'iShares Global Clean Energy ETF', 'ICLN Clean Energy', 80, 25),
}


def _prep_grouping_etf(fund):
    cik, series_name, label, minimum, allow_unresolved = FUNDS[fund]
    data_dir = Path(__file__).resolve().parent.parent / 'data'

    accession, primary_doc, report_date = nport.find_filing(cik, series_name)
    holdings = nport.fetch_stock_holdings(cik, accession, primary_doc)
    if len(holdings) < minimum:
        raise ValueError(
            f'{label} N-PORT lists only {len(holdings)} stocks (expected >={minimum})')
    # A few recent listings lag in OpenFIGI; dropping up to
    # allow_unresolved (with a loud warning) beats blocking the whole
    # refresh on them. They re-enter automatically once OpenFIGI maps
    # their identifiers.
    tickers, unresolved = nport.resolve_tickers(holdings, data_dir,
                                                allow_unresolved=allow_unresolved)
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


def read_prep_smh():
    _prep_grouping_etf('smh')


def read_prep_soxx():
    _prep_grouping_etf('soxx')


def read_prep_iyr():
    _prep_grouping_etf('iyr')


def read_prep_gdx():
    _prep_grouping_etf('gdx')


def read_prep_xbi():
    _prep_grouping_etf('xbi')


def read_prep_kre():
    _prep_grouping_etf('kre')


def read_prep_icln():
    _prep_grouping_etf('icln')


if __name__ == '__main__':
    for fund in FUNDS:
        _prep_grouping_etf(fund)
