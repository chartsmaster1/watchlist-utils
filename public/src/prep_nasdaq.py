
import json
import pandas as pd
import numpy as np
import logging
from pathlib import Path
from common.wiki import fetch_by_schema
from common.tickers import normalize_tickers, report_missing_market_caps

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

# The Nasdaq-100 list page classifies by ICB industry, while the other
# index files (s&p500, dow, russell) use GICS sector names. Map ICB to
# the equivalent GICS sector so 'Sector' means the same thing in every
# file; unmapped values pass through unchanged.
ICB_TO_GICS_SECTOR = {
    'Technology': 'Information Technology',
    'Telecommunications': 'Communication Services',
    'Oil & Gas': 'Energy',
    'Oil, Gas & Consumable Fuels': 'Energy',
    'Basic Materials': 'Materials',
    'Consumer Goods': 'Consumer Staples',
    'Consumer Services': 'Consumer Discretionary',
}


def sort_by_market_cap(df):
    """
    Sorts the DataFrame by MarketCap in descending order.
    """
    data_dir = Path(__file__).resolve().parent.parent / 'data'
    mc_df = pd.read_json(data_dir / 'stocks.json')
    mc_df['Ticker'] = normalize_tickers(mc_df['Ticker'])
    mc_df['TickerKey'] = mc_df['Ticker']

    in_df = df.copy()
    in_df.columns = ['Name', 'Ticker', 'Sector']
    in_df['TickerKey'] = normalize_tickers(in_df['Ticker'])
    in_df = in_df[in_df['TickerKey'] != '']

    in_mc_df = (
        in_df.merge(
            mc_df[['TickerKey', 'MarketCap']],
            on='TickerKey',
            how='left'
        )
        .sort_values(by='MarketCap', ascending=False)
    )
    in_mc_df = in_mc_df.drop(columns=['TickerKey'])

    return in_mc_df


def read_prep_nasdaq():
    
    url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
    data_dir = Path(__file__).resolve().parent.parent / 'data'
    file_name = 'nasdaq'
    file_path = data_dir / (file_name + '.json')
    
    try:
        comps, _table_idx = fetch_by_schema('nasdaq100')
        icb_col = next(
            (c for c in comps.columns if str(c).startswith('ICB Industry')),
            None,
        )
        if icb_col is None:
            raise ValueError(
                f'Nasdaq-100 table has no ICB Industry column: {list(comps.columns)}'
            )
        comps_sorted = sort_by_market_cap(comps[['Company', 'Ticker', icb_col]])
        # print(comps_sorted[comps_sorted['MarketCap'].isnull()])

        report_missing_market_caps(comps_sorted)

        comps_sorted['Sector'] = comps_sorted['Sector'].map(
            lambda s: ICB_TO_GICS_SECTOR.get(str(s).strip(), str(s).strip())
        )

        comps_list = comps_sorted[['Name', 'Ticker', 'Sector']].values.tolist()

        res_list = []
        for item in comps_list:
            d = {
                'Name': item[0],
                'Ticker': item[1],
                'Exchange': 'NASDAQ',
                'Sector': item[2]
            }
            res_list.append(d)

        with open(file_path, "w") as write_file:
            json.dump(res_list, write_file)

        print('Nasdaq data read and json write was successfull.')

        try:
            df = pd.read_json(file_path, dtype=str, encoding='utf-8')
            df.to_csv(data_dir / 'nasdaq.csv', index=False, encoding='utf-8-sig')
            print('Nasdaq data read and csv write was successfull.')

        except Exception as e:
            logging.error(str(e))
            print('Failed to save Nasdaq data to csv.')


    except Exception as e:
        logging.error(str(e))
        print(f'Nasdaq data read failed. {e}')


if __name__ == '__main__':

    read_prep_nasdaq()
