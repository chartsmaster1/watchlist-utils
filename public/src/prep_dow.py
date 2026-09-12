
import json
import pandas as pd
import numpy as np
import logging
from pathlib import Path
from common.wiki import fetch_by_schema
from common.tickers import normalize_tickers, report_missing_market_caps

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')

def sort_by_market_cap(df):
    """
    Sorts the DataFrame by MarketCap in descending order.
    """
    data_dir = Path(__file__).resolve().parent.parent / 'data'
    mc_df = pd.read_json(data_dir / 'stocks.json')
    mc_df['Ticker'] = normalize_tickers(mc_df['Ticker'])
    mc_df['TickerKey'] = mc_df['Ticker']

    in_df = df.copy()
    in_df.columns = ['Name', 'Ticker', 'Exchange']
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

def read_prep_dow():

    url = 'https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average'
    data_dir = Path(__file__).resolve().parent.parent / 'data'
    file_name = 'dow'
    file_path = data_dir / (file_name + '.json')
    
    try:
        comps, _table_idx = fetch_by_schema('dow')
        comps_sorted = sort_by_market_cap(comps[['Company', 'Symbol', 'Exchange']])

        report_missing_market_caps(comps_sorted)

        comps_list = comps_sorted[['Name', 'Ticker', 'Exchange']].values.tolist()
        
        res_list = []
        for item in comps_list:
            d = {
                'Name': item[0],
                'Ticker': item[1],
                'Exchange': item[2]
            }
            res_list.append(d)

        with open(file_path, "w") as write_file:
            json.dump(res_list, write_file)

        print('Dow data read and json write was successfull.')

        try:
            df = pd.read_json(file_path)
            df.to_csv(data_dir / 'dow.csv', index=False, encoding='utf-8-sig')
            print('Dow data read and csv write was successfull.')

        except Exception as e:
            logging.error(str(e))
            print('Failed to save Dow data to csv.')


    except Exception as e:
        logging.error(str(e))
        print(f'Dow data read failed. {e}')


if __name__ == '__main__':

    read_prep_dow()