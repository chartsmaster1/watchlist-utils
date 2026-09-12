
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

    sp_df = df.copy()
    sp_df.columns = ['Name', 'Ticker', 'Sector']
    sp_df['TickerKey'] = normalize_tickers(sp_df['Ticker'])
    sp_df = sp_df[sp_df['TickerKey'] != '']

    sp_mc_df = (
        sp_df.merge(
            mc_df[['TickerKey', 'MarketCap']],
            on='TickerKey',
            how='left'
        )
        .sort_values(by='MarketCap', ascending=False)
    )
    sp_mc_df = sp_mc_df.drop(columns=['TickerKey'])

    return sp_mc_df


def read_prep_sandp():
    
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    data_dir = Path(__file__).resolve().parent.parent / 'data'
    file_name = 's&p500'
    json_file_path = data_dir / (file_name + '.json')
    csv_file_path = data_dir / (file_name + '.csv')
    try:
        comps, _table_idx = fetch_by_schema('sp500')
        comps_sorted = sort_by_market_cap(comps[['Security', 'Symbol', 'GICS Sector']])

        report_missing_market_caps(comps_sorted)

        comps_list = comps_sorted[['Name', 'Ticker', 'Sector', 'MarketCap']].values.tolist()
        
        res_list = []
        for item in comps_list:
            d = {
                'Name': item[0],
                'Ticker': item[1],
                'Exchange': '',
                'Sector': item[2],
                'MarketCap': item[3]
            }
            res_list.append(d)

        with open(json_file_path, "w") as write_file:
            json.dump(res_list, write_file)

        print('S&P500 data read and json write was successfull.')

        try:
            df = pd.read_json(json_file_path)
            df['MarketCap'] = df['MarketCap'].astype('float')
            df.to_csv(csv_file_path, index=False, encoding='utf-8-sig')
            print('S&P500 data read and csv write was successfull.')

        except Exception as e:
            logging.error(str(e))
            print(f'Failed to save S&P500 data to CSV. {e}')

            

    except Exception as e:
        logging.error(str(e))
        print(f'S&P500 data read failed. {e}')



if __name__ == '__main__':

    read_prep_sandp()