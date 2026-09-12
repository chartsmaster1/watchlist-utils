# Source: live scrape of https://companiesmarketcap.com (see common/marketcap_live.py).
# Manual fallback: download CompaniesMarketCap.csv into ../data/ if scrape is blocked.
# Note (fixed): keep_default_na=False so ("Nano Labs","NA") no longer becomes NaN.


import json
import pandas as pd
import logging
from pathlib import Path

from common.marketcap_live import scrape_companies

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')


def read_prep_companies_market_cap(use_live=True):
    
    file_name = 'stocks'
    file_path = Path(__file__).resolve().parent.parent / 'data' / (file_name + '.json')

    # Pages to scrape live (100 rows each). 40 pages = top 4000 covers all but
    # ~110 small-cap Russell names; see compare_marketcap.py for coverage check.
    live_pages, live_delay = 40, 1.0

    try:
        if use_live:
            print(f'Scraping companiesmarketcap.com ({live_pages} pages)...')
            df_live = scrape_companies(max_pages=live_pages, delay=live_delay)
            print(f'Live scrape OK: {len(df_live)} rows.')
            df_new = df_live[['Rank', 'Name', 'Ticker', 'MarketCap', 'Country']]
        else:
            raise RuntimeError('skip-live')

        res_list = df_new.to_dict(orient='records')
        for d in res_list:
            d['Rank'] = int(d['Rank'])
            d['MarketCap'] = int(d['MarketCap'])

        with open(file_path, "w") as write_file:
            json.dump(res_list, write_file)

        print('Companies market cap data read was successfull.')

    except Exception as e:
        if use_live and str(e) != 'skip-live':
            print(f'Live scrape failed ({e}), falling back to manual CSV...')
            logging.warning(f'Live scrape failed ({e}), trying manual CSV fallback.')
            return read_prep_companies_market_cap(use_live=False)
        if str(e) == 'skip-live':
            # Manual CSV fallback: keep_default_na=False fixes Nano Labs "NA" -> NaN bug.
            df_raw = pd.read_csv(
                Path(__file__).resolve().parent.parent / 'data' / 'CompaniesMarketCap.csv',
                keep_default_na=False,
            )
            df_raw = df_raw[df_raw['Symbol'].astype(str).str.strip() != '']
            df_raw['Symbol'] = df_raw['Symbol'].astype(str).str.strip()
            df_csv = df_raw[df_raw['marketcap'] > 0].reset_index(drop=True)
            res_list = [
                {'Rank': int(df_csv.loc[i, 'Rank']), 'Name': df_csv.loc[i, 'Name'],
                 'Ticker': df_csv.loc[i, 'Symbol'], 'MarketCap': int(df_csv.loc[i, 'marketcap']),
                 'Country': df_csv.loc[i, 'country']}
                for i in df_csv.index
            ]
            with open(file_path, "w") as write_file:
                json.dump(res_list, write_file)
            print('Companies market cap data read was successfull (manual CSV fallback).')
            return
        logging.error(str(e))
        print(f'Companies market cap data read failed. {e}')



if __name__ == '__main__':

    read_prep_companies_market_cap()