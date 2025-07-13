
import json
import pandas as pd
import numpy as np
import logging

logging.basicConfig(filename='error.log', filemode='w', format='%(levelname)s - %(message)s')


def sort_by_market_cap(df):
    """
    Sorts the DataFrame by MarketCap in descending order.
    """
    mc_df = pd.read_json('../data/stocks.json')
    mc_df['Ticker'] = np.where(mc_df['Ticker'] == 'BRK-B', 'BRK.B', mc_df['Ticker'])
    mc_df['Ticker'] = np.where(mc_df['Ticker'] == 'BF-A', 'BF.B', mc_df['Ticker'])

    in_df = df.copy()
    in_df.columns = ['Name', 'Ticker']
    in_df = in_df[~in_df['Ticker'].isin(['GOOGL'])]

    in_mc_df = (
        in_df.merge(
            mc_df[['Ticker', 'MarketCap']],
            on='Ticker',
            how='left'
        )
        .sort_values(by='MarketCap', ascending=False)
    )

    return in_mc_df


def read_prep_nasdaq():
    
    url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
    file_name = 'nasdaq'
    file_path = '../data/' + file_name + '.json'
    
    try:
        comps = pd.read_html(url)[4]
        comps_sorted = sort_by_market_cap(comps[['Company', 'Ticker']])
        # print(comps_sorted[comps_sorted['MarketCap'].isnull()])

        assert comps_sorted[comps_sorted['MarketCap'].isnull()].shape[0] == 0, "Fix the ticker issue before joining the two dataframes."

        comps_list = comps_sorted[['Name', 'Ticker']].values.tolist()
        
        res_list = []
        for item in comps_list:
            d = {
                'Name': item[0],
                'Ticker': item[1],
                'Exchange': 'NASDAQ'
            }
            res_list.append(d)

        with open(file_path, "w") as write_file:
            json.dump(res_list, write_file)

        print('Nasdaq data read was successfull.')

    except Exception as e:
        logging.error(str(e))
        print(f'Nasdaq data read failed. {e}')


if __name__ == '__main__':

    read_prep_nasdaq()
