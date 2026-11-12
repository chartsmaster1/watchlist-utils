# *** Run this script after prep_spdr.py ***
# Sectors are built from the 11 sector SPDR fund lists (xlk.json, xlf.json, ...)
# — the funds themselves are the sector memberships, with real weights —
# instead of grouping spy.json by its Sector field. The ticker sets are
# identical (verified 2026-11-12: 503/503), so the switch changes no names;
# Comps gain the fund Weight.
import json
import pandas as pd
import logging
from pathlib import Path

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')


# Communication Services Select Sector (XLC)
# Consumer Discretionary Select Sector (XLY)
# Consumer Staples Select Sector (XLP)
# Energy Select Sector (XLE)
# Financial Select Sector (XLF)
# Health Care Select Sector (XLV)
# Industrial Select Sector (XLI)
# Materials Select Sector (XLB)
# Real Estate Select Sector (XLRE)
# Technology Select Sector (XLK)
# Utilities Select Sector (XLU)

sector_map = {
    'Industrials': 'XLI',
    'Health Care': 'XLV',
    'Information Technology': 'XLK',
    'Communication Services': 'XLC',
    'Consumer Discretionary': 'XLY',
    'Utilities': 'XLU',
    'Financials': 'XLF',
    'Materials': 'XLB',
    'Real Estate': 'XLRE',
    'Consumer Staples': 'XLP',
    'Energy': 'XLE'
}

# fund file per sector ticker (lowercase, as written by prep_spdr)
sector_files = {v: v.lower() + '.json' for v in sector_map.values()}


def prep_spy_sectors():
    data_dir = Path(__file__).resolve().parent.parent / 'data'
    file_name = 'spysectors'
    file_path = data_dir / (file_name + '.json')

    res_list = []
    frames = []
    all_tickers = []
    for name, ticker in sector_map.items():
        fund_path = data_dir / sector_files[ticker]
        if not fund_path.exists():
            raise FileNotFoundError(f"Missing sector fund file: {fund_path}")
        fund_df = pd.read_json(fund_path, orient='records')
        if len(fund_df) < 10:
            raise ValueError(f"{sector_files[ticker]} has only {len(fund_df)} rows, expected >= 10")
        if fund_df['Ticker'].duplicated().any():
            raise ValueError(f"{sector_files[ticker]} has duplicate tickers")

        sec_items = [
            {'Name': r['Name'], 'Ticker': r['Ticker'], 'Exchange': '',
             'Weight': r.get('Weight')}
            for r in fund_df.to_dict(orient='records')
        ]
        res_list.append({'Name': name, 'Ticker': ticker, 'Comps': sec_items})
        all_tickers.extend(fund_df['Ticker'].tolist())
        frames.append(fund_df)

    if len(all_tickers) != len(set(all_tickers)):
        raise ValueError("Duplicate tickers across sector funds")
    if len(all_tickers) < 450:
        raise ValueError(f"Only {len(all_tickers)} sector members, expected >= 450")

    # informational cross-check against spy.json (funds are the source of
    # truth; a diff here is reported, not a failure)
    spy_path = data_dir / 'spy.json'
    if spy_path.exists():
        spy_tickers = {r['Ticker'] for r in json.load(open(spy_path))}
        diff = spy_tickers ^ set(all_tickers)
        if diff:
            print(f"NOTE: sector funds differ from spy.json by {len(diff)}: {sorted(diff)}")
        else:
            print("Sector funds match spy.json tickers exactly.")

    if res_list:
        with open(file_path, 'w') as fp:
            json.dump(res_list, fp)

        print('S&P 500 sectors data read and json write was successfull.')

        try:
            comps_df = pd.concat(frames, ignore_index=True)
            comps_df['MarketCap'] = comps_df['MarketCap'].round(0).astype('Int64')
            comps_df.to_csv(
                data_dir / 'spysectors.csv', index=False, encoding='utf-8-sig'
            )
            print('S&P 500 sectors data saved to CSV successfully.')
        except Exception as e:
            logging.error(str(e))
            print(f'Failed to save S&P 500 sectors data to CSV. {e}')

    else:
        raise ValueError("Failed to collect SPY sectors.")


if __name__ == '__main__':

    prep_spy_sectors()
